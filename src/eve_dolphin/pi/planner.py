"""Backward PI planner using active SDE recipes and live colony projections."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

from eve_dolphin.characters import CharacterRepository
from eve_dolphin.database import Database
from eve_dolphin.pi.catalog import PiCatalogRepository
from eve_dolphin.pi.forecast import forecast_colony
from eve_dolphin.pi.models import (
    PiCatalog,
    PiCommodity,
    PiGoalMode,
    PiInfrastructureBudget,
    PiLaunchpadCargo,
    PiLaunchpadFill,
    PiLayoutStage,
    PiOperationMode,
    PiPlanLine,
    PiPlanRequest,
    PiPlanResult,
    PiProfile,
    PiRecipe,
    PiTier,
)
from eve_dolphin.pi.profiles import PiProfileRepository
from eve_dolphin.sync.planetary_repository import PlanetarySnapshotRepository

PI_TAXABLE_VALUE = {
    PiTier.RAW: Decimal("5"),
    PiTier.BASIC: Decimal("400"),
    PiTier.REFINED: Decimal("7200"),
    PiTier.SPECIALIZED: Decimal("60000"),
    PiTier.ADVANCED: Decimal("1200000"),
}

COMMAND_CENTER_BUDGETS = {
    0: (1_675, 6_000),
    1: (7_057, 9_000),
    2: (12_136, 12_000),
    3: (17_215, 15_000),
    4: (21_315, 17_000),
    5: (25_415, 19_000),
}

# CPU (tf), powergrid (MW). Links are distance-dependent and therefore covered by
# the user-selected infrastructure reserve instead of a misleading fixed value.
PI_BUILDING_RESOURCES = {
    "launchpad": (3_600, 700),
    "storage": (500, 700),
    "ecu": (400, 2_600),
    "extractor_head": (110, 550),
    "basic_factory": (200, 800),
    "advanced_factory": (500, 700),
    "high_tech_factory": (1_100, 400),
}


class PiPlannerService:
    def __init__(
        self,
        database: Database,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._characters = CharacterRepository(database)
        self._snapshots = PlanetarySnapshotRepository(database)
        self._catalogs = PiCatalogRepository(database)
        self._profiles = PiProfileRepository(database)
        self._clock = clock or (lambda: datetime.now(UTC))

    def targets(self, language: str) -> tuple[tuple[int, str, PiTier], ...]:
        catalog = self._catalogs.load(language)
        return tuple(
            (commodity.type_id, commodity.name, commodity.tier)
            for commodity in sorted(
                catalog.commodities.values(),
                key=lambda value: (int(value.tier), value.name.casefold()),
            )
            if commodity.type_id in catalog.recipes_by_output
        )

    def plan(self, request: PiPlanRequest, language: str) -> PiPlanResult:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("PI planner clock must include a timezone")
        catalog = self._catalogs.load(language)
        target = catalog.commodities.get(request.target_type_id)
        if target is None or request.target_type_id not in catalog.recipes_by_output:
            raise ValueError("PI planning target is not available in the active SDE")
        profile = self._profiles.get(request.profile_id)
        if profile is None:
            raise ValueError("PI planning profile does not exist")
        source_tier = (
            request.source_tier if request.source_tier is not None else profile.supply_tier
        )
        if request.source_tier is None:
            request = replace(request, source_tier=source_tier)
        request = _resolve_launchpad_request(request, catalog, target, source_tier)
        planning_window = _planning_window(request, catalog, target)

        available, factory_capacity = self._planning_state(catalog, now, planning_window)
        demand: Counter[int] = Counter({target.type_id: request.target_quantity})
        line_data: dict[
            int, tuple[int, int, int, int, int, int, int, int, int, int, int, int, int]
        ] = {}
        pending = {target.type_id}
        while pending:
            type_id = max(
                pending,
                key=lambda identifier: (
                    int(catalog.commodities[identifier].tier),
                    catalog.commodities[identifier].name.casefold(),
                ),
            )
            pending.remove(type_id)
            commodity = catalog.commodities[type_id]
            required = demand[type_id]
            used_available = min(required, available[type_id])
            net = required - used_available
            excess = max(0, available[type_id] - required)
            recipe = catalog.recipe_for_output(type_id)
            planned_output = 0
            gross_cycles = _ceil_div(required, recipe.output.quantity) if recipe else 0
            cycles = 0
            imported = 0
            unresolved = 0
            available_cycles = 0
            capacity_shortfall = 0
            additional_factories = 0
            source_quantity = 0
            recommended_factories = 0
            if (
                net > 0
                and request.operation_mode is PiOperationMode.IMPORT
                and commodity.tier <= source_tier
            ):
                imported = net
            elif (
                net > 0
                and request.operation_mode is PiOperationMode.EXTRACTOR
                and commodity.tier is PiTier.RAW
            ):
                source_quantity = net
            elif net > 0 and recipe is not None:
                cycles = _ceil_div(net, recipe.output.quantity)
                planned_output = cycles * recipe.output.quantity
                available_cycles = factory_capacity[type_id]
                capacity_shortfall = max(0, cycles - available_cycles)
                cycles_per_factory = (
                    int(planning_window.total_seconds()) // recipe.cycle_time_seconds
                )
                if capacity_shortfall and cycles_per_factory > 0:
                    additional_factories = _ceil_div(capacity_shortfall, cycles_per_factory)
                if cycles_per_factory > 0:
                    recommended_factories = _ceil_div(cycles, cycles_per_factory)
                excess += planned_output - net
                for item in recipe.inputs:
                    demand[item.commodity.type_id] += cycles * item.quantity
                    pending.add(item.commodity.type_id)
            elif net > 0:
                unresolved = net
            line_data[type_id] = (
                required,
                used_available,
                planned_output,
                gross_cycles,
                cycles,
                available_cycles,
                capacity_shortfall,
                additional_factories,
                imported,
                unresolved,
                excess,
                source_quantity,
                recommended_factories,
            )

        lines = tuple(
            PiPlanLine(
                commodity=catalog.commodities[type_id],
                required=values[0],
                required_per_day=(
                    Decimal(values[0])
                    * Decimal(86400)
                    / Decimal(int(planning_window.total_seconds()))
                ),
                available_at_deadline=available[type_id],
                used_from_available=values[1],
                planned_output=values[2],
                gross_cycles=values[3],
                cycles=values[4],
                available_factory_cycles=values[5],
                factory_shortfall_cycles=values[6],
                additional_factories=values[7],
                import_quantity=values[8],
                unresolved_quantity=values[9],
                excess_quantity=values[10],
                source_quantity=values[11],
                recommended_factories=values[12],
            )
            for type_id, values in sorted(
                line_data.items(),
                key=lambda item: (
                    -int(catalog.commodities[item[0]].tier),
                    catalog.commodities[item[0]].name.casefold(),
                ),
            )
        )
        layout = _layout(request, catalog, lines, planning_window)
        return _cost_result(
            request,
            profile,
            target,
            lines,
            layout,
            catalog,
            _infrastructure_budget(request, lines, layout),
        )

    def _planning_state(
        self, catalog: PiCatalog, now: datetime, horizon: timedelta
    ) -> tuple[Counter[int], Counter[int]]:
        total: Counter[int] = Counter()
        capacity: Counter[int] = Counter()
        used_cycles: Counter[int] = Counter()
        horizon_seconds = int(horizon.total_seconds())
        for character in self._characters.list_all():
            for colony in self._snapshots.current_colonies(character.character_id):
                forecast = forecast_colony(colony, catalog, now, horizon)
                total.update(
                    {
                        quantity.commodity.type_id: quantity.quantity
                        for quantity in forecast.projected_inventory
                    }
                )
                for quantity in forecast.factory_outputs:
                    recipe = catalog.recipe_for_output(quantity.commodity.type_id)
                    if recipe is not None:
                        used_cycles[quantity.commodity.type_id] += (
                            quantity.quantity // recipe.output.quantity
                        )
                for pin in colony.pins:
                    if pin.factory_schematic_id is None:
                        continue
                    recipe = catalog.recipes_by_id.get(pin.factory_schematic_id)
                    if recipe is not None:
                        capacity[recipe.output.commodity.type_id] += (
                            horizon_seconds // recipe.cycle_time_seconds
                        )
        remaining = Counter(
            {type_id: max(0, cycles - used_cycles[type_id]) for type_id, cycles in capacity.items()}
        )
        return total, remaining


def _cost_result(
    request: PiPlanRequest,
    profile: PiProfile,
    target: PiCommodity,
    lines: tuple[PiPlanLine, ...],
    layout: tuple[PiLayoutStage, ...],
    catalog: PiCatalog,
    infrastructure_budget: PiInfrastructureBudget,
) -> PiPlanResult:
    imports = tuple(line for line in lines if line.import_quantity > 0)
    import_volume = sum(
        (Decimal(line.import_quantity) * line.commodity.volume_m3 for line in imports),
        start=Decimal(0),
    )
    export_volume = Decimal(request.target_quantity) * target.volume_m3
    import_tax = sum(
        (
            Decimal(line.import_quantity)
            * PI_TAXABLE_VALUE[line.commodity.tier]
            * profile.import_tax_percent
            / Decimal(100)
            for line in imports
        ),
        start=Decimal(0),
    )
    export_tax = (
        Decimal(request.target_quantity)
        * PI_TAXABLE_VALUE[target.tier]
        * profile.export_tax_percent
        / Decimal(100)
    )
    total_volume = import_volume + export_volume
    trips = int((total_volume / profile.cargo_capacity_m3).to_integral_value(ROUND_CEILING))
    transport = total_volume * profile.transport_isk_per_m3
    risk = transport * profile.risk_markup_percent / Decimal(100)
    blocked: list[str] = []
    if imports and not profile.has_customs_office:
        blocked.append("imports_require_customs_office")
    if not profile.has_customs_office and export_volume > Decimal(500):
        blocked.append("command_center_export_requires_multiple_launches")
    if any(line.unresolved_quantity for line in lines):
        blocked.append("raw_material_shortfall")
    if any(line.factory_shortfall_cycles for line in lines):
        blocked.append("factory_capacity_shortfall")
    if infrastructure_budget.remaining_cpu < 0:
        blocked.append("planet_cpu_shortfall")
    if infrastructure_budget.remaining_power < 0:
        blocked.append("planet_power_shortfall")
    launchpad_fill = _launchpad_fill(request, target, lines, catalog)
    return PiPlanResult(
        request=request,
        profile=profile,
        target=target,
        lines=lines,
        import_volume_m3=import_volume,
        export_volume_m3=export_volume,
        cargo_trips=trips,
        import_tax_isk=import_tax,
        export_tax_isk=export_tax,
        transport_cost_isk=transport,
        risk_markup_isk=risk,
        total_logistics_isk=import_tax + export_tax + transport + risk,
        blocked_reasons=tuple(blocked),
        layout=layout,
        launchpad_fill=launchpad_fill,
        infrastructure_budget=infrastructure_budget,
    )


def _resolve_launchpad_request(
    request: PiPlanRequest,
    catalog: PiCatalog,
    target: PiCommodity,
    source_tier: PiTier,
) -> PiPlanRequest:
    if request.goal_mode is PiGoalMode.MANUAL:
        return request
    capacity_units = int(request.launchpad_capacity_m3 // target.volume_m3)
    if capacity_units <= 0:
        raise ValueError("Selected product does not fit into the launchpad capacity")
    recipe = catalog.recipe_for_output(target.type_id)
    if recipe is None:
        raise ValueError("PI planning target has no production recipe")
    output_cycles = capacity_units // recipe.output.quantity
    input_capacity = request.launchpad_capacity_m3 * request.input_launchpads
    low = 0
    high = output_cycles
    while low < high:
        candidate = (low + high + 1) // 2
        inputs = _launchpad_inputs(candidate, recipe, catalog, request, source_tier)
        input_volume = _commodity_volume(inputs, catalog)
        if input_volume <= input_capacity:
            low = candidate
        else:
            high = candidate - 1
    input_cycles = low
    cycles = min(output_cycles, input_cycles)
    if cycles <= 0:
        raise ValueError("A complete production batch does not fit into the launchpad capacity")
    quantity = cycles * recipe.output.quantity
    batches = _ceil_div(cycles, request.final_factories)
    seconds = max(1, batches * recipe.cycle_time_seconds)
    days = max(1, _ceil_div(seconds, 86400))
    return replace(request, target_quantity=quantity, days=min(days, 365))


def _planning_window(
    request: PiPlanRequest,
    catalog: PiCatalog,
    target: PiCommodity,
) -> timedelta:
    if request.goal_mode is PiGoalMode.MANUAL:
        return timedelta(days=request.days)
    recipe = catalog.recipe_for_output(target.type_id)
    if recipe is None:
        raise ValueError("PI planning target has no production recipe")
    cycles = _ceil_div(request.target_quantity, recipe.output.quantity)
    seconds = _ceil_div(cycles, request.final_factories) * recipe.cycle_time_seconds
    return timedelta(seconds=max(1, seconds))


def _launchpad_fill(
    request: PiPlanRequest,
    target: PiCommodity,
    lines: tuple[PiPlanLine, ...],
    catalog: PiCatalog,
) -> PiLaunchpadFill | None:
    if request.goal_mode is not PiGoalMode.LAUNCHPAD:
        return None
    target_line = next(line for line in lines if line.commodity.type_id == target.type_id)
    recipe = catalog.recipe_for_output(target.type_id)
    if recipe is None:
        return None
    fill_seconds = (
        _ceil_div(target_line.cycles, request.final_factories) * recipe.cycle_time_seconds
    )
    product_volume = Decimal(request.target_quantity) * target.volume_m3
    source_tier = request.source_tier if request.source_tier is not None else PiTier.RAW
    quantities = _launchpad_inputs(target_line.cycles, recipe, catalog, request, source_tier)
    input_quantities = tuple(
        (catalog.commodities[type_id], quantity)
        for type_id, quantity in sorted(
            quantities.items(),
            key=lambda item: catalog.commodities[item[0]].name.casefold(),
        )
    )
    input_volume = sum(
        (Decimal(quantity) * commodity.volume_m3 for commodity, quantity in input_quantities),
        start=Decimal(0),
    )
    input_cargo = _allocate_launchpad_cargo(
        input_quantities,
        request.input_launchpads,
        request.launchpad_capacity_m3,
    )
    return PiLaunchpadFill(
        capacity_m3=request.launchpad_capacity_m3,
        product_quantity=request.target_quantity,
        product_volume_m3=product_volume,
        unused_volume_m3=max(Decimal(0), request.launchpad_capacity_m3 - product_volume),
        input_launchpads=request.input_launchpads,
        input_capacity_m3=request.launchpad_capacity_m3 * request.input_launchpads,
        input_volume_m3=input_volume,
        input_quantities=input_quantities,
        input_cargo=input_cargo,
        fill_time=timedelta(seconds=fill_seconds),
        final_factories=request.final_factories,
    )


def _allocate_launchpad_cargo(
    inputs: tuple[tuple[PiCommodity, int], ...],
    launchpad_count: int,
    capacity_m3: Decimal,
) -> tuple[PiLaunchpadCargo, ...]:
    remaining_capacity = [capacity_m3 for _index in range(launchpad_count)]
    result: list[PiLaunchpadCargo] = []
    for commodity, quantity in sorted(
        inputs,
        key=lambda item: (-item[0].volume_m3, item[0].name.casefold()),
    ):
        remaining_quantity = quantity
        for index in range(launchpad_count):
            if remaining_quantity <= 0:
                break
            fitting = int(remaining_capacity[index] // commodity.volume_m3)
            allocated = min(remaining_quantity, fitting)
            if allocated <= 0:
                continue
            volume = Decimal(allocated) * commodity.volume_m3
            result.append(PiLaunchpadCargo(index + 1, commodity, allocated, volume))
            remaining_capacity[index] -= volume
            remaining_quantity -= allocated
        if remaining_quantity:
            raise ValueError("PI input goods cannot be distributed across the launchpads")
    return tuple(result)


def _launchpad_inputs(
    target_cycles: int,
    target_recipe: PiRecipe,
    catalog: PiCatalog,
    request: PiPlanRequest,
    source_tier: PiTier,
) -> Counter[int]:
    demand: Counter[int] = Counter(
        {item.commodity.type_id: target_cycles * item.quantity for item in target_recipe.inputs}
    )
    stop_tier = source_tier if request.operation_mode is PiOperationMode.IMPORT else PiTier.RAW
    pending = {type_id for type_id in demand if catalog.commodities[type_id].tier > stop_tier}
    while pending:
        type_id = max(pending, key=lambda identifier: int(catalog.commodities[identifier].tier))
        pending.remove(type_id)
        quantity = demand.pop(type_id)
        child = catalog.recipe_for_output(type_id)
        if child is None:
            demand[type_id] += quantity
            continue
        cycles = _ceil_div(quantity, child.output.quantity)
        for item in child.inputs:
            demand[item.commodity.type_id] += cycles * item.quantity
            if item.commodity.tier > stop_tier:
                pending.add(item.commodity.type_id)
    return demand


def _commodity_volume(quantities: Counter[int], catalog: PiCatalog) -> Decimal:
    return sum(
        (
            Decimal(quantity) * catalog.commodities[type_id].volume_m3
            for type_id, quantity in quantities.items()
        ),
        start=Decimal(0),
    )


def _layout(
    request: PiPlanRequest,
    catalog: PiCatalog,
    lines: tuple[PiPlanLine, ...],
    planning_window: timedelta,
) -> tuple[PiLayoutStage, ...]:
    result: list[PiLayoutStage] = []
    planning_seconds = int(planning_window.total_seconds())
    for line in lines:
        recipe = catalog.recipe_for_output(line.commodity.type_id)
        if recipe is None or line.cycles <= 0:
            continue
        input_per_day = sum(
            _ceil_div(line.cycles * item.quantity * 86400, planning_seconds)
            for item in recipe.inputs
        )
        output_per_day = _ceil_div(line.planned_output * 86400, planning_seconds)
        result.append(
            PiLayoutStage(
                commodity=line.commodity,
                factories=(
                    request.final_factories
                    if request.goal_mode is PiGoalMode.LAUNCHPAD
                    and line.commodity.type_id == request.target_type_id
                    else max(1, line.recommended_factories)
                ),
                cycles=line.cycles,
                input_units_per_day=input_per_day,
                output_units_per_day=output_per_day,
                buffer_storage=(
                    request.storage_strategy.value == "buffered"
                    and line.commodity.type_id != request.target_type_id
                ),
            )
        )
    return tuple(sorted(result, key=lambda stage: int(stage.commodity.tier)))


def _infrastructure_budget(
    request: PiPlanRequest,
    lines: tuple[PiPlanLine, ...],
    layout: tuple[PiLayoutStage, ...],
) -> PiInfrastructureBudget:
    total_cpu, total_power = COMMAND_CENTER_BUDGETS[request.command_center_level]
    reserve_ratio = request.infrastructure_reserve_percent / Decimal(100)
    reserved_cpu = int(
        (Decimal(total_cpu) * reserve_ratio).to_integral_value(rounding=ROUND_CEILING)
    )
    reserved_power = int(
        (Decimal(total_power) * reserve_ratio).to_integral_value(rounding=ROUND_CEILING)
    )

    basic_factories = sum(
        stage.factories for stage in layout if stage.commodity.tier is PiTier.BASIC
    )
    advanced_factories = sum(
        stage.factories
        for stage in layout
        if stage.commodity.tier in {PiTier.REFINED, PiTier.SPECIALIZED}
    )
    high_tech_factories = sum(
        stage.factories for stage in layout if stage.commodity.tier is PiTier.ADVANCED
    )
    storage_facilities = len({stage.commodity.tier for stage in layout if stage.buffer_storage})
    raw_sources = sum(
        1 for line in lines if line.commodity.tier is PiTier.RAW and line.source_quantity > 0
    )
    extractor_control_units = (
        raw_sources if request.operation_mode is PiOperationMode.EXTRACTOR else 0
    )
    extractor_heads = extractor_control_units * request.extractor_heads_per_ecu

    launchpads = request.input_launchpads + 1 if request.goal_mode is PiGoalMode.LAUNCHPAD else 1
    fixed_cpu, fixed_power = _resource_sum(
        (("launchpad", launchpads), ("storage", storage_facilities))
    )
    variable_cpu, variable_power = _resource_sum(
        (
            ("ecu", extractor_control_units),
            ("extractor_head", extractor_heads),
            ("basic_factory", basic_factories),
            ("advanced_factory", advanced_factories),
            ("high_tech_factory", high_tech_factories),
        )
    )
    used_cpu = fixed_cpu + variable_cpu
    used_power = fixed_power + variable_power
    usable_cpu = total_cpu - reserved_cpu
    usable_power = total_power - reserved_power
    if variable_cpu <= 0 and variable_power <= 0:
        maximum_layout_copies = 0
    else:
        cpu_copies = (
            max(0, usable_cpu - fixed_cpu) // variable_cpu if variable_cpu > 0 else 2_000_000_000
        )
        power_copies = (
            max(0, usable_power - fixed_power) // variable_power
            if variable_power > 0
            else 2_000_000_000
        )
        maximum_layout_copies = min(cpu_copies, power_copies)
    target_factories = next(
        (stage.factories for stage in layout if stage.commodity.type_id == request.target_type_id),
        0,
    )
    return PiInfrastructureBudget(
        command_center_level=request.command_center_level,
        total_cpu=total_cpu,
        total_power=total_power,
        reserved_cpu=reserved_cpu,
        reserved_power=reserved_power,
        used_cpu=used_cpu,
        used_power=used_power,
        remaining_cpu=usable_cpu - used_cpu,
        remaining_power=usable_power - used_power,
        launchpads=launchpads,
        storage_facilities=storage_facilities,
        extractor_control_units=extractor_control_units,
        extractor_heads=extractor_heads,
        basic_factories=basic_factories,
        advanced_factories=advanced_factories,
        high_tech_factories=high_tech_factories,
        maximum_layout_copies=maximum_layout_copies,
        maximum_final_factories=maximum_layout_copies * target_factories,
        required_planet_types=("barren", "temperate") if high_tech_factories else (),
    )


def _resource_sum(items: tuple[tuple[str, int], ...]) -> tuple[int, int]:
    cpu = sum(PI_BUILDING_RESOURCES[kind][0] * count for kind, count in items)
    power = sum(PI_BUILDING_RESOURCES[kind][1] * count for kind, count in items)
    return cpu, power


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor
