# Databricks notebook source
# Runtime 14.3 LTS+; existing Unity Catalog schemas and restricted service principal.
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))
from datetime import timedelta
from lakehouse.source import PostgresCustomers, instant
from lakehouse.cadence import full_baseline_due,job_timestamp
from lakehouse.pipeline import CustomerPipeline, DeltaTables
from lakehouse.storage import S3Store

for key in ('batch_id', 'window_end', 'catalog', 'storage_root', 'secret_scope', 'key_version', 'scheduled_at'):
    dbutils.widgets.text(key, '')
settings = {k: dbutils.widgets.get(k) for k in ('batch_id', 'window_end', 'catalog', 'storage_root', 'secret_scope', 'key_version', 'scheduled_at')}
if not all(settings.values()):
    raise ValueError('All customer job parameters are required')
store = S3Store(settings['storage_root'])
batch = settings['batch_id']
# Persisted request survives task retries, repairs and the post-cursor audit repair path.
request, _ = store.json(f'landing/customers/{batch}/request.json')
if request is None:
    cursor, _ = store.json('cursors/customers.json')
    cutoff = instant(job_timestamp(settings['window_end']))
    baseline=None
    if cursor:
        previous,_=store.json(f'publications/{cursor["last_batch_id"]}.json')
        base,_=store.json(f'publications/{previous["baseline_batch_id"]}.json')
        baseline=base['window_end']
    request = dict(batch_id=batch, window_start=cursor['last_successful_watermark'] if cursor else (cutoff - timedelta(hours=1)).isoformat(),
                   window_end=cutoff.isoformat(), full_snapshot=full_baseline_due(job_timestamp(settings['scheduled_at']),baseline))
scope = settings['secret_scope']
pipeline = CustomerPipeline(spark, store, DeltaTables(spark, settings['catalog']),
    PostgresCustomers(dbutils.secrets.get(scope, 'postgres-dsn')),
    dbutils.secrets.get(scope, 'identity-pepper'), dbutils.secrets.get(scope, 'email-pepper'), settings['key_version'])
result = pipeline.run(request)
# Return control-plane metadata only, never rows, SQL plans, config objects or secrets.
dbutils.notebook.exit(__import__('json').dumps({k: result[k] for k in ('batch_id', 'rows_read', 'rows_written', 'rows_rejected')}))
