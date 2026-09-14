"""Validation for the FX rate pipeline (proc_PzWyOakCVL, proc_AsyyNwdM2X).

FX_RATE_DAILY is read by every currency normalization in the platform, so the
tests here are mostly about what must NOT reach it: uncast rates, zero rates, and
superseded deliveries. A bad rate does not error anywhere downstream -- it
multiplies through revenue and looks like a business result.
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines import fx_rate, snowflake_sqlite  # noqa: E402


class FxRateCase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        snowflake_sqlite.register(self.conn)
        self.conn.executescript(
            """
            CREATE TABLE fx_rate_file (
                rate_date TEXT, from_currency TEXT, to_currency TEXT, fx_rate TEXT);
            CREATE TABLE RAW_FX_RATES (
                RATE_DATE TEXT NOT NULL, FROM_CURRENCY TEXT NOT NULL,
                TO_CURRENCY TEXT NOT NULL, FX_RATE REAL, _SOURCE_FILE TEXT,
                _SOURCE_SYSTEM TEXT NOT NULL, _INGESTED_AT TEXT NOT NULL,
                _INGESTION_JOB_ID TEXT NOT NULL, _BATCH_ID TEXT);
            CREATE TABLE landing_file_manifest (
                file_name TEXT NOT NULL, storage_uri TEXT NOT NULL, file_format TEXT,
                partner_id TEXT, size_bytes NUMERIC, checksum_sha256 TEXT,
                received_at TEXT NOT NULL, load_status TEXT,
                loaded_row_count NUMERIC, rejected_row_count NUMERIC);
            CREATE TABLE FX_RATE_DAILY (
                RATE_DATE TEXT NOT NULL, FROM_CURRENCY TEXT NOT NULL,
                TO_CURRENCY TEXT NOT NULL, FX_RATE REAL NOT NULL);
            """
        )

    def tearDown(self):
        self.conn.close()

    def deliver(self, rows, *, batch_id="b1", source_file="fx_rates_20260301.csv"):
        """Stage one file's rows and ingest them."""
        self.conn.execute("DELETE FROM fx_rate_file")
        self.conn.executemany("INSERT INTO fx_rate_file VALUES (?,?,?,?)", rows)
        return fx_rate.ingest(self.conn, batch_id=batch_id, source_file=source_file,
                              storage_uri=f"s3://enterprise-landing/fx/{source_file}",
                              dialect="sqlite")

    def build(self):
        return fx_rate.build_core(self.conn, dialect="sqlite")

    def rates(self):
        return self.conn.execute(
            "SELECT RATE_DATE, FROM_CURRENCY, TO_CURRENCY, FX_RATE FROM FX_RATE_DAILY"
        ).fetchall()

    def raw(self, columns="*"):
        return self.conn.execute(f"SELECT {columns} FROM RAW_FX_RATES").fetchall()


class IngestionTests(FxRateCase):
    def test_landed_rates_carry_ingestion_metadata(self):
        self.deliver([("2026-03-01", "EUR", "USD", "1.08")])
        source_file, system, job, batch = self.raw(
            "_SOURCE_FILE, _SOURCE_SYSTEM, _INGESTION_JOB_ID, _BATCH_ID")[0]
        self.assertEqual(source_file, "fx_rates_20260301.csv")
        self.assertEqual(system, "FX_PROVIDER")
        self.assertEqual(job, fx_rate.INGESTION_JOB_ID)
        self.assertEqual(batch, "b1")

    def test_currency_codes_are_normalized_at_ingestion(self):
        """'usd' and 'USD ' are the same code; letting both through splits every join."""
        self.deliver([("2026-03-01", " eur ", "usd", "1.08")])
        self.assertEqual(self.raw("FROM_CURRENCY, TO_CURRENCY")[0], ("EUR", "USD"))

    def test_uncastable_rate_lands_with_a_null_rather_than_being_dropped(self):
        """It must stay countable against the manifest."""
        self.deliver([("2026-03-01", "EUR", "USD", "not-a-number")])
        self.assertEqual(len(self.raw()), 1)
        self.assertIsNone(self.raw("FX_RATE")[0][0])

    def test_row_with_an_unparseable_grain_key_is_rejected_at_ingestion(self):
        """A row with no usable rate date cannot be stored at this table's grain."""
        self.deliver([("2026-03-01", "EUR", "USD", "1.08"),
                      ("not-a-date", "GBP", "USD", "1.26"),
                      ("2026-03-01", "   ", "USD", "1.00")])
        self.assertEqual([r[1] for r in self.raw("RATE_DATE, FROM_CURRENCY")], ["EUR"])

    def test_one_malformed_row_does_not_abort_the_load(self):
        """Plain TO_NUMBER raises; the whole daily file would be lost."""
        result = self.deliver([("2026-03-01", "EUR", "USD", "1.08"),
                               ("2026-03-01", "JPY", "USD", "oops"),
                               ("2026-03-01", "GBP", "USD", "1.26")])
        self.assertEqual(result.target_rows["RAW_FX_RATES"], 3)

    def test_ingestion_appends_and_does_not_truncate(self):
        """A corrected redelivery must not erase the original."""
        self.deliver([("2026-03-01", "EUR", "USD", "1.08")], batch_id="b1",
                     source_file="fx_rates_20260301.csv")
        self.deliver([("2026-03-01", "EUR", "USD", "1.09")], batch_id="b2",
                     source_file="fx_rates_20260301_corrected.csv")
        self.assertEqual(len(self.raw()), 2)


