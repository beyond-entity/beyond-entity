"""Customer vertical slice. ADR-010 is the publication/replay contract."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re
import uuid
from pyspark.sql import functions as F
from .source import COLUMNS, instant, validate_request
from .storage import encode, Conflict
from .transforms import RAW_SCHEMA, QualityError, transform


def now():
    return datetime.now(timezone.utc).isoformat()


class DeltaTables:
    def __init__(self, spark, catalog='retail_lakehouse'):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', catalog):
            raise ValueError('Unsafe catalog identifier')
        self.spark = spark
        self.names = {k: f'{catalog}.{schema}.{table}' for k, schema, table in [
            ('raw', 'bronze', 'raw_customers'), ('quarantine', 'bronze', 'quality_quarantine'),
            ('normalized', 'silver_restricted', 'normalized_customers'),
            ('identity', 'silver_restricted', 'customer_identity_map'), ('silver', 'silver', 'silver_customers')]}

    def exists(self, key):
        return self.spark.catalog.tableExists(self.names[key])

    def read(self, key, version=None):
        reader = self.spark.read.format('delta')
        if version is not None:
            reader = reader.option('versionAsOf', version)
        return reader.table(self.names[key])

    def write(self, key, frame, mode):
        frame.write.format('delta').mode(mode).saveAsTable(self.names[key])
        return int(self.spark.sql(f'DESCRIBE HISTORY {self.names[key]} LIMIT 1').first()['version'])


class CustomerPipeline:
    def __init__(self, spark, store, tables, source, identity_pepper, email_pepper, key_version):
        self.spark, self.store, self.tables, self.source = spark, store, tables, source
        self.secrets = identity_pepper, email_pepper, key_version
        spark.conf.set('spark.sql.session.timeZone', 'UTC')
        # Enable at cluster creation too; do not expose plans containing secret values.
        spark.conf.set('spark.sql.redaction.options.regex', '(?i)secret|password|token|pepper|dsn')

    def publication(self, batch):
        result, _ = self.store.json(f'publications/{batch}.json')
        if result is None:
            raise QualityError('Committed publication missing')
        return result

    def epoch(self, request, previous):
        if request['full_snapshot']:
            return [request['batch_id']], request['batch_id']
        if previous is None:
            raise QualityError('Initial run requires full snapshot')
        batches = [request['batch_id']]
        current = previous
        seen = set(batches)
        while True:
            b = current['batch_id']
            if b in seen:
                raise QualityError('Publication cycle')
            seen.add(b)
            batches.append(b)
            if current['full_snapshot']:
                if instant(request['window_end']) - instant(current['window_end']) > timedelta(hours=48):
                    raise QualityError('Baseline older than 48 hours')
                return batches, b
            current = self.publication(current['previous_batch_id'])

    def landing(self, request):
        batch = request['batch_id']
        manifest_key = f'landing/customers/{batch}/complete.json'
        manifest, _ = self.store.json(manifest_key)
        data_key = f'postgresql/customers/batch_id={batch}/rows.jsonl'
        if manifest is None:
            self.store.immutable(f'landing/customers/{batch}/request.json', request)
            # Data objects are atomic writes. Recover a completed orphan without querying the source.
            data, _ = self.store.get(data_key)
            extracted = now()
            if data is not None:
                rows = [json.loads(x) for x in data.splitlines()]
                count = len(rows)
                extracted = rows[0]['extracted_at'] if rows else extracted
            else:
                lines, count, size = [], 0, 0
                for row in self.source.rows(request):
                    if set(row) != set(COLUMNS) or any(x is not None and not isinstance(x, str) for x in row.values()):
                        raise QualityError('Source contract mismatch')
                    line = encode({**row, 'source_file': self.store.uri(data_key), 'batch_id': batch, 'extracted_at': extracted}) + b'\n'
                    size += len(line)
                    if size > 64 * 1024 * 1024:
                        raise QualityError('Sample batch exceeds 64 MiB; partitioned extractor required')
                    lines.append(line)
                    count += 1
                data = b''.join(lines)
                self.store.put(data_key, data, None)
            manifest = {'request': request, 'data_key': data_key, 'rows_read': count,
                        'sha256': hashlib.sha256(data).hexdigest(), 'extracted_at': extracted}
            self.store.immutable(manifest_key, manifest)
        if manifest['request'] != request:
            raise Conflict('Batch request changed')
        data, _ = self.store.get(manifest['data_key'])
        if data is None or hashlib.sha256(data).hexdigest() != manifest['sha256']:
            raise QualityError('Landing checksum mismatch')
        return manifest, data

    def audit(self, run_id, started, status, rows_read, rows_written, rows_rejected):
        key = f'audit/{run_id}.json'
        if self.store.json(key)[0] is None:
            self.store.immutable(key, dict(run_id=run_id, job_name='customers', started_at=started,
                                          completed_at=now(), status=status, rows_read=rows_read,
                                          rows_written=rows_written, rows_rejected=rows_rejected))

    def run(self, request, fail_after=None):
        """fail_after is a test fault hook: raw, normalized, identity, silver, manifest, cursor."""
        validate_request(request)
        batch = request['batch_id']
        started, counts = now(), [0, 0, 0]
        with self.store.lock(batch):
            cursor, etag = self.store.json('cursors/customers.json')
            previous = self.publication(cursor['last_batch_id']) if cursor else None
            if previous and previous['batch_id'] == batch:
                if any(previous[k] != request[k] for k in request):
                    raise Conflict('Committed request differs')
                self.audit(batch, previous['committed_at'], 'SUCCEEDED', previous['rows_read'], previous['rows_written'], previous['rows_rejected'])
                return previous
            if cursor and instant(request['window_start']) != instant(cursor['last_successful_watermark']):
                raise QualityError('Window must start at committed cursor')
            if previous and previous['key_version'] != self.secrets[2]:
                raise QualityError('Key rotation requires coordinated architecture/backfill')
            batches, baseline = self.epoch(request, previous)
            try:
                manifest, data = self.landing(request)
                counts[0] = manifest['rows_read']
                # Explicit schema: do not infer or coerce source PII types.
                rows = []
                ingested_at = now()
                for line in data.splitlines():
                    row = json.loads(line)
                    rows.append(tuple(row[c] for c in (*COLUMNS, 'source_file', 'batch_id')) + (instant(ingested_at),))
                raw_batch = self.spark.createDataFrame(rows, RAW_SCHEMA)
                if raw_batch.groupBy('customer_id').count().filter('count > 1').limit(1).count():
                    raise QualityError('Duplicate source key within landing batch')
                present = self.tables.exists('raw') and self.tables.read('raw').filter(F.col('batch_id') == batch).limit(1).count()
                if not present:
                    raw_version = self.tables.write('raw', raw_batch, 'append')
                else:
                    raw_version = int(self.spark.sql(f'DESCRIBE HISTORY {self.tables.names["raw"]} LIMIT 1').first()['version'])
                self.fault(fail_after, 'raw')
                raw = self.tables.read('raw', raw_version).filter(F.col('batch_id').isin(batches))
                # Batch manifests prove completeness even for empty full snapshots.
                expected = sum(self.store.json(f'landing/customers/{b}/complete.json')[0]['rows_read'] for b in batches)
                if raw.count() != expected:
                    raise QualityError('Bronze epoch is incomplete or duplicated')
                normalized, identity, silver, rejects, blocking = transform(raw, *self.secrets)
                counts[2] = rejects.filter(F.col('batch_id') == batch).count()
                with self.store.lock(batch, scope='quarantine'):
                    if self.tables.exists('quarantine'):
                        rejects = rejects.join(self.tables.read('quarantine').select('reject_id'), 'reject_id', 'left_anti')
                    self.tables.write('quarantine', rejects, 'append')
                if blocking:
                    raise QualityError('Current customer quality gate failed; see restricted quarantine')
                counts[1] = normalized.count()
                versions = {}
                for key, frame, pk in [('normalized', normalized, 'customer_id'), ('identity', identity, 'customer_id'), ('silver', silver, 'customer_key')]:
                    if frame.count() != counts[1] or frame.filter(F.col(pk).isNull()).limit(1).count() or frame.select(pk).distinct().count() != counts[1]:
                        raise QualityError('Customer sink count/key reconciliation failed')
                    versions[key + '_version'] = self.tables.write(key, frame, 'overwrite')
                    # Validate the actual committed sink, not only the computed frame.
                    if self.tables.read(key, versions[key + '_version']).count() != counts[1]:
                        raise QualityError('Persisted customer sink count mismatch')
                    self.fault(fail_after, key)
                pub = {**request, **versions, 'previous_batch_id': previous['batch_id'] if previous else None,
                       'baseline_batch_id': baseline, 'raw_version': raw_version, 'rows_read': counts[0],
                       'rows_written': counts[1], 'rows_rejected': counts[2], 'key_version': self.secrets[2], 'committed_at': now()}
                pub_key = f'publications/{batch}.json'
                existing, _ = self.store.json(pub_key)
                if existing:
                    # Previous attempt finished sinks. Its immutable versions are authoritative.
                    if any(existing[k] != pub[k] for k in (*request.keys(), 'previous_batch_id', 'baseline_batch_id', 'key_version')):
                        raise Conflict('Publication predecessor/request differs')
                    pub = existing
                else:
                    self.store.immutable(pub_key, pub)
                self.fault(fail_after, 'manifest')
                self.store.put('cursors/customers.json', encode(dict(source_table='customers', last_successful_watermark=request['window_end'],
                    last_batch_id=batch, checkpoint_uri=self.store.uri(pub_key))), etag)
                self.fault(fail_after, 'cursor')
                self.audit(batch, started, 'SUCCEEDED', *counts)
                return pub
            except Exception:
                # A committed cursor takes precedence over a failed post-commit audit response.
                active, _ = self.store.json('cursors/customers.json')
                if not active or active['last_batch_id'] != batch:
                    self.audit(batch + '-attempt-' + uuid.uuid4().hex, started, 'FAILED', *counts)
                raise

    @staticmethod
    def fault(actual, stage):
        if actual == stage:
            raise RuntimeError('Injected failure after ' + stage)


def read_published_customers(store, tables):
    """Capture one cursor once, then pin all tables for downstream jobs."""
    cursor, _ = store.json('cursors/customers.json')
    if cursor is None:
        raise QualityError('No committed customer publication')
    pub, _ = store.json(f'publications/{cursor["last_batch_id"]}.json')
    return {k: tables.read(k, pub[k + '_version']) for k in ('normalized', 'identity', 'silver')}
