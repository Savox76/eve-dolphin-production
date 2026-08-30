from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from types import TracebackType

import pytest

from eve_dolphin.characters import BrowserLaunchError, CharacterSsoFlow, EveCharacter
from eve_dolphin.sso.callback import CallbackCancelledError
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import AuthorizationRequest, CallbackResult, SsoMetadata


class FakeSsoClient:
    def __init__(self) -> None:
        self.scopes: tuple[str, ...] = ()

    def fetch_metadata(self) -> SsoMetadata:
        return _metadata()

    def create_authorization_request(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        scopes: Sequence[str] = (),
    ) -> AuthorizationRequest:
        assert metadata == _metadata()
        assert config == _config()
        self.scopes = tuple(scopes)
        return _request()


class FakeCallbackServer:
    def __init__(self, redirect_uri: str) -> None:
        assert redirect_uri == _config().redirect_uri
        self.active = False

    def __enter__(self) -> FakeCallbackServer:
        self.active = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.active = False

    def wait_for_result(
        self,
        expected_state: str,
        timeout_seconds: float = 180.0,
        cancelled: Callable[[], bool] | None = None,
    ) -> CallbackResult:
        assert self.active
        assert expected_state == _request().state
        assert timeout_seconds == 180.0
        assert cancelled is None
        return CallbackResult(state=expected_state, code="authorization-code")


class FakeLinkService:
    def __init__(self) -> None:
        self.callback: CallbackResult | None = None

    def complete_link(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        request: AuthorizationRequest,
        callback: CallbackResult,
    ) -> EveCharacter:
        assert metadata == _metadata()
        assert config == _config()
        assert request == _request()
        self.callback = callback
        return _character()


def test_callback_is_listening_before_system_browser_opens() -> None:
    callback_server = FakeCallbackServer(_config().redirect_uri)
    client = FakeSsoClient()
    link_service = FakeLinkService()
    opened_urls: list[str] = []
    ready_urls: list[str] = []

    def open_browser(url: str) -> bool:
        assert callback_server.active
        opened_urls.append(url)
        return True

    flow = CharacterSsoFlow(
        client,
        link_service,
        callback_factory=lambda _redirect_uri: callback_server,
        browser_opener=open_browser,
    )

    character = flow.link_character(
        _config(),
        ("esi-assets.read_assets.v1",),
        authorization_ready=ready_urls.append,
    )

    assert character == _character()
    assert client.scopes == ("esi-assets.read_assets.v1",)
    assert ready_urls == [_request().url]
    assert opened_urls == [_request().url]
    assert link_service.callback == CallbackResult(
        state=_request().state,
        code="authorization-code",
    )


def test_failed_browser_launch_stops_before_token_exchange() -> None:
    link_service = FakeLinkService()
    flow = CharacterSsoFlow(
        FakeSsoClient(),
        link_service,
        callback_factory=FakeCallbackServer,
        browser_opener=lambda _url: False,
    )

    with pytest.raises(BrowserLaunchError):
        flow.link_character(_config())

    assert link_service.callback is None


def test_cancelled_flow_does_not_open_browser() -> None:
    opened_urls: list[str] = []

    def open_browser(url: str) -> bool:
        opened_urls.append(url)
        return True

    flow = CharacterSsoFlow(
        FakeSsoClient(),
        FakeLinkService(),
        callback_factory=FakeCallbackServer,
        browser_opener=open_browser,
    )

    with pytest.raises(CallbackCancelledError):
        flow.link_character(_config(), cancelled=lambda: True)

    assert opened_urls == []


def _config() -> SsoConfig:
    return SsoConfig("public-client")


def _metadata() -> SsoMetadata:
    return SsoMetadata(
        issuer="https://login.eveonline.com/",
        authorization_endpoint="https://login.eveonline.com/v2/oauth/authorize",
        token_endpoint="https://login.eveonline.com/v2/oauth/token",
        jwks_uri="https://login.eveonline.com/oauth/jwks",
    )


def _request() -> AuthorizationRequest:
    return AuthorizationRequest(
        "https://login.eveonline.com/v2/oauth/authorize?state=state",
        "state",
        "verifier",
    )


def _character() -> EveCharacter:
    return EveCharacter(
        1001,
        "Industrial Pilot",
        "owner",
        (),
        datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
    )
