from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import cast

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from eve_dolphin.sso.models import SsoMetadata
from eve_dolphin.sso.validation import (
    AccessTokenValidationError,
    EveAccessTokenValidator,
)

CLIENT_ID = "public-client"
KEY_ID = "test-signing-key"


class JwksTransport:
    def __init__(self, jwks: dict[str, object]) -> None:
        self.jwks = jwks

    def get_json(self, url: str) -> dict[str, object]:
        assert url == "https://login.eveonline.com/oauth/jwks"
        return self.jwks

    def post_form(self, url: str, data: Mapping[str, str]) -> dict[str, object]:
        raise AssertionError("JWT validation must not post data")


def test_access_token_signature_and_character_claims_are_validated() -> None:
    private_key, jwks = _signing_material()
    token = _encode_token(private_key)
    validator = EveAccessTokenValidator(JwksTransport(jwks))

    character = validator.validate(token, _metadata(), CLIENT_ID)

    assert character.character_id == 2112345678
    assert character.character_name == "Industrial Pilot"
    assert character.owner_hash == "owner-hash"
    assert character.granted_scopes == (
        "esi-assets.read_assets.v1",
        "esi-planets.manage_planets.v1",
    )


def test_access_token_for_another_client_is_rejected() -> None:
    private_key, jwks = _signing_material()
    token = _encode_token(private_key, audiences=["different-client", "EVE Online"])

    with pytest.raises(AccessTokenValidationError, match="audience"):
        EveAccessTokenValidator(JwksTransport(jwks)).validate(token, _metadata(), CLIENT_ID)


def test_access_token_with_unknown_signing_key_is_rejected() -> None:
    private_key, jwks = _signing_material()
    token = _encode_token(private_key, key_id="unknown")

    with pytest.raises(AccessTokenValidationError, match="signing key"):
        EveAccessTokenValidator(JwksTransport(jwks)).validate(token, _metadata(), CLIENT_ID)


def test_metadata_with_unexpected_issuer_is_rejected_before_key_fetch() -> None:
    private_key, jwks = _signing_material()
    token = _encode_token(private_key)
    metadata = _metadata()
    unexpected_metadata = SsoMetadata(
        issuer="https://attacker.invalid/",
        authorization_endpoint=metadata.authorization_endpoint,
        token_endpoint=metadata.token_endpoint,
        jwks_uri=metadata.jwks_uri,
    )

    with pytest.raises(AccessTokenValidationError, match="metadata"):
        EveAccessTokenValidator(JwksTransport(jwks)).validate(token, unexpected_metadata, CLIENT_ID)


def _signing_material() -> tuple[rsa.RSAPrivateKey, dict[str, object]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    assert isinstance(public_jwk, dict)
    public_jwk.update({"kid": KEY_ID, "alg": "RS256", "use": "sig"})
    return private_key, {"keys": [cast(dict[str, object], public_jwk)]}


def _encode_token(
    private_key: rsa.RSAPrivateKey,
    audiences: list[str] | None = None,
    key_id: str = KEY_ID,
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": "https://login.eveonline.com/",
            "aud": audiences or [CLIENT_ID, "EVE Online"],
            "sub": "CHARACTER:EVE:2112345678",
            "name": "Industrial Pilot",
            "owner": "owner-hash",
            "scp": ["esi-assets.read_assets.v1", "esi-planets.manage_planets.v1"],
            "iat": now,
            "exp": now + timedelta(minutes=20),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": key_id},
    )


def _metadata() -> SsoMetadata:
    return SsoMetadata(
        issuer="https://login.eveonline.com/",
        authorization_endpoint="https://login.eveonline.com/v2/oauth/authorize",
        token_endpoint="https://login.eveonline.com/v2/oauth/token",
        jwks_uri="https://login.eveonline.com/oauth/jwks",
    )
