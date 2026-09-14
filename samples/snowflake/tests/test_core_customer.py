"""Validation for the CORE customer spine (proc_j3HyTdoXBh, proc_PASXcCWvuz).

Executes the modeled Snowflake SQL against SQLite fixtures through the dialect
shim. The point is to make the identity-resolution decisions *executable*: that
deduplication happens per source customer reference, that customers without an
email are excluded rather than crashing the build, that four systems collapse to
one enterprise key, and that the rebuild is idempotent.
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines import snowflake_sqlite  # noqa: E402
from pipelines.core_customer import run  # noqa: E402

ORACLE_TZ = "UTC"  # the sample's explicit configuration assumption; verify in a real environment

ORACLE, POSTGRES, MYSQL, PARTNER = (
    "ORACLE_SALES", "POSTGRES_SUBSCRIPTION", "MYSQL_SUPPORT", "PARTNER_LANDING",
)


def key(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode()).hexdigest()


def email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


class CoreSpineCase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        snowflake_sqlite.register(self.conn)
        self.conn.executescript(
            """
            CREATE TABLE RAW_CUSTOMERS (
                CUSTOMER_ID INTEGER, CUSTOMER_NAME TEXT, EMAIL TEXT, PHONE_NUMBER TEXT,
                BILLING_ADDRESS TEXT, COUNTRY_CODE TEXT, CUSTOMER_STATUS TEXT,
                CREATED_AT TEXT, UPDATED_AT TEXT, _SOURCE_SYSTEM TEXT,
                _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE RAW_PARTNER_ACQUISITION_COST (
                CAMPAIGN_ID TEXT, PARTNER_ID TEXT, COST_DATE TEXT, ACQUISITION_COST NUMERIC,
                CURRENCY_CODE TEXT, _INGESTED_AT TEXT);
            CREATE TABLE RAW_SUBSCRIPTIONS (
                SUBSCRIPTION_ID TEXT, CRM_CUSTOMER_REF TEXT, BILLING_EMAIL TEXT, PLAN_ID TEXT,
                SUBSCRIPTION_STATUS TEXT, STARTED_AT TEXT, CURRENT_PERIOD_START TEXT,
                CURRENT_PERIOD_END TEXT, CANCELED_AT TEXT, MRR_AMOUNT REAL, CURRENCY_CODE TEXT,
                UPDATED_AT TEXT, _SOURCE_SYSTEM TEXT, _INGESTED_AT TEXT,
                _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE RAW_SUPPORT_TICKETS (
                TICKET_ID TEXT, SUPPORT_CUSTOMER_REF TEXT, CONTACT_EMAIL TEXT, TICKET_STATUS TEXT,
                PRIORITY TEXT, CATEGORY_CODE TEXT, CREATED_AT TEXT, RESOLVED_AT TEXT, CHANNEL TEXT,
                _SOURCE_SYSTEM TEXT, _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE RAW_PARTNER_CUSTOMER_MAP (
                PARTNER_CUSTOMER_ID TEXT, PARTNER_ID TEXT, EMAIL TEXT, SIGNUP_AT TEXT,
                FIRST_TOUCH_CAMPAIGN_ID TEXT, _SOURCE_FILE TEXT, _SOURCE_SYSTEM TEXT,
                _INGESTED_AT TEXT, _INGESTION_JOB_ID TEXT, _BATCH_ID TEXT);
            CREATE TABLE CUSTOMER_IDENTITY_MAP (
                ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL, SOURCE_SYSTEM TEXT NOT NULL,
                SOURCE_CUSTOMER_REF TEXT NOT NULL, EMAIL_NORMALIZED TEXT, EMAIL_HASH TEXT,
                MATCH_METHOD TEXT NOT NULL, MATCH_CONFIDENCE REAL,
                RESOLVED_AT TEXT NOT NULL, IS_ACTIVE BOOLEAN);
            CREATE TABLE CUSTOMER (
                ENTERPRISE_CUSTOMER_KEY TEXT NOT NULL PRIMARY KEY, CUSTOMER_NAME TEXT,
                EMAIL TEXT, EMAIL_HASH TEXT, PHONE_NUMBER TEXT, BILLING_COUNTRY_CODE TEXT,
                CUSTOMER_STATUS TEXT, FIRST_SEEN_AT_UTC TEXT, ACQUISITION_CAMPAIGN_ID TEXT,
    ACQUISITION_CAMPAIGN_KEY TEXT,
                SOURCE_SYSTEM_COUNT INTEGER);
            """
        )

    def tearDown(self):
        self.conn.close()

    # -- fixture helpers -------------------------------------------------
    def oracle(self, cid, email, *, name="Ada Lovelace", status="ACTIVE",
               created="2026-01-15 09:30:00", updated="2026-03-01 10:00:00",
               ingested="2026-03-01 10:05:00", country="US"):
        self.conn.execute(
            "INSERT INTO RAW_CUSTOMERS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (cid, name, email, "+1-555-0100", "1 Example St", country, status,
             created, updated, ORACLE, ingested, "dag_ingest_oracle_customers", "b1"))

    def subscription(self, sub_id, crm_ref, email, *, updated="2026-03-01 10:00:00",
                     ingested="2026-03-01 10:05:00"):
        self.conn.execute(
            "INSERT INTO RAW_SUBSCRIPTIONS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (sub_id, crm_ref, email, "PLAN_A", "ACTIVE", "2026-01-01", "2026-03-01",
             "2026-04-01", None, 99.0, "USD", updated, POSTGRES, ingested,
             "dag_ingest_postgres_subscriptions", "b1"))

    def ticket(self, ticket_id, support_ref, email, *, created="2026-03-01 10:00:00",
               ingested="2026-03-01 10:05:00"):
        self.conn.execute(
            "INSERT INTO RAW_SUPPORT_TICKETS VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ticket_id, support_ref, email, "OPEN", "P2", "BILLING", created, None,
             "EMAIL", MYSQL, ingested, "dag_ingest_mysql_support", "b1"))

    def partner(self, partner_customer_id, email, *, campaign="CMP_1",
                partner_id="PTR_1", signup="2026-01-05 08:00:00",
                ingested="2026-03-01 03:05:00", batch="b1"):
        self.conn.execute(
            "INSERT INTO RAW_PARTNER_CUSTOMER_MAP VALUES (?,?,?,?,?,?,?,?,?,?)",
            (partner_customer_id, partner_id, email, signup, campaign, "f.csv",
             PARTNER, ingested, "dag_ingest_partner_files", batch))

    def build(self, oracle_server_timezone=ORACLE_TZ):
        return run(self.conn, oracle_server_timezone=oracle_server_timezone, dialect="sqlite")

    def identity_rows(self, **where):
        sql = "SELECT SOURCE_SYSTEM, SOURCE_CUSTOMER_REF, ENTERPRISE_CUSTOMER_KEY, MATCH_METHOD, MATCH_CONFIDENCE, IS_ACTIVE FROM CUSTOMER_IDENTITY_MAP"
        if where:
            sql += " WHERE " + " AND ".join(f"{k}=?" for k in where)
        return self.conn.execute(sql, tuple(where.values())).fetchall()

    def customers(self, columns="*"):
        return self.conn.execute(f"SELECT {columns} FROM CUSTOMER").fetchall()


class IdentityResolutionTests(CoreSpineCase):
    def test_append_only_versions_collapse_to_one_crosswalk_row(self):
        """Three landed versions of one customer are one identity, not three."""
        for n, updated in enumerate(["2026-03-01 10:00:00", "2026-03-02 10:00:00",
                                     "2026-03-03 10:00:00"]):
            self.oracle(1, "ada@example.com", updated=updated,
                        ingested=f"2026-03-0{n+1} 10:05:00")
        self.build()
        rows = self.identity_rows(SOURCE_SYSTEM=ORACLE)
        self.assertEqual(len(rows), 1)

    def test_many_subscriptions_per_customer_collapse(self):
        """Partitioning on the subscription key would emit one row per subscription."""
        self.subscription("SUB_1", "CRM_9", "ada@example.com")
        self.subscription("SUB_2", "CRM_9", "ada@example.com")
        self.subscription("SUB_3", "CRM_9", "ada@example.com")
        self.build()
        self.assertEqual(len(self.identity_rows(SOURCE_SYSTEM=POSTGRES)), 1)

    def test_many_tickets_per_customer_collapse(self):
        """The largest fan-out risk: a customer raises many tickets."""
        for i in range(1, 8):
            self.ticket(f"TCK_{i}", "SUP_5", "ada@example.com")
        self.build()
        self.assertEqual(len(self.identity_rows(SOURCE_SYSTEM=MYSQL)), 1)

    def test_four_systems_resolve_to_one_enterprise_key(self):
        self.oracle(1, "Ada@Example.com ")
        self.subscription("SUB_1", "CRM_9", "ADA@example.com")
        self.ticket("TCK_1", "SUP_5", "ada@EXAMPLE.com")
        self.partner("PC_7", " ada@example.com")
        self.build()
        keys = {row[2] for row in self.identity_rows()}
        self.assertEqual(keys, {key("ada@example.com")})
        self.assertEqual(len(self.identity_rows()), 4, "one row per source system")

    def test_null_and_blank_emails_are_excluded_not_fatal(self):
        """ENTERPRISE_CUSTOMER_KEY is NOT NULL and MD5(NULL) is NULL."""
        self.oracle(1, "ada@example.com")
        self.oracle(2, None, name="No Email")
        self.oracle(3, "   ", name="Blank Email")
        result = self.build()
        self.assertEqual(result.rows_for("trans_WU55bR1llr"), 1)
        refs = {row[1] for row in self.identity_rows(SOURCE_SYSTEM=ORACLE)}
        self.assertEqual(refs, {"1"})

    def test_match_confidence_differs_by_source(self):
        self.oracle(1, "ada@example.com")
        self.subscription("SUB_1", "CRM_9", "ada@example.com")
        self.ticket("TCK_1", "SUP_5", "ada@example.com")
        self.partner("PC_7", "ada@example.com")
        self.build()
        confidence = {row[0]: row[4] for row in self.identity_rows()}
        self.assertEqual(confidence[ORACLE], 1.0)
        self.assertEqual(confidence[POSTGRES], 1.0)
        self.assertEqual(confidence[MYSQL], 0.95)
        self.assertEqual(confidence[PARTNER], 0.80)

    # -- D19: the partner identifier space is scoped by partner ----------
    def test_two_partners_reusing_one_identifier_are_two_identities(self):
        """partner_customer_id is unique only within a partner.

        Partitioning on it alone silently dropped one of the two customers.
        """
        self.partner("PC_7", "ada@example.com", partner_id="PTR_1")
        self.partner("PC_7", "grace@example.com", partner_id="PTR_2")
        self.build()
        refs = sorted(row[1] for row in self.identity_rows(SOURCE_SYSTEM=PARTNER))
        self.assertEqual(refs, ["PTR_1:PC_7", "PTR_2:PC_7"])

    def test_partner_source_reference_identifies_one_source_row(self):
        self.partner("PC_7", "ada@example.com", partner_id="PTR_1")
        self.build()
        self.assertEqual(self.identity_rows(SOURCE_SYSTEM=PARTNER)[0][1], "PTR_1:PC_7")

    def test_redelivered_partner_mapping_collapses_to_the_latest_delivery(self):
        self.partner("PC_7", "ada@example.com", ingested="2026-03-01 03:05:00",
                     batch="b1")
        self.partner("PC_7", "ada@example.com", ingested="2026-03-02 03:05:00",
                     batch="b2")
        self.build()
        self.assertEqual(len(self.identity_rows(SOURCE_SYSTEM=PARTNER)), 1)

    def test_partner_branch_declares_a_weaker_match_method(self):
        self.partner("PC_7", "ada@example.com")
        self.build()
        self.assertEqual(self.identity_rows()[0][3], "PARTNER_DECLARED")

    def test_is_active_is_populated(self):
        self.oracle(1, "ada@example.com")
        self.build()
        self.assertTrue(self.identity_rows()[0][5])

    def test_email_hash_is_sha256_of_the_normalized_email(self):
        self.oracle(1, "  Ada@Example.COM ")
        self.build()
        stored = self.conn.execute(
            "SELECT EMAIL_NORMALIZED, EMAIL_HASH FROM CUSTOMER_IDENTITY_MAP").fetchone()
        self.assertEqual(stored[0], "ada@example.com")
        self.assertEqual(stored[1], email_hash("ada@example.com"))


class CoreCustomerTests(CoreSpineCase):
    def test_one_row_per_enterprise_customer_despite_versions_and_partner_duplicates(self):
        for n in range(3):
            self.oracle(1, "ada@example.com", updated=f"2026-03-0{n+1} 10:00:00",
                        ingested=f"2026-03-0{n+1} 10:05:00")
        self.partner("PC_7", "ada@example.com", campaign="CMP_1")
        self.partner("PC_8", "ada@example.com", campaign="CMP_2")
        self.build()
        self.assertEqual(len(self.customers()), 1)

    def test_latest_source_version_wins(self):
        self.oracle(1, "ada@example.com", status="ACTIVE", updated="2026-03-01 10:00:00")
        self.oracle(1, "ada@example.com", status="DORMANT", updated="2026-03-05 10:00:00")
        self.build()
        self.assertEqual(self.customers("CUSTOMER_STATUS")[0][0], "DORMANT")

    def test_status_vocabulary_is_mapped(self):
        self.oracle(1, "a@example.com", status="ACTIVE")
        self.oracle(2, "b@example.com", status="DORMANT")
        self.oracle(3, "c@example.com", status="SUSPENDED_BY_FINANCE")
        self.build()
        mapped = dict(self.conn.execute(
            "SELECT EMAIL, CUSTOMER_STATUS FROM CUSTOMER").fetchall())
        self.assertEqual(mapped["a@example.com"], "ACTIVE")
        self.assertEqual(mapped["b@example.com"], "DORMANT")
        self.assertEqual(mapped["c@example.com"], "CLOSED")

    def test_oracle_timestamps_are_treated_as_utc_by_configuration(self):
        """The sample's assumption: Oracle already stores UTC, so this is a no-op."""
        self.oracle(1, "ada@example.com", created="2026-01-15 09:30:00")
        self.build()
        self.assertEqual(self.customers("FIRST_SEEN_AT_UTC")[0][0], "2026-01-15 09:30:00")

    def test_the_source_zone_is_a_real_parameter_not_a_session_setting(self):
        """Changing the configured zone must change the result, or it is being ignored."""
        self.oracle(1, "ada@example.com", created="2026-01-15 09:30:00")
        self.build(oracle_server_timezone="America/Chicago")
        self.assertEqual(self.customers("FIRST_SEEN_AT_UTC")[0][0], "2026-01-15 15:30:00")

    def test_source_system_count_reflects_resolved_systems(self):
        self.oracle(1, "ada@example.com")
        self.subscription("SUB_1", "CRM_9", "ada@example.com")
        self.ticket("TCK_1", "SUP_5", "ada@example.com")
        self.partner("PC_7", "ada@example.com")
        self.oracle(2, "solo@example.com")
        self.build()
        counts = dict(self.conn.execute(
            "SELECT EMAIL, SOURCE_SYSTEM_COUNT FROM CUSTOMER").fetchall())
        self.assertEqual(counts["ada@example.com"], 4)
        self.assertEqual(counts["solo@example.com"], 1)

    def test_billing_address_is_reduced_to_country_code(self):
        self.oracle(1, "ada@example.com", country="GB")
        self.build()
        row = self.conn.execute("SELECT * FROM CUSTOMER").fetchone()
        self.assertNotIn("1 Example St", [str(v) for v in row])
        self.assertEqual(self.customers("BILLING_COUNTRY_CODE")[0][0], "GB")

    def test_email_hash_carries_through_from_the_crosswalk(self):
        self.oracle(1, "ada@example.com")
        self.build()
        self.assertEqual(self.customers("EMAIL_HASH")[0][0], email_hash("ada@example.com"))

    # -- D20: the acquisition campaign must not depend on row order ------
    def test_acquisition_campaign_is_first_touch_when_partners_disagree(self):
        """Two partners claim the same person; the earlier signup is first touch.

        Before the tie-break the winner was whichever row the engine happened to
        emit first, so the same data could publish either campaign.
        """
        self.oracle(1, "ada@example.com")
        self.partner("PC_9", "ada@example.com", partner_id="PTR_2",
                     campaign="CMP_LATE", signup="2026-02-01 08:00:00")
        self.partner("PC_7", "ada@example.com", partner_id="PTR_1",
                     campaign="CMP_EARLY", signup="2026-01-05 08:00:00")
        self.build()
        self.assertEqual(self.customers("ACQUISITION_CAMPAIGN_ID")[0][0], "CMP_EARLY")

    def test_a_mapping_with_a_known_signup_beats_one_without(self):
        """SQLite sorts NULLs first and Snowflake last; the CASE settles it."""
        self.oracle(1, "ada@example.com")
        self.partner("PC_9", "ada@example.com", partner_id="PTR_2",
                     campaign="CMP_UNDATED", signup=None)
        self.partner("PC_7", "ada@example.com", partner_id="PTR_1",
                     campaign="CMP_DATED", signup="2026-01-05 08:00:00")
        self.build()
        self.assertEqual(self.customers("ACQUISITION_CAMPAIGN_ID")[0][0], "CMP_DATED")

    def test_redelivered_mapping_does_not_change_the_acquisition_campaign(self):
        """A corrected delivery of one mapping must not fan the customer out."""
        self.oracle(1, "ada@example.com")
        self.partner("PC_7", "ada@example.com", campaign="CMP_SPRING",
                     ingested="2026-03-01 03:05:00", batch="b1")
        self.partner("PC_7", "ada@example.com", campaign="CMP_SPRING",
                     ingested="2026-03-02 03:05:00", batch="b2")
        self.build()
        self.assertEqual(len(self.customers()), 1)
        self.assertEqual(self.customers("ACQUISITION_CAMPAIGN_ID")[0][0], "CMP_SPRING")

    def test_acquisition_campaign_attached_from_partner_mapping(self):
        self.oracle(1, "ada@example.com")
        self.partner("PC_7", "ada@example.com", campaign="CMP_SPRING")
        self.build()
        self.assertEqual(self.customers("ACQUISITION_CAMPAIGN_ID")[0][0], "CMP_SPRING")

    # -- D22: the campaign reference must be resolvable --------------------
    def test_the_acquisition_campaign_key_is_partner_scoped(self):
        """Campaign ids are unique only within a partner, so the id alone is unjoinable."""
        self.oracle(1, "ada@example.com")
        self.partner("PC_7", "ada@example.com", partner_id="PTR_3",
                     campaign="CMP_SPRING")
        self.build()
        campaign_id, campaign_key = self.customers(
            "ACQUISITION_CAMPAIGN_ID, ACQUISITION_CAMPAIGN_KEY")[0]
        self.assertEqual(campaign_id, "CMP_SPRING")
        self.assertEqual(campaign_key, "PTR_3:CMP_SPRING")

    def test_a_customer_with_no_partner_mapping_has_no_campaign_key(self):
        """A key pointing at nothing is worse than no key."""
        self.oracle(1, "ada@example.com")
        self.build()
        self.assertIsNone(self.customers("ACQUISITION_CAMPAIGN_KEY")[0][0])

    # -- membership: the enterprise key is the spine, not Oracle -----------
    def test_customers_discovered_by_other_systems_reach_customer(self):
        """Subscription-only, support-only and partner-only customers all participate."""
        self.oracle(1, "ada@example.com")
        self.subscription("SUB_1", "CRM_9", "subonly@example.com")
        self.ticket("TCK_1", "SUP_5", "supportonly@example.com")
        self.partner("PC_7", "partneronly@example.com")
        self.build()
        emails = {row[0] for row in self.customers("EMAIL")}
        self.assertEqual(emails, {"ada@example.com", "subonly@example.com",
                                  "supportonly@example.com", "partneronly@example.com"})

    def test_non_oracle_customer_has_null_oracle_attributes_and_unknown_status(self):
        self.subscription("SUB_1", "CRM_9", "subonly@example.com")
        self.build()
        name, phone, country, status, first_seen = self.conn.execute(
            "SELECT CUSTOMER_NAME, PHONE_NUMBER, BILLING_COUNTRY_CODE, CUSTOMER_STATUS,"
            " FIRST_SEEN_AT_UTC FROM CUSTOMER").fetchone()
        self.assertIsNone(name)
        self.assertIsNone(phone)
        self.assertIsNone(country)
        self.assertEqual(status, "UNKNOWN", "absence of an Oracle row is not a closed account")
        self.assertIsNone(first_seen, "documented gap: no cross-system first-seen")

    def test_non_oracle_customer_still_has_an_email_and_hash(self):
        self.ticket("TCK_1", "SUP_5", "  SupportOnly@Example.com ")
        self.build()
        email, hashed = self.conn.execute(
            "SELECT EMAIL, EMAIL_HASH FROM CUSTOMER").fetchone()
        self.assertEqual(email, "supportonly@example.com")
        self.assertEqual(hashed, email_hash("supportonly@example.com"))

    def test_oracle_attributes_win_when_the_customer_is_in_several_systems(self):
        """The QUALIFY must prefer the Oracle-attributed crosswalk row."""
        self.ticket("TCK_1", "SUP_5", "ada@example.com")
        self.subscription("SUB_1", "CRM_9", "ada@example.com")
        self.oracle(1, "ada@example.com", name="Ada Lovelace", country="GB")
        self.build()
        name, country, status = self.conn.execute(
            "SELECT CUSTOMER_NAME, BILLING_COUNTRY_CODE, CUSTOMER_STATUS FROM CUSTOMER"
        ).fetchone()
        self.assertEqual((name, country, status), ("Ada Lovelace", "GB", "ACTIVE"))

    def test_non_oracle_customers_are_counted_by_source_system_count(self):
        self.subscription("SUB_1", "CRM_9", "shared@example.com")
        self.ticket("TCK_1", "SUP_5", "shared@example.com")
        self.build()
        self.assertEqual(self.customers("SOURCE_SYSTEM_COUNT")[0][0], 2)

    def test_oracle_scoping_prevents_cross_space_reference_collision(self):
        """A PostgreSQL CRM ref that looks like an Oracle CUSTOMER_ID must not borrow its row."""
        self.oracle(1, "ada@example.com", name="Ada")
        self.subscription("SUB_1", "1", "imposter@example.com")
        self.build()
        names = dict(self.conn.execute("SELECT EMAIL, CUSTOMER_NAME FROM CUSTOMER").fetchall())
        self.assertEqual(names["ada@example.com"], "Ada")
        self.assertIsNone(names["imposter@example.com"],
                          "the imposter must get its own row, not Ada's attributes")

    def test_rebuild_is_idempotent(self):
        self.oracle(1, "ada@example.com")
        self.subscription("SUB_1", "CRM_9", "ada@example.com")
        first = self.build()
        second = self.build()
        self.assertEqual(first.target_rows, second.target_rows)
        self.assertEqual(second.target_rows["CUSTOMER_IDENTITY_MAP"], 2)
        self.assertEqual(second.target_rows["CUSTOMER"], 1)

    def test_empty_sources_produce_empty_tables_without_error(self):
        result = self.build()
        self.assertEqual(result.target_rows, {"CUSTOMER_IDENTITY_MAP": 0, "CUSTOMER": 0})

    def test_unbound_parameter_is_rejected(self):
        with self.assertRaises(TypeError):
            run(self.conn, dialect="sqlite")  # oracle_server_timezone is required


if __name__ == "__main__":
    unittest.main(verbosity=2)
