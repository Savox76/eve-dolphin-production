"""Read-only access to the active local SDE version and import metadata."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime

from eve_dolphin.database import Database
from eve_dolphin.sde.models import SdeBuildStatus


class SdeRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def active_build(self) -> SdeBuildStatus | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT b.build_number, b.release_date, b.imported_at,
                       b.activated_at, b.archive_sha256
                FROM sde_current AS current
                JOIN sde_builds AS b ON b.build_number = current.build_number
                WHERE current.singleton = 1 AND b.status = 'ready'
                """
            ).fetchone()
            if row is None:
                return None
            count_rows = connection.execute(
                """
                SELECT dataset, record_count
                FROM sde_dataset_counts
                WHERE build_number = ?
                ORDER BY dataset
                """,
                (row["build_number"],),
            ).fetchall()
            warning_rows = connection.execute(
                """
                SELECT warning, record_count
                FROM sde_import_warnings
                WHERE build_number = ?
                ORDER BY warning
                """,
                (row["build_number"],),
            ).fetchall()
        return _status_from_rows(row, count_rows, warning_rows)

    def latest_cache_headers(self) -> tuple[str | None, str | None]:
        """Return validators from the most recently downloaded build."""

        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT metadata_etag, metadata_last_modified
                FROM sde_builds
                ORDER BY downloaded_at DESC, build_number DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None, None
        etag = row["metadata_etag"]
        last_modified = row["metadata_last_modified"]
        return (
            str(etag) if etag is not None else None,
            str(last_modified) if last_modified is not None else None,
        )

    def has_pi_planning_data(self) -> bool:
        """Return whether the active build contains the Phase-3 universe catalog."""

        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    EXISTS(
                        SELECT 1 FROM sde_current AS current
                        JOIN sde_solar_systems AS system
                          ON system.build_number = current.build_number
                        WHERE current.singleton = 1
                    ) AS has_systems,
                    EXISTS(
                        SELECT 1 FROM sde_current AS current
                        JOIN sde_planets AS planet
                          ON planet.build_number = current.build_number
                        WHERE current.singleton = 1
                    ) AS has_planets
                """
            ).fetchone()
        return row is not None and bool(row["has_systems"]) and bool(row["has_planets"])

    def type_names(self, type_ids: Iterable[int], language: str) -> dict[int, str]:
        """Resolve type IDs against the active SDE without exposing an inactive build."""

        if language not in {"de", "en"}:
            raise ValueError("unsupported SDE type-name language")
        identifiers = tuple(sorted(set(type_ids)))
        if any(type_id <= 0 for type_id in identifiers):
            raise ValueError("SDE type IDs must be positive")
        if not identifiers:
            return {}
        name_expression = (
            "COALESCE(NULLIF(type.name_de, ''), type.name_en)"
            if language == "de"
            else "type.name_en"
        )
        resolved: dict[int, str] = {}
        with self._database.connect() as connection:
            active = connection.execute(
                "SELECT build_number FROM sde_current WHERE singleton = 1"
            ).fetchone()
            if active is None:
                return {}
            build_number = int(active["build_number"])
            for offset in range(0, len(identifiers), 500):
                chunk = identifiers[offset : offset + 500]
                placeholders = ", ".join("?" for _identifier in chunk)
                rows = connection.execute(
                    f"""
                    SELECT type.type_id, {name_expression} AS display_name
                    FROM sde_types AS type
                    JOIN sde_builds AS build ON build.build_number = type.build_number
                    WHERE type.build_number = ? AND build.status = 'ready'
                      AND type.type_id IN ({placeholders})
                    """,
                    (build_number, *chunk),
                ).fetchall()
                resolved.update((int(row["type_id"]), str(row["display_name"])) for row in rows)
        return resolved


def _status_from_rows(
    row: sqlite3.Row,
    count_rows: list[sqlite3.Row],
    warning_rows: list[sqlite3.Row],
) -> SdeBuildStatus:
    imported_at = row["imported_at"]
    activated_at = row["activated_at"]
    if imported_at is None or activated_at is None:
        raise ValueError("active SDE build has incomplete timestamps")
    return SdeBuildStatus(
        build_number=int(row["build_number"]),
        release_date=datetime.fromisoformat(str(row["release_date"])),
        imported_at=datetime.fromisoformat(str(imported_at)),
        activated_at=datetime.fromisoformat(str(activated_at)),
        archive_sha256=str(row["archive_sha256"]),
        dataset_counts={
            str(count_row["dataset"]): int(count_row["record_count"]) for count_row in count_rows
        },
        warnings={
            str(warning_row["warning"]): int(warning_row["record_count"])
            for warning_row in warning_rows
        },
    )
