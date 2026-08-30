"""Small HTTP boundary that keeps SSO logic deterministic in tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

import httpx


class OAuthTokenRequestError(RuntimeError):
    """A token endpoint rejected a request without exposing sensitive payload data."""

    def __init__(
        self,
        error_code: str | None,
        status_code: int,
        *,
        retry_after: str | None = None,
    ) -> None:
        self.error_code = error_code
        self.status_code = status_code
        self.retry_after = retry_after
        detail = error_code or f"HTTP {status_code}"
        super().__init__(f"OAuth token request failed ({detail})")


class HttpTransport(Protocol):
    def get_json(self, url: str) -> dict[str, object]: ...

    def post_form(self, url: str, data: Mapping[str, str]) -> dict[str, object]: ...


class HttpxTransport:
    """Network transport with bounded timeouts and HTTP status validation."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._timeout_seconds = timeout_seconds

    def get_json(self, url: str) -> dict[str, object]:
        response = httpx.get(url, timeout=self._timeout_seconds, follow_redirects=False)
        response.raise_for_status()
        return _object_payload(response)

    def post_form(self, url: str, data: Mapping[str, str]) -> dict[str, object]:
        response = httpx.post(
            url,
            data=data,
            timeout=self._timeout_seconds,
            follow_redirects=False,
        )
        if response.is_error:
            raise OAuthTokenRequestError(
                _oauth_error_code(response),
                response.status_code,
                retry_after=response.headers.get("Retry-After"),
            )
        response.raise_for_status()
        return _object_payload(response)


def _object_payload(response: httpx.Response) -> dict[str, object]:
    payload = cast(object, response.json())
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise ValueError("HTTP response is not a JSON object")
    return cast(dict[str, object], payload)


def _oauth_error_code(response: httpx.Response) -> str | None:
    try:
        payload = cast(object, response.json())
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    error_code = payload.get("error")
    return error_code if isinstance(error_code, str) and error_code else None
