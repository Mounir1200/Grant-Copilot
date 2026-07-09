"""SQLite connection, schema, and a commit-and-close session helper."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline (
    user_id    TEXT NOT NULL,
    grant_id   TEXT NOT NULL,
    title      TEXT NOT NULL,
    agency     TEXT NOT NULL,
    close_date TEXT,
    url        TEXT NOT NULL,
    status     TEXT NOT NULL,
    saved_at   TEXT NOT NULL,
    reminded   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, grant_id)
);
CREATE TABLE IF NOT EXISTS mission (
    user_id        TEXT PRIMARY KEY,
    summary        TEXT NOT NULL,
    applicant_type TEXT NOT NULL DEFAULT '',
    focus_areas    TEXT NOT NULL DEFAULT ''
);
"""


@contextmanager
def session(path: str) -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success (rollback on error), always close."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init(path: str) -> None:
    with session(path) as connection:
        connection.executescript(_SCHEMA)
        _ensure_column(connection, "pipeline", "reminded", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(
            connection, "mission", "applicant_type", "TEXT NOT NULL DEFAULT ''"
        )
        _ensure_column(connection, "mission", "focus_areas", "TEXT NOT NULL DEFAULT ''")


def _ensure_column(
    connection: sqlite3.Connection, table: str, column: str, declaration: str
) -> None:
    """Add a column to an existing table if a prior schema lacked it (migration)."""
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
