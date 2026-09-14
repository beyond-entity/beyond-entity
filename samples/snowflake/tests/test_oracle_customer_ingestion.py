"""Validation for Beyond Entity proc_4osn63QZFi, against SQLite fixtures.

Standard library only; no Oracle or Snowflake resources are contacted. The point
is to check that the pipeline honors the modeled contract -- column set, window
semantics, append-only behavior, ingestion metadata -- not to simulate either
vendor's engine.
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines import contract  # noqa: E402
from pipelines.oracle_customer_ingestion import (  # noqa: E402
    INGESTION_JOB_ID,
    load_contract,
    run,
)

# The modeled RAW_CUSTOMERS contract (ent_K0JacNbYrd), in order.
MODELED_COLUMNS = (
    "CUSTOMER_ID", "CUSTOMER_NAME", "EMAIL", "PHONE_NUMBER", "BILLING_ADDRESS",
    "COUNTRY_CODE", "CUSTOMER_STATUS", "CREATED_AT", "UPDATED_AT",
    "_SOURCE_SYSTEM", "_INGESTED_AT", "_INGESTION_JOB_ID", "_BATCH_ID",
)
NOT_NULL_COLUMNS = ("CUSTOMER_ID", "_SOURCE_SYSTEM", "_INGESTED_AT", "_INGESTION_JOB_ID")
PII_COLUMNS = ("CUSTOMER_NAME", "EMAIL", "PHONE_NUMBER", "BILLING_ADDRESS")

T0 = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)


def _oracle() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE CUSTOMERS (
               CUSTOMER_ID INTEGER NOT NULL, CUSTOMER_NAME TEXT, EMAIL TEXT,
               PHONE_NUMBER TEXT, BILLING_ADDRESS TEXT, COUNTRY_CODE TEXT,
               CUSTOMER_STATUS TEXT, CREATED_AT TIMESTAMP, UPDATED_AT TIMESTAMP)"""
    )
    return conn


