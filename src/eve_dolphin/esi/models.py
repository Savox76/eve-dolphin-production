"""Typed cached and returned ESI representations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EsiCacheEntry:
    payload: object
    etag: str | None
    last_modified: str | None
    expires_at: datetime | None
    received_at: datetime

    def __post_init__(self) -> None:
        if self.received_at.tzinfo is None:
            raise ValueError("ESI received_at must include a timezone")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("ESI expires_at must include a timezone")


@dataclass(frozen=True, slots=True)
class EsiResponse:
    payload: object
    received_at: datetime
    expires_at: datetime | None
    from_cache: bool
    not_modified: bool
    pages: int | None
