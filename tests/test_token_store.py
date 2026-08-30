from __future__ import annotations

import pytest

from eve_production_tool.security.token_store import SERVICE_NAME, KeyringTokenStore


class FakeCredentialBackend:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.values.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.values[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        self.values.pop((service_name, username), None)


def test_refresh_tokens_are_isolated_by_character() -> None:
    backend = FakeCredentialBackend()
    store = KeyringTokenStore(backend)

    store.set_refresh_token(1001, "token-a")
    store.set_refresh_token(1002, "token-b")

    assert store.get_refresh_token(1001) == "token-a"
    assert store.get_refresh_token(1002) == "token-b"
    assert (SERVICE_NAME, "eve-character:1001:refresh-token") in backend.values

    store.delete_refresh_token(1001)

    assert store.get_refresh_token(1001) is None
    assert store.get_refresh_token(1002) == "token-b"


@pytest.mark.parametrize("character_id", [0, -1])
def test_invalid_character_ids_are_rejected(character_id: int) -> None:
    store = KeyringTokenStore(FakeCredentialBackend())

    with pytest.raises(ValueError, match="character_id"):
        store.get_refresh_token(character_id)


def test_empty_refresh_token_is_rejected() -> None:
    store = KeyringTokenStore(FakeCredentialBackend())

    with pytest.raises(ValueError, match="refresh_token"):
        store.set_refresh_token(1001, "")
