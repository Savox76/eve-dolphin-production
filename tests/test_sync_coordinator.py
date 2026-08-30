from __future__ import annotations

from threading import Barrier, Lock

from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import SsoMetadata
from eve_dolphin.sync.coordinator import CharacterSyncCoordinator


class _ParallelService:
    def __init__(self, barrier: Barrier) -> None:
        self._barrier = barrier
        self._lock = Lock()
        self.calls: list[int] = []

    def sync(self, character_id: int, metadata: SsoMetadata, config: SsoConfig) -> object:
        self._barrier.wait(timeout=2)
        with self._lock:
            self.calls.append(character_id)
        return object()


class _SelectiveService:
    def sync(self, character_id: int, metadata: SsoMetadata, config: SsoConfig) -> object:
        if character_id == 8:
            raise _MissingScopeError
        return object()


class _MissingScopeError(PermissionError):
    missing_scopes = ("esi-planets.manage_planets.v1",)


class _AlwaysService:
    def __init__(self) -> None:
        self._lock = Lock()
        self.calls: list[int] = []

    def sync(self, character_id: int, metadata: SsoMetadata, config: SsoConfig) -> object:
        with self._lock:
            self.calls.append(character_id)
        return object()


def test_two_characters_synchronize_in_parallel_and_keep_requested_order() -> None:
    service = _ParallelService(Barrier(2))
    coordinator = CharacterSyncCoordinator({"industry": service}, max_workers=2)

    batch = coordinator.sync_characters((8, 7), _metadata(), _config())

    assert [outcome.character_id for outcome in batch.outcomes] == [8, 7]
    assert set(service.calls) == {7, 8}
    assert batch.succeeded_count == 2
    assert batch.failed_count == 0


def test_character_failure_is_isolated_and_remaining_resources_continue() -> None:
    final_service = _AlwaysService()
    coordinator = CharacterSyncCoordinator(
        {"planetary": _SelectiveService(), "jobs": final_service}, max_workers=2
    )

    batch = coordinator.sync_characters((7, 8), _metadata(), _config())

    first, second = batch.outcomes
    assert first.succeeded is True
    assert first.succeeded_resources == ("planetary", "jobs")
    assert second.succeeded is False
    assert second.succeeded_resources == ("jobs",)
    assert second.failures[0].resource == "planetary"
    assert second.failures[0].error_type == "_MissingScopeError"
    assert batch.missing_scopes == ("esi-planets.manage_planets.v1",)
    assert set(final_service.calls) == {7, 8}


def _metadata() -> SsoMetadata:
    return SsoMetadata(
        issuer="https://login.eveonline.com",
        authorization_endpoint="https://login.eveonline.com/v2/oauth/authorize",
        token_endpoint="https://login.eveonline.com/v2/oauth/token",
        jwks_uri="https://login.eveonline.com/oauth/jwks",
    )


def _config() -> SsoConfig:
    return SsoConfig(client_id="client-id")
