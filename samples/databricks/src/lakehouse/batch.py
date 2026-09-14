"""Commerce source and checksum-verified authoritative partner ingestion."""
import csv
import hashlib
import io
import json
from datetime import timedelta
from pyspark.sql import functions as F
from .source import instant
from .pipeline import now
from .storage import encode, Conflict
from .epochs import Epochs, versions, safe_id
from .modeled import CONTRACT, sql_type
from .transforms import QualityError

SOURCES = {'orders':'order_id','order_items':'order_item_id','products':'product_id'}


class PostgresSnapshot:
    """All due commerce sources share one repeatable-read transaction."""
    def __init__(self, dsn):
        self.dsn = dsn
    def __enter__(self):
        import psycopg
        from psycopg.rows import dict_row
        self.connection = psycopg.connect(self.dsn,row_factory=dict_row)
        self.connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        self.connection.execute("SET LOCAL TIME ZONE 'UTC'")
        return self
    def __exit__(self,*args):
        self.connection.close()
    def rows(self, table, request):
        if table not in SOURCES:
            raise ValueError('Unmodeled source')
        cols = [c['column_name'] for c in CONTRACT['entities'][table]['columns']]
        query = 'SELECT '+','.join(f'CAST({c} AS TEXT) AS {c}' for c in cols)+f' FROM public.{table}'
        query += f" WHERE (%s OR updated_at >= %s::timestamptz - INTERVAL '5 minutes') AND updated_at < %s::timestamptz ORDER BY updated_at,{SOURCES[table]}"
        with self.connection.cursor(name='extract_'+table) as cursor:
            cursor.execute(query,(request['full_snapshot'],request['window_start'],request['window_end']))
            yield from cursor


class SourcePipeline:
    def __init__(self,spark,warehouse,store):
        self.spark,self.w,self.store=spark,warehouse,store
        self.epochs=Epochs(store,'commerce_source')

    def landing(self,table,request,provider):
        rid=safe_id(request['run_id']); key=f'landing/{table}/{rid}'
        completed,_=self.store.json(key+'/complete.json')
        cols=[c['column_name'] for c in CONTRACT['entities'][table]['columns']]
        if completed:
            if completed['request']!=request:raise Conflict('Source batch changed')
        else:
            self.store.immutable(key+'/request.json',request)
            data,_=self.store.get(key+'/rows.jsonl')
            extracted=now()
            if data is None:
                chunks=[];size=0
                for row in provider.rows(table,request):
                    if set(row)!=set(cols) or any(x is not None and not isinstance(x,str) for x in row.values()):
                        raise QualityError('Source string contract differs: '+table)
                    chunk=encode({**row,'source_file':self.store.uri(key+'/rows.jsonl'),'batch_id':rid,'extracted_at':extracted})+b'\n'
                    size+=len(chunk)
                    if size>64*1024*1024:raise QualityError('Source batch exceeds sample 64 MiB limit')
                    chunks.append(chunk)
                data=b''.join(chunks);self.store.put(key+'/rows.jsonl',data,None)
            completed={'request':request,'sha256':hashlib.sha256(data).hexdigest(),'rows_read':len(data.splitlines())}
            self.store.immutable(key+'/complete.json',completed)
        data,_=self.store.get(key+'/rows.jsonl')
        if data is None or hashlib.sha256(data).hexdigest()!=completed['sha256']:raise QualityError('Source checksum mismatch')
        rows=[json.loads(x) for x in data.splitlines()]
        if len({r[SOURCES[table]] for r in rows})!=len(rows):raise QualityError('Duplicate source primary key')
        schema=','.join(f'{c} STRING' for c in cols+['source_file','batch_id'])+',ingested_at TIMESTAMP'
        timestamp=instant(now())
        frame=self.spark.createDataFrame([tuple(r[c] for c in cols+['source_file','batch_id'])+(timestamp,) for r in rows],schema)
        return frame,completed['rows_read']

    def run(self,request,provider):
        if type(request['full_snapshot']) is not bool or instant(request['window_start'])>=instant(request['window_end']) or instant(request['window_end'])>instant(now()):raise ValueError('Invalid source window')
        with self.epochs.run(request) as (previous,token):
            if previous and previous['request']==request:return previous
            if previous and request['window_start']!=previous['request']['window_end']:raise QualityError('Source cursor gap')
            if not previous and not request['full_snapshot']:raise QualityError('Initial full baseline required')
            due=list(SOURCES) if request['full_snapshot'] else list(request.get('due',['orders','order_items']))
            if not set(due)<=set(SOURCES) or not {'orders','order_items'}<=set(due):raise ValueError('Invalid due sources')
            out=versions(previous) if previous else {}; read=0
            for table in due:
                frame,count=self.landing(table,request,provider);read+=count
                raw='raw_'+table
                if not self.w.exists(raw) or not self.w.read(raw).filter(F.col('batch_id')==request['run_id']).limit(1).count():
                    out[raw]=self.w.write(raw,frame,'append')
                else:out[raw]=self.w.version(raw)
            baseline=request['run_id'] if request['full_snapshot'] else previous['tables'][0]['baseline_run_id']
            return self.epochs.commit(request,out,previous,token,baseline=baseline,metrics=(read,read,0))

    def horizon(self,epoch):
        current=epoch; batches=[]; cutoff=instant(epoch['request']['window_end'])
        while True:
            batches.append(current['request']['run_id'])
            if current['request']['full_snapshot']:
                if cutoff-instant(current['request']['window_end'])>timedelta(hours=48):raise QualityError('Stale commerce baseline')
                break
            current=self.epochs.get(current['tables'][0]['previous_run_id'])
        result={}
        for table,version in versions(epoch).items():
            source=table.removeprefix('raw_'); expected=0
            for rid in batches:
                manifest,_=self.store.json(f'landing/{source}/{rid}/complete.json')
                if manifest:expected+=manifest['rows_read']
            frame=self.w.read(table,version).filter(F.col('batch_id').isin(batches))
            if frame.count()!=expected:raise QualityError('Incomplete committed source horizon')
            result[table]=frame
        return result


