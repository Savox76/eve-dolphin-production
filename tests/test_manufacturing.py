from __future__ import annotations

from pathlib import Path

from eve_dolphin.database import Database
from eve_dolphin.manufacturing import (
    BlueprintKind,
    ManufacturingPlannerService,
)


def test_owned_blueprints_join_active_sde_and_character_snapshots(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_manufacturing(database)

    blueprints = ManufacturingPlannerService(database).list_blueprints("de")

    assert len(blueprints) == 2
    original, copy = blueprints
    assert original.product_name == "Testprodukt"
    assert original.blueprint_name == "Test Blueprint"
    assert original.character_name == "Main-Char"
    assert original.kind is BlueprintKind.ORIGINAL
    assert original.available_runs is None
    assert copy.kind is BlueprintKind.COPY
    assert copy.available_runs == 3
    assert [(item.name, item.quantity_per_run) for item in original.materials] == [
        ("Kleinteil", 1),
        ("Testmaterial", 7),
    ]


def test_manufacturing_plan_applies_job_level_me_te_and_location_stock(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path)
    _seed_manufacturing(database)
    service = ManufacturingPlannerService(database)
    original = service.list_blueprints("de")[0]

    plan = service.calculate(original, 10)

    assert plan.runs == 5
    assert plan.planned_output == 10
    assert plan.surplus == 0
    assert plan.duration_seconds == 240
    assert plan.can_run_with_blueprint is True
    assert plan.materials_available_at_location is False
    assert [
        (
            line.name,
            line.required_quantity,
            line.available_at_location,
            line.available_total,
            line.missing_at_location,
        )
        for line in plan.materials
    ] == [
        ("Kleinteil", 5, 0, 0, 5),
        ("Testmaterial", 32, 20, 35, 12),
    ]


def test_bpc_run_limit_is_reported_without_changing_material_need(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_manufacturing(database)
    service = ManufacturingPlannerService(database)
    copy = service.list_blueprints("en")[1]

    plan = service.calculate(copy, 10)

    assert plan.runs == 5
    assert plan.blueprint_run_shortfall == 2
    assert plan.can_run_with_blueprint is False
    assert plan.materials[1].required_quantity == 32


def test_manufacturing_catalog_is_empty_without_active_sde_or_snapshot(tmp_path: Path) -> None:
    service = ManufacturingPlannerService(_database(tmp_path))

    assert service.list_blueprints("de") == ()


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "client.sqlite3")
    database.initialize()
    return database


def _seed_manufacturing(database: Database) -> None:
    with database.connect() as connection, connection:
        connection.execute(
            """
            INSERT INTO sde_builds(
                build_number, release_date, source_url, archive_sha256, archive_size,
                downloaded_at, import_started_at, imported_at, activated_at, status
            ) VALUES (
                100, '2026-08-31T00:00:00+00:00', 'https://example.invalid/sde',
                ?, 1, '2026-08-31T00:00:00+00:00', '2026-08-31T00:00:00+00:00',
                '2026-08-31T00:00:00+00:00', '2026-08-31T00:00:00+00:00', 'ready'
            )
            """,
            ("a" * 64,),
        )
        connection.execute("INSERT INTO sde_current VALUES (1, 100)")
        connection.execute("INSERT INTO sde_categories VALUES (100, 1, 'Kategorie', 'Category', 1)")
        connection.execute(
            "INSERT INTO sde_market_groups VALUES (100, 1, NULL, 'Markt', 'Market', 1)"
        )
        connection.execute("INSERT INTO sde_groups VALUES (100, 1, 1, 'Gruppe', 'Group', 1)")
        connection.executemany(
            """
            INSERT INTO sde_types(
                build_number, type_id, group_id, market_group_id,
                name_de, name_en, volume, portion_size, published
            ) VALUES (100, ?, 1, 1, ?, ?, 1, 1, 1)
            """,
            (
                (1000, "Test Blueprint", "Test Blueprint"),
                (1001, "Testprodukt", "Test Product"),
                (1002, "Testmaterial", "Test Material"),
                (1003, "Kleinteil", "Small Part"),
            ),
        )
        connection.execute("INSERT INTO sde_blueprints VALUES (100, 1000, 100)")
        connection.execute(
            "INSERT INTO sde_blueprint_activities VALUES (100, 1000, 'manufacturing', 60)"
        )
        connection.executemany(
            "INSERT INTO sde_blueprint_materials VALUES (100, 1000, 'manufacturing', ?, ?)",
            ((1002, 7), (1003, 1)),
        )
        connection.execute(
            "INSERT INTO sde_blueprint_products VALUES (100, 1000, 'manufacturing', 1001, 2, NULL)"
        )
        connection.execute(
            """
            INSERT INTO eve_characters(
                character_id, character_name, granted_scopes_json, linked_at
            ) VALUES (7, 'Main-Char', '[]', '2026-08-31T00:00:00+00:00')
            """
        )
        cursor = connection.execute(
            """
            INSERT INTO industry_snapshots(
                character_id, fetched_at, asset_count, blueprint_count
            ) VALUES (7, '2026-08-31T00:00:00+00:00', 2, 2)
            """
        )
        assert cursor.lastrowid is not None
        snapshot_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO industry_current VALUES (7, ?)",
            (snapshot_id,),
        )
        connection.executemany(
            """
            INSERT INTO character_blueprints(
                snapshot_id, item_id, type_id, location_id, location_flag,
                quantity, time_efficiency, material_efficiency, runs
            ) VALUES (?, ?, 1000, 6001, 'Hangar', ?, 20, 10, ?)
            """,
            (
                (snapshot_id, 7001, -1, -1),
                (snapshot_id, 7002, -2, 3),
            ),
        )
        connection.executemany(
            """
            INSERT INTO character_assets(
                snapshot_id, item_id, type_id, quantity, location_id,
                location_type, location_flag, is_singleton
            ) VALUES (?, ?, 1002, ?, ?, 'station', 'Hangar', 0)
            """,
            (
                (snapshot_id, 8001, 20, 6001),
                (snapshot_id, 8002, 15, 6002),
            ),
        )
