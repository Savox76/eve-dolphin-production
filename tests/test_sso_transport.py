from __future__ import annotations

import httpx
import pytest

from eve_dolphin.sso.transport import HttpxTransport, OAuthTokenRequestError


def test_oauth_error_is_structured_without_response_description(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("POST", "https://login.eveonline.com/v2/oauth/token")

    def reject(*args: object, **kwargs: object) -> httpx.Response:
        return httpx.Response(
            400,
            request=request,
            json={
                "error": "invalid_grant",
                "error_description": "sensitive provider detail",
            },
        )

    monkeypatch.setattr(httpx, "post", reject)

    with pytest.raises(OAuthTokenRequestError) as caught:
        HttpxTransport().post_form(str(request.url), {"refresh_token": "secret"})

    assert caught.value.error_code == "invalid_grant"
    assert caught.value.status_code == 400
    assert "sensitive provider detail" not in str(caught.value)
    assert "secret" not in str(caught.value)


def test_oauth_rate_limit_exposes_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", "https://login.eveonline.com/v2/oauth/token")

    def rate_limited(*args: object, **kwargs: object) -> httpx.Response:
        return httpx.Response(
            429,
            request=request,
            headers={"Retry-After": "60"},
            json={"error": "temporarily_unavailable"},
        )

    monkeypatch.setattr(httpx, "post", rate_limited)

    with pytest.raises(OAuthTokenRequestError) as caught:
        HttpxTransport().post_form(str(request.url), {})

    assert caught.value.retry_after == "60"
