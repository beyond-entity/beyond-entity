"""Explicit JSONL object handoffs; no unsolicited external API/message delivery."""
from datetime import date
from pyspark.sql import functions as F
from .modeled import ModeledSQL
from .epochs import Epochs,versions,safe_id
from .runtime import customer_inputs
from .storage import Conflict
from .transforms import QualityError


def json_lines(frame):
    chunks=[];size=0
    for row in frame.toJSON().toLocalIterator():
        part=row.encode()+b'\n';size+=len(part)
        if size>64*1024*1024:raise QualityError('Sample export exceeds 64 MiB; partitioned export required')
        chunks.append(part)
    return b''.join(chunks)


class Exports:
    def __init__(self,spark,warehouse,store):self.spark,self.w,self.store=spark,warehouse,store
    def activation(self,run_id,as_of_date,model_version,currency):
        safe_id(run_id);date.fromisoformat(as_of_date)
        # Always recheck consent, including retries of a prior export invocation.
        with self.store.lock(run_id,scope='activation'):
            ml,_=Epochs(self.store,'ml').current()
            if ml is None:raise QualityError('ML publication required')
            customers,_=customer_inputs(self.store,self.w)
            scores=self.w.read('customer_churn_scores',versions(ml)['customer_churn_scores'])
            selected=scores.filter((F.col('as_of_date')==F.lit(as_of_date).cast('date'))&(F.col('model_version')==model_version)&(F.col('currency')==currency))
            if (ml['request']['as_of_date'],ml['request']['requested_model_version'],ml['request']['reporting_currency'])!=(as_of_date,model_version,currency):
                raise QualityError('Activation must select the published ML request')
            frame=ModeledSQL(self.spark).run('activation_export',{'customer_churn_scores':selected,'silver_customers':customers['silver']},
                {'as_of_date':as_of_date,'requested_model_version':model_version,'reporting_currency':currency})['customer_activation_export']
            key='exports/activation/active.jsonl';data=json_lines(frame);_,etag=self.store.get(key)
            self.store.put(key,data,etag)
            return {'uri':self.store.uri(key),'rows_written':frame.count()}
    def report(self,run_id,start,end):
        safe_id(run_id)
        if date.fromisoformat(start)>=date.fromisoformat(end):raise ValueError('Report date interval is empty or reversed')
        with self.store.lock(run_id,scope='report'):
            request=dict(run_id=run_id,report_start=start,report_end=end)
            key=f'exports/reports/{run_id}'
            self.store.immutable(key+'/request.json',request)
            data,_=self.store.get(key+'/rows.jsonl')
            if data is None:
                source,_=self.store.json(key+'/source.json')
                if source is None:
                    gold,_=Epochs(self.store,'gold').current()
                    if gold is None:raise QualityError('Gold publication required')
                    source=dict(consumer_pipeline='report',consumer_run_id=run_id,source_pipeline='gold',source_run_id=gold['request']['run_id'],
                                source_table='daily_sales',source_delta_version=versions(gold)['daily_sales'])
                    self.store.immutable(key+'/source.json',source)
                frame=ModeledSQL(self.spark).run('report_export',{'daily_sales':self.w.read('daily_sales',source['source_delta_version'])},
                    {'report_start':start,'report_end':end})['sales_report_extract']
                data=json_lines(frame);self.store.put(key+'/rows.jsonl',data,None)
            return {'uri':self.store.uri(key+'/rows.jsonl'),'rows_written':len(data.splitlines())}
