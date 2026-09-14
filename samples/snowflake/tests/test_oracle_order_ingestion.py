"""Validation for Beyond Entity proc_U9h1dVHj2j "Oracle Order Ingestion".

One processor, three RAW tables, three windowing rules. The interesting one is
order items: ORDER_ITEMS has no timestamp, so the modeled statement windows it
through a join to its parent order. That join is why `contract.py` carries the
FROM clause through verbatim instead of rebuilding it.
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.oracle_order_ingestion import (  # noqa: E402
    INGESTION_JOB_ID,
    ORDERS_TRANSFORMATION_ID,
    ORDER_ITEMS_TRANSFORMATION_ID,
    PAYMENTS_TRANSFORMATION_ID,
    load_contracts,
    run,
)

T0 = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)
HOUR = timedelta(hours=1)

MODELED = {
    "RAW_ORDERS": ("ORDER_ID", "CUSTOMER_ID", "ORDER_STATUS", "ORDER_DATE", "CURRENCY_CODE",
                   "TOTAL_AMOUNT", "CHANNEL_CODE", "UPDATED_AT", "_SOURCE_SYSTEM",
                   "_INGESTED_AT", "_INGESTION_JOB_ID", "_BATCH_ID"),
    "RAW_ORDER_ITEMS": ("ORDER_ITEM_ID", "ORDER_ID", "PRODUCT_CODE", "QUANTITY", "UNIT_PRICE",
                        "LINE_AMOUNT", "CURRENCY_CODE", "_SOURCE_SYSTEM", "_INGESTED_AT",
                        "_INGESTION_JOB_ID", "_BATCH_ID"),
    "RAW_PAYMENTS": ("PAYMENT_ID", "ORDER_ID", "PAYMENT_METHOD", "PAYMENT_STATUS",
                     "PAYMENT_AMOUNT", "CURRENCY_CODE", "PAID_AT", "_SOURCE_SYSTEM",
                     "_INGESTED_AT", "_INGESTION_JOB_ID", "_BATCH_ID"),
}
NOT_NULL = {
    "RAW_ORDERS": ("ORDER_ID", "CUSTOMER_ID", "_SOURCE_SYSTEM", "_INGESTED_AT", "_INGESTION_JOB_ID"),
    "RAW_ORDER_ITEMS": ("ORDER_ITEM_ID", "ORDER_ID", "_SOURCE_SYSTEM", "_INGESTED_AT", "_INGESTION_JOB_ID"),
    "RAW_PAYMENTS": ("PAYMENT_ID", "ORDER_ID", "_SOURCE_SYSTEM", "_INGESTED_AT", "_INGESTION_JOB_ID"),
}


def _oracle() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE ORDERS (
            ORDER_ID INTEGER, CUSTOMER_ID INTEGER, ORDER_STATUS TEXT, ORDER_DATE TIMESTAMP,
            CURRENCY_CODE TEXT, TOTAL_AMOUNT NUMERIC, CHANNEL_CODE TEXT, UPDATED_AT TIMESTAMP);
        CREATE TABLE ORDER_ITEMS (
            ORDER_ITEM_ID INTEGER, ORDER_ID INTEGER, PRODUCT_CODE TEXT, QUANTITY INTEGER,
            UNIT_PRICE NUMERIC, LINE_AMOUNT NUMERIC, CURRENCY_CODE TEXT);
        CREATE TABLE PAYMENTS (
            PAYMENT_ID INTEGER, ORDER_ID INTEGER, PAYMENT_METHOD TEXT, PAYMENT_STATUS TEXT,
            PAYMENT_AMOUNT NUMERIC, CURRENCY_CODE TEXT, PAID_AT TIMESTAMP,
            CARD_LAST_FOUR TEXT);
        """
    )
    return conn


