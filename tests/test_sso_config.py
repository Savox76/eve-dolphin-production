from __future__ import annotations

import pytest

from eve_dolphin.sso.config import (
    DEFAULT_REDIRECT_URI,
    SsoConfig,
    SsoConfigurationError,
)


def test_sso_config_loads_public_client_values_from_environment() -> None:
    config = SsoConfig.from_environment({"EVE_SSO_CLIENT_ID": "public-client"})

    assert config.client_id == "public-client"
    assert config.redirect_uri == DEFAULT_REDIRECT_URI
    assert not hasattr(config, "client_secret")


def test_missing_client_id_is_rejected() -> None:
    with pytest.raises(SsoConfigurationError, match="client ID"):
        SsoConfig.from_environment({})


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "https://127.0.0.1:38636/callback",
        "http://localhost:38636/callback",
        "http://0.0.0.0:38636/callback",
        "http://127.0.0.1/callback",
        "http://127.0.0.1:38636/other",
        "http://127.0.0.1:38636/callback?code=stored",
    ],
)
def test_non_exact_loopback_redirect_is_rejected(redirect_uri: str) -> None:
    with pytest.raises(SsoConfigurationError, match="redirect URI"):
        SsoConfig(client_id="public-client", redirect_uri=redirect_uri)
