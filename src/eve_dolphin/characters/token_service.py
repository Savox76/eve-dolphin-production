"""Short-lived access token renewal with safe refresh-token rotation."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol

from eve_dolphin.characters.models import AuthorizationStatus
from eve_dolphin.characters.repository import CharacterAuthorizationRepository
from eve_dolphin.security import TokenStore
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import SsoMetadata, TokenResponse
from eve_dolphin.sso.transport import OAuthTokenRequestError
from eve_dolphin.sso.validation import AccessTokenValidator


class CharacterNotLinkedError(LookupError):
    """The requested character has no local record."""


class CharacterReauthorizationRequired(RuntimeError):
    """The character must grant EVE Dolphin access again in the browser."""


class RefreshedIdentityMismatchError(RuntimeError):
    """A refreshed token belongs to a different EVE character or owner."""


class RefreshTokenClient(Protocol):
    def refresh_access_token(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        refresh_token: str,
    ) -> TokenResponse: ...


@dataclass(frozen=True, slots=True)
class CharacterAccessToken:
    character_id: int
    access_token: str
    expires_at: datetime
    granted_scopes: tuple[str, ...]


class CharacterTokenService:
    """Renew access without ever persisting the resulting access token."""

    def __init__(
        self,
        repository: CharacterAuthorizationRepository,
        token_store: TokenStore,
        sso_client: RefreshTokenClient,
        token_validator: AccessTokenValidator,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._token_store = token_store
        self._sso_client = sso_client
        self._token_validator = token_validator
        self._clock = clock or (lambda: datetime.now(UTC))
        self._locks_guard = Lock()
        self._character_locks: dict[int, Lock] = {}

    def refresh(
        self,
        character_id: int,
        metadata: SsoMetadata,
        config: SsoConfig,
    ) -> CharacterAccessToken:
        with self._lock_for(character_id):
            return self._refresh_locked(character_id, metadata, config)

    def _refresh_locked(
        self,
        character_id: int,
        metadata: SsoMetadata,
        config: SsoConfig,
    ) -> CharacterAccessToken:
        character = self._repository.get(character_id)
        if character is None:
            raise CharacterNotLinkedError(f"character {character_id} is not linked")
        if character.authorization_status is AuthorizationStatus.REAUTHORIZATION_REQUIRED:
            raise CharacterReauthorizationRequired(
                f"character {character_id} requires reauthorization"
            )

        refresh_token = self._token_store.get_refresh_token(character_id)
        if refresh_token is None:
            self._mark_reauthorization_required(character_id, delete_token=False)
            raise CharacterReauthorizationRequired(f"character {character_id} has no refresh token")

        try:
            response = self._sso_client.refresh_access_token(
                metadata,
                config,
                refresh_token,
            )
        except OAuthTokenRequestError as error:
            if error.error_code == "invalid_grant":
                self._mark_reauthorization_required(character_id, delete_token=True)
                raise CharacterReauthorizationRequired(
                    f"character {character_id} access was revoked"
                ) from error
            raise

        identity = self._token_validator.validate(
            response.access_token,
            metadata,
            config.client_id,
        )
        if identity.character_id != character_id or _owner_changed(
            character.owner_hash, identity.owner_hash
        ):
            self._mark_reauthorization_required(character_id, delete_token=True)
            raise RefreshedIdentityMismatchError(
                "refreshed access token does not match the linked character"
            )

        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")

        # EVE may rotate refresh tokens. Persist the returned value before any
        # non-essential SQLite metadata update; the previous token may already be invalid.
        try:
            self._token_store.set_refresh_token(character_id, response.refresh_token)
        except Exception:
            # A rotated token that cannot be saved may make the previous token unusable.
            # Stop future refresh attempts until the player authorizes the character again.
            self._repository.mark_reauthorization_required(character_id, now)
            raise
        self._repository.upsert(
            replace(
                character,
                character_name=identity.character_name,
                owner_hash=identity.owner_hash or character.owner_hash,
                granted_scopes=identity.granted_scopes,
                authorization_status=AuthorizationStatus.ACTIVE,
                authorization_error_at=None,
            )
        )
        return CharacterAccessToken(
            character_id=character_id,
            access_token=response.access_token,
            expires_at=now + timedelta(seconds=response.expires_in),
            granted_scopes=identity.granted_scopes,
        )

    def _mark_reauthorization_required(self, character_id: int, *, delete_token: bool) -> None:
        failed_at = self._clock()
        if failed_at.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        if not self._repository.mark_reauthorization_required(character_id, failed_at):
            raise CharacterNotLinkedError(f"character {character_id} is not linked")
        if delete_token:
            self._token_store.delete_refresh_token(character_id)

    def _lock_for(self, character_id: int) -> Lock:
        with self._locks_guard:
            return self._character_locks.setdefault(character_id, Lock())


def _owner_changed(existing_owner: str | None, refreshed_owner: str | None) -> bool:
    if existing_owner is None or refreshed_owner is None:
        return False
    return not secrets.compare_digest(existing_owner, refreshed_owner)
