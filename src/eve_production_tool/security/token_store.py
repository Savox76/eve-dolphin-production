"""Refresh-token storage isolated from SQLite and application exports."""

from __future__ import annotations

from typing import Protocol

import keyring
from keyring.errors import PasswordDeleteError

SERVICE_NAME = "EVE Production Tool"


class CredentialBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


class TokenStore(Protocol):
    """Minimal interface needed by the later EVE SSO implementation."""

    def get_refresh_token(self, character_id: int) -> str | None: ...

    def set_refresh_token(self, character_id: int, refresh_token: str) -> None: ...

    def delete_refresh_token(self, character_id: int) -> None: ...


class KeyringTokenStore:
    """Store one refresh token per character in the operating-system keyring."""

    def __init__(self, backend: CredentialBackend = keyring) -> None:
        self._backend = backend

    def get_refresh_token(self, character_id: int) -> str | None:
        return self._backend.get_password(SERVICE_NAME, self._credential_name(character_id))

    def set_refresh_token(self, character_id: int, refresh_token: str) -> None:
        if not refresh_token:
            raise ValueError("refresh_token must not be empty")
        self._backend.set_password(
            SERVICE_NAME,
            self._credential_name(character_id),
            refresh_token,
        )

    def delete_refresh_token(self, character_id: int) -> None:
        try:
            self._backend.delete_password(SERVICE_NAME, self._credential_name(character_id))
        except PasswordDeleteError:
            return

    @staticmethod
    def _credential_name(character_id: int) -> str:
        if character_id <= 0:
            raise ValueError("character_id must be positive")
        return f"eve-character:{character_id}:refresh-token"
