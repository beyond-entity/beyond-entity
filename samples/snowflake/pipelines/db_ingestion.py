"""Run database-sourced ingestion: extract from a source system, load into RAW.

This is the half of the platform that cannot execute its modeled SQL as written.
Beyond Entity models a cross-system ingestion as one INSERT ... SELECT so that
column-level lineage is expressible, but the SELECT lives in Oracle (or MySQL, or
PostgreSQL) and the INSERT lives in Snowflake. `contract.py` derives the two halves
from the modeled text so the executed column list cannot drift from the model.

File-based ingestion does NOT come through here: Snowflake reads the landing zone
stage itself, so those statements run verbatim through `sql_runner`.

A processor may own several statements -- Oracle Order Ingestion writes three RAW
tables in one run -- so this module works over a directory, in processing order,
against one source connection and one target connection.

PII: several of these jobs carry pii_level 3 columns across a system boundary.
Nothing here logs, returns or raises a row value; only counts and identifiers leave.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pipelines import contract

logger = logging.getLogger(__name__)

DEFAULT_FETCH_SIZE = 5_000

_FILENAME = re.compile(r"^(?P<order>\d+)_(?P<transformation>trans_[A-Za-z0-9]+)_")


@dataclass(frozen=True)
class StatementResult:
    transformation_id: str
    target_table: str
    rows_extracted: int
    rows_loaded: int

    @property
    def reconciled(self) -> bool:
        return self.rows_extracted == self.rows_loaded


@dataclass(frozen=True)
class IngestionResult:
    """What a run did. Deliberately carries no row data -- see the PII note above."""

    batch_id: str
    window_start: datetime
    window_end: datetime
    ingested_at: datetime
    statements: tuple[StatementResult, ...]

    @property
    def rows_extracted(self) -> int:
        return sum(s.rows_extracted for s in self.statements)

    @property
    def rows_loaded(self) -> int:
        return sum(s.rows_loaded for s in self.statements)

    @property
    def reconciled(self) -> bool:
        return all(s.reconciled for s in self.statements)

    def rows_for(self, transformation_id: str) -> int:
        for statement in self.statements:
            if statement.transformation_id == transformation_id:
                return statement.rows_loaded
        raise KeyError(transformation_id)

    def rows_into(self, target_table: str) -> int:
        return sum(s.rows_loaded for s in self.statements
                   if s.target_table == target_table.upper())


def load_contracts(sql_dir: Path) -> tuple[tuple[str, contract.LoadContract], ...]:
    """The modeled statements in a directory, parsed, in processing order."""
    parsed = []
    for path in sorted(sql_dir.glob("*.sql")):
        name = _FILENAME.match(path.name)
        if not name:
            raise ValueError(f"unexpected file in {sql_dir.name}: {path.name}")
        parsed.append((int(name.group("order")), name.group("transformation"),
                       contract.parse(path.read_text())))
    return tuple((tid, c) for _, tid, c in sorted(parsed, key=lambda p: p[0]))


def _metadata_values(loaded: contract.LoadContract, parameters: dict,
                     ingested_at: datetime) -> dict[str, object]:
    values: dict[str, object] = {}
    for column in loaded.columns:
        if column.kind == "literal":
            values[column.name] = column.value
        elif column.kind == "load_timestamp":
            values[column.name] = ingested_at
        elif column.kind == "parameter":
            if column.value not in parameters:
                raise KeyError(f"missing run parameter {column.value!r}")
            values[column.name] = parameters[column.value]
    return values


def run(
    source_conn,
    target_conn,
    *,
    sql_dir: Path,
    ingestion_job_id: str,
    window_start: datetime,
    window_end: datetime,
    batch_id: str,
    extra_parameters: dict | None = None,
    paramstyle: str = "qmark",
    fetch_size: int = DEFAULT_FETCH_SIZE,
) -> IngestionResult:
    """Extract one window from the source system and append it to RAW.

    `window_start` is inclusive and `window_end` exclusive, matching the modeled
    predicate, so adjacent windows neither duplicate nor drop a row -- which is what
    makes an append-only target safe to re-run on a fixed interval.

    _INGESTED_AT is stamped once per RUN in UTC, not per row and not per statement:
    every row landed by one run shares a load time, so a batch is identifiable by it.
    """
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")

    ingested_at = datetime.now(timezone.utc)
    parameters = {
        "ingestion_job_id": ingestion_job_id,
        "batch_id": batch_id,
        "window_start": window_start,
        "window_end": window_end,
        **(extra_parameters or {}),
    }

    logger.info("%s: extracting window [%s, %s) batch=%s",
                ingestion_job_id, window_start.isoformat(), window_end.isoformat(), batch_id)

    results: list[StatementResult] = []
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    for transformation_id, loaded in load_contracts(sql_dir):
        missing = set(loaded.where_parameters) - set(parameters)
        if missing:
            raise KeyError(f"{transformation_id}: unbound parameter(s) {sorted(missing)}")
        source_cursor.execute(
            loaded.extract_sql(),
            {name: parameters[name] for name in loaded.where_parameters},
        )
        metadata = _metadata_values(loaded, parameters, ingested_at)
        position = {name: index for index, name in enumerate(loaded.source_columns)}
        insert_sql = loaded.load_sql(paramstyle)

        extracted = loaded_rows = 0
        while True:
            chunk = source_cursor.fetchmany(fetch_size)
            if not chunk:
                break
            extracted += len(chunk)
            payload = [
                tuple(
                    row[position[column.value]] if column.kind == "source"
                    else metadata[column.name]
                    for column in loaded.columns
                )
                for row in chunk
            ]
            target_cursor.executemany(insert_sql, payload)
            loaded_rows += len(payload)

        logger.info("%s: appended %d row(s) to %s",
                    transformation_id, loaded_rows, loaded.target_table)
        results.append(StatementResult(transformation_id, loaded.target_table.upper(),
                                       extracted, loaded_rows))

    return IngestionResult(batch_id=batch_id, window_start=window_start,
                           window_end=window_end, ingested_at=ingested_at,
                           statements=tuple(results))
