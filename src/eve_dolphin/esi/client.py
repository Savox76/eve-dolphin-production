"""Cache-aware, bounded and rate-limit-aware EVE ESI HTTP client."""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
from threading import RLock
from typing import cast
from urllib.parse import urlencode

import httpx

from eve_dolphin import __version__
from eve_dolphin.esi.cache import EsiMemoryCache
from eve_dolphin.esi.errors import (
    EsiHttpError,
    EsiProtocolError,
    EsiRateLimitError,
    EsiTransportError,
)
from eve_dolphin.esi.models import EsiCacheEntry, EsiResponse

ESI_BASE_URL = "https://esi.evetech.net"
ESI_COMPATIBILITY_DATE = "2026-08-30"
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
MAX_RETRIES = 2
ERROR_LIMIT_FLOOR = 5
BUCKET_REMAINING_FLOOR = 2
RETRYABLE_STATUSES = frozenset({420, 429, 502, 503, 504})


class EveEsiClient:
    """Perform ESI GET requests without violating cache or rate-limit boundaries."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        cache: EsiMemoryCache | None = None,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._client = client or httpx.Client(
            base_url=ESI_BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=False,
            headers={"User-Agent": f"EVE-Dolphin/{__version__} (local desktop client)"},
        )
        self._owns_client = client is None
        self._cache = cache or EsiMemoryCache()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleeper = sleeper or time.sleep
        self._blocked_until: datetime | None = None
        self._limit_lock = RLock()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str | int | bool] | None = None,
        access_token: str | None = None,
        character_id: int | None = None,
    ) -> EsiResponse:
        _validate_request(path, access_token, character_id)
        now = self._now()
        self._enforce_gate(now)
        cache_key = _cache_key(path, params, character_id)
        cached = self._cache.get(cache_key)
        if cached is not None and cached.expires_at is not None and now < cached.expires_at:
            return _cached_response(cached, not_modified=False)

        headers = {"X-Compatibility-Date": ESI_COMPATIBILITY_DATE}
        if access_token is not None:
            headers["Authorization"] = f"Bearer {access_token}"
        if cached is not None:
            if cached.etag:
                headers["If-None-Match"] = cached.etag
            if cached.last_modified:
                headers["If-Modified-Since"] = cached.last_modified

        response = self._request_with_retries(path, params, headers)
        received_at = self._now()
        self._observe_limits(response, received_at)
        if response.status_code == 304:
            if cached is None:
                raise EsiProtocolError("ESI returned 304 without a cached representation")
            refreshed = EsiCacheEntry(
                payload=cached.payload,
                etag=response.headers.get("ETag", cached.etag),
                last_modified=response.headers.get("Last-Modified", cached.last_modified),
                expires_at=_http_date(response.headers.get("Expires")),
                received_at=received_at,
                pages=_positive_header(response.headers.get("X-Pages")) or cached.pages,
            )
            self._cache.put(cache_key, refreshed)
            return _cached_response(refreshed, not_modified=True)
        if not 200 <= response.status_code < 300:
            raise EsiHttpError(response.status_code, _error_message(response))
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise EsiProtocolError("ESI response exceeds the size limit")
        try:
            payload = cast(object, json.loads(response.content, parse_float=Decimal))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise EsiProtocolError("ESI response is not valid JSON") from error
        entry = EsiCacheEntry(
            payload=payload,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
            expires_at=_http_date(response.headers.get("Expires")),
            received_at=received_at,
            pages=_positive_header(response.headers.get("X-Pages")),
        )
        self._cache.put(cache_key, entry)
        return EsiResponse(
            payload=payload,
            received_at=received_at,
            expires_at=entry.expires_at,
            from_cache=False,
            not_modified=False,
            pages=entry.pages,
            etag=entry.etag,
            last_modified=entry.last_modified,
        )

    def _request_with_retries(
        self,
        path: str,
        params: Mapping[str, str | int | bool] | None,
        headers: Mapping[str, str],
    ) -> httpx.Response:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._client.get(path, params=params, headers=headers)
            except httpx.TransportError as error:
                if attempt == MAX_RETRIES:
                    raise EsiTransportError("ESI network request failed") from error
                self._sleeper(float(2**attempt))
                continue
            self._observe_limits(response, self._now())
            if response.status_code not in RETRYABLE_STATUSES:
                return response
            retry_after = _retry_delay(response, attempt)
            if attempt == MAX_RETRIES:
                raise EsiRateLimitError("ESI retry limit reached", retry_after)
            self._sleeper(retry_after)
        raise AssertionError("bounded ESI retry loop did not return")

    def _observe_limits(self, response: httpx.Response, now: datetime) -> None:
        with self._limit_lock:
            error_remaining = _nonnegative_header(response.headers.get("X-ESI-Error-Limit-Remain"))
            error_reset = _nonnegative_header(response.headers.get("X-ESI-Error-Limit-Reset"))
            if error_remaining is not None and error_remaining <= ERROR_LIMIT_FLOOR:
                self._block(now, float(error_reset or 60))
            bucket_remaining = _nonnegative_header(response.headers.get("X-Ratelimit-Remaining"))
            retry_after = _seconds(response.headers.get("Retry-After"))
            if bucket_remaining is not None and bucket_remaining <= BUCKET_REMAINING_FLOOR:
                self._block(now, retry_after or 1.0)

    def _block(self, now: datetime, seconds: float) -> None:
        candidate = now + timedelta(seconds=max(seconds, 0.0))
        if self._blocked_until is None or candidate > self._blocked_until:
            self._blocked_until = candidate

    def _enforce_gate(self, now: datetime) -> None:
        with self._limit_lock:
            if self._blocked_until is not None and now < self._blocked_until:
                raise EsiRateLimitError(
                    "ESI requests are paused by the server limit",
                    (self._blocked_until - now).total_seconds(),
                )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value


def _validate_request(path: str, access_token: str | None, character_id: int | None) -> None:
    if not path.startswith("/") or path.startswith("//") or "://" in path:
        raise ValueError("ESI path must be an absolute API path, not a URL")
    if (access_token is None) != (character_id is None):
        raise ValueError("private ESI requests require both access_token and character_id")
    if character_id is not None and character_id <= 0:
        raise ValueError("ESI character_id must be positive")


def _cache_key(
    path: str,
    params: Mapping[str, str | int | bool] | None,
    character_id: int | None,
) -> str:
    query = urlencode(sorted((params or {}).items()))
    scope = f"character:{character_id}" if character_id is not None else "public"
    raw = f"GET\n{path}\n{query}\n{scope}".encode()
    return hashlib.sha256(raw).hexdigest()


def _cached_response(entry: EsiCacheEntry, *, not_modified: bool) -> EsiResponse:
    return EsiResponse(
        payload=entry.payload,
        received_at=entry.received_at,
        expires_at=entry.expires_at,
        from_cache=True,
        not_modified=not_modified,
        pages=entry.pages,
        etag=entry.etag,
        last_modified=entry.last_modified,
    )


def _http_date(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError) as error:
        raise EsiProtocolError("ESI returned an invalid HTTP date") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _positive_header(value: str | None) -> int | None:
    parsed = _nonnegative_header(value)
    if parsed is not None and parsed <= 0:
        raise EsiProtocolError("ESI returned a non-positive page count")
    return parsed


def _nonnegative_header(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise EsiProtocolError("ESI returned an invalid numeric header") from error
    if parsed < 0:
        raise EsiProtocolError("ESI returned a negative numeric header")
    return parsed


def _seconds(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except ValueError as error:
        raise EsiProtocolError("ESI returned an invalid retry delay") from error
    if not math.isfinite(parsed) or parsed < 0:
        raise EsiProtocolError("ESI returned an invalid retry delay")
    return parsed


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = _seconds(response.headers.get("Retry-After"))
    if retry_after is not None:
        return retry_after
    error_reset = _seconds(response.headers.get("X-ESI-Error-Limit-Reset"))
    if error_reset is not None:
        return error_reset
    return float(2**attempt)


def _error_message(response: httpx.Response) -> str:
    try:
        payload = cast(object, response.json())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return f"ESI request failed with HTTP {response.status_code}"
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, str) and error:
            return error[:200]
    return f"ESI request failed with HTTP {response.status_code}"
