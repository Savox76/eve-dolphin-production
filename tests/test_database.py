from __future__ import annotations

import sqlite3
from contextlib import suppress
from pathlib import Path

from eve_production_tool.database import Database
from eve_production_tool.database.migrations import LATEST_SCHEMA_VERSION


def test_initialize_is_repeatable_and_reaches_latest_schema(tmp_path: Path) -> None:
    database = Database(tmp_path / "client.sqlite3")

    database.initialize()
    database.initialize()

    assert database.schema_version() == LATEST_SCHEMA_VERSION
    assert database.is_current()

    with database.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        migration_count = connection.execute(
            "SELECT COUNT(*) AS count FROM schema_migrations"
        ).fetchone()

    assert {"schema_migrations", "app_settings", "eve_characters", "sync_runs"} <= tables
    assert migration_count is not None
    assert migration_count["count"] == LATEST_SCHEMA_VERSION


def test_schema_has_no_token_or_client_secret_columns(tmp_path: Path) -> None:
    database = Database(tmp_path / "client.sqlite3")
    database.initialize()

    with database.connect() as connection:
        schema_rows = connection.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"
        ).fetchall()

    schema = "\n".join(str(row["sql"]).lower() for row in schema_rows)
    assert "refresh_token" not in schema
    assert "access_token" not in schema
    assert "client_secret" not in schema


def test_foreign_keys_are_enabled_for_every_connection(tmp_path: Path) -> None:
    database = Database(tmp_path / "client.sqlite3")
    database.initialize()

    with database.connect() as connection:
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()

    assert foreign_keys is not None
    assert foreign_keys[0] == 1


def test_failed_write_does_not_leave_invalid_sync_run(tmp_path: Path) -> None:
    database = Database(tmp_path / "client.sqlite3")
    database.initialize()

    with database.connect() as connection, connection:
        with suppress(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO sync_runs(character_id, sync_kind, status, started_at)
                VALUES (999, 'assets', 'running', CURRENT_TIMESTAMP)
                """
            )

        count = connection.execute("SELECT COUNT(*) FROM sync_runs").fetchone()

    assert count is not None
    assert count[0] == 0


def test_existing_database_is_backed_up_before_migration(tmp_path: Path) -> None:
    database_path = tmp_path / "client.sqlite3"
    backup_dir = tmp_path / "backups"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE legacy_data(value TEXT NOT NULL)")
        connection.execute("INSERT INTO legacy_data VALUES ('preserved')")

    database = Database(database_path, backup_dir)
    database.initialize()

    backups = list(backup_dir.glob("*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        preserved = connection.execute("SELECT value FROM legacy_data").fetchone()
    assert preserved is not None
    assert preserved[0] == "preserved"
