"""Validation for PostgreSQL Subscription and MySQL Support ingestion, and the
CORE support build.

Two things here are unlike anything earlier in the platform:

* subscription events advance on an **id high-water mark** read from the target,
  not a time window;
* support tickets land **twice** in their life, so the CORE build's deduplication
  is what keeps RESOLUTION_SECONDS from being half nulls.
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines import (  # noqa: E402
    core_support, mysql_support_ingestion, postgres_subscription_ingestion, snowflake_sqlite,
)

T0 = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)
HOUR = timedelta(hours=1)
TZ = "UTC"


def _source() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE subscriptions (
            subscription_id TEXT, crm_customer_ref TEXT, billing_email TEXT, plan_id TEXT,
            subscription_status TEXT, started_at TIMESTAMP, current_period_start TIMESTAMP,
            current_period_end TIMESTAMP, canceled_at TIMESTAMP, mrr_amount NUMERIC,
            currency_code TEXT, updated_at TIMESTAMP);
        CREATE TABLE subscription_events (
            event_id INTEGER, subscription_id TEXT, event_type TEXT, status TEXT,
            event_at TIMESTAMP, source_channel TEXT);
        CREATE TABLE support_tickets (
            ticket_id INTEGER, support_customer_ref TEXT, contact_email TEXT,
            ticket_status TEXT, priority TEXT, category_code TEXT, created_at TIMESTAMP,
            resolved_at TIMESTAMP, channel TEXT);
        CREATE TABLE support_interactions (
            interaction_id INTEGER, ticket_id INTEGER, interaction_type TEXT, agent_id TEXT,
            interaction_at TIMESTAMP, duration_seconds INTEGER, note_text TEXT);
        """
    )
    return conn


