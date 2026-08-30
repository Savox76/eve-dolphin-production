"""Read the active SDE's complete planetary-production catalog."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal

from eve_dolphin.database import Database
from eve_dolphin.pi.models import (
    PiCatalog,
    PiCommodity,
    PiRecipe,
    PiRecipeItem,
    PiTier,
    UniverseLocation,
)


class PiCatalogRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def load(self, language: str) -> PiCatalog:
        name_column = _name_column(language)
        with self._database.connect() as connection:
            active = connection.execute(
                "SELECT build_number FROM sde_current WHERE singleton = 1"
            ).fetchone()
            if active is None:
                return PiCatalog({}, {}, {}, {})
            build_number = int(active["build_number"])
            schematic_rows = connection.execute(
                f"""
                SELECT schematic_id, cycle_time_seconds,
                       COALESCE(NULLIF({name_column}, ''), name_en) AS display_name
                FROM sde_planet_schematics
                WHERE build_number = ?
                ORDER BY schematic_id
                """,
                (build_number,),
            ).fetchall()
            item_rows = connection.execute(
                f"""
                SELECT item.schematic_id, item.type_id, item.is_input, item.quantity,
                       COALESCE(NULLIF(type.{name_column}, ''), type.name_en) AS display_name,
                       type.volume
                FROM sde_planet_schematic_types AS item
                JOIN sde_types AS type
                  ON type.build_number = item.build_number AND type.type_id = item.type_id
                WHERE item.build_number = ?
                ORDER BY item.schematic_id, item.is_input DESC, item.type_id
                """,
                (build_number,),
            ).fetchall()
            capacity_rows = connection.execute(
                """
                SELECT type_id, capacity FROM sde_types
                WHERE build_number = ? AND capacity IS NOT NULL AND capacity > 0
                """,
                (build_number,),
            ).fetchall()

        item_data: dict[int, list[tuple[int, bool, int, str, Decimal]]] = defaultdict(list)
        for row in item_rows:
            item_data[int(row["schematic_id"])].append(
                (
                    int(row["type_id"]),
                    bool(row["is_input"]),
                    int(row["quantity"]),
                    str(row["display_name"]),
                    _decimal(row["volume"]),
                )
            )
        raw_recipes: dict[int, tuple[int, str, int, tuple[tuple[int, int], ...], int, int]] = {}
        names: dict[int, str] = {}
        volumes: dict[int, Decimal] = {}
        for row in schematic_rows:
            schematic_id = int(row["schematic_id"])
            inputs: list[tuple[int, int]] = []
            outputs: list[tuple[int, int]] = []
            for type_id, is_input, quantity, name, volume in item_data[schematic_id]:
                names[type_id] = name
                volumes[type_id] = volume
                (inputs if is_input else outputs).append((type_id, quantity))
            if len(outputs) != 1 or not inputs:
                raise ValueError("active SDE PI schematic must have inputs and one output")
            output_id, output_quantity = outputs[0]
            if output_id in raw_recipes:
                raise ValueError("active SDE has multiple PI schematics for one product")
            raw_recipes[output_id] = (
                schematic_id,
                str(row["display_name"]),
                int(row["cycle_time_seconds"]),
                tuple(inputs),
                output_id,
                output_quantity,
            )

        tiers = _derive_tiers(raw_recipes)
        commodities = {
            type_id: PiCommodity(type_id, names[type_id], volumes[type_id], tiers[type_id])
            for type_id in names
        }
        recipes_by_output: dict[int, PiRecipe] = {}
        recipes_by_id: dict[int, PiRecipe] = {}
        for output_type_id, raw in raw_recipes.items():
            schematic_id, name, cycle_time, raw_inputs, _, output_quantity = raw
            recipe = PiRecipe(
                schematic_id=schematic_id,
                name=name,
                cycle_time_seconds=cycle_time,
                inputs=tuple(
                    PiRecipeItem(commodities[type_id], quantity) for type_id, quantity in raw_inputs
                ),
                output=PiRecipeItem(commodities[output_type_id], output_quantity),
            )
            recipes_by_output[output_type_id] = recipe
            recipes_by_id[schematic_id] = recipe
        return PiCatalog(
            commodities=commodities,
            recipes_by_output=recipes_by_output,
            recipes_by_id=recipes_by_id,
            type_capacities_m3={
                int(row["type_id"]): _decimal(row["capacity"]) for row in capacity_rows
            },
        )

    def locations(
        self,
        planet_ids: Iterable[int],
        language: str,
    ) -> dict[int, UniverseLocation]:
        identifiers = tuple(sorted(set(planet_ids)))
        if not identifiers:
            return {}
        if any(identifier <= 0 for identifier in identifiers):
            raise ValueError("planet IDs must be positive")
        name_column = _name_column(language)
        locations: dict[int, UniverseLocation] = {}
        with self._database.connect() as connection:
            active = connection.execute(
                "SELECT build_number FROM sde_current WHERE singleton = 1"
            ).fetchone()
            if active is None:
                return {}
            build_number = int(active["build_number"])
            for offset in range(0, len(identifiers), 500):
                chunk = identifiers[offset : offset + 500]
                placeholders = ", ".join("?" for _identifier in chunk)
                rows = connection.execute(
                    f"""
                    SELECT planet.planet_id, planet.celestial_index,
                           system.solar_system_id,
                           COALESCE(NULLIF(system.{name_column}, ''), system.name_en)
                               AS system_name,
                           system.security_status
                    FROM sde_planets AS planet
                    JOIN sde_solar_systems AS system
                      ON system.build_number = planet.build_number
                     AND system.solar_system_id = planet.solar_system_id
                    WHERE planet.build_number = ?
                      AND planet.planet_id IN ({placeholders})
                    """,
                    (build_number, *chunk),
                ).fetchall()
                for row in rows:
                    system_name = str(row["system_name"])
                    planet_id = int(row["planet_id"])
                    locations[planet_id] = UniverseLocation(
                        planet_id=planet_id,
                        planet_name=f"{system_name} {_roman(int(row['celestial_index']))}",
                        solar_system_id=int(row["solar_system_id"]),
                        solar_system_name=system_name,
                        security_status=_decimal(row["security_status"]),
                    )
        return locations


def _derive_tiers(
    recipes: dict[int, tuple[int, str, int, tuple[tuple[int, int], ...], int, int]],
) -> dict[int, PiTier]:
    tiers: dict[int, PiTier] = {}
    visiting: set[int] = set()

    def tier(type_id: int) -> PiTier:
        if type_id in tiers:
            return tiers[type_id]
        recipe = recipes.get(type_id)
        if recipe is None:
            tiers[type_id] = PiTier.RAW
            return PiTier.RAW
        if type_id in visiting:
            raise ValueError("active SDE PI schematics contain a cycle")
        visiting.add(type_id)
        input_tier = max(tier(input_id) for input_id, _quantity in recipe[3])
        visiting.remove(type_id)
        value = int(input_tier) + 1
        if value > int(PiTier.ADVANCED):
            raise ValueError("active SDE PI schematic depth exceeds P4")
        tiers[type_id] = PiTier(value)
        return tiers[type_id]

    identifiers = set(recipes)
    identifiers.update(input_id for recipe in recipes.values() for input_id, _ in recipe[3])
    for identifier in identifiers:
        tier(identifier)
    return tiers


def _name_column(language: str) -> str:
    if language == "de":
        return "name_de"
    if language == "en":
        return "name_en"
    raise ValueError("unsupported PI catalog language")


def _decimal(value: object) -> Decimal:
    return Decimal("0") if value is None else Decimal(str(value))


def _roman(value: int) -> str:
    if value <= 0 or value > 99:
        return str(value)
    numerals = (
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remainder = value
    result: list[str] = []
    for amount, numeral in numerals:
        while remainder >= amount:
            result.append(numeral)
            remainder -= amount
    return "".join(result)
