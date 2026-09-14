"""Validation for partner file ingestion (proc_a5OA9FY6dc).

This job is the only one that loads three landing objects in a single run, and
that is where its interesting failure modes live: a parameter shared across the
three files, and a manifest that has to describe three deliveries rather than one.

It is also the entry point for externally-sourced PII, so the column list is part
of the contract -- the mapping file's five modeled columns, nothing wider.
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines import partner_file_ingestion, snowflake_sqlite  # noqa: E402

CAMPAIGN_FILE = "campaign/partner_campaign_20260301.csv"
MAP_FILE = "mapping/partner_customer_map_20260301.parquet"
COST_FILE = "cost/partner_acquisition_cost_20260301.parquet"
ROOT = "s3://enterprise-landing/"


class PartnerIngestionCase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        snowflake_sqlite.register(self.conn)
        self.conn.executescript(
            """
            CREATE TABLE partner_campaign_file (
                campaign_id TEXT, partner_id TEXT, campaign_name TEXT, channel TEXT,
                start_date TEXT, end_date TEXT, acquisition_cost TEXT,
                currency_code TEXT, target_segment TEXT);
            CREATE TABLE partner_customer_map_file (
                partner_customer_id TEXT, partner_id TEXT, email TEXT, signup_at TEXT,
                first_touch_campaign_id TEXT);
            CREATE TABLE partner_acquisition_cost_file (
                campaign_id TEXT, partner_id TEXT, cost_date TEXT,
                acquisition_cost TEXT, currency_code TEXT, attributed_signups TEXT);

            CREATE TABLE RAW_CAMPAIGN_DATA (
                CAMPAIGN_ID TEXT NOT NULL, PARTNER_ID TEXT NOT NULL, CAMPAIGN_NAME TEXT,
                CHANNEL TEXT, START_DATE TEXT, END_DATE TEXT, ACQUISITION_COST NUMERIC,
                CURRENCY_CODE TEXT, TARGET_SEGMENT TEXT, _SOURCE_FILE TEXT,
                _SOURCE_SYSTEM TEXT NOT NULL, _INGESTED_AT TEXT NOT NULL,
                _INGESTION_JOB_ID TEXT NOT NULL, _BATCH_ID TEXT);
            CREATE TABLE RAW_PARTNER_CUSTOMER_MAP (
                PARTNER_CUSTOMER_ID TEXT NOT NULL, PARTNER_ID TEXT NOT NULL, EMAIL TEXT,
                SIGNUP_AT TEXT, FIRST_TOUCH_CAMPAIGN_ID TEXT, _SOURCE_FILE TEXT,
                _SOURCE_SYSTEM TEXT NOT NULL, _INGESTED_AT TEXT NOT NULL,
                _INGESTION_JOB_ID TEXT NOT NULL, _BATCH_ID TEXT);
            CREATE TABLE RAW_PARTNER_ACQUISITION_COST (
                CAMPAIGN_ID TEXT NOT NULL, PARTNER_ID TEXT NOT NULL, COST_DATE TEXT NOT NULL,
                ACQUISITION_COST NUMERIC, CURRENCY_CODE TEXT, ATTRIBUTED_SIGNUPS NUMERIC,
                _SOURCE_FILE TEXT, _SOURCE_SYSTEM TEXT NOT NULL, _INGESTED_AT TEXT NOT NULL,
                _INGESTION_JOB_ID TEXT NOT NULL, _BATCH_ID TEXT);
            CREATE TABLE landing_file_manifest (
                file_name TEXT NOT NULL, storage_uri TEXT NOT NULL, file_format TEXT,
                partner_id TEXT, size_bytes NUMERIC, checksum_sha256 TEXT,
                received_at TEXT NOT NULL, load_status TEXT,
                loaded_row_count NUMERIC, rejected_row_count NUMERIC);
            """
        )

    def tearDown(self):
        self.conn.close()

    # -- staging ---------------------------------------------------------
    def stage_campaign(self, rows):
        self.conn.executemany(
            "INSERT INTO partner_campaign_file VALUES (?,?,?,?,?,?,?,?,?)", rows)

    def stage_map(self, rows):
        self.conn.executemany(
            "INSERT INTO partner_customer_map_file VALUES (?,?,?,?,?)", rows)

    def stage_cost(self, rows):
        self.conn.executemany(
            "INSERT INTO partner_acquisition_cost_file VALUES (?,?,?,?,?,?)", rows)

    def ingest(self, *, batch_id="b1", partner_id_filter=None,
               campaign_source_file=CAMPAIGN_FILE):
        return partner_file_ingestion.ingest(
            self.conn, batch_id=batch_id,
            campaign_source_file=campaign_source_file,
            customer_map_source_file=MAP_FILE,
            cost_source_file=COST_FILE,
            partner_id_filter=partner_id_filter,
            dialect="sqlite")

    # -- reading back ----------------------------------------------------
    def rows(self, table, columns="*"):
        return self.conn.execute(f"SELECT {columns} FROM {table}").fetchall()

    def manifest(self, columns="*"):
        return self.conn.execute(
            f"SELECT {columns} FROM landing_file_manifest ORDER BY file_name").fetchall()


class SourceFileIsolationTests(PartnerIngestionCase):
    """D18: one parameter shared by three files destroys the manifest join."""

    def test_each_raw_table_records_its_own_landing_object(self):
        self.stage_campaign([("CMP_1", "PTR_1", "Spring", "SEARCH",
                              "2026-03-01", "2026-03-31", "100.00", "USD", "SMB")])
        self.stage_map([("PC_7", "PTR_1", "ada@example.com",
                         "2026-01-05 08:00:00", "CMP_1")])
        self.stage_cost([("CMP_1", "PTR_1", "2026-03-01", "25.00", "USD", "4")])
        self.ingest()
        landed = {
            self.rows("RAW_CAMPAIGN_DATA", "_SOURCE_FILE")[0][0],
            self.rows("RAW_PARTNER_CUSTOMER_MAP", "_SOURCE_FILE")[0][0],
            self.rows("RAW_PARTNER_ACQUISITION_COST", "_SOURCE_FILE")[0][0],
        }
        self.assertEqual(landed, {CAMPAIGN_FILE, MAP_FILE, COST_FILE})

    def test_every_landed_row_joins_back_to_its_own_manifest_entry(self):
        """_SOURCE_FILE exists for exactly this join."""
        self.stage_campaign([("CMP_1", "PTR_1", "Spring", "SEARCH",
                              "2026-03-01", "2026-03-31", "100.00", "USD", "SMB")])
        self.stage_map([("PC_7", "PTR_1", "ada@example.com", None, "CMP_1")])
        self.stage_cost([("CMP_1", "PTR_1", "2026-03-01", "25.00", "USD", "4")])
        self.ingest()
        for table in partner_file_ingestion.TARGET_TABLES:
            unmatched = self.conn.execute(
                f"SELECT COUNT(*) FROM {table} t LEFT JOIN landing_file_manifest m"
                " ON m.file_name = t._SOURCE_FILE WHERE m.file_name IS NULL").fetchone()[0]
            self.assertEqual(unmatched, 0, table)


class ManifestTests(PartnerIngestionCase):
    def test_one_manifest_row_per_delivered_file(self):
        self.ingest()
        self.assertEqual([r[0] for r in self.manifest("file_name")],
                         sorted([CAMPAIGN_FILE, MAP_FILE, COST_FILE]))

    def test_manifest_records_each_files_own_uri_and_format(self):
        self.ingest()
        rows = {name: (uri, fmt)
                for name, uri, fmt in self.manifest("file_name, storage_uri, file_format")}
        self.assertEqual(rows[CAMPAIGN_FILE], (ROOT + CAMPAIGN_FILE, "CSV"))
        self.assertEqual(rows[MAP_FILE], (ROOT + MAP_FILE, "PARQUET"))
        self.assertEqual(rows[COST_FILE], (ROOT + COST_FILE, "PARQUET"))

    def test_counts_match_the_two_tier_rejection_rule(self):
        self.stage_campaign([
            ("CMP_1", "PTR_1", "Spring", "SEARCH", "2026-03-01", "2026-03-31",
             "100.00", "USD", "SMB"),
            ("CMP_2", "PTR_1", "Summer", "SOCIAL", "2026-04-01", "2026-04-30",
             "oops", "USD", "SMB"),          # bad MEASURE -- lands, counts as loaded
            ("   ", "PTR_1", "Broken", "EMAIL", None, None, "5.00", "USD", None),
            ("CMP_3", None, "No partner", "EMAIL", None, None, "5.00", "USD", None),
        ])
        self.ingest()
        loaded, rejected = self.conn.execute(
            "SELECT loaded_row_count, rejected_row_count FROM landing_file_manifest"
            " WHERE file_name = ?", (CAMPAIGN_FILE,)).fetchone()
        self.assertEqual((loaded, rejected), (2, 2))
        self.assertEqual(len(self.rows("RAW_CAMPAIGN_DATA")), loaded)

    def test_cost_file_counts_an_unparseable_cost_date_as_rejected(self):
        """COST_DATE is part of that file's grain, so it is a grain key, not a measure."""
        self.stage_cost([("CMP_1", "PTR_1", "2026-03-01", "25.00", "USD", "4"),
                         ("CMP_1", "PTR_1", "not-a-date", "25.00", "USD", "4")])
        self.ingest()
        loaded, rejected = self.conn.execute(
            "SELECT loaded_row_count, rejected_row_count FROM landing_file_manifest"
            " WHERE file_name = ?", (COST_FILE,)).fetchone()
        self.assertEqual((loaded, rejected), (1, 1))