def _warehouse() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    snowflake_sqlite.register(conn)
    conn.executescript(
        """
        CREATE TABLE RAW_PARTNER_ACQUISITION_COST (
            CAMPAIGN_ID TEXT, PARTNER_ID TEXT, COST_DATE TEXT, ACQUISITION_COST NUMERIC,
            CURRENCY_CODE TEXT, _INGESTED_AT TEXT);
        CREATE TABLE RAW_SUBSCRIPTIONS (
            SUBSCRIPTION_ID TEXT NOT NULL, CRM_CUSTOMER_REF TEXT NOT NULL, BILLING_EMAIL TEXT,
            PLAN_ID TEXT, SUBSCRIPTION_STATUS TEXT, STARTED_AT TIMESTAMP,
            CURRENT_PERIOD_START TIMESTAMP, CURRENT_PERIOD_END TIMESTAMP,
            CANCELED_AT TIMESTAMP, MRR_AMOUNT NUMERIC, CURRENCY_CODE TEXT,
            UPDATED_AT TIMESTAMP, _SOURCE_SYSTEM TEXT NOT NULL, _INGESTED_AT TIMESTAMP NOT NULL,
            _INGESTION_JOB_ID TEXT NOT NULL, _BATCH_ID TEXT);
        CREATE TABLE RAW_SUBSCRIPTION_EVENTS (
            EVENT_ID NUMERIC NOT NULL, SUBSCRIPTION_ID TEXT NOT NULL, EVENT_TYPE TEXT,
            STATUS TEXT, EVENT_AT TIMESTAMP, SOURCE_CHANNEL TEXT,
            _SOURCE_SYSTEM TEXT NOT NULL, _INGESTED_AT TIMESTAMP NOT NULL,
            _INGESTION_JOB_ID TEXT NOT NULL, _BATCH_ID TEXT);
        CREATE TABLE RAW_SUPPORT_TICKETS (
            TICKET_ID NUMERIC NOT NULL, SUPPORT_CUSTOMER_REF TEXT NOT NULL, CONTACT_EMAIL TEXT,
            TICKET_STATUS TEXT, PRIORITY TEXT, CATEGORY_CODE TEXT, CREATED_AT TIMESTAMP,
            RESOLVED_AT TIMESTAMP, CHANNEL TEXT, _SOURCE_SYSTEM TEXT NOT NULL,
            _INGESTED_AT TIMESTAMP NOT NULL, _INGESTION_JOB_ID TEXT NOT NULL, _BATCH_ID TEXT);
        CREATE TABLE RAW_SUPPORT_INTERACTIONS (
            INTERACTION_ID NUMERIC NOT NULL, TICKET_ID NUMERIC NOT NULL, INTERACTION_TYPE TEXT,
            AGENT_ID TEXT, INTERACTION_AT TIMESTAMP, DURATION_SECONDS NUMERIC,
            _SOURCE_SYSTEM TEXT NOT NULL, _INGESTED_AT TIMESTAMP NOT NULL,
            _INGESTION_JOB_ID TEXT NOT NULL, _BATCH_ID TEXT);
        CREATE TABLE RAW_ORDERS (
            ORDER_ID NUMERIC, CUSTOMER_ID NUMERIC, ORDER_STATUS TEXT, ORDER_DATE TEXT,
            CURRENCY_CODE TEXT, TOTAL_AMOUNT REAL, CHANNEL_CODE TEXT, UPDATED_AT TEXT,
            _SOURCE_SYSTEM TEXT, _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
        CREATE TABLE RAW_PAYMENTS (
            PAYMENT_ID NUMERIC, ORDER_ID NUMERIC, PAYMENT_METHOD TEXT, PAYMENT_STATUS TEXT,
            PAYMENT_AMOUNT REAL, CURRENCY_CODE TEXT, PAID_AT TEXT, _SOURCE_SYSTEM TEXT,
            _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
        CREATE TABLE FX_RATE_DAILY (
            RATE_DATE TEXT NOT NULL, FROM_CURRENCY TEXT NOT NULL,
            TO_CURRENCY TEXT NOT NULL, FX_RATE REAL NOT NULL);
        CREATE TABLE FX_COVERAGE_GAP (
            REQUIRED_CURRENCY TEXT NOT NULL, REQUIRED_DATE TEXT NOT NULL,
            SOURCE_TABLE TEXT NOT NULL, AFFECTED_ROW_COUNT NUMERIC NOT NULL,
            DETECTED_AT TEXT NOT NULL);
        CREATE TABLE SUBSCRIPTION_FACT (
            SUBSCRIPTION_KEY TEXT NOT NULL PRIMARY KEY, ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL,
            PLAN_ID TEXT, LIFECYCLE_STATE TEXT, STARTED_AT_UTC TEXT, CANCELED_AT_UTC TEXT,
            CURRENT_PERIOD_START_UTC TEXT, CURRENT_PERIOD_END_UTC TEXT,
            SOURCE_CURRENCY_CODE TEXT, MRR_AMOUNT_SOURCE REAL,
            FX_RATE_APPLIED REAL NOT NULL, MRR_USD REAL NOT NULL);
        CREATE TABLE CUSTOMER_IDENTITY_MAP (
            ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL, SOURCE_SYSTEM TEXT NOT NULL,
            SOURCE_CUSTOMER_REF TEXT NOT NULL, EMAIL_NORMALIZED TEXT, EMAIL_HASH TEXT,
            MATCH_METHOD TEXT NOT NULL, MATCH_CONFIDENCE REAL, RESOLVED_AT TEXT NOT NULL,
            IS_ACTIVE BOOLEAN);
        CREATE TABLE SUPPORT_INTERACTION_FACT (
            TICKET_KEY TEXT NOT NULL PRIMARY KEY, ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL,
            TICKET_STATUS TEXT, PRIORITY TEXT, CATEGORY_CODE TEXT,
            CREATED_AT_UTC TEXT NOT NULL, RESOLVED_AT_UTC TEXT, RESOLUTION_SECONDS NUMERIC,
            IS_RESOLVED BOOLEAN, CHANNEL TEXT);
        INSERT INTO CUSTOMER_IDENTITY_MAP VALUES
            ('CUST_KEY_1','MYSQL_SUPPORT','SUP_1','a@example.com','h','EMAIL_NORMALIZED',
             0.95,'2026-03-01 04:00:00',1);
        INSERT INTO CUSTOMER_IDENTITY_MAP VALUES
            ('CUST_KEY_1','POSTGRES_SUBSCRIPTION','CRM_1','a@example.com','h',
             'EMAIL_NORMALIZED',1.0,'2026-03-01 04:00:00',1);
        """
    )
    return conn


class Base(unittest.TestCase):
    def setUp(self):
        self.source, self.target = _source(), _warehouse()

    def tearDown(self):
        self.source.close()
        self.target.close()

    def raw(self, table, columns="*"):
        return self.target.execute(f"SELECT {columns} FROM {table}").fetchall()


