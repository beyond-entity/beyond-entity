"""CORE subscription build -- Beyond Entity proc_VlepSlkKoH.

MRR converts at the rate for the **billing period start** -- the period the
recurring revenue belongs to, not an operational timestamp such as creation or
update time. CURRENT_PERIOD_START_UTC, MRR_AMOUNT_SOURCE and FX_RATE_APPLIED are
all carried on the fact so MRR_USD is reproducible from the row.

Gated by the FX coverage assertion on RAW_SUBSCRIPTIONS gaps only: a rate missing
for orders must not block subscription revenue.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import fx_coverage, sql_runner
from pipelines.sql_runner import BuildResult

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "core" / "subscription"

PROCESSOR_ID = "proc_VlepSlkKoH"
SOURCE_TABLES = ("RAW_SUBSCRIPTIONS",)


def build(conn, *, postgres_server_timezone: str, oracle_server_timezone: str = "UTC",
          dialect: str = "snowflake") -> BuildResult:
    """Assert subscription FX coverage, then rebuild SUBSCRIPTION_FACT.

    `oracle_server_timezone` is needed only because the coverage assertion rebuilds
    the whole gap table, including its order and payment branches. Gaps found there
    do not block this build.
    """
    fx_coverage.assert_coverage(
        conn, source_tables=SOURCE_TABLES,
        timezones={"oracle_server_timezone": oracle_server_timezone,
                   "postgres_server_timezone": postgres_server_timezone},
        dialect=dialect,
    )
    return sql_runner.run(
        conn, sql_dir=SQL_DIR,
        parameters={"postgres_server_timezone": postgres_server_timezone},
        dialect=dialect, rebuild=True,
    )
