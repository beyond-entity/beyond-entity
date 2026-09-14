"""Airflow DAG for Beyond Entity proc_EMd95vDcg4 "PostgreSQL Subscription Ingestion".

One task covering both statements. They share a batch, and the event high-water
mark is read from the target inside the run, so splitting them would only create a
window in which the mark could be read before a concurrent write.

Note the two different progress mechanisms in one processor: subscriptions use the
Airflow data interval, subscription events use an id high-water mark read from
RAW_SUBSCRIPTION_EVENTS. That is deliberate -- see the pipeline module.
"""

from __future__ import annotations

import pendulum
from airflow.decorators import dag, task

from pipelines.postgres_subscription_ingestion import INGESTION_JOB_ID, run

SCHEDULE = "15 * * * *"  # proc_EMd95vDcg4 other_info.schedule


@dag(
    dag_id=INGESTION_JOB_ID,
    schedule=SCHEDULE,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,  # the event high-water mark must not be read concurrently
    tags=["ingestion", "postgresql", "raw", "pii"],
    doc_md=__doc__,
)
def dag_ingest_postgres_subscriptions():
    @task(task_id="append_raw_subscription_tables")
    def append_raw_subscription_tables(**context) -> dict:
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

        source = PostgresHook(postgres_conn_id="postgres_subscriptions").get_conn()
        target = SnowflakeHook(snowflake_conn_id="enterprise_dw").get_conn()
        try:
            result = run(source, target,
                         window_start=context["data_interval_start"],
                         window_end=context["data_interval_end"],
                         batch_id=context["run_id"], paramstyle="pyformat")
            if not result.reconciled:
                raise RuntimeError(
                    f"extracted {result.rows_extracted} but loaded {result.rows_loaded}")
            target.commit()
        except Exception:
            target.rollback()
            raise
        finally:
            source.close()
            target.close()

        # Counts only: BILLING_EMAIL is pii_level 3 and XCom is readable from the UI.
        return {"batch_id": result.batch_id,
                "subscriptions": result.rows_into("RAW_SUBSCRIPTIONS"),
                "events": result.rows_into("RAW_SUBSCRIPTION_EVENTS")}

    append_raw_subscription_tables()


dag_ingest_postgres_subscriptions()
