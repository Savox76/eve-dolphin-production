"""Character domain model stored locally after a verified EVE SSO login."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AuthorizationStatus(StrEnum):
    ACTIVE = "active"
    REAUTHORIZATION_REQUIRED = "reauthorization_required"


@dataclass(frozen=True, slots=True)
class EveCharacter:
    character_id: int
    character_name: str
    owner_hash: str | None
    granted_scopes: tuple[str, ...]
    linked_at: datetime
    last_sync_at: datetime | None = None
    authorization_status: AuthorizationStatus = AuthorizationStatus.ACTIVE
    authorization_error_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.character_id <= 0:
            raise ValueError("character_id must be positive")
        if not self.character_name.strip():
            raise ValueError("character_name must not be empty")
        if self.linked_at.tzinfo is None:
            raise ValueError("linked_at must include a timezone")
        if self.last_sync_at is not None and self.last_sync_at.tzinfo is None:
            raise ValueError("last_sync_at must include a timezone")
        if self.authorization_error_at is not None and self.authorization_error_at.tzinfo is None:
            raise ValueError("authorization_error_at must include a timezone")
        if (
            self.authorization_status is AuthorizationStatus.REAUTHORIZATION_REQUIRED
            and self.authorization_error_at is None
        ):
            raise ValueError("reauthorization_required must include an error time")
        if (
            self.authorization_status is AuthorizationStatus.ACTIVE
            and self.authorization_error_at is not None
        ):
            raise ValueError("active authorization cannot include an error time")
