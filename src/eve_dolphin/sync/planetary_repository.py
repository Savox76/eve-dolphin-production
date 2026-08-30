"""Atomic persistence for complete per-character planetary layouts."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal

from eve_dolphin.database import Database
from eve_dolphin.sync.planetary_models import (
    ExtractorDetails,
    PlanetarySnapshot,
    PlanetColony,
    PlanetLink,
    PlanetPin,
    PlanetRoute,
)


class PlanetarySnapshotRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def start_run(self, character_id: int, started_at: datetime) -> int:
        _validate_identity_time(character_id, started_at)
        with self._database.connect() as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO sync_runs(character_id, sync_kind, status, started_at)
                VALUES (?, 'planetary', 'running', ?)
                """,
                (character_id, started_at.isoformat()),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not create a planetary sync run ID")
            return cursor.lastrowid

    def fail_run(self, run_id: int, failed_at: datetime, reason: str) -> None:
        if run_id <= 0 or failed_at.tzinfo is None:
            raise ValueError("failed planetary sync run metadata is invalid")
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
        colonies: tuple[PlanetColony, ...],
        colonies_last_modified: str | None,
    ) -> PlanetarySnapshot:
        _validate_identity_time(character_id, fetched_at)
        pin_count = sum(len(colony.pins) for colony in colonies)
        link_count = sum(len(colony.links) for colony in colonies)
        route_count = sum(len(colony.routes) for colony in colonies)
        with self._database.connect() as connection, connection:
            snapshot_id = self._insert_snapshot(
                connection,
                character_id,
                fetched_at,
                colonies_last_modified,
                len(colonies),
                pin_count,
                link_count,
                route_count,
            )
            for colony in colonies:
                self._insert_colony(connection, snapshot_id, colony)
            connection.execute(
                """
                INSERT INTO planetary_current(character_id, snapshot_id) VALUES (?, ?)
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
                raise ValueError("planetary sync run is not active")
            connection.execute(
                "UPDATE eve_characters SET last_sync_at = ? WHERE character_id = ?",
                (fetched_at.isoformat(), character_id),
            )
            connection.execute(
                "DELETE FROM planetary_snapshots WHERE character_id = ? AND id != ?",
                (character_id, snapshot_id),
            )
        snapshot = self.current(character_id)
        if snapshot is None or snapshot.snapshot_id != snapshot_id:
            raise RuntimeError("activated planetary snapshot is unavailable")
        return snapshot

    def current(self, character_id: int) -> PlanetarySnapshot | None:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot.id, snapshot.character_id, snapshot.fetched_at,
                       snapshot.colony_count, snapshot.pin_count, snapshot.link_count,
                       snapshot.route_count, snapshot.colonies_last_modified
                FROM planetary_current AS current
                JOIN planetary_snapshots AS snapshot ON snapshot.id = current.snapshot_id
                WHERE current.character_id = ?
                """,
                (character_id,),
            ).fetchone()
        return _snapshot_from_row(row) if row is not None else None

    def current_colonies(self, character_id: int) -> tuple[PlanetColony, ...]:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        with self._database.connect() as connection:
            colony_rows = connection.execute(
                """
                SELECT planet.* FROM planetary_current AS current
                JOIN character_planets AS planet ON planet.snapshot_id = current.snapshot_id
                WHERE current.character_id = ?
                ORDER BY planet.planet_id
                """,
                (character_id,),
            ).fetchall()
            return tuple(_colony_from_database(connection, row) for row in colony_rows)

    @staticmethod
    def _insert_snapshot(
        connection: sqlite3.Connection,
        character_id: int,
        fetched_at: datetime,
        last_modified: str | None,
        colony_count: int,
        pin_count: int,
        link_count: int,
        route_count: int,
    ) -> int:
        cursor = connection.execute(
            """
            INSERT INTO planetary_snapshots(
                character_id, fetched_at, colonies_last_modified, colony_count,
                pin_count, link_count, route_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                character_id,
                fetched_at.isoformat(),
                last_modified,
                colony_count,
                pin_count,
                link_count,
                route_count,
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not create a planetary snapshot ID")
        return cursor.lastrowid

    @staticmethod
    def _insert_colony(
        connection: sqlite3.Connection, snapshot_id: int, colony: PlanetColony
    ) -> None:
        connection.execute(
            """
            INSERT INTO character_planets(
                snapshot_id, planet_id, owner_id, solar_system_id, planet_type,
                last_update, upgrade_level, num_pins, layout_last_modified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                colony.planet_id,
                colony.owner_id,
                colony.solar_system_id,
                colony.planet_type,
                colony.last_update.isoformat(),
                colony.upgrade_level,
                colony.num_pins,
                colony.layout_last_modified,
            ),
        )
        for pin in colony.pins:
            _insert_pin(connection, snapshot_id, colony.planet_id, pin)
        connection.executemany(
            """
            INSERT INTO planet_links(
                snapshot_id, planet_id, source_pin_id, destination_pin_id, link_level
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                (
                    snapshot_id,
                    colony.planet_id,
                    link.source_pin_id,
                    link.destination_pin_id,
                    link.link_level,
                )
                for link in colony.links
            ),
        )
        for route in colony.routes:
            connection.execute(
                """
                INSERT INTO planet_routes(
                    snapshot_id, planet_id, route_id, source_pin_id,
                    destination_pin_id, content_type_id, quantity_decimal
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    colony.planet_id,
                    route.route_id,
                    route.source_pin_id,
                    route.destination_pin_id,
                    route.content_type_id,
                    str(route.quantity),
                ),
            )
            connection.executemany(
                """
                INSERT INTO planet_route_waypoints(
                    snapshot_id, planet_id, route_id, position, pin_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    (snapshot_id, colony.planet_id, route.route_id, position, pin_id)
                    for position, pin_id in enumerate(route.waypoints)
                ),
            )


def _insert_pin(
    connection: sqlite3.Connection, snapshot_id: int, planet_id: int, pin: PlanetPin
) -> None:
    extractor = pin.extractor_details
    connection.execute(
        """
        INSERT INTO planet_pins(
            snapshot_id, planet_id, pin_id, type_id, latitude_decimal,
            longitude_decimal, schematic_id, expiry_time, install_time,
            last_cycle_start, has_extractor_details, extractor_cycle_time,
            extractor_head_radius_decimal,
            extractor_product_type_id, extractor_qty_per_cycle, factory_schematic_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            planet_id,
            pin.pin_id,
            pin.type_id,
            str(pin.latitude),
            str(pin.longitude),
            pin.schematic_id,
            _isoformat(pin.expiry_time),
            _isoformat(pin.install_time),
            _isoformat(pin.last_cycle_start),
            int(extractor is not None),
            extractor.cycle_time if extractor else None,
            str(extractor.head_radius) if extractor and extractor.head_radius is not None else None,
            extractor.product_type_id if extractor else None,
            extractor.qty_per_cycle if extractor else None,
            pin.factory_schematic_id,
        ),
    )
    connection.executemany(
        """
        INSERT INTO planet_pin_contents(
            snapshot_id, planet_id, pin_id, type_id, amount
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            (snapshot_id, planet_id, pin.pin_id, content.type_id, content.amount)
            for content in pin.contents
        ),
    )
    if extractor is not None:
        connection.executemany(
            """
            INSERT INTO planet_extractor_heads(
                snapshot_id, planet_id, pin_id, head_id, latitude_decimal, longitude_decimal
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    snapshot_id,
                    planet_id,
                    pin.pin_id,
                    head.head_id,
                    str(head.latitude),
                    str(head.longitude),
                )
                for head in extractor.heads
            ),
        )


def _colony_from_database(connection: sqlite3.Connection, row: sqlite3.Row) -> PlanetColony:
    snapshot_id = int(row["snapshot_id"])
    planet_id = int(row["planet_id"])
    pins = tuple(
        _pin_from_database(connection, pin_row)
        for pin_row in connection.execute(
            """
            SELECT * FROM planet_pins
            WHERE snapshot_id = ? AND planet_id = ? ORDER BY pin_id
            """,
            (snapshot_id, planet_id),
        ).fetchall()
    )
    links = tuple(
        _link_from_row(link_row)
        for link_row in connection.execute(
            """
            SELECT * FROM planet_links
            WHERE snapshot_id = ? AND planet_id = ?
            ORDER BY source_pin_id, destination_pin_id
            """,
            (snapshot_id, planet_id),
        ).fetchall()
    )
    routes = tuple(
        _route_from_database(connection, route_row)
        for route_row in connection.execute(
            """
            SELECT * FROM planet_routes
            WHERE snapshot_id = ? AND planet_id = ? ORDER BY route_id
            """,
            (snapshot_id, planet_id),
        ).fetchall()
    )
    return PlanetColony(
        planet_id=planet_id,
        owner_id=int(row["owner_id"]),
        solar_system_id=int(row["solar_system_id"]),
        planet_type=str(row["planet_type"]),
        last_update=datetime.fromisoformat(str(row["last_update"])),
        upgrade_level=int(row["upgrade_level"]),
        num_pins=int(row["num_pins"]),
        layout_last_modified=(
            str(row["layout_last_modified"]) if row["layout_last_modified"] is not None else None
        ),
        pins=pins,
        links=links,
        routes=routes,
    )


