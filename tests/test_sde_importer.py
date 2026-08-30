from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eve_dolphin.database import Database
from eve_dolphin.sde.importer import SdeArchiveValidationError, SdeImporter
from eve_dolphin.sde.models import SdeArchive, SdeRelease
from eve_dolphin.sde.repository import SdeRepository

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def test_import_normalizes_and_atomically_activates_production_data(tmp_path: Path) -> None:
    database = _database(tmp_path)
    archive = _archive(tmp_path, 101)

    first = SdeImporter(database, clock=lambda: NOW).import_archive(archive)
    second = SdeImporter(database, clock=lambda: NOW).import_archive(archive)

    assert first.activated is True
    assert second.activated is False
    assert first.status.build_number == 101
    assert first.status.dataset_counts["types"] == 6
    assert first.status.dataset_counts["blueprint_materials"] == 1
    assert first.status.dataset_counts["planet_schematic_types"] == 2
    assert first.status.dataset_counts["solar_systems"] == 1
    assert first.status.dataset_counts["planets"] == 1
    assert first.status.warnings == {}
    with database.connect() as connection:
        material = connection.execute(
            """
            SELECT material_type_id, quantity FROM sde_blueprint_materials
            WHERE build_number = 101 AND blueprint_type_id = 100
            """
        ).fetchone()
        product = connection.execute(
            """
            SELECT product_type_id, quantity FROM sde_blueprint_products
            WHERE build_number = 101 AND blueprint_type_id = 100
            """
        ).fetchone()
    assert material is not None and tuple(material) == (101, 2)
    assert product is not None and tuple(product) == (102, 1)


def test_invalid_new_build_preserves_previous_active_build(tmp_path: Path) -> None:
    database = _database(tmp_path)
    importer = SdeImporter(database, clock=lambda: NOW)
    importer.import_archive(_archive(tmp_path, 101))
    invalid = _archive(tmp_path, 102, omitted_file="types.jsonl")

    with pytest.raises(SdeArchiveValidationError):
        importer.import_archive(invalid)

    active = SdeRepository(database).active_build()
    assert active is not None and active.build_number == 101
    with database.connect() as connection:
        failed = connection.execute(
            "SELECT status, failure_reason FROM sde_builds WHERE build_number = 102"
        ).fetchone()
        staged_rows = connection.execute(
            "SELECT COUNT(*) FROM sde_categories WHERE build_number = 102"
        ).fetchone()
    assert failed is not None and tuple(failed) == ("failed", "SdeArchiveValidationError")
    assert staged_rows is not None and staged_rows[0] == 0


def test_changed_archive_is_rejected_before_staging(tmp_path: Path) -> None:
    database = _database(tmp_path)
    archive = _archive(tmp_path, 101)
    archive.path.write_bytes(archive.path.read_bytes() + b"changed")

    with pytest.raises(SdeArchiveValidationError, match="size changed"):
        SdeImporter(database, clock=lambda: NOW).import_archive(archive)

    with database.connect() as connection:
        count = connection.execute("SELECT COUNT(*) FROM sde_builds").fetchone()
    assert count is not None and count[0] == 0


def test_official_orphan_blueprint_reference_is_recorded_as_warning(tmp_path: Path) -> None:
    database = _database(tmp_path)
    archive = _archive(tmp_path, 101, material_type_id=999)

    result = SdeImporter(database, clock=lambda: NOW).import_archive(archive)

    assert result.status.warnings == {"blueprint_material_type_missing": 1}


def test_active_legacy_build_is_atomically_enriched_for_pi_planning(tmp_path: Path) -> None:
    database = _database(tmp_path)
    archive = _archive(tmp_path, 101)
    importer = SdeImporter(database, clock=lambda: NOW)
    importer.import_archive(archive)
    with database.connect() as connection, connection:
        connection.execute("DELETE FROM sde_planets WHERE build_number = 101")
        connection.execute(
            "DELETE FROM sde_dataset_counts WHERE build_number = 101 "
            "AND dataset IN ('type_capacities', 'solar_systems', 'planets')"
        )

    result = importer.import_archive(archive)

    assert result.activated is False
    assert result.status.dataset_counts["type_capacities"] == 6
    assert result.status.dataset_counts["solar_systems"] == 1
    assert result.status.dataset_counts["planets"] == 1
    assert SdeRepository(database).has_pi_planning_data()


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "eve-dolphin.sqlite3")
    database.initialize()
    return database


def _archive(
    tmp_path: Path,
    build_number: int,
    *,
    omitted_file: str | None = None,
    material_type_id: int = 101,
) -> SdeArchive:
    datasets = _datasets(build_number, material_type_id)
    path = tmp_path / f"sde-{build_number}.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for filename, records in datasets.items():
            if filename != omitted_file:
                payload = "".join(json.dumps(record) + "\n" for record in records)
                bundle.writestr(filename, payload)
    content = path.read_bytes()
    release = SdeRelease(
        build_number=build_number,
        release_date=datetime(2026, 8, 28, 11, 7, 12, tzinfo=UTC),
        archive_url=f"https://example.invalid/sde-{build_number}.zip",
        etag='"metadata"',
        last_modified="Fri, 28 Aug 2026 11:07:12 GMT",
    )
    return SdeArchive(
        release=release,
        path=path,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        downloaded_at=NOW,
        etag='"archive"',
    )


def _datasets(build_number: int, material_type_id: int) -> dict[str, list[object]]:
    return {
        "_sde.jsonl": [{"_key": "sde", "buildNumber": build_number}],
        "categories.jsonl": [{"_key": 1, "name": _name("Category"), "published": True}],
        "marketGroups.jsonl": [{"_key": 10, "name": _name("Market"), "hasTypes": True}],
        "groups.jsonl": [{"_key": 2, "categoryID": 1, "name": _name("Group"), "published": True}],
        "types.jsonl": [
            {
                "_key": type_id,
                "groupID": 2,
                "marketGroupID": 10,
                "name": _name(label),
                "published": True,
                "portionSize": 1,
            }
            for type_id, label in (
                (11, "Temperate Planet"),
                (100, "Blueprint"),
                (101, "Material"),
                (102, "Product"),
                (103, "PI Input"),
                (104, "PI Output"),
            )
        ],
        "blueprints.jsonl": [
            {
                "_key": 100,
                "blueprintTypeID": 100,
                "maxProductionLimit": 10,
                "activities": {
                    "manufacturing": {
                        "time": 60,
                        "materials": [{"typeID": material_type_id, "quantity": 2}],
                        "products": [{"typeID": 102, "quantity": 1}],
                    }
                },
            }
        ],
        "planetSchematics.jsonl": [
            {
                "_key": 7,
                "cycleTime": 1800,
                "name": _name("PI Recipe"),
                "types": [
                    {"_key": 103, "isInput": True, "quantity": 40},
                    {"_key": 104, "isInput": False, "quantity": 5},
                ],
            }
        ],
        "mapSolarSystems.jsonl": [
            {
                "_key": 30000142,
                "constellationID": 20000020,
                "regionID": 10000002,
                "name": _name("Jita"),
                "securityStatus": 0.9459,
            }
        ],
        "mapPlanets.jsonl": [
            {
                "_key": 40009077,
                "solarSystemID": 30000142,
                "celestialIndex": 4,
                "typeID": 11,
            }
        ],
    }


def _name(value: str) -> dict[str, str]:
    return {"de": value, "en": value}
