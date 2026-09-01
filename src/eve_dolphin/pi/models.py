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


class PiOperationMode(StrEnum):
    EXTRACTOR = "extractor"
    IMPORT = "import"


class PiStorageStrategy(StrEnum):
    DIRECT = "direct"
    BUFFERED = "buffered"


class PiGoalMode(StrEnum):
    MANUAL = "manual"
    LAUNCHPAD = "launchpad"


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
    operation_mode: PiOperationMode = PiOperationMode.IMPORT
    source_tier: PiTier | None = None
    storage_strategy: PiStorageStrategy = PiStorageStrategy.DIRECT
    goal_mode: PiGoalMode = PiGoalMode.MANUAL
    launchpad_capacity_m3: Decimal = Decimal("10000")
    input_launchpads: int = 1
    final_factories: int = 1
    command_center_level: int = 5
    infrastructure_reserve_percent: Decimal = Decimal("10")
    extractor_heads_per_ecu: int = 5

    def __post_init__(self) -> None:
        if self.target_type_id <= 0 or self.target_quantity <= 0:
            raise ValueError("PI planning target must be positive")
        if not 1 <= self.days <= 365:
            raise ValueError("PI planning horizon must be between 1 and 365 days")
        if self.profile_id <= 0:
            raise ValueError("PI planning profile ID must be positive")
        if self.source_tier is not None and self.source_tier is PiTier.ADVANCED:
            raise ValueError("P4 cannot be used as a PI input tier")
        if self.launchpad_capacity_m3 <= 0:
            raise ValueError("PI launchpad capacity must be positive")
        if not 1 <= self.input_launchpads <= 20:
            raise ValueError("PI input launchpad count must be between 1 and 20")
        if not 1 <= self.final_factories <= 100:
            raise ValueError("PI final factory count must be between 1 and 100")
        if not 0 <= self.command_center_level <= 5:
            raise ValueError("command center level must be between 0 and 5")
        if not Decimal(0) <= self.infrastructure_reserve_percent <= Decimal(50):
            raise ValueError("PI infrastructure reserve must be between 0 and 50 percent")
        if not 1 <= self.extractor_heads_per_ecu <= 10:
            raise ValueError("extractor heads per ECU must be between 1 and 10")


@dataclass(frozen=True, slots=True)
class PiPlanLine:
    commodity: PiCommodity
    required: int
    required_per_day: Decimal
    available_at_deadline: int
    used_from_available: int
    planned_output: int
    gross_cycles: int
    cycles: int
    available_factory_cycles: int
    factory_shortfall_cycles: int
    additional_factories: int
    import_quantity: int
    unresolved_quantity: int
    excess_quantity: int
    source_quantity: int = 0
    recommended_factories: int = 0


@dataclass(frozen=True, slots=True)
class PiLayoutStage:
    commodity: PiCommodity
    factories: int
    cycles: int
    input_units_per_day: int
    output_units_per_day: int
    buffer_storage: bool


@dataclass(frozen=True, slots=True)
class PiLaunchpadFill:
    capacity_m3: Decimal
    product_quantity: int
    product_volume_m3: Decimal
    unused_volume_m3: Decimal
    input_launchpads: int
    input_capacity_m3: Decimal
    input_volume_m3: Decimal
    input_quantities: tuple[tuple[PiCommodity, int], ...]
    fill_time: timedelta
    final_factories: int


@dataclass(frozen=True, slots=True)
class PiInfrastructureBudget:
    command_center_level: int
    total_cpu: int
    total_power: int
    reserved_cpu: int
    reserved_power: int
    used_cpu: int
    used_power: int
    remaining_cpu: int
    remaining_power: int
    launchpads: int
    storage_facilities: int
    extractor_control_units: int
    extractor_heads: int
    basic_factories: int
    advanced_factories: int
    high_tech_factories: int
    maximum_layout_copies: int
    maximum_final_factories: int
    required_planet_types: tuple[str, ...] = ()

    @property
    def is_feasible(self) -> bool:
        return self.remaining_cpu >= 0 and self.remaining_power >= 0


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
    layout: tuple[PiLayoutStage, ...]
    launchpad_fill: PiLaunchpadFill | None = None
    infrastructure_budget: PiInfrastructureBudget | None = None

    @property
    def is_feasible(self) -> bool:
        return not self.blocked_reasons and not any(line.unresolved_quantity for line in self.lines)


@dataclass(frozen=True, slots=True)
class SavedPiPlan:
    plan_id: int | None
    name: str
    request: PiPlanRequest

    def __post_init__(self) -> None:
        if self.plan_id is not None and self.plan_id <= 0:
            raise ValueError("saved PI plan ID must be positive")
        if not self.name.strip():
            raise ValueError("saved PI plan name must not be empty")
