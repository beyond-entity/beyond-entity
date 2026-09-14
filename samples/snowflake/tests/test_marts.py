"""Validation for the ANALYTICS marts: CUSTOMER_360 and MONTHLY_REVENUE.

These two builds carried D21, the multi-fact fan-out, which is the most damaging
defect found in this project: joining several independent one-to-many facts to one
grain and then aggregating multiplies every measure by the cardinality of the other
facts. The output stays plausible -- just several times too large -- so most of the
cases here are arithmetic against hand-computed totals rather than shape checks.

They also implement two written business rules: BR-1 (which subscriptions count and
how several collapse into one state) and BR-3 (which month each measure lands in).
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines import (  # noqa: E402
    campaign_performance, customer_360, lifetime_value, monthly_revenue,
    retention, snowflake_sqlite, support_health,
)

CORE_SCHEMA = """
CREATE TABLE CUSTOMER (
    ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL, CUSTOMER_NAME TEXT, EMAIL TEXT,
    EMAIL_HASH TEXT, PHONE_NUMBER TEXT, BILLING_COUNTRY_CODE TEXT,
    CUSTOMER_STATUS TEXT, FIRST_SEEN_AT_UTC TEXT, ACQUISITION_CAMPAIGN_ID TEXT,
    ACQUISITION_CAMPAIGN_KEY TEXT,
    SOURCE_SYSTEM_COUNT NUMERIC);
CREATE TABLE ORDER_FACT (
    ORDER_KEY TEXT NOT NULL, ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL,
    ORDER_STATUS TEXT, ORDERED_AT_UTC TEXT, ORDER_DATE_UTC TEXT,
    SOURCE_CURRENCY_CODE TEXT, ORDER_AMOUNT_SOURCE NUMERIC,
    FX_RATE_APPLIED NUMERIC, ORDER_AMOUNT_USD NUMERIC, CHANNEL_CODE TEXT);
CREATE TABLE PAYMENT (
    PAYMENT_KEY TEXT NOT NULL, ORDER_KEY TEXT NOT NULL,
    ENTERPRISE_CUSTOMER_KEY TEXT, PAYMENT_STATUS TEXT, PAYMENT_METHOD TEXT,
    PAID_AT_UTC TEXT, SOURCE_CURRENCY_CODE TEXT, PAYMENT_AMOUNT_USD NUMERIC);
CREATE TABLE SUBSCRIPTION_FACT (
    SUBSCRIPTION_KEY TEXT NOT NULL, ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL,
    PLAN_ID TEXT, LIFECYCLE_STATE TEXT, STARTED_AT_UTC TEXT, CANCELED_AT_UTC TEXT,
    CURRENT_PERIOD_START_UTC TEXT, CURRENT_PERIOD_END_UTC TEXT,
    SOURCE_CURRENCY_CODE TEXT, MRR_AMOUNT_SOURCE NUMERIC,
    FX_RATE_APPLIED NUMERIC, MRR_USD NUMERIC);
CREATE TABLE SUPPORT_INTERACTION_FACT (
    TICKET_KEY TEXT NOT NULL, ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL,
    TICKET_STATUS TEXT, PRIORITY TEXT, CATEGORY_CODE TEXT,
    CREATED_AT_UTC TEXT, RESOLVED_AT_UTC TEXT, RESOLUTION_SECONDS NUMERIC,
    IS_RESOLVED BOOLEAN, CHANNEL TEXT);
