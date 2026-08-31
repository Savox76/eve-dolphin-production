"""Persistent editable PI target-plan definitions."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from eve_dolphin.database import Database
from eve_dolphin.pi.models import (
    PiOperationMode,
    PiPlanRequest,
    PiStorageStrategy,
    PiTier,
    SavedPiPlan,
)


class SavedPiPlanRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def list_all(self) -> tuple[SavedPiPlan, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM pi_saved_plans ORDER BY name COLLATE NOCASE, id"
            ).fetchall()
        return tuple(_plan(row) for row in rows)

    def get(self, plan_id: int) -> SavedPiPlan | None:
        if plan_id <= 0:
            raise ValueError("saved PI plan ID must be positive")
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM pi_saved_plans WHERE id = ?", (plan_id,)
            ).fetchone()
        return _plan(row) if row is not None else None

    def save(self, plan: SavedPiPlan) -> SavedPiPlan:
        now = datetime.now(UTC).isoformat()
        request = plan.request
        values = (
            plan.name.strip(),
            request.target_type_id,
            request.target_quantity,
            request.days,
            request.profile_id,
            request.operation_mode.value,
            int(request.source_tier) if request.source_tier is not None else None,
            request.storage_strategy.value,
            now,
        )
        with self._database.connect() as connection, connection:
            if plan.plan_id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO pi_saved_plans(
                        name, target_type_id, target_quantity, days, profile_id,
                        operation_mode, source_tier, storage_strategy, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("SQLite did not create a saved PI plan ID")
                plan_id = int(cursor.lastrowid)
            else:
                cursor = connection.execute(
                    """
                    UPDATE pi_saved_plans
                    SET name = ?, target_type_id = ?, target_quantity = ?, days = ?,
                        profile_id = ?, operation_mode = ?, source_tier = ?,
                        storage_strategy = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (*values, plan.plan_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("saved PI plan does not exist")
                plan_id = plan.plan_id
        stored = self.get(plan_id)
        if stored is None:
            raise RuntimeError("saved PI plan disappeared after write")
        return stored

    def delete(self, plan_id: int) -> None:
        if plan_id <= 0:
            raise ValueError("saved PI plan ID must be positive")
        with self._database.connect() as connection, connection:
            connection.execute("DELETE FROM pi_saved_plans WHERE id = ?", (plan_id,))


def _plan(row: sqlite3.Row) -> SavedPiPlan:
    source_value = row["source_tier"]
    return SavedPiPlan(
        int(row["id"]),
        str(row["name"]),
        PiPlanRequest(
            target_type_id=int(row["target_type_id"]),
            target_quantity=int(row["target_quantity"]),
            days=int(row["days"]),
            profile_id=int(row["profile_id"]),
            operation_mode=PiOperationMode(str(row["operation_mode"])),
            source_tier=PiTier(int(source_value)) if source_value is not None else None,
            storage_strategy=PiStorageStrategy(str(row["storage_strategy"])),
        ),
    )