class SubscriptionIngestionTests(Base):
    def subscription(self, sub_id, *, ref="CRM_1", updated=T0 + HOUR / 2, mrr=99.0):
        self.source.execute("INSERT INTO subscriptions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (sub_id, ref, "a@example.com", "PLAN_A", "ACTIVE", T0,
                             T0, T0 + 30 * 24 * HOUR, None, mrr, "EUR", updated))

    def event(self, event_id, sub_id="SUB_1"):
        self.source.execute("INSERT INTO subscription_events VALUES (?,?,?,?,?,?)",
                            (event_id, sub_id, "RENEWED", "ACTIVE", T0, "SYSTEM"))

    def ingest(self, start=T0, end=T0 + HOUR, batch_id="run_a"):
        return postgres_subscription_ingestion.run(
            self.source, self.target, window_start=start, window_end=end, batch_id=batch_id)

    def test_subscriptions_are_windowed_on_updated_at(self):
        self.subscription("SUB_1", updated=T0 + HOUR / 2)
        self.subscription("SUB_2", updated=T0 + 5 * HOUR)
        self.ingest()
        self.assertEqual([r[0] for r in self.raw("RAW_SUBSCRIPTIONS", "SUBSCRIPTION_ID")],
                         ["SUB_1"])

    def test_the_event_high_water_mark_starts_at_zero(self):
        self.assertEqual(postgres_subscription_ingestion.last_event_id(self.target), 0)

    def test_events_advance_on_the_id_mark_not_the_window(self):
        """Events outside the time window still land; already-landed ones do not."""
        self.event(1); self.event(2)
        first = self.ingest(batch_id="run_a")
        self.assertEqual(first.rows_into("RAW_SUBSCRIPTION_EVENTS"), 2)

        self.event(3)
        second = self.ingest(batch_id="run_b")
        self.assertEqual(second.rows_into("RAW_SUBSCRIPTION_EVENTS"), 1,
                         "only the new event, and no time window was involved")
        self.assertEqual(sorted(r[0] for r in self.raw("RAW_SUBSCRIPTION_EVENTS", "EVENT_ID")),
                         [1, 2, 3])

    def test_the_mark_is_read_from_the_landed_data(self):
        self.event(1); self.event(2)
        self.ingest()
        self.assertEqual(postgres_subscription_ingestion.last_event_id(self.target), 2)

    def test_rerunning_with_no_new_events_lands_nothing(self):
        self.event(1)
        self.ingest(batch_id="run_a")
        again = self.ingest(batch_id="run_b")
        self.assertEqual(again.rows_into("RAW_SUBSCRIPTION_EVENTS"), 0)

    def test_metadata_is_stamped_on_both_tables(self):
        self.subscription("SUB_1"); self.event(1)
        self.ingest(batch_id="run_a")
        for table in ("RAW_SUBSCRIPTIONS", "RAW_SUBSCRIPTION_EVENTS"):
            system, job, batch = self.raw(
                table, "_SOURCE_SYSTEM, _INGESTION_JOB_ID, _BATCH_ID")[0]
            self.assertEqual(system, "POSTGRES_SUBSCRIPTION")
            self.assertEqual(job, postgres_subscription_ingestion.INGESTION_JOB_ID)
            self.assertEqual(batch, "run_a")


class SupportIngestionTests(Base):
    def ticket(self, ticket_id, *, ref="SUP_1", created=T0 + HOUR / 2, resolved=None,
               status="OPEN"):
        self.source.execute("INSERT INTO support_tickets VALUES (?,?,?,?,?,?,?,?,?)",
                            (ticket_id, ref, "a@example.com", status, "P2", "BILLING",
                             created, resolved, "EMAIL"))

    def interaction(self, interaction_id, ticket_id, *, at=T0 + HOUR / 2):
        self.source.execute("INSERT INTO support_interactions VALUES (?,?,?,?,?,?,?)",
                            (interaction_id, ticket_id, "REPLY", "AGENT_9", at, 120,
                             "customer said something private"))

    def ingest(self, start=T0, end=T0 + HOUR, batch_id="run_a"):
        return mysql_support_ingestion.run(self.source, self.target, window_start=start,
                                           window_end=end, batch_id=batch_id)

    def test_a_ticket_lands_again_when_it_is_resolved(self):
        """Windowing on created_at alone would leave RESOLVED_AT permanently null."""
        self.ticket(1, created=T0 + HOUR / 2)
        self.ingest(batch_id="run_a")
        self.source.execute("UPDATE support_tickets SET resolved_at=?, ticket_status='CLOSED'"
                            " WHERE ticket_id=1", (T0 + 5 * HOUR + HOUR / 2,))
        self.ingest(start=T0 + 5 * HOUR, end=T0 + 6 * HOUR, batch_id="run_b")
        landings = self.raw("RAW_SUPPORT_TICKETS", "RESOLVED_AT, _BATCH_ID")
        self.assertEqual(len(landings), 2)
        self.assertIsNone(landings[0][0])
        self.assertIsNotNone(landings[1][0])

    def test_interactions_are_windowed_on_interaction_at(self):
        self.interaction(10, 1, at=T0 + HOUR / 2)
        self.interaction(11, 1, at=T0 + 5 * HOUR)
        self.ingest()
        self.assertEqual([r[0] for r in self.raw("RAW_SUPPORT_INTERACTIONS", "INTERACTION_ID")],
                         [10])

    def test_note_text_never_reaches_the_warehouse(self):
        self.interaction(10, 1)
        self.ingest()
        landed = [str(v) for v in self.raw("RAW_SUPPORT_INTERACTIONS")[0]]
        self.assertNotIn("customer said something private", landed)


