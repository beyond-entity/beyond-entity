import os
os.environ.setdefault('SPARK_LOCAL_IP', '127.0.0.1')
os.environ.setdefault('PYSPARK_PYTHON', __import__('sys').executable)
import pytest
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip


@pytest.fixture(scope='session')
def spark(tmp_path_factory):
    builder = (SparkSession.builder.master('local[2]').appName('BE-customer-contract-tests')
               .config('spark.ui.enabled', 'false').config('spark.sql.shuffle.partitions', '2')
               .config('spark.databricks.delta.snapshotPartitions', '2')
               .config('spark.sql.warehouse.dir', str(tmp_path_factory.mktemp('warehouse')))
               .config('spark.sql.extensions', 'io.delta.sql.DeltaSparkSessionExtension')
               .config('spark.sql.catalog.spark_catalog', 'org.apache.spark.sql.delta.catalog.DeltaCatalog')
               .config('spark.sql.session.timeZone', 'UTC'))
    session = configure_spark_with_delta_pip(builder).getOrCreate()
    session.sparkContext.setLogLevel('ERROR')
    yield session
    session.stop()
