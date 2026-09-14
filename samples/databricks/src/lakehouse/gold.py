"""Modeled Gold marts from a pinned Silver epoch and retained event version."""
from datetime import date
from contextlib import nullcontext
from pyspark.sql import functions as F
from .modeled import ModeledSQL
from .epochs import Epochs, versions, dependencies
from .runtime import pin
from .transforms import QualityError

KEYS=['aggregate_daily_sales','aggregate_product_performance','aggregate_customer_value','aggregate_customer_activity','build_customer_360']


def build_gold(spark,tables,as_of_date,reporting_currency):
    date.fromisoformat(as_of_date)
    sql=ModeledSQL(spark);result={}
    for key in KEYS:
        result.update(sql.run(key,{**tables,**result},{'as_of_date':as_of_date,'reporting_currency':reporting_currency,'activity_cutoff':as_of_date+'T00:00:00Z'}))
    orders=tables['silver_orders'].filter((F.col('order_status')=='completed') & (F.col('ordered_at')<F.lit(as_of_date).cast('timestamp')))
    expected=orders.join(tables['silver_order_items'],'order_id').groupBy('currency').agg(F.sum('line_amount').alias('expected'))
    actual=result['daily_sales'].groupBy('currency').agg(F.sum('gross_revenue').alias('actual'))
    difference=expected.join(actual,'currency','full').filter(F.coalesce('expected',F.lit(0))!=F.coalesce('actual',F.lit(0)))
    if difference.limit(1).count():raise QualityError('Gold per-currency revenue reconciliation failed')
    return result


class GoldPipeline:
    def __init__(self,spark,warehouse,store):
        self.spark,self.w,self.store=spark,warehouse,store;self.epochs=Epochs(store,'gold')
    def run(self,request,reporting_currency,approved_currencies):
        request={**request,'reporting_currency':reporting_currency,'approved_currencies':sorted(approved_currencies)}
        date.fromisoformat(request['as_of_date'])
        if reporting_currency not in approved_currencies:raise ValueError('Reporting currency must be approved')
        with self.epochs.run(request) as (previous,token):
            if previous and previous['request']==request:return previous
            def select():
                silver,_=Epochs(self.store,'silver_commerce').current()
                if silver is None or not self.w.exists('silver_customer_events'):raise QualityError('Silver and event history are required')
                return {'silver_run':silver['request']['run_id'],'event_version':self.w.version('silver_customer_events')}
            pins=pin(self.store,'gold',request['run_id'],select)
            silver=Epochs(self.store,'silver_commerce').get(pins['silver_run'])
            tables={t:self.w.read(t,v) for t,v in versions(silver).items()}
            customer_deps=[(d['source_pipeline'],d['source_run_id'],d['source_table'],d['source_delta_version']) for d in silver['dependencies'] if d['source_pipeline']=='customers']
            for _,_,table,version in customer_deps:tables[table]=self.w.read(table,version)
            if 'silver_customers' not in tables:raise QualityError('Silver publication lacks pinned customer contract')
            tables['silver_customer_events']=self.w.read('silver_customer_events',pins['event_version'])
            output=build_gold(self.spark,tables,request['as_of_date'],reporting_currency)
            published={}
            for t,f in output.items():
                lock=self.store.lock(request['run_id'],scope='activity') if t=='customer_activity_summary' else nullcontext()
                with lock:published[t]=self.w.write(t,f)
            deps=dependencies(silver)+customer_deps+[('events','delta-'+str(pins['event_version']),'silver_customer_events',pins['event_version'])]
            return self.epochs.commit(request,published,previous,token,deps,metrics=(sum(f.count() for f in tables.values()),sum(f.count() for f in output.values()),0))


class ActivityPipeline:
    def __init__(self,spark,warehouse,store):
        self.spark,self.w,self.store=spark,warehouse,store;self.epochs=Epochs(store,'activity_live')
    def run(self,request):
        from .runtime import customer_inputs
        from .source import instant
        instant(request['window_end'])
        with self.epochs.run(request) as (previous,token):
            if previous and previous['request']==request:return previous
            def select():
                _,deps=customer_inputs(self.store,self.w)
                return {'customer_dependencies':deps,'event_version':self.w.version('silver_customer_events')}
            pins=pin(self.store,'activity_live',request['run_id'],select)
            deps=pins['customer_dependencies']
            tables={t:self.w.read(t,v) for _,_,t,v in deps}
            tables['silver_customer_events']=self.w.read('silver_customer_events',pins['event_version'])
            frame=ModeledSQL(self.spark).run('aggregate_customer_activity',tables,{'activity_cutoff':request['window_end']})['customer_activity_summary']
            with self.store.lock(request['run_id'],scope='activity'):
                version=self.w.write('customer_activity_summary',frame)
            return self.epochs.commit(request,{'customer_activity_summary':version},previous,token,
                deps+[('events','delta-'+str(pins['event_version']),'silver_customer_events',pins['event_version'])],metrics=(tables['silver_customer_events'].count(),frame.count(),0))
