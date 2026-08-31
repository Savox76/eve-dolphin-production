"""Immutable manufacturing catalog and calculation models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BlueprintKind(StrEnum):
    ORIGINAL = "original"
    COPY = "copy"


@dataclass(frozen=True, slots=True)
class BlueprintMaterial:
    type_id: int
    name: str
    quantity_per_run: int


@dataclass(frozen=True, slots=True)
class OwnedManufacturingBlueprint:
    item_id: int
    blueprint_type_id: int
    blueprint_name: str
    product_type_id: int
    product_name: str
    output_per_run: int
    base_time_seconds: int
    character_id: int
    character_name: str
    location_id: int
    location_flag: str
    kind: BlueprintKind
    material_efficiency: int
    time_efficiency: int
    available_runs: int | None
    materials: tuple[BlueprintMaterial, ...]


@dataclass(frozen=True, slots=True)
class ManufacturingMaterialLine:
    type_id: int
    name: str
    base_quantity_per_run: int
    required_quantity: int
    available_at_location: int
    available_total: int

    @property
    def missing_at_location(self) -> int:
        return max(0, self.required_quantity - self.available_at_location)


@dataclass(frozen=True, slots=True)
class ManufacturingPlan:
    blueprint: OwnedManufacturingBlueprint
    target_quantity: int
    runs: int
    planned_output: int
    surplus: int
    duration_seconds: int
    blueprint_run_shortfall: int
    materials: tuple[ManufacturingMaterialLine, ...]

    @property
    def can_run_with_blueprint(self) -> bool:
        return self.blueprint_run_shortfall == 0

    @property
    def materials_available_at_location(self) -> bool:
        return all(line.missing_at_location == 0 for line in self.materials)
