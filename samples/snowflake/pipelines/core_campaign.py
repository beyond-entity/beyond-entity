"""Build Core Campaign -- Beyond Entity proc_7x7b2hFPxu.

Two statements. The first conforms the daily partner cost feed, converting each
day at its own COST_DATE rate; the second builds one CAMPAIGN row per campaign
from the latest delivery plus the summed days.

The split is not stylistic. BR-2 defines campaign spend as the sum of daily costs
each converted on its own date, so there is no single applied rate for a campaign
and the per-day conversion has to be stored somewhere it can be audited.

The FX gate runs first, on RAW_PARTNER_ACQUISITION_COST. It matters more here than
anywhere else: campaign spend is a SUM, and SUM ignores NULLs, so one missing rate
would quietly *reduce* a campaign total -- the campaign would look cheaper and its
return on ad spend better. Understating spend silently is exactly what the FX
policy exists to prevent.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import fx_coverage, sql_runner
from pipelines.fx_coverage import CoverageGap, FxCoverageError
from pipelines.sql_runner import BuildResult

__all__ = ["build", "assert_fx_coverage", "CoverageGap", "FxCoverageError",
           "SOURCE_TABLES", "PROCESSOR_ID", "SQL_DIR"]

_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = _ROOT / "sql" / "core" / "campaign"

PROCESSOR_ID = "proc_7x7b2hFPxu"
SOURCE_TABLES = ("RAW_PARTNER_ACQUISITION_COST",)


def assert_fx_coverage(conn, *, oracle_server_timezone: str = "UTC",
                       postgres_server_timezone: str = "UTC",
                       dialect: str = "snowflake"):
    """Raise FxCoverageError if any campaign cost day has no rate.

    Per-build: a gap in orders or subscriptions does not block campaigns, and a
    campaign gap does not block them.

    The timezone arguments are not used by anything campaign-specific -- cost dates
    are already DATEs by the time they leave RAW. They are here because the gate
    rebuilds the whole FX_COVERAGE_GAP table, including the order and subscription
    branches, which do need them.
    """
    return fx_coverage.assert_coverage(
        conn, source_tables=SOURCE_TABLES,
        timezones={"oracle_server_timezone": oracle_server_timezone,
                   "postgres_server_timezone": postgres_server_timezone},
        dialect=dialect,
    )


def build(conn, *, oracle_server_timezone: str = "UTC",
          postgres_server_timezone: str = "UTC",
          dialect: str = "snowflake") -> BuildResult:
    """Assert FX coverage, then rebuild CAMPAIGN_DAILY_COST and CAMPAIGN."""
    assert_fx_coverage(conn, oracle_server_timezone=oracle_server_timezone,
                       postgres_server_timezone=postgres_server_timezone,
                       dialect=dialect)
    return sql_runner.run(conn, sql_dir=SQL_DIR, parameters={},
                          dialect=dialect, rebuild=True)