class ManifestTests(FxRateCase):
    """rejected_row_count had no producer until the two-tier rule needed one."""

    def manifest(self, columns="*"):
        return self.conn.execute(f"SELECT {columns} FROM landing_file_manifest").fetchall()

    def test_a_manifest_row_is_written_per_delivery(self):
        self.deliver([("2026-03-01", "EUR", "USD", "1.08")])
        name, uri, fmt, status = self.manifest(
            "file_name, storage_uri, file_format, load_status")[0]
        self.assertEqual(name, "fx_rates_20260301.csv")
        self.assertEqual(uri, "s3://enterprise-landing/fx/fx_rates_20260301.csv")
        self.assertEqual((fmt, status), ("CSV", "LOADED"))

    def test_counts_match_the_two_tier_rejection_rule(self):
        """Loaded and rejected are the two sides of the ingestion WHERE clause."""
        self.deliver([("2026-03-01", "EUR", "USD", "1.08"),
                      ("2026-03-01", "GBP", "USD", "oops"),
                      ("not-a-date", "JPY", "USD", "1.00"),
                      ("2026-03-01", "   ", "USD", "1.00")])
        loaded, rejected = self.manifest("loaded_row_count, rejected_row_count")[0]
        self.assertEqual(loaded, 2, "good row plus the one whose only fault is its measure")
        self.assertEqual(rejected, 2, "the two rows with unusable grain keys")
        self.assertEqual(len(self.raw()), 2)

    def test_rejected_count_is_zero_for_a_clean_file(self):
        self.deliver([("2026-03-01", "EUR", "USD", "1.08")])
        self.assertEqual(self.manifest("rejected_row_count")[0][0], 0)

    def test_each_delivery_gets_its_own_manifest_row(self):
        self.deliver([("2026-03-01", "EUR", "USD", "1.08")], source_file="a.csv")
        self.deliver([("2026-03-01", "EUR", "USD", "1.09")], source_file="b.csv")
        self.assertEqual([r[0] for r in self.manifest("file_name")], ["a.csv", "b.csv"])


class CoreBuildTests(FxRateCase):
    def test_clean_rates_reach_core(self):
        self.deliver([("2026-03-01", "EUR", "USD", "1.08"),
                      ("2026-03-01", "GBP", "USD", "1.26")])
        self.build()
        self.assertEqual(sorted(self.rates()),
                         [("2026-03-01", "EUR", "USD", 1.08),
                          ("2026-03-01", "GBP", "USD", 1.26)])

    def test_uncastable_rate_is_dropped_at_the_core_boundary(self):
        self.deliver([("2026-03-01", "EUR", "USD", "1.08"),
                      ("2026-03-01", "JPY", "USD", "oops")])
        self.build()
        self.assertEqual([r[1] for r in self.rates()], ["EUR"])
        self.assertEqual(len(self.raw()), 2, "the bad row stays visible in RAW")

    def test_zero_rate_is_rejected(self):
        """A zero rate errors nowhere and reports the currency as earning nothing."""
        self.deliver([("2026-03-01", "EUR", "USD", "0")])
        self.build()
        self.assertEqual(self.rates(), [])

    def test_negative_rate_is_rejected(self):
        self.deliver([("2026-03-01", "EUR", "USD", "-1.08")])
        self.build()
        self.assertEqual(self.rates(), [])

    def test_corrected_redelivery_supersedes_the_original(self):
        self.deliver([("2026-03-01", "EUR", "USD", "1.08")], batch_id="b1")
        self.deliver([("2026-03-01", "EUR", "USD", "1.09")], batch_id="b2")
        self.build()
        self.assertEqual(self.rates(), [("2026-03-01", "EUR", "USD", 1.09)])

    def test_distinct_rate_dates_and_pairs_both_survive(self):
        self.deliver([("2026-03-01", "EUR", "USD", "1.08"),
                      ("2026-03-02", "EUR", "USD", "1.07"),
                      ("2026-03-01", "GBP", "USD", "1.26")])
        self.build()
        self.assertEqual(len(self.rates()), 3)

    def test_core_rebuild_is_idempotent(self):
        self.deliver([("2026-03-01", "EUR", "USD", "1.08")])
        first = self.build()
        second = self.build()
        self.assertEqual(first.target_rows, second.target_rows)
        self.assertEqual(second.target_rows["FX_RATE_DAILY"], 1)

    def test_empty_delivery_produces_an_empty_reference_table(self):
        result = self.build()
        self.assertEqual(result.target_rows["FX_RATE_DAILY"], 0)

    def test_every_core_column_is_populated(self):
        """FX_RATE_DAILY declares all four columns NOT NULL."""
        self.deliver([("2026-03-01", "EUR", "USD", "1.08")])
        self.build()
        for value in self.rates()[0]:
            self.assertIsNotNone(value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
