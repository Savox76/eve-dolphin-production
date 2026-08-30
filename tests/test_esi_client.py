from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import format_datetime

import httpx
import pytest

from eve_dolphin.esi import (
    ESI_COMPATIBILITY_DATE,
    EsiHttpError,
    EsiProtocolError,
    EsiRateLimitError,
    EsiTransportError,
    EveEsiClient,
)
from eve_dolphin.esi.pagination import EsiPaginator

NOW = datetime(2026, 8, 30, 13, 0, tzinfo=UTC)


def test_public_request_sends_compatibility_and_uses_fresh_cache() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"name": "Tritanium"},
            headers={
                "ETag": '"type-34"',
                "Last-Modified": "Sun, 30 Aug 2026 12:00:00 GMT",
                "Expires": "Sun, 30 Aug 2026 14:00:00 GMT",
            },
        )

    client = _client(handler)

    first = client.get_json("/universe/types/34/")
    second = client.get_json("/universe/types/34/")

    assert first.payload == {"name": "Tritanium"}
    assert first.from_cache is False
    assert second.from_cache is True
    assert len(requests) == 1
    assert requests[0].headers["X-Compatibility-Date"] == ESI_COMPATIBILITY_DATE


def test_expired_cache_is_revalidated_and_304_refreshes_representation() -> None:
    current = [NOW]
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                json=[1, 2, 3],
                headers={"ETag": '"assets"', "Expires": _http_date(NOW + timedelta(minutes=1))},
            )
        assert request.headers["If-None-Match"] == '"assets"'
        return httpx.Response(
            304,
            headers={"ETag": '"assets"', "Expires": _http_date(NOW + timedelta(minutes=6))},
        )

    client = _client(handler, clock=lambda: current[0])
    first = client.get_json("/characters/7/assets/", access_token="secret", character_id=7)
    current[0] = NOW + timedelta(minutes=2)
    second = client.get_json("/characters/7/assets/", access_token="secret", character_id=7)

    assert first.payload == second.payload == [1, 2, 3]
    assert second.from_cache is True
    assert second.not_modified is True
    assert calls == 2


def test_private_cache_is_separated_by_character_and_token_is_not_in_url() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"call": len(requests)})

    client = _client(handler)

    first = client.get_json("/characters/7/assets/", access_token="token-seven", character_id=7)
    second = client.get_json("/characters/8/assets/", access_token="token-eight", character_id=8)

    assert first.payload != second.payload
    assert len(requests) == 2
    assert requests[0].headers["Authorization"] == "Bearer token-seven"
    assert "token-seven" not in str(requests[0].url)


def test_429_respects_retry_after_then_succeeds() -> None:
    sleeps: list[float] = []
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler, sleeper=sleeps.append)

    response = client.get_json("/markets/prices/")

    assert response.payload == {"ok": True}
    assert sleeps == [3.0]


def test_retry_limit_surfaces_rate_limit_delay() -> None:
    client = _client(
        lambda request: httpx.Response(420, headers={"X-ESI-Error-Limit-Reset": "12"}),
        sleeper=lambda seconds: None,
    )

    with pytest.raises(EsiRateLimitError) as caught:
        client.get_json("/markets/prices/")

    assert caught.value.retry_after == 12


def test_low_error_budget_blocks_follow_up_without_network_request() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"ok": True},
            headers={"X-ESI-Error-Limit-Remain": "5", "X-ESI-Error-Limit-Reset": "30"},
        )

    client = _client(handler)
    client.get_json("/markets/prices/")

    with pytest.raises(EsiRateLimitError) as caught:
        client.get_json("/universe/systems/30000142/")

    assert caught.value.retry_after == 30
    assert calls == 1


def test_transport_failures_are_bounded() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("offline", request=request)

    client = _client(handler, sleeper=lambda seconds: None)

    with pytest.raises(EsiTransportError):
        client.get_json("/markets/prices/")

    assert calls == 3


def test_auth_error_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(403, json={"error": "Forbidden"})

    client = _client(handler)

    with pytest.raises(EsiHttpError) as caught:
        client.get_json("/characters/7/assets/", access_token="token", character_id=7)

    assert caught.value.status_code == 403
    assert str(caught.value) == "Forbidden"
    assert calls == 1


def test_json_decimal_values_are_not_parsed_through_binary_float() -> None:
    client = _client(
        lambda request: httpx.Response(200, content=b'{"cost":1234.56,"probability":0.42}')
    )

    response = client.get_json("/markets/prices/")

    assert response.payload == {
        "cost": Decimal("1234.56"),
        "probability": Decimal("0.42"),
    }


def test_invalid_pages_and_private_request_boundaries_are_rejected() -> None:
    client = _client(lambda request: httpx.Response(200, json=[], headers={"X-Pages": "0"}))

    with pytest.raises(EsiProtocolError):
        client.get_json("/markets/10000002/orders/")
    with pytest.raises(ValueError):
        client.get_json("https://attacker.invalid/")
    with pytest.raises(ValueError):
        client.get_json("/characters/7/assets/", access_token="token")


def test_paginator_collects_consistent_pages() -> None:
    requested_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        requested_pages.append(page)
        return httpx.Response(
            200,
            json=[{"item_id": page}],
            headers={"X-Pages": "2", "Last-Modified": "Sun, 30 Aug 2026 12:00:00 GMT"},
        )

    records, last_modified = EsiPaginator(_client(handler)).get_list(
        "/characters/7/assets/", access_token="token", character_id=7
    )

    assert records == ({"item_id": 1}, {"item_id": 2})
    assert last_modified == "Sun, 30 Aug 2026 12:00:00 GMT"
    assert requested_pages == [1, 2]


def test_paginator_rejects_pages_from_different_resource_versions() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        return httpx.Response(
            200,
            json=[],
            headers={
                "X-Pages": "2",
                "Last-Modified": f"Sun, 30 Aug 2026 1{page}:00:00 GMT",
            },
        )

    with pytest.raises(EsiProtocolError, match="inconsistent"):
        EsiPaginator(_client(handler)).get_list(
            "/characters/7/assets/", access_token="token", character_id=7
        )


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    clock: Callable[[], datetime] = lambda: NOW,
    sleeper: Callable[[float], None] = lambda seconds: None,
) -> EveEsiClient:
    return EveEsiClient(
        httpx.Client(transport=httpx.MockTransport(handler), base_url="https://esi.evetech.net"),
        clock=clock,
        sleeper=sleeper,
    )


def _http_date(value: datetime) -> str:
    return format_datetime(value, usegmt=True)
