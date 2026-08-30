"""Atomic persistence for complete per-character industry job snapshots."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal

from eve_dolphin.database import Database
from eve_dolphin.sync.job_models import CharacterIndustryJob, IndustryJobSnapshot


class IndustryJobSnapshotRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def start_run(self, character_id: int, started_at: datetime) -> int:
        _validate_identity_time(character_id, started_at)
        with self._database.connect() as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO sync_runs(character_id, sync_kind, status, started_at)
                VALUES (?, 'industry_jobs', 'running', ?)
                """,
                (character_id, started_at.isoformat()),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not create an industry job sync run ID")
            return cursor.lastrowid

    def fail_run(self, run_id: int, failed_at: datetime, reason: str) -> None:
        if run_id <= 0 or failed_at.tzinfo is None:
            raise ValueError("failed job sync run metadata is invalid")
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                UPDATE sync_runs SET status = 'failed', finished_at = ?, message = ?
                WHERE id = ? AND status = 'running'
                """,
                (failed_at.isoformat(), reason[:200], run_id),
            )

    def activate(
        self,
        run_id: int,
        character_id: int,
        fetched_at: datetime,
        jobs: tuple[CharacterIndustryJob, ...],
        last_modified: str | None,
    ) -> IndustryJobSnapshot:
        _validate_identity_time(character_id, fetched_at)
        with self._database.connect() as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO industry_job_snapshots(
                    character_id, fetched_at, last_modified, job_count
                ) VALUES (?, ?, ?, ?)
                """,
                (character_id, fetched_at.isoformat(), last_modified, len(jobs)),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not create an industry job snapshot ID")
            snapshot_id = cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO character_industry_jobs(
                    snapshot_id, job_id, installer_id, facility_id, station_id,
                    activity_id, blueprint_id, blueprint_type_id,
                    blueprint_location_id, output_location_id, runs, status,
                    duration_seconds, start_date, end_date, completed_character_id,
                    completed_date, pause_date, cost_decimal, licensed_runs,
                    probability_decimal, product_type_id, successful_runs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ((_job_row(snapshot_id, job)) for job in jobs),
            )
            connection.execute(
                """
                INSERT INTO industry_jobs_current(character_id, snapshot_id) VALUES (?, ?)
                ON CONFLICT(character_id) DO UPDATE SET snapshot_id = excluded.snapshot_id
                """,
                (character_id, snapshot_id),
            )
            run = connection.execute(
                """
                UPDATE sync_runs SET status = 'succeeded', finished_at = ?, message = NULL
                WHERE id = ? AND character_id = ? AND status = 'running'
                """,
                (fetched_at.isoformat(), run_id, character_id),
            )
            if run.rowcount != 1:
                raise ValueError("industry job sync run is not active")
            connection.execute(
                "UPDATE eve_characters SET last_sync_at = ? WHERE character_id = ?",
                (fetched_at.isoformat(), character_id),
            )
            connection.execute(
                "DELETE FROM industry_job_snapshots WHERE character_id = ? AND id != ?",
                (character_id, snapshot_id),
            )
        snapshot = self.current(character_id)
        if snapshot is None or snapshot.snapshot_id != snapshot_id:
            raise RuntimeError("activated industry job snapshot is unavailable")
        return snapshot

    def current(self, character_id: int) -> IndustryJobSnapshot | None:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot.id, snapshot.character_id, snapshot.fetched_at,
                       snapshot.job_count, snapshot.last_modified
                FROM industry_jobs_current AS current
                JOIN industry_job_snapshots AS snapshot ON snapshot.id = current.snapshot_id
                WHERE current.character_id = ?
                """,
                (character_id,),
            ).fetchone()
        return _snapshot_from_row(row) if row is not None else None

    def current_jobs(self, character_id: int) -> tuple[CharacterIndustryJob, ...]:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT job.* FROM industry_jobs_current AS current
                JOIN character_industry_jobs AS job ON job.snapshot_id = current.snapshot_id
                WHERE current.character_id = ?
                ORDER BY job.end_date, job.job_id
                """,
                (character_id,),
            ).fetchall()
        return tuple(_job_from_row(row) for row in rows)


def _job_row(snapshot_id: int, job: CharacterIndustryJob) -> tuple[object, ...]:
    return (
        snapshot_id,
        job.job_id,
        job.installer_id,
        job.facility_id,
        job.station_id,
        job.activity_id,
        job.blueprint_id,
        job.blueprint_type_id,
        job.blueprint_location_id,
        job.output_location_id,
        job.runs,
        job.status,
        job.duration_seconds,
        job.start_date.isoformat(),
        job.end_date.isoformat(),
        job.completed_character_id,
        _isoformat(job.completed_date),
        _isoformat(job.pause_date),
        str(job.cost) if job.cost is not None else None,
        job.licensed_runs,
        str(job.probability) if job.probability is not None else None,
        job.product_type_id,
        job.successful_runs,
    )


def _job_from_row(row: sqlite3.Row) -> CharacterIndustryJob:
    return CharacterIndustryJob(
        job_id=int(row["job_id"]),
        installer_id=int(row["installer_id"]),
        facility_id=int(row["facility_id"]),
        station_id=int(row["station_id"]),
        activity_id=int(row["activity_id"]),
        blueprint_id=int(row["blueprint_id"]),
        blueprint_type_id=int(row["blueprint_type_id"]),
        blueprint_location_id=int(row["blueprint_location_id"]),
        output_location_id=int(row["output_location_id"]),
        runs=int(row["runs"]),
        status=str(row["status"]),
        duration_seconds=int(row["duration_seconds"]),
        start_date=datetime.fromisoformat(str(row["start_date"])),
        end_date=datetime.fromisoformat(str(row["end_date"])),
        completed_character_id=_optional_int(row["completed_character_id"]),
        completed_date=_optional_datetime(row["completed_date"]),
        pause_date=_optional_datetime(row["pause_date"]),
        cost=_optional_decimal(row["cost_decimal"]),
        licensed_runs=_optional_int(row["licensed_runs"]),
        probability=_optional_decimal(row["probability_decimal"]),
        product_type_id=_optional_int(row["product_type_id"]),
        successful_runs=_optional_int(row["successful_runs"]),
    )


def _snapshot_from_row(row: sqlite3.Row) -> IndustryJobSnapshot:
    return IndustryJobSnapshot(
        snapshot_id=int(row["id"]),
        character_id=int(row["character_id"]),
        fetched_at=datetime.fromisoformat(str(row["fetched_at"])),
        job_count=int(row["job_count"]),
        last_modified=str(row["last_modified"]) if row["last_modified"] is not None else None,
    )


def _validate_identity_time(character_id: int, value: datetime) -> None:
    if character_id <= 0:
        raise ValueError("character_id must be positive")
    if value.tzinfo is None:
        raise ValueError("job sync timestamp must include a timezone")


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _optional_datetime(value: object) -> datetime | None:
    return datetime.fromisoformat(str(value)) if value is not None else None


def _optional_decimal(value: object) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _optional_int(value: object) -> int | None:
    return int(str(value)) if value is not None else None
