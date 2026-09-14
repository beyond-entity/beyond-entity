"""Build Subscription Retention -- Beyond Entity proc_F3jEWvf4lM.

One row per (cohort month, plan). BR-5 governs what retained means: the
revenue-bearing states of BR-1, not merely 'not churned'.

Retained and churned do not add up to the cohort, and that is correct -- a
trialling or paused subscription is neither.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = _ROOT / "sql" / "analytics" / "retention"

PROCESSOR_ID = "proc_F3jEWvf4lM"

#: BR-5, and BR-1's revenue-bearing states. Kept here as data so the rule is
#: checkable against business_rules.md rather than buried in a CASE.
RETAINED_STATES = ("ACTIVE", "AT_RISK")
CHURNED_STATE = "CHURNED"


def build(conn, *, dialect: str = "snowflake") -> BuildResult:
    """Rebuild SUBSCRIPTION_RETENTION from the conformed subscription fact."""
    return sql_runner.run(conn, sql_dir=SQL_DIR, parameters={},
                          dialect=dialect, rebuild=True)