"""


class MartCase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        snowflake_sqlite.register(self.conn)
        self.conn.executescript(CORE_SCHEMA + """
            CREATE TABLE CUSTOMER_360 (
                ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL, CUSTOMER_KEY_HASH TEXT,
                BILLING_COUNTRY_CODE TEXT, CUSTOMER_STATUS TEXT,
                FIRST_SEEN_AT_UTC TEXT, ACQUISITION_CAMPAIGN_ID TEXT,
                TOTAL_ORDERS NUMERIC, TOTAL_ORDER_REVENUE_USD NUMERIC,
                LAST_ORDER_AT_UTC TEXT, SUBSCRIPTION_LIFECYCLE_STATE TEXT,
                CURRENT_MRR_USD NUMERIC, SUPPORT_TICKET_COUNT NUMERIC,
                AVG_RESOLUTION_SECONDS NUMERIC, CONTRIBUTING_SOURCE_SYSTEMS NUMERIC);
            CREATE TABLE MONTHLY_REVENUE (
                REVENUE_MONTH TEXT NOT NULL, BILLING_COUNTRY_CODE TEXT,
                CHANNEL_CODE TEXT, ORDER_COUNT NUMERIC, ORDER_REVENUE_USD NUMERIC,
                SETTLED_REVENUE_USD NUMERIC, RECURRING_REVENUE_USD NUMERIC,
                DISTINCT_CUSTOMER_COUNT NUMERIC);
            CREATE TABLE MONTHLY_REVENUE_CONTRIBUTION (
                REVENUE_MONTH TEXT NOT NULL, BILLING_COUNTRY_CODE TEXT,
                CHANNEL_CODE TEXT, ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL,
                ORDER_COUNT NUMERIC, ORDER_REVENUE_USD NUMERIC,
                SETTLED_REVENUE_USD NUMERIC, RECURRING_REVENUE_USD NUMERIC);
        """)

    def tearDown(self):
        self.conn.close()

    # -- fixtures --------------------------------------------------------
    def customer(self, key="EK_1", *, country="US", status="ACTIVE", campaign="CMP_1",
                 partner="PTR_1", systems=2, first_seen="2026-01-01 00:00:00"):
        campaign_key = None if campaign is None else f"{partner}:{campaign}"
        self.conn.execute(
            "INSERT INTO CUSTOMER VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (key, "Ada", "ada@example.com", f"hash-{key}", "555", country, status,
             first_seen, campaign, campaign_key, systems))

    def order(self, order_key, *, customer="EK_1", amount=100.0,
              at="2026-03-05 10:00:00", date="2026-03-05", channel="WEB"):
        self.conn.execute(
            "INSERT INTO ORDER_FACT VALUES (?,?,?,?,?,?,?,?,?,?)",
            (order_key, customer, "COMPLETE", at, date, "USD", amount, 1, amount,
             channel))

    def payment(self, payment_key, order_key, *, customer="EK_1", amount=50.0,
                paid_at="2026-03-06 10:00:00"):
        self.conn.execute(
            "INSERT INTO PAYMENT VALUES (?,?,?,?,?,?,?,?)",
            (payment_key, order_key, customer, "SETTLED", "CARD", paid_at, "USD",
             amount))

    def subscription(self, sub_key, *, customer="EK_1", state="ACTIVE", mrr=30.0,
                     period_start="2026-03-01 00:00:00"):
        self.conn.execute(
            "INSERT INTO SUBSCRIPTION_FACT VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (sub_key, customer, "PLAN_A", state, "2026-01-01 00:00:00", None,
             period_start, "2026-04-01 00:00:00", "USD", mrr, 1, mrr))

    def ticket(self, ticket_key, *, customer="EK_1", seconds=600):
        self.conn.execute(
            "INSERT INTO SUPPORT_INTERACTION_FACT"
            " (TICKET_KEY, ENTERPRISE_CUSTOMER_KEY, TICKET_STATUS, PRIORITY,"
            " CATEGORY_CODE, CREATED_AT_UTC, RESOLUTION_SECONDS, IS_RESOLVED)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (ticket_key, customer, "RESOLVED", "P2", "BILLING",
             "2026-03-05 10:00:00", seconds, 1))


class CustomerThreeSixtyCase(MartCase):
    def build(self):
        return customer_360.build(self.conn, dialect="sqlite")

    def rows(self, columns="*"):
        return self.conn.execute(
            f"SELECT {columns} FROM CUSTOMER_360 ORDER BY ENTERPRISE_CUSTOMER_KEY"
        ).fetchall()


class FanOutTests(CustomerThreeSixtyCase):
    """D21. Three facts joined to one customer multiply each other."""

    def stage_the_fan_out(self):
        """3 orders, 2 subscriptions, 4 tickets: the join would produce 24 rows."""
        self.customer()
        for n in range(3):
            self.order(f"ORD_{n}", amount=100.0)
        for n in range(2):
            self.subscription(f"SUB_{n}", mrr=30.0)
        for n in range(4):
            self.ticket(f"TCK_{n}", seconds=600)

    def test_order_count_is_not_multiplied_by_the_other_facts(self):
        self.stage_the_fan_out()
        self.build()
        self.assertEqual(self.rows("TOTAL_ORDERS")[0][0], 3)

    def test_order_revenue_is_not_multiplied_by_the_other_facts(self):
        """This read 2400 instead of 300 -- plausible, and eight times too large."""
        self.stage_the_fan_out()
        self.build()
        self.assertEqual(self.rows("TOTAL_ORDER_REVENUE_USD")[0][0], 300.0)

    def test_ticket_count_is_not_multiplied_by_the_other_facts(self):
        self.stage_the_fan_out()
        self.build()
        self.assertEqual(self.rows("SUPPORT_TICKET_COUNT")[0][0], 4)

    def test_mrr_is_not_multiplied_by_the_other_facts(self):
        self.stage_the_fan_out()
        self.build()
        self.assertEqual(self.rows("CURRENT_MRR_USD")[0][0], 60.0)

    def test_average_resolution_is_not_distorted_by_repetition(self):
        self.customer()
        self.order("ORD_1")
        self.ticket("TCK_1", seconds=100)
        self.ticket("TCK_2", seconds=300)
        self.build()
        self.assertEqual(self.rows("AVG_RESOLUTION_SECONDS")[0][0], 200.0)

    def test_one_row_per_customer(self):
        self.stage_the_fan_out()
        self.build()
        self.assertEqual(len(self.rows()), 1)


class SubscriptionCollapseTests(CustomerThreeSixtyCase):
    """BR-1: revenue-bearing states, and precedence for the single state column."""

    def test_only_revenue_bearing_states_count_towards_mrr(self):
        self.customer()
        self.subscription("SUB_1", state="ACTIVE", mrr=30.0)
        self.subscription("SUB_2", state="AT_RISK", mrr=20.0)
        self.subscription("SUB_3", state="CHURNED", mrr=99.0)
        self.subscription("SUB_4", state="PAUSED", mrr=99.0)
        self.subscription("SUB_5", state="TRIAL", mrr=99.0)
        self.build()
        self.assertEqual(self.rows("CURRENT_MRR_USD")[0][0], 50.0)

    def test_all_concurrent_revenue_bearing_plans_are_summed(self):
        self.customer()
        self.subscription("SUB_1", state="ACTIVE", mrr=30.0)
        self.subscription("SUB_2", state="ACTIVE", mrr=45.0)
        self.build()
        self.assertEqual(self.rows("CURRENT_MRR_USD")[0][0], 75.0)

    def test_a_cancelled_subscription_alone_leaves_no_current_mrr(self):
        self.customer()
        self.subscription("SUB_1", state="CHURNED", mrr=30.0)
        self.build()
        self.assertIsNone(self.rows("CURRENT_MRR_USD")[0][0])

    def test_active_beats_churned(self):
        """MAX() of the state string returned CHURNED: the alphabet deciding."""
        self.customer()
        self.subscription("SUB_1", state="ACTIVE")
        self.subscription("SUB_2", state="CHURNED")
        self.build()
        self.assertEqual(self.rows("SUBSCRIPTION_LIFECYCLE_STATE")[0][0], "ACTIVE")

    def test_active_beats_trial(self):
        """MAX() returned TRIAL, for the same reason."""
        self.customer()
        self.subscription("SUB_1", state="ACTIVE")
        self.subscription("SUB_2", state="TRIAL")
        self.build()
        self.assertEqual(self.rows("SUBSCRIPTION_LIFECYCLE_STATE")[0][0], "ACTIVE")

    def test_the_full_precedence_order_holds(self):
        expected = customer_360.LIFECYCLE_PRECEDENCE
        for rank, winner in enumerate(expected):
            with self.subTest(winner=winner):
                self.conn.execute("DELETE FROM CUSTOMER")
                self.conn.execute("DELETE FROM SUBSCRIPTION_FACT")
                self.customer()
                for n, state in enumerate(expected[rank:]):
                    self.subscription(f"SUB_{n}", state=state)
                self.build()
                self.assertEqual(
                    self.rows("SUBSCRIPTION_LIFECYCLE_STATE")[0][0], winner)

    def test_a_customer_with_no_subscription_has_no_state(self):
        self.customer()
        self.order("ORD_1")
        self.build()
        self.assertIsNone(self.rows("SUBSCRIPTION_LIFECYCLE_STATE")[0][0])


class MaskingAndMembershipTests(CustomerThreeSixtyCase):
    def test_only_the_hashed_identifier_crosses_into_analytics(self):
        """Raw email, name and phone stop at CORE."""
        self.customer()
        self.build()
        published = self.conn.execute("SELECT * FROM CUSTOMER_360").fetchone()
        self.assertIn("hash-EK_1", published)
        for secret in ("ada@example.com", "Ada", "555"):
            self.assertNotIn(secret, published)

    def test_a_customer_with_no_facts_at_all_still_appears(self):
        """The spine is the customer, not any one source system."""
        self.customer("EK_LONELY")
        self.build()
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows("TOTAL_ORDERS")[0][0], 0)

    def test_contributing_source_systems_has_a_producer(self):
        """It was declared and written by nothing."""
        self.customer(systems=3)
        self.build()
        self.assertEqual(self.rows("CONTRIBUTING_SOURCE_SYSTEMS")[0][0], 3)

    def test_facts_belonging_to_another_customer_do_not_leak_in(self):
        self.customer("EK_1")
        self.customer("EK_2")
        self.order("ORD_1", customer="EK_1", amount=100.0)
        self.order("ORD_2", customer="EK_2", amount=700.0)
        self.build()
        revenue = dict(self.rows("ENTERPRISE_CUSTOMER_KEY, TOTAL_ORDER_REVENUE_USD"))
        self.assertEqual(revenue, {"EK_1": 100.0, "EK_2": 700.0})


class MonthlyRevenueCase(MartCase):
    def build(self):
        return monthly_revenue.build(self.conn, dialect="sqlite")

    def mart(self, columns="*"):
        return self.conn.execute(
            f"SELECT {columns} FROM MONTHLY_REVENUE"
            " ORDER BY REVENUE_MONTH, BILLING_COUNTRY_CODE, CHANNEL_CODE").fetchall()

    def measure(self, column, month, channel="WEB", country="US"):
        row = self.conn.execute(
            f"SELECT {column} FROM MONTHLY_REVENUE WHERE REVENUE_MONTH = ?"
            " AND BILLING_COUNTRY_CODE = ? AND (CHANNEL_CODE = ? OR"
            " (CHANNEL_CODE IS NULL AND ? IS NULL))",
            (month, country, channel, channel)).fetchone()
        return None if row is None else row[0]


class MonthAnchoringTests(MonthlyRevenueCase):
    """BR-3: each measure is reported in the month it belongs to."""

    def test_orders_report_in_the_order_month(self):
        self.customer()
        self.order("ORD_1", date="2026-03-05", amount=100.0)
        self.order("ORD_2", date="2026-04-02", amount=250.0)
        self.build()
        self.assertEqual(self.measure("ORDER_REVENUE_USD", "2026-03-01"), 100.0)
        self.assertEqual(self.measure("ORDER_REVENUE_USD", "2026-04-01"), 250.0)

    def test_payments_report_in_the_settlement_month_not_the_order_month(self):
        """A column named 'settled' was reporting the month the order was booked."""
        self.customer()
        self.order("ORD_1", date="2026-03-28", amount=100.0)
        self.payment("PAY_1", "ORD_1", amount=100.0, paid_at="2026-04-02 09:00:00")
        self.build()
        self.assertIsNone(self.measure("SETTLED_REVENUE_USD", "2026-03-01"))
        self.assertEqual(self.measure("SETTLED_REVENUE_USD", "2026-04-01"), 100.0)

    def test_recurring_revenue_reports_in_the_billing_period_month(self):
        self.customer()
        self.subscription("SUB_1", mrr=30.0, period_start="2026-05-01 00:00:00")
        self.build()
        self.assertEqual(
            self.measure("RECURRING_REVENUE_USD", "2026-05-01", channel=None), 30.0)

    def test_a_subscription_only_customer_still_contributes(self):
        """Driven by ORDER_FACT, such a customer contributed nothing for ever."""
        self.customer("EK_SUB")
        self.subscription("SUB_1", customer="EK_SUB", mrr=42.0)
        self.build()
        self.assertEqual(
            self.measure("RECURRING_REVENUE_USD", "2026-03-01", channel=None), 42.0)

    def test_recurring_revenue_appears_in_months_with_no_orders(self):
        self.customer()
        self.order("ORD_1", date="2026-03-05")
        self.subscription("SUB_1", mrr=30.0, period_start="2026-07-01 00:00:00")
        self.build()
        self.assertEqual(
            self.measure("RECURRING_REVENUE_USD", "2026-07-01", channel=None), 30.0)

    def test_recurring_revenue_carries_no_sales_channel(self):
        """A subscription has no channel; naming one would invent a sale."""
        self.customer()
        self.subscription("SUB_1", mrr=30.0)
        self.build()
        channels = {row[0] for row in self.mart("CHANNEL_CODE")}
        self.assertEqual(channels, {None})

    def test_payments_inherit_the_channel_of_the_order_they_settle(self):
        self.customer()
        self.order("ORD_1", date="2026-03-05", channel="RETAIL")
        self.payment("PAY_1", "ORD_1", amount=60.0, paid_at="2026-03-09 09:00:00")
        self.build()
        self.assertEqual(
            self.measure("SETTLED_REVENUE_USD", "2026-03-01", channel="RETAIL"), 60.0)

    def test_only_revenue_bearing_subscriptions_contribute(self):
        self.customer()
        self.subscription("SUB_1", state="CHURNED", mrr=99.0)
        self.build()
        self.assertEqual(self.mart(), [])


class MonthlyFanOutTests(MonthlyRevenueCase):
    """D21 again: payments and subscriptions multiplied the order measures."""

    def stage_the_fan_out(self):
        """1 order, 3 payments against it, 2 subscriptions, all in March."""
        self.customer()
        self.order("ORD_1", date="2026-03-05", amount=100.0)
        for n in range(3):
            self.payment(f"PAY_{n}", "ORD_1", amount=20.0,
                         paid_at="2026-03-06 10:00:00")
        for n in range(2):
            self.subscription(f"SUB_{n}", mrr=30.0)
        self.build()

    def test_order_revenue_is_not_multiplied_by_payments_and_subscriptions(self):
        """This read 600 instead of 100."""
        self.stage_the_fan_out()
        self.assertEqual(self.measure("ORDER_REVENUE_USD", "2026-03-01"), 100.0)

    def test_order_count_is_not_multiplied(self):
        self.stage_the_fan_out()
        self.assertEqual(self.measure("ORDER_COUNT", "2026-03-01"), 1)

    def test_settled_revenue_is_not_multiplied_by_subscriptions(self):
        self.stage_the_fan_out()
        self.assertEqual(self.measure("SETTLED_REVENUE_USD", "2026-03-01"), 60.0)

    def test_recurring_revenue_is_not_multiplied_by_payments(self):
        self.stage_the_fan_out()
        self.assertEqual(
            self.measure("RECURRING_REVENUE_USD", "2026-03-01", channel=None), 60.0)


class MartGrainTests(MonthlyRevenueCase):
    def test_distinct_customers_are_counted_not_summed(self):
        self.customer("EK_1")
        self.customer("EK_2")
        self.order("ORD_1", customer="EK_1", date="2026-03-05")
        self.order("ORD_2", customer="EK_1", date="2026-03-06")
        self.order("ORD_3", customer="EK_2", date="2026-03-07")
        self.payment("PAY_1", "ORD_1", customer="EK_1",
                     paid_at="2026-03-08 09:00:00")
        self.build()
        self.assertEqual(self.measure("DISTINCT_CUSTOMER_COUNT", "2026-03-01"), 2)

    def test_the_published_mart_carries_no_customer_identifier(self):
        self.customer()
        self.order("ORD_1", date="2026-03-05")
        self.build()
        columns = [d[0] for d in
                   self.conn.execute("SELECT * FROM MONTHLY_REVENUE").description]
        self.assertNotIn("ENTERPRISE_CUSTOMER_KEY", columns)

    def test_the_three_measures_stay_separate(self):
        self.customer()
        self.order("ORD_1", date="2026-03-05", amount=100.0)
        self.payment("PAY_1", "ORD_1", amount=40.0, paid_at="2026-03-09 09:00:00")
        self.build()
        booked, settled = self.conn.execute(
            "SELECT ORDER_REVENUE_USD, SETTLED_REVENUE_USD FROM MONTHLY_REVENUE"
            " WHERE REVENUE_MONTH = '2026-03-01'").fetchone()
        self.assertEqual((booked, settled), (100.0, 40.0))

    def test_country_and_channel_split_the_mart(self):
        self.customer("EK_US", country="US")
        self.customer("EK_DE", country="DE")
        self.order("ORD_1", customer="EK_US", date="2026-03-05", channel="WEB",
                   amount=10.0)
        self.order("ORD_2", customer="EK_DE", date="2026-03-05", channel="WEB",
                   amount=20.0)
        self.order("ORD_3", customer="EK_US", date="2026-03-05", channel="RETAIL",
                   amount=30.0)
        self.build()
        self.assertEqual(len(self.mart()), 3)

    def test_a_rebuild_is_idempotent(self):
        self.customer()
        self.order("ORD_1", date="2026-03-05", amount=100.0)
        self.build()
        self.build()
        self.assertEqual(self.measure("ORDER_REVENUE_USD", "2026-03-01"), 100.0)
        self.assertEqual(len(self.mart()), 1)


class SupportHealthCase(MartCase):
    """proc_tUDyM0IkCx. The one mart that needed no correction."""

    def setUp(self):
        super().setUp()
        self.conn.executescript("""
            CREATE TABLE CUSTOMER_SUPPORT_HEALTH (
                REPORTING_MONTH TEXT NOT NULL, CATEGORY_CODE TEXT, PRIORITY TEXT,
                TICKET_COUNT NUMERIC, RESOLVED_TICKET_COUNT NUMERIC,
                AVG_RESOLUTION_TIME NUMERIC, AFFECTED_CUSTOMER_COUNT NUMERIC,
                ESCALATION_RATE NUMERIC);
        """)

    def support_ticket(self, ticket_key, *, customer="EK_1", status="RESOLVED",
                       priority="P2", category="BILLING",
                       created="2026-03-05 10:00:00", seconds=600, resolved=True):
        self.conn.execute(
            "INSERT INTO SUPPORT_INTERACTION_FACT"
            " (TICKET_KEY, ENTERPRISE_CUSTOMER_KEY, TICKET_STATUS, PRIORITY,"
            " CATEGORY_CODE, CREATED_AT_UTC, RESOLUTION_SECONDS, IS_RESOLVED)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (ticket_key, customer, status, priority, category, created, seconds,
             1 if resolved else 0))

    def build(self):
        return support_health.build(self.conn, dialect="sqlite")

    def health(self, columns="*"):
        return self.conn.execute(
            f"SELECT {columns} FROM CUSTOMER_SUPPORT_HEALTH"
            " ORDER BY REPORTING_MONTH, CATEGORY_CODE, PRIORITY").fetchall()


class SupportHealthTests(SupportHealthCase):
    def test_tickets_group_by_month_category_and_priority(self):
        self.support_ticket("T1", category="BILLING", priority="P1")
        self.support_ticket("T2", category="BILLING", priority="P1")
        self.support_ticket("T3", category="BILLING", priority="P2")
        self.support_ticket("T4", category="ACCESS", priority="P1")
        self.build()
        counts = {(cat, pri): n for cat, pri, n in
                  self.health("CATEGORY_CODE, PRIORITY, TICKET_COUNT")}
        self.assertEqual(counts, {("ACCESS", "P1"): 1, ("BILLING", "P1"): 2,
                                  ("BILLING", "P2"): 1})

    def test_the_reporting_month_is_when_the_ticket_arrived(self):
        """An open ticket must not vanish from the month it landed in."""
        self.support_ticket("T1", created="2026-03-31 23:00:00", status="OPEN",
                            resolved=False, seconds=None)
        self.build()
        self.assertEqual(self.health("REPORTING_MONTH")[0][0], "2026-03-01")

    def test_unresolved_tickets_do_not_drag_the_average_to_zero(self):
        """RESOLUTION_SECONDS is null, not zero, and AVG ignores nulls."""
        self.support_ticket("T1", seconds=100)
        self.support_ticket("T2", seconds=300)
        self.support_ticket("T3", seconds=None, resolved=False, status="OPEN")
        self.build()
        count, resolved, average = self.health(
            "TICKET_COUNT, RESOLVED_TICKET_COUNT, AVG_RESOLUTION_TIME")[0]
        self.assertEqual((count, resolved), (3, 2))
        self.assertEqual(average, 200.0)

    def test_escalation_rate_is_the_proportion_escalated(self):
        self.support_ticket("T1", status="ESCALATED")
        self.support_ticket("T2", status="RESOLVED")
        self.support_ticket("T3", status="RESOLVED")
        self.support_ticket("T4", status="RESOLVED")
        self.build()
        self.assertEqual(self.health("ESCALATION_RATE")[0][0], 0.25)

    def test_escalated_is_a_status_core_actually_produces(self):
        """An indicator over a status the source never emits reads as good news."""
        core_build = Path(__file__).resolve().parent.parent / "sql" / "core" / "support"
        mapped = "".join(p.read_text() for p in core_build.glob("*.sql"))
        self.assertIn("THEN 'ESCALATED'", mapped)

    def test_affected_customers_are_counted_distinctly(self):
        self.support_ticket("T1", customer="EK_1")
        self.support_ticket("T2", customer="EK_1")
        self.support_ticket("T3", customer="EK_2")
        self.build()
        count, affected = self.health("TICKET_COUNT, AFFECTED_CUSTOMER_COUNT")[0]
        self.assertEqual((count, affected), (3, 2))

    def test_the_mart_carries_no_customer_identifier(self):
        self.support_ticket("T1")
        self.build()
        columns = [d[0] for d in self.conn.execute(
            "SELECT * FROM CUSTOMER_SUPPORT_HEALTH").description]
        self.assertNotIn("ENTERPRISE_CUSTOMER_KEY", columns)

    def test_a_rebuild_is_idempotent(self):
        self.support_ticket("T1")
        self.build()
        self.build()
        self.assertEqual(len(self.health()), 1)
        self.assertEqual(self.health("TICKET_COUNT")[0][0], 1)


class CampaignPerformanceCase(MartCase):
    """proc_EkjDDx59xe. The cross-system attribution join."""

    def setUp(self):
        super().setUp()
        self.conn.executescript("""
            CREATE TABLE CAMPAIGN (
                CAMPAIGN_KEY TEXT NOT NULL, PARTNER_ID TEXT NOT NULL,
                CAMPAIGN_ID TEXT NOT NULL, CAMPAIGN_NAME TEXT, CHANNEL TEXT,
                START_DATE TEXT, END_DATE TEXT, SOURCE_CURRENCY_CODE TEXT,
                TOTAL_SPEND_SOURCE NUMERIC, TOTAL_SPEND_USD NUMERIC,
                COST_DAY_COUNT NUMERIC, ATTRIBUTED_SIGNUPS NUMERIC,
                TARGET_SEGMENT TEXT);
            CREATE TABLE CAMPAIGN_PERFORMANCE (
                CAMPAIGN_KEY TEXT NOT NULL, CAMPAIGN_NAME TEXT, CHANNEL TEXT,
                TOTAL_SPEND_USD NUMERIC, ACQUIRED_CUSTOMER_COUNT NUMERIC,
                ATTRIBUTED_REVENUE_USD NUMERIC, COST_PER_ACQUISITION_USD NUMERIC,
                RETURN_ON_AD_SPEND NUMERIC);
        """)

    def campaign(self, campaign_id="CMP_1", partner="PTR_1", *, spend=100.0,
                 name="Spring", channel="SEARCH"):
        self.conn.execute(
            "INSERT INTO CAMPAIGN (CAMPAIGN_KEY, PARTNER_ID, CAMPAIGN_ID, CAMPAIGN_NAME,"
            " CHANNEL, TOTAL_SPEND_USD) VALUES (?,?,?,?,?,?)",
            (f"{partner}:{campaign_id}", partner, campaign_id, name, channel, spend))

    def build(self):
        return campaign_performance.build(self.conn, dialect="sqlite")

    def performance(self, columns="*"):
        return self.conn.execute(
            f"SELECT {columns} FROM CAMPAIGN_PERFORMANCE ORDER BY CAMPAIGN_KEY").fetchall()


class CampaignPerformanceTests(CampaignPerformanceCase):
    def test_spend_meets_the_revenue_of_the_customers_it_acquired(self):
        """The join only works because identity resolution ran first."""
        self.campaign(spend=100.0)
        self.customer("EK_1", campaign="CMP_1", partner="PTR_1")
        self.order("ORD_1", customer="EK_1", amount=500.0)
        self.build()
        spend, acquired, revenue = self.performance(
            "TOTAL_SPEND_USD, ACQUIRED_CUSTOMER_COUNT, ATTRIBUTED_REVENUE_USD")[0]
        self.assertEqual((spend, acquired, revenue), (100.0, 1, 500.0))

    def test_two_partners_reusing_a_campaign_id_are_not_credited_with_each_other(self):
        """D22. Joining on CAMPAIGN_ID alone swapped customers between partners."""
        self.campaign("CMP_1", "PTR_1", spend=100.0)
        self.campaign("CMP_1", "PTR_2", spend=900.0)
        self.customer("EK_1", campaign="CMP_1", partner="PTR_1")
        self.customer("EK_2", campaign="CMP_1", partner="PTR_2")
        self.order("ORD_1", customer="EK_1", amount=10.0)
        self.order("ORD_2", customer="EK_2", amount=7000.0)
        self.build()
        revenue = dict(self.performance("CAMPAIGN_KEY, ATTRIBUTED_REVENUE_USD"))
        self.assertEqual(revenue, {"PTR_1:CMP_1": 10.0, "PTR_2:CMP_1": 7000.0})
        acquired = dict(self.performance("CAMPAIGN_KEY, ACQUIRED_CUSTOMER_COUNT"))
        self.assertEqual(acquired, {"PTR_1:CMP_1": 1, "PTR_2:CMP_1": 1})

    def test_several_orders_per_customer_do_not_inflate_the_customer_count(self):
        self.campaign()
        self.customer("EK_1", campaign="CMP_1")
        for n in range(4):
            self.order(f"ORD_{n}", customer="EK_1", amount=25.0)
        self.build()
        acquired, revenue = self.performance(
            "ACQUIRED_CUSTOMER_COUNT, ATTRIBUTED_REVENUE_USD")[0]
        self.assertEqual((acquired, revenue), (1, 100.0))

    def test_cost_per_acquisition_and_return_on_ad_spend(self):
        self.campaign(spend=200.0)
        self.customer("EK_1", campaign="CMP_1")
        self.customer("EK_2", campaign="CMP_1")
        self.order("ORD_1", customer="EK_1", amount=300.0)
        self.order("ORD_2", customer="EK_2", amount=500.0)
        self.build()
        cpa, roas = self.performance("COST_PER_ACQUISITION_USD, RETURN_ON_AD_SPEND")[0]
        self.assertEqual(cpa, 100.0)
        self.assertEqual(roas, 4.0)

    def test_a_campaign_that_acquired_nobody_does_not_divide_by_zero(self):
        """Snowflake raises on division by zero; one such campaign fails the build."""
        self.campaign(spend=200.0)
        self.build()
        acquired, cpa = self.performance(
            "ACQUIRED_CUSTOMER_COUNT, COST_PER_ACQUISITION_USD")[0]
        self.assertEqual(acquired, 0)
        self.assertIsNone(cpa)

    def test_a_campaign_with_no_delivered_cost_has_no_return_on_spend(self):
        self.campaign(spend=None)
        self.customer("EK_1", campaign="CMP_1")
        self.order("ORD_1", customer="EK_1", amount=500.0)
        self.build()
        self.assertIsNone(self.performance("RETURN_ON_AD_SPEND")[0][0])

    def test_a_zero_spend_campaign_has_no_return_on_spend(self):
        self.campaign(spend=0.0)
        self.customer("EK_1", campaign="CMP_1")
        self.order("ORD_1", customer="EK_1", amount=500.0)
        self.build()
        self.assertIsNone(self.performance("RETURN_ON_AD_SPEND")[0][0])

    def test_a_customer_with_no_acquisition_campaign_is_attributed_nowhere(self):
        self.campaign()
        self.customer("EK_1", campaign=None)
        self.order("ORD_1", customer="EK_1", amount=500.0)
        self.build()
        acquired, revenue = self.performance(
            "ACQUIRED_CUSTOMER_COUNT, ATTRIBUTED_REVENUE_USD")[0]
        self.assertEqual(acquired, 0)
        self.assertIsNone(revenue)

    def test_every_campaign_appears_even_with_no_customers(self):
        self.campaign("CMP_1", "PTR_1")
        self.campaign("CMP_2", "PTR_1")
        self.build()
        self.assertEqual(len(self.performance()), 2)

    def test_a_rebuild_is_idempotent(self):
        self.campaign()
        self.customer("EK_1", campaign="CMP_1")
        self.build()
        self.build()
        self.assertEqual(len(self.performance()), 1)


class LifetimeValueCase(CampaignPerformanceCase):
    """proc_AR6brQlFmY. BR-4: net off the customer's SHARE of campaign spend."""

    def setUp(self):
        super().setUp()
        self.conn.executescript("""
            CREATE TABLE CUSTOMER_LIFETIME_VALUE (
                ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL, TOTAL_REVENUE NUMERIC,
                CURRENT_MRR_USD NUMERIC, ORDER_COUNT NUMERIC,
                AVG_ORDER_VALUE_USD NUMERIC, TENURE_DAYS NUMERIC,
                ACQUISITION_COST_USD NUMERIC, NET_LIFETIME_VALUE_USD NUMERIC);
        """)

    def build(self):
        return lifetime_value.build(self.conn, dialect="sqlite")

    def ltv(self, columns="*"):
        return self.conn.execute(
            f"SELECT {columns} FROM CUSTOMER_LIFETIME_VALUE"
            " ORDER BY ENTERPRISE_CUSTOMER_KEY").fetchall()


