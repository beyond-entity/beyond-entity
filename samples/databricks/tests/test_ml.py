from datetime import date
import json
import math
import pytest
from pyspark.sql import functions as F
from lakehouse.gold import build_gold
from lakehouse.ml import MLPipeline,register_model,validate_model
from lakehouse.modeled import Warehouse,ModeledSQL
from lakehouse.exports import Exports
from lakehouse.epochs import Epochs
from lakehouse.storage import LocalStore,encode
from lakehouse.transforms import QualityError
from test_gold import gold_tables


def artifact(**changes):
    return dict(model_version='synthetic-v1',artifact_uri='urn:synthetic:test-only',training_cutoff='2026-08-01',currency='USD',
        intercept=0.,recency_coefficient=0.,orders_coefficient=0.,revenue_coefficient=0.,views_coefficient=0.,carts_coefficient=0.,approved=True,**changes)


def setup(spark,tmp_path):
    store=LocalStore(tmp_path/'objects');w=Warehouse(spark,root=str(tmp_path/'tables'))
    source=gold_tables(spark);cv=w.write('silver_customers',source['silver_customers'])
    store.immutable('publications/c1.json',{'batch_id':'c1','silver_version':cv,'normalized_version':0,'identity_version':0})
    # Export provider reads each published customer table; minimal restricted fixtures are still physical Delta.
    n=source['silver_customers'].select(F.lit(1).cast('long').alias('customer_id'),F.lit('x').alias('full_name'),F.lit('x@y').alias('email_norm'),F.lit('1').alias('phone_norm'),F.lit('x').alias('address'),'country_code','marketing_consent','created_at','updated_at').limit(1)
    w.write('normalized_customers',n)
    w.write('customer_identity_map',n.select('customer_id',F.lit('c1').alias('customer_key'),F.lit('v1').alias('key_version'),'updated_at'))
    store.put('cursors/customers.json',encode({'last_batch_id':'c1'}),None)
    out=build_gold(spark,source,'2026-09-03','USD');v={t:w.write(t,f) for t,f in out.items()}
    e=Epochs(store,'gold');req={'run_id':'g1','as_of_date':'2026-09-03'}
    with e.run(req) as (prior,token):e.commit(req,v,prior,token)
    return store,w


def test_model_validation_rejects_nonfinite_and_training_leakage():
    bad=artifact();bad['intercept']=math.nan
    with pytest.raises(QualityError,match='finite'):validate_model(bad)
    bad=artifact();bad['training_cutoff']='2026-09-03'
    with pytest.raises(QualityError,match='trained'):validate_model(bad,'2026-09-03','USD')


def test_ml_features_scores_freeze_registry_and_consent_export(spark,tmp_path):
    store,w=setup(spark,tmp_path)
    model=artifact();version=register_model(spark,w,store,model)
    assert register_model(spark,w,store,model)==version
    changed={**model,'intercept':1.}
    with pytest.raises(QualityError,match='immutable'):register_model(spark,w,store,changed)
    p=MLPipeline(spark,w,store);req={'run_id':'ml1','as_of_date':'2026-09-03'}
    pub=p.run(req,'synthetic-v1','USD')
    assert p.run(req,'synthetic-v1','USD')==pub
    scores=w.read('customer_churn_scores').collect()
    assert len(scores)==2 and all(x.churn_probability==.5 for x in scores)
    assert w.read('churn_feature_snapshots').filter("customer_key='cold'").first().days_since_purchase==365
    modified=w.read('churn_feature_snapshots').withColumn('total_orders',F.col('total_orders')+1)
    with pytest.raises(QualityError,match='Frozen'):p.freeze_features(modified,'2026-09-03','USD','different')
    exports=Exports(spark,w,store)
    assert exports.activation('a1','2026-09-03','synthetic-v1','USD')['rows_written']==1
    current=w.read('silver_customers').withColumn('marketing_consent',F.lit(False))
    cv=w.write('silver_customers',current)
    store.immutable('publications/c2.json',{'batch_id':'c2','silver_version':cv,'normalized_version':0,'identity_version':0})
    _,etag=store.get('cursors/customers.json');store.put('cursors/customers.json',encode({'last_batch_id':'c2'}),etag)
    assert exports.activation('a1','2026-09-03','synthetic-v1','USD')['rows_written']==0
    assert store.get('exports/activation/active.jsonl')[0]==b''
    assert exports.report('r1','2026-09-01','2026-09-02')['rows_written']==2
    assert exports.report('r2','2026-09-02','2026-09-03')['rows_written']==0


def test_empty_feature_partition_is_frozen(spark,tmp_path):
    store,w=setup(spark,tmp_path)
    p=MLPipeline(spark,w,store)
    gold=w.read('customer_360').filter('false')
    empty=ModeledSQL(spark).run('build_churn_features',{'customer_360':gold,'customer_activity_summary':w.read('customer_activity_summary')},
        {'as_of_date':'2026-09-03','reporting_currency':'USD'})['churn_feature_snapshots']
    p.freeze_features(empty,'2026-09-03','USD','empty')
    full=ModeledSQL(spark).run('build_churn_features',{'customer_360':w.read('customer_360'),'customer_activity_summary':w.read('customer_activity_summary')},
        {'as_of_date':'2026-09-03','reporting_currency':'USD'})['churn_feature_snapshots']
    with pytest.raises(QualityError,match='Frozen'):p.freeze_features(full,'2026-09-03','USD','later')
