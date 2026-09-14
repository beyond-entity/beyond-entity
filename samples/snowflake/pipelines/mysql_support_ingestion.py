"""MySQL Support Ingestion -- Beyond Entity proc_a9NaJ21I2p.

The tightest schedule in the platform at every 30 minutes, because support health
is monitored intraday.

Tickets are windowed on `created_at` **OR** `resolved_at`. Windowing on creation
alone would mean a ticket resolved in any later window was never re-extracted, so
its RESOLVED_AT would stay null in RAW forever and
CUSTOMER_SUPPORT_HEALTH.AVG_RESOLUTION_TIME would be computed from nulls. The
consequence is that a ticket lands twice in its life; Build Core Support
Interaction dedups to the latest landing.

`support_interactions.note_text` is deliberately not ingested. That free-text PII
exclusion is enforced by the statement's column list, so do not widen it.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pipelines import db_ingestion
from pipelines.db_ingestion import IngestionResult

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "ingestion" / "mysql_support"

PROCESSOR_ID = "proc_a9NaJ21I2p"
INGESTION_JOB_ID = "dag_ingest_mysql_support"

TICKETS_TRANSFORMATION_ID = "trans_Tg8Y7ew2EN"
INTERACTIONS_TRANSFORMATION_ID = "trans_DETbiMgTqj"

DEFAULT_FETCH_SIZE = db_ingestion.DEFAULT_FETCH_SIZE


def run(source_conn, target_conn, *, window_start: datetime, window_end: datetime,
        batch_id: str, paramstyle: str = "qmark",
        fetch_size: int = DEFAULT_FETCH_SIZE) -> IngestionResult:
    return db_ingestion.run(
        source_conn, target_conn,
        sql_dir=SQL_DIR,
        ingestion_job_id=INGESTION_JOB_ID,
        window_start=window_start, window_end=window_end, batch_id=batch_id,
        paramstyle=paramstyle, fetch_size=fetch_size,
    )