def _warehouse() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE RAW_CUSTOMERS (
               CUSTOMER_ID NUMERIC(18) NOT NULL, CUSTOMER_NAME VARCHAR(200),
               EMAIL VARCHAR(320), PHONE_NUMBER VARCHAR(50),
               BILLING_ADDRESS VARCHAR(500), COUNTRY_CODE VARCHAR(2),
               CUSTOMER_STATUS VARCHAR(20), CREATED_AT TIMESTAMP,
               UPDATED_AT TIMESTAMP, _SOURCE_SYSTEM VARCHAR(30) NOT NULL,
               _INGESTED_AT TIMESTAMP NOT NULL, _INGESTION_JOB_ID VARCHAR(60) NOT NULL,
               _BATCH_ID VARCHAR(60))"""
    )
    return conn


def _customer(cid: int, updated: datetime, *, status: str = "ACTIVE",
              name: str | None = None) -> tuple:
    return (
        cid, name or f"Customer {cid}", f"c{cid}@example.com", f"+1-555-{cid:04d}",
        f"{cid} Example Street", "US", status, T0 - timedelta(days=30), updated,
    )


class ContractTests(unittest.TestCase):
    """The parsed statement must match the modeled entity, column for column."""

    def setUp(self):
        self.contract = load_contract()

    def test_target_columns_match_the_model(self):
        self.assertEqual(self.contract.target_columns, MODELED_COLUMNS)

    def test_every_not_null_column_has_a_producer(self):
        produced = {c.name for c in self.contract.columns}
        for column in NOT_NULL_COLUMNS:
            self.assertIn(column, produced)

    def test_ingestion_metadata_is_not_extracted_from_the_source(self):
        kinds = {c.name: c.kind for c in self.contract.columns}
        self.assertEqual(kinds["_SOURCE_SYSTEM"], "literal")
        self.assertEqual(kinds["_INGESTED_AT"], "load_timestamp")
        self.assertEqual(kinds["_INGESTION_JOB_ID"], "parameter")
        self.assertEqual(kinds["_BATCH_ID"], "parameter")

    def test_extract_pulls_only_source_columns(self):
        self.assertNotIn("_SOURCE_SYSTEM", self.contract.extract_sql())
        self.assertEqual(len(self.contract.source_columns), 9)

    def test_window_is_half_open(self):
        self.assertIn(">= :window_start", self.contract.where_clause)
        self.assertIn("< :window_end", self.contract.where_clause)

    def test_malformed_sql_is_rejected_rather_than_guessed(self):
        with self.assertRaises(contract.ContractError):
            contract.parse("INSERT INTO T (A) SELECT UPPER(c.A) FROM S c")


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.source = _oracle()
        self.target = _warehouse()

    def tearDown(self):
        self.source.close()
        self.target.close()

    def _seed(self, rows):
        self.source.executemany(
            "INSERT INTO CUSTOMERS VALUES (?,?,?,?,?,?,?,?,?)", rows
        )

    def _run(self, start, end, batch_id):
        return run(self.source, self.target,
                   window_start=start, window_end=end, batch_id=batch_id)

    def _raw(self, columns="*"):
        return self.target.execute(f"SELECT {columns} FROM RAW_CUSTOMERS").fetchall()

    def test_loads_the_window_and_reconciles(self):
        self._seed([_customer(1, T0 + timedelta(hours=1)),
                    _customer(2, T0 + timedelta(hours=5))])
        result = self._run(T0, T0 + timedelta(hours=6), "run_a")
        self.assertEqual(result.rows_loaded, 2)
        self.assertTrue(result.reconciled)
        self.assertEqual(len(self._raw()), 2)

    def test_window_boundaries_neither_duplicate_nor_drop(self):
        boundary = T0 + timedelta(hours=6)
        self._seed([_customer(1, T0), _customer(2, boundary)])
        first = self._run(T0, boundary, "run_a")
        second = self._run(boundary, boundary + timedelta(hours=6), "run_b")
        self.assertEqual((first.rows_loaded, second.rows_loaded), (1, 1))
        loaded = sorted(row[0] for row in self._raw("CUSTOMER_ID"))
        self.assertEqual(loaded, [1, 2])

    def test_rows_outside_the_window_are_not_loaded(self):
        self._seed([_customer(1, T0 - timedelta(hours=1)),
                    _customer(2, T0 + timedelta(hours=7))])
        result = self._run(T0, T0 + timedelta(hours=6), "run_a")
        self.assertEqual(result.rows_loaded, 0)

    def test_append_only_keeps_every_source_version(self):
        """A changed customer produces a second row; RAW never updates in place."""
        self._seed([_customer(1, T0 + timedelta(hours=1), status="ACTIVE")])
        self._run(T0, T0 + timedelta(hours=6), "run_a")

        self.source.execute(
            "UPDATE CUSTOMERS SET CUSTOMER_STATUS='DORMANT', UPDATED_AT=? "
            "WHERE CUSTOMER_ID=1", (T0 + timedelta(hours=7),)
        )
        self._run(T0 + timedelta(hours=6), T0 + timedelta(hours=12), "run_b")

        versions = self._raw("CUSTOMER_ID, CUSTOMER_STATUS, _BATCH_ID")
        self.assertEqual(len(versions), 2)
        self.assertEqual(
            sorted((row[1], row[2]) for row in versions),
            [("ACTIVE", "run_a"), ("DORMANT", "run_b")],
        )

    def test_ingestion_metadata_is_stamped_on_every_row(self):
        self._seed([_customer(1, T0 + timedelta(hours=1)),
                    _customer(2, T0 + timedelta(hours=2))])
        self._run(T0, T0 + timedelta(hours=6), "run_a")
        for source_system, job_id, batch_id, ingested_at in self._raw(
            "_SOURCE_SYSTEM, _INGESTION_JOB_ID, _BATCH_ID, _INGESTED_AT"
        ):
            self.assertEqual(source_system, "ORACLE_SALES")
            self.assertEqual(job_id, INGESTION_JOB_ID)
            self.assertEqual(batch_id, "run_a")
            self.assertIsNotNone(ingested_at)

    def test_ingested_at_is_one_utc_load_time_per_run(self):
        self._seed([_customer(i, T0 + timedelta(hours=1)) for i in range(1, 4)])
        result = self._run(T0, T0 + timedelta(hours=6), "run_a")
        stamps = {row[0] for row in self._raw("_INGESTED_AT")}
        self.assertEqual(len(stamps), 1, "one load timestamp per run, not per row")
        self.assertEqual(result.ingested_at.tzinfo, timezone.utc)

    def test_pii_columns_cross_the_boundary_unmasked(self):
        """RAW is the restricted zone: masking happens later, not here."""
        self._seed([_customer(1, T0 + timedelta(hours=1), name="Ada Lovelace")])
        self._run(T0, T0 + timedelta(hours=6), "run_a")
        name, email = self._raw("CUSTOMER_NAME, EMAIL")[0]
        self.assertEqual(name, "Ada Lovelace")
        self.assertEqual(email, "c1@example.com")

    def test_result_carries_no_row_data(self):
        self._seed([_customer(1, T0 + timedelta(hours=1), name="Ada Lovelace")])
        result = self._run(T0, T0 + timedelta(hours=6), "run_a")
        self.assertNotIn("Ada Lovelace", repr(result))
        for column in PII_COLUMNS:
            self.assertNotIn(column.lower(), repr(result).lower())

    def test_empty_window_is_not_an_error(self):
        result = self._run(T0, T0 + timedelta(hours=6), "run_a")
        self.assertEqual(result.rows_loaded, 0)
        self.assertTrue(result.reconciled)

    def test_inverted_window_is_rejected(self):
        with self.assertRaises(ValueError):
            self._run(T0 + timedelta(hours=6), T0, "run_a")

    def test_large_window_spans_multiple_fetch_batches(self):
        self._seed([_customer(i, T0 + timedelta(minutes=1)) for i in range(1, 26)])
        result = run(self.source, self.target, window_start=T0,
                     window_end=T0 + timedelta(hours=6), batch_id="run_a",
                     fetch_size=10)
        self.assertEqual(result.rows_loaded, 25)
        self.assertEqual(len(self._raw()), 25)


if __name__ == "__main__":
    unittest.main(verbosity=2)
