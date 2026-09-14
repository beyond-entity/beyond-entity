"""Build Customer 360 -- Beyond Entity proc_qi2OyAuAAl.

The flagship mart, and the PII masking boundary: EMAIL_HASH reaches ANALYTICS,
raw EMAIL, CUSTOMER_NAME and PHONE_NUMBER do not.

Each CORE fact is aggregated in its own scalar subquery rather than joined. That
is the D21 fix: three LEFT JOINs to independent one-to-many facts multiplied each
other, so a customer with 3 orders, 2 subscriptions and 4 tickets reported 24
orders and eight times its real revenue. Nothing about the output looked wrong.

BR-1 governs how a customer's several subscriptions collapse into one row.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = _ROOT / "sql" / "analytics" / "customer_360"

PROCESSOR_ID = "proc_qi2OyAuAAl"

#: BR-1, highest precedence first. Kept here as data, not buried in an ORDER BY,
#: so the rule is checkable against business_rules.md.
LIFECYCLE_PRECEDENCE = ("ACTIVE", "AT_RISK", "TRIAL", "PAUSED", "CHURNED")
REVENUE_BEARING_STATES = ("ACTIVE", "AT_RISK")


def build(conn, *, dialect: str = "snowflake") -> BuildResult:
    """Rebuild CUSTOMER_360 from the CORE facts."""
    return sql_runner.run(conn, sql_dir=SQL_DIR, parameters={},
                          dialect=dialect, rebuild=True)
