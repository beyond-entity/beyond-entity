"""Execute an ordered set of modeled statements against one database.

Used by every pipeline whose SQL runs inside a single system: the CORE builds, and
file-based ingestion, where Snowflake reads the landing zone stage itself. Only
ingestion from another *database* needs the extract/load split in `contract.py`.

Statement order, target table and transformation id all come from the file names
in the directory, which are generated from the model. Nothing here decides what
to run; it decides only how.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pipelines import snowflake_sqlite

logger = logging.getLogger(__name__)

_FILENAME = re.compile(r"^(?P<order>\d+)_(?P<transformation>trans_[A-Za-z0-9]+)_")
_TARGET = re.compile(r"INSERT\s+INTO\s+(\w+)", re.IGNORECASE)
_PARAM = re.compile(r":(\w+)")


@dataclass(frozen=True)
class Step:
    order: int
    transformation_id: str
    target_table: str
    sql: str
    path: Path


@dataclass(frozen=True)
class StepResult:
    transformation_id: str
    target_table: str
    rows_written: int


@dataclass(frozen=True)
class BuildResult:
    steps: tuple[StepResult, ...]
    target_rows: dict[str, int]

    def rows_for(self, transformation_id: str) -> int:
        for step in self.steps:
            if step.transformation_id == transformation_id:
                return step.rows_written
        raise KeyError(transformation_id)


def load_steps(sql_dir: Path) -> tuple[Step, ...]:
    """The modeled statements in a directory, in processing order."""
    steps = []
    for path in sorted(sql_dir.glob("*.sql")):
        name = _FILENAME.match(path.name)
        if not name:
            raise ValueError(f"unexpected file in {sql_dir.name}: {path.name}")
        sql = path.read_text()
        target = _TARGET.search(sql)
        if not target:
            raise ValueError(f"no INSERT target in {path.name}")
        steps.append(Step(int(name.group("order")), name.group("transformation"),
                          target.group(1).upper(), sql, path))
    return tuple(sorted(steps, key=lambda s: s.order))


def run(conn, *, sql_dir: Path, parameters: dict, dialect: str = "snowflake",
        rebuild: bool = True) -> BuildResult:
    """Execute every statement in `sql_dir`, in order, on one connection.

    `rebuild=True` truncates each target the first time it is written, which makes
    a re-run idempotent. Append-only targets must pass `rebuild=False`: truncating
    RAW would destroy the version history the whole layer exists to keep.
    """
    if dialect not in ("snowflake", "sqlite"):
        raise ValueError(f"unknown dialect: {dialect!r}")

    truncate = "TRUNCATE TABLE {}" if dialect == "snowflake" else "DELETE FROM {}"
    cursor = conn.cursor()
    truncated: set[str] = set()
    results: list[StepResult] = []

    for step in load_steps(sql_dir):
        if rebuild and step.target_table not in truncated:
            logger.info("rebuilding %s", step.target_table)
            cursor.execute(truncate.format(step.target_table))
            truncated.add(step.target_table)

        sql = snowflake_sqlite.translate(step.sql) if dialect == "sqlite" else step.sql
        required = set(_PARAM.findall(sql))
        missing = required - set(parameters)
        if missing:
            raise KeyError(f"{step.transformation_id}: unbound parameter(s) {sorted(missing)}")
        bound = {name: parameters[name] for name in required}

        cursor.execute(sql, bound) if bound else cursor.execute(sql)
        written = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
        logger.info("%s wrote %d row(s) into %s",
                    step.transformation_id, written, step.target_table)
        results.append(StepResult(step.transformation_id, step.target_table, written))

    targets = {r.target_table for r in results}
    counts = {t: cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in targets}
    return BuildResult(tuple(results), counts)
