"""Truthful freshness and failure states for locally persisted EVE data."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from eve_dolphin.database import Database
from eve_dolphin.sync.industry import INDUSTRY_CACHE_TTL
from eve_dolphin.sync.jobs import JOB_CACHE_TTL
from eve_dolphin.sync.planetary import PLANETARY_CACHE_TTL


class DataFreshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    FAILED = "failed"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class ResourceDataStatus:
    state: DataFreshness
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class SdeDataStatus:
    state: DataFreshness
    build_number: int | None
    release_date: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class CharacterDataStatus:
    character_id: int
    character_name: str
    industry: ResourceDataStatus
    jobs: ResourceDataStatus
    planetary: ResourceDataStatus


@dataclass(frozen=True, slots=True)
class DataStatusOverview:
    sde: SdeDataStatus
    characters: tuple[CharacterDataStatus, ...]


class DataStatusRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def overview(self, now: datetime | None = None) -> DataStatusOverview:
        checked_at = now or datetime.now(UTC)
        if checked_at.tzinfo is None:
            raise ValueError("status timestamp must include a timezone")
        with self._database.connect() as connection:
            sde = _sde_status(connection)
            characters = tuple(
                CharacterDataStatus(
                    character_id=int(row["character_id"]),
                    character_name=str(row["character_name"]),
                    industry=_resource_status(
                        connection,
                        int(row["character_id"]),
                        "industry",
                        "industry_snapshots",
                        INDUSTRY_CACHE_TTL,
                        checked_at,
                    ),
                    jobs=_resource_status(
                        connection,
                        int(row["character_id"]),
                        "industry_jobs",
                        "industry_job_snapshots",
                        JOB_CACHE_TTL,
                        checked_at,
                    ),
                    planetary=_resource_status(
                        connection,
                        int(row["character_id"]),
                        "planetary",
                        "planetary_snapshots",
                        PLANETARY_CACHE_TTL,
                        checked_at,
                    ),
                )
                for row in connection.execute(
                    """
                    SELECT character_id, character_name FROM eve_characters
                    ORDER BY character_name COLLATE NOCASE, character_id
                    """
                ).fetchall()
            )
        return DataStatusOverview(sde, characters)


def _resource_status(
    connection: sqlite3.Connection,
    character_id: int,
    sync_kind: str,
    snapshot_table: str,
    ttl: timedelta,
    now: datetime,
) -> ResourceDataStatus:
    if snapshot_table not in {
        "industry_snapshots",
        "industry_job_snapshots",
        "planetary_snapshots",
    }:
        raise ValueError("unsupported snapshot table")
    snapshot = connection.execute(
        f"""
        SELECT fetched_at FROM {snapshot_table}
        WHERE character_id = ? ORDER BY fetched_at DESC, id DESC LIMIT 1
        """,
        (character_id,),
    ).fetchone()
    fetched_at = (
        datetime.fromisoformat(str(snapshot["fetched_at"])) if snapshot is not None else None
    )
    latest_run = connection.execute(
        """
        SELECT status, started_at FROM sync_runs
        WHERE character_id = ? AND sync_kind = ?
        ORDER BY id DESC LIMIT 1
        """,
        (character_id, sync_kind),
    ).fetchone()
    if latest_run is not None and latest_run["status"] == "failed":
        failed_at = datetime.fromisoformat(str(latest_run["started_at"]))
        if fetched_at is None or failed_at >= fetched_at:
            return ResourceDataStatus(DataFreshness.FAILED, fetched_at)
    if fetched_at is None:
        return ResourceDataStatus(DataFreshness.MISSING, None)
    state = DataFreshness.CURRENT if now < fetched_at + ttl else DataFreshness.STALE
    return ResourceDataStatus(state, fetched_at)


def _sde_status(connection: sqlite3.Connection) -> SdeDataStatus:
    active = connection.execute(
        """
        SELECT build.build_number, build.release_date, build.activated_at
        FROM sde_current AS current
        JOIN sde_builds AS build ON build.build_number = current.build_number
        WHERE current.singleton = 1 AND build.status = 'ready'
        """
    ).fetchone()
    latest_failed = connection.execute(
        """
        SELECT build_number, import_started_at FROM sde_builds
        WHERE status = 'failed' ORDER BY import_started_at DESC, build_number DESC LIMIT 1
        """
    ).fetchone()
    latest_run = connection.execute(
        """
        SELECT status, started_at FROM sync_runs
        WHERE character_id IS NULL AND sync_kind = 'sde'
        ORDER BY id DESC LIMIT 1
        """
    ).fetchone()
    if active is None:
        state = (
            DataFreshness.FAILED
            if latest_failed is not None
            or (latest_run is not None and latest_run["status"] == "failed")
            else DataFreshness.MISSING
        )
        return SdeDataStatus(state, None, None, None)
    activated_at = datetime.fromisoformat(str(active["activated_at"]))
    state = DataFreshness.CURRENT
    if latest_failed is not None:
        failed_at = datetime.fromisoformat(str(latest_failed["import_started_at"]))
        if failed_at >= activated_at:
            state = DataFreshness.FAILED
    if latest_run is not None and latest_run["status"] == "failed":
        failed_at = datetime.fromisoformat(str(latest_run["started_at"]))
        if failed_at >= activated_at:
            state = DataFreshness.FAILED
    return SdeDataStatus(
        state=state,
        build_number=int(active["build_number"]),
        release_date=datetime.fromisoformat(str(active["release_date"])),
        updated_at=activated_at,
    )
