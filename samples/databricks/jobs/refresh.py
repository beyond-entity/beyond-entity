# Databricks notebook source
import os,sys,json
sys.path.insert(0,os.path.abspath('../src'))
from lakehouse.gold import GoldPipeline
from lakehouse.cadence import job_timestamp
from lakehouse.modeled import Warehouse
from lakehouse.storage import S3Store
for k in ('mode','run_id','as_of_date','catalog','storage_root','reporting_currency','approved_currencies','model_version','report_start','report_end','window_end'):
    dbutils.widgets.text(k,'')
c={k:dbutils.widgets.get(k) for k in ('mode','run_id','as_of_date','catalog','storage_root','reporting_currency','approved_currencies','model_version','report_start','report_end','window_end')}
store=S3Store(c['storage_root']);w=Warehouse(spark,c['catalog']);request=dict(run_id=c['run_id'],as_of_date=c['as_of_date'])
if c['mode']=='gold':
    GoldPipeline(spark,w,store).run(request,c['reporting_currency'],json.loads(c['approved_currencies']))
elif c['mode']=='activity':
    from lakehouse.gold import ActivityPipeline
    ActivityPipeline(spark,w,store).run(dict(run_id=c['run_id'],window_end=job_timestamp(c['window_end'])))
elif c['mode']=='ml':
    from lakehouse.ml import MLPipeline
    MLPipeline(spark,w,store).run(request,c['model_version'],c['reporting_currency'])
elif c['mode']=='activation':
    from lakehouse.exports import Exports
    from lakehouse.epochs import Epochs
    published,_=Epochs(store,'ml').current()
    if published is None:raise ValueError('ML publication required')
    r=published['request']
    Exports(spark,w,store).activation(c['run_id'],r['as_of_date'],r['requested_model_version'],r['reporting_currency'])
elif c['mode']=='report':
    from lakehouse.exports import Exports
    from datetime import date,timedelta
    end=c['report_end'] or c['as_of_date'];start=c['report_start'] or (date.fromisoformat(end)-timedelta(days=1)).isoformat()
    Exports(spark,w,store).report(c['run_id'],start,end)
else:
    raise ValueError('Unknown refresh mode')
