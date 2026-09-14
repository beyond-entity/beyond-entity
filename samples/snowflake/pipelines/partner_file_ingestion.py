"""Partner file ingestion -- Beyond Entity proc_a5OA9FY6dc.

Three landing objects, three RAW tables, one run. Like the FX ingestion this
executes entirely inside Snowflake -- the files are read from an external stage --
so the modeled statements run verbatim and no extract/load split is needed.

D18. The processor originally declared a single `source_file` run parameter, which
all three loads would have bound. That would stamp three different landing objects
with the same `_SOURCE_FILE`, and `_SOURCE_FILE` exists precisely so a landed row
can be joined back to its own `landing_file_manifest` entry. Each file now binds
its own source file and storage URI, and writes its own manifest row.

Append-only: `rebuild=False`. Truncating RAW would destroy the delivery history
that makes a corrected partner file traceable.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = _ROOT / "sql" / "ingestion" / "partner"

PROCESSOR_ID = "proc_a5OA9FY6dc"
INGESTION_JOB_ID = "dag_ingest_partner_files"

TARGET_TABLES = ("RAW_CAMPAIGN_DATA", "RAW_PARTNER_CUSTOMER_MAP",
                 "RAW_PARTNER_ACQUISITION_COST")


def landing_files(load_date) -> dict[str, str]:
    """The three landing objects for one daily drop.

    The path patterns are modeled on the landing zone entities (ent_xJRehU39lS,
    ent_OQHbvJ5s88, ent_NmN647zEgK); keep them in step with Beyond Entity rather
    than editing them here.
    """
    stamp = load_date.strftime("%Y%m%d") if hasattr(load_date, "strftime") else str(load_date)
    return {
        "campaign": f"campaign/partner_campaign_{stamp}.csv",
        "customer_map": f"mapping/partner_customer_map_{stamp}.parquet",
        "cost": f"cost/partner_acquisition_cost_{stamp}.parquet",
    }


def ingest(conn, *, batch_id: str, campaign_source_file: str,
           customer_map_source_file: str, cost_source_file: str,
           storage_root: str = "s3://enterprise-landing/",
           partner_id_filter: str | None = None,
           dialect: str = "snowflake") -> BuildResult:
    """Append one daily partner drop into the three RAW tables.

    `partner_id_filter` is the modeled single-partner reload: None loads the whole
    day. It is applied to the loads *and* to the manifest counts, and the scope is
    recorded in `landing_file_manifest.partner_id`, so a deliberately narrow reload
    cannot be misread as a collapse in delivered volume.
    """
    parameters = {
        "ingestion_job_id": INGESTION_JOB_ID,
        "batch_id": batch_id,
        "partner_id_filter": partner_id_filter,
        "campaign_source_file": campaign_source_file,
        "campaign_storage_uri": storage_root + campaign_source_file,
        "customer_map_source_file": customer_map_source_file,
        "customer_map_storage_uri": storage_root + customer_map_source_file,
        "cost_source_file": cost_source_file,
        "cost_storage_uri": storage_root + cost_source_file,
    }
    return sql_runner.run(conn, sql_dir=SQL_DIR, parameters=parameters,
                          dialect=dialect, rebuild=False)
