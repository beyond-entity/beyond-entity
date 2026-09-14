"""Build Campaign Performance -- Beyond Entity proc_EkjDDx59xe.

Partner campaign spend against the Oracle order revenue of the customers that
campaign acquired. The dataset exists only because identity resolution mapped the
partner customer identifier space onto the same enterprise key the orders carry.

The join goes through CUSTOMER.ACQUISITION_CAMPAIGN_KEY, not ACQUISITION_CAMPAIGN_ID:
campaign identifiers are unique only within a partner.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = _ROOT / "sql" / "analytics" / "campaign_performance"

PROCESSOR_ID = "proc_EkjDDx59xe"


def build(conn, *, dialect: str = "snowflake") -> BuildResult:
    """Rebuild CAMPAIGN_PERFORMANCE from CAMPAIGN, CUSTOMER and ORDER_FACT."""
    return sql_runner.run(conn, sql_dir=SQL_DIR, parameters={},
                          dialect=dialect, rebuild=True)
