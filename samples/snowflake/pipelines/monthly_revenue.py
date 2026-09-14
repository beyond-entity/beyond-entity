"""Build Monthly Revenue -- Beyond Entity proc_5WN7LCvuxV.

Three contributions and one aggregate, not one join.

BR-3: each measure is reported in the month it belongs to -- orders in the order
month, payments in the settlement month, subscription MRR in the billing period
month. The previous single GROUP BY was driven by ORDER_FACT, so recurring revenue
only appeared in months where the customer also ordered and a subscription-only
customer contributed nothing for ever.

The contributions are staged at customer grain because DISTINCT_CUSTOMER_COUNT
cannot be summed across three separately aggregated inputs.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = _ROOT / "sql" / "analytics" / "monthly_revenue"

PROCESSOR_ID = "proc_5WN7LCvuxV"


def build(conn, *, dialect: str = "snowflake") -> BuildResult:
    """Rebuild the contribution staging table and MONTHLY_REVENUE from it."""
    return sql_runner.run(conn, sql_dir=SQL_DIR, parameters={},
                          dialect=dialect, rebuild=True)
