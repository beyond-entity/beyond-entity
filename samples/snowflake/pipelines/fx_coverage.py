"""The FX quality gate -- Beyond Entity proc_UK8fvT1Asw.

    A missing required FX rate is a DATA QUALITY FAILURE.
    Do not drop the affected revenue rows -- revenue would be silently understated.
    Do not publish null USD amounts -- unresolved numbers are indistinguishable from
    real ones once they reach a dashboard.
    Fail the affected revenue build.

**The gate is per build, not global.** Each revenue build reads only the gaps for
the RAW tables it consumes, which is what `FX_COVERAGE_GAP.SOURCE_TABLE` is for. A
rate missing for orders must not block subscription revenue, and the reverse.

Each source is checked on the date its revenue *belongs to*: orders on the order
date, payments on their settlement date, subscriptions on the billing period start.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from pipelines import sql_runner

logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "core" / "fx_coverage"
PROCESSOR_ID = "proc_UK8fvT1Asw"


@dataclass(frozen=True)
class CoverageGap:
    currency: str
    date: str
    source_table: str
    affected_rows: int

    def __str__(self) -> str:
        return (f"{self.currency} on {self.date} "
                f"({self.source_table}, {self.affected_rows} row(s))")


class FxCoverageError(RuntimeError):
    """A required FX rate is missing, so the revenue build must not publish.

    Carries the gaps rather than only a message: the point of failing is that
    someone can see which rates to go and get.
    """

    def __init__(self, gaps: tuple[CoverageGap, ...]):
        self.gaps = gaps
        detail = "; ".join(str(gap) for gap in gaps)
        super().__init__(
            f"{len(gaps)} required FX rate(s) unavailable, revenue build blocked: {detail}"
        )


def assert_coverage(conn, *, source_tables: tuple[str, ...], timezones: dict,
                    dialect: str = "snowflake"):
    """Rebuild FX_COVERAGE_GAP and raise if any gap applies to `source_tables`.

    The whole gap table is rebuilt every run -- it is one assertion over the
    platform -- but only the rows naming the caller's source tables can block it.
    """
    result = sql_runner.run(conn, sql_dir=SQL_DIR, parameters=timezones,
                            dialect=dialect, rebuild=True)
    placeholders = ", ".join("?" for _ in source_tables)
    rows = conn.cursor().execute(
        "SELECT REQUIRED_CURRENCY, REQUIRED_DATE, SOURCE_TABLE, AFFECTED_ROW_COUNT"
        f" FROM FX_COVERAGE_GAP WHERE SOURCE_TABLE IN ({placeholders})"
        " ORDER BY SOURCE_TABLE, REQUIRED_CURRENCY, REQUIRED_DATE",
        source_tables,
    ).fetchall()
    if rows:
        gaps = tuple(CoverageGap(c, str(d), t, int(n)) for c, d, t, n in rows)
        logger.error("FX coverage assertion failed for %s: %d gap(s)",
                     ", ".join(source_tables), len(gaps))
        raise FxCoverageError(gaps)

    logger.info("FX coverage assertion passed for %s", ", ".join(source_tables))
    return result
