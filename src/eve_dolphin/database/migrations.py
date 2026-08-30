"""Ordered, transactional SQLite schema migrations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    description: str
    sql: str


MIGRATIONS = (
    Migration(
        version=1,
        description="local profile, characters and synchronization foundation",
        sql="""
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE eve_characters (
            character_id INTEGER PRIMARY KEY,
            character_name TEXT NOT NULL,
            owner_hash TEXT,
            granted_scopes_json TEXT NOT NULL DEFAULT '[]',
            linked_at TEXT NOT NULL,
            last_sync_at TEXT
        );

        CREATE TABLE sync_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER,
            sync_kind TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'cancelled')),
            started_at TEXT NOT NULL,
            finished_at TEXT,
            message TEXT,
            FOREIGN KEY (character_id) REFERENCES eve_characters(character_id) ON DELETE CASCADE
        );

        CREATE INDEX sync_runs_character_started_idx
            ON sync_runs(character_id, started_at DESC);
        """,
    ),
    Migration(
        version=2,
        description="character authorization health",
        sql="""
        ALTER TABLE eve_characters
            ADD COLUMN authorization_status TEXT NOT NULL DEFAULT 'active'
            CHECK (authorization_status IN ('active', 'reauthorization_required'));

        ALTER TABLE eve_characters
            ADD COLUMN authorization_error_at TEXT;
        """,
    ),
)

LATEST_SCHEMA_VERSION = MIGRATIONS[-1].version
