"""Streaming, versioned import with atomic activation of a validated SDE build."""

from __future__ import annotations

import hashlib
import json
import secrets
import zipfile
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from typing import cast

from eve_dolphin.database import Database
from eve_dolphin.sde.models import SdeArchive, SdeImportResult
from eve_dolphin.sde.repository import SdeRepository

REQUIRED_FILES: Mapping[str, int] = {
    "_sde.jsonl": 64 * 1024,
    "categories.jsonl": 1024 * 1024,
    "marketGroups.jsonl": 8 * 1024 * 1024,
    "groups.jsonl": 8 * 1024 * 1024,
    "types.jsonl": 256 * 1024 * 1024,
    "blueprints.jsonl": 32 * 1024 * 1024,
    "planetSchematics.jsonl": 2 * 1024 * 1024,
}
MAX_JSON_LINE_BYTES = 2 * 1024 * 1024
BATCH_SIZE = 1000


class SdeArchiveValidationError(ValueError):
    """The archive cannot be trusted as a complete production SDE input."""


class SdeImportError(RuntimeError):
    """The staged build could not be validated or activated."""


class SdeImporter:
    """Import only the production/PI datasets and switch versions in one transaction."""

    def __init__(
        self,
        database: Database,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._database = database
        self._repository = SdeRepository(database)
        self._clock = clock or (lambda: datetime.now(UTC))

    def import_archive(self, archive: SdeArchive) -> SdeImportResult:
        existing = self._repository.active_build()
        if existing is not None and existing.build_number == archive.release.build_number:
            if not secrets.compare_digest(existing.archive_sha256, archive.sha256):
                raise SdeArchiveValidationError("active SDE build has a different archive digest")
            return SdeImportResult(status=existing, activated=False)

        _validate_archive_file(archive)
        started_at = self._now()
        self._start_import(archive, started_at)
        try:
            with zipfile.ZipFile(archive.path) as bundle:
                _validate_bundle_structure(bundle)
                _validate_embedded_release(bundle, archive.release.build_number)
                self._import_categories(bundle, archive.release.build_number)
                self._import_market_groups(bundle, archive.release.build_number)
                self._import_groups(bundle, archive.release.build_number)
                self._import_types(bundle, archive.release.build_number)
                self._import_blueprints(bundle, archive.release.build_number)
                self._import_planet_schematics(bundle, archive.release.build_number)
            self._validate_staged_build(archive.release.build_number)
            self._activate_build(archive.release.build_number)
        except Exception as error:
            self._mark_failed(archive, started_at, type(error).__name__)
            raise

        status = self._repository.active_build()
        if status is None or status.build_number != archive.release.build_number:
            raise SdeImportError("SDE activation did not select the imported build")
        return SdeImportResult(status=status, activated=True)

    def _start_import(self, archive: SdeArchive, started_at: datetime) -> None:
        build_number = archive.release.build_number
        with self._database.connect() as connection, connection:
            current = connection.execute(
                "SELECT build_number FROM sde_current WHERE singleton = 1"
            ).fetchone()
            if current is not None and int(current["build_number"]) == build_number:
                raise SdeImportError("active SDE build cannot be replaced in place")
            connection.execute("DELETE FROM sde_builds WHERE build_number = ?", (build_number,))
            connection.execute(
                """
                INSERT INTO sde_builds(
                    build_number, release_date, source_url, archive_sha256,
                    archive_size, metadata_etag, metadata_last_modified,
                    archive_etag, archive_last_modified, downloaded_at,
                    import_started_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'importing')
                """,
                (
                    build_number,
                    archive.release.release_date.isoformat(),
                    archive.release.archive_url,
                    archive.sha256,
                    archive.size_bytes,
                    archive.release.etag,
                    archive.release.last_modified,
                    archive.etag,
                    archive.last_modified,
                    archive.downloaded_at.isoformat(),
                    started_at.isoformat(),
                ),
            )

    def _import_categories(self, bundle: zipfile.ZipFile, build_number: int) -> None:
        rows = (
            (
                build_number,
                _nonnegative_int(record.get("_key"), "category _key"),
                *_localized_name(record),
                _boolean_int(record.get("published"), "category published"),
            )
            for record in _records(bundle, "categories.jsonl")
        )
        count = self._insert_rows(
            """
            INSERT INTO sde_categories(
                build_number, category_id, name_de, name_en, published
            ) VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._record_count(build_number, "categories", count)

    def _import_market_groups(self, bundle: zipfile.ZipFile, build_number: int) -> None:
        rows = (
            (
                build_number,
                _nonnegative_int(record.get("_key"), "market group _key"),
                _optional_nonnegative_int(record.get("parentGroupID"), "parentGroupID"),
                *_localized_name(record),
                _boolean_int(record.get("hasTypes"), "market group hasTypes"),
            )
            for record in _records(bundle, "marketGroups.jsonl")
        )
        count = self._insert_rows(
            """
            INSERT INTO sde_market_groups(
                build_number, market_group_id, parent_group_id,
                name_de, name_en, has_types
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._record_count(build_number, "market_groups", count)

    def _import_groups(self, bundle: zipfile.ZipFile, build_number: int) -> None:
        rows = (
            (
                build_number,
                _nonnegative_int(record.get("_key"), "group _key"),
                _nonnegative_int(record.get("categoryID"), "group categoryID"),
                *_localized_name(record),
                _boolean_int(record.get("published"), "group published"),
            )
            for record in _records(bundle, "groups.jsonl")
        )
        count = self._insert_rows(
            """
            INSERT INTO sde_groups(
                build_number, group_id, category_id, name_de, name_en, published
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._record_count(build_number, "groups", count)

    def _import_types(self, bundle: zipfile.ZipFile, build_number: int) -> None:
        rows = (
            (
                build_number,
                _nonnegative_int(record.get("_key"), "type _key"),
                _nonnegative_int(record.get("groupID"), "type groupID"),
                _optional_nonnegative_int(record.get("marketGroupID"), "marketGroupID"),
                *_localized_name(record),
                _optional_number(record.get("volume"), "type volume"),
                _optional_number(record.get("mass"), "type mass"),
                _optional_positive_int(record.get("portionSize"), "type portionSize"),
                _boolean_int(record.get("published"), "type published"),
            )
            for record in _records(bundle, "types.jsonl")
        )
        count = self._insert_rows(
            """
            INSERT INTO sde_types(
                build_number, type_id, group_id, market_group_id, name_de,
                name_en, volume, mass, portion_size, published
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._record_count(build_number, "types", count)

    def _import_blueprints(self, bundle: zipfile.ZipFile, build_number: int) -> None:
        blueprint_count = 0
        activity_count = 0
        material_count = 0
        product_count = 0
        with self._database.connect() as connection:
            for record in _records(bundle, "blueprints.jsonl"):
                blueprint_id = _positive_int(record.get("blueprintTypeID"), "blueprintTypeID")
                if blueprint_id != _positive_int(record.get("_key"), "blueprint _key"):
                    raise SdeArchiveValidationError("blueprint keys do not match")
                activity_rows, material_rows, product_rows = _blueprint_rows(
                    build_number, blueprint_id, record.get("activities")
                )
                with connection:
                    connection.execute(
                        """
                        INSERT INTO sde_blueprints(
                            build_number, blueprint_type_id, max_production_limit
                        ) VALUES (?, ?, ?)
                        """,
                        (
                            build_number,
                            blueprint_id,
                            _optional_positive_int(
                                record.get("maxProductionLimit"), "maxProductionLimit"
                            ),
                        ),
                    )
                    connection.executemany(
                        """
                        INSERT INTO sde_blueprint_activities(
                            build_number, blueprint_type_id, activity, time_seconds
                        ) VALUES (?, ?, ?, ?)
                        """,
                        activity_rows,
                    )
                    connection.executemany(
                        """
                        INSERT INTO sde_blueprint_materials(
                            build_number, blueprint_type_id, activity,
                            material_type_id, quantity
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        material_rows,
                    )
                    connection.executemany(
                        """
                        INSERT INTO sde_blueprint_products(
                            build_number, blueprint_type_id, activity,
                            product_type_id, quantity, probability
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        product_rows,
                    )
                blueprint_count += 1
                activity_count += len(activity_rows)
                material_count += len(material_rows)
                product_count += len(product_rows)
        self._record_count(build_number, "blueprints", blueprint_count)
        self._record_count(build_number, "blueprint_activities", activity_count)
        self._record_count(build_number, "blueprint_materials", material_count)
        self._record_count(build_number, "blueprint_products", product_count)

    def _import_planet_schematics(self, bundle: zipfile.ZipFile, build_number: int) -> None:
        schematic_count = 0
        type_count = 0
        with self._database.connect() as connection:
            for record in _records(bundle, "planetSchematics.jsonl"):
                schematic_id = _nonnegative_int(record.get("_key"), "schematic _key")
                type_rows = _schematic_type_rows(build_number, schematic_id, record.get("types"))
                with connection:
                    connection.execute(
                        """
                        INSERT INTO sde_planet_schematics(
                            build_number, schematic_id, cycle_time_seconds,
                            name_de, name_en
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            build_number,
                            schematic_id,
                            _positive_int(record.get("cycleTime"), "schematic cycleTime"),
                            *_localized_name(record),
                        ),
                    )
                    connection.executemany(
                        """
                        INSERT INTO sde_planet_schematic_types(
                            build_number, schematic_id, type_id, is_input, quantity
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        type_rows,
                    )
                schematic_count += 1
                type_count += len(type_rows)
        self._record_count(build_number, "planet_schematics", schematic_count)
        self._record_count(build_number, "planet_schematic_types", type_count)

    def _insert_rows(self, sql: str, rows: Iterable[Sequence[object]]) -> int:
        count = 0
        batch: list[Sequence[object]] = []
        with self._database.connect() as connection:
            for row in rows:
                batch.append(row)
                if len(batch) == BATCH_SIZE:
                    with connection:
                        connection.executemany(sql, batch)
                    count += len(batch)
                    batch.clear()
            if batch:
                with connection:
                    connection.executemany(sql, batch)
                count += len(batch)
        return count

    def _record_count(self, build_number: int, dataset: str, count: int) -> None:
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO sde_dataset_counts(build_number, dataset, record_count)
                VALUES (?, ?, ?)
                """,
                (build_number, dataset, count),
            )

    def _validate_staged_build(self, build_number: int) -> None:
        required_counts = {
            "categories",
            "market_groups",
            "groups",
            "types",
            "blueprints",
            "blueprint_activities",
            "blueprint_materials",
            "blueprint_products",
            "planet_schematics",
            "planet_schematic_types",
        }
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT dataset, record_count FROM sde_dataset_counts
                WHERE build_number = ?
                """,
                (build_number,),
            ).fetchall()
            counts = {str(row["dataset"]): int(row["record_count"]) for row in rows}
            unresolved_materials = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM sde_blueprint_materials AS material
                LEFT JOIN sde_types AS item
                    ON item.build_number = material.build_number
                    AND item.type_id = material.material_type_id
                WHERE material.build_number = ? AND item.type_id IS NULL
                """,
                (build_number,),
            ).fetchone()
            unresolved_products = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM sde_blueprint_products AS product
                LEFT JOIN sde_types AS item
                    ON item.build_number = product.build_number
                    AND item.type_id = product.product_type_id
                WHERE product.build_number = ? AND item.type_id IS NULL
                """,
                (build_number,),
            ).fetchone()
            integrity = connection.execute("PRAGMA foreign_key_check").fetchall()
        if set(counts) != required_counts or any(counts[name] <= 0 for name in required_counts):
            raise SdeImportError("SDE staging counts are incomplete")
        if integrity:
            raise SdeImportError("SDE staging contains broken references")
        assert unresolved_materials is not None
        assert unresolved_products is not None
        warnings = {
            "blueprint_material_type_missing": int(unresolved_materials["count"]),
            "blueprint_product_type_missing": int(unresolved_products["count"]),
        }
        with self._database.connect() as connection, connection:
            connection.executemany(
                """
                INSERT INTO sde_import_warnings(build_number, warning, record_count)
                VALUES (?, ?, ?)
                """,
                (
                    (build_number, warning, count)
                    for warning, count in warnings.items()
                    if count > 0
                ),
            )

    def _activate_build(self, build_number: int) -> None:
        timestamp = self._now().isoformat()
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                UPDATE sde_builds
                SET status = 'ready', imported_at = ?, activated_at = ?,
                    failure_reason = NULL
                WHERE build_number = ? AND status = 'importing'
                """,
                (timestamp, timestamp, build_number),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise SdeImportError("SDE staged build is not ready for activation")
            connection.execute(
                """
                INSERT INTO sde_current(singleton, build_number) VALUES (1, ?)
                ON CONFLICT(singleton) DO UPDATE SET build_number = excluded.build_number
                """,
                (build_number,),
            )

    def _mark_failed(
        self,
        archive: SdeArchive,
        started_at: datetime,
        failure_reason: str,
    ) -> None:
        build_number = archive.release.build_number
        with self._database.connect() as connection, connection:
            current = connection.execute(
                "SELECT build_number FROM sde_current WHERE singleton = 1"
            ).fetchone()
            if current is not None and int(current["build_number"]) == build_number:
                return
            connection.execute("DELETE FROM sde_builds WHERE build_number = ?", (build_number,))
            connection.execute(
                """
                INSERT INTO sde_builds(
                    build_number, release_date, source_url, archive_sha256,
                    archive_size, metadata_etag, metadata_last_modified,
                    archive_etag, archive_last_modified, downloaded_at,
                    import_started_at, status, failure_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'failed', ?)
                """,
                (
                    build_number,
                    archive.release.release_date.isoformat(),
                    archive.release.archive_url,
                    archive.sha256,
                    archive.size_bytes,
                    archive.release.etag,
                    archive.release.last_modified,
                    archive.etag,
                    archive.last_modified,
                    archive.downloaded_at.isoformat(),
                    started_at.isoformat(),
                    failure_reason[:200],
                ),
            )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value


def _validate_archive_file(archive: SdeArchive) -> None:
    try:
        actual_size = archive.path.stat().st_size
    except OSError as error:
        raise SdeArchiveValidationError("SDE archive is not readable") from error
    if actual_size != archive.size_bytes:
        raise SdeArchiveValidationError("SDE archive size changed after download")
    digest = hashlib.sha256()
    try:
        with archive.path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise SdeArchiveValidationError("SDE archive cannot be hashed") from error
    if not secrets.compare_digest(digest.hexdigest(), archive.sha256):
        raise SdeArchiveValidationError("SDE archive digest changed after download")


def _validate_bundle_structure(bundle: zipfile.ZipFile) -> None:
    names = bundle.namelist()
    if len(names) != len(set(names)):
        raise SdeArchiveValidationError("SDE archive contains duplicate entries")
    for filename, size_limit in REQUIRED_FILES.items():
        try:
            info = bundle.getinfo(filename)
        except KeyError as error:
            raise SdeArchiveValidationError(
                f"SDE archive is missing required dataset {filename}"
            ) from error
        if info.is_dir() or info.flag_bits & 0x1:
            raise SdeArchiveValidationError("SDE dataset is a directory or encrypted")
        if info.file_size <= 0 or info.file_size > size_limit:
            raise SdeArchiveValidationError(f"SDE dataset {filename} is outside its size limit")
        if info.compress_size <= 0 or info.file_size / info.compress_size > 500:
            raise SdeArchiveValidationError(
                f"SDE dataset {filename} has an unsafe compression ratio"
            )


def _validate_embedded_release(bundle: zipfile.ZipFile, expected_build: int) -> None:
    records = tuple(_records(bundle, "_sde.jsonl"))
    matches = [record for record in records if record.get("_key") == "sde"]
    if len(matches) != 1:
        raise SdeArchiveValidationError("SDE archive has invalid embedded metadata")
    actual_build = _positive_int(matches[0].get("buildNumber"), "embedded buildNumber")
    if actual_build != expected_build:
        raise SdeArchiveValidationError("SDE archive build does not match latest metadata")


def _records(bundle: zipfile.ZipFile, filename: str) -> Iterator[dict[str, object]]:
    with bundle.open(filename) as source:
        line_number = 0
        while True:
            raw_line = source.readline(MAX_JSON_LINE_BYTES + 1)
            if not raw_line:
                break
            line_number += 1
            if len(raw_line) > MAX_JSON_LINE_BYTES:
                raise SdeArchiveValidationError(f"SDE {filename} line exceeds size limit")
            if not raw_line.strip():
                continue
            try:
                payload = cast(object, json.loads(raw_line))
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise SdeArchiveValidationError(
                    f"SDE {filename} contains invalid JSON at line {line_number}"
                ) from error
            if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
                raise SdeArchiveValidationError(
                    f"SDE {filename} record at line {line_number} is not an object"
                )
            yield cast(dict[str, object], payload)


def _localized_name(record: Mapping[str, object]) -> tuple[str, str]:
    value = record.get("name")
    if not isinstance(value, dict):
        raise SdeArchiveValidationError("SDE record has no localized name")
    names = cast(dict[object, object], value)
    english = names.get("en")
    if not isinstance(english, str) or not english.strip():
        raise SdeArchiveValidationError("SDE record has no English name")
    german = names.get("de")
    return (
        german if isinstance(german, str) and german.strip() else english,
        english,
    )


def _blueprint_rows(
    build_number: int,
    blueprint_id: int,
    raw_activities: object,
) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]], list[tuple[object, ...]]]:
    if not isinstance(raw_activities, dict) or not raw_activities:
        raise SdeArchiveValidationError("blueprint has no activities")
    activities = cast(dict[object, object], raw_activities)
    activity_rows: list[tuple[object, ...]] = []
    material_rows: list[tuple[object, ...]] = []
    product_rows: list[tuple[object, ...]] = []
    for raw_name, raw_activity in activities.items():
        if not isinstance(raw_name, str) or not raw_name or not isinstance(raw_activity, dict):
            raise SdeArchiveValidationError("blueprint activity is invalid")
        activity = cast(dict[object, object], raw_activity)
        activity_rows.append(
            (
                build_number,
                blueprint_id,
                raw_name,
                _optional_nonnegative_int(activity.get("time"), "activity time"),
            )
        )
        for item in _object_list(activity.get("materials"), "activity materials"):
            material_rows.append(
                (
                    build_number,
                    blueprint_id,
                    raw_name,
                    _positive_int(item.get("typeID"), "material typeID"),
                    _positive_int(item.get("quantity"), "material quantity"),
                )
            )
        for item in _object_list(activity.get("products"), "activity products"):
            probability = _optional_number(item.get("probability"), "product probability")
            if probability is not None and not 0 <= probability <= 1:
                raise SdeArchiveValidationError("product probability is outside 0..1")
            product_rows.append(
                (
                    build_number,
                    blueprint_id,
                    raw_name,
                    _positive_int(item.get("typeID"), "product typeID"),
                    _positive_int(item.get("quantity"), "product quantity"),
                    probability,
                )
            )
    return activity_rows, material_rows, product_rows


def _schematic_type_rows(
    build_number: int,
    schematic_id: int,
    raw_types: object,
) -> list[tuple[object, ...]]:
    items = _object_list(raw_types, "schematic types", required=True)
    return [
        (
            build_number,
            schematic_id,
            _positive_int(item.get("_key"), "schematic type _key"),
            _boolean_int(item.get("isInput"), "schematic isInput"),
            _positive_int(item.get("quantity"), "schematic quantity"),
        )
        for item in items
    ]


def _object_list(
    value: object,
    name: str,
    *,
    required: bool = False,
) -> tuple[dict[object, object], ...]:
    if value is None and not required:
        return ()
    if not isinstance(value, list) or (required and not value):
        raise SdeArchiveValidationError(f"{name} is not a valid list")
    if not all(isinstance(item, dict) for item in value):
        raise SdeArchiveValidationError(f"{name} contains a non-object")
    return tuple(cast(list[dict[object, object]], value))


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SdeArchiveValidationError(f"{name} must be a positive integer")
    return value


def _nonnegative_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SdeArchiveValidationError(f"{name} must be a non-negative integer")
    return value


def _optional_positive_int(value: object, name: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, name)


def _optional_nonnegative_int(value: object, name: str) -> int | None:
    if value is None:
        return None
    return _nonnegative_int(value, name)


def _optional_number(value: object, name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SdeArchiveValidationError(f"{name} must be numeric")
    return float(value)


def _boolean_int(value: object, name: str) -> int:
    if not isinstance(value, bool):
        raise SdeArchiveValidationError(f"{name} must be a boolean")
    return int(value)