class CoreSupportBuildTests(Base):
    def land(self, ticket_id, *, ref="SUP_1", created="2026-03-01 09:00:00", resolved=None,
             status="OPEN", ingested="2026-03-01 10:00:00", batch="run_a"):
        self.target.execute("INSERT INTO RAW_SUPPORT_TICKETS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (ticket_id, ref, "a@example.com", status, "P2", "BILLING",
                             created, resolved, "EMAIL", "MYSQL_SUPPORT", ingested,
                             "dag_ingest_mysql_support", batch))

    def build(self, tz=TZ):
        return core_support.run(self.target, mysql_server_timezone=tz, dialect="sqlite")

    def fact(self, columns="*"):
        return self.target.execute(f"SELECT {columns} FROM SUPPORT_INTERACTION_FACT").fetchall()

    def test_a_twice_landed_ticket_yields_one_resolved_row(self):
        """The defect this dedup exists to prevent: two rows, one with a null duration."""
        self.land(1, ingested="2026-03-01 10:00:00", batch="run_a")
        self.land(1, resolved="2026-03-01 12:30:00", status="CLOSED",
                  ingested="2026-03-01 13:00:00", batch="run_b")
        self.build()
        rows = self.fact("TICKET_KEY, RESOLUTION_SECONDS, IS_RESOLVED")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], 12600)   # 3h30m
        self.assertTrue(rows[0][2])

    def test_a_reopened_ticket_takes_the_latest_landing(self):
        self.land(1, resolved="2026-03-01 12:30:00", status="CLOSED",
                  ingested="2026-03-01 13:00:00", batch="run_b")
        self.land(1, resolved=None, status="OPEN",
                  ingested="2026-03-01 15:00:00", batch="run_c")
        self.build()
        self.assertEqual(self.fact("TICKET_STATUS, IS_RESOLVED")[0], ("OPEN", 0))

    def test_unresolved_tickets_have_a_null_duration_not_zero(self):
        """Zero would drag the average down; null cannot."""
        self.land(1)
        self.build()
        self.assertIsNone(self.fact("RESOLUTION_SECONDS")[0][0])

    def test_status_vocabulary_is_mapped(self):
        for n, (src, want) in enumerate(
                [("NEW", "OPEN"), ("PENDING_CUSTOMER", "WAITING"),
                 ("ESCALATED", "ESCALATED"), ("CLOSED", "RESOLVED")], start=1):
            self.land(n, status=src)
        self.build()
        got = dict(self.fact("TICKET_KEY, TICKET_STATUS"))
        self.assertEqual(got["2"], "WAITING")
        self.assertEqual(got["4"], "RESOLVED")

    def test_identity_join_is_scoped_to_mysql(self):
        """A partner reference that looks like a support ref must not match."""
        self.target.execute("INSERT INTO CUSTOMER_IDENTITY_MAP VALUES"
                            " ('WRONG','PARTNER_LANDING','SUP_1','x','h','PARTNER_DECLARED',"
                            "0.8,'2026-03-01 04:00:00',1)")
        self.land(1)
        self.build()
        self.assertEqual(self.fact("ENTERPRISE_CUSTOMER_KEY"), [("CUST_KEY_1",)])

    def test_the_source_zone_is_a_real_parameter(self):
        """Both timestamps shift together, so the duration is unchanged -- but the
        absolute UTC times must move, or the parameter is being ignored."""
        self.land(1, created="2026-01-15 09:00:00", resolved="2026-01-15 10:00:00")
        self.build(tz="America/Chicago")
        created, seconds = self.fact("CREATED_AT_UTC, RESOLUTION_SECONDS")[0]
        self.assertEqual(created, "2026-01-15 15:00:00")
        self.assertEqual(seconds, 3600)

    def test_rebuild_is_idempotent(self):
        self.land(1)
        first = self.build()
        second = self.build()
        self.assertEqual(first.target_rows, second.target_rows)
        self.assertEqual(second.target_rows["SUPPORT_INTERACTION_FACT"], 1)


