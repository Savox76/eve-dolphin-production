"""Secure handoff from validated SSO responses to local character storage."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from eve_dolphin.characters.models import EveCharacter
from eve_dolphin.characters.repository import CharacterWriter
from eve_dolphin.security import TokenStore
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import (
    AuthorizationRequest,
    CallbackResult,
    SsoMetadata,
    TokenResponse,
)
from eve_dolphin.sso.validation import AccessTokenValidator


class SsoAuthorizationError(ValueError):
    """The browser authorization was rejected or was not correlated safely."""


class UnexpectedCharacterError(SsoAuthorizationError):
    """A permission upgrade selected a character other than the requested one."""


class AuthorizationCodeExchanger(Protocol):
    def exchange_authorization_code(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        authorization_code: str,
        code_verifier: str,
    ) -> TokenResponse: ...


class CharacterLinkService:
    """Link and unlink characters while keeping refresh tokens out of SQLite."""

    def __init__(
        self,
        repository: CharacterWriter,
        token_store: TokenStore,
        sso_client: AuthorizationCodeExchanger,
        token_validator: AccessTokenValidator,
        clock: Callable[[], datetime] | None = None,
        expected_character_id: int | None = None,
    ) -> None:
        if expected_character_id is not None and expected_character_id <= 0:
            raise ValueError("expected_character_id must be positive")
        self._repository = repository
        self._token_store = token_store
        self._sso_client = sso_client
        self._token_validator = token_validator
        self._clock = clock or (lambda: datetime.now(UTC))
        self._expected_character_id = expected_character_id

    def complete_link(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        request: AuthorizationRequest,
        callback: CallbackResult,
    ) -> EveCharacter:
        if not secrets.compare_digest(request.state, callback.state):
            raise SsoAuthorizationError("EVE SSO callback state does not match")
        if callback.error is not None:
            raise SsoAuthorizationError("EVE SSO authorization was not completed")
        if callback.code is None:
            raise SsoAuthorizationError("EVE SSO callback contains no authorization code")

        token_response = self._sso_client.exchange_authorization_code(
            metadata,
            config,
            callback.code,
            request.code_verifier,
        )
        identity = self._token_validator.validate(
            token_response.access_token,
            metadata,
            config.client_id,
        )
        if (
            self._expected_character_id is not None
            and identity.character_id != self._expected_character_id
        ):
            raise UnexpectedCharacterError(
                "EVE SSO returned a different character than the one being reauthorized"
            )
        character = EveCharacter(
            character_id=identity.character_id,
            character_name=identity.character_name,
            owner_hash=identity.owner_hash,
            granted_scopes=identity.granted_scopes,
            linked_at=self._clock(),
        )

        previous_token = self._token_store.get_refresh_token(character.character_id)
        self._token_store.set_refresh_token(character.character_id, token_response.refresh_token)
        try:
            self._repository.upsert(character)
        except Exception:
            if previous_token is None:
                self._token_store.delete_refresh_token(character.character_id)
            else:
                self._token_store.set_refresh_token(character.character_id, previous_token)
            raise
        return character

    def unlink(self, character_id: int) -> bool:
        self._token_store.delete_refresh_token(character_id)
        return self._repository.remove(character_id)
