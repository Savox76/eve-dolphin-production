"""Typed values passed through the EVE SSO workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self


class SsoResponseError(ValueError):
    """EVE SSO returned a structurally invalid response."""


@dataclass(frozen=True, slots=True)
class PkcePair:
    verifier: str
    challenge: str


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    url: str
    state: str
    code_verifier: str


@dataclass(frozen=True, slots=True)
class SsoMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        return cls(
            issuer=_required_https_url(payload, "issuer"),
            authorization_endpoint=_required_https_url(payload, "authorization_endpoint"),
            token_endpoint=_required_https_url(payload, "token_endpoint"),
            jwks_uri=_required_https_url(payload, "jwks_uri"),
        )


@dataclass(frozen=True, slots=True)
class TokenResponse:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        expires_in = payload.get("expires_in")
        if not isinstance(expires_in, int) or isinstance(expires_in, bool) or expires_in <= 0:
            raise SsoResponseError("token response has no valid expires_in value")
        token_type = _required_string(payload, "token_type")
        if token_type.casefold() != "bearer":
            raise SsoResponseError("token response uses an unsupported token type")
        return cls(
            access_token=_required_string(payload, "access_token"),
            refresh_token=_required_string(payload, "refresh_token"),
            token_type=token_type,
            expires_in=expires_in,
        )


@dataclass(frozen=True, slots=True)
class ValidatedCharacter:
    character_id: int
    character_name: str
    granted_scopes: tuple[str, ...]
    owner_hash: str | None = None


@dataclass(frozen=True, slots=True)
class CallbackResult:
    state: str
    code: str | None = None
    error: str | None = None
    error_description: str | None = None


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise SsoResponseError(f"SSO response has no valid {key} value")
    return value


def _required_https_url(payload: dict[str, object], key: str) -> str:
    value = _required_string(payload, key)
    if not value.startswith("https://"):
        raise SsoResponseError(f"SSO metadata {key} must use HTTPS")
    return value
