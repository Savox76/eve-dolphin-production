"""Deterministic PI extractor, factory, and storage forecasts."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import ROUND_FLOOR, Decimal

from eve_dolphin.pi.models import (
    ColonyForecast,
    ForecastQuantity,
    ForecastRate,
    PiCatalog,
)
from eve_dolphin.sync.planetary_models import PlanetColony

SECONDS_PER_HOUR = Decimal(3600)


def forecast_colony(
    colony: PlanetColony,
    catalog: PiCatalog,
    now: datetime,
    horizon: timedelta,
) -> ColonyForecast:
    if now.tzinfo is None:
        raise ValueError("PI forecast time must include a timezone")
    if horizon <= timedelta(0):
        raise ValueError("PI forecast horizon must be positive")

    inventory: Counter[int] = Counter()
    for pin in colony.pins:
        for content in pin.contents:
            inventory[content.type_id] += content.amount
    initial_volume = _inventory_volume(inventory, catalog)

    extracted: Counter[int] = Counter()
    rates: dict[int, Decimal] = defaultdict(Decimal)
    horizon_end = now + horizon
    for pin in colony.pins:
        extractor = pin.extractor_details
        if (
            extractor is None
            or extractor.product_type_id is None
            or extractor.cycle_time is None
            or extractor.cycle_time <= 0
            or extractor.qty_per_cycle is None
            or extractor.qty_per_cycle <= 0
            or pin.expiry_time is None
            or pin.expiry_time <= now
        ):
            continue
        product_type_id = extractor.product_type_id
        rates[product_type_id] += (
            Decimal(extractor.qty_per_cycle) * SECONDS_PER_HOUR / Decimal(extractor.cycle_time)
        )
        seconds = Decimal(str((min(pin.expiry_time, horizon_end) - now).total_seconds()))
        cycles = int((seconds / Decimal(extractor.cycle_time)).to_integral_value(ROUND_FLOOR))
        quantity = cycles * extractor.qty_per_cycle
        extracted[product_type_id] += quantity
        inventory[product_type_id] += quantity

    factory_outputs: Counter[int] = Counter()
    stalled_factories = 0
    constrained_factories = 0
    incomplete_factories = 0
    factories_by_tier: dict[int, list[int]] = defaultdict(list)
    for pin in colony.pins:
        if pin.factory_schematic_id is None:
            continue
        recipe = catalog.recipes_by_id.get(pin.factory_schematic_id)
        if recipe is None:
            incomplete_factories += 1
            continue
        factories_by_tier[int(recipe.output.commodity.tier)].append(pin.factory_schematic_id)

    horizon_seconds = Decimal(str(horizon.total_seconds()))
    for tier in sorted(factories_by_tier):
        for schematic_id in factories_by_tier[tier]:
            recipe = catalog.recipes_by_id[schematic_id]
            capacity_cycles = int(
                (horizon_seconds / Decimal(recipe.cycle_time_seconds)).to_integral_value(
                    ROUND_FLOOR
                )
            )
            supplied_cycles = min(
                (inventory[item.commodity.type_id] // item.quantity for item in recipe.inputs),
                default=0,
            )
            cycles = min(capacity_cycles, supplied_cycles)
            if capacity_cycles > 0 and cycles == 0:
                stalled_factories += 1
            elif cycles < capacity_cycles:
                constrained_factories += 1
            for item in recipe.inputs:
                inventory[item.commodity.type_id] -= cycles * item.quantity
            output_quantity = cycles * recipe.output.quantity
            inventory[recipe.output.commodity.type_id] += output_quantity
            factory_outputs[recipe.output.commodity.type_id] += output_quantity

    storage_capacity = sum(
        (catalog.type_capacities_m3.get(pin.type_id, Decimal(0)) for pin in colony.pins),
        start=Decimal(0),
    )
    projected_volume = _inventory_volume(inventory, catalog)
    fill_percent = (
        min(Decimal(100), initial_volume * Decimal(100) / storage_capacity)
        if storage_capacity > 0
        else None
    )
    estimated_full_at = None
    growth = projected_volume - initial_volume
    if storage_capacity > initial_volume and growth > 0:
        horizon_seconds_float = Decimal(str(horizon.total_seconds()))
        seconds_to_full = (storage_capacity - initial_volume) * horizon_seconds_float / growth
        estimated_full_at = now + timedelta(seconds=float(seconds_to_full))

    return ColonyForecast(
        horizon=horizon,
        extractor_rates=_rates(rates, catalog),
        extracted=_quantities(extracted, catalog),
        factory_outputs=_quantities(factory_outputs, catalog),
        projected_inventory=_quantities(inventory, catalog),
        stalled_factories=stalled_factories,
        constrained_factories=constrained_factories,
        incomplete_factories=incomplete_factories,
        storage_used_m3=initial_volume,
        storage_capacity_m3=storage_capacity,
        storage_fill_percent=fill_percent,
        estimated_full_at=estimated_full_at,
    )


def _inventory_volume(inventory: Counter[int], catalog: PiCatalog) -> Decimal:
    return sum(
        (
            Decimal(quantity) * catalog.commodities[type_id].volume_m3
            for type_id, quantity in inventory.items()
            if type_id in catalog.commodities
        ),
        start=Decimal(0),
    )


def _quantities(values: Counter[int], catalog: PiCatalog) -> tuple[ForecastQuantity, ...]:
    known = tuple(
        (type_id, quantity)
        for type_id, quantity in values.items()
        if quantity > 0 and type_id in catalog.commodities
    )
    return tuple(
        ForecastQuantity(catalog.commodities[type_id], quantity)
        for type_id, quantity in sorted(
            known,
            key=lambda item: (
                int(catalog.commodities[item[0]].tier),
                catalog.commodities[item[0]].name.casefold(),
            ),
        )
    )


def _rates(values: dict[int, Decimal], catalog: PiCatalog) -> tuple[ForecastRate, ...]:
    known = tuple(
        (type_id, rate)
        for type_id, rate in values.items()
        if rate > 0 and type_id in catalog.commodities
    )
    return tuple(
        ForecastRate(catalog.commodities[type_id], rate)
        for type_id, rate in sorted(
            known, key=lambda item: catalog.commodities[item[0]].name.casefold()
        )
    )
