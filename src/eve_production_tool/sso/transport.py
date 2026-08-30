"""Small HTTP boundary that keeps SSO logic deterministic in tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

import httpx


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
        response.raise_for_status()
        return _object_payload(response)


def _object_payload(response: httpx.Response) -> dict[str, object]:
    payload = cast(object, response.json())
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise ValueError("HTTP response is not a JSON object")
    return cast(dict[str, object], payload)
