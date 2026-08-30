from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from eve_dolphin.characters import CharacterRepository, EveCharacter
from eve_dolphin.database import Database
from eve_dolphin.status import DataFreshness, DataStatusRepository

NOW = datetime(2026, 8, 30, 18, 0, tzinfo=UTC)


def test_status_distinguishes_current_stale_failed_and_missing_data(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7, "Alpha")
    _link(database, 8, "Beta")
    with database.connect() as connection, connection:
        connection.execute(
            """
            INSERT INTO industry_snapshots(
                character_id, fetched_at, asset_count, blueprint_count
            ) VALUES (7, ?, 2, 1)
            """,
            ((NOW - timedelta(minutes=30)).isoformat(),),
        )
        connection.execute(
            """
            INSERT INTO industry_job_snapshots(character_id, fetched_at, job_count)
            VALUES (7, ?, 3)
            """,
            ((NOW - timedelta(minutes=10)).isoformat(),),
        )
        connection.execute(
            """
            INSERT INTO sync_runs(
                character_id, sync_kind, status, started_at, finished_at, message
            ) VALUES (7, 'planetary', 'failed', ?, ?, 'EsiProtocolError')
            """,
            ((NOW - timedelta(minutes=1)).isoformat(), NOW.isoformat()),
        )

    overview = DataStatusRepository(database).overview(NOW)

    alpha, beta = overview.characters
    assert alpha.industry.state is DataFreshness.CURRENT
    assert alpha.jobs.state is DataFreshness.STALE
    assert alpha.planetary.state is DataFreshness.FAILED
    assert beta.industry.state is DataFreshness.MISSING
    assert beta.jobs.state is DataFreshness.MISSING
    assert beta.planetary.state is DataFreshness.MISSING


def test_sde_status_keeps_active_version_visible_after_new_import_failure(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path)
    with database.connect() as connection, connection:
        _insert_sde_build(connection, 100, "ready", NOW - timedelta(days=2))
        connection.execute("INSERT INTO sde_current(singleton, build_number) VALUES (1, 100)")

    current = DataStatusRepository(database).overview(NOW).sde

    assert current.state is DataFreshness.CURRENT
    assert current.build_number == 100
    assert current.release_date == NOW - timedelta(days=3)

    with database.connect() as connection, connection:
        _insert_sde_build(connection, 101, "failed", NOW - timedelta(hours=1))

    failed = DataStatusRepository(database).overview(NOW).sde

    assert failed.state is DataFreshness.FAILED
    assert failed.build_number == 100


def test_sde_download_failure_is_visible_without_an_import_record(tmp_path: Path) -> None:
    database = _database(tmp_path)
    with database.connect() as connection, connection:
        connection.execute(
            """
            INSERT INTO sync_runs(
                character_id, sync_kind, status, started_at, finished_at, message
            ) VALUES (NULL, 'sde', 'failed', ?, ?, 'SdeDownloadError')
            """,
            ((NOW - timedelta(minutes=1)).isoformat(), NOW.isoformat()),
        )

    status = DataStatusRepository(database).overview(NOW).sde

    assert status.state is DataFreshness.FAILED
    assert status.build_number is None


def _insert_sde_build(
    connection: sqlite3.Connection, build_number: int, status: str, imported_at: datetime
) -> None:
    release_date = NOW - timedelta(days=3)
    connection.execute(
        """
        INSERT INTO sde_builds(
            build_number, release_date, source_url, archive_sha256, archive_size,
            downloaded_at, import_started_at, imported_at, activated_at, status,
            failure_reason
        ) VALUES (?, ?, 'https://example.invalid/sde.zip', ?, 100, ?, ?, ?, ?, ?, ?)
        """,
        (
            build_number,
            release_date.isoformat(),
            "a" * 64,
            imported_at.isoformat(),
            imported_at.isoformat(),
            imported_at.isoformat() if status == "ready" else None,
            imported_at.isoformat() if status == "ready" else None,
            status,
            "invalid archive" if status == "failed" else None,
        ),
    )


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "eve-dolphin.sqlite3")
    database.initialize()
    return database


def _link(database: Database, character_id: int, name: str) -> None:
    CharacterRepository(database).upsert(
        EveCharacter(character_id, name, None, (), NOW - timedelta(days=1))
    )
