"""Composition boundary for user-triggered Phase 2 synchronization."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from eve_dolphin.characters import CharacterRepository, CharacterTokenService
from eve_dolphin.database import Database
from eve_dolphin.esi import EsiPaginator, EveEsiClient
from eve_dolphin.sde import EveSdeClient, SdeImporter, SdeRepository, SdeUpdateService
from eve_dolphin.security import KeyringTokenStore
from eve_dolphin.sso.client import EveSsoClient
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.validation import EveAccessTokenValidator
from eve_dolphin.sync.coordinator import (
    CharacterResourceSync,
    CharacterSyncBatch,
    CharacterSyncCoordinator,
)
from eve_dolphin.sync.industry import IndustrySyncService
from eve_dolphin.sync.jobs import IndustryJobSyncService
from eve_dolphin.sync.jobs_repository import IndustryJobSnapshotRepository
from eve_dolphin.sync.planetary import PlanetarySyncService
from eve_dolphin.sync.planetary_repository import PlanetarySnapshotRepository
from eve_dolphin.sync.repository import IndustrySnapshotRepository

LOGGER = logging.getLogger(__name__)


class PhaseTwoSyncRunner:
    """Update the SDE and synchronize every linked character on demand."""

    def __init__(
        self,
        database: Database,
        characters: CharacterRepository,
        sde_dir: Path,
    ) -> None:
        self._database = database
        self._characters = characters
        self._sde_dir = sde_dir

    def sync_all(self) -> CharacterSyncBatch:
        global_failures = self._update_sde()
        character_ids = tuple(character.character_id for character in self._characters.list_all())
        if not character_ids:
            return CharacterSyncBatch((), global_failures)

        config = SsoConfig.from_environment()
        sso_client = EveSsoClient()
        metadata = sso_client.fetch_metadata()
        token_service = CharacterTokenService(
            self._characters,
            KeyringTokenStore(),
            sso_client,
            EveAccessTokenValidator(),
        )
        esi_client = EveEsiClient()
        try:
            services: dict[str, CharacterResourceSync] = {
                "industry": IndustrySyncService(
                    token_service,
                    EsiPaginator(esi_client),
                    IndustrySnapshotRepository(self._database),
                ),
                "industry_jobs": IndustryJobSyncService(
                    token_service,
                    esi_client,
                    IndustryJobSnapshotRepository(self._database),
                ),
                "planetary": PlanetarySyncService(
                    token_service,
                    esi_client,
                    PlanetarySnapshotRepository(self._database),
                ),
            }
            batch = CharacterSyncCoordinator(services).sync_characters(
                character_ids, metadata, config
            )
            return CharacterSyncBatch(batch.outcomes, global_failures)
        finally:
            esi_client.close()

    def _update_sde(self) -> tuple[str, ...]:
        run_id = self._start_sde_run()
        client = EveSdeClient()
        try:
            SdeUpdateService(
                client,
                SdeImporter(self._database),
                SdeRepository(self._database),
                self._sde_dir,
            ).update()
        except Exception as error:
            LOGGER.exception("Official EVE SDE update failed")
            self._finish_sde_run(run_id, "failed", type(error).__name__)
            return (type(error).__name__,)
        finally:
            client.close()
        self._finish_sde_run(run_id, "succeeded", None)
        return ()

    def _start_sde_run(self) -> int:
        with self._database.connect() as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO sync_runs(character_id, sync_kind, status, started_at)
                VALUES (NULL, 'sde', 'running', ?)
                """,
                (datetime.now(UTC).isoformat(),),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not create an SDE synchronization run")
            return cursor.lastrowid

    def _finish_sde_run(self, run_id: int, status: str, message: str | None) -> None:
        with self._database.connect() as connection, connection:
            result = connection.execute(
                """
                UPDATE sync_runs SET status = ?, finished_at = ?, message = ?
                WHERE id = ? AND character_id IS NULL AND status = 'running'
                """,
                (status, datetime.now(UTC).isoformat(), message, run_id),
            )
            if result.rowcount != 1:
                raise RuntimeError("SDE synchronization run is not active")
