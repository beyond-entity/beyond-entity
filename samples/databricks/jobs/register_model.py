# Databricks notebook source
import os,sys,json
sys.path.insert(0,os.path.abspath('../src'))
from lakehouse.ml import register_model
from lakehouse.modeled import Warehouse
from lakehouse.storage import S3Store
for k in ('catalog','storage_root','artifact_object_key'):
    dbutils.widgets.text(k,'')
store=S3Store(dbutils.widgets.get('storage_root'))
data,_=store.get(dbutils.widgets.get('artifact_object_key'))
if data is None:raise ValueError('Approved release artifact object required')
register_model(spark,Warehouse(spark,dbutils.widgets.get('catalog')),store,json.loads(data))
