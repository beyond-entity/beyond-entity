"""Kafka Bronze + live watermark Silver and nightly retained-history reconciliation."""
from contextlib import nullcontext
from pyspark.sql import functions as F
from .modeled import ModeledSQL, CONTRACT
from .pipeline import now

ENVELOPE = 'event_id STRING, event_type STRING, customer_id STRING, session_id STRING, product_id STRING, order_id STRING, event_time STRING, schema_version STRING'


def decode_kafka(kafka):
    return kafka.select(F.from_json(F.col('value').cast('string'), ENVELOPE).alias('e'),
                        F.col('topic').alias('kafka_topic'), F.col('partition').alias('kafka_partition'),
                        F.col('offset').alias('kafka_offset')).select('e.*', 'kafka_topic', 'kafka_partition', 'kafka_offset', F.current_timestamp().alias('ingested_at'))


def valid_syntax(frame):
    return frame.filter("""event_id IS NOT NULL AND length(trim(event_id)) > 0 AND schema_version = '1'
        AND try_cast(event_time AS timestamp) IS NOT NULL
        AND try_cast(event_time AS timestamp) <= ingested_at + INTERVAL 5 MINUTES
        AND ((event_type IN ('product_viewed','product_added_to_cart') AND length(trim(session_id)) > 0 AND try_cast(product_id AS bigint) IS NOT NULL)
          OR (event_type IN ('order_created','order_cancelled') AND try_cast(order_id AS bigint) IS NOT NULL))""")


def live_candidates(bronze_stream):
    return (valid_syntax(bronze_stream).withColumn('_event_timestamp', F.expr('try_cast(event_time as timestamp)'))
            .withWatermark('_event_timestamp', '2 hours').dropDuplicatesWithinWatermark(['event_id']))


class EventPipeline:
    def __init__(self, spark, warehouse, identity_provider, store=None):
        self.spark, self.warehouse, self.identity_provider, self.store = spark, warehouse, identity_provider, store

    def process(self, raw, batch_id, query_id='events', replay=False):
        lock = self.store.lock(query_id + '-' + str(batch_id), scope='events') if self.store else nullcontext()
        with lock:
            raw = raw.drop('_event_timestamp').persist()
            try:
                rows_read = raw.count()  # Fully consume stateful foreachBatch input, including empty batches.
                identity = self.identity_provider()  # A single publication-pinned snapshot per microbatch.
                sql = ModeledSQL(self.spark)
                inputs = {'raw_customer_events': raw, 'customer_identity_map': identity}
                accepted = sql.run('clean_events', inputs)['silver_customer_events'].persist()
                cached_accepted = accepted
                try:
                    # Nightly replay includes invalid/late raw rows excluded by the live watermark path.
                    rejects = sql.run('quarantine', inputs, indices=[6])['quality_quarantine']
                    # Reconciliation also detects conflicting payloads within one retained raw horizon.
                    semantic=raw.select('event_id',F.sha2(F.to_json(F.struct('event_type',F.expr('try_cast(customer_id as bigint)').alias('customer_id'),
                        'session_id',F.expr('try_cast(product_id as bigint)').alias('product_id'),F.expr('try_cast(order_id as bigint)').alias('order_id'),
                        F.expr('try_cast(event_time as timestamp)').alias('event_time'),'schema_version')),256).alias('_payload'))
                    duplicate_conflicts=semantic.filter('event_id IS NOT NULL').groupBy('event_id').agg(F.countDistinct('_payload').alias('variants')).filter('variants>1').select('event_id')
                    if duplicate_conflicts.limit(1).count():
                        references=raw.join(duplicate_conflicts,'event_id').select(
                            F.sha2(F.concat_ws(':','kafka_topic',F.col('kafka_partition').cast('string'),F.col('kafka_offset').cast('string')),256).alias('reject_id'),
                            F.lit('raw_customer_events').alias('source_table'),F.col('event_id').alias('source_record_id'),F.col('kafka_offset').cast('string').alias('batch_id'),
                            F.lit('CONFLICTING_EVENT_ID').alias('reason_code'),F.col('kafka_topic').alias('source_file'),F.current_timestamp().alias('detected_at'))
                        rejects=rejects.unionByName(references)
                    if self.warehouse.exists('silver_customer_events'):
                        existing = self.warehouse.read('silver_customer_events')
                        joined = accepted.alias('a').join(existing.alias('b'), 'event_id')
                        fields = [c for c in accepted.columns if c != 'event_id']
                        conflicts = joined.filter('NOT (' + ' AND '.join(f'a.`{c}` <=> b.`{c}`' for c in fields) + ')').select('event_id')
                        if conflicts.limit(1).count():
                            refs = raw.join(conflicts, 'event_id').select(
                                F.sha2(F.concat_ws(':', 'kafka_topic', F.col('kafka_partition').cast('string'), F.col('kafka_offset').cast('string')), 256).alias('reject_id'),
                                F.lit('raw_customer_events').alias('source_table'), F.col('event_id').alias('source_record_id'),
                                F.col('kafka_offset').cast('string').alias('batch_id'), F.lit('CONFLICTING_EVENT_ID').alias('reason_code'),
                                F.col('kafka_topic').alias('source_file'), F.current_timestamp().alias('detected_at'))
                            rejects = rejects.unionByName(refs)
                            accepted = accepted.join(conflicts, 'event_id', 'left_anti')
                    rejects = rejects.dropDuplicates(['reject_id'])
                    rows_rejected = rejects.count()
                    qlock = self.store.lock(query_id + '-quarantine', scope='quarantine') if self.store else nullcontext()
                    with qlock:
                        self.warehouse.merge('quality_quarantine', rejects, ['reject_id'])
                    before = self.warehouse.read('silver_customer_events').count() if self.warehouse.exists('silver_customer_events') else 0
                    version = self.warehouse.merge('silver_customer_events', accepted, ['event_id'])
                    after = self.warehouse.read('silver_customer_events', version).count()
                    if self.store:
                        key = f'audit/{query_id}-{batch_id}.json'
                        if self.store.json(key)[0] is None:
                            self.store.immutable(key, dict(run_id=f'{query_id}-{batch_id}', job_name='event_replay' if replay else 'event_stream',
                                started_at=now(), completed_at=now(), status='SUCCEEDED', rows_read=rows_read, rows_written=after-before, rows_rejected=rows_rejected))
                    return {'version': version, 'rows_read': rows_read, 'rows_written': after-before, 'rows_rejected': rows_rejected}
                finally:
                    cached_accepted.unpersist()
            finally:
                raw.unpersist()

    def start_silver(self, bronze_stream, checkpoint, query_id='events', available_now=False):
        writer = (live_candidates(bronze_stream).writeStream.option('checkpointLocation', checkpoint)
                  .foreachBatch(lambda frame, batch: self.process(frame, batch, query_id)))
        return writer.trigger(availableNow=True).start() if available_now else writer.trigger(processingTime='30 seconds').start()

    def reconcile(self, raw_version, run_id):
        return self.process(self.warehouse.read('raw_customer_events', raw_version), run_id, 'events-replay', replay=True)


def start_bronze(spark, kafka_options, warehouse, checkpoint):
    source = spark.readStream.format('kafka').options(**{'startingOffsets':'earliest',**kafka_options,'failOnDataLoss':'true'}).load()
    writer = decode_kafka(source).writeStream.format('delta').outputMode('append').option('checkpointLocation', checkpoint).trigger(processingTime='30 seconds')
    if warehouse.root:
        return writer.start(warehouse.root + '/raw_customer_events')
    return writer.toTable(warehouse.name('raw_customer_events'))
