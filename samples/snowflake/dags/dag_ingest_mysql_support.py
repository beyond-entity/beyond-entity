"""Airflow DAG for Beyond Entity proc_a9NaJ21I2p "MySQL Support Ingestion".

Every 30 minutes -- the tightest schedule in the platform, because support health
is monitored intraday.

Tickets are windowed on created_at OR resolved_at, so a ticket lands twice in its
life and Build Core Support Interaction dedups to the latest landing. Do not
"optimise" the window down to created_at: that is the defect that would leave
RESOLVED_AT permanently null and AVG_RESOLUTION_TIME computed from nulls.
"""

from __future__ import annotations

import pendulum
from airflow.decorators import dag, task

from pipelines.mysql_support_ingestion import INGESTION_JOB_ID, run

SCHEDULE = "*/30 * * * *"  # proc_a9NaJ21I2p other_info.schedule


@dag(
    dag_id=INGESTION_JOB_ID,
    schedule=SCHEDULE,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["ingestion", "mysql", "raw", "pii"],
    doc_md=__doc__,
)
def dag_ingest_mysql_support():
    @task(task_id="append_raw_support_tables")
    def append_raw_support_tables(**context) -> dict:
        from airflow.providers.mysql.hooks.mysql import MySqlHook
        from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

        source = MySqlHook(mysql_conn_id="mysql_support").get_conn()
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

        # Counts only: CONTACT_EMAIL is pii_level 3 and XCom is readable from the UI.
        return {"batch_id": result.batch_id,
                "tickets": result.rows_into("RAW_SUPPORT_TICKETS"),
                "interactions": result.rows_into("RAW_SUPPORT_INTERACTIONS")}

    append_raw_support_tables()


dag_ingest_mysql_support()
