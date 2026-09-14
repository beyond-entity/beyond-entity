"""Execute Beyond Entity staged SQL with explicit contracts and publication-aware sinks."""
import json
import re
import uuid
from pathlib import Path
from pyspark.sql import functions as F
from delta.tables import DeltaTable
from .transforms import QualityError

CONTRACT = json.loads(Path(__file__).with_name('contracts.json').read_text())
SCHEMAS = {'bronze': 'bronze', 'restricted': 'silver_restricted', 'silver': 'silver', 'gold': 'gold', 'ml': 'ml'}


def sql_type(t):
    return {'TIMESTAMP_LTZ': 'TIMESTAMP', 'TIMESTAMP_TZ': 'TIMESTAMP', 'number': 'DOUBLE',
            'string': 'STRING', 'Boolean': 'BOOLEAN', 'DECIMAL': 'DECIMAL(18,2)'}.get(t, t)


def conform(frame, table):
    columns = CONTRACT['entities'][table]['columns']
    if set(frame.columns) != {c['column_name'] for c in columns}:
        raise QualityError('Output columns differ from modeled contract: ' + table)
    # ANSI CAST raises on overflow, unlike silent decimal truncation to NULL.
    expressions=[]
    from pyspark.sql.types import NumericType
    for c in columns:
        name=c['column_name']
        if c['data_type']=='number' and isinstance(frame.schema[name].dataType,NumericType):
            expressions.append(f'`{name}`')
        else:
            expressions.append(f"CAST(`{name}` AS {sql_type(c['data_type'])}) AS `{name}`")
    result=frame.selectExpr(*expressions)
    required = [c['column_name'] for c in columns if c['is_not_null'] or c['is_primary_key']]
    if required and result.filter(' OR '.join(f'`{c}` IS NULL' for c in required)).limit(1).count():
        raise QualityError('Required output field missing: ' + table)
    keys = [c['column_name'] for c in columns if c['is_primary_key']]
    if keys and result.groupBy(*keys).count().filter('count > 1').limit(1).count():
        raise QualityError('Duplicate output grain: ' + table)
    return result


class ModeledSQL:
    def __init__(self, spark):
        self.spark = spark
        self.prefix = '_be_' + uuid.uuid4().hex + '_'
        self.views = set()
        names = set(CONTRACT['entities']) | {p['module'] for p in CONTRACT['processors'].values()}
        self.identifiers = re.compile(r'\b(' + '|'.join(re.escape(n) for n in sorted(names,key=len,reverse=True)) + r')\b')
        spark.conf.set('spark.sql.session.timeZone', 'UTC')
        spark.conf.set('spark.sql.ansi.enabled', 'true')

    def qualify(self, sql):
        # Only replace model identifiers outside SQL string literals (including escaped quotes).
        pieces = re.split(r"('(?:''|[^'])*')", sql)
        return ''.join(piece if i % 2 else self.identifiers.sub(lambda m: "global_temp."+self.prefix+m.group(0),piece) for i,piece in enumerate(pieces))

    def view(self, name, frame):
        qualified=self.prefix+name
        frame.createOrReplaceGlobalTempView(qualified)
        self.views.add(qualified)

    def bind(self, tables):
        for name, frame in tables.items():
            self.view(name,frame)

    def run(self, key, tables=None, params=None, indices=None):
        self.bind(tables or {})
        processor = CONTRACT['processors'][key]
        outputs = {}
        try:
            for index, sql in enumerate(processor['sql']):
                if indices is not None and index not in indices:
                    continue
                if sql.startswith('SELECT '):
                    self.view(processor['module'],self.spark.sql(self.qualify(sql), args=params or {}))
                elif sql.startswith('INSERT INTO '):
                    match = re.match(r'INSERT INTO (\w+) \(([^)]+)\) (SELECT .*)', sql, re.S)
                    if not match:
                        raise ValueError('Unsupported modeled INSERT')
                    name, columns, select = match.groups()
                    names = [c.strip() for c in columns.split(',')]
                    frame = self.spark.sql(self.qualify(select), args=params or {}).toDF(*names)
                    frame = conform(frame, name)
                    if name in outputs:
                        frame = outputs[name].unionByName(frame)
                    outputs[name] = frame
                else:
                    raise ValueError('Use a transactional source adapter for this processor')
            return outputs
        finally:
            # Returned DataFrames contain analyzed plans; no per-microbatch catalog leak.
            for name in self.views:
                self.spark.catalog.dropGlobalTempView(name)
            self.views.clear()


class Warehouse:
    def __init__(self, spark, catalog='retail_lakehouse', root=None):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', catalog):
            raise ValueError('Unsafe catalog')
        self.spark, self.catalog, self.root = spark, catalog, root

    def name(self, table):
        if table not in CONTRACT['entities']:
            raise ValueError('Unmodeled table')
        if self.root:
            return f'delta.`{self.root}/{table}`'
        return f"{self.catalog}.{SCHEMAS[CONTRACT['entities'][table]['model']]}.{table}"

    def exists(self, table):
        return DeltaTable.isDeltaTable(self.spark, self.root + '/' + table) if self.root else self.spark.catalog.tableExists(self.name(table))

    def read(self, table, version=None):
        reader = self.spark.read.format('delta')
        if version is not None:
            reader = reader.option('versionAsOf', version)
        return reader.load(self.root + '/' + table) if self.root else reader.table(self.name(table))

    def version(self, table):
        return int(self.spark.sql('DESCRIBE HISTORY ' + self.name(table) + ' LIMIT 1').first()['version'])

    def write(self, table, frame, mode='overwrite'):
        writer = conform(frame, table).write.format('delta').mode(mode)
        if self.root:
            writer.save(self.root + '/' + table)
        else:
            writer.saveAsTable(self.name(table))
        return self.version(table)

    def merge(self, table, frame, keys):
        frame = conform(frame, table)
        if not self.exists(table):
            return self.write(table, frame)
        target = DeltaTable.forPath(self.spark, self.root + '/' + table) if self.root else DeltaTable.forName(self.spark, self.name(table))
        target.alias('t').merge(frame.alias('s'), ' AND '.join(f't.`{k}` = s.`{k}`' for k in keys)).whenNotMatchedInsertAll().execute()
        return self.version(table)