def _warehouse() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE RAW_ORDERS (
            ORDER_ID NUMERIC(18) NOT NULL, CUSTOMER_ID NUMERIC(18) NOT NULL,
            ORDER_STATUS VARCHAR(20), ORDER_DATE TIMESTAMP, CURRENCY_CODE VARCHAR(3),
            TOTAL_AMOUNT NUMERIC(18,2), CHANNEL_CODE VARCHAR(30), UPDATED_AT TIMESTAMP,
            _SOURCE_SYSTEM VARCHAR(30) NOT NULL, _INGESTED_AT TIMESTAMP NOT NULL,
            _INGESTION_JOB_ID VARCHAR(60) NOT NULL, _BATCH_ID VARCHAR(60));
        CREATE TABLE RAW_ORDER_ITEMS (
            ORDER_ITEM_ID NUMERIC(18) NOT NULL, ORDER_ID NUMERIC(18) NOT NULL,
            PRODUCT_CODE VARCHAR(50), QUANTITY NUMERIC(10), UNIT_PRICE NUMERIC(18,2),
            LINE_AMOUNT NUMERIC(18,2), CURRENCY_CODE VARCHAR(3),
            _SOURCE_SYSTEM VARCHAR(30) NOT NULL, _INGESTED_AT TIMESTAMP NOT NULL,
            _INGESTION_JOB_ID VARCHAR(60) NOT NULL, _BATCH_ID VARCHAR(60));
        CREATE TABLE RAW_PAYMENTS (
            PAYMENT_ID NUMERIC(18) NOT NULL, ORDER_ID NUMERIC(18) NOT NULL,
            PAYMENT_METHOD VARCHAR(30), PAYMENT_STATUS VARCHAR(20),
            PAYMENT_AMOUNT NUMERIC(18,2), CURRENCY_CODE VARCHAR(3), PAID_AT TIMESTAMP,
            _SOURCE_SYSTEM VARCHAR(30) NOT NULL, _INGESTED_AT TIMESTAMP NOT NULL,
            _INGESTION_JOB_ID VARCHAR(60) NOT NULL, _BATCH_ID VARCHAR(60));
        """
    )
    return conn


class ContractTests(unittest.TestCase):
    """The parsed statements must match the modeled entities, column for column."""

    def setUp(self):
        self.contracts = dict(load_contracts())

    def test_all_three_statements_are_present_in_order(self):
        self.assertEqual([tid for tid, _ in load_contracts()],
                         [ORDERS_TRANSFORMATION_ID, ORDER_ITEMS_TRANSFORMATION_ID,
                          PAYMENTS_TRANSFORMATION_ID])

    def test_target_columns_match_the_model(self):
        for tid, loaded in self.contracts.items():
            self.assertEqual(loaded.target_columns, MODELED[loaded.target_table], tid)

    def test_every_not_null_column_has_a_producer(self):
        for loaded in self.contracts.values():
            produced = {c.name for c in loaded.columns}
            for column in NOT_NULL[loaded.target_table]:
                self.assertIn(column, produced, loaded.target_table)

    def test_the_order_items_join_survives_parsing(self):
        """Rebuilding the FROM clause would drop it and orphan the WHERE's alias."""
        extract = self.contracts[ORDER_ITEMS_TRANSFORMATION_ID].extract_sql()
        self.assertIn("JOIN ORDERS o", extract)
        self.assertIn("o.UPDATED_AT", extract)

    def test_card_last_four_is_not_ingested(self):
        payments = self.contracts[PAYMENTS_TRANSFORMATION_ID]
        self.assertNotIn("CARD_LAST_FOUR", payments.extract_sql())
        self.assertNotIn("CARD_LAST_FOUR", payments.target_columns)


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.source, self.target = _oracle(), _warehouse()

    def tearDown(self):
        self.source.close()
        self.target.close()

    def order(self, order_id, *, updated=T0 + HOUR / 2, currency="EUR", amount=100.0,
              customer_id=7):
        self.source.execute("INSERT INTO ORDERS VALUES (?,?,?,?,?,?,?,?)",
                            (order_id, customer_id, "PAID", T0, currency, amount, "WEB", updated))

    def item(self, item_id, order_id, *, currency="EUR"):
        self.source.execute("INSERT INTO ORDER_ITEMS VALUES (?,?,?,?,?,?,?)",
                            (item_id, order_id, "SKU-1", 2, 50.0, 100.0, currency))

    def payment(self, payment_id, order_id, *, paid_at=T0 + HOUR / 2, currency="EUR"):
        self.source.execute("INSERT INTO PAYMENTS VALUES (?,?,?,?,?,?,?,?)",
                            (payment_id, order_id, "CARD", "CAPTURED", 100.0, currency,
                             paid_at, "4321"))

    def ingest(self, start=T0, end=T0 + HOUR, batch_id="run_a"):
        return run(self.source, self.target, window_start=start, window_end=end,
                   batch_id=batch_id)

    def raw(self, table, columns="*"):
        return self.target.execute(f"SELECT {columns} FROM {table}").fetchall()

    def test_one_run_lands_all_three_tables(self):
        self.order(1); self.item(10, 1); self.payment(100, 1)
        result = self.ingest()
        self.assertEqual(result.rows_into("RAW_ORDERS"), 1)
        self.assertEqual(result.rows_into("RAW_ORDER_ITEMS"), 1)
        self.assertEqual(result.rows_into("RAW_PAYMENTS"), 1)
        self.assertTrue(result.reconciled)

    def test_order_items_are_windowed_through_the_parent_order(self):
        """ORDER_ITEMS has no timestamp; its window comes from the order."""
        self.order(1, updated=T0 + HOUR / 2)          # in window
        self.order(2, updated=T0 + 5 * HOUR)          # out of window
        self.item(10, 1)
        self.item(20, 2)
        self.ingest()
        self.assertEqual([r[0] for r in self.raw("RAW_ORDER_ITEMS", "ORDER_ITEM_ID")], [10])

    def test_an_item_with_no_parent_order_is_not_landed(self):
        self.item(99, 404)
        self.ingest()
        self.assertEqual(self.raw("RAW_ORDER_ITEMS"), [])

    def test_payments_are_windowed_on_their_own_settlement_time(self):
        """A payment can settle long after the order it pays."""
        self.order(1, updated=T0 + HOUR / 2)
        self.payment(100, 1, paid_at=T0 + 5 * HOUR)   # settles outside this window
        first = self.ingest()
        self.assertEqual(first.rows_into("RAW_PAYMENTS"), 0)
        later = self.ingest(start=T0 + 5 * HOUR, end=T0 + 6 * HOUR, batch_id="run_b")
        self.assertEqual(later.rows_into("RAW_PAYMENTS"), 1)
        self.assertEqual(later.rows_into("RAW_ORDERS"), 0, "the order stays in its own window")

    def test_card_last_four_never_reaches_the_warehouse(self):
        self.order(1); self.payment(100, 1)
        self.ingest()
        landed = [str(v) for v in self.raw("RAW_PAYMENTS")[0]]
        self.assertNotIn("4321", landed)

    def test_all_three_tables_share_one_ingested_at_and_batch(self):
        """A batch must be identifiable across the three tables it wrote."""
        self.order(1); self.item(10, 1); self.payment(100, 1)
        self.ingest(batch_id="run_a")
        stamps, batches = set(), set()
        for table in ("RAW_ORDERS", "RAW_ORDER_ITEMS", "RAW_PAYMENTS"):
            for ingested, batch in self.raw(table, "_INGESTED_AT, _BATCH_ID"):
                stamps.add(ingested); batches.add(batch)
        self.assertEqual(len(stamps), 1)
        self.assertEqual(batches, {"run_a"})

    def test_ingestion_metadata_is_stamped(self):
        self.order(1)
        self.ingest()
        system, job = self.raw("RAW_ORDERS", "_SOURCE_SYSTEM, _INGESTION_JOB_ID")[0]
        self.assertEqual(system, "ORACLE_SALES")
        self.assertEqual(job, INGESTION_JOB_ID)

    def test_window_boundaries_neither_duplicate_nor_drop(self):
        boundary = T0 + HOUR
        self.order(1, updated=T0)
        self.order(2, updated=boundary)
        first = self.ingest(T0, boundary, "run_a")
        second = self.ingest(boundary, boundary + HOUR, "run_b")
        self.assertEqual((first.rows_into("RAW_ORDERS"), second.rows_into("RAW_ORDERS")), (1, 1))
        self.assertEqual(sorted(r[0] for r in self.raw("RAW_ORDERS", "ORDER_ID")), [1, 2])

    def test_append_only_keeps_every_source_version(self):
        self.order(1, updated=T0 + HOUR / 2, amount=100.0)
        self.ingest(batch_id="run_a")
        self.source.execute("UPDATE ORDERS SET TOTAL_AMOUNT=150.0, UPDATED_AT=? WHERE ORDER_ID=1",
                            (T0 + 2 * HOUR,))
        self.ingest(start=T0 + 2 * HOUR, end=T0 + 3 * HOUR, batch_id="run_b")
        versions = sorted(self.raw("RAW_ORDERS", "TOTAL_AMOUNT, _BATCH_ID"))
        self.assertEqual(versions, [(100.0, "run_a"), (150.0, "run_b")])

    def test_empty_window_is_not_an_error(self):
        result = self.ingest()
        self.assertEqual(result.rows_loaded, 0)
        self.assertTrue(result.reconciled)

    def test_inverted_window_is_rejected(self):
        with self.assertRaises(ValueError):
            self.ingest(start=T0 + HOUR, end=T0)

    def test_result_carries_no_row_data(self):
        self.order(1); self.payment(100, 1)
        result = self.ingest()
        self.assertNotIn("4321", repr(result))
        self.assertNotIn("SKU", repr(result))

    def test_rows_for_reports_each_statement_separately(self):
        self.order(1); self.item(10, 1); self.item(11, 1); self.payment(100, 1)
        result = self.ingest()
        self.assertEqual(result.rows_for(ORDERS_TRANSFORMATION_ID), 1)
        self.assertEqual(result.rows_for(ORDER_ITEMS_TRANSFORMATION_ID), 2)
        self.assertEqual(result.rows_for(PAYMENTS_TRANSFORMATION_ID), 1)

    def test_large_window_spans_multiple_fetch_batches(self):
        for n in range(1, 26):
            self.order(n)
        result = run(self.source, self.target, window_start=T0, window_end=T0 + HOUR,
                     batch_id="run_a", fetch_size=10)
        self.assertEqual(result.rows_into("RAW_ORDERS"), 25)


