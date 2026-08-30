from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from eve_dolphin.characters import CharacterRepository, EveCharacter
from eve_dolphin.database import Database
from eve_dolphin.pi import PlanetaryOverviewService
from eve_dolphin.sde import SdeRepository
from eve_dolphin.sync.planetary_models import (
    ExtractorDetails,
    PlanetColony,
    PlanetLink,
    PlanetPin,
    PlanetPinContent,
    PlanetRoute,
)
from eve_dolphin.sync.planetary_repository import PlanetarySnapshotRepository

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def test_overview_combines_complete_colony_status_with_active_sde_names(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path)
    _seed_character(database)
    _seed_sde(database)
    colony = _colony()
    snapshots = PlanetarySnapshotRepository(database)
    run_id = snapshots.start_run(1001, NOW)
    snapshots.activate(run_id, 1001, NOW, (colony,), '"colonies"')

    overview = PlanetaryOverviewService(database, clock=lambda: NOW).list_colonies("de")

    assert len(overview) == 1
    result = overview[0]
    assert result.character_name == "Industrial Pilot"
    assert result.planet_id == 4001
    assert result.pin_count == 5
    assert result.link_count == 1
    assert result.route_count == 1
    assert result.factory_count == 1
    assert result.active_extractors == 1
    assert result.expired_extractors == 1
    assert result.incomplete_extractors == 1
    assert result.extractor_count == 3
    assert result.next_expiry == NOW + timedelta(hours=2)
    assert [(value.name, value.count) for value in result.extractor_products] == [
        ("Wässrige Flüssigkeiten", 3)
    ]
    assert [(value.name, value.quantity) for value in result.stored_contents] == [("Water", 1_250)]
    assert [(value.name, value.count) for value in result.pin_types] == [
        ("Extraktorkontrolleinheit", 3),
        ("Industry Facility", 1),
        ("Lager", 1),
    ]


def test_overview_uses_type_ids_when_no_active_sde_exists(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_character(database)
    snapshots = PlanetarySnapshotRepository(database)
    run_id = snapshots.start_run(1001, NOW)
    snapshots.activate(run_id, 1001, NOW, (_colony(),), None)

    result = PlanetaryOverviewService(database, clock=lambda: NOW).list_colonies("en")[0]

    assert all(value.name is None for value in result.pin_types)
    assert all(value.name is None for value in result.extractor_products)
    assert all(value.name is None for value in result.stored_contents)


def test_type_name_lookup_validates_language_ids_and_active_build(tmp_path: Path) -> None:
    database = _database(tmp_path)
    repository = SdeRepository(database)

    assert repository.type_names((2268,), "de") == {}
    with pytest.raises(ValueError, match="language"):
        repository.type_names((2268,), "fr")
    with pytest.raises(ValueError, match="positive"):
        repository.type_names((0,), "de")

    _seed_sde(database)
    assert repository.type_names((2268, 3645, 999999), "de") == {
        2268: "Wässrige Flüssigkeiten",
        3645: "Water",
    }


def test_overview_rejects_a_naive_clock(tmp_path: Path) -> None:
    database = _database(tmp_path)

    with pytest.raises(ValueError, match="timezone"):
        PlanetaryOverviewService(
            database, clock=lambda: datetime(2026, 8, 30, 12, 0)
        ).list_colonies("de")


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "client.sqlite3", tmp_path / "backups")
    database.initialize()
    return database


def _seed_character(database: Database) -> None:
    CharacterRepository(database).upsert(EveCharacter(1001, "Industrial Pilot", "owner", (), NOW))


def _seed_sde(database: Database) -> None:
    with database.connect() as connection, connection:
        connection.execute(
            """
            INSERT INTO sde_builds(
                build_number, release_date, source_url, archive_sha256, archive_size,
                downloaded_at, import_started_at, imported_at, activated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready')
            """,
            (
                3484357,
                NOW.isoformat(),
                "https://example.invalid/sde.zip",
                "a" * 64,
                1,
                NOW.isoformat(),
                NOW.isoformat(),
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )
        connection.execute("INSERT INTO sde_current(singleton, build_number) VALUES (1, 3484357)")
        connection.execute(
            """
            INSERT INTO sde_categories(
                build_number, category_id, name_de, name_en, published
            ) VALUES (3484357, 1, 'Planetare Industrie', 'Planetary Industry', 1)
            """
        )
        connection.execute(
            """
            INSERT INTO sde_groups(
                build_number, group_id, category_id, name_de, name_en, published
            ) VALUES (3484357, 10, 1, 'PI', 'PI', 1)
            """
        )
        connection.executemany(
            """
            INSERT INTO sde_types(
                build_number, type_id, group_id, market_group_id, name_de, name_en,
                volume, mass, portion_size, published
            ) VALUES (3484357, ?, 10, NULL, ?, ?, NULL, NULL, NULL, 1)
            """,
            (
                (2848, "Extraktorkontrolleinheit", "Extractor Control Unit"),
                (2469, "", "Industry Facility"),
                (2535, "Lager", "Storage Facility"),
                (2268, "Wässrige Flüssigkeiten", "Aqueous Liquids"),
                (3645, "", "Water"),
            ),
        )


def _colony() -> PlanetColony:
    extractor = ExtractorDetails((), 900, Decimal("0.1"), 2268, 100)
    pins = (
        _pin(1, 2848, extractor=extractor, expiry=NOW + timedelta(hours=2)),
        _pin(2, 2848, extractor=extractor, expiry=NOW - timedelta(minutes=1)),
        _pin(3, 2848, extractor=extractor),
        _pin(
            4,
            2469,
            contents=(PlanetPinContent(3645, 50),),
            factory_schematic_id=65,
        ),
        _pin(5, 2535, contents=(PlanetPinContent(3645, 1_200),)),
    )
    return PlanetColony(
        planet_id=4001,
        owner_id=1001,
        solar_system_id=30000142,
        planet_type="temperate",
        last_update=NOW - timedelta(minutes=4),
        upgrade_level=4,
        num_pins=5,
        layout_last_modified='"layout"',
        pins=pins,
        links=(PlanetLink(1, 4, 0),),
        routes=(PlanetRoute(77, 1, 4, 2268, Decimal("100"), ()),),
    )


def _pin(
    pin_id: int,
    type_id: int,
    *,
    extractor: ExtractorDetails | None = None,
    expiry: datetime | None = None,
    contents: tuple[PlanetPinContent, ...] = (),
    factory_schematic_id: int | None = None,
) -> PlanetPin:
    return PlanetPin(
        pin_id=pin_id,
        type_id=type_id,
        latitude=Decimal("0.1"),
        longitude=Decimal("0.2"),
        contents=contents,
        schematic_id=None,
        expiry_time=expiry,
        install_time=NOW - timedelta(days=1) if extractor is not None else None,
        last_cycle_start=NOW - timedelta(minutes=15) if extractor is not None else None,
        extractor_details=extractor,
        factory_schematic_id=factory_schematic_id,
    )
