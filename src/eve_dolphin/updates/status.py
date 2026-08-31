"""Persistent hand-off state between the desktop client and update helper."""

from __future__ import annotations

import json
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

UPDATE_STATE_NAME = "update-state.json"
MAX_STATE_BYTES = 16 * 1024


class UpdateStateStatus(StrEnum):
    APPLYING = "applying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class UpdateState:
    status: UpdateStateStatus
    version: str
    updated_at: datetime
    error_code: str | None = None


def write_update_state(
    update_dir: Path,
    status: UpdateStateStatus,
    version: str,
    *,
    error_code: str | None = None,
) -> None:
    """Atomically persist a small, non-sensitive updater result."""

    update_dir.mkdir(parents=True, exist_ok=True)
    path = update_dir / UPDATE_STATE_NAME
    temporary = path.with_suffix(".tmp")
    payload = {
        "status": status.value,
        "version": version,
        "updated_at": datetime.now(UTC).isoformat(),
        "error_code": error_code,
    }
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def read_update_state(update_dir: Path) -> UpdateState | None:
    path = update_dir / UPDATE_STATE_NAME
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_STATE_BYTES:
        raise ValueError("update state is too large")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("update state is invalid")

    status = UpdateStateStatus(str(payload.get("status", "")))
    version = payload.get("version")
    error_code = payload.get("error_code")
    updated_at_raw = payload.get("updated_at")
    if not isinstance(version, str) or not version or len(version) > 64:
        raise ValueError("update state version is invalid")
    if error_code is not None and (not isinstance(error_code, str) or len(error_code) > 64):
        raise ValueError("update state error code is invalid")
    if not isinstance(updated_at_raw, str):
        raise ValueError("update state timestamp is invalid")
    updated_at = datetime.fromisoformat(updated_at_raw)
    if updated_at.tzinfo is None:
        raise ValueError("update state timestamp has no timezone")
    return UpdateState(status, version, updated_at, error_code)


def consume_update_result(update_dir: Path) -> UpdateState | None:
    """Return and remove one terminal result after the restarted app reads it."""

    path = update_dir / UPDATE_STATE_NAME
    try:
        state = read_update_state(update_dir)
    except (OSError, ValueError, json.JSONDecodeError):
        with suppress(OSError):
            path.unlink()
        return None
    if state is None or state.status is UpdateStateStatus.APPLYING:
        return None
    with suppress(OSError):
        path.unlink()
    return state
