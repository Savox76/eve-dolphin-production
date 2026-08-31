"""Backward PI planner using active SDE recipes and live colony projections."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

from eve_dolphin.characters import CharacterRepository
from eve_dolphin.database import Database
from eve_dolphin.pi.catalog import PiCatalogRepository
from eve_dolphin.pi.forecast import forecast_colony
from eve_dolphin.pi.models import (
    PiCatalog,
    PiCommodity,
    PiLayoutStage,
    PiOperationMode,
    PiPlanLine,
    PiPlanRequest,
    PiPlanResult,
    PiProfile,
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

        available, factory_capacity = self._planning_state(catalog, now, request.days)
        demand: Counter[int] = Counter({target.type_id: request.target_quantity})
        line_data: dict[int, tuple[int, int, int, int, int, int, int, int, int, int, int, int]] = {}
        source_tier = request.source_tier or profile.supply_tier
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
                cycles_per_factory = request.days * 86400 // recipe.cycle_time_seconds
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
                required_per_day=Decimal(values[0]) / Decimal(request.days),
                available_at_deadline=available[type_id],
                used_from_available=values[1],
                planned_output=values[2],
                cycles=values[3],
                available_factory_cycles=values[4],
                factory_shortfall_cycles=values[5],
                additional_factories=values[6],
                import_quantity=values[7],
                unresolved_quantity=values[8],
                excess_quantity=values[9],
                source_quantity=values[10],
                recommended_factories=values[11],
            )
            for type_id, values in sorted(
                line_data.items(),
                key=lambda item: (
                    -int(catalog.commodities[item[0]].tier),
                    catalog.commodities[item[0]].name.casefold(),
                ),
            )
        )
        return _cost_result(request, profile, target, lines, _layout(request, catalog, lines))

    def _planning_state(
        self, catalog: PiCatalog, now: datetime, days: int
    ) -> tuple[Counter[int], Counter[int]]:
        total: Counter[int] = Counter()
        capacity: Counter[int] = Counter()
        used_cycles: Counter[int] = Counter()
        horizon = timedelta(days=days)
        horizon_seconds = days * 86400
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
    )


def _layout(
    request: PiPlanRequest,
    catalog: PiCatalog,
    lines: tuple[PiPlanLine, ...],
) -> tuple[PiLayoutStage, ...]:
    result: list[PiLayoutStage] = []
    for line in lines:
        recipe = catalog.recipe_for_output(line.commodity.type_id)
        if recipe is None or line.cycles <= 0:
            continue
        input_per_day = sum(
            _ceil_div(line.cycles * item.quantity, request.days) for item in recipe.inputs
        )
        output_per_day = _ceil_div(line.planned_output, request.days)
        result.append(
            PiLayoutStage(
                commodity=line.commodity,
                factories=max(1, line.recommended_factories),
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


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor
