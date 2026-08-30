"""Persistent local POCO, transport, and wormhole planning profiles."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

from eve_dolphin.database import Database
from eve_dolphin.pi.models import PiProfile, PiTier, SpaceKind

DEFAULT_PROFILES = (
    PiProfile(
        None,
        "Standard Highsec",
        SpaceKind.HIGHSEC,
        True,
        Decimal("5"),
        Decimal("10"),
        Decimal("0"),
        Decimal("60000"),
        Decimal("0"),
        PiTier.RAW,
    ),
    PiProfile(
        None,
        "Wurmloch mit POCO",
        SpaceKind.WORMHOLE,
        True,
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
        Decimal("60000"),
        Decimal("10"),
        PiTier.RAW,
    ),
    PiProfile(
        None,
        "Wurmloch ohne POCO",
        SpaceKind.WORMHOLE,
        False,
        Decimal("0"),
        Decimal("15"),
        Decimal("0"),
        Decimal("500"),
        Decimal("20"),
        PiTier.RAW,
    ),
)


class PiProfileRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def ensure_defaults(self) -> None:
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection, connection:
            count = connection.execute("SELECT COUNT(*) AS count FROM pi_profiles").fetchone()
            if count is None or int(count["count"]) != 0:
                return
            connection.executemany(
                """
                INSERT OR IGNORE INTO pi_profiles(
                    name, space_kind, has_customs_office,
                    import_tax_percent_decimal, export_tax_percent_decimal,
                    transport_isk_per_m3_decimal, cargo_capacity_m3_decimal,
                    risk_markup_percent_decimal, supply_tier, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        profile.name,
                        profile.space_kind.value,
                        int(profile.has_customs_office),
                        str(profile.import_tax_percent),
                        str(profile.export_tax_percent),
                        str(profile.transport_isk_per_m3),
                        str(profile.cargo_capacity_m3),
                        str(profile.risk_markup_percent),
                        int(profile.supply_tier),
                        now,
                    )
                    for profile in DEFAULT_PROFILES
                ),
            )

    def list_all(self) -> tuple[PiProfile, ...]:
        self.ensure_defaults()
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM pi_profiles ORDER BY name COLLATE NOCASE, id"
            ).fetchall()
        return tuple(_profile_from_row(row) for row in rows)

    def get(self, profile_id: int) -> PiProfile | None:
        if profile_id <= 0:
            raise ValueError("PI profile ID must be positive")
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM pi_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        return _profile_from_row(row) if row is not None else None

    def save(self, profile: PiProfile) -> PiProfile:
        now = datetime.now(UTC).isoformat()
        values = (
            profile.name.strip(),
            profile.space_kind.value,
            int(profile.has_customs_office),
            str(profile.import_tax_percent),
            str(profile.export_tax_percent),
            str(profile.transport_isk_per_m3),
            str(profile.cargo_capacity_m3),
            str(profile.risk_markup_percent),
            int(profile.supply_tier),
            now,
        )
        with self._database.connect() as connection, connection:
            if profile.profile_id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO pi_profiles(
                        name, space_kind, has_customs_office,
                        import_tax_percent_decimal, export_tax_percent_decimal,
                        transport_isk_per_m3_decimal, cargo_capacity_m3_decimal,
                        risk_markup_percent_decimal, supply_tier, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("SQLite did not create a PI profile ID")
                profile_id = cursor.lastrowid
            else:
                result = connection.execute(
                    """
                    UPDATE pi_profiles SET
                        name = ?, space_kind = ?, has_customs_office = ?,
                        import_tax_percent_decimal = ?, export_tax_percent_decimal = ?,
                        transport_isk_per_m3_decimal = ?, cargo_capacity_m3_decimal = ?,
                        risk_markup_percent_decimal = ?, supply_tier = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (*values, profile.profile_id),
                )
                if result.rowcount != 1:
                    raise ValueError("PI profile does not exist")
                profile_id = profile.profile_id
        stored = self.get(profile_id)
        if stored is None:
            raise RuntimeError("saved PI profile is unavailable")
        return stored


def _profile_from_row(row: sqlite3.Row) -> PiProfile:
    return PiProfile(
        profile_id=int(row["id"]),
        name=str(row["name"]),
        space_kind=SpaceKind(str(row["space_kind"])),
        has_customs_office=bool(row["has_customs_office"]),
        import_tax_percent=Decimal(str(row["import_tax_percent_decimal"])),
        export_tax_percent=Decimal(str(row["export_tax_percent_decimal"])),
        transport_isk_per_m3=Decimal(str(row["transport_isk_per_m3_decimal"])),
        cargo_capacity_m3=Decimal(str(row["cargo_capacity_m3_decimal"])),
        risk_markup_percent=Decimal(str(row["risk_markup_percent_decimal"])),
        supply_tier=PiTier(int(row["supply_tier"])),
    )
