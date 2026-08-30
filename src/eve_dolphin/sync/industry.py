"""Coordinated asset and blueprint synchronization for one linked character."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol

from eve_dolphin.characters.token_service import CharacterAccessToken
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import SsoMetadata
from eve_dolphin.sso.scopes import ScopePackage, scopes_for_packages
from eve_dolphin.sync.models import IndustrySyncResult, parse_assets, parse_blueprints
from eve_dolphin.sync.repository import IndustrySnapshotRepository

INDUSTRY_SCOPES = scopes_for_packages(ScopePackage.INDUSTRY)
REQUIRED_SCOPES = frozenset({"esi-assets.read_assets.v1", "esi-characters.read_blueprints.v1"})
assert frozenset(INDUSTRY_SCOPES) >= REQUIRED_SCOPES
INDUSTRY_CACHE_TTL = timedelta(hours=1)


class MissingIndustryScopesError(PermissionError):
    def __init__(self, missing_scopes: tuple[str, ...]) -> None:
        super().__init__("character has not granted the required industry scopes")
        self.missing_scopes = missing_scopes


class AccessTokenProvider(Protocol):
    def refresh(
        self, character_id: int, metadata: SsoMetadata, config: SsoConfig
    ) -> CharacterAccessToken: ...


class ListPaginator(Protocol):
    def get_list(
        self,
        path: str,
        *,
        access_token: str,
        character_id: int,
        params: Mapping[str, str | int | bool] | None = None,
    ) -> tuple[tuple[object, ...], str | None]: ...


class IndustrySyncService:
    def __init__(
        self,
        token_service: AccessTokenProvider,
        paginator: ListPaginator,
        repository: IndustrySnapshotRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._token_service = token_service
        self._paginator = paginator
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._locks_guard = Lock()
        self._character_locks: dict[int, Lock] = {}

    def sync(
        self,
        character_id: int,
        metadata: SsoMetadata,
        config: SsoConfig,
    ) -> IndustrySyncResult:
        with self._lock_for(character_id):
            return self._sync_locked(character_id, metadata, config)

    def _sync_locked(
        self,
        character_id: int,
        metadata: SsoMetadata,
        config: SsoConfig,
    ) -> IndustrySyncResult:
        started_at = self._now()
        current = self._repository.current(character_id)
        if current is not None and started_at < current.fetched_at + INDUSTRY_CACHE_TTL:
            return IndustrySyncResult(snapshot=current, refreshed=False)
        run_id = self._repository.start_run(character_id, started_at)
        try:
            token = self._token_service.refresh(character_id, metadata, config)
            missing = tuple(sorted(REQUIRED_SCOPES - set(token.granted_scopes)))
            if missing:
                raise MissingIndustryScopesError(missing)
            assets_payload, assets_modified = self._paginator.get_list(
                f"/characters/{character_id}/assets/",
                access_token=token.access_token,
                character_id=character_id,
            )
            blueprints_payload, blueprints_modified = self._paginator.get_list(
                f"/characters/{character_id}/blueprints/",
                access_token=token.access_token,
                character_id=character_id,
            )
            assets = parse_assets(assets_payload)
            blueprints = parse_blueprints(blueprints_payload)
            snapshot = self._repository.activate(
                run_id,
                character_id,
                self._now(),
                assets,
                blueprints,
                assets_modified,
                blueprints_modified,
            )
        except Exception as error:
            self._repository.fail_run(run_id, self._now(), type(error).__name__)
            raise
        return IndustrySyncResult(snapshot=snapshot, refreshed=True)

    def _lock_for(self, character_id: int) -> Lock:
        with self._locks_guard:
            return self._character_locks.setdefault(character_id, Lock())

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value