class LifetimeValueTests(LifetimeValueCase):
    def test_orders_and_subscriptions_do_not_multiply_each_other(self):
        """D21. 4 orders and 2 subscriptions reported 8 orders and twice the revenue."""
        self.customer("EK_1", campaign=None)
        for n in range(4):
            self.order(f"ORD_{n}", amount=100.0)
        for n in range(2):
            self.subscription(f"SUB_{n}", mrr=30.0)
        self.build()
        orders, revenue, mrr = self.ltv("ORDER_COUNT, TOTAL_REVENUE, CURRENT_MRR_USD")[0]
        self.assertEqual((orders, revenue, mrr), (4, 400.0, 60.0))

    def test_average_order_value_is_not_distorted(self):
        self.customer("EK_1", campaign=None)
        self.order("ORD_1", amount=100.0)
        self.order("ORD_2", amount=300.0)
        self.subscription("SUB_1", mrr=30.0)
        self.build()
        self.assertEqual(self.ltv("AVG_ORDER_VALUE_USD")[0][0], 200.0)

    def test_only_revenue_bearing_subscriptions_count(self):
        """BR-1 again: a cancelled plan is not current recurring revenue."""
        self.customer("EK_1", campaign=None)
        self.subscription("SUB_1", state="ACTIVE", mrr=30.0)
        self.subscription("SUB_2", state="CHURNED", mrr=99.0)
        self.build()
        self.assertEqual(self.ltv("CURRENT_MRR_USD")[0][0], 30.0)

    # -- BR-4: acquisition cost is a share, not the whole campaign ---------
    def test_acquisition_cost_is_the_campaigns_cost_per_acquisition(self):
        """The old expression charged the full spend to every acquired customer."""
        self.campaign(spend=300.0)
        self.customer("EK_1", campaign="CMP_1")
        self.customer("EK_2", campaign="CMP_1")
        self.customer("EK_3", campaign="CMP_1")
        self.build()
        costs = [row[0] for row in self.ltv("ACQUISITION_COST_USD")]
        self.assertEqual(costs, [100.0, 100.0, 100.0])

    def test_acquisition_costs_add_back_up_to_the_campaign_spend(self):
        self.campaign(spend=300.0)
        for n in range(3):
            self.customer(f"EK_{n}", campaign="CMP_1")
        self.build()
        total = sum(row[0] for row in self.ltv("ACQUISITION_COST_USD"))
        self.assertEqual(total, 300.0)

    def test_two_partners_reusing_a_campaign_id_do_not_share_spend(self):
        """D22. The campaign is reached by key, not by the partner-scoped id."""
        self.campaign("CMP_1", "PTR_1", spend=100.0)
        self.campaign("CMP_1", "PTR_2", spend=900.0)
        self.customer("EK_1", campaign="CMP_1", partner="PTR_1")
        self.customer("EK_2", campaign="CMP_1", partner="PTR_2")
        self.build()
        costs = dict(self.ltv("ENTERPRISE_CUSTOMER_KEY, ACQUISITION_COST_USD"))
        self.assertEqual(costs, {"EK_1": 100.0, "EK_2": 900.0})

    def test_the_net_includes_current_mrr(self):
        """The old statement computed subscription revenue and then ignored it."""
        self.campaign(spend=50.0)
        self.customer("EK_1", campaign="CMP_1")
        self.order("ORD_1", amount=200.0)
        self.subscription("SUB_1", mrr=30.0)
        self.build()
        self.assertEqual(self.ltv("NET_LIFETIME_VALUE_USD")[0][0], 180.0)

    def test_a_customer_with_no_campaign_has_unknown_cost_and_a_usable_net(self):
        """Propagating the NULL would empty the column for most customers."""
        self.customer("EK_1", campaign=None)
        self.order("ORD_1", amount=200.0)
        self.build()
        cost, net = self.ltv("ACQUISITION_COST_USD, NET_LIFETIME_VALUE_USD")[0]
        self.assertIsNone(cost)
        self.assertEqual(net, 200.0)

    def test_a_customer_with_no_revenue_at_all_still_nets_its_acquisition_cost(self):
        self.campaign(spend=80.0)
        self.customer("EK_1", campaign="CMP_1")
        self.build()
        revenue, net = self.ltv("TOTAL_REVENUE, NET_LIFETIME_VALUE_USD")[0]
        self.assertIsNone(revenue)
        self.assertEqual(net, -80.0)

    def test_a_campaign_with_no_delivered_spend_leaves_cost_unknown(self):
        self.campaign(spend=None)
        self.customer("EK_1", campaign="CMP_1")
        self.order("ORD_1", amount=200.0)
        self.build()
        cost, net = self.ltv("ACQUISITION_COST_USD, NET_LIFETIME_VALUE_USD")[0]
        self.assertIsNone(cost)
        self.assertEqual(net, 200.0)

    def test_one_row_per_customer(self):
        self.customer("EK_1", campaign=None)
        self.customer("EK_2", campaign=None)
        self.order("ORD_1", customer="EK_1")
        self.order("ORD_2", customer="EK_1")
        self.build()
        self.assertEqual(len(self.ltv()), 2)