def _pin_from_database(connection: sqlite3.Connection, row: sqlite3.Row) -> PlanetPin:
    from eve_dolphin.sync.planetary_models import ExtractorHead, PlanetPinContent

    identity = (int(row["snapshot_id"]), int(row["planet_id"]), int(row["pin_id"]))
    contents = tuple(
        PlanetPinContent(int(value["type_id"]), int(value["amount"]))
        for value in connection.execute(
            """
            SELECT type_id, amount FROM planet_pin_contents
            WHERE snapshot_id = ? AND planet_id = ? AND pin_id = ? ORDER BY type_id
            """,
            identity,
        ).fetchall()
    )
    head_rows = connection.execute(
        """
        SELECT head_id, latitude_decimal, longitude_decimal FROM planet_extractor_heads
        WHERE snapshot_id = ? AND planet_id = ? AND pin_id = ? ORDER BY head_id
        """,
        identity,
    ).fetchall()
    extractor: ExtractorDetails | None = None
    extractor_present = bool(row["has_extractor_details"])
    if extractor_present:
        extractor = ExtractorDetails(
            heads=tuple(
                ExtractorHead(
                    int(value["head_id"]),
                    Decimal(str(value["latitude_decimal"])),
                    Decimal(str(value["longitude_decimal"])),
                )
                for value in head_rows
            ),
            cycle_time=_optional_int(row["extractor_cycle_time"]),
            head_radius=_optional_decimal(row["extractor_head_radius_decimal"]),
            product_type_id=_optional_int(row["extractor_product_type_id"]),
            qty_per_cycle=_optional_int(row["extractor_qty_per_cycle"]),
        )
    return PlanetPin(
        pin_id=identity[2],
        type_id=int(row["type_id"]),
        latitude=Decimal(str(row["latitude_decimal"])),
        longitude=Decimal(str(row["longitude_decimal"])),
        contents=contents,
        schematic_id=_optional_int(row["schematic_id"]),
        expiry_time=_optional_datetime(row["expiry_time"]),
        install_time=_optional_datetime(row["install_time"]),
        last_cycle_start=_optional_datetime(row["last_cycle_start"]),
        extractor_details=extractor,
        factory_schematic_id=_optional_int(row["factory_schematic_id"]),
    )


def _link_from_row(row: sqlite3.Row) -> PlanetLink:
    return PlanetLink(
        int(row["source_pin_id"]), int(row["destination_pin_id"]), int(row["link_level"])
    )


def _route_from_database(connection: sqlite3.Connection, row: sqlite3.Row) -> PlanetRoute:
    waypoints = tuple(
        int(value["pin_id"])
        for value in connection.execute(
            """
            SELECT pin_id FROM planet_route_waypoints
            WHERE snapshot_id = ? AND planet_id = ? AND route_id = ? ORDER BY position
            """,
            (row["snapshot_id"], row["planet_id"], row["route_id"]),
        ).fetchall()
    )
    return PlanetRoute(
        route_id=int(row["route_id"]),
        source_pin_id=int(row["source_pin_id"]),
        destination_pin_id=int(row["destination_pin_id"]),
        content_type_id=int(row["content_type_id"]),
        quantity=Decimal(str(row["quantity_decimal"])),
        waypoints=waypoints,
    )


def _snapshot_from_row(row: sqlite3.Row) -> PlanetarySnapshot:
    return PlanetarySnapshot(
        snapshot_id=int(row["id"]),
        character_id=int(row["character_id"]),
        fetched_at=datetime.fromisoformat(str(row["fetched_at"])),
        colony_count=int(row["colony_count"]),
        pin_count=int(row["pin_count"]),
        link_count=int(row["link_count"]),
        route_count=int(row["route_count"]),
        colonies_last_modified=(
            str(row["colonies_last_modified"])
            if row["colonies_last_modified"] is not None
            else None
        ),
    )


def _validate_identity_time(character_id: int, value: datetime) -> None:
    if character_id <= 0:
        raise ValueError("character_id must be positive")
    if value.tzinfo is None:
        raise ValueError("planetary sync timestamp must include a timezone")


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _optional_datetime(value: object) -> datetime | None:
    return datetime.fromisoformat(str(value)) if value is not None else None


def _optional_decimal(value: object) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _optional_int(value: object) -> int | None:
    return int(str(value)) if value is not None else None
