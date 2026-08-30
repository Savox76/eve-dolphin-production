"""Validated internal representations of character production resources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast

from eve_dolphin.esi.errors import EsiProtocolError

LOCATION_TYPES = frozenset({"station", "solar_system", "item", "other"})


@dataclass(frozen=True, slots=True)
class CharacterAsset:
    item_id: int
    type_id: int
    quantity: int
    location_id: int
    location_type: str
    location_flag: str
    is_singleton: bool
    is_blueprint_copy: bool | None


@dataclass(frozen=True, slots=True)
class CharacterBlueprint:
    item_id: int
    type_id: int
    location_id: int
    location_flag: str
    quantity: int
    time_efficiency: int
    material_efficiency: int
    runs: int


@dataclass(frozen=True, slots=True)
class IndustrySnapshot:
    snapshot_id: int
    character_id: int
    fetched_at: datetime
    asset_count: int
    blueprint_count: int
    assets_last_modified: str | None
    blueprints_last_modified: str | None


@dataclass(frozen=True, slots=True)
class IndustrySyncResult:
    snapshot: IndustrySnapshot
    refreshed: bool


def parse_assets(payload: tuple[object, ...]) -> tuple[CharacterAsset, ...]:
    assets: list[CharacterAsset] = []
    item_ids: set[int] = set()
    for value in payload:
        record = _record(value, "asset")
        item_id = _positive_int(record, "item_id")
        if item_id in item_ids:
            raise EsiProtocolError("ESI assets contain duplicate item IDs")
        item_ids.add(item_id)
        location_type = _string(record, "location_type")
        if location_type not in LOCATION_TYPES:
            raise EsiProtocolError("ESI asset has an unknown location_type")
        blueprint_copy = record.get("is_blueprint_copy")
        if blueprint_copy is not None and not isinstance(blueprint_copy, bool):
            raise EsiProtocolError("ESI asset is_blueprint_copy must be boolean")
        assets.append(
            CharacterAsset(
                item_id=item_id,
                type_id=_positive_int(record, "type_id"),
                quantity=_positive_int(record, "quantity"),
                location_id=_integer(record, "location_id"),
                location_type=location_type,
                location_flag=_string(record, "location_flag"),
                is_singleton=_boolean(record, "is_singleton"),
                is_blueprint_copy=blueprint_copy,
            )
        )
    return tuple(assets)


def parse_blueprints(payload: tuple[object, ...]) -> tuple[CharacterBlueprint, ...]:
    blueprints: list[CharacterBlueprint] = []
    item_ids: set[int] = set()
    for value in payload:
        record = _record(value, "blueprint")
        item_id = _positive_int(record, "item_id")
        if item_id in item_ids:
            raise EsiProtocolError("ESI blueprints contain duplicate item IDs")
        item_ids.add(item_id)
        quantity = _integer(record, "quantity")
        runs = _integer(record, "runs")
        if quantity < -2 or quantity == 0:
            raise EsiProtocolError("ESI blueprint quantity is invalid")
        if runs < -1:
            raise EsiProtocolError("ESI blueprint runs is invalid")
        blueprints.append(
            CharacterBlueprint(
                item_id=item_id,
                type_id=_positive_int(record, "type_id"),
                location_id=_integer(record, "location_id"),
                location_flag=_string(record, "location_flag"),
                quantity=quantity,
                time_efficiency=_integer(record, "time_efficiency"),
                material_efficiency=_integer(record, "material_efficiency"),
                runs=runs,
            )
        )
    return tuple(blueprints)


def _record(value: object, resource: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise EsiProtocolError(f"ESI {resource} record is not an object")
    return cast(dict[str, object], value)


def _integer(record: dict[str, object], key: str) -> int:
    value = record.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise EsiProtocolError(f"ESI record has no valid {key}")
    return value


def _positive_int(record: dict[str, object], key: str) -> int:
    value = _integer(record, key)
    if value <= 0:
        raise EsiProtocolError(f"ESI record has no positive {key}")
    return value


def _string(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise EsiProtocolError(f"ESI record has no valid {key}")
    return value


def _boolean(record: dict[str, object], key: str) -> bool:
    value = record.get(key)
    if not isinstance(value, bool):
        raise EsiProtocolError(f"ESI record has no valid {key}")
    return value
