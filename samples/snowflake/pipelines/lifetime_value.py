"""Build Customer Lifetime Value -- Beyond Entity proc_AR6brQlFmY.

Terminal step of the revenue lineage chain. Each CORE fact is aggregated in its
own scalar subquery rather than joined: joining them multiplied every measure.

BR-4 governs the net. Read it as revenue booked to date, plus the current monthly
recurring run rate, less the customer's share of the acquisition campaign's spend
-- not a projection, and the two revenue terms are not the same time dimension.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = _ROOT / "sql" / "analytics" / "lifetime_value"

PROCESSOR_ID = "proc_AR6brQlFmY"


def build(conn, *, dialect: str = "snowflake") -> BuildResult:
    """Rebuild CUSTOMER_LIFETIME_VALUE."""
    return sql_runner.run(conn, sql_dir=SQL_DIR, parameters={},
                          dialect=dialect, rebuild=True)
