"""Cryptographic validation and character extraction for EVE access tokens."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, cast

import jwt
from jwt import InvalidTokenError, PyJWK

from eve_dolphin.sso.models import SsoMetadata, ValidatedCharacter
from eve_dolphin.sso.transport import HttpTransport, HttpxTransport

ALLOWED_ALGORITHM = "RS256"
EXPECTED_EVE_AUDIENCE = "EVE Online"
ACCEPTED_ISSUERS = (
    "https://login.eveonline.com/",
    "https://login.eveonline.com",
    "login.eveonline.com",
    "logineveonline.com",
)


class AccessTokenValidationError(ValueError):
    """An access token is invalid or belongs to another application."""


class AccessTokenValidator(Protocol):
    def validate(
        self,
        access_token: str,
        metadata: SsoMetadata,
        client_id: str,
    ) -> ValidatedCharacter: ...


class EveAccessTokenValidator:
    """Validate EVE's RSA signature and all security-relevant JWT claims."""

    def __init__(self, transport: HttpTransport | None = None) -> None:
        self._transport = transport or HttpxTransport()

    def validate(
        self,
        access_token: str,
        metadata: SsoMetadata,
        client_id: str,
    ) -> ValidatedCharacter:
        if not access_token or not client_id:
            raise AccessTokenValidationError("access token and client ID are required")
        if metadata.issuer not in ACCEPTED_ISSUERS:
            raise AccessTokenValidationError("SSO metadata uses an unexpected issuer")

        try:
            header = jwt.get_unverified_header(access_token)
            algorithm = header.get("alg")
            key_id = header.get("kid")
            if algorithm != ALLOWED_ALGORITHM or not isinstance(key_id, str) or not key_id:
                raise AccessTokenValidationError("access token uses an unsupported signing key")

            jwks = self._transport.get_json(metadata.jwks_uri)
            key_data = _select_signing_key(jwks, key_id)
            signing_key = PyJWK.from_dict(key_data, algorithm=ALLOWED_ALGORITHM).key
            claims = jwt.decode(
                access_token,
                key=signing_key,
                algorithms=[ALLOWED_ALGORITHM],
                audience=EXPECTED_EVE_AUDIENCE,
                issuer=ACCEPTED_ISSUERS,
                options={"require": ["exp", "iss", "aud", "sub", "name", "scp"]},
            )
            return _validated_character(cast(dict[str, object], claims), client_id)
        except AccessTokenValidationError:
            raise
        except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
            raise AccessTokenValidationError("EVE access token validation failed") from error


def _select_signing_key(jwks: dict[str, object], key_id: str) -> dict[str, object]:
    raw_keys = jwks.get("keys")
    if not isinstance(raw_keys, list):
        raise AccessTokenValidationError("JWKS response has no keys")
    matching_keys: list[dict[str, object]] = []
    for raw_key in raw_keys:
        if not isinstance(raw_key, dict):
            continue
        key = cast(dict[str, object], raw_key)
        if key.get("kid") == key_id and key.get("alg") in (None, ALLOWED_ALGORITHM):
            matching_keys.append(key)
    if len(matching_keys) != 1:
        raise AccessTokenValidationError("JWT signing key is missing or ambiguous")
    return matching_keys[0]


def _validated_character(claims: dict[str, object], client_id: str) -> ValidatedCharacter:
    audiences = _string_sequence(claims.get("aud"), "aud")
    if client_id not in audiences or EXPECTED_EVE_AUDIENCE not in audiences:
        raise AccessTokenValidationError("access token audience does not match this application")

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.startswith("CHARACTER:EVE:"):
        raise AccessTokenValidationError("access token subject is not an EVE character")
    try:
        character_id = int(subject.removeprefix("CHARACTER:EVE:"))
    except ValueError as error:
        raise AccessTokenValidationError("access token has an invalid character ID") from error
    if character_id <= 0:
        raise AccessTokenValidationError("access token has an invalid character ID")

    character_name = claims.get("name")
    if not isinstance(character_name, str) or not character_name.strip():
        raise AccessTokenValidationError("access token has no character name")
    scopes = _string_sequence(claims.get("scp"), "scp")
    owner = claims.get("owner")
    if owner is not None and not isinstance(owner, str):
        raise AccessTokenValidationError("access token has an invalid owner claim")

    return ValidatedCharacter(
        character_id=character_id,
        character_name=character_name,
        granted_scopes=tuple(dict.fromkeys(scopes)),
        owner_hash=owner,
    )


def _string_sequence(value: object, claim_name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise AccessTokenValidationError(f"access token {claim_name} claim must be an array")
    if not all(isinstance(item, str) and item for item in value):
        raise AccessTokenValidationError(f"access token {claim_name} claim contains invalid data")
    return tuple(cast(Sequence[str], value))
