"""Character Industry Job synchronization with persistent cache boundaries."""

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
from eve_dolphin.sync.job_models import IndustryJobSyncResult, parse_industry_jobs
from eve_dolphin.sync.jobs_repository import IndustryJobSnapshotRepository

JOB_SCOPE = "esi-industry.read_character_jobs.v1"
JOB_CACHE_TTL = timedelta(minutes=5)
assert JOB_SCOPE in scopes_for_packages(ScopePackage.INDUSTRY)


class MissingIndustryJobScopeError(PermissionError):
    def __init__(self) -> None:
        super().__init__("character has not granted the required industry job scope")
        self.missing_scopes = (JOB_SCOPE,)


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


class IndustryJobSyncService:
    def __init__(
        self,
        token_service: AccessTokenProvider,
        esi_client: JsonGetter,
        repository: IndustryJobSnapshotRepository,
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
    ) -> IndustryJobSyncResult:
        with self._lock_for(character_id):
            return self._sync_locked(character_id, metadata, config)

    def _sync_locked(
        self,
        character_id: int,
        metadata: SsoMetadata,
        config: SsoConfig,
    ) -> IndustryJobSyncResult:
        started_at = self._now()
        current = self._repository.current(character_id)
        if current is not None and started_at < current.fetched_at + JOB_CACHE_TTL:
            return IndustryJobSyncResult(snapshot=current, refreshed=False)
        run_id = self._repository.start_run(character_id, started_at)
        try:
            token = self._token_service.refresh(character_id, metadata, config)
            if JOB_SCOPE not in token.granted_scopes:
                raise MissingIndustryJobScopeError
            response = self._esi_client.get_json(
                f"/characters/{character_id}/industry/jobs/",
                params={"include_completed": True},
                access_token=token.access_token,
                character_id=character_id,
            )
            jobs = parse_industry_jobs(response.payload)
            snapshot = self._repository.activate(
                run_id,
                character_id,
                self._now(),
                jobs,
                response.last_modified,
            )
        except Exception as error:
            self._repository.fail_run(run_id, self._now(), type(error).__name__)
            raise
        return IndustryJobSyncResult(snapshot=snapshot, refreshed=True)

    def _lock_for(self, character_id: int) -> Lock:
        with self._locks_guard:
            return self._character_locks.setdefault(character_id, Lock())

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value
