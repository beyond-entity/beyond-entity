# Databricks notebook source
import os, sys, json
sys.path.insert(0, os.path.abspath('../src'))
from lakehouse.streaming import EventPipeline, start_bronze
from lakehouse.modeled import Warehouse
from lakehouse.pipeline import DeltaTables, read_published_customers
from lakehouse.storage import S3Store
for key in ('mode','catalog','storage_root','checkpoint_root','secret_scope','run_id'):
    dbutils.widgets.text(key,'')
cfg={k:dbutils.widgets.get(k) for k in ('mode','catalog','storage_root','checkpoint_root','secret_scope','run_id')}
store=S3Store(cfg['storage_root'])
w=Warehouse(spark,cfg['catalog'])
p=EventPipeline(spark,w,lambda:read_published_customers(store,DeltaTables(spark,cfg['catalog']))['identity'],store)
if cfg['mode']=='bronze':
    options=json.loads(dbutils.secrets.get(cfg['secret_scope'],'kafka-options-json'))
    start_bronze(spark,options,w,cfg['checkpoint_root']+'/bronze-events').awaitTermination()
elif cfg['mode']=='silver':
    stream=spark.readStream.format('delta').table(w.name('raw_customer_events'))
    p.start_silver(stream,cfg['checkpoint_root']+'/silver-events').awaitTermination()
elif cfg['mode']=='replay':
    p.reconcile(w.version('raw_customer_events'),cfg['run_id'])
else:
    raise ValueError('Unknown event mode')
