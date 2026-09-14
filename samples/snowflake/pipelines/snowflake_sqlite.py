"""Run Snowflake-dialect statements against SQLite. Validation harness only.

The CORE builds are Snowflake SQL and are executed as such in deployment. This
module exists so their *semantics* -- deduplication, the null-email exclusion,
status mapping, the UTC conversion -- can be executed and asserted without a
warehouse. It is a translator, not an emulator: anything it cannot translate
faithfully it refuses rather than approximating, because a harness that quietly
diverges from the modeled SQL would be worse than no harness.

Not supported, deliberately: MERGE, multi-table INSERT, Snowflake-specific
semi-structured types, and any QUALIFY predicate that is not a single
ROW_NUMBER() window compared to a constant.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from pipelines.contract import ContractError, find_top_level_from, split_top_level

_COMMENT = re.compile(r"--[^\n]*")
_QUALIFY = re.compile(r"\bQUALIFY\b", re.IGNORECASE)
_INSERT_HEAD = re.compile(
    r"(?P<insert>\s*INSERT\s+INTO\s+\w+\s*\([^)]*\)\s*)(?P<select>SELECT\b.*)",
    re.IGNORECASE | re.DOTALL,
)
_ROW_NUMBER = re.compile(r"ROW_NUMBER\s*\(\s*\)\s*OVER\s*", re.IGNORECASE)


def _match_paren(text: str, start: int) -> int:
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ContractError("unbalanced parentheses in window specification")


def rewrite_qualify(sql: str) -> str:
    """Turn `... QUALIFY ROW_NUMBER() OVER (...) = 1` into a wrapped subquery.

    SQLite has window functions but no QUALIFY. The select items are aliased
    positionally so the outer query can project them without needing to know
    what the expressions are.
    """
    hit = _QUALIFY.search(sql)
    if not hit:
        return sql

    head, predicate = sql[: hit.start()], sql[hit.end() :].strip()
    parts = _INSERT_HEAD.match(head)
    if not parts:
        raise ContractError("QUALIFY is only supported on INSERT ... SELECT here")

    body = parts.group("select")
    from_at = find_top_level_from(body)
    items = split_top_level(body[len("SELECT") : from_at])
    remainder = body[from_at:]

    window = _ROW_NUMBER.match(predicate)
    if not window:
        raise ContractError(f"unsupported QUALIFY predicate: {predicate!r}")
    end = _match_paren(predicate, window.end())
    window_expr, comparison = predicate[:end], predicate[end:].strip()

    aliased = ", ".join(f"{item} AS _c{i}" for i, item in enumerate(items))
    projected = ", ".join(f"_c{i}" for i in range(len(items)))
    return (
        f"{parts.group('insert')}SELECT {projected} FROM ("
        f"SELECT {aliased}, {window_expr} AS _rn {remainder}"
        f") WHERE _rn {comparison}"
    )


def translate(sql: str) -> str:
    """Rewrite one Snowflake statement into its SQLite equivalent."""
    statement = _COMMENT.sub("", sql).strip()
    statement = re.sub(r"\bCURRENT_TIMESTAMP\s*\(\s*\)", "CURRENT_TIMESTAMP",
                       statement, flags=re.IGNORECASE)
    return rewrite_qualify(statement)


def _md5(value):
    return None if value is None else hashlib.md5(str(value).encode()).hexdigest()


def _sha2(value, bits=256):
    if value is None:
        return None
    if int(bits) != 256:
        raise ContractError(f"SHA2 width {bits} not supported in the harness")
    return hashlib.sha256(str(value).encode()).hexdigest()


def _convert_timezone(source_zone, target_zone, value):
    """Three-argument CONVERT_TIMEZONE: interpret a naive timestamp in source_zone."""
    if value is None:
        return None
    moment = datetime.fromisoformat(str(value))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo(source_zone))
    return moment.astimezone(ZoneInfo(target_zone)).replace(tzinfo=None).isoformat(sep=" ")


def _try(fn):
    """Snowflake's TRY_ casts return NULL where the strict form raises."""
    def attempt(value):
        try:
            return fn(value)
        except (TypeError, ValueError):
            return None
    return attempt


