from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from eve_dolphin.characters.models import AuthorizationStatus, EveCharacter
from eve_dolphin.characters.token_service import (
    CharacterReauthorizationRequired,
    CharacterTokenService,
    RefreshedIdentityMismatchError,
)
from eve_dolphin.security import TokenStore
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import SsoMetadata, TokenResponse, ValidatedCharacter
from eve_dolphin.sso.transport import OAuthTokenRequestError

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class FakeRepository:
    def __init__(self, character: EveCharacter, *, fail_upsert: bool = False) -> None:
        self.character = character
        self.fail_upsert = fail_upsert

    def get(self, character_id: int) -> EveCharacter | None:
        return self.character if self.character.character_id == character_id else None

    def upsert(self, character: EveCharacter) -> None:
        if self.fail_upsert:
            raise RuntimeError("database unavailable")
        self.character = character

    def mark_reauthorization_required(self, character_id: int, failed_at: datetime) -> bool:
        if self.character.character_id != character_id:
            return False
        self.character = replace(
            self.character,
            authorization_status=AuthorizationStatus.REAUTHORIZATION_REQUIRED,
            authorization_error_at=failed_at,
        )
        return True


class FakeTokenStore(TokenStore):
    def __init__(
        self,
        refresh_token: str | None = "current-refresh",
        *,
        fail_set: bool = False,
    ) -> None:
        self.refresh_token = refresh_token
        self.fail_set = fail_set

    def get_refresh_token(self, character_id: int) -> str | None:
        return self.refresh_token

    def set_refresh_token(self, character_id: int, refresh_token: str) -> None:
        if self.fail_set:
            raise RuntimeError("credential store unavailable")
        self.refresh_token = refresh_token

    def delete_refresh_token(self, character_id: int) -> None:
        self.refresh_token = None


class FakeSsoClient:
    def __init__(self, error: OAuthTokenRequestError | None = None) -> None:
        self.error = error
        self.calls = 0

    def refresh_access_token(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        refresh_token: str,
    ) -> TokenResponse:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert refresh_token == "current-refresh"
        return TokenResponse("signed-access", "rotated-refresh", "Bearer", 1200)


class FakeValidator:
    def __init__(self, character_id: int = 1001, owner_hash: str = "owner") -> None:
        self.character_id = character_id
        self.owner_hash = owner_hash

    def validate(
        self,
        access_token: str,
        metadata: SsoMetadata,
        client_id: str,
    ) -> ValidatedCharacter:
        assert access_token == "signed-access"
        return ValidatedCharacter(
            self.character_id,
            "Industrial Pilot Renamed",
            ("esi-assets.read_assets.v1",),
            self.owner_hash,
        )


def test_refresh_rotates_token_and_returns_only_short_lived_access() -> None:
    repository = FakeRepository(_character())
    token_store = FakeTokenStore()
    service = _service(repository, token_store)

    access = service.refresh(1001, _metadata(), _config())

    assert token_store.refresh_token == "rotated-refresh"
    assert access.access_token == "signed-access"
    assert access.expires_at == datetime(2026, 8, 30, 12, 20, tzinfo=UTC)
    assert repository.character.character_name == "Industrial Pilot Renamed"
    assert repository.character.granted_scopes == ("esi-assets.read_assets.v1",)
    assert repository.character.authorization_status is AuthorizationStatus.ACTIVE


def test_rotated_token_is_kept_if_metadata_update_fails() -> None:
    repository = FakeRepository(_character(), fail_upsert=True)
    token_store = FakeTokenStore()
    service = _service(repository, token_store)

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.refresh(1001, _metadata(), _config())

    assert token_store.refresh_token == "rotated-refresh"


def test_failed_rotated_token_storage_stops_future_refresh_attempts() -> None:
    repository = FakeRepository(_character())
    token_store = FakeTokenStore(fail_set=True)
    service = _service(repository, token_store)

    with pytest.raises(RuntimeError, match="credential store unavailable"):
        service.refresh(1001, _metadata(), _config())

    assert token_store.refresh_token == "current-refresh"
    assert repository.character.authorization_status is AuthorizationStatus.REAUTHORIZATION_REQUIRED


def test_invalid_grant_removes_token_and_requires_new_authorization() -> None:
    repository = FakeRepository(_character())
    token_store = FakeTokenStore()
    client = FakeSsoClient(OAuthTokenRequestError("invalid_grant", 400))
    service = _service(repository, token_store, client=client)

    with pytest.raises(CharacterReauthorizationRequired, match="revoked"):
        service.refresh(1001, _metadata(), _config())

    assert token_store.refresh_token is None
    assert repository.character.authorization_status is AuthorizationStatus.REAUTHORIZATION_REQUIRED
    assert repository.character.authorization_error_at == NOW

    with pytest.raises(CharacterReauthorizationRequired, match="requires reauthorization"):
        service.refresh(1001, _metadata(), _config())
    assert client.calls == 1


def test_temporary_oauth_error_preserves_refresh_token() -> None:
    repository = FakeRepository(_character())
    token_store = FakeTokenStore()
    error = OAuthTokenRequestError("temporarily_unavailable", 429, retry_after="60")
    service = _service(repository, token_store, client=FakeSsoClient(error))

    with pytest.raises(OAuthTokenRequestError) as caught:
        service.refresh(1001, _metadata(), _config())

    assert caught.value.retry_after == "60"
    assert token_store.refresh_token == "current-refresh"
    assert repository.character.authorization_status is AuthorizationStatus.ACTIVE


def test_missing_token_marks_character_for_reauthorization() -> None:
    repository = FakeRepository(_character())
    service = _service(repository, FakeTokenStore(None))

    with pytest.raises(CharacterReauthorizationRequired, match="no refresh token"):
        service.refresh(1001, _metadata(), _config())

    assert repository.character.authorization_status is AuthorizationStatus.REAUTHORIZATION_REQUIRED


def test_refreshed_identity_mismatch_is_never_rotated_into_character() -> None:
    repository = FakeRepository(_character())
    token_store = FakeTokenStore()
    service = _service(repository, token_store, validator=FakeValidator(character_id=2002))

    with pytest.raises(RefreshedIdentityMismatchError, match="does not match"):
        service.refresh(1001, _metadata(), _config())

    assert token_store.refresh_token is None
    assert repository.character.authorization_status is AuthorizationStatus.REAUTHORIZATION_REQUIRED


def _service(
    repository: FakeRepository,
    token_store: FakeTokenStore,
    *,
    client: FakeSsoClient | None = None,
    validator: FakeValidator | None = None,
) -> CharacterTokenService:
    return CharacterTokenService(
        repository,
        token_store,
        client or FakeSsoClient(),
        validator or FakeValidator(),
        clock=lambda: NOW,
    )


def _character() -> EveCharacter:
    return EveCharacter(
        1001,
        "Industrial Pilot",
        "owner",
        (),
        datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
    )


def _config() -> SsoConfig:
    return SsoConfig(client_id="public-client")


def _metadata() -> SsoMetadata:
    return SsoMetadata(
        issuer="https://login.eveonline.com/",
        authorization_endpoint="https://login.eveonline.com/v2/oauth/authorize",
        token_endpoint="https://login.eveonline.com/v2/oauth/token",
        jwks_uri="https://login.eveonline.com/oauth/jwks",
    )
