"""Atomic SQLite persistence for complete per-character industry snapshots."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from eve_dolphin.database import Database
from eve_dolphin.sync.models import CharacterAsset, CharacterBlueprint, IndustrySnapshot


class IndustrySnapshotRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def start_run(self, character_id: int, started_at: datetime) -> int:
        _validate_identity_time(character_id, started_at)
        with self._database.connect() as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO sync_runs(character_id, sync_kind, status, started_at)
                VALUES (?, 'industry_core', 'running', ?)
                """,
                (character_id, started_at.isoformat()),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not create a sync run ID")
            return cursor.lastrowid

    def fail_run(self, run_id: int, failed_at: datetime, reason: str) -> None:
        if run_id <= 0 or failed_at.tzinfo is None:
            raise ValueError("failed sync run metadata is invalid")
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
        assets: tuple[CharacterAsset, ...],
        blueprints: tuple[CharacterBlueprint, ...],
        assets_last_modified: str | None,
        blueprints_last_modified: str | None,
    ) -> IndustrySnapshot:
        _validate_identity_time(character_id, fetched_at)
        with self._database.connect() as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO industry_snapshots(
                    character_id, fetched_at, assets_last_modified,
                    blueprints_last_modified, asset_count, blueprint_count
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    character_id,
                    fetched_at.isoformat(),
                    assets_last_modified,
                    blueprints_last_modified,
                    len(assets),
                    len(blueprints),
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not create a snapshot ID")
            snapshot_id = cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO character_assets(
                    snapshot_id, item_id, type_id, quantity, location_id,
                    location_type, location_flag, is_singleton, is_blueprint_copy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        snapshot_id,
                        asset.item_id,
                        asset.type_id,
                        asset.quantity,
                        asset.location_id,
                        asset.location_type,
                        asset.location_flag,
                        int(asset.is_singleton),
                        int(asset.is_blueprint_copy)
                        if asset.is_blueprint_copy is not None
                        else None,
                    )
                    for asset in assets
                ),
            )
            connection.executemany(
                """
                INSERT INTO character_blueprints(
                    snapshot_id, item_id, type_id, location_id, location_flag,
                    quantity, time_efficiency, material_efficiency, runs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        snapshot_id,
                        blueprint.item_id,
                        blueprint.type_id,
                        blueprint.location_id,
                        blueprint.location_flag,
                        blueprint.quantity,
                        blueprint.time_efficiency,
                        blueprint.material_efficiency,
                        blueprint.runs,
                    )
                    for blueprint in blueprints
                ),
            )
            connection.execute(
                """
                INSERT INTO industry_current(character_id, snapshot_id) VALUES (?, ?)
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
                raise ValueError("industry sync run is not active")
            connection.execute(
                "UPDATE eve_characters SET last_sync_at = ? WHERE character_id = ?",
                (fetched_at.isoformat(), character_id),
            )
            connection.execute(
                "DELETE FROM industry_snapshots WHERE character_id = ? AND id != ?",
                (character_id, snapshot_id),
            )
        snapshot = self.current(character_id)
        if snapshot is None or snapshot.snapshot_id != snapshot_id:
            raise RuntimeError("activated industry snapshot is unavailable")
        return snapshot

    def current(self, character_id: int) -> IndustrySnapshot | None:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot.id, snapshot.character_id, snapshot.fetched_at,
                       snapshot.asset_count, snapshot.blueprint_count,
                       snapshot.assets_last_modified, snapshot.blueprints_last_modified
                FROM industry_current AS current
                JOIN industry_snapshots AS snapshot ON snapshot.id = current.snapshot_id
                WHERE current.character_id = ?
                """,
                (character_id,),
            ).fetchone()
        return _snapshot_from_row(row) if row is not None else None

    def current_assets(self, character_id: int) -> tuple[CharacterAsset, ...]:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT asset.item_id, asset.type_id, asset.quantity,
                       asset.location_id, asset.location_type, asset.location_flag,
                       asset.is_singleton, asset.is_blueprint_copy
                FROM industry_current AS current
                JOIN character_assets AS asset ON asset.snapshot_id = current.snapshot_id
                WHERE current.character_id = ?
                ORDER BY asset.item_id
                """,
                (character_id,),
            ).fetchall()
        return tuple(_asset_from_row(row) for row in rows)

    def current_blueprints(self, character_id: int) -> tuple[CharacterBlueprint, ...]:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT blueprint.item_id, blueprint.type_id, blueprint.location_id,
                       blueprint.location_flag, blueprint.quantity,
                       blueprint.time_efficiency, blueprint.material_efficiency,
                       blueprint.runs
                FROM industry_current AS current
                JOIN character_blueprints AS blueprint
                    ON blueprint.snapshot_id = current.snapshot_id
                WHERE current.character_id = ?
                ORDER BY blueprint.item_id
                """,
                (character_id,),
            ).fetchall()
        return tuple(_blueprint_from_row(row) for row in rows)


def _validate_identity_time(character_id: int, value: datetime) -> None:
    if character_id <= 0:
        raise ValueError("character_id must be positive")
    if value.tzinfo is None:
        raise ValueError("sync timestamp must include a timezone")


def _snapshot_from_row(row: sqlite3.Row) -> IndustrySnapshot:
    return IndustrySnapshot(
        snapshot_id=int(row["id"]),
        character_id=int(row["character_id"]),
        fetched_at=datetime.fromisoformat(str(row["fetched_at"])),
        asset_count=int(row["asset_count"]),
        blueprint_count=int(row["blueprint_count"]),
        assets_last_modified=(
            str(row["assets_last_modified"]) if row["assets_last_modified"] is not None else None
        ),
        blueprints_last_modified=(
            str(row["blueprints_last_modified"])
            if row["blueprints_last_modified"] is not None
            else None
        ),
    )


def _asset_from_row(row: sqlite3.Row) -> CharacterAsset:
    blueprint_copy = row["is_blueprint_copy"]
    return CharacterAsset(
        item_id=int(row["item_id"]),
        type_id=int(row["type_id"]),
        quantity=int(row["quantity"]),
        location_id=int(row["location_id"]),
        location_type=str(row["location_type"]),
        location_flag=str(row["location_flag"]),
        is_singleton=bool(row["is_singleton"]),
        is_blueprint_copy=bool(blueprint_copy) if blueprint_copy is not None else None,
    )


def _blueprint_from_row(row: sqlite3.Row) -> CharacterBlueprint:
    return CharacterBlueprint(
        item_id=int(row["item_id"]),
        type_id=int(row["type_id"]),
        location_id=int(row["location_id"]),
        location_flag=str(row["location_flag"]),
        quantity=int(row["quantity"]),
        time_efficiency=int(row["time_efficiency"]),
        material_efficiency=int(row["material_efficiency"]),
        runs=int(row["runs"]),
    )
