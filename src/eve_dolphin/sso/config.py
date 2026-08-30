"""Configuration and loopback redirect validation for EVE SSO."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_REDIRECT_URI = "http://127.0.0.1:38636/callback"
CLIENT_ID_ENVIRONMENT_VARIABLE = "EVE_SSO_CLIENT_ID"
REDIRECT_URI_ENVIRONMENT_VARIABLE = "EVE_SSO_REDIRECT_URI"


class SsoConfigurationError(ValueError):
    """The public SSO client configuration is absent or unsafe."""


@dataclass(frozen=True, slots=True)
class SsoConfig:
    """Public desktop OAuth configuration; deliberately contains no client secret."""

    client_id: str
    redirect_uri: str = DEFAULT_REDIRECT_URI

    def __post_init__(self) -> None:
        if not self.client_id.strip():
            raise SsoConfigurationError("EVE SSO client ID is required")
        validate_loopback_redirect_uri(self.redirect_uri)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> SsoConfig:
        values = os.environ if environment is None else environment
        return cls(
            client_id=values.get(CLIENT_ID_ENVIRONMENT_VARIABLE, ""),
            redirect_uri=values.get(REDIRECT_URI_ENVIRONMENT_VARIABLE, DEFAULT_REDIRECT_URI),
        )


def validate_loopback_redirect_uri(redirect_uri: str) -> None:
    """Allow only a fixed HTTP callback on the IPv4 loopback interface."""

    parsed = urlsplit(redirect_uri)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        raise SsoConfigurationError("redirect URI must use http://127.0.0.1")
    if parsed.username is not None or parsed.password is not None:
        raise SsoConfigurationError("redirect URI must not contain user information")
    try:
        port = parsed.port
    except ValueError as error:
        raise SsoConfigurationError("redirect URI contains an invalid port") from error
    if port is None or not 1 <= port <= 65535:
        raise SsoConfigurationError("redirect URI must contain a fixed TCP port")
    if parsed.path != "/callback":
        raise SsoConfigurationError("redirect URI path must be /callback")
    if parsed.query or parsed.fragment:
        raise SsoConfigurationError("redirect URI must not contain query or fragment data")
