import hashlib
from datetime import datetime, timezone
import pytest
from lakehouse.source import COLUMNS, validate_request
from lakehouse.storage import LocalStore, Conflict
from lakehouse.transforms import RAW_SCHEMA, transform, QualityError
from lakehouse.pipeline import CustomerPipeline, DeltaTables, read_published_customers


def row(id='1', **updates):
    value = dict(zip(COLUMNS, [id, ' Alice ', ' Alice@Example.COM ', '+1 (202) 555-0123', ' Main St ', ' us ', 'true',
                              '2026-09-01T01:00:00Z', '2026-09-02T01:00:00Z', 'false']))
    return {**value, **updates}


def raw(spark, records):
    return spark.createDataFrame([tuple(r[c] for c in COLUMNS) + ('s3://fixture/a', str(i), datetime(2026, 9, 3, tzinfo=timezone.utc))
                                  for i, r in enumerate(records)], RAW_SCHEMA)


def test_normalization_privacy_tombstones_and_resolution(spark):
    values = [row(), row('2'), row('2', updated_at='2026-09-03T01:00:00Z', is_deleted='true', email=None),
              row('3', email='bad'), row('3', updated_at='2026-09-03T01:00:00Z', marketing_consent='garbage')]
    n, identity, silver, rejects, blocked = transform(raw(spark, values), 'test-id', 'test-email', 'v1')
    assert not blocked
    ns = {r.customer_id: r.asDict() for r in n.collect()}
    assert set(ns) == {1, 3}
    assert ns[1]['email_norm'] == 'alice@example.com'
    assert ns[1]['phone_norm'] == '12025550123'
    assert ns[3]['marketing_consent'] is False
    assert rejects.count() == 1
    assert set(silver.columns) == {'customer_key', 'email_hash', 'country_code', 'marketing_consent', 'created_at', 'updated_at'}
    ids = {r.customer_id: r.customer_key for r in identity.collect()}
    assert ids[1] == hashlib.sha256(b'test-id:1').hexdigest()
    assert silver.first().email_hash == hashlib.sha256(b'test-email:alice@example.com').hexdigest()


@pytest.mark.parametrize('change', [{'updated_at': 'bad'}, {'customer_id': '01'}, {'is_deleted': 'bad'}, {'email': 'bad'}])
def test_invalid_current_record_blocks(spark, change):
    *_, rejects, blocked = transform(raw(spark, [row(**change)]), 'id', 'email', 'v1')
    assert blocked and rejects.count() == 1


class Source:
    def __init__(self, rows):
        self.data, self.calls = rows, 0
    def rows(self, request):
        self.calls += 1
        yield from self.data


class LocalDelta(DeltaTables):
    def __init__(self, spark, root):
        self.spark = spark
        self.paths = {k: str(root / k) for k in ('raw', 'quarantine', 'normalized', 'identity', 'silver')}
        self.names = {k: f'delta.`{v}`' for k, v in self.paths.items()}
    def exists(self, key):
        from delta.tables import DeltaTable
        return DeltaTable.isDeltaTable(self.spark, self.paths[key])
    def read(self, key, version=None):
        reader = self.spark.read.format('delta')
        if version is not None:
            reader = reader.option('versionAsOf', version)
        return reader.load(self.paths[key])
    def write(self, key, frame, mode):
        frame.write.format('delta').mode(mode).save(self.paths[key])
        return int(self.spark.sql(f'DESCRIBE HISTORY {self.names[key]} LIMIT 1').first()['version'])


def request(batch='baseline', start='2026-09-01T00:00:00Z', end='2026-09-03T00:00:00Z', full=True):
    return dict(batch_id=batch, window_start=start, window_end=end, full_snapshot=full)


@pytest.mark.parametrize('interrupted_stage', ['silver', 'manifest'])
def test_end_to_end_restart_publication_and_delete(spark, tmp_path, interrupted_stage):
    store = LocalStore(tmp_path / 'objects')
    tables = LocalDelta(spark, tmp_path / 'delta')
    source = Source([row(), row('2')])
    pipeline = CustomerPipeline(spark, store, tables, source, 'id', 'email', 'v1')
    with pytest.raises(RuntimeError, match='Injected'):
        pipeline.run(request(), fail_after='raw')
    assert store.json('cursors/customers.json')[0] is None
    baseline = pipeline.run(request())
    assert source.calls == 1
    assert tables.read('raw').count() == 2
    assert pipeline.run(request()) == baseline
    assert read_published_customers(store, tables)['silver'].count() == 2
    source.data = [row('2', updated_at='2026-09-03T01:00:00Z', is_deleted='true')]
    inc = request('inc', '2026-09-03T00:00:00Z', '2026-09-04T00:00:00Z', False)
    with pytest.raises(RuntimeError, match='Injected'):
        pipeline.run(inc, fail_after=interrupted_stage)
    # Physical current versions have changed; consumers still see the complete old epoch.
    assert read_published_customers(store, tables)['identity'].count() == 2
    assert tables.read('identity').count() == 1
    committed = pipeline.run(inc)
    assert committed['rows_written'] == 1 and tables.read('raw').count() == 3
    assert read_published_customers(store, tables)['silver'].count() == 1
    # Future full baseline may legitimately be empty, and must remove stale customers.
    source.data = []
    empty = request('empty', '2026-09-04T00:00:00Z', '2026-09-05T00:00:00Z', True)
    with pytest.raises(RuntimeError, match='Injected'):
        pipeline.run(empty, fail_after='cursor')
    result = pipeline.run(empty)
    assert result['rows_written'] == 0
    assert read_published_customers(store, tables)['silver'].count() == 0
    assert store.json('audit/empty.json')[0]['status'] == 'SUCCEEDED'


def test_gate_failure_keeps_cursor_and_failed_batches_excluded(spark, tmp_path):
    store, source = LocalStore(tmp_path / 'objects'), Source([row()])
    tables = LocalDelta(spark, tmp_path / 'delta')
    p = CustomerPipeline(spark, store, tables, source, 'id', 'email', 'v1')
    p.run(request())
    source.data = [row(updated_at='broken')]
    bad = request('bad', '2026-09-03T00:00:00Z', '2026-09-04T00:00:00Z', False)
    with pytest.raises(QualityError):
        p.run(bad)
    assert store.json('cursors/customers.json')[0]['last_batch_id'] == 'baseline'
    assert tables.read('quarantine').count() == 1
    source.data = [row(updated_at='2026-09-03T01:00:00Z')]
    fixed = {**bad, 'batch_id': 'fixed'}
    assert p.run(fixed)['rows_written'] == 1
    assert tables.read('raw').count() == 3  # Failed Bronze remains evidence, excluded from committed replay.
    stale = request('stale', '2026-09-04T00:00:00Z', '2026-09-06T00:00:00Z', False)
    with pytest.raises(QualityError, match='48 hours'):
        p.run(stale)


def test_conditional_artifacts_and_lock(tmp_path):
    s = LocalStore(tmp_path)
    s.immutable('a.json', {'a': 1})
    s.immutable('a.json', {'a': 1})
    with pytest.raises(Conflict):
        s.immutable('a.json', {'a': 2})
    with s.lock('a'):
        with pytest.raises(Conflict):
            with s.lock('b'):
                pass
    assert s.get('locks/customers.json')[0] is None
    with pytest.raises(ValueError):
        validate_request(request(batch='../unsafe'))
