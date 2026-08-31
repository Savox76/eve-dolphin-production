"""Explainable T1 manufacturing material and duration calculations."""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal

from eve_dolphin.database import Database
from eve_dolphin.manufacturing.models import (
    ManufacturingMaterialLine,
    ManufacturingPlan,
    OwnedManufacturingBlueprint,
)
from eve_dolphin.manufacturing.repository import ManufacturingRepository


class ManufacturingPlannerService:
    def __init__(self, database: Database) -> None:
        self._repository = ManufacturingRepository(database)

    def list_blueprints(self, language: str) -> tuple[OwnedManufacturingBlueprint, ...]:
        return self._repository.list_blueprints(language)

    def calculate(
        self,
        blueprint: OwnedManufacturingBlueprint,
        target_quantity: int,
        *,
        material_modifier: Decimal = Decimal("1"),
        time_modifier: Decimal = Decimal("1"),
    ) -> ManufacturingPlan:
        if target_quantity <= 0:
            raise ValueError("target quantity must be positive")
        if material_modifier <= 0 or time_modifier <= 0:
            raise ValueError("manufacturing modifiers must be positive")
        runs = _ceil_divide(target_quantity, blueprint.output_per_run)
        planned_output = runs * blueprint.output_per_run
        local, total = self._repository.asset_quantities(
            {material.type_id for material in blueprint.materials},
            blueprint.location_id,
        )
        efficiency = Decimal(1) - Decimal(blueprint.material_efficiency) / Decimal(100)
        lines = tuple(
            ManufacturingMaterialLine(
                type_id=material.type_id,
                name=material.name,
                base_quantity_per_run=material.quantity_per_run,
                required_quantity=max(
                    runs,
                    _ceil(
                        Decimal(material.quantity_per_run) * runs * efficiency * material_modifier
                    ),
                ),
                available_at_location=local.get(material.type_id, 0),
                available_total=total.get(material.type_id, 0),
            )
            for material in blueprint.materials
        )
        time_efficiency = Decimal(1) - Decimal(blueprint.time_efficiency) / Decimal(100)
        duration_seconds = max(
            1,
            _ceil(Decimal(blueprint.base_time_seconds) * runs * time_efficiency * time_modifier),
        )
        run_shortfall = (
            0 if blueprint.available_runs is None else max(0, runs - blueprint.available_runs)
        )
        return ManufacturingPlan(
            blueprint=blueprint,
            target_quantity=target_quantity,
            runs=runs,
            planned_output=planned_output,
            surplus=planned_output - target_quantity,
            duration_seconds=duration_seconds,
            blueprint_run_shortfall=run_shortfall,
            materials=lines,
        )


def _ceil(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def _ceil_divide(dividend: int, divisor: int) -> int:
    if divisor <= 0:
        raise ValueError("manufacturing output per run must be positive")
    return (dividend + divisor - 1) // divisor
