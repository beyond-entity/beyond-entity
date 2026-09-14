"""FX rates -- Beyond Entity proc_PzWyOakCVL and proc_AsyyNwdM2X.

FX_RATE_DAILY is the reference table every currency normalization in the platform
reads, so this pipeline gates Build Core Order, Build Core Payment, Build Core
Subscription and every revenue mart.

Both halves execute **inside Snowflake**. The ingestion reads the landing zone
stage directly, so unlike the database-sourced ingestions it needs no extract/load
split -- the modeled statement runs verbatim.

The two halves differ in one way that matters: ingestion **appends** to RAW, the
CORE build **rebuilds**. Truncating RAW would destroy the delivery history that
makes a corrected rate file traceable.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

_ROOT = Path(__file__).resolve().parent.parent
INGESTION_SQL_DIR = _ROOT / "sql" / "ingestion" / "fx"
CORE_SQL_DIR = _ROOT / "sql" / "core" / "fx"

INGESTION_PROCESSOR_ID = "proc_PzWyOakCVL"
CORE_PROCESSOR_ID = "proc_AsyyNwdM2X"
INGESTION_JOB_ID = "dag_ingest_fx_rates"


def ingest(conn, *, batch_id: str, source_file: str, storage_uri: str | None = None,
           dialect: str = "snowflake") -> BuildResult:
    """Append one delivered rate file into RAW_FX_RATES.

    Append-only on purpose: a corrected file redelivers the same rate dates, and
    both deliveries must stay visible so the correction is traceable. The CORE
    build is what picks the latest.

    Also writes the landing_file_manifest row, which is the producer of
    rejected_row_count. The loaded and rejected counts are the two sides of the
    ingestion WHERE clause, so the manifest reports the two-tier rejection rule's
    own rejections rather than leaving the column permanently zero.
    """
    return sql_runner.run(
        conn,
        sql_dir=INGESTION_SQL_DIR,
        parameters={"ingestion_job_id": INGESTION_JOB_ID,
                    "batch_id": batch_id,
                    "source_file": source_file,
                    "storage_uri": storage_uri or source_file},
        dialect=dialect,
        rebuild=False,
    )


def build_core(conn, *, dialect: str = "snowflake") -> BuildResult:
    """Rebuild FX_RATE_DAILY from the landed rates."""
    return sql_runner.run(conn, sql_dir=CORE_SQL_DIR, parameters={},
                          dialect=dialect, rebuild=True)
