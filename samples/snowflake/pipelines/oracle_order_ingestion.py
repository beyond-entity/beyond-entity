"""Oracle Order Ingestion -- Beyond Entity proc_U9h1dVHj2j.

Hourly incremental append of Oracle orders, order lines and payments into the RAW
layer. One processor, three target tables, three modeled statements executed in
processing order against the same window and the same batch.

Two windowing decisions are the architecture's, not this module's:

* **Order items are windowed through their parent order.** ORDER_ITEMS carries no
  timestamp, so the modeled statement joins ORDERS and takes the window from there.
  A run therefore lands exactly the line items belonging to the orders it landed,
  keeping the two tables consistent within a batch. `contract.py` carries that join
  through verbatim -- rebuilding the FROM clause would drop it and leave the WHERE
  referencing an alias that no longer exists.

* **Payments are windowed on PAID_AT**, their own settlement time, not the order's
  update time. A payment can settle days after the order it pays.

`CARD_LAST_FOUR` is deliberately absent from the payments statement. The PII
exclusion is enforced by that column list, so do not widen it.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pipelines import db_ingestion
from pipelines.db_ingestion import IngestionResult

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "ingestion" / "oracle_orders"

PROCESSOR_ID = "proc_U9h1dVHj2j"
INGESTION_JOB_ID = "dag_ingest_oracle_orders"

ORDERS_TRANSFORMATION_ID = "trans_W0R9eiHhld"
ORDER_ITEMS_TRANSFORMATION_ID = "trans_6p4HVsjvDB"
PAYMENTS_TRANSFORMATION_ID = "trans_XR5OUYHu6Q"

DEFAULT_FETCH_SIZE = db_ingestion.DEFAULT_FETCH_SIZE


def load_contracts():
    """The three modeled statements, parsed, in processing order."""
    return db_ingestion.load_contracts(SQL_DIR)


def run(source_conn, target_conn, *, window_start: datetime, window_end: datetime,
        batch_id: str, paramstyle: str = "qmark",
        fetch_size: int = DEFAULT_FETCH_SIZE) -> IngestionResult:
    """Land one hourly window of orders, order items and payments.

    All three statements share one `_INGESTED_AT`, so a batch is identifiable by its
    load time across the three tables, and one `_BATCH_ID` so a run is replayable as
    a unit.
    """
    return db_ingestion.run(
        source_conn, target_conn,
        sql_dir=SQL_DIR,
        ingestion_job_id=INGESTION_JOB_ID,
        window_start=window_start, window_end=window_end, batch_id=batch_id,
        paramstyle=paramstyle, fetch_size=fetch_size,
    )