class RetentionCase(MartCase):
    """proc_F3jEWvf4lM. BR-5: cohort grain, revenue-bearing states."""

    def setUp(self):
        super().setUp()
        self.conn.executescript("""
            CREATE TABLE SUBSCRIPTION_RETENTION (
                COHORT_MONTH TEXT NOT NULL, PLAN_ID TEXT, COHORT_SIZE NUMERIC,
                RETAINED_COUNT NUMERIC, CHURNED_COUNT NUMERIC,
                RETENTION_RATE NUMERIC, RETAINED_MRR_USD NUMERIC);
        """)

    def cohort_subscription(self, key, *, state="ACTIVE", mrr=30.0, plan="PLAN_A",
                            started="2026-01-15 00:00:00"):
        self.conn.execute(
            "INSERT INTO SUBSCRIPTION_FACT VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (key, "EK_1", plan, state, started, None, "2026-03-01 00:00:00",
             "2026-04-01 00:00:00", "USD", mrr, 1, mrr))

    def build(self):
        return retention.build(self.conn, dialect="sqlite")

    def cohorts(self, columns="*"):
        return self.conn.execute(
            f"SELECT {columns} FROM SUBSCRIPTION_RETENTION"
            " ORDER BY COHORT_MONTH, PLAN_ID").fetchall()


