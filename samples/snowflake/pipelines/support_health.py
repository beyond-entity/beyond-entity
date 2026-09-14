"""Build Customer Support Health -- Beyond Entity proc_tUDyM0IkCx.

The terminal step of the support lineage chain, and the only mart that needed no
correction: it aggregates a single fact, so there is no second one-to-many table
for it to multiply against.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = _ROOT / "sql" / "analytics" / "support_health"

PROCESSOR_ID = "proc_tUDyM0IkCx"


def build(conn, *, dialect: str = "snowflake") -> BuildResult:
    """Rebuild CUSTOMER_SUPPORT_HEALTH from the conformed support fact."""
    return sql_runner.run(conn, sql_dir=SQL_DIR, parameters={},
                          dialect=dialect, rebuild=True)
