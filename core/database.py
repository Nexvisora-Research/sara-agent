"""SQLite connection management and schema migrations for Phase A."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


SCHEMA_VERSION = 1


class Database:
    """Small dependency-injectable SQLite database wrapper."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migration_lock = threading.Lock()
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._migration_lock, self.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS background_tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    handler TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    scheduled_at TEXT,
                    result TEXT,
                    error TEXT,
                    logs TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_background_tasks_status
                    ON background_tasks(status);
                CREATE INDEX IF NOT EXISTS idx_background_tasks_scheduled
                    ON background_tasks(scheduled_at);
                """
            )
            row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,)
                )
            elif int(row["version"]) > SCHEMA_VERSION:
                raise RuntimeError(
                    f"database schema {row['version']} is newer than supported {SCHEMA_VERSION}"
                )

