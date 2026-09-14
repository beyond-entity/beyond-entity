"""Dated features and approved artifact inference, without invented model coefficients."""
from datetime import date
import math
from pyspark.sql import functions as F
from .modeled import ModeledSQL,CONTRACT,conform
from .epochs import Epochs,versions,dependencies,safe_id
from .runtime import pin
from .pipeline import now
from .transforms import QualityError

COEFFICIENTS=['intercept','recency_coefficient','orders_coefficient','revenue_coefficient','views_coefficient','carts_coefficient']


def validate_model(model,as_of_date=None,currency=None):
    if any(not isinstance(model.get(c),(int,float)) or isinstance(model[c],bool) or not math.isfinite(model[c]) for c in COEFFICIENTS):
        raise QualityError('Model coefficients must be finite numbers')
    if not isinstance(model.get('approved'),bool):raise QualityError('Model approval must be Boolean')
    if not model.get('model_version') or not model.get('artifact_uri'):raise QualityError('Model version and artifact provenance required')
    cutoff=model['training_cutoff']
    cutoff=date.fromisoformat(cutoff) if isinstance(cutoff,str) else cutoff
    if as_of_date and (not model['approved'] or cutoff>=date.fromisoformat(as_of_date) or model['currency']!=currency):
        raise QualityError('Model must be approved, currency-compatible, and trained before scoring cutoff')


def equal_rows(left,right,ignore=()):
    columns=[c for c in left.columns if c not in ignore]
    a,b=left.select(*columns),right.select(*columns)
    return not a.exceptAll(b).limit(1).count() and not b.exceptAll(a).limit(1).count()


def register_model(spark,warehouse,store,model):
    validate_model(model)
    expected={c['column_name'] for c in CONTRACT['entities']['churn_model_versions']['columns']}
    if set(model)!=expected:raise QualityError('Model artifact fields differ from contract')
    params={**model,'training_cutoff':date.fromisoformat(model['training_cutoff']) if isinstance(model['training_cutoff'],str) else model['training_cutoff']}
    with store.lock('register',scope='model_registry'):
        candidate=ModeledSQL(spark).run('model_register',params=params)['churn_model_versions']
        if warehouse.exists('churn_model_versions'):
            old=warehouse.read('churn_model_versions').filter(F.col('model_version')==model['model_version'])
            if old.limit(1).count():
                if not equal_rows(candidate,old):raise QualityError('Conflicting immutable model version')
                return warehouse.version('churn_model_versions')
        return warehouse.merge('churn_model_versions',candidate,['model_version'])


class MLPipeline:
    def __init__(self,spark,warehouse,store):
        self.spark,self.w,self.store=spark,warehouse,store;self.epochs=Epochs(store,'ml')

    def freeze_features(self,frame,as_of_date,currency,run_id):
        date.fromisoformat(as_of_date)
        if not currency.isalpha() or len(currency)!=3 or not currency.isupper():raise ValueError('Invalid feature currency')
        table='churn_feature_snapshots';key=f'frozen/{table}/{as_of_date}/{currency}.json'
        old,_=self.store.json(key)
        predicate=(F.col('as_of_date')==F.lit(as_of_date).cast('date'))&(F.col('currency')==currency)
        if old:
            frozen=self.w.read(table,old['delta_version']).filter(predicate)
            if not equal_rows(frame,frozen):raise QualityError('Frozen feature partition differs; explicit backfill decision required')
            return old['delta_version'],frozen
        if self.w.exists(table):
            existing=self.w.read(table).filter(predicate)
            if existing.limit(1).count():
                if not equal_rows(frame,existing):raise QualityError('Existing feature partition differs')
                version=self.w.version(table)
            else:version=self.w.write(table,frame,'append')
        else:version=self.w.write(table,frame,'append')
        row=dict(pipeline_name='ml',run_id=run_id,table_name=table,delta_version=version,previous_run_id=None,
                 baseline_run_id=run_id,full_snapshot=True,window_start=None,window_end=None,as_of_date=as_of_date,committed_at=now())
        self.store.immutable(key,row)
        return version,self.w.read(table,version).filter(predicate)

    def run(self,request,model_version,reporting_currency):
        request={**request,'requested_model_version':model_version,'reporting_currency':reporting_currency}
        asof=request['as_of_date'];date.fromisoformat(asof)
        with self.epochs.run(request) as (previous,token):
            if previous and previous['request']==request:return previous
            def select():
                gold,_=Epochs(self.store,'gold').current()
                if gold is None or gold['request']['as_of_date']!=asof:raise QualityError('Gold snapshot date must match scoring date')
                if not self.w.exists('churn_model_versions'):raise QualityError('Approved model artifact required')
                return {'gold_run':gold['request']['run_id'],'model_delta_version':self.w.version('churn_model_versions')}
            pins=pin(self.store,'ml',request['run_id'],select)
            gold=Epochs(self.store,'gold').get(pins['gold_run'])
            tables={t:self.w.read(t,v) for t,v in versions(gold).items()}
            model_table=self.w.read('churn_model_versions',pins['model_delta_version'])
            rows=model_table.filter(F.col('model_version')==model_version).limit(2).collect()
            if len(rows)!=1:raise QualityError('Exactly one model version required')
            validate_model(rows[0].asDict(),asof,reporting_currency)
            sql=ModeledSQL(self.spark);params={'as_of_date':asof,'reporting_currency':reporting_currency,'requested_model_version':model_version}
            features=sql.run('build_churn_features',tables,params)['churn_feature_snapshots']
            fv,frozen=self.freeze_features(features,asof,reporting_currency,request['run_id'])
            scores=sql.run('score_customer_churn',{'churn_feature_snapshots':frozen,'churn_model_versions':model_table},params)['customer_churn_scores']
            if scores.count()!=frozen.count() or scores.filter('churn_probability IS NULL OR isnan(churn_probability) OR churn_probability < 0 OR churn_probability > 1').limit(1).count():
                raise QualityError('Scoring completeness/probability gate failed')
            if self.w.exists('customer_churn_scores'):
                existing=self.w.read('customer_churn_scores').filter((F.col('as_of_date')==F.lit(asof).cast('date'))&(F.col('model_version')==model_version)&(F.col('currency')==reporting_currency))
                if existing.limit(1).count() and not equal_rows(scores,existing,ignore=['scored_at']):raise QualityError('Conflicting immutable score partition')
            sv=self.w.merge('customer_churn_scores',scores,['customer_key','as_of_date','model_version','currency'])
            return self.epochs.commit(request,{'churn_feature_snapshots':fv,'customer_churn_scores':sv},previous,token,
                dependencies(gold)+[('model_registry',model_version,'churn_model_versions',pins['model_delta_version'])],metrics=(frozen.count(),scores.count(),0))
