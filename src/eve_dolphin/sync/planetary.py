"""Coordinated ESI planetary colony synchronization for one character."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol

from eve_dolphin.characters.token_service import CharacterAccessToken
from eve_dolphin.esi.models import EsiResponse
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import SsoMetadata
from eve_dolphin.sso.scopes import ScopePackage, scopes_for_packages
from eve_dolphin.sync.planetary_models import (
    PlanetarySyncResult,
    parse_colony,
    parse_colony_summaries,
)
from eve_dolphin.sync.planetary_repository import PlanetarySnapshotRepository

PLANETARY_SCOPE = "esi-planets.manage_planets.v1"
PLANETARY_CACHE_TTL = timedelta(minutes=10)
assert PLANETARY_SCOPE in scopes_for_packages(ScopePackage.PLANETARY_INDUSTRY)


class MissingPlanetaryScopeError(PermissionError):
    def __init__(self) -> None:
        super().__init__("character has not granted the required planetary scope")
        self.missing_scopes = (PLANETARY_SCOPE,)


class AccessTokenProvider(Protocol):
    def refresh(
        self, character_id: int, metadata: SsoMetadata, config: SsoConfig
    ) -> CharacterAccessToken: ...


class JsonGetter(Protocol):
    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str | int | bool] | None = None,
        access_token: str | None = None,
        character_id: int | None = None,
    ) -> EsiResponse: ...


class PlanetarySyncService:
    def __init__(
        self,
        token_service: AccessTokenProvider,
        esi_client: JsonGetter,
        repository: PlanetarySnapshotRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._token_service = token_service
        self._esi_client = esi_client
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._locks_guard = Lock()
        self._character_locks: dict[int, Lock] = {}

    def sync(
        self,
        character_id: int,
        metadata: SsoMetadata,
        config: SsoConfig,
    ) -> PlanetarySyncResult:
        with self._lock_for(character_id):
            return self._sync_locked(character_id, metadata, config)

    def _sync_locked(
        self,
        character_id: int,
        metadata: SsoMetadata,
        config: SsoConfig,
    ) -> PlanetarySyncResult:
        started_at = self._now()
        current = self._repository.current(character_id)
        if current is not None and started_at < current.fetched_at + PLANETARY_CACHE_TTL:
            return PlanetarySyncResult(snapshot=current, refreshed=False)
        run_id = self._repository.start_run(character_id, started_at)
        try:
            token = self._token_service.refresh(character_id, metadata, config)
            if PLANETARY_SCOPE not in token.granted_scopes:
                raise MissingPlanetaryScopeError
            response = self._esi_client.get_json(
                f"/characters/{character_id}/planets/",
                access_token=token.access_token,
                character_id=character_id,
            )
            summaries = parse_colony_summaries(response.payload, character_id)
            colonies = []
            for summary in summaries:
                planet_id = summary["planet_id"]
                detail = self._esi_client.get_json(
                    f"/characters/{character_id}/planets/{planet_id}/",
                    access_token=token.access_token,
                    character_id=character_id,
                )
                colonies.append(parse_colony(summary, detail.payload, detail.last_modified))
            snapshot = self._repository.activate(
                run_id,
                character_id,
                self._now(),
                tuple(colonies),
                response.last_modified,
            )
        except Exception as error:
            self._repository.fail_run(run_id, self._now(), type(error).__name__)
            raise
        return PlanetarySyncResult(snapshot=snapshot, refreshed=True)

    def _lock_for(self, character_id: int) -> Lock:
        with self._locks_guard:
            return self._character_locks.setdefault(character_id, Lock())

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value
