import io
import json
from unittest.mock import MagicMock, patch
from botocore.stub import Stubber
import boto3
import pytest
from lakehouse.storage import S3Store, Conflict
from lakehouse.source import PostgresCustomers
from test_customer import request, row, Source
from lakehouse.pipeline import CustomerPipeline
from lakehouse.storage import LocalStore, encode


def test_s3_conditional_write_and_missing():
    client = boto3.client('s3', region_name='us-east-1', aws_access_key_id='synthetic', aws_secret_access_key='synthetic')
    store = S3Store('s3://example-test/root', client)
    with Stubber(client) as stub:
        stub.add_response('put_object', {}, {'Bucket': 'example-test', 'Key': 'root/a', 'Body': b'x', 'IfNoneMatch': '*'})
        store.put('a', b'x', None)
        stub.add_response('put_object', {}, {'Bucket': 'example-test', 'Key': 'root/a', 'Body': b'y', 'IfMatch': 'etag-1'})
        store.put('a', b'y', 'etag-1')
        stub.add_client_error('put_object', 'PreconditionFailed', http_status_code=412,
                              expected_params={'Bucket': 'example-test', 'Key': 'root/a', 'Body': b'x', 'IfNoneMatch': '*'})
        with pytest.raises(Conflict):
            store.put('a', b'x', None)
        stub.add_client_error('get_object', 'NoSuchKey', http_status_code=404,
                              expected_params={'Bucket': 'example-test', 'Key': 'root/missing'})
        assert store.get('missing') == (None, None)
        stub.assert_no_pending_responses()


def test_postgres_repeatable_read_utc_and_bound_parameters():
    conn, cursor = MagicMock(), MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.__iter__.return_value = iter([row()])
    with patch('psycopg.connect') as connect:
        connect.return_value.__enter__.return_value = conn
        assert list(PostgresCustomers('synthetic-dsn').rows(request())) == [row()]
    assert [c.args[0] for c in conn.execute.call_args_list] == [
        'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY', "SET LOCAL TIME ZONE 'UTC'"]
    sql, params = cursor.execute.call_args.args
    assert "INTERVAL '5 minutes'" in sql and 'ORDER BY updated_at, customer_id' in sql
    assert params == (True, request()['window_start'], request()['window_end'])
    assert '2026-' not in sql


def test_landing_orphan_recovery_without_source_read(tmp_path):
    store, source = LocalStore(tmp_path), Source([row()])
    p = object.__new__(CustomerPipeline)
    p.store, p.source = store, source
    req = request()
    key = 'postgresql/customers/batch_id=baseline/rows.jsonl'
    store.immutable('landing/customers/baseline/request.json', req)
    data = encode({**row(), 'source_file': store.uri(key), 'batch_id': 'baseline', 'extracted_at': '2026-09-03T00:00:00Z'}) + b'\n'
    store.put(key, data, None)
    manifest, actual = p.landing(req)
    assert actual == data and manifest['rows_read'] == 1 and source.calls == 0
    # Immutable request prevents batch ID reuse for different source windows.
    with pytest.raises(Conflict):
        p.landing({**req, 'window_end': '2026-09-04T00:00:00Z'})
