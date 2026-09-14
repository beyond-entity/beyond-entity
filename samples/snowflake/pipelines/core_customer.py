"""CORE customer spine -- Beyond Entity proc_j3HyTdoXBh and proc_PASXcCWvuz.

1. **Resolve Customer Identity** (`proc_j3HyTdoXBh`) rebuilds CUSTOMER_IDENTITY_MAP
   from four independent identifier spaces. Each branch collapses to one row per
   source *customer reference* -- not per source row, which matters twice over:
   RAW is append-only and holds every version, and a customer naturally has many
   subscriptions and many tickets.
2. **Build Core Customer** (`proc_PASXcCWvuz`) rebuilds CUSTOMER from that
   crosswalk. The crosswalk is the spine: every resolved enterprise customer key
   gets a row whichever system found it, and Oracle contributes attributes when the
   customer exists there.

Both are **full rebuilds**, matching their declared grains. Neither is incremental:
the crosswalk states current identity, not history, and appending to it violates
the grain every downstream CORE build depends on.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "core" / "customer"

IDENTITY_PROCESSOR_ID = "proc_j3HyTdoXBh"
BUILD_PROCESSOR_ID = "proc_PASXcCWvuz"


def run(conn, *, oracle_server_timezone: str, dialect: str = "snowflake") -> BuildResult:
    """Rebuild CUSTOMER_IDENTITY_MAP then CUSTOMER.

    `oracle_server_timezone` is the source zone for RAW_CUSTOMERS.CREATED_AT. It is
    passed explicitly rather than inherited from the Snowflake session, so the
    assumption is auditable and changing it is a one-value change. This sample
    assumes 'UTC'; verify against the real Oracle system before deployment.
    """
    return sql_runner.run(
        conn,
        sql_dir=SQL_DIR,
        parameters={"oracle_server_timezone": oracle_server_timezone},
        dialect=dialect,
        rebuild=True,
    )
