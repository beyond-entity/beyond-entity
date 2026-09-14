"""Validation for the revenue chain and its FX quality gate.

The policy under test: a missing required FX rate is a data quality failure. The
affected revenue rows are neither dropped nor published with null USD amounts --
the build fails, and nothing is published at all.
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines import core_customer, revenue, snowflake_sqlite, sql_runner  # noqa: E402
from pipelines.revenue import FxCoverageError  # noqa: E402

TZ = "UTC"
ORACLE = "ORACLE_SALES"


class RevenueCase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        snowflake_sqlite.register(self.conn)
        self.conn.executescript(
            """
            CREATE TABLE RAW_ORDERS (
                ORDER_ID INTEGER, CUSTOMER_ID INTEGER, ORDER_STATUS TEXT, ORDER_DATE TEXT,
                CURRENCY_CODE TEXT, TOTAL_AMOUNT REAL, CHANNEL_CODE TEXT, UPDATED_AT TEXT,
                _SOURCE_SYSTEM TEXT, _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE RAW_PAYMENTS (
                PAYMENT_ID INTEGER, ORDER_ID INTEGER, PAYMENT_METHOD TEXT, PAYMENT_STATUS TEXT,
                PAYMENT_AMOUNT REAL, CURRENCY_CODE TEXT, PAID_AT TEXT, _SOURCE_SYSTEM TEXT,
                _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
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
            """
        )
        self.identity("CUST_KEY_1", "1")

    def tearDown(self):
        self.conn.close()

    # -- fixtures --------------------------------------------------------
    def identity(self, key, ref, system=ORACLE):
        self.conn.execute(
            "INSERT INTO CUSTOMER_IDENTITY_MAP VALUES (?,?,?,?,?,?,?,?,?)",
            (key, system, ref, "a@example.com", "hash", "EMAIL_NORMALIZED", 1.0,
             "2026-03-01 04:00:00", True))

    def order(self, order_id, *, customer_id=1, currency="EUR", amount=100.0,
              date="2026-03-01 10:00:00", status="PAID", updated="2026-03-01 10:00:00",
              ingested="2026-03-01 10:05:00"):
        self.conn.execute(
            "INSERT INTO RAW_ORDERS VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (order_id, customer_id, status, date, currency, amount, "WEB", updated,
             ORACLE, ingested, "dag_ingest_oracle_orders", "b1"))

    def payment(self, payment_id, order_id, *, currency="EUR", amount=100.0,
                paid_at="2026-03-01 12:00:00", status="CAPTURED",
                ingested="2026-03-01 12:05:00"):
        self.conn.execute(
            "INSERT INTO RAW_PAYMENTS VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (payment_id, order_id, "CARD", status, amount, currency, paid_at,
             ORACLE, ingested, "dag_ingest_oracle_orders", "b1"))

    def rate(self, currency, date, value, *, to_currency="USD"):
        self.conn.execute("INSERT INTO FX_RATE_DAILY VALUES (?,?,?,?)",
                          (date, currency, to_currency, value))

    def build(self):
        return revenue.build(self.conn, oracle_server_timezone=TZ, dialect="sqlite")

    def orders(self, columns="*"):
        return self.conn.execute(f"SELECT {columns} FROM ORDER_FACT").fetchall()

    def payments(self, columns="*"):
        return self.conn.execute(f"SELECT {columns} FROM PAYMENT").fetchall()


class FxGateTests(RevenueCase):
    def test_missing_rate_fails_the_build(self):
        self.order(1, currency="EUR", date="2026-03-01 10:00:00")
        with self.assertRaises(FxCoverageError):
            self.build()

    def test_nothing_is_published_when_a_rate_is_missing(self):
        """Not dropped, not null -- not published at all."""
        self.order(1, currency="EUR")
        self.order(2, currency="USD")
        with self.assertRaises(FxCoverageError):
            self.build()
        self.assertEqual(self.orders(), [], "the USD order must not be published either")

    def test_the_failure_names_the_missing_rates(self):
        """Failing is only useful if someone can see which rates to go and get."""
        self.order(1, currency="EUR", date="2026-03-01 10:00:00")
        self.order(2, currency="JPY", date="2026-03-02 10:00:00")
        with self.assertRaises(FxCoverageError) as caught:
            self.build()
        gaps = {(g.currency, g.date) for g in caught.exception.gaps}
        self.assertEqual(gaps, {("EUR", "2026-03-01"), ("JPY", "2026-03-02")})
        self.assertIn("EUR", str(caught.exception))

    def test_usd_needs_no_rate(self):
        """A currency that cannot be wrong must not be able to block revenue."""
        self.order(1, currency="USD", amount=250.0)
        self.build()
        self.assertEqual(self.orders("ORDER_AMOUNT_USD, FX_RATE_APPLIED"), [(250.0, 1.0)])

    def test_a_rate_on_the_wrong_date_does_not_satisfy_the_requirement(self):
        self.order(1, currency="EUR", date="2026-03-01 10:00:00")
        self.rate("EUR", "2026-03-02", 1.08)
        with self.assertRaises(FxCoverageError):
            self.build()

    def test_a_rate_to_the_wrong_target_currency_does_not_satisfy(self):
        self.order(1, currency="EUR", date="2026-03-01 10:00:00")
        self.rate("EUR", "2026-03-01", 0.86, to_currency="GBP")
        with self.assertRaises(FxCoverageError):
            self.build()

    def test_payments_are_checked_on_their_own_settlement_date(self):
        """A payment can settle days after its order, at a different rate."""
        self.order(1, currency="EUR", date="2026-03-01 10:00:00")
        self.rate("EUR", "2026-03-01", 1.08)
        self.payment(9, 1, currency="EUR", paid_at="2026-03-05 12:00:00")
        with self.assertRaises(FxCoverageError) as caught:
            self.build()
        self.assertEqual([(g.currency, g.date, g.source_table) for g in caught.exception.gaps],
                         [("EUR", "2026-03-05", "RAW_PAYMENTS")])

    def test_the_gap_is_rebuilt_not_accumulated(self):
        self.order(1, currency="EUR", date="2026-03-01 10:00:00")
        with self.assertRaises(FxCoverageError):
            self.build()
        self.rate("EUR", "2026-03-01", 1.08)
        self.build()
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM FX_COVERAGE_GAP").fetchone()[0], 0)

    def test_a_missing_subscription_rate_does_not_block_orders(self):
        """The gate is per build: SOURCE_TABLE is what keeps revenue streams separate."""
        self.order(1, currency="USD")
        self.conn.execute(
            "INSERT INTO RAW_SUBSCRIPTIONS VALUES"
            " ('SUB_1','CRM_9','a@example.com','PLAN_A','ACTIVE','2026-03-01 00:00:00',"
            "'2026-03-01 00:00:00','2026-04-01 00:00:00',NULL,50.0,'JPY',"
            "'2026-03-01 00:00:00','POSTGRES_SUBSCRIPTION','2026-03-01 01:00:00','j','b1')")
        self.build()   # must not raise
        self.assertEqual(len(self.orders()), 1)
        gaps = self.conn.execute(
            "SELECT SOURCE_TABLE FROM FX_COVERAGE_GAP").fetchall()
        self.assertEqual(gaps, [("RAW_SUBSCRIPTIONS",)],
                         "the subscription gap is still recorded, just not blocking here")

    def test_the_gate_does_not_block_unrelated_pipelines(self):
        """A missing exchange rate says nothing about customer identity."""
        self.order(1, currency="EUR")
        with self.assertRaises(FxCoverageError):
            self.build()
        # The customer spine has its own tables; prove it still runs to completion.
        self.conn.executescript(
            """
            CREATE TABLE RAW_CUSTOMERS (
                CUSTOMER_ID INTEGER, CUSTOMER_NAME TEXT, EMAIL TEXT, PHONE_NUMBER TEXT,
                BILLING_ADDRESS TEXT, COUNTRY_CODE TEXT, CUSTOMER_STATUS TEXT,
                CREATED_AT TEXT, UPDATED_AT TEXT, _SOURCE_SYSTEM TEXT, _INGESTED_AT TEXT,
                _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE RAW_SUPPORT_TICKETS (
                TICKET_ID TEXT, SUPPORT_CUSTOMER_REF TEXT, CONTACT_EMAIL TEXT,
                TICKET_STATUS TEXT, PRIORITY TEXT, CATEGORY_CODE TEXT, CREATED_AT TEXT,
                RESOLVED_AT TEXT, CHANNEL TEXT, _SOURCE_SYSTEM TEXT, _INGESTED_AT TEXT,
                _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE RAW_PARTNER_CUSTOMER_MAP (
                PARTNER_CUSTOMER_ID TEXT, PARTNER_ID TEXT, EMAIL TEXT, SIGNUP_AT TEXT,
                FIRST_TOUCH_CAMPAIGN_ID TEXT, _SOURCE_FILE TEXT, _SOURCE_SYSTEM TEXT,
                _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE CUSTOMER (
                ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL PRIMARY KEY, CUSTOMER_NAME TEXT,
                EMAIL TEXT, EMAIL_HASH TEXT, PHONE_NUMBER TEXT, BILLING_COUNTRY_CODE TEXT,
                CUSTOMER_STATUS TEXT, FIRST_SEEN_AT_UTC TEXT, ACQUISITION_CAMPAIGN_ID TEXT,
    ACQUISITION_CAMPAIGN_KEY TEXT,
                SOURCE_SYSTEM_COUNT INTEGER);
            INSERT INTO RAW_CUSTOMERS VALUES
                (1,'Ada','ada@example.com','x','y','US','ACTIVE','2026-01-01 00:00:00',
                 '2026-03-01 10:00:00','ORACLE_SALES','2026-03-01 10:05:00','j','b1');
            """
        )
        result = core_customer.run(self.conn, oracle_server_timezone=TZ, dialect="sqlite")
        self.assertEqual(result.target_rows["CUSTOMER"], 1)


class RevenueBuildTests(RevenueCase):
    def test_currency_is_normalized_on_the_orders_own_date(self):
        self.order(1, currency="EUR", amount=100.0, date="2026-03-01 10:00:00")
        self.rate("EUR", "2026-03-01", 1.08)
        self.build()
        self.assertEqual(self.orders("ORDER_AMOUNT_SOURCE, FX_RATE_APPLIED, ORDER_AMOUNT_USD"),
                         [(100.0, 1.08, 108.0)])

    def test_several_rate_dates_do_not_multiply_the_order(self):
        """An FX join without the date predicate fans out and inflates revenue."""
        self.order(1, currency="EUR", amount=100.0, date="2026-03-01 10:00:00")
        self.rate("EUR", "2026-03-01", 1.08)
        self.rate("EUR", "2026-03-02", 1.09)
        self.rate("EUR", "2026-03-03", 1.10)
        self.build()
        self.assertEqual(len(self.orders()), 1)
        self.assertEqual(self.orders("ORDER_AMOUNT_USD")[0][0], 108.0)

    def test_append_only_versions_collapse_to_the_latest_order(self):
        self.order(1, status="PENDING", amount=100.0, currency="USD",
                   updated="2026-03-01 10:00:00")
        self.order(1, status="COMPLETED", amount=150.0, currency="USD",
                   updated="2026-03-04 10:00:00")
        self.build()
        self.assertEqual(self.orders("ORDER_STATUS, ORDER_AMOUNT_USD"),
                         [("FULFILLED", 150.0)])

    def test_identity_join_is_scoped_to_oracle(self):
        """A PostgreSQL CRM ref that looks like an Oracle customer id must not match."""
        self.identity("WRONG_KEY", "1", system="POSTGRES_SUBSCRIPTION")
        self.order(1, customer_id=1, currency="USD")
        self.build()
        self.assertEqual(self.orders("ENTERPRISE_CUSTOMER_KEY"), [("CUST_KEY_1",)])

    def test_status_vocabulary_is_mapped(self):
        for n, (src, want) in enumerate(
                [("PENDING", "PENDING"), ("PAID", "CONFIRMED"), ("SHIPPED", "CONFIRMED"),
                 ("COMPLETED", "FULFILLED"), ("CANCELLED", "CANCELLED"), ("WEIRD", "REFUNDED")],
                start=1):
            self.order(n, status=src, currency="USD")
        self.build()
        got = dict(self.conn.execute(
            "SELECT ORDER_KEY, ORDER_STATUS FROM ORDER_FACT").fetchall())
        self.assertEqual(got["4"], "FULFILLED")
        self.assertEqual(got["6"], "REFUNDED")

    def test_payment_inherits_the_customer_key_from_the_order(self):
        self.order(1, currency="USD")
        self.payment(9, 1, currency="USD", amount=50.0)
        self.build()
        self.assertEqual(self.payments("ENTERPRISE_CUSTOMER_KEY, PAYMENT_AMOUNT_USD"),
                         [("CUST_KEY_1", 50.0)])

    def test_payment_converts_on_its_own_settlement_date(self):
        self.order(1, currency="EUR", amount=100.0, date="2026-03-01 10:00:00")
        self.rate("EUR", "2026-03-01", 1.08)
        self.rate("EUR", "2026-03-05", 1.20)
        self.payment(9, 1, currency="EUR", amount=100.0, paid_at="2026-03-05 12:00:00")
        self.build()
        self.assertEqual(self.orders("ORDER_AMOUNT_USD")[0][0], 108.0)
        self.assertEqual(self.payments("PAYMENT_AMOUNT_USD")[0][0], 120.0)

    def test_payment_status_vocabulary_is_mapped(self):
        self.order(1, currency="USD")
        self.payment(9, 1, currency="USD", status="CAPTURED")
        self.build()
        self.assertEqual(self.payments("PAYMENT_STATUS"), [("SETTLED",)])

    def test_rebuild_is_idempotent(self):
        self.order(1, currency="USD")
        self.payment(9, 1, currency="USD")
        first = self.build()
        second = self.build()
        self.assertEqual(first.target_rows, second.target_rows)
        self.assertEqual(second.target_rows["ORDER_FACT"], 1)

    def test_not_null_backstop_fires_if_the_gate_is_bypassed(self):
        """Defence in depth: publishing a null USD amount must be impossible."""
        self.order(1, currency="EUR")  # no rate, and we skip assert_fx_coverage
        with self.assertRaises(sqlite3.IntegrityError):
            sql_runner.run(self.conn, sql_dir=revenue.REVENUE_SQL_DIR,
                           parameters={"oracle_server_timezone": TZ},
                           dialect="sqlite", rebuild=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
