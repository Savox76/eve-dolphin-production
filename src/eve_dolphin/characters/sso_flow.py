"""End-to-end character authorization flow independent from the Qt UI thread."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable, Sequence
from types import TracebackType
from typing import Protocol

from eve_dolphin.characters.models import EveCharacter
from eve_dolphin.sso.callback import CallbackCancelledError, LoopbackCallbackServer
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import AuthorizationRequest, CallbackResult, SsoMetadata


class BrowserLaunchError(RuntimeError):
    """The operating system could not open the EVE authorization page."""


class AuthorizationRequestClient(Protocol):
    def fetch_metadata(self) -> SsoMetadata: ...

    def create_authorization_request(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        scopes: Sequence[str] = (),
    ) -> AuthorizationRequest: ...


class CallbackReceiver(Protocol):
    def __enter__(self) -> CallbackReceiver: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def wait_for_result(
        self,
        expected_state: str,
        timeout_seconds: float = 180.0,
        cancelled: Callable[[], bool] | None = None,
    ) -> CallbackResult: ...


class CharacterLinkCompleter(Protocol):
    def complete_link(
        self,
        metadata: SsoMetadata,
        config: SsoConfig,
        request: AuthorizationRequest,
        callback: CallbackResult,
    ) -> EveCharacter: ...


class CharacterSsoFlow:
    """Open EVE SSO only after the local callback is ready to receive it."""

    def __init__(
        self,
        sso_client: AuthorizationRequestClient,
        link_service: CharacterLinkCompleter,
        callback_factory: Callable[[str], CallbackReceiver] = LoopbackCallbackServer,
        browser_opener: Callable[[str], bool] = webbrowser.open_new_tab,
    ) -> None:
        self._sso_client = sso_client
        self._link_service = link_service
        self._callback_factory = callback_factory
        self._browser_opener = browser_opener

    def link_character(
        self,
        config: SsoConfig,
        scopes: Sequence[str] = (),
        authorization_ready: Callable[[str], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> EveCharacter:
        if cancelled is not None and cancelled():
            raise CallbackCancelledError("EVE SSO authorization was cancelled")
        metadata = self._sso_client.fetch_metadata()
        request = self._sso_client.create_authorization_request(metadata, config, scopes)

        with self._callback_factory(config.redirect_uri) as callback_server:
            if cancelled is not None and cancelled():
                raise CallbackCancelledError("EVE SSO authorization was cancelled")
            if authorization_ready is not None:
                authorization_ready(request.url)
            if not self._browser_opener(request.url):
                raise BrowserLaunchError("system browser could not be opened")
            callback = callback_server.wait_for_result(request.state, cancelled=cancelled)

        return self._link_service.complete_link(metadata, config, request, callback)
