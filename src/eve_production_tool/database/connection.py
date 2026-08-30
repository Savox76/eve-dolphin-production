"""SQLite connection policy and migration runner."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from eve_production_tool.database.migrations import LATEST_SCHEMA_VERSION, MIGRATIONS


class Database:
    """Own the local database path and enforce connection settings."""

    def __init__(self, path: Path, backup_dir: Path | None = None) -> None:
        self.path = path
        self.backup_dir = backup_dir

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection with the application's safety settings enabled."""

        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the database and apply each missing migration once."""

        database_existed = self.path.exists() and self.path.stat().st_size > 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            applied = {
                row["version"]
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            pending_migrations = tuple(
                migration for migration in MIGRATIONS if migration.version not in applied
            )
            if database_existed and pending_migrations and self.backup_dir is not None:
                self._backup_before_migration(connection, max(applied, default=0))
            for migration in pending_migrations:
                script = f"""
                    BEGIN IMMEDIATE;
                    {migration.sql}
                    INSERT INTO schema_migrations(version, description)
                    VALUES ({migration.version}, {self._quote(migration.description)});
                    COMMIT;
                """
                try:
                    connection.executescript(script)
                except sqlite3.Error:
                    if connection.in_transaction:
                        connection.rollback()
                    raise

    def schema_version(self) -> int:
        """Return the highest successfully applied schema version."""

        with self.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()
        return int(row["version"]) if row is not None else 0

    def is_current(self) -> bool:
        return self.schema_version() == LATEST_SCHEMA_VERSION

    def _backup_before_migration(
        self, connection: sqlite3.Connection, current_version: int
    ) -> Path:
        assert self.backup_dir is not None
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = self.backup_dir / (
            f"eve-production-tool-schema-{current_version}-{timestamp}.sqlite3"
        )
        with sqlite3.connect(backup_path) as backup_connection:
            connection.backup(backup_connection)
        return backup_path

    @staticmethod
    def _quote(value: str) -> str:
        """Quote trusted migration metadata as a SQLite text literal."""

        return "'" + value.replace("'", "''") + "'"
