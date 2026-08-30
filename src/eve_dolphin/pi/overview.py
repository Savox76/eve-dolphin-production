"""Character-spanning read model for the first visible PI overview."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from eve_dolphin.characters import CharacterRepository, EveCharacter
from eve_dolphin.database import Database
from eve_dolphin.sde import SdeRepository
from eve_dolphin.sync.planetary_models import PlanetColony
from eve_dolphin.sync.planetary_repository import PlanetarySnapshotRepository


@dataclass(frozen=True, slots=True)
class NamedCount:
    type_id: int
    name: str | None
    count: int


@dataclass(frozen=True, slots=True)
class NamedQuantity:
    type_id: int
    name: str | None
    quantity: int


@dataclass(frozen=True, slots=True)
class ColonyOverview:
    character_id: int
    character_name: str
    planet_id: int
    solar_system_id: int
    planet_type: str
    snapshot_at: datetime
    last_update: datetime
    upgrade_level: int
    pin_count: int
    link_count: int
    route_count: int
    factory_count: int
    active_extractors: int
    expired_extractors: int
    incomplete_extractors: int
    next_expiry: datetime | None
    pin_types: tuple[NamedCount, ...]
    extractor_products: tuple[NamedCount, ...]
    stored_contents: tuple[NamedQuantity, ...]

    @property
    def extractor_count(self) -> int:
        return self.active_extractors + self.expired_extractors + self.incomplete_extractors


class PlanetaryOverviewService:
    """Build an immutable UI model from active snapshots and the active SDE."""

    def __init__(
        self,
        database: Database,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._characters = CharacterRepository(database)
        self._snapshots = PlanetarySnapshotRepository(database)
        self._sde = SdeRepository(database)
        self._clock = clock or (lambda: datetime.now(UTC))

    def list_colonies(self, language: str) -> tuple[ColonyOverview, ...]:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("planetary overview clock must include a timezone")
        source: list[tuple[EveCharacter, datetime, PlanetColony]] = []
        type_ids: set[int] = set()
        for character in self._characters.list_all():
            snapshot = self._snapshots.current(character.character_id)
            if snapshot is None:
                continue
            for colony in self._snapshots.current_colonies(character.character_id):
                source.append((character, snapshot.fetched_at, colony))
                type_ids.update(_referenced_type_ids(colony))
        names = self._sde.type_names(type_ids, language)
        overview = tuple(
            _colony_overview(character, snapshot_at, colony, names, now)
            for character, snapshot_at, colony in source
        )
        return tuple(
            sorted(
                overview,
                key=lambda colony: (
                    colony.character_name.casefold(),
                    colony.solar_system_id,
                    colony.planet_id,
                ),
            )
        )


def _referenced_type_ids(colony: PlanetColony) -> set[int]:
    identifiers = {pin.type_id for pin in colony.pins}
    identifiers.update(content.type_id for pin in colony.pins for content in pin.contents)
    identifiers.update(route.content_type_id for route in colony.routes)
    identifiers.update(
        extractor.product_type_id
        for pin in colony.pins
        if (extractor := pin.extractor_details) is not None
        and extractor.product_type_id is not None
    )
    return identifiers


def _colony_overview(
    character: EveCharacter,
    snapshot_at: datetime,
    colony: PlanetColony,
    names: Mapping[int, str],
    now: datetime,
) -> ColonyOverview:
    active_extractors = 0
    expired_extractors = 0
    incomplete_extractors = 0
    future_expiries: list[datetime] = []
    pin_types: Counter[int] = Counter()
    extractor_products: Counter[int] = Counter()
    stored_contents: Counter[int] = Counter()
    factory_count = 0
    for pin in colony.pins:
        pin_types[pin.type_id] += 1
        factory_count += int(pin.factory_schematic_id is not None)
        for content in pin.contents:
            stored_contents[content.type_id] += content.amount
        extractor = pin.extractor_details
        if extractor is None:
            continue
        if extractor.product_type_id is not None:
            extractor_products[extractor.product_type_id] += 1
        if pin.expiry_time is None:
            incomplete_extractors += 1
        elif pin.expiry_time <= now:
            expired_extractors += 1
        else:
            active_extractors += 1
            future_expiries.append(pin.expiry_time)
    return ColonyOverview(
        character_id=character.character_id,
        character_name=character.character_name,
        planet_id=colony.planet_id,
        solar_system_id=colony.solar_system_id,
        planet_type=colony.planet_type,
        snapshot_at=snapshot_at,
        last_update=colony.last_update,
        upgrade_level=colony.upgrade_level,
        pin_count=len(colony.pins),
        link_count=len(colony.links),
        route_count=len(colony.routes),
        factory_count=factory_count,
        active_extractors=active_extractors,
        expired_extractors=expired_extractors,
        incomplete_extractors=incomplete_extractors,
        next_expiry=min(future_expiries, default=None),
        pin_types=_named_counts(pin_types, names),
        extractor_products=_named_counts(extractor_products, names),
        stored_contents=_named_quantities(stored_contents, names),
    )


def _named_counts(values: Mapping[int, int], names: Mapping[int, str]) -> tuple[NamedCount, ...]:
    return tuple(
        NamedCount(type_id, names.get(type_id), count)
        for type_id, count in sorted(values.items(), key=lambda value: _name_key(value[0], names))
    )


def _named_quantities(
    values: Mapping[int, int], names: Mapping[int, str]
) -> tuple[NamedQuantity, ...]:
    return tuple(
        NamedQuantity(type_id, names.get(type_id), quantity)
        for type_id, quantity in sorted(
            values.items(), key=lambda value: _name_key(value[0], names)
        )
    )


def _name_key(type_id: int, names: Mapping[int, str]) -> tuple[bool, str, int]:
    name = names.get(type_id)
    return name is None, name.casefold() if name is not None else "", type_id
