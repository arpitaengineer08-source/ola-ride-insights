"""Thin, dependency-free data-access layer (SQLite)."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src import config as C

_HEADER = re.compile(r"^--\s*name:\s*(?P<id>\w+)\s*\|\s*(?P<title>.+)$")
_NOTE = re.compile(r"^--\s*note:\s*(?P<note>.+)$")
FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum)\b", re.I)


@dataclass(frozen=True)
class NamedQuery:
    id: str
    title: str
    sql: str
    note: str = ""


def connect(read_only: bool = True) -> sqlite3.Connection:
    """Open the DB. Read-only URI mode makes the app safe even for free-form SQL."""
    if not C.DB_PATH.exists():
        raise FileNotFoundError(f"{C.DB_PATH} not found - run `python -m src.etl` first.")
    uri = f"file:{C.DB_PATH.as_posix()}?mode={'ro' if read_only else 'rw'}"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def load_queries(path: Path) -> list[NamedQuery]:
    """Parse a .sql file that uses '-- name: id | title' block headers."""
    out, cur_id, cur_title, notes, buf = [], None, None, [], []

    def flush():
        if cur_id and buf:
            out.append(NamedQuery(cur_id, cur_title, "\n".join(buf).strip(), " ".join(notes)))

    for line in path.read_text(encoding="utf-8").splitlines():
        if m := _HEADER.match(line.strip()):
            flush()
            cur_id, cur_title, notes, buf = m["id"], m["title"].strip(), [], []
        elif cur_id:
            if m := _NOTE.match(line.strip()):
                notes.append(m["note"].strip())
            elif not line.strip().startswith("--"):
                buf.append(line.rstrip())
    flush()
    return out


@lru_cache(maxsize=1)
def all_queries() -> dict[str, NamedQuery]:
    qs = load_queries(C.SQL_DIR / "01_assignment_queries.sql") + load_queries(C.SQL_DIR / "02_advanced_analytics.sql")
    return {q.id: q for q in qs}


def run_sql(sql: str, params: tuple | dict = (), con: sqlite3.Connection | None = None) -> pd.DataFrame:
    own = con is None
    con = con or connect()
    try:
        return pd.read_sql_query(sql, con, params=params)
    finally:
        if own:
            con.close()


def run_user_sql(sql: str, limit: int = 5000) -> pd.DataFrame:
    """Execute a user-typed SELECT safely (single statement, read-only connection, row cap)."""
    stmt = sql.strip().rstrip(";")
    if ";" in stmt:
        raise ValueError("Only one statement is allowed.")
    if not re.match(r"^(select|with)\b", stmt, re.I) or FORBIDDEN.search(stmt):
        raise ValueError("Only read-only SELECT / WITH queries are allowed.")
    return run_sql(f"SELECT * FROM ({stmt}) LIMIT {int(limit)}")
