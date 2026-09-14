"""Oracle Customer Ingestion -- Beyond Entity proc_4osn63QZFi.

Six-hourly incremental append of Oracle SALES.CUSTOMERS into RAW_CUSTOMERS.

Two properties of the architecture drive the shape of this pipeline:

* **RAW is append-only.** Each run appends the source rows whose UPDATED_AT falls
  in the window; it never updates or deletes. RAW_CUSTOMERS therefore holds one row
  per source *version* of a customer. Collapsing those to the current version is
  CORE's job and deliberately not this one's -- doing it here would destroy the
  history that _BATCH_ID exists to make replayable.

* **This job carries unmasked PII** across a system boundary. CUSTOMER_NAME, EMAIL,
  PHONE_NUMBER and BILLING_ADDRESS are pii_level 3, which is why RAW is
  access-restricted and why nothing here logs or returns a row value.

The extract/load mechanics live in `db_ingestion`, shared with the other
database-sourced ingestions.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pipelines import contract, db_ingestion
from pipelines.db_ingestion import IngestionResult

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "ingestion" / "oracle_customers"

PROCESSOR_ID = "proc_4osn63QZFi"
TRANSFORMATION_ID = "trans_4THOjFhbA6"
INGESTION_JOB_ID = "dag_ingest_oracle_customers"

DEFAULT_FETCH_SIZE = db_ingestion.DEFAULT_FETCH_SIZE


def load_contract() -> contract.LoadContract:
    """The modeled statement, parsed into its extract and load halves."""
    return db_ingestion.load_contracts(SQL_DIR)[0][1]


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