class CastingAndRejectionTests(PartnerIngestionCase):
    def test_row_missing_either_half_of_the_grain_key_is_rejected(self):
        """campaign_id is unique only within a partner, so both are required."""
        self.stage_campaign([
            ("CMP_1", "PTR_1", "Ok", "SEARCH", None, None, None, "USD", None),
            (None, "PTR_1", "No campaign", "SEARCH", None, None, None, "USD", None),
            ("CMP_2", "  ", "No partner", "SEARCH", None, None, None, "USD", None),
        ])
        self.ingest()
        self.assertEqual([r[0] for r in self.rows("RAW_CAMPAIGN_DATA", "CAMPAIGN_ID")],
                         ["CMP_1"])

    def test_uncastable_measure_lands_null_rather_than_being_dropped(self):
        """It must stay countable against the manifest; CORE is where it drops."""
        self.stage_campaign([("CMP_1", "PTR_1", "Spring", "SEARCH",
                              "not-a-date", None, "not-a-number", "USD", None)])
        self.ingest()
        start, cost = self.rows("RAW_CAMPAIGN_DATA", "START_DATE, ACQUISITION_COST")[0]
        self.assertIsNone(start)
        self.assertIsNone(cost)

    def test_one_malformed_row_does_not_abort_the_load(self):
        """Plain TO_DATE / TO_NUMBER raise; the whole daily drop would be lost."""
        self.stage_campaign([
            ("CMP_1", "PTR_1", "A", "SEARCH", "2026-03-01", None, "1.00", "USD", None),
            ("CMP_2", "PTR_1", "B", "SEARCH", "nope", None, "oops", "USD", None),
            ("CMP_3", "PTR_1", "C", "SEARCH", "2026-03-02", None, "2.00", "USD", None),
        ])
        result = self.ingest()
        self.assertEqual(result.target_rows["RAW_CAMPAIGN_DATA"], 3)

    def test_uncastable_signup_lands_null(self):
        self.stage_map([("PC_7", "PTR_1", "ada@example.com", "not-a-timestamp", "CMP_1")])
        self.ingest()
        self.assertIsNone(self.rows("RAW_PARTNER_CUSTOMER_MAP", "SIGNUP_AT")[0][0])

    def test_codes_are_normalized_but_free_text_is_not(self):
        """'usd' and 'USD ' are the same code; a campaign name is not a code."""
        self.stage_campaign([("CMP_1", "PTR_1", " Spring Sale ", " search ",
                              None, None, None, " usd ", " SMB ")])
        self.ingest()
        name, channel, currency, segment = self.rows(
            "RAW_CAMPAIGN_DATA", "CAMPAIGN_NAME, CHANNEL, CURRENCY_CODE, TARGET_SEGMENT")[0]
        self.assertEqual((channel, currency), ("SEARCH", "USD"))
        self.assertEqual((name, segment), (" Spring Sale ", " SMB "))

    def test_partner_email_lands_verbatim_for_core_to_normalize(self):
        """RAW is the faithful record of what the partner delivered."""
        self.stage_map([("PC_7", "PTR_1", " Ada@Example.COM ", None, "CMP_1")])
        self.ingest()
        self.assertEqual(self.rows("RAW_PARTNER_CUSTOMER_MAP", "EMAIL")[0][0],
                         " Ada@Example.COM ")


