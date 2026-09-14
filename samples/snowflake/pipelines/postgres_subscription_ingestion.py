"""PostgreSQL Subscription Ingestion -- Beyond Entity proc_EMd95vDcg4.

Hourly append of subscriptions and subscription events into RAW. The two
statements use **different progress mechanisms**, and that is the architecture's
decision rather than an inconsistency:

* **Subscriptions** are mutable rows, windowed on `updated_at` from the
  orchestrator's data interval like every other database ingestion.
* **Subscription events** are an immutable append-only stream with a monotonic
  `event_id`, windowed on an id high-water mark. An id mark cannot miss a
  late-written event the way a time window can.

The high-water mark is read from the TARGET -- `MAX(EVENT_ID)` on
RAW_SUBSCRIPTION_EVENTS -- immediately before extracting. It is deliberately not a
watermark table: deriving progress from data already landed keeps exactly one copy
of the state, so there is nothing that can disagree with the table itself.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from pipelines import db_ingestion
from pipelines.db_ingestion import IngestionResult

logger = logging.getLogger(__name__)

SQL_DIR = (Path(__file__).resolve().parent.parent
           / "sql" / "ingestion" / "postgres_subscriptions")

PROCESSOR_ID = "proc_EMd95vDcg4"
INGESTION_JOB_ID = "dag_ingest_postgres_subscriptions"

SUBSCRIPTIONS_TRANSFORMATION_ID = "trans_IkCCZ85WpW"
EVENTS_TRANSFORMATION_ID = "trans_dqJ9ocHpzo"

DEFAULT_FETCH_SIZE = db_ingestion.DEFAULT_FETCH_SIZE


def last_event_id(target_conn) -> int:
    """The event high-water mark, read from the landed data itself."""
    row = target_conn.cursor().execute(
        "SELECT COALESCE(MAX(EVENT_ID), 0) FROM RAW_SUBSCRIPTION_EVENTS").fetchone()
    return int(row[0])


def run(source_conn, target_conn, *, window_start: datetime, window_end: datetime,
        batch_id: str, paramstyle: str = "qmark",
        fetch_size: int = DEFAULT_FETCH_SIZE) -> IngestionResult:
    mark = last_event_id(target_conn)
    logger.info("%s: event high-water mark is %d", INGESTION_JOB_ID, mark)
    return db_ingestion.run(
        source_conn, target_conn,
        sql_dir=SQL_DIR,
        ingestion_job_id=INGESTION_JOB_ID,
        window_start=window_start, window_end=window_end, batch_id=batch_id,
        extra_parameters={"last_event_id": mark},
        paramstyle=paramstyle, fetch_size=fetch_size,
    )
