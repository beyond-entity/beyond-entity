"""Commerce Silver with source-version, currency, join and grain publication gates."""
from datetime import timedelta
from pyspark.sql import functions as F, Window
from .modeled import ModeledSQL
from .batch import SourcePipeline, SOURCES
from .epochs import Epochs, versions, dependencies
from .pipeline import read_published_customers, DeltaTables
from .source import instant
from .transforms import QualityError
from .runtime import pin


def latest(raw, key):
    bad = raw.filter(f'try_cast({key} as bigint) IS NULL OR {key} <> CAST(try_cast({key} as bigint) AS string) OR try_cast(updated_at AS timestamp) IS NULL OR try_cast(is_deleted AS boolean) IS NULL')
    distinct=raw.dropDuplicates(raw.columns)
    tie = distinct.groupBy(key,'updated_at','ingested_at','batch_id').count().filter('count > 1').limit(1).count()
    window=Window.partitionBy(key).orderBy(F.expr('try_cast(updated_at as timestamp)').desc(),F.col('ingested_at').desc(),F.col('batch_id').desc())
    selected=distinct.withColumn('_r',F.row_number().over(window)).filter('_r=1').drop('_r')
    return selected,bool(tie or bad.limit(1).count())


def reject_refs(raw,source,reason):
    key=SOURCES[source.removeprefix('raw_')]
    return raw.select(F.sha2(F.concat_ws(':',F.coalesce(F.col(key),F.lit('null')),'batch_id','source_file',F.lit(reason)),256).alias('reject_id'),
        F.lit(source).alias('source_table'),F.col(key).alias('source_record_id'),'batch_id',F.lit(reason).alias('reason_code'),'source_file',F.current_timestamp().alias('detected_at'))


class SilverPipeline:
    def __init__(self,spark,warehouse,store,customer_provider):
        self.spark,self.w,self.store,self.customer_provider=spark,warehouse,store,customer_provider
        self.epochs=Epochs(store,'silver_commerce')

    def run(self,request,approved_currencies,partner_id):
        request={**request,'approved_currencies':sorted(approved_currencies),'authoritative_partner_id':partner_id}
        if not approved_currencies or any(len(c)!=3 or not c.isupper() for c in approved_currencies):raise ValueError('Approved currencies required')
        with self.epochs.run(request) as (previous,token):
            if previous and previous['request']==request:return previous
            cached_customers={}
            def select_inputs():
                source,_=Epochs(self.store,'commerce_source').current();partner,_=Epochs(self.store,'partner').current()
                if source is None or partner is None:raise QualityError('Missing source/partner publication')
                customers,deps=self.customer_provider();cached_customers.update(customers)
                return {'source_run':source['request']['run_id'],'partner_run':partner['request']['run_id'],'customer_dependencies':deps}
            pins=pin(self.store,'silver_commerce',request['run_id'],select_inputs)
            source=Epochs(self.store,'commerce_source').get(pins['source_run']);partner=Epochs(self.store,'partner').get(pins['partner_run'])
            customer_deps=pins['customer_dependencies']
            customers=cached_customers or {'identity':self.w.read(t,v) for p,r,t,v in customer_deps if t=='customer_identity_map'}
            cutoff=instant(request['window_end'])
            for epoch in (source,partner):
                age=cutoff-instant(epoch['request']['window_end'])
                if age<timedelta(0) or age>timedelta(hours=48):raise QualityError('Source/partner publication is stale or from the future')
            raw=SourcePipeline(self.spark,self.w,self.store).horizon(source)
            selected={}; blocked=False; refs=[]
            for table,frame in raw.items():
                chosen,bad=latest(frame,SOURCES[table.removeprefix('raw_')]);selected[table]=chosen;blocked|=bad
                if bad:refs.append(reject_refs(chosen,table,'INVALID_SOURCE_VERSION'))
            partner_raw=self.w.read('raw_partner_products',versions(partner)['raw_partner_products']).filter(F.col('batch_id')==partner['request']['run_id'])
            sql=ModeledSQL(self.spark); tables={**selected,'raw_partner_products':partner_raw,'customer_identity_map':customers['identity']}
            params={'authoritative_partner_id':partner_id}
            output={}
            for key in ['clean_products','clean_orders','clean_items','clean_partner','enrich_products']:
                output.update(sql.run(key,{**tables,**output},params))
            # Reconcile all current live source rows against accepted IDs; never count inner-join drops as success.
            for source_name,target in [('orders','silver_orders'),('products','silver_products'),('order_items','silver_order_items')]:
                key=SOURCES[source_name];live=selected['raw_'+source_name].filter('try_cast(is_deleted as boolean)=false')
                missing=live.alias('r').join(output[target].select(F.col(key).cast('string').alias(key)),key,'left_anti')
                if missing.limit(1).count():blocked=True;refs.append(reject_refs(missing,'raw_'+source_name,'INVALID_OR_UNRESOLVED_RECORD'))
                if source_name in ('orders','products'):
                    invalid=live.filter(~F.upper(F.trim('currency')).isin(list(approved_currencies)))
                    if invalid.limit(1).count():blocked=True;refs.append(reject_refs(invalid,'raw_'+source_name,'UNAPPROVED_CURRENCY'))
            historic=sql.run('quarantine',{**raw,'raw_partner_products':partner_raw,'customer_identity_map':customers['identity'],**output},indices=[1,2,3,4,5,7])['quality_quarantine']
            for frame in refs:historic=historic.unionByName(frame)
            historic=historic.dropDuplicates(['reject_id'])
            with self.store.lock(request['run_id'],scope='quarantine'):
                self.w.merge('quality_quarantine',historic,['reject_id'])
            if blocked:raise QualityError('Silver current-epoch quality/reconciliation failed')
            published={table:self.w.write(table,frame) for table,frame in output.items()}
            deps=dependencies(source)+dependencies(partner)+customer_deps
            return self.epochs.commit(request,published,previous,token,deps,metrics=(sum(x.count() for x in raw.values()),sum(x.count() for x in output.values()),historic.count()))
