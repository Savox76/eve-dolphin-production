"""Typed planetary-industry catalog, forecast, and planning values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import IntEnum, StrEnum


class PiTier(IntEnum):
    RAW = 0
    BASIC = 1
    REFINED = 2
    SPECIALIZED = 3
    ADVANCED = 4


class SpaceKind(StrEnum):
    HIGHSEC = "highsec"
    LOWSEC = "lowsec"
    NULLSEC = "nullsec"
    WORMHOLE = "wormhole"


@dataclass(frozen=True, slots=True)
class PiCommodity:
    type_id: int
    name: str
    volume_m3: Decimal
    tier: PiTier


@dataclass(frozen=True, slots=True)
class PiRecipeItem:
    commodity: PiCommodity
    quantity: int


@dataclass(frozen=True, slots=True)
class PiRecipe:
    schematic_id: int
    name: str
    cycle_time_seconds: int
    inputs: tuple[PiRecipeItem, ...]
    output: PiRecipeItem


@dataclass(frozen=True, slots=True)
class PiCatalog:
    commodities: dict[int, PiCommodity]
    recipes_by_output: dict[int, PiRecipe]
    recipes_by_id: dict[int, PiRecipe]
    type_capacities_m3: dict[int, Decimal]

    def recipe_for_output(self, type_id: int) -> PiRecipe | None:
        return self.recipes_by_output.get(type_id)


@dataclass(frozen=True, slots=True)
class UniverseLocation:
    planet_id: int
    planet_name: str
    solar_system_id: int
    solar_system_name: str
    security_status: Decimal


@dataclass(frozen=True, slots=True)
class PiProfile:
    profile_id: int | None
    name: str
    space_kind: SpaceKind
    has_customs_office: bool
    import_tax_percent: Decimal
    export_tax_percent: Decimal
    transport_isk_per_m3: Decimal
    cargo_capacity_m3: Decimal
    risk_markup_percent: Decimal
    supply_tier: PiTier

    def __post_init__(self) -> None:
        if self.profile_id is not None and self.profile_id <= 0:
            raise ValueError("PI profile ID must be positive")
        if not self.name.strip():
            raise ValueError("PI profile name must not be empty")
        for value in (
            self.import_tax_percent,
            self.export_tax_percent,
            self.risk_markup_percent,
        ):
            if value < 0 or value > 100:
                raise ValueError("PI profile percentages must be between 0 and 100")
        if self.transport_isk_per_m3 < 0:
            raise ValueError("PI transport rate must not be negative")
        if self.cargo_capacity_m3 <= 0:
            raise ValueError("PI cargo capacity must be positive")


@dataclass(frozen=True, slots=True)
class ForecastQuantity:
    commodity: PiCommodity
    quantity: int


@dataclass(frozen=True, slots=True)
class ForecastRate:
    commodity: PiCommodity
    units_per_hour: Decimal


@dataclass(frozen=True, slots=True)
class ColonyForecast:
    horizon: timedelta
    extractor_rates: tuple[ForecastRate, ...]
    extracted: tuple[ForecastQuantity, ...]
    factory_outputs: tuple[ForecastQuantity, ...]
    projected_inventory: tuple[ForecastQuantity, ...]
    stalled_factories: int
    constrained_factories: int
    incomplete_factories: int
    storage_used_m3: Decimal
    storage_capacity_m3: Decimal
    storage_fill_percent: Decimal | None
    estimated_full_at: datetime | None


@dataclass(frozen=True, slots=True)
class PiPlanRequest:
    target_type_id: int
    target_quantity: int
    days: int
    profile_id: int

    def __post_init__(self) -> None:
        if self.target_type_id <= 0 or self.target_quantity <= 0:
            raise ValueError("PI planning target must be positive")
        if not 1 <= self.days <= 365:
            raise ValueError("PI planning horizon must be between 1 and 365 days")
        if self.profile_id <= 0:
            raise ValueError("PI planning profile ID must be positive")


@dataclass(frozen=True, slots=True)
class PiPlanLine:
    commodity: PiCommodity
    required: int
    required_per_day: Decimal
    available_at_deadline: int
    used_from_available: int
    planned_output: int
    cycles: int
    available_factory_cycles: int
    factory_shortfall_cycles: int
    additional_factories: int
    import_quantity: int
    unresolved_quantity: int
    excess_quantity: int


@dataclass(frozen=True, slots=True)
class PiPlanResult:
    request: PiPlanRequest
    profile: PiProfile
    target: PiCommodity
    lines: tuple[PiPlanLine, ...]
    import_volume_m3: Decimal
    export_volume_m3: Decimal
    cargo_trips: int
    import_tax_isk: Decimal
    export_tax_isk: Decimal
    transport_cost_isk: Decimal
    risk_markup_isk: Decimal
    total_logistics_isk: Decimal
    blocked_reasons: tuple[str, ...]

    @property
    def is_feasible(self) -> bool:
        return not self.blocked_reasons and not any(line.unresolved_quantity for line in self.lines)
