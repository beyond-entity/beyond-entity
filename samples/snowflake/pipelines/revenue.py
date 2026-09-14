"""Revenue chain -- Beyond Entity proc_UK8fvT1Asw, proc_3ASyTmTu51, proc_3Ddf5VeRop.

The FX quality policy lives here in executable form:

    A missing required FX rate is a DATA QUALITY FAILURE.
    Do not drop the affected revenue rows -- revenue would be silently understated.
    Do not publish null USD amounts -- unresolved numbers are indistinguishable from
    real ones once they reach a dashboard.
    Fail the revenue build.

`Assert FX Rate Coverage` rebuilds FX_COVERAGE_GAP with every currency/date pair the
landed revenue rows require and FX_RATE_DAILY does not have. A non-empty gap raises
`FxCoverageError` and the revenue builds never execute.

The blast radius is deliberately narrow. This gate sits between FX_RATE_DAILY and the
revenue builds only. A missing exchange rate says nothing about customer identity or
support tickets, so those pipelines are untouched and keep running.

Defence in depth: ORDER_FACT.ORDER_AMOUNT_USD, ORDER_FACT.FX_RATE_APPLIED and
PAYMENT.PAYMENT_AMOUNT_USD are NOT NULL. If the gate is ever bypassed, the insert
fails rather than publishing an unresolved number.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pipelines import fx_coverage, sql_runner
from pipelines.fx_coverage import CoverageGap, FxCoverageError  # re-exported
from pipelines.sql_runner import BuildResult

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
REVENUE_SQL_DIR = _ROOT / "sql" / "core" / "revenue"

ORDER_PROCESSOR_ID = "proc_3ASyTmTu51"
PAYMENT_PROCESSOR_ID = "proc_3Ddf5VeRop"


SOURCE_TABLES = ("RAW_ORDERS", "RAW_PAYMENTS")


def assert_fx_coverage(conn, *, oracle_server_timezone: str,
                       postgres_server_timezone: str = "UTC",
                       dialect: str = "snowflake"):
    """Raise if any order or payment rate is missing. Subscription gaps do not apply."""
    return fx_coverage.assert_coverage(
        conn, source_tables=SOURCE_TABLES,
        timezones={"oracle_server_timezone": oracle_server_timezone,
                   "postgres_server_timezone": postgres_server_timezone},
        dialect=dialect,
    )


def build(conn, *, oracle_server_timezone: str, dialect: str = "snowflake") -> BuildResult:
    """Assert FX coverage, then rebuild ORDER_FACT and PAYMENT.

    The assertion runs first and raises on failure, so a revenue build with a missing
    rate produces no rows at all rather than partial or null-bearing ones.
    """
    assert_fx_coverage(conn, oracle_server_timezone=oracle_server_timezone,
                       dialect=dialect)
    return sql_runner.run(
        conn,
        sql_dir=REVENUE_SQL_DIR,
        parameters={"oracle_server_timezone": oracle_server_timezone},
        dialect=dialect,
        rebuild=True,
    )