class CoreSubscriptionBuildTests(Base):
    """MRR converts on the billing period start -- the period the revenue belongs to."""

    def land(self, sub_id="SUB_1", *, ref="CRM_1", currency="EUR", mrr=100.0,
             started="2026-01-10 00:00:00", period_start="2026-03-01 00:00:00",
             period_end="2026-04-01 00:00:00", status="ACTIVE",
             updated="2026-03-02 00:00:00", ingested="2026-03-02 01:00:00", batch="run_a"):
        self.target.execute(
            "INSERT INTO RAW_SUBSCRIPTIONS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (sub_id, ref, "a@example.com", "PLAN_A", status, started, period_start,
             period_end, None, mrr, currency, updated, "POSTGRES_SUBSCRIPTION",
             ingested, "dag_ingest_postgres_subscriptions", batch))

    def rate(self, date, value, *, currency="EUR"):
        self.target.execute("INSERT INTO FX_RATE_DAILY VALUES (?,?,?,?)",
                            (date, currency, "USD", value))

    def build(self):
        from pipelines import core_subscription
        return core_subscription.build(self.target, postgres_server_timezone=TZ,
                                       dialect="sqlite")

    def fact(self, columns="*"):
        return self.target.execute(f"SELECT {columns} FROM SUBSCRIPTION_FACT").fetchall()

    def test_the_billing_period_start_rate_is_used(self):
        """Not the started_at rate and not the updated_at rate -- the period's own."""
        self.land(started="2026-01-10 00:00:00", period_start="2026-03-01 00:00:00",
                  updated="2026-03-02 00:00:00", mrr=100.0)
        self.rate("2026-01-10", 1.50)   # when the subscription began
        self.rate("2026-03-01", 1.08)   # the billing period this MRR belongs to
        self.rate("2026-03-02", 1.20)   # when the row was last updated
        self.build()
        source, applied, usd = self.fact(
            "MRR_AMOUNT_SOURCE, FX_RATE_APPLIED, MRR_USD")[0]
        self.assertEqual((source, applied, usd), (100.0, 1.08, 108.0))

    def test_the_conversion_date_is_recorded_on_the_fact(self):
        """Without it nobody can tell which rate applied."""
        self.land(period_start="2026-03-01 00:00:00")
        self.rate("2026-03-01", 1.08)
        self.build()
        self.assertEqual(self.fact("CURRENT_PERIOD_START_UTC")[0][0], "2026-03-01 00:00:00")

    def test_a_missing_period_start_rate_blocks_the_build(self):
        from pipelines.fx_coverage import FxCoverageError
        self.land(period_start="2026-03-01 00:00:00")
        self.rate("2026-03-02", 1.20)   # a rate exists, but not for the period start
        with self.assertRaises(FxCoverageError) as caught:
            self.build()
        self.assertEqual([(g.currency, g.date, g.source_table) for g in caught.exception.gaps],
                         [("EUR", "2026-03-01", "RAW_SUBSCRIPTIONS")])
        self.assertEqual(self.fact(), [], "nothing published")

    def test_a_missing_order_rate_does_not_block_subscriptions(self):
        """The gate is per build. SOURCE_TABLE keeps the revenue streams separate."""
        self.land(period_start="2026-03-01 00:00:00")
        self.rate("2026-03-01", 1.08)
        self.target.execute(
            "INSERT INTO RAW_ORDERS VALUES (1,7,'PAID','2026-03-01 10:00:00','JPY',500.0,"
            "'WEB','2026-03-01 10:00:00','ORACLE_SALES','2026-03-01 11:00:00','j','b1')")
        self.build()   # must not raise
        self.assertEqual(len(self.fact()), 1)

    def test_usd_subscriptions_need_no_rate(self):
        self.land(currency="USD", mrr=250.0)
        self.build()
        self.assertEqual(self.fact("FX_RATE_APPLIED, MRR_USD")[0], (1.0, 250.0))

    def test_append_only_versions_collapse_to_the_latest(self):
        self.land(mrr=100.0, status="ACTIVE", updated="2026-03-02 00:00:00",
                  ingested="2026-03-02 01:00:00")
        self.land(mrr=150.0, status="PAST_DUE", updated="2026-03-05 00:00:00",
                  ingested="2026-03-05 01:00:00", batch="run_b")
        self.rate("2026-03-01", 1.08)
        self.build()
        rows = self.fact("MRR_AMOUNT_SOURCE, LIFECYCLE_STATE")
        self.assertEqual(rows, [(150.0, "AT_RISK")])

    def test_lifecycle_vocabulary_is_mapped(self):
        for n, (src, want) in enumerate(
                [("TRIALING", "TRIAL"), ("PAST_DUE", "AT_RISK"),
                 ("PAUSED", "PAUSED"), ("CANCELED", "CHURNED")], start=1):
            self.land(f"SUB_{n}", currency="USD", status=src)
        self.build()
        got = dict(self.fact("SUBSCRIPTION_KEY, LIFECYCLE_STATE"))
        self.assertEqual(got["SUB_1"], "TRIAL")
        self.assertEqual(got["SUB_2"], "AT_RISK")
        self.assertEqual(got["SUB_4"], "CHURNED")

    def test_identity_join_is_scoped_to_postgres(self):
        self.target.execute("INSERT INTO CUSTOMER_IDENTITY_MAP VALUES"
                            " ('WRONG','PARTNER_LANDING','CRM_1','x','h','PARTNER_DECLARED',"
                            "0.8,'2026-03-01 04:00:00',1)")
        self.land(currency="USD")
        self.build()
        self.assertEqual(self.fact("ENTERPRISE_CUSTOMER_KEY"), [("CUST_KEY_1",)])

    def test_not_null_backstop_fires_if_the_gate_is_bypassed(self):
        from pipelines import core_subscription, sql_runner
        self.land(currency="EUR")   # no rate, and we skip the assertion
        with self.assertRaises(sqlite3.IntegrityError):
            sql_runner.run(self.target, sql_dir=core_subscription.SQL_DIR,
                           parameters={"postgres_server_timezone": TZ},
                           dialect="sqlite", rebuild=True)

    def test_rebuild_is_idempotent(self):
        self.land(currency="USD")
        first = self.build()
        second = self.build()
        self.assertEqual(first.target_rows, second.target_rows)
        self.assertEqual(second.target_rows["SUBSCRIPTION_FACT"], 1)


