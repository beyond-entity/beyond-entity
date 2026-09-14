"""proc_tLb4Vvc4IN: extract PostgreSQL customers as canonical raw strings."""
from datetime import datetime, timezone
import re

COLUMNS = ('customer_id', 'full_name', 'email', 'phone', 'address', 'country_code',
           'marketing_consent', 'created_at', 'updated_at', 'is_deleted')


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('UTC-aware timestamp required')
    return result.astimezone(timezone.utc)


def validate_request(request):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', request['batch_id']):
        raise ValueError('Unsafe batch_id')
    start, end = instant(request['window_start']), instant(request['window_end'])
    if start >= end or end > datetime.now(timezone.utc):
        raise ValueError('Invalid extraction window')
    if type(request['full_snapshot']) is not bool:
        raise ValueError('full_snapshot must be Boolean')


class PostgresCustomers:
    def __init__(self, dsn):
        self.dsn = dsn  # from secret service; never include this object in logging

    def rows(self, request):
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            conn.execute("SET LOCAL TIME ZONE 'UTC'")
            sql = 'SELECT ' + ', '.join(f'CAST({c} AS TEXT) AS {c}' for c in COLUMNS)
            sql += ''' FROM public.customers
                       WHERE (%s OR updated_at >= %s::timestamptz - INTERVAL '5 minutes')
                       AND updated_at < %s::timestamptz ORDER BY updated_at, customer_id'''
            with conn.cursor(name='customer_extract') as cursor:
                cursor.execute(sql, (request['full_snapshot'], request['window_start'], request['window_end']))
                for row in cursor:
                    yield row