class AppendOnlyTests(PartnerIngestionCase):
    def test_a_redelivery_does_not_erase_the_original(self):
        self.stage_campaign([("CMP_1", "PTR_1", "Spring", "SEARCH",
                              None, None, "100.00", "USD", None)])
        self.ingest(batch_id="b1")
        self.conn.execute("DELETE FROM partner_campaign_file")
        self.stage_campaign([("CMP_1", "PTR_1", "Spring", "SEARCH",
                              None, None, "120.00", "USD", None)])
        self.ingest(batch_id="b2",
                    campaign_source_file="campaign/partner_campaign_20260301_fixed.csv")
        self.assertEqual(len(self.rows("RAW_CAMPAIGN_DATA")), 2)

    def test_landed_rows_carry_ingestion_metadata(self):
        self.stage_campaign([("CMP_1", "PTR_1", "Spring", "SEARCH",
                              None, None, None, "USD", None)])
        self.ingest(batch_id="run_42")
        system, job, batch = self.rows(
            "RAW_CAMPAIGN_DATA", "_SOURCE_SYSTEM, _INGESTION_JOB_ID, _BATCH_ID")[0]
        self.assertEqual(system, "PARTNER_LANDING")
        self.assertEqual(job, partner_file_ingestion.INGESTION_JOB_ID)
        self.assertEqual(batch, "run_42")


