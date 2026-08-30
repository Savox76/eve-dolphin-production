"""Stable error categories exposed by the shared ESI client."""

from __future__ import annotations


class EsiError(RuntimeError):
    """Base error for a failed ESI operation."""


class EsiTransportError(EsiError):
    """Network access failed after the bounded retry policy."""


class EsiProtocolError(EsiError):
    """ESI returned content or headers that cannot safely be processed."""


class EsiRateLimitError(EsiError):
    """A known ESI error or bucket limit temporarily blocks requests."""

    def __init__(self, message: str, retry_after: float) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class EsiHttpError(EsiError):
    """ESI returned a non-retryable HTTP response."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
