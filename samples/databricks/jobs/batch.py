# Databricks notebook source
import os,sys,json,hashlib
sys.path.insert(0,os.path.abspath('../src'))
from datetime import timedelta
from lakehouse.batch import PostgresSnapshot,SourcePipeline,PartnerPipeline
from lakehouse.silver import SilverPipeline
from lakehouse.modeled import Warehouse
from lakehouse.storage import S3Store
from lakehouse.runtime import customer_inputs
from lakehouse.epochs import Epochs
from lakehouse.source import instant
from lakehouse.cadence import full_baseline_due,products_due,job_timestamp
for k in ('mode','run_id','window_end','catalog','storage_root','secret_scope','approved_currencies','partner_id','partner_object_key','partner_sha256','scheduled_at'):
    dbutils.widgets.text(k,'')
c={k:dbutils.widgets.get(k) for k in ('mode','run_id','window_end','catalog','storage_root','secret_scope','approved_currencies','partner_id','partner_object_key','partner_sha256','scheduled_at')}
store=S3Store(c['storage_root']);w=Warehouse(spark,c['catalog']);cutoff=instant(job_timestamp(c['window_end']))
if c['mode']=='source':
    prior,_=Epochs(store,'commerce_source').current()
    req_key=f'job-requests/commerce_source/{c["run_id"]}.json'
    request,_=store.json(req_key)
    if request is None:
        baseline=Epochs(store,'commerce_source').get(prior['tables'][0]['baseline_run_id'])['request']['window_end'] if prior else None
        full=full_baseline_due(job_timestamp(c['scheduled_at']),baseline)
        product_epoch=prior
        while product_epoch and not product_epoch['request']['full_snapshot'] and 'products' not in product_epoch['request'].get('due',[]):
            product_epoch=Epochs(store,'commerce_source').get(product_epoch['tables'][0]['previous_run_id'])
        product_cutoff=product_epoch['request']['window_end'] if product_epoch else None
        request=dict(run_id=c['run_id'],window_start=prior['request']['window_end'] if prior else (cutoff-timedelta(hours=1)).isoformat(),
            window_end=cutoff.isoformat(),full_snapshot=full,due=['orders','order_items','products'] if products_due(job_timestamp(c['scheduled_at']),product_cutoff) else ['orders','order_items'])
        store.immutable(req_key,request)
    with PostgresSnapshot(dbutils.secrets.get(c['secret_scope'],'postgres-dsn')) as source:
        SourcePipeline(spark,w,store).run(request,source)
elif c['mode']=='partner':
    data,_=store.get(c['partner_object_key'])
    if data is None:raise ValueError('Partner delivery object missing')
    PartnerPipeline(spark,w,store).run(dict(run_id=c['run_id'],window_end=cutoff.isoformat(),full_snapshot=True),data,c['partner_sha256'],c['partner_id'])
elif c['mode']=='silver':
    SilverPipeline(spark,w,store,lambda:customer_inputs(store,w)).run(dict(run_id=c['run_id'],window_end=cutoff.isoformat(),full_snapshot=True),json.loads(c['approved_currencies']),c['partner_id'])
else:raise ValueError('Unknown batch mode')
