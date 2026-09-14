"""Airflow DAG for Beyond Entity proc_a5OA9FY6dc "Partner File Ingestion".

The DAG id is the processor's modeled `module_name` and the schedule is its modeled
`other_info.schedule` -- both belong to the architecture, so change them in Beyond
Entity first.

Snowflake reads the landing zone stage itself, so there is no extract step and one
connection is involved. Airflow schedules it; it does not move the data.

One task, not three. The three files are loaded in one transaction because the
partner customer mapping is the fourth identifier space feeding CORE identity
resolution and the campaign file is what its FIRST_TOUCH_CAMPAIGN_ID points at:
landing one without the other would publish a day where attribution silently
resolves to nothing.

The XCom payload carries counts and file names only. The mapping file transports
unmasked partner PII and XCom is readable from the Airflow UI.
"""

from __future__ import annotations

import pendulum
from airflow.decorators import dag, task

from pipelines.partner_file_ingestion import INGESTION_JOB_ID, ingest, landing_files

SCHEDULE = "0 3 * * *"  # proc_a5OA9FY6dc other_info.schedule


@dag(
    dag_id=INGESTION_JOB_ID,
    schedule=SCHEDULE,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,  # deliveries must not interleave against append-only targets
    tags=["ingestion", "partner", "landing-zone", "raw", "pii"],
    doc_md=__doc__,
)
def dag_ingest_partner_files():
    @task(task_id="append_raw_partner_tables")
    def append_raw_partner_tables(**context) -> dict:
        from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

        target = SnowflakeHook(snowflake_conn_id="enterprise_dw").get_conn()
        files = landing_files(context["data_interval_start"])
        # Set by a manual trigger for a single-partner reload; None loads the whole day.
        partner_id_filter = (context["dag_run"].conf or {}).get("partner_id_filter")

        try:
            result = ingest(target, batch_id=context["run_id"],
                            campaign_source_file=files["campaign"],
                            customer_map_source_file=files["customer_map"],
                            cost_source_file=files["cost"],
                            partner_id_filter=partner_id_filter)
            target.commit()
        except Exception:
            target.rollback()
            raise
        finally:
            target.close()

        return {
            "batch_id": context["run_id"],
            "partner_id_filter": partner_id_filter,
            "source_files": files,
            "rows_landed": {t: result.target_rows.get(t, 0)
                            for t in ("RAW_CAMPAIGN_DATA", "RAW_PARTNER_CUSTOMER_MAP",
                                      "RAW_PARTNER_ACQUISITION_COST")},
        }

    append_raw_partner_tables()


dag_ingest_partner_files()
