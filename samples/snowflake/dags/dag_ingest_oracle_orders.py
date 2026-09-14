"""Airflow DAG for Beyond Entity proc_U9h1dVHj2j "Oracle Order Ingestion".

The DAG id is the processor's modeled `module_name` and the schedule its modeled
`other_info.schedule`. Both belong to the architecture -- change them in Beyond
Entity first.

One task, not three. The three statements land orders, their line items and their
payments for the same window, and order items are windowed *through* their parent
order, so splitting them into separate tasks would let a retry land line items for
orders a previous attempt never landed. They share one `_INGESTED_AT` and one
`_BATCH_ID` so the run is identifiable and replayable as a unit.

This job carries pii_level 3 columns across a system boundary, so the XCom payload
is counts and identifiers only -- XCom is readable from the Airflow UI.
"""

from __future__ import annotations

import pendulum
from airflow.decorators import dag, task

from pipelines.oracle_order_ingestion import INGESTION_JOB_ID, run

SCHEDULE = "0 * * * *"  # proc_U9h1dVHj2j other_info.schedule


@dag(
    dag_id=INGESTION_JOB_ID,
    schedule=SCHEDULE,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,  # windows must not interleave against an append-only target
    tags=["ingestion", "oracle", "raw", "revenue"],
    doc_md=__doc__,
)
def dag_ingest_oracle_orders():
    @task(task_id="append_raw_order_tables")
    def append_raw_order_tables(**context) -> dict:
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

        return {
            "batch_id": result.batch_id,
            "rows_loaded": result.rows_loaded,
            "orders": result.rows_into("RAW_ORDERS"),
            "order_items": result.rows_into("RAW_ORDER_ITEMS"),
            "payments": result.rows_into("RAW_PAYMENTS"),
            "window_start": result.window_start.isoformat(),
            "window_end": result.window_end.isoformat(),
        }

    append_raw_order_tables()


dag_ingest_oracle_orders()
