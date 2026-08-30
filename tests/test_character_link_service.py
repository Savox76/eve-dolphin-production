from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eve_production_tool.characters.models import EveCharacter
from eve_production_tool.characters.service import CharacterLinkService, SsoAuthorizationError
from eve_production_tool.security import TokenStore
from eve_production_tool.sso.config import SsoConfig
from eve_production_tool.sso.models import (
    AuthorizationRequest,
    CallbackResult,
    SsoMetadata,
    TokenResponse,
    ValidatedCharacter,
)


class FakeRepository:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.characters: dict[int, EveCharacter] = {}

    def upsert(self, character: EveCharacter) -> None:
        if self.fail:
            raise RuntimeError("database unavailable")
        self.characters[character.character_id] = character

    def remove(self, character_id: int) -> bool:
        return self.characters.pop(character_id, None) is not None


class FakeTokenStore(TokenStore):
    def __init__(self) -> None:
        self.tokens: dict[int, str] = {}

    def get_refresh_token(self, character_id: int) -> str | None:
        return self.tokens.get(character_id)

    def set_refresh_token(self, character_id: int, refresh_token: str) -> None:
        self.tokens[character_id] = refresh_token

    def delete_refresh_token(self, character_id: int) -> None:
        self.tokens.pop(character_id, None)


class FakeSsoClient:
    def exchange_authorization_code(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        authorization_code: str,
        code_verifier: str,
    ) -> TokenResponse:
        assert authorization_code == "code"
        assert code_verifier == "verifier"
        return TokenResponse("signed-access", "new-refresh", "Bearer", 1200)


class FakeValidator:
    def validate(
        self,
        access_token: str,
        metadata: SsoMetadata,
        client_id: str,
    ) -> ValidatedCharacter:
        assert access_token == "signed-access"
        assert client_id == "public-client"
        return ValidatedCharacter(1001, "Industrial Pilot", ("scope-a",), "owner")


def test_validated_character_and_refresh_token_are_linked() -> None:
    repository = FakeRepository()
    token_store = FakeTokenStore()
    service = _service(repository, token_store)

    character = service.complete_link(_metadata(), _config(), _request(), _callback())

    assert repository.characters == {1001: character}
    assert token_store.tokens == {1001: "new-refresh"}
    assert character.linked_at == datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def test_database_failure_restores_existing_refresh_token() -> None:
    repository = FakeRepository(fail=True)
    token_store = FakeTokenStore()
    token_store.tokens[1001] = "existing-refresh"
    service = _service(repository, token_store)

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.complete_link(_metadata(), _config(), _request(), _callback())

    assert token_store.tokens == {1001: "existing-refresh"}


def test_wrong_state_stops_before_token_exchange() -> None:
    service = _service(FakeRepository(), FakeTokenStore())

    with pytest.raises(SsoAuthorizationError, match="state"):
        service.complete_link(
            _metadata(),
            _config(),
            _request(),
            CallbackResult(state="wrong", code="code"),
        )


def _service(repository: FakeRepository, token_store: FakeTokenStore) -> CharacterLinkService:
    return CharacterLinkService(
        repository,
        token_store,
        FakeSsoClient(),
        FakeValidator(),
        clock=lambda: datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
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


def _request() -> AuthorizationRequest:
    return AuthorizationRequest("https://example.invalid", "state", "verifier")


def _callback() -> CallbackResult:
    return CallbackResult(state="state", code="code")
