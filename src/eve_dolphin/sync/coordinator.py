"""Bounded parallel synchronization across isolated EVE characters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import SsoMetadata


class CharacterResourceSync(Protocol):
    def sync(self, character_id: int, metadata: SsoMetadata, config: SsoConfig) -> object: ...


@dataclass(frozen=True, slots=True)
class ResourceSyncFailure:
    resource: str
    error_type: str
    missing_scopes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CharacterSyncOutcome:
    character_id: int
    succeeded_resources: tuple[str, ...]
    failures: tuple[ResourceSyncFailure, ...]

    @property
    def succeeded(self) -> bool:
        return not self.failures


@dataclass(frozen=True, slots=True)
class CharacterSyncBatch:
    outcomes: tuple[CharacterSyncOutcome, ...]
    global_failures: tuple[str, ...] = ()

    @property
    def succeeded_count(self) -> int:
        return sum(outcome.succeeded for outcome in self.outcomes)

    @property
    def failed_count(self) -> int:
        return len(self.outcomes) - self.succeeded_count

    @property
    def missing_scopes(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                scope
                for outcome in self.outcomes
                for failure in outcome.failures
                for scope in failure.missing_scopes
            )
        )


class CharacterSyncCoordinator:
    """Run each character independently while bounding concurrent ESI work."""

    def __init__(
        self,
        services: Mapping[str, CharacterResourceSync],
        *,
        max_workers: int = 4,
    ) -> None:
        if not services or any(not name.strip() for name in services):
            raise ValueError("at least one named synchronization service is required")
        if max_workers <= 0:
            raise ValueError("max_workers must be positive")
        self._services = tuple(services.items())
        self._max_workers = max_workers

    def sync_characters(
        self,
        character_ids: Sequence[int],
        metadata: SsoMetadata,
        config: SsoConfig,
    ) -> CharacterSyncBatch:
        ordered_ids = tuple(character_ids)
        if any(character_id <= 0 for character_id in ordered_ids):
            raise ValueError("character IDs must be positive")
        if len(set(ordered_ids)) != len(ordered_ids):
            raise ValueError("character IDs must be unique")
        if not ordered_ids:
            return CharacterSyncBatch(())
        with ThreadPoolExecutor(
            max_workers=min(self._max_workers, len(ordered_ids)),
            thread_name_prefix="eve-dolphin-sync",
        ) as executor:
            futures = {
                character_id: executor.submit(self._sync_character, character_id, metadata, config)
                for character_id in ordered_ids
            }
            outcomes = tuple(futures[character_id].result() for character_id in ordered_ids)
        return CharacterSyncBatch(outcomes)

    def _sync_character(
        self,
        character_id: int,
        metadata: SsoMetadata,
        config: SsoConfig,
    ) -> CharacterSyncOutcome:
        succeeded: list[str] = []
        failures: list[ResourceSyncFailure] = []
        for resource, service in self._services:
            try:
                service.sync(character_id, metadata, config)
            except Exception as error:
                missing = getattr(error, "missing_scopes", ())
                missing_scopes = (
                    tuple(scope for scope in missing if isinstance(scope, str))
                    if isinstance(missing, (tuple, list, set, frozenset))
                    else ()
                )
                failures.append(ResourceSyncFailure(resource, type(error).__name__, missing_scopes))
            else:
                succeeded.append(resource)
        return CharacterSyncOutcome(character_id, tuple(succeeded), tuple(failures))
