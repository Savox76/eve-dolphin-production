"""Validated representations of ESI planetary colonies and layouts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import cast

from eve_dolphin.esi.errors import EsiProtocolError

PLANET_TYPES = frozenset(
    {"temperate", "barren", "oceanic", "ice", "gas", "lava", "storm", "plasma"}
)


@dataclass(frozen=True, slots=True)
class PlanetPinContent:
    type_id: int
    amount: int


@dataclass(frozen=True, slots=True)
class ExtractorHead:
    head_id: int
    latitude: Decimal
    longitude: Decimal


@dataclass(frozen=True, slots=True)
class ExtractorDetails:
    heads: tuple[ExtractorHead, ...]
    cycle_time: int | None
    head_radius: Decimal | None
    product_type_id: int | None
    qty_per_cycle: int | None


@dataclass(frozen=True, slots=True)
class PlanetPin:
    pin_id: int
    type_id: int
    latitude: Decimal
    longitude: Decimal
    contents: tuple[PlanetPinContent, ...]
    schematic_id: int | None
    expiry_time: datetime | None
    install_time: datetime | None
    last_cycle_start: datetime | None
    extractor_details: ExtractorDetails | None
    factory_schematic_id: int | None


@dataclass(frozen=True, slots=True)
class PlanetLink:
    source_pin_id: int
    destination_pin_id: int
    link_level: int


@dataclass(frozen=True, slots=True)
class PlanetRoute:
    route_id: int
    source_pin_id: int
    destination_pin_id: int
    content_type_id: int
    quantity: Decimal
    waypoints: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PlanetColony:
    planet_id: int
    owner_id: int
    solar_system_id: int
    planet_type: str
    last_update: datetime
    upgrade_level: int
    num_pins: int
    layout_last_modified: str | None
    pins: tuple[PlanetPin, ...]
    links: tuple[PlanetLink, ...]
    routes: tuple[PlanetRoute, ...]


@dataclass(frozen=True, slots=True)
class PlanetarySnapshot:
    snapshot_id: int
    character_id: int
    fetched_at: datetime
    colony_count: int
    pin_count: int
    link_count: int
    route_count: int
    colonies_last_modified: str | None


@dataclass(frozen=True, slots=True)
class PlanetarySyncResult:
    snapshot: PlanetarySnapshot
    refreshed: bool


def parse_colony_summaries(payload: object, character_id: int) -> tuple[dict[str, object], ...]:
    if not isinstance(payload, list):
        raise EsiProtocolError("ESI planetary colonies resource is not a list")
    summaries: list[dict[str, object]] = []
    planet_ids: set[int] = set()
    for value in payload:
        record = _record(value, "colony")
        planet_id = _positive_int(record, "planet_id")
        if planet_id in planet_ids:
            raise EsiProtocolError("ESI planetary colonies contain duplicate planet IDs")
        planet_ids.add(planet_id)
        if _positive_int(record, "owner_id") != character_id:
            raise EsiProtocolError("ESI planetary colony owner does not match character")
        planet_type = _string(record, "planet_type")
        if planet_type not in PLANET_TYPES:
            raise EsiProtocolError("ESI planetary colony has an unknown planet_type")
        upgrade_level = _integer(record, "upgrade_level")
        num_pins = _integer(record, "num_pins")
        if upgrade_level < 0 or num_pins < 0:
            raise EsiProtocolError("ESI planetary colony counts are negative")
        _positive_int(record, "solar_system_id")
        _timestamp(record, "last_update")
        summaries.append(record)
    return tuple(summaries)


def parse_colony(
    summary: dict[str, object], payload: object, layout_last_modified: str | None
) -> PlanetColony:
    record = _record(payload, "colony layout")
    pins_value = record.get("pins")
    links_value = record.get("links")
    routes_value = record.get("routes")
    if not isinstance(pins_value, list):
        raise EsiProtocolError("ESI planetary layout pins are not a list")
    if not isinstance(links_value, list):
        raise EsiProtocolError("ESI planetary layout links are not a list")
    if not isinstance(routes_value, list):
        raise EsiProtocolError("ESI planetary layout routes are not a list")

    pins = tuple(_parse_pin(value) for value in pins_value)
    pin_ids = {pin.pin_id for pin in pins}
    if len(pin_ids) != len(pins):
        raise EsiProtocolError("ESI planetary layout contains duplicate pin IDs")
    links = tuple(_parse_link(value, pin_ids) for value in links_value)
    link_keys = {(link.source_pin_id, link.destination_pin_id) for link in links}
    if len(link_keys) != len(links):
        raise EsiProtocolError("ESI planetary layout contains duplicate links")
    routes = tuple(_parse_route(value, pin_ids) for value in routes_value)
    if len({route.route_id for route in routes}) != len(routes):
        raise EsiProtocolError("ESI planetary layout contains duplicate route IDs")

    return PlanetColony(
        planet_id=_positive_int(summary, "planet_id"),
        owner_id=_positive_int(summary, "owner_id"),
        solar_system_id=_positive_int(summary, "solar_system_id"),
        planet_type=_string(summary, "planet_type"),
        last_update=_timestamp(summary, "last_update"),
        upgrade_level=_nonnegative_int(summary, "upgrade_level"),
        num_pins=_nonnegative_int(summary, "num_pins"),
        layout_last_modified=layout_last_modified,
        pins=pins,
        links=links,
        routes=routes,
    )


def _parse_pin(value: object) -> PlanetPin:
    record = _record(value, "colony pin")
    contents_value = record.get("contents", [])
    if not isinstance(contents_value, list):
        raise EsiProtocolError("ESI planetary pin contents are not a list")
    contents = tuple(_parse_content(item) for item in contents_value)
    if len({content.type_id for content in contents}) != len(contents):
        raise EsiProtocolError("ESI planetary pin contains duplicate content types")

    extractor_value = record.get("extractor_details")
    extractor = None if extractor_value is None else _parse_extractor(extractor_value)
    factory_value = record.get("factory_details")
    factory_schematic_id: int | None = None
    if factory_value is not None:
        factory = _record(factory_value, "factory details")
        factory_schematic_id = _positive_int(factory, "schematic_id")

    return PlanetPin(
        pin_id=_positive_int(record, "pin_id"),
        type_id=_positive_int(record, "type_id"),
        latitude=_decimal(record, "latitude"),
        longitude=_decimal(record, "longitude"),
        contents=contents,
        schematic_id=_optional_positive_int(record, "schematic_id"),
        expiry_time=_optional_timestamp(record, "expiry_time"),
        install_time=_optional_timestamp(record, "install_time"),
        last_cycle_start=_optional_timestamp(record, "last_cycle_start"),
        extractor_details=extractor,
        factory_schematic_id=factory_schematic_id,
    )


def _parse_content(value: object) -> PlanetPinContent:
    record = _record(value, "pin content")
    return PlanetPinContent(
        type_id=_positive_int(record, "type_id"),
        amount=_nonnegative_int(record, "amount"),
    )


def _parse_extractor(value: object) -> ExtractorDetails:
    record = _record(value, "extractor details")
    heads_value = record.get("heads")
    if not isinstance(heads_value, list):
        raise EsiProtocolError("ESI planetary extractor heads are not a list")
    heads = tuple(_parse_head(item) for item in heads_value)
    if len({head.head_id for head in heads}) != len(heads):
        raise EsiProtocolError("ESI planetary extractor contains duplicate head IDs")
    return ExtractorDetails(
        heads=heads,
        cycle_time=_optional_nonnegative_int(record, "cycle_time"),
        head_radius=_optional_decimal(record, "head_radius"),
        product_type_id=_optional_positive_int(record, "product_type_id"),
        qty_per_cycle=_optional_nonnegative_int(record, "qty_per_cycle"),
    )


def _parse_head(value: object) -> ExtractorHead:
    record = _record(value, "extractor head")
    return ExtractorHead(
        head_id=_nonnegative_int(record, "head_id"),
        latitude=_decimal(record, "latitude"),
        longitude=_decimal(record, "longitude"),
    )


def _parse_link(value: object, pin_ids: set[int]) -> PlanetLink:
    record = _record(value, "colony link")
    source = _positive_int(record, "source_pin_id")
    destination = _positive_int(record, "destination_pin_id")
    if source not in pin_ids or destination not in pin_ids:
        raise EsiProtocolError("ESI planetary link references an unknown pin")
    return PlanetLink(source, destination, _nonnegative_int(record, "link_level"))


def _parse_route(value: object, pin_ids: set[int]) -> PlanetRoute:
    record = _record(value, "colony route")
    source = _positive_int(record, "source_pin_id")
    destination = _positive_int(record, "destination_pin_id")
    waypoints_value = record.get("waypoints", [])
    if not isinstance(waypoints_value, list):
        raise EsiProtocolError("ESI planetary route waypoints are not a list")
    waypoints = tuple(_positive_value(item, "route waypoint") for item in waypoints_value)
    if (
        source not in pin_ids
        or destination not in pin_ids
        or any(waypoint not in pin_ids for waypoint in waypoints)
    ):
        raise EsiProtocolError("ESI planetary route references an unknown pin")
    quantity = _decimal(record, "quantity")
    if quantity < 0:
        raise EsiProtocolError("ESI planetary route quantity is negative")
    return PlanetRoute(
        route_id=_positive_int(record, "route_id"),
        source_pin_id=source,
        destination_pin_id=destination,
        content_type_id=_positive_int(record, "content_type_id"),
        quantity=quantity,
        waypoints=waypoints,
    )


def _record(value: object, resource: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise EsiProtocolError(f"ESI planetary {resource} is not an object")
    return cast(dict[str, object], value)


def _integer(record: dict[str, object], key: str) -> int:
    value = record.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise EsiProtocolError(f"ESI planetary record has no valid {key}")
    return value


def _positive_int(record: dict[str, object], key: str) -> int:
    return _positive_value(_integer(record, key), key)


def _positive_value(value: object, key: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise EsiProtocolError(f"ESI planetary record has no positive {key}")
    return value


def _nonnegative_int(record: dict[str, object], key: str) -> int:
    value = _integer(record, key)
    if value < 0:
        raise EsiProtocolError(f"ESI planetary record has a negative {key}")
    return value


def _optional_positive_int(record: dict[str, object], key: str) -> int | None:
    return None if record.get(key) is None else _positive_int(record, key)


def _optional_nonnegative_int(record: dict[str, object], key: str) -> int | None:
    return None if record.get(key) is None else _nonnegative_int(record, key)


def _string(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise EsiProtocolError(f"ESI planetary record has no valid {key}")
    return value


def _timestamp(record: dict[str, object], key: str) -> datetime:
    value = _string(record, key)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EsiProtocolError(f"ESI planetary record has an invalid {key}") from error
    if parsed.tzinfo is None:
        raise EsiProtocolError(f"ESI planetary record {key} has no timezone")
    return parsed


def _optional_timestamp(record: dict[str, object], key: str) -> datetime | None:
    return None if record.get(key) is None else _timestamp(record, key)


def _decimal(record: dict[str, object], key: str) -> Decimal:
    value = record.get(key)
    if not isinstance(value, (int, float, Decimal)) or isinstance(value, bool):
        raise EsiProtocolError(f"ESI planetary record has no numeric {key}")
    if isinstance(value, float) and not math.isfinite(value):
        raise EsiProtocolError(f"ESI planetary record has a non-finite {key}")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as error:
        raise EsiProtocolError(f"ESI planetary record has an invalid {key}") from error
    if not parsed.is_finite():
        raise EsiProtocolError(f"ESI planetary record has a non-finite {key}")
    return parsed


def _optional_decimal(record: dict[str, object], key: str) -> Decimal | None:
    return None if record.get(key) is None else _decimal(record, key)
