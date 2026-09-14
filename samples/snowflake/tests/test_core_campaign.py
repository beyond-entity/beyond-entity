"""Validation for Build Core Campaign (proc_7x7b2hFPxu) and its FX gate.

Campaign spend is the sum of daily costs, each converted at its own COST_DATE rate
(BR-2). Three of the original statement's defects produced a wrong number rather
than an error, and all three are asserted against here: the whole-key FX join, the
missing dedup on append-only RAW, and the acquisition-cost join that omitted
PARTNER_ID even though campaign identifiers are only unique within a partner.
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines import core_campaign, snowflake_sqlite  # noqa: E402
from pipelines.core_campaign import FxCoverageError  # noqa: E402


class CampaignCase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        snowflake_sqlite.register(self.conn)
        self.conn.executescript(
            """
            CREATE TABLE RAW_CAMPAIGN_DATA (
                CAMPAIGN_ID TEXT NOT NULL, PARTNER_ID TEXT NOT NULL, CAMPAIGN_NAME TEXT,
                CHANNEL TEXT, START_DATE TEXT, END_DATE TEXT, ACQUISITION_COST NUMERIC,
                CURRENCY_CODE TEXT, TARGET_SEGMENT TEXT, _SOURCE_FILE TEXT,
                _SOURCE_SYSTEM TEXT, _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT,
                _BATCH_ID TEXT);
            CREATE TABLE RAW_PARTNER_ACQUISITION_COST (
                CAMPAIGN_ID TEXT NOT NULL, PARTNER_ID TEXT NOT NULL, COST_DATE TEXT NOT NULL,
                ACQUISITION_COST NUMERIC, CURRENCY_CODE TEXT, ATTRIBUTED_SIGNUPS NUMERIC,
                _SOURCE_FILE TEXT, _SOURCE_SYSTEM TEXT, _INGESTED_AT TEXT,
                _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE RAW_ORDERS (
                ORDER_ID TEXT, ORDER_DATE TEXT, CURRENCY_CODE TEXT, _INGESTED_AT TEXT);
            CREATE TABLE RAW_PAYMENTS (
                PAYMENT_ID TEXT, PAID_AT TEXT, CURRENCY_CODE TEXT, _INGESTED_AT TEXT);
            CREATE TABLE RAW_SUBSCRIPTIONS (
                SUBSCRIPTION_ID TEXT, CURRENT_PERIOD_START TEXT, CURRENCY_CODE TEXT,
                MRR_AMOUNT NUMERIC, _INGESTED_AT TEXT);
            CREATE TABLE FX_RATE_DAILY (
                RATE_DATE TEXT NOT NULL, FROM_CURRENCY TEXT NOT NULL,
                TO_CURRENCY TEXT NOT NULL, FX_RATE REAL NOT NULL);
            CREATE TABLE FX_COVERAGE_GAP (
                REQUIRED_CURRENCY TEXT NOT NULL, REQUIRED_DATE TEXT NOT NULL,
                SOURCE_TABLE TEXT NOT NULL, AFFECTED_ROW_COUNT NUMERIC NOT NULL,
                DETECTED_AT TEXT NOT NULL);
            CREATE TABLE CAMPAIGN_DAILY_COST (
                CAMPAIGN_KEY TEXT NOT NULL, PARTNER_ID TEXT NOT NULL,
                CAMPAIGN_ID TEXT NOT NULL, COST_DATE TEXT NOT NULL,
                SOURCE_CURRENCY_CODE TEXT, COST_AMOUNT_SOURCE NUMERIC,
                FX_RATE_APPLIED NUMERIC NOT NULL, COST_AMOUNT_USD NUMERIC NOT NULL,
                ATTRIBUTED_SIGNUPS NUMERIC);
            CREATE TABLE CAMPAIGN (
                CAMPAIGN_KEY TEXT NOT NULL, PARTNER_ID TEXT NOT NULL,
                CAMPAIGN_ID TEXT NOT NULL, CAMPAIGN_NAME TEXT, CHANNEL TEXT,
                START_DATE TEXT, END_DATE TEXT, SOURCE_CURRENCY_CODE TEXT,
                TOTAL_SPEND_SOURCE NUMERIC, TOTAL_SPEND_USD NUMERIC,
                COST_DAY_COUNT NUMERIC, ATTRIBUTED_SIGNUPS NUMERIC, TARGET_SEGMENT TEXT);
            """
        )

    def tearDown(self):
        self.conn.close()

    # -- fixtures --------------------------------------------------------
    def campaign(self, campaign_id="CMP_1", partner="PTR_1", *, name="Spring",
                 currency="USD", ingested="2026-03-01 03:05:00", batch="b1"):
        self.conn.execute(
            "INSERT INTO RAW_CAMPAIGN_DATA VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (campaign_id, partner, name, "SEARCH", "2026-03-01", "2026-03-31", None,
             currency, "SMB", "f.csv", "PARTNER_LANDING", ingested,
             "dag_ingest_partner_files", batch))

    def cost(self, cost_date, amount, *, campaign_id="CMP_1", partner="PTR_1",
             currency="USD", signups=1, ingested="2026-03-01 03:05:00", batch="b1"):
        self.conn.execute(
            "INSERT INTO RAW_PARTNER_ACQUISITION_COST VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (campaign_id, partner, cost_date, amount, currency, signups, "c.parquet",
             "PARTNER_LANDING", ingested, "dag_ingest_partner_files", batch))

    def rate(self, date, currency, rate, to_currency="USD"):
        self.conn.execute("INSERT INTO FX_RATE_DAILY VALUES (?,?,?,?)",
                          (date, currency, to_currency, rate))

    def build(self):
        return core_campaign.build(self.conn, dialect="sqlite")

    def campaigns(self, columns="*"):
        return self.conn.execute(
            f"SELECT {columns} FROM CAMPAIGN ORDER BY CAMPAIGN_KEY").fetchall()

    def days(self, columns="*"):
        return self.conn.execute(
            f"SELECT {columns} FROM CAMPAIGN_DAILY_COST ORDER BY CAMPAIGN_KEY, COST_DATE"
        ).fetchall()


class SpendAggregationTests(CampaignCase):
    def test_spend_is_the_sum_across_cost_dates(self):
        """BR-2. One arbitrary day's cost is not a campaign total."""
        self.campaign()
        self.cost("2026-03-01", 100.0)
        self.cost("2026-03-02", 250.0)
        self.cost("2026-03-03", 50.0)
        self.build()
        spend, days = self.campaigns("TOTAL_SPEND_USD, COST_DAY_COUNT")[0]
        self.assertEqual(spend, 400.0)
        self.assertEqual(days, 3)

    def test_each_day_converts_at_its_own_rate(self):
        """A campaign spanning a rate move must not use one rate for all of it."""
        self.campaign(currency="EUR")
        self.cost("2026-03-01", 100.0, currency="EUR")
        self.cost("2026-03-02", 100.0, currency="EUR")
        self.rate("2026-03-01", "EUR", 1.10)
        self.rate("2026-03-02", "EUR", 1.20)
        self.build()
        self.assertAlmostEqual(self.campaigns("TOTAL_SPEND_USD")[0][0], 230.0)

    def test_source_total_is_kept_for_audit(self):
        """No single FX_RATE_APPLIED can reproduce a multi-day total."""
        self.campaign(currency="EUR")
        self.cost("2026-03-01", 100.0, currency="EUR")
        self.cost("2026-03-02", 100.0, currency="EUR")
        self.rate("2026-03-01", "EUR", 1.10)
        self.rate("2026-03-02", "EUR", 1.20)
        self.build()
        self.assertAlmostEqual(self.campaigns("TOTAL_SPEND_SOURCE")[0][0], 200.0)

    def test_attributed_signups_follow_the_same_source_grain(self):
        self.campaign()
        self.cost("2026-03-01", 10.0, signups=3)
        self.cost("2026-03-02", 10.0, signups=4)
        self.build()
        self.assertEqual(self.campaigns("ATTRIBUTED_SIGNUPS")[0][0], 7)

    def test_usd_rows_need_no_rate(self):
        self.campaign()
        self.cost("2026-03-01", 100.0, currency="USD")
        self.build()
        rate, usd = self.days("FX_RATE_APPLIED, COST_AMOUNT_USD")[0]
        self.assertEqual((rate, usd), (1, 100.0))

    def test_campaign_with_no_cost_rows_reports_no_spend_not_zero(self):
        """No delivered cost is not the same as spending nothing."""
        self.campaign()
        self.build()
        spend, days = self.campaigns("TOTAL_SPEND_USD, COST_DAY_COUNT")[0]
        self.assertIsNone(spend)
        self.assertEqual(days, 0)

    def test_uncastable_cost_drops_at_the_core_boundary(self):
        self.campaign()
        self.cost("2026-03-01", None)
        self.cost("2026-03-02", 40.0)
        self.build()
        self.assertEqual(len(self.days()), 1)
        self.assertEqual(self.campaigns("TOTAL_SPEND_USD")[0][0], 40.0)


class PartnerScopingTests(CampaignCase):
    """Campaign identifiers are unique only within a partner."""

    def test_two_partners_reusing_a_campaign_id_keep_separate_spend(self):
        """The cost join omitted PARTNER_ID, so each partner got the other's spend."""
        self.campaign("CMP_1", "PTR_1")
        self.campaign("CMP_1", "PTR_2")
        self.cost("2026-03-01", 100.0, campaign_id="CMP_1", partner="PTR_1")
        self.cost("2026-03-01", 900.0, campaign_id="CMP_1", partner="PTR_2")
        self.build()
        spend = dict(self.campaigns("CAMPAIGN_KEY, TOTAL_SPEND_USD"))
        self.assertEqual(spend, {"PTR_1:CMP_1": 100.0, "PTR_2:CMP_1": 900.0})

    def test_campaign_key_is_composite(self):
        self.campaign("CMP_1", "PTR_9")
        self.build()
        self.assertEqual(self.campaigns("CAMPAIGN_KEY")[0][0], "PTR_9:CMP_1")


class DeduplicationTests(CampaignCase):
    def test_redelivered_campaign_produces_one_row(self):
        """RAW is append-only; the build read it without dedup."""
        self.campaign(name="Spring", ingested="2026-03-01 03:05:00", batch="b1")
        self.campaign(name="Spring Revised", ingested="2026-03-02 03:05:00", batch="b2")
        self.build()
        self.assertEqual(len(self.campaigns()), 1)
        self.assertEqual(self.campaigns("CAMPAIGN_NAME")[0][0], "Spring Revised")

    def test_redelivered_cost_day_is_not_counted_twice(self):
        self.campaign()
        self.cost("2026-03-01", 100.0, ingested="2026-03-01 03:05:00", batch="b1")
        self.cost("2026-03-01", 120.0, ingested="2026-03-02 03:05:00", batch="b2")
        self.build()
        spend, days = self.campaigns("TOTAL_SPEND_USD, COST_DAY_COUNT")[0]
        self.assertEqual((spend, days), (120.0, 1))

    def test_several_cost_days_do_not_multiply_the_campaign_row(self):
        """Summing days through a join would fan the campaign back out."""
        self.campaign()
        for day in range(1, 6):
            self.cost(f"2026-03-0{day}", 10.0)
        self.build()
        self.assertEqual(len(self.campaigns()), 1)

    def test_fx_join_carries_the_whole_rate_key(self):
        """A join on currency alone matches every rate date and multiplies the row."""
        self.campaign(currency="EUR")
        self.cost("2026-03-01", 100.0, currency="EUR")
        for day, rate in (("2026-03-01", 1.10), ("2026-03-02", 1.20),
                          ("2026-03-03", 1.30)):
            self.rate(day, "EUR", rate)
        self.build()
        self.assertEqual(len(self.days()), 1)
        self.assertAlmostEqual(self.campaigns("TOTAL_SPEND_USD")[0][0], 110.0)

    def test_a_rate_to_another_currency_is_not_used(self):
        self.campaign(currency="EUR")
        self.cost("2026-03-01", 100.0, currency="EUR")
        self.rate("2026-03-01", "EUR", 0.9, to_currency="GBP")
        self.rate("2026-03-01", "EUR", 1.10)
        self.build()
        self.assertAlmostEqual(self.campaigns("TOTAL_SPEND_USD")[0][0], 110.0)


class FxGateTests(CampaignCase):
    def test_a_missing_rate_blocks_the_campaign_build(self):
        """SUM ignores NULLs, so an unresolved day would quietly shrink the campaign."""
        self.campaign(currency="EUR")
        self.cost("2026-03-01", 100.0, currency="EUR")
        self.cost("2026-03-02", 100.0, currency="EUR")
        self.rate("2026-03-01", "EUR", 1.10)
        with self.assertRaises(FxCoverageError) as raised:
            self.build()
        self.assertEqual(len(raised.exception.gaps), 1)
        gap = raised.exception.gaps[0]
        self.assertEqual((gap.currency, gap.date), ("EUR", "2026-03-02"))
        self.assertEqual(gap.source_table, "RAW_PARTNER_ACQUISITION_COST")

    def test_a_blocked_build_publishes_nothing(self):
        self.campaign(currency="EUR")
        self.cost("2026-03-01", 100.0, currency="EUR")
        with self.assertRaises(FxCoverageError):
            self.build()
        self.assertEqual(self.campaigns(), [])
        self.assertEqual(self.days(), [])

    def test_a_cost_row_with_no_amount_requires_no_rate(self):
        self.campaign(currency="EUR")
        self.cost("2026-03-01", None, currency="EUR")
        self.build()
        self.assertEqual(self.days(), [])

    def test_an_order_gap_does_not_block_campaigns(self):
        """The gate is per build. A real order gap is detected, and ignored here."""
        self.conn.execute(
            "INSERT INTO RAW_ORDERS VALUES ('ORD_1','2026-03-01 10:00:00','EUR','now')")
        self.campaign()
        self.cost("2026-03-01", 100.0)
        self.build()
        self.assertEqual(len(self.campaigns()), 1)
        blocking = self.conn.execute(
            "SELECT SOURCE_TABLE FROM FX_COVERAGE_GAP").fetchall()
        self.assertEqual(blocking, [("RAW_ORDERS",)])


if __name__ == "__main__":
    unittest.main()
