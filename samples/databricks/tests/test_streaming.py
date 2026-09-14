from datetime import datetime, timezone
from pathlib import Path
from pyspark.sql import functions as F
from lakehouse.streaming import EventPipeline, decode_kafka
from lakehouse.modeled import Warehouse


def events(spark, rows):
    defaults = dict(event_id='e1', event_type='product_viewed', customer_id='1', session_id='s', product_id='10', order_id=None,
                    event_time='2026-09-01T01:00:00Z', schema_version='1', kafka_topic='events', kafka_partition=0, kafka_offset=0,
                    ingested_at=datetime(2026,9,1,2,tzinfo=timezone.utc))
    schema='event_id string,event_type string,customer_id string,session_id string,product_id string,order_id string,event_time string,schema_version string,kafka_topic string,kafka_partition int,kafka_offset long,ingested_at timestamp'
    return spark.createDataFrame([{**defaults, **r} for r in rows], schema)


def test_event_replay_validation_identity_recovery_and_retention(spark, tmp_path):
    w = Warehouse(spark, root=str(tmp_path/'tables'))
    mapping = [spark.createDataFrame([(1,'key1')], 'customer_id long, customer_key string')]
    p = EventPipeline(spark, w, lambda: mapping[0])
    raw = events(spark,[{}, {'event_id':'late','kafka_offset':1,'event_time':'2026-08-01T00:00:00Z'},
        {'event_id':'orphan','customer_id':'2','kafka_offset':2}, {'event_id':'bad','product_id':None,'kafka_offset':3},
        {'event_id':'future','event_time':'2099-01-01T00:00:00Z','kafka_offset':4}])
    assert p.process(raw, 0, replay=True)['rows_written'] == 2
    assert w.read('quality_quarantine').count() == 3
    assert p.process(raw, 0, replay=True)['rows_written'] == 0
    mapping[0] = spark.createDataFrame([(1,'key1'),(2,'key2')], 'customer_id long, customer_key string')
    assert p.process(raw, 1, replay=True)['rows_written'] == 1
    # Replaying only a new horizon preserves old Silver history.
    assert p.process(events(spark,[{'event_id':'new','kafka_offset':10}]), 2)['rows_written'] == 1
    assert w.read('silver_customer_events').count() == 4
    assert p.process(events(spark,[{'event_id':'e1','event_type':'product_added_to_cart','kafka_offset':11}]),3)['rows_rejected'] == 1
    assert w.read('silver_customer_events').filter("event_id='e1'").first().event_type == 'product_viewed'


def test_actual_stream_checkpoint_restart(spark, tmp_path):
    source = tmp_path/'source'; source.mkdir()
    frame = events(spark,[{}, {'kafka_offset':1}])
    frame.write.mode('overwrite').parquet(str(source/'batch'))
    w = Warehouse(spark, root=str(tmp_path/'tables'))
    identity = spark.createDataFrame([(1,'key')], 'customer_id long, customer_key string')
    p = EventPipeline(spark,w,lambda:identity)
    def run():
        stream = spark.readStream.schema(frame.schema).option('recursiveFileLookup','true').parquet(str(source))
        q = p.start_silver(stream,str(tmp_path/'checkpoint'),available_now=True)
        q.awaitTermination(120)
        assert not q.isActive
        assert not [t for t in spark.catalog.listTables('global_temp') if t.name.startswith('_be_')]
    run()
    assert w.read('silver_customer_events').count() == 1
    run()
    assert w.read('silver_customer_events').count() == 1


def test_conflicting_payloads_in_one_replay_horizon(spark,tmp_path):
    w=Warehouse(spark,root=str(tmp_path/'tables'))
    identity=spark.createDataFrame([(1,'key')],'customer_id long,customer_key string')
    p=EventPipeline(spark,w,lambda:identity)
    result=p.process(events(spark,[{}, {'kafka_offset':1,'event_type':'product_added_to_cart'}]),0,replay=True)
    assert result['rows_rejected']==2 and result['rows_written']==1
    assert w.read('silver_customer_events').first().event_type=='product_viewed'
    assert not [t for t in spark.catalog.listTables('global_temp') if t.name.startswith('_be_')]