class EndToEndTests(Base):
    """MySQL -> RAW -> CORE, with the double landing the design depends on."""

    def test_a_ticket_created_then_resolved_produces_one_correct_fact_row(self):
        self.source.execute("INSERT INTO support_tickets VALUES (?,?,?,?,?,?,?,?,?)",
                            (1, "SUP_1", "a@example.com", "OPEN", "P1", "BILLING",
                             T0 + HOUR / 2, None, "EMAIL"))
        mysql_support_ingestion.run(self.source, self.target, window_start=T0,
                                    window_end=T0 + HOUR, batch_id="run_a")
        self.source.execute("UPDATE support_tickets SET resolved_at=?, ticket_status='CLOSED'"
                            " WHERE ticket_id=1", (T0 + 2 * HOUR + HOUR / 2,))
        mysql_support_ingestion.run(self.source, self.target, window_start=T0 + 2 * HOUR,
                                    window_end=T0 + 3 * HOUR, batch_id="run_b")

        self.assertEqual(len(self.raw("RAW_SUPPORT_TICKETS")), 2, "RAW keeps both landings")
        core_support.run(self.target, mysql_server_timezone=TZ, dialect="sqlite")
        rows = self.target.execute(
            "SELECT TICKET_KEY, TICKET_STATUS, RESOLUTION_SECONDS, IS_RESOLVED"
            " FROM SUPPORT_INTERACTION_FACT").fetchall()
        self.assertEqual(len(rows), 1, "CORE collapses them to one")
        self.assertEqual(rows[0][1], "RESOLVED")
        self.assertEqual(rows[0][2], 7200)   # 00:30 -> 02:30
        self.assertTrue(rows[0][3])


if __name__ == "__main__":
    unittest.main(verbosity=2)
