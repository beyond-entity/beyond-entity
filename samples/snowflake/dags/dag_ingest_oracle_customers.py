"""Airflow DAG for Beyond Entity proc_4osn63QZFi "Oracle Customer Ingestion".

The DAG id is the processor's modeled `module_name`, and the schedule is its
modeled `other_info.schedule` -- both are the architecture's, not this file's, so
change them in Beyond Entity first.

The modeled transformation takes :window_start and :window_end as INPUT ports.
Airflow's data interval supplies them directly, which is why this pipeline needs
no watermark table: the orchestrator already owns run-window state, and a second
copy of it in the warehouse could disagree with the first. Re-running a cleared
task replays exactly its own window.
"""

from __future__ import annotations

import pendulum
from airflow.decorators import dag, task

from pipelines.oracle_customer_ingestion import INGESTION_JOB_ID, run

SCHEDULE = "0 */6 * * *"  # proc_4osn63QZFi other_info.schedule


@dag(
    dag_id=INGESTION_JOB_ID,
    schedule=SCHEDULE,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,  # windows must not interleave against an append-only target
    tags=["ingestion", "oracle", "raw", "pii"],
    doc_md=__doc__,
)
def dag_ingest_oracle_customers():
    @task(task_id="append_raw_customers")
    def append_raw_customers(**context) -> dict:
        from airflow.providers.common.sql.hooks.handlers import fetch_all_handler  # noqa: F401
        from airflow.providers.oracle.hooks.oracle import OracleHook
        from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

        source = OracleHook(oracle_conn_id="oracle_sales").get_conn()
        target = SnowflakeHook(snowflake_conn_id="enterprise_dw").get_conn()

        try:
            result = run(
                source,
                target,
                window_start=context["data_interval_start"],
                window_end=context["data_interval_end"],
                batch_id=context["run_id"],
                paramstyle="pyformat",
            )
            if not result.reconciled:
                raise RuntimeError(
                    f"extracted {result.rows_extracted} but loaded {result.rows_loaded}"
                )
            target.commit()
        except Exception:
            target.rollback()
            raise
        finally:
            source.close()
            target.close()

        # Counts only -- this job carries pii_level 3 columns and must not leak
        # row values into XCom, which is readable from the Airflow UI.
        return {
            "batch_id": result.batch_id,
            "rows_loaded": result.rows_loaded,
            "window_start": result.window_start.isoformat(),
            "window_end": result.window_end.isoformat(),
        }

    append_raw_customers()


dag_ingest_oracle_customers()