class PartnerPipeline:
    def __init__(self,spark,warehouse,store):
        self.spark,self.w,self.store=spark,warehouse,store;self.epochs=Epochs(store,'partner')
    def run(self,request,data,expected_sha256,partner_id):
        request={**request,'expected_sha256':expected_sha256,'authoritative_partner_id':partner_id}
        if hashlib.sha256(data).hexdigest()!=expected_sha256:raise QualityError('Partner checksum mismatch')
        with self.epochs.run(request) as (previous,token):
            if previous and previous['request']==request:return previous
            key=f'landing/partner/{safe_id(request["run_id"])}/delivery.csv'
            old,_=self.store.get(key)
            if old is None:self.store.put(key,data,None)
            elif old!=data:raise Conflict('Partner delivery changed')
            reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
            fields=['partner_id','product_code','brand','supplier_region','effective_date']
            if reader.fieldnames!=fields:raise QualityError('Partner CSV columns/order differ')
            rows=list(reader)
            if any(r['partner_id']!=partner_id or any(not v or not v.strip() for v in r.values()) for r in rows):raise QualityError('Invalid authoritative partner delivery')
            if len({r['product_code'].strip().upper() for r in rows})!=len(rows):raise QualityError('Duplicate partner SKU')
            schema=','.join(f'{c} STRING' for c in fields+['file_checksum','source_file','batch_id'])+',ingested_at TIMESTAMP'
            raw=self.spark.createDataFrame([tuple(r[c] for c in fields)+(expected_sha256,self.store.uri(key),request['run_id'],instant(now())) for r in rows],schema)
            if raw.filter('try_cast(effective_date as date) IS NULL').limit(1).count():raise QualityError('Invalid partner effective date')
            if not self.w.exists('raw_partner_products') or not self.w.read('raw_partner_products').filter(F.col('batch_id')==request['run_id']).limit(1).count():
                version=self.w.write('raw_partner_products',raw,'append')
            else:version=self.w.version('raw_partner_products')
            return self.epochs.commit(request,{'raw_partner_products':version},previous,token,metrics=(len(rows),len(rows),0))
