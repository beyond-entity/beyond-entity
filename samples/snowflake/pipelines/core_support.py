"""CORE support build -- Beyond Entity proc_u5kiETSFgV.

Conforms support tickets into SUPPORT_INTERACTION_FACT and derives
RESOLUTION_SECONDS, the value CUSTOMER_SUPPORT_HEALTH.AVG_RESOLUTION_TIME rests on.

No currency here, so the FX coverage gate does not apply: a missing exchange rate
cannot block support reporting.
"""

from __future__ import annotations

from pathlib import Path

from pipelines import sql_runner
from pipelines.sql_runner import BuildResult

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "core" / "support"

PROCESSOR_ID = "proc_u5kiETSFgV"


def run(conn, *, mysql_server_timezone: str, dialect: str = "snowflake") -> BuildResult:
    """Rebuild SUPPORT_INTERACTION_FACT.

    `mysql_server_timezone` is the source zone for the ticket timestamps, passed
    explicitly rather than inherited from the Snowflake session so the assumption
    is auditable. This sample assumes 'UTC'; verify against the real MySQL system.
    """
    return sql_runner.run(conn, sql_dir=SQL_DIR,
                          parameters={"mysql_server_timezone": mysql_server_timezone},
                          dialect=dialect, rebuild=True)
