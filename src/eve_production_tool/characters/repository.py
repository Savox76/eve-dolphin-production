"""SQLite persistence for locally linked EVE characters."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Protocol

from eve_production_tool.characters.models import EveCharacter
from eve_production_tool.database import Database


class CharacterWriter(Protocol):
    def upsert(self, character: EveCharacter) -> None: ...

    def remove(self, character_id: int) -> bool: ...


class CharacterRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def upsert(self, character: EveCharacter) -> None:
        scopes_json = json.dumps(character.granted_scopes, separators=(",", ":"))
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO eve_characters(
                    character_id,
                    character_name,
                    owner_hash,
                    granted_scopes_json,
                    linked_at,
                    last_sync_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(character_id) DO UPDATE SET
                    character_name = excluded.character_name,
                    owner_hash = excluded.owner_hash,
                    granted_scopes_json = excluded.granted_scopes_json,
                    linked_at = excluded.linked_at
                """,
                (
                    character.character_id,
                    character.character_name,
                    character.owner_hash,
                    scopes_json,
                    character.linked_at.isoformat(),
                    character.last_sync_at.isoformat()
                    if character.last_sync_at is not None
                    else None,
                ),
            )

    def get(self, character_id: int) -> EveCharacter | None:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT character_id, character_name, owner_hash, granted_scopes_json,
                       linked_at, last_sync_at
                FROM eve_characters
                WHERE character_id = ?
                """,
                (character_id,),
            ).fetchone()
        return _character_from_row(row) if row is not None else None

    def list_all(self) -> tuple[EveCharacter, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT character_id, character_name, owner_hash, granted_scopes_json,
                       linked_at, last_sync_at
                FROM eve_characters
                ORDER BY character_name COLLATE NOCASE, character_id
                """
            ).fetchall()
        return tuple(_character_from_row(row) for row in rows)

    def remove(self, character_id: int) -> bool:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        with self._database.connect() as connection, connection:
            cursor = connection.execute(
                "DELETE FROM eve_characters WHERE character_id = ?", (character_id,)
            )
        return cursor.rowcount > 0


def _character_from_row(row: sqlite3.Row) -> EveCharacter:
    character_id = int(row["character_id"])
    character_name = str(row["character_name"])
    owner_value = row["owner_hash"]
    scopes_value = json.loads(str(row["granted_scopes_json"]))
    linked_at = datetime.fromisoformat(str(row["linked_at"]))
    last_sync_value = row["last_sync_at"]
    if not isinstance(scopes_value, list) or not all(
        isinstance(scope, str) for scope in scopes_value
    ):
        raise ValueError("stored character scopes are invalid")
    return EveCharacter(
        character_id=character_id,
        character_name=character_name,
        owner_hash=str(owner_value) if owner_value is not None else None,
        granted_scopes=tuple(scopes_value),
        linked_at=linked_at,
        last_sync_at=(datetime.fromisoformat(str(last_sync_value)) if last_sync_value else None),
    )
