"""EVE SSO metadata, authorization URL and PKCE token exchange client."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlencode

from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import (
    AuthorizationRequest,
    SsoMetadata,
    TokenResponse,
)
from eve_dolphin.sso.pkce import generate_pkce_pair, generate_state
from eve_dolphin.sso.transport import HttpTransport, HttpxTransport

METADATA_URL = "https://login.eveonline.com/.well-known/oauth-authorization-server"


class EveSsoClient:
    """Perform the public-client portions of EVE's Authorization Code flow."""

    def __init__(self, transport: HttpTransport | None = None) -> None:
        self._transport = transport or HttpxTransport()

    def fetch_metadata(self) -> SsoMetadata:
        return SsoMetadata.from_mapping(self._transport.get_json(METADATA_URL))

    def create_authorization_request(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        scopes: Sequence[str] = (),
    ) -> AuthorizationRequest:
        normalized_scopes = _normalize_scopes(scopes)
        pkce = generate_pkce_pair()
        state = generate_state()
        query = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "scope": " ".join(normalized_scopes),
            "state": state,
            "code_challenge": pkce.challenge,
            "code_challenge_method": "S256",
        }
        return AuthorizationRequest(
            url=f"{metadata.authorization_endpoint}?{urlencode(query)}",
            state=state,
            code_verifier=pkce.verifier,
        )

    def exchange_authorization_code(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        authorization_code: str,
        code_verifier: str,
    ) -> TokenResponse:
        if not authorization_code or not code_verifier:
            raise ValueError("authorization code and PKCE verifier are required")
        payload = self._transport.post_form(
            metadata.token_endpoint,
            {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "client_id": config.client_id,
                "code_verifier": code_verifier,
                "redirect_uri": config.redirect_uri,
            },
        )
        return TokenResponse.from_mapping(payload)


def _normalize_scopes(scopes: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(scope.strip() for scope in scopes if scope.strip()))
    if any(any(character.isspace() for character in scope) for scope in normalized):
        raise ValueError("each EVE SSO scope must be a single value")
    return normalized