class RetentionTests(RetentionCase):
    def test_the_retention_rate_is_a_rate(self):
        """D23. Grouping by state too made it only ever exactly 1.0 or 0.0."""
        self.cohort_subscription("S1", state="ACTIVE")
        self.cohort_subscription("S2", state="ACTIVE")
        self.cohort_subscription("S3", state="CHURNED")
        self.cohort_subscription("S4", state="CHURNED")
        self.build()
        size, retained, churned, rate = self.cohorts(
            "COHORT_SIZE, RETAINED_COUNT, CHURNED_COUNT, RETENTION_RATE")[0]
        self.assertEqual((size, retained, churned), (4, 2, 2))
        self.assertEqual(rate, 0.5)

    def test_one_row_per_cohort_and_plan_not_per_state(self):
        self.cohort_subscription("S1", state="ACTIVE")
        self.cohort_subscription("S2", state="CHURNED")
        self.cohort_subscription("S3", state="PAUSED")
        self.build()
        self.assertEqual(len(self.cohorts()), 1)

    def test_cohort_size_is_the_cohort_not_a_state_slice(self):
        for n in range(5):
            self.cohort_subscription(f"S{n}", state="CHURNED")
        self.cohort_subscription("S9", state="ACTIVE")
        self.build()
        self.assertEqual(self.cohorts("COHORT_SIZE")[0][0], 6)

    def test_cohorts_split_by_start_month_and_plan(self):
        self.cohort_subscription("S1", started="2026-01-15 00:00:00", plan="PLAN_A")
        self.cohort_subscription("S2", started="2026-02-15 00:00:00", plan="PLAN_A")
        self.cohort_subscription("S3", started="2026-01-20 00:00:00", plan="PLAN_B")
        self.build()
        keys = self.cohorts("COHORT_MONTH, PLAN_ID")
        self.assertEqual(keys, [("2026-01-01", "PLAN_A"), ("2026-01-01", "PLAN_B"),
                                ("2026-02-01", "PLAN_A")])

    # -- BR-5: retained means revenue-bearing ------------------------------
    def test_at_risk_counts_as_retained(self):
        self.cohort_subscription("S1", state="AT_RISK")
        self.build()
        self.assertEqual(self.cohorts("RETAINED_COUNT")[0][0], 1)

    def test_trial_and_paused_are_neither_retained_nor_churned(self):
        """Not paying, so not retained; not cancelled, so not churned."""
        self.cohort_subscription("S1", state="ACTIVE")
        self.cohort_subscription("S2", state="TRIAL")
        self.cohort_subscription("S3", state="PAUSED")
        self.cohort_subscription("S4", state="CHURNED")
        self.build()
        size, retained, churned = self.cohorts(
            "COHORT_SIZE, RETAINED_COUNT, CHURNED_COUNT")[0]
        self.assertEqual((size, retained, churned), (4, 1, 1))
        self.assertNotEqual(retained + churned, size)

    def test_retained_mrr_excludes_the_churned(self):
        """It used to report churned subscriptions' MRR under a retained column."""
        self.cohort_subscription("S1", state="ACTIVE", mrr=30.0)
        self.cohort_subscription("S2", state="CHURNED", mrr=500.0)
        self.cohort_subscription("S3", state="TRIAL", mrr=700.0)
        self.build()
        self.assertEqual(self.cohorts("RETAINED_MRR_USD")[0][0], 30.0)

    def test_a_fully_churned_cohort_reports_zero_not_null(self):
        self.cohort_subscription("S1", state="CHURNED", mrr=30.0)
        self.build()
        rate, mrr = self.cohorts("RETENTION_RATE, RETAINED_MRR_USD")[0]
        self.assertEqual((rate, mrr), (0.0, 0.0))

    def test_a_subscription_with_no_start_has_no_cohort(self):
        self.cohort_subscription("S1", started=None)
        self.build()
        self.assertEqual(self.cohorts(), [])

    def test_the_mart_carries_no_customer_identifier(self):
        self.cohort_subscription("S1")
        self.build()
        columns = [d[0] for d in self.conn.execute(
            "SELECT * FROM SUBSCRIPTION_RETENTION").description]
        self.assertNotIn("ENTERPRISE_CUSTOMER_KEY", columns)

    def test_a_rebuild_is_idempotent(self):
        self.cohort_subscription("S1")
        self.build()
        self.build()
        self.assertEqual(len(self.cohorts()), 1)


if __name__ == "__main__":
    unittest.main()
