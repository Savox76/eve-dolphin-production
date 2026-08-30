"""Single-use loopback HTTP callback for the system-browser SSO flow."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import TracebackType
from urllib.parse import parse_qs, urlsplit

from eve_dolphin.sso.config import validate_loopback_redirect_uri
from eve_dolphin.sso.models import CallbackResult


class CallbackTimeoutError(TimeoutError):
    """The browser did not return to the local client in time."""


class CallbackCancelledError(RuntimeError):
    """The desktop client was closed while authorization was pending."""


class CallbackStateMismatchError(ValueError):
    """The callback did not carry the state created by this login attempt."""


class LoopbackCallbackServer:
    """Receive exactly one EVE SSO result on a fixed IPv4 loopback callback."""

    def __init__(self, redirect_uri: str) -> None:
        validate_loopback_redirect_uri(redirect_uri)
        parsed = urlsplit(redirect_uri)
        assert parsed.hostname == "127.0.0.1"
        assert parsed.port is not None
        self._server = _CallbackHttpServer(
            (parsed.hostname, parsed.port),
            _CallbackRequestHandler,
            callback_path=parsed.path,
        )

    def __enter__(self) -> LoopbackCallbackServer:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def wait_for_result(
        self,
        expected_state: str,
        timeout_seconds: float = 180.0,
        cancelled: Callable[[], bool] | None = None,
    ) -> CallbackResult:
        if not expected_state:
            raise ValueError("expected_state must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self._server.expected_state = expected_state
        deadline = time.monotonic() + timeout_seconds
        while self._server.result is None:
            if cancelled is not None and cancelled():
                raise CallbackCancelledError("EVE SSO callback was cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CallbackTimeoutError("EVE SSO callback timed out")
            self._server.timeout = min(remaining, 0.5)
            self._server.handle_request()

        result = self._server.result
        if not secrets.compare_digest(result.state, expected_state):
            raise CallbackStateMismatchError("EVE SSO callback state does not match")
        return result

    def close(self) -> None:
        self._server.server_close()


class _CallbackHttpServer(HTTPServer):
    allow_reuse_address = False

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        callback_path: str,
    ) -> None:
        self.callback_path = callback_path
        self.expected_state = ""
        self.result: CallbackResult | None = None
        super().__init__(server_address, handler_class)


class _CallbackRequestHandler(BaseHTTPRequestHandler):
    server: _CallbackHttpServer

    def do_GET(self) -> None:
        if len(self.path) > 4096:
            self._send_page(HTTPStatus.REQUEST_URI_TOO_LONG, "Ungültige Anfrage")
            return

        parsed = urlsplit(self.path)
        if parsed.path != self.server.callback_path:
            self._send_page(HTTPStatus.NOT_FOUND, "Nicht gefunden")
            return

        query = parse_qs(parsed.query, keep_blank_values=True)
        state = _single_query_value(query, "state")
        code = _single_query_value(query, "code")
        error = _single_query_value(query, "error")
        error_description = _single_query_value(query, "error_description")

        if state is None or not secrets.compare_digest(state, self.server.expected_state):
            self.server.result = CallbackResult(state=state or "", error="state_mismatch")
            self._send_page(HTTPStatus.BAD_REQUEST, "Anmeldung konnte nicht bestätigt werden")
            return
        if (code is None) == (error is None):
            self.server.result = CallbackResult(state=state, error="invalid_response")
            self._send_page(HTTPStatus.BAD_REQUEST, "Ungültige Antwort von EVE SSO")
            return

        self.server.result = CallbackResult(
            state=state,
            code=code,
            error=error,
            error_description=error_description,
        )
        message = (
            "Anmeldung abgeschlossen - dieses Fenster kann geschlossen werden."
            if code is not None
            else "Anmeldung abgebrochen - dieses Fenster kann geschlossen werden."
        )
        self._send_page(HTTPStatus.OK, message)

    def log_message(self, format: str, *args: object) -> None:
        """Avoid writing authorization callback query data to application logs."""

    def _send_page(self, status: HTTPStatus, message: str) -> None:
        body = (
            "<!doctype html><html lang='de'><meta charset='utf-8'>"
            f"<title>EVE Dolphin</title><body><p>{message}</p></body></html>"
        ).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def _single_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if values is None or len(values) != 1 or not values[0]:
        return None
    return values[0]
