from __future__ import annotations

import socket
import threading
from dataclasses import dataclass

import httpx

from eve_production_tool.sso.callback import (
    CallbackStateMismatchError,
    LoopbackCallbackServer,
)
from eve_production_tool.sso.models import CallbackResult


@dataclass
class WaitOutcome:
    result: CallbackResult | None = None
    error: BaseException | None = None


def test_loopback_callback_accepts_one_exact_correlated_response() -> None:
    port = _available_loopback_port()
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    outcome = WaitOutcome()

    with LoopbackCallbackServer(redirect_uri) as server:
        thread = _wait_in_thread(server, "correct-state", outcome)
        with httpx.Client(trust_env=False, timeout=2.0) as client:
            not_found = client.get(f"http://127.0.0.1:{port}/wrong")
            response = client.get(
                redirect_uri,
                params={"code": "one-time-code", "state": "correct-state"},
            )
        thread.join(timeout=2.0)

    assert not_found.status_code == 404
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert outcome.error is None
    assert outcome.result == CallbackResult(state="correct-state", code="one-time-code")
    assert not thread.is_alive()


def test_loopback_callback_rejects_wrong_state() -> None:
    port = _available_loopback_port()
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    outcome = WaitOutcome()

    with LoopbackCallbackServer(redirect_uri) as server:
        thread = _wait_in_thread(server, "expected", outcome)
        with httpx.Client(trust_env=False, timeout=2.0) as client:
            response = client.get(
                redirect_uri,
                params={"code": "one-time-code", "state": "attacker"},
            )
        thread.join(timeout=2.0)

    assert response.status_code == 400
    assert isinstance(outcome.error, CallbackStateMismatchError)
    assert outcome.result is None


def test_loopback_callback_returns_eve_authorization_error_without_echoing_it() -> None:
    port = _available_loopback_port()
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    outcome = WaitOutcome()

    with LoopbackCallbackServer(redirect_uri) as server:
        thread = _wait_in_thread(server, "expected", outcome)
        with httpx.Client(trust_env=False, timeout=2.0) as client:
            response = client.get(
                redirect_uri,
                params={
                    "error": "access_denied",
                    "error_description": "private browser message",
                    "state": "expected",
                },
            )
        thread.join(timeout=2.0)

    assert response.status_code == 200
    assert "private browser message" not in response.text
    assert outcome.result == CallbackResult(
        state="expected",
        error="access_denied",
        error_description="private browser message",
    )


def _available_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_in_thread(
    server: LoopbackCallbackServer,
    expected_state: str,
    outcome: WaitOutcome,
) -> threading.Thread:
    def wait() -> None:
        try:
            outcome.result = server.wait_for_result(expected_state, timeout_seconds=2.0)
        except BaseException as error:
            outcome.error = error

    thread = threading.Thread(target=wait, daemon=True)
    thread.start()
    return thread