def _to_date(value):
    if value is None:
        return None
    return datetime.fromisoformat(str(value)[:10]).date().isoformat()


def _to_timestamp_ntz(value):
    if value is None:
        return None
    return datetime.fromisoformat(str(value)).isoformat(sep=" ")


_DATEDIFF_SECONDS = {"second": 1, "seconds": 1, "s": 1, "sec": 1, "day": 86400,
                     "days": 86400, "d": 86400}


def _datediff(unit, start, end):
    """Snowflake DATEDIFF, for the granularities the modeled SQL actually uses.

    Snowflake counts *boundaries crossed*, not elapsed units, so its day
    difference between 23:59 and 00:01 the next morning is 1. That distinction
    does not arise in the two places the model uses this -- support resolution in
    seconds, and customer tenure in days across months -- but it is why anything
    coarser than a day is refused rather than approximated by division.
    """
    if start is None or end is None:
        return None
    scale = _DATEDIFF_SECONDS.get(str(unit).lower())
    if scale is None:
        raise ContractError(f"DATEDIFF unit {unit!r} not supported in the harness")
    began = datetime.fromisoformat(str(start))
    ended = datetime.fromisoformat(str(end))
    if scale == 86400:
        return (ended.date() - began.date()).days
    return int((ended - began).total_seconds() / scale)


def _to_number(value):
    if value is None or str(value).strip() == "":
        return None
    text = str(value)
    return float(text) if "." in text else int(text)


def _concat(*values):
    """Snowflake CONCAT: variadic, and NULL if any argument is NULL.

    SQLite's `||` has the same NULL rule but is not variadic, and rewriting the
    modeled call into `||` would edit the statement rather than translate it.
    """
    if any(v is None for v in values):
        return None
    return "".join(str(v) for v in values)


def _date_trunc(part, value):
    """Snowflake DATE_TRUNC, month only.

    Only 'month' is translated because only 'month' is used by the modeled SQL. Any
    other part raises rather than returning a quietly wrong bucket -- this harness
    refuses what it cannot translate faithfully.
    """
    if value is None:
        return None
    if str(part).lower() != "month":
        raise ContractError(f"DATE_TRUNC part {part!r} not supported in the harness")
    text = str(value)
    if len(text) < 7 or text[4] != "-":
        raise ContractError(f"DATE_TRUNC expects an ISO date, got {value!r}")
    return f"{text[:7]}-01"


def register(conn) -> None:
    """Install the Snowflake scalar functions the modeled SQL uses."""
    conn.create_function("MD5", 1, _md5)
    conn.create_function("CONCAT", -1, _concat)
    conn.create_function("DATE_TRUNC", 2, _date_trunc)
    conn.create_function("SHA2", 2, _sha2)
    conn.create_function("CONVERT_TIMEZONE", 3, _convert_timezone)
    conn.create_function("TO_VARCHAR", 1, lambda v: None if v is None else str(v))
    conn.create_function("DATEDIFF", 3, _datediff)
    conn.create_function("TO_NUMBER", 1, _to_number)
    conn.create_function("TO_DATE", 1, _to_date)
    conn.create_function("TO_TIMESTAMP_NTZ", 1, _to_timestamp_ntz)
    # The TRY_ forms are not a convenience: the strict forms raise, so a single
    # malformed row in a delivered file would abort the entire load.
    conn.create_function("TRY_TO_NUMBER", 1, _try(_to_number))
    conn.create_function("TRY_TO_DATE", 1, _try(_to_date))
    conn.create_function("TRY_TO_TIMESTAMP_NTZ", 1, _try(_to_timestamp_ntz))
