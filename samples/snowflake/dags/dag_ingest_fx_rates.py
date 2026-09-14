"""Airflow DAG for Beyond Entity proc_PzWyOakCVL "FX Rate File Ingestion".

The DAG id is the processor's modeled `module_name` and the schedule is its modeled
`other_info.schedule` -- both belong to the architecture, so change them in Beyond
Entity first.

This ingestion differs from the database-sourced ones in an important way: the file
is read from an external stage by Snowflake itself, so there is no extract step and
only one connection is involved. Airflow schedules it; it does not move the data.

It runs at 02:45, ahead of every CORE build, because FX_RATE_DAILY is the reference
data every currency normalization reads. If this job has not run, revenue figures
are stale or absent rather than silently wrong -- which is the failure mode we want.
"""

from __future__ import annotations

import pendulum
from airflow.decorators import dag, task

from pipelines.fx_rate import INGESTION_JOB_ID, ingest

SCHEDULE = "45 2 * * *"  # proc_PzWyOakCVL other_info.schedule


@dag(
    dag_id=INGESTION_JOB_ID,
    schedule=SCHEDULE,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,  # deliveries must not interleave against an append-only target
    tags=["ingestion", "fx", "raw", "reference-data"],
    doc_md=__doc__,
)
def dag_ingest_fx_rates():
    @task(task_id="append_raw_fx_rates")
    def append_raw_fx_rates(**context) -> dict:
        from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

        target = SnowflakeHook(snowflake_conn_id="enterprise_dw").get_conn()
        source_file = context["data_interval_start"].format("[fx/fx_rates_]YYYYMMDD[.csv]")

        try:
            result = ingest(target, batch_id=context["run_id"],
                            source_file=source_file)
            target.commit()
        except Exception:
            target.rollback()
            raise
        finally:
            target.close()

        return {
            "batch_id": context["run_id"],
            "source_file": source_file,
            "rows_landed": result.target_rows.get("RAW_FX_RATES", 0),
        }

    append_raw_fx_rates()


dag_ingest_fx_rates()