class EndToEndTests(unittest.TestCase):
    """Oracle -> RAW -> CORE, composed. The first test where the two halves meet.

    Everything before this has tested CORE against seeded RAW fixtures. Here RAW is
    populated by the real ingestion, so a mismatch between what ingestion writes and
    what the CORE builds expect would show up.
    """

    def setUp(self):
        from pipelines import snowflake_sqlite
        self.source, self.target = _oracle(), _warehouse()
        snowflake_sqlite.register(self.target)
        self.target.executescript(
            """
            CREATE TABLE CUSTOMER_IDENTITY_MAP (
                ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL, SOURCE_SYSTEM TEXT NOT NULL,
                SOURCE_CUSTOMER_REF TEXT NOT NULL, EMAIL_NORMALIZED TEXT, EMAIL_HASH TEXT,
                MATCH_METHOD TEXT NOT NULL, MATCH_CONFIDENCE REAL,
                RESOLVED_AT TEXT NOT NULL, IS_ACTIVE BOOLEAN);
            CREATE TABLE RAW_PARTNER_ACQUISITION_COST (
                CAMPAIGN_ID TEXT, PARTNER_ID TEXT, COST_DATE TEXT, ACQUISITION_COST NUMERIC,
                CURRENCY_CODE TEXT, _INGESTED_AT TEXT);
            CREATE TABLE RAW_SUBSCRIPTIONS (
                SUBSCRIPTION_ID TEXT, CRM_CUSTOMER_REF TEXT, BILLING_EMAIL TEXT, PLAN_ID TEXT,
                SUBSCRIPTION_STATUS TEXT, STARTED_AT TEXT, CURRENT_PERIOD_START TEXT,
                CURRENT_PERIOD_END TEXT, CANCELED_AT TEXT, MRR_AMOUNT REAL,
                CURRENCY_CODE TEXT, UPDATED_AT TEXT, _SOURCE_SYSTEM TEXT,
                _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE FX_RATE_DAILY (
                RATE_DATE TEXT NOT NULL, FROM_CURRENCY TEXT NOT NULL,
                TO_CURRENCY TEXT NOT NULL, FX_RATE REAL NOT NULL);
            CREATE TABLE FX_COVERAGE_GAP (
                REQUIRED_CURRENCY TEXT NOT NULL, REQUIRED_DATE TEXT NOT NULL,
                SOURCE_TABLE TEXT NOT NULL, AFFECTED_ROW_COUNT NUMERIC NOT NULL,
                DETECTED_AT TEXT NOT NULL);
            CREATE TABLE ORDER_FACT (
                ORDER_KEY TEXT NOT NULL PRIMARY KEY, ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL,
                ORDER_STATUS TEXT, ORDERED_AT_UTC TEXT NOT NULL, ORDER_DATE_UTC TEXT,
                SOURCE_CURRENCY_CODE TEXT, ORDER_AMOUNT_SOURCE REAL,
                FX_RATE_APPLIED REAL NOT NULL, ORDER_AMOUNT_USD REAL NOT NULL,
                CHANNEL_CODE TEXT);
            CREATE TABLE PAYMENT (
                PAYMENT_KEY TEXT NOT NULL PRIMARY KEY, ORDER_KEY TEXT NOT NULL,
                ENTERPRISE_CUSTOMER_KEY TEXT, PAYMENT_STATUS TEXT, PAYMENT_METHOD TEXT,
                PAID_AT_UTC TEXT, SOURCE_CURRENCY_CODE TEXT,
                PAYMENT_AMOUNT_USD REAL NOT NULL);
            INSERT INTO CUSTOMER_IDENTITY_MAP VALUES
                ('CUST_KEY_7','ORACLE_SALES','7','a@example.com','h','EMAIL_NORMALIZED',
                 1.0,'2026-03-01 04:00:00',1);
            """
        )

    def tearDown(self):
        self.source.close()
        self.target.close()

    def _seed_oracle(self, currency="EUR", amount=100.0):
        self.source.execute("INSERT INTO ORDERS VALUES (?,?,?,?,?,?,?,?)",
                            (1, 7, "PAID", "2026-03-01 09:00:00", currency, amount,
                             "WEB", T0 + HOUR / 2))
        # Settles inside the same ingestion window as its order, so one run lands both.
        self.source.execute("INSERT INTO PAYMENTS VALUES (?,?,?,?,?,?,?,?)",
                            (100, 1, "CARD", "CAPTURED", amount, currency,
                             T0 + timedelta(minutes=45), "4321"))

    def _ingest(self):
        return run(self.source, self.target, window_start=T0, window_end=T0 + HOUR,
                   batch_id="run_a")

    def test_landed_orders_flow_through_the_revenue_build(self):
        from pipelines import revenue
        self._seed_oracle(currency="EUR", amount=100.0)
        self.target.execute("INSERT INTO FX_RATE_DAILY VALUES ('2026-03-01','EUR','USD',1.08)")
        self._ingest()
        revenue.build(self.target, oracle_server_timezone="UTC", dialect="sqlite")
        self.assertEqual(
            self.target.execute(
                "SELECT ORDER_AMOUNT_SOURCE, FX_RATE_APPLIED, ORDER_AMOUNT_USD"
                " FROM ORDER_FACT").fetchall(),
            [(100.0, 1.08, 108.0)])
        self.assertEqual(
            self.target.execute("SELECT PAYMENT_AMOUNT_USD FROM PAYMENT").fetchall(),
            [(108.0,)])

    def test_a_landed_order_with_no_rate_blocks_the_revenue_build(self):
        """The gate sees real landed rows, not fixtures."""
        from pipelines.revenue import FxCoverageError, build
        self._seed_oracle(currency="JPY")
        self._ingest()
        with self.assertRaises(FxCoverageError) as caught:
            build(self.target, oracle_server_timezone="UTC", dialect="sqlite")
        self.assertEqual({g.currency for g in caught.exception.gaps}, {"JPY"})
        self.assertEqual(self.target.execute("SELECT COUNT(*) FROM ORDER_FACT").fetchone()[0], 0)

    def test_pii_excluded_at_ingestion_cannot_reach_core(self):
        from pipelines import revenue
        self._seed_oracle(currency="USD")
        self._ingest()
        revenue.build(self.target, oracle_server_timezone="UTC", dialect="sqlite")
        for table in ("RAW_PAYMENTS", "PAYMENT"):
            rows = self.target.execute(f"SELECT * FROM {table}").fetchall()
            self.assertNotIn("4321", [str(v) for row in rows for v in row])


if __name__ == "__main__":
    unittest.main(verbosity=2)
