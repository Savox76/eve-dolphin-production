from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import parse_qs, urlsplit

from eve_dolphin.sso.client import METADATA_URL, EveSsoClient
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import SsoMetadata


class FakeTransport:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, str]]] = []

    def get_json(self, url: str) -> dict[str, object]:
        assert url == METADATA_URL
        return {
            "issuer": "https://login.eveonline.com/",
            "authorization_endpoint": "https://login.eveonline.com/v2/oauth/authorize",
            "token_endpoint": "https://login.eveonline.com/v2/oauth/token",
            "jwks_uri": "https://login.eveonline.com/oauth/jwks",
        }

    def post_form(self, url: str, data: Mapping[str, str]) -> dict[str, object]:
        self.posts.append((url, dict(data)))
        return {
            "access_token": "signed-access-token",
            "refresh_token": "private-refresh-token",
            "token_type": "Bearer",
            "expires_in": 1199,
        }


def test_metadata_drives_authorization_request_without_client_secret() -> None:
    transport = FakeTransport()
    client = EveSsoClient(transport)
    config = SsoConfig(client_id="public-client")

    metadata = client.fetch_metadata()
    request = client.create_authorization_request(
        metadata,
        config,
        ["esi-assets.read_assets.v1", "esi-assets.read_assets.v1"],
    )

    parsed = urlsplit(request.url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == metadata.authorization_endpoint
    assert query == {
        "response_type": ["code"],
        "client_id": ["public-client"],
        "redirect_uri": [config.redirect_uri],
        "scope": ["esi-assets.read_assets.v1"],
        "state": [request.state],
        "code_challenge": [query["code_challenge"][0]],
        "code_challenge_method": ["S256"],
    }
    assert "client_secret" not in query
    assert len(request.code_verifier) == 43


def test_pkce_code_exchange_posts_only_public_client_fields() -> None:
    transport = FakeTransport()
    client = EveSsoClient(transport)
    metadata = SsoMetadata.from_mapping(transport.get_json(METADATA_URL))
    config = SsoConfig(client_id="public-client")

    response = client.exchange_authorization_code(metadata, config, "one-time-code", "verifier")

    assert response.refresh_token == "private-refresh-token"
    assert transport.posts == [
        (
            metadata.token_endpoint,
            {
                "grant_type": "authorization_code",
                "code": "one-time-code",
                "client_id": "public-client",
                "code_verifier": "verifier",
            },
        )
    ]
    assert "client_secret" not in transport.posts[0][1]


def test_refresh_posts_rotatable_token_without_client_secret() -> None:
    transport = FakeTransport()
    client = EveSsoClient(transport)
    metadata = SsoMetadata.from_mapping(transport.get_json(METADATA_URL))
    config = SsoConfig(client_id="public-client")

    response = client.refresh_access_token(metadata, config, "current-refresh-token")

    assert response.refresh_token == "private-refresh-token"
    assert transport.posts == [
        (
            metadata.token_endpoint,
            {
                "grant_type": "refresh_token",
                "refresh_token": "current-refresh-token",
                "client_id": "public-client",
            },
        )
    ]
    assert "client_secret" not in transport.posts[0][1]
