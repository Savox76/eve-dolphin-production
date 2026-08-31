"""Join active SDE recipes with active personal blueprint and asset snapshots."""

from __future__ import annotations

import sqlite3
from collections import defaultdict

from eve_dolphin.database import Database
from eve_dolphin.manufacturing.models import (
    BlueprintKind,
    BlueprintMaterial,
    OwnedManufacturingBlueprint,
)


class ManufacturingRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def list_blueprints(self, language: str) -> tuple[OwnedManufacturingBlueprint, ...]:
        name_column = _name_column(language)
        with self._database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT blueprint.item_id,
                       blueprint.type_id AS blueprint_type_id,
                       blueprint.location_id, blueprint.location_flag,
                       blueprint.quantity, blueprint.runs,
                       blueprint.material_efficiency, blueprint.time_efficiency,
                       character.character_id, character.character_name,
                       COALESCE(NULLIF(blueprint_type.{name_column}, ''),
                                blueprint_type.name_en) AS blueprint_name,
                       product.product_type_id, product.quantity AS output_per_run,
                       COALESCE(NULLIF(product_type.{name_column}, ''),
                                product_type.name_en) AS product_name,
                       activity.time_seconds
                FROM sde_current AS active
                JOIN sde_blueprint_activities AS activity
                  ON activity.build_number = active.build_number
                 AND activity.activity = 'manufacturing'
                JOIN sde_blueprint_products AS product
                  ON product.build_number = activity.build_number
                 AND product.blueprint_type_id = activity.blueprint_type_id
                 AND product.activity = activity.activity
                JOIN sde_types AS blueprint_type
                  ON blueprint_type.build_number = activity.build_number
                 AND blueprint_type.type_id = activity.blueprint_type_id
                JOIN sde_types AS product_type
                  ON product_type.build_number = product.build_number
                 AND product_type.type_id = product.product_type_id
                JOIN character_blueprints AS blueprint
                  ON blueprint.type_id = activity.blueprint_type_id
                JOIN industry_current AS current
                  ON current.snapshot_id = blueprint.snapshot_id
                JOIN eve_characters AS character
                  ON character.character_id = current.character_id
                WHERE active.singleton = 1
                  AND activity.time_seconds IS NOT NULL
                  AND activity.time_seconds > 0
                ORDER BY product_name COLLATE NOCASE,
                         character.character_name COLLATE NOCASE,
                         blueprint.item_id
                """
            ).fetchall()
            if not rows:
                return ()
            build_row = connection.execute(
                "SELECT build_number FROM sde_current WHERE singleton = 1"
            ).fetchone()
            assert build_row is not None
            material_rows = connection.execute(
                f"""
                SELECT material.blueprint_type_id, material.material_type_id,
                       material.quantity,
                       COALESCE(NULLIF(type.{name_column}, ''), type.name_en) AS material_name
                FROM sde_blueprint_materials AS material
                JOIN sde_types AS type
                  ON type.build_number = material.build_number
                 AND type.type_id = material.material_type_id
                WHERE material.build_number = ?
                  AND material.activity = 'manufacturing'
                ORDER BY material.blueprint_type_id, material_name COLLATE NOCASE
                """,
                (int(build_row["build_number"]),),
            ).fetchall()

        materials: dict[int, list[BlueprintMaterial]] = defaultdict(list)
        for row in material_rows:
            materials[int(row["blueprint_type_id"])].append(
                BlueprintMaterial(
                    type_id=int(row["material_type_id"]),
                    name=str(row["material_name"]),
                    quantity_per_run=int(row["quantity"]),
                )
            )
        product_counts: dict[int, int] = defaultdict(int)
        for row in rows:
            product_counts[int(row["item_id"])] += 1
        if any(count != 1 for count in product_counts.values()):
            raise ValueError("manufacturing blueprint must have exactly one product")
        return tuple(self._blueprint(row, materials) for row in rows)

    def asset_quantities(
        self,
        type_ids: set[int],
        location_id: int,
    ) -> tuple[dict[int, int], dict[int, int]]:
        if not type_ids:
            return {}, {}
        identifiers = tuple(sorted(type_ids))
        placeholders = ", ".join("?" for _identifier in identifiers)
        with self._database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT asset.type_id,
                       SUM(asset.quantity) AS total_quantity,
                       SUM(CASE WHEN asset.location_id = ? THEN asset.quantity ELSE 0 END)
                           AS local_quantity
                FROM character_assets AS asset
                JOIN industry_current AS current ON current.snapshot_id = asset.snapshot_id
                WHERE asset.type_id IN ({placeholders})
                GROUP BY asset.type_id
                """,
                (location_id, *identifiers),
            ).fetchall()
        total = {int(row["type_id"]): int(row["total_quantity"]) for row in rows}
        local = {int(row["type_id"]): int(row["local_quantity"]) for row in rows}
        return local, total

    @staticmethod
    def _blueprint(
        row: sqlite3.Row,
        materials: dict[int, list[BlueprintMaterial]],
    ) -> OwnedManufacturingBlueprint:
        blueprint_type_id = int(row["blueprint_type_id"])
        quantity = int(row["quantity"])
        runs = int(row["runs"])
        material_efficiency = int(row["material_efficiency"])
        time_efficiency = int(row["time_efficiency"])
        if quantity not in (-2, -1):
            raise ValueError("manufacturing blueprint has an invalid quantity marker")
        kind = BlueprintKind.COPY if quantity == -2 else BlueprintKind.ORIGINAL
        if (kind is BlueprintKind.ORIGINAL and runs != -1) or (
            kind is BlueprintKind.COPY and runs < 0
        ):
            raise ValueError("manufacturing blueprint has invalid available runs")
        if not 0 <= material_efficiency <= 10 or not 0 <= time_efficiency <= 20:
            raise ValueError("manufacturing blueprint has invalid ME or TE")
        return OwnedManufacturingBlueprint(
            item_id=int(row["item_id"]),
            blueprint_type_id=blueprint_type_id,
            blueprint_name=str(row["blueprint_name"]),
            product_type_id=int(row["product_type_id"]),
            product_name=str(row["product_name"]),
            output_per_run=int(row["output_per_run"]),
            base_time_seconds=int(row["time_seconds"]),
            character_id=int(row["character_id"]),
            character_name=str(row["character_name"]),
            location_id=int(row["location_id"]),
            location_flag=str(row["location_flag"]),
            kind=kind,
            material_efficiency=material_efficiency,
            time_efficiency=time_efficiency,
            available_runs=None if kind is BlueprintKind.ORIGINAL else runs,
            materials=tuple(materials[blueprint_type_id]),
        )


def _name_column(language: str) -> str:
    if language == "de":
        return "name_de"
    if language == "en":
        return "name_en"
    raise ValueError("unsupported manufacturing catalog language")
