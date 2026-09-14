"""Derive the extract and load halves of a modeled INSERT ... SELECT.

Beyond Entity models a cross-system ingestion as a single statement so that
column-level lineage is expressible. A real run cannot execute it as one
statement -- the SELECT lives in Oracle and the INSERT lives in Snowflake -- so
the pipeline splits it. Splitting it *here*, from the modeled text, keeps the
executed columns and the modeled lineage identical by construction.

Only the shape the model actually produces is supported: a flat column list, a
single source table with an alias, and a conjunctive WHERE. Anything else raises
rather than guessing, because a silent mis-parse would be a silent divergence
from the architecture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_COMMENT = re.compile(r"--[^\n]*")
_INSERT = re.compile(
    r"\bINSERT\s+INTO\s+(?P<table>[A-Za-z_][\w$]*)\s*\((?P<cols>[^)]*)\)\s*"
    r"(?P<body>SELECT\b.*)",
    re.IGNORECASE | re.DOTALL,
)
_FROM = re.compile(r"\bFROM\s+(?P<table>[A-Za-z_][\w$]*)\s+(?P<alias>[A-Za-z_]\w*)",
                   re.IGNORECASE)
_SOURCE_COL = re.compile(r"^(?P<alias>[A-Za-z_]\w*)\.(?P<column>[A-Za-z_][\w$]*)$")
_PARAM = re.compile(r"^:(?P<name>\w+)$")
_LITERAL = re.compile(r"^'(?P<value>[^']*)'$")
_NOW = re.compile(r"^CURRENT_TIMESTAMP\s*\(\s*\)$", re.IGNORECASE)


class ContractError(ValueError):
    """The modeled SQL is not in a shape this loader can honor."""


@dataclass(frozen=True)
class Column:
    """One target column and where its value comes from."""

    name: str          # target column in the warehouse table
    kind: str          # "source" | "literal" | "parameter" | "load_timestamp"
    value: str | None  # source column, literal text, or parameter name


@dataclass(frozen=True)
class LoadContract:
    target_table: str
    source_table: str
    source_alias: str
    columns: tuple[Column, ...]
    remainder: str
    where_clause: str
    where_parameters: tuple[str, ...]

    @property
    def source_columns(self) -> tuple[str, ...]:
        return tuple(c.value for c in self.columns if c.kind == "source")

    @property
    def target_columns(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.columns)

    def extract_sql(self) -> str:
        """The SELECT to run against the source system.

        Everything from FROM onwards is carried through verbatim rather than
        rebuilt. Reconstructing it would drop any JOIN -- and the order-items
        ingestion windows itself through a join to its parent order, because
        ORDER_ITEMS has no timestamp of its own. A rebuilt FROM clause would
        have produced a statement whose WHERE referenced an absent alias.
        """
        projected = ", ".join(f"{self.source_alias}.{c}" for c in self.source_columns)
        return f"SELECT {projected}\n{self.remainder}"

    def load_sql(self, paramstyle: str = "qmark") -> str:
        """The INSERT to run against the warehouse.

        Snowflake's connector defaults to pyformat; SQLite and a qmark-configured
        Snowflake session use "?". Both are supported so the same contract drives
        the demo harness and a real warehouse session.
        """
        marker = {"qmark": "?", "format": "%s", "pyformat": "%s"}.get(paramstyle)
        if marker is None:
            raise ContractError(f"unsupported paramstyle: {paramstyle!r}")
        cols = ", ".join(self.target_columns)
        placeholders = ", ".join(marker for _ in self.target_columns)
        return f"INSERT INTO {self.target_table} ({cols}) VALUES ({placeholders})"


def split_top_level(text: str) -> list[str]:
    items, depth, current = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items


def find_top_level_from(body: str) -> int:
    depth = 0
    for match in re.finditer(r"[()]|\bFROM\b", body, re.IGNORECASE):
        token = match.group(0)
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        elif depth == 0:
            return match.start()
    raise ContractError("no top-level FROM in the modeled SELECT")


def parse(sql: str) -> LoadContract:
    statement = _COMMENT.sub("", sql)
    insert = _INSERT.search(statement)
    if not insert:
        raise ContractError("expected a single INSERT INTO <table> (...) SELECT ...")

    target_columns = [c.strip() for c in insert.group("cols").split(",") if c.strip()]
    body = insert.group("body")

    from_at = find_top_level_from(body)
    select_list = split_top_level(body[len("SELECT"):from_at])
    remainder = body[from_at:]

    if len(select_list) != len(target_columns):
        raise ContractError(
            f"{len(target_columns)} target columns but {len(select_list)} select items"
        )

    source = _FROM.search(remainder)
    if not source:
        raise ContractError("expected FROM <table> <alias>")
    alias = source.group("alias")

    where = re.search(r"\bWHERE\b(?P<clause>.*)", remainder, re.IGNORECASE | re.DOTALL)
    where_clause = " ".join(where.group("clause").split()) if where else "1=1"

    columns = []
    for target, expression in zip(target_columns, select_list):
        expression = " ".join(expression.split())
        if (m := _SOURCE_COL.match(expression)) and m.group("alias") == alias:
            columns.append(Column(target, "source", m.group("column")))
        elif m := _LITERAL.match(expression):
            columns.append(Column(target, "literal", m.group("value")))
        elif m := _PARAM.match(expression):
            columns.append(Column(target, "parameter", m.group("name")))
        elif _NOW.match(expression):
            columns.append(Column(target, "load_timestamp", None))
        else:
            raise ContractError(
                f"unsupported select expression for {target}: {expression!r}"
            )

    return LoadContract(
        target_table=insert.group("table"),
        source_table=source.group("table"),
        source_alias=alias,
        columns=tuple(columns),
        remainder=remainder.strip(),
        where_clause=where_clause,
        where_parameters=tuple(re.findall(r":(\w+)", where_clause)),
    )
