# Databricks notebook source
import os,sys,json
sys.path.insert(0,os.path.abspath('../src'))
import psycopg
from psycopg.rows import dict_row
from lakehouse.application import KafkaPublisher,relay_order_events
for k in ('secret_scope','kafka_topic'):
    dbutils.widgets.text(k,'')
scope=dbutils.widgets.get('secret_scope')
publisher=KafkaPublisher.configured(json.loads(dbutils.secrets.get(scope,'kafka-producer-options-json')),dbutils.widgets.get('kafka_topic'))
with psycopg.connect(dbutils.secrets.get(scope,'postgres-dsn'),row_factory=dict_row) as connection:
    result=relay_order_events(connection,publisher)
if result['failed']:
    raise RuntimeError('Outbox delivery failures remain pending for retry')