class SinglePartnerReloadTests(PartnerIngestionCase):
    """The modeled partner_id_filter: reload one partner without the whole day."""

    def stage_two_partners(self):
        self.stage_campaign([
            ("CMP_1", "PTR_1", "A", "SEARCH", None, None, "1.00", "USD", None),
            ("CMP_2", "PTR_2", "B", "SEARCH", None, None, "2.00", "USD", None),
        ])
        self.stage_map([("PC_7", "PTR_1", "ada@example.com", None, "CMP_1"),
                        ("PC_8", "PTR_2", "grace@example.com", None, "CMP_2")])
        self.stage_cost([("CMP_1", "PTR_1", "2026-03-01", "1.00", "USD", "1"),
                         ("CMP_2", "PTR_2", "2026-03-01", "2.00", "USD", "2")])

    def test_no_filter_loads_every_partner(self):
        self.stage_two_partners()
        self.ingest()
        self.assertEqual(len(self.rows("RAW_CAMPAIGN_DATA")), 2)
        self.assertEqual(len(self.rows("RAW_PARTNER_CUSTOMER_MAP")), 2)
        self.assertEqual(len(self.rows("RAW_PARTNER_ACQUISITION_COST")), 2)

    def test_filter_scopes_all_three_loads(self):
        self.stage_two_partners()
        self.ingest(partner_id_filter="PTR_2")
        for table in partner_file_ingestion.TARGET_TABLES:
            self.assertEqual([r[0] for r in self.rows(table, "PARTNER_ID")], ["PTR_2"],
                             table)

    def test_manifest_counts_follow_the_filter(self):
        """Otherwise a scoped reload looks like a collapse in delivered volume."""
        self.stage_two_partners()
        self.ingest(partner_id_filter="PTR_2")
        for name, loaded in self.manifest("file_name, loaded_row_count"):
            self.assertEqual(loaded, 1, name)

    def test_manifest_records_the_scope_of_the_run(self):
        self.stage_two_partners()
        self.ingest(partner_id_filter="PTR_2")
        self.assertEqual({r[0] for r in self.manifest("partner_id")}, {"PTR_2"})

    def test_a_full_load_records_no_partner_scope(self):
        self.stage_two_partners()
        self.ingest()
        self.assertEqual({r[0] for r in self.manifest("partner_id")}, {None})


class LandingPathTests(PartnerIngestionCase):
    def test_landing_paths_match_the_modeled_patterns(self):
        import datetime

        files = partner_file_ingestion.landing_files(datetime.date(2026, 3, 1))
        self.assertEqual(files, {"campaign": CAMPAIGN_FILE,
                                 "customer_map": MAP_FILE,
                                 "cost": COST_FILE})


if __name__ == "__main__":
    unittest.main()
