"""ADR-012 immutable publication envelopes with explicit version/dependency rows."""
from contextlib import contextmanager
import re
import uuid
from .storage import encode, Conflict
from .pipeline import now
from .transforms import QualityError


def safe_id(value):
    if not re.fullmatch('[A-Za-z0-9_-]{1,100}', value):
        raise ValueError('Unsafe run identifier')
    return value


class Epochs:
    def __init__(self, store, pipeline):
        safe_id(pipeline)
        self.store, self.pipeline = store, pipeline

    def get(self, run_id):
        value, _ = self.store.json(f'epochs/{self.pipeline}/{safe_id(run_id)}.json')
        if value is None:
            raise QualityError('Missing committed epoch: ' + self.pipeline)
        return value

    def current(self):
        cursor, token = self.store.json(f'cursors/{self.pipeline}.json')
        return (self.get(cursor['last_batch_id']) if cursor else None), token

    @contextmanager
    def run(self, request):
        safe_id(request['run_id'])
        with self.store.lock(request['run_id'], scope=self.pipeline):
            previous, token = self.current()
            if previous and previous['request']['run_id'] == request['run_id'] and previous['request'] != request:
                raise Conflict('Committed run request differs')
            if previous and previous['request'] == request and 'audit' in previous:
                self.store.immutable(f'audit/{self.pipeline}-{request["run_id"]}.json',previous['audit'])
            try:
                yield previous, token
            except Exception:
                current, _ = self.current()
                if not current or current['request']['run_id'] != request['run_id']:
                    self.audit(request['run_id']+'-attempt-'+uuid.uuid4().hex, 'FAILED', None, None, None)
                raise

    def audit(self, run_id, status, rows_read, rows_written, rows_rejected):
        key = f'audit/{self.pipeline}-{run_id}.json'
        if self.store.json(key)[0] is None:
            self.store.immutable(key, dict(run_id=run_id,job_name=self.pipeline,started_at=now(),completed_at=now(),status=status,
                                           rows_read=rows_read,rows_written=rows_written,rows_rejected=rows_rejected))

    def commit(self, request, versions, previous, token, dependencies=(), baseline=None, metrics=(0,0,0)):
        rid = request['run_id']
        rows = [dict(pipeline_name=self.pipeline,run_id=rid,table_name=table,delta_version=version,
                     previous_run_id=previous['request']['run_id'] if previous else None,
                     baseline_run_id=baseline or rid,full_snapshot=request.get('full_snapshot',True),
                     window_start=request.get('window_start'),window_end=request.get('window_end'),
                     as_of_date=request.get('as_of_date'),committed_at=now()) for table,version in versions.items()]
        deps = [dict(consumer_pipeline=self.pipeline,consumer_run_id=rid,source_pipeline=p,source_run_id=r,
                     source_table=t,source_delta_version=v) for p,r,t,v in dependencies]
        value = {'request':request,'tables':rows,'dependencies':deps,'audit':dict(run_id=rid,job_name=self.pipeline,started_at=now(),completed_at=now(),status='SUCCEEDED',rows_read=metrics[0],rows_written=metrics[1],rows_rejected=metrics[2])}
        key = f'epochs/{self.pipeline}/{rid}.json'
        existing, _ = self.store.json(key)
        if existing:
            if existing['request'] != request or existing['dependencies'] != deps:
                raise Conflict('Immutable epoch request/dependencies differ')
            value = existing
        else:
            self.store.immutable(key,value)
        self.store.put(f'cursors/{self.pipeline}.json',encode(dict(source_table=self.pipeline,last_batch_id=rid,
            last_successful_watermark=request.get('window_end',request.get('as_of_date',now())),checkpoint_uri=self.store.uri(key))),token)
        self.store.immutable(f'audit/{self.pipeline}-{rid}.json',value['audit'])
        return value


def versions(epoch):
    return {r['table_name']:r['delta_version'] for r in epoch['tables']}


def dependencies(epoch):
    return [(r['pipeline_name'],r['run_id'],r['table_name'],r['delta_version']) for r in epoch['tables']]
