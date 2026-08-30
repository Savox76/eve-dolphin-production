"""Validated character industry job representations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import cast

from eve_dolphin.esi.errors import EsiProtocolError

JOB_STATUSES = frozenset({"active", "cancelled", "delivered", "paused", "ready", "reverted"})


@dataclass(frozen=True, slots=True)
class CharacterIndustryJob:
    job_id: int
    installer_id: int
    facility_id: int
    station_id: int
    activity_id: int
    blueprint_id: int
    blueprint_type_id: int
    blueprint_location_id: int
    output_location_id: int
    runs: int
    status: str
    duration_seconds: int
    start_date: datetime
    end_date: datetime
    completed_character_id: int | None
    completed_date: datetime | None
    pause_date: datetime | None
    cost: Decimal | None
    licensed_runs: int | None
    probability: Decimal | None
    product_type_id: int | None
    successful_runs: int | None


@dataclass(frozen=True, slots=True)
class IndustryJobSnapshot:
    snapshot_id: int
    character_id: int
    fetched_at: datetime
    job_count: int
    last_modified: str | None


@dataclass(frozen=True, slots=True)
class IndustryJobSyncResult:
    snapshot: IndustryJobSnapshot
    refreshed: bool


def parse_industry_jobs(payload: object) -> tuple[CharacterIndustryJob, ...]:
    if not isinstance(payload, list):
        raise EsiProtocolError("ESI industry jobs resource is not a list")
    jobs: list[CharacterIndustryJob] = []
    job_ids: set[int] = set()
    for value in payload:
        record = _record(value)
        job_id = _positive_int(record, "job_id")
        if job_id in job_ids:
            raise EsiProtocolError("ESI industry jobs contain duplicate job IDs")
        job_ids.add(job_id)
        status = _string(record, "status")
        if status not in JOB_STATUSES:
            raise EsiProtocolError("ESI industry job has an unknown status")
        duration = _integer(record, "duration")
        if duration < 0:
            raise EsiProtocolError("ESI industry job duration is negative")
        probability = _optional_decimal(record, "probability")
        if probability is not None and not Decimal(0) <= probability <= Decimal(1):
            raise EsiProtocolError("ESI industry job probability is outside 0..1")
        cost = _optional_decimal(record, "cost")
        if cost is not None and cost < 0:
            raise EsiProtocolError("ESI industry job cost is negative")
        jobs.append(
            CharacterIndustryJob(
                job_id=job_id,
                installer_id=_positive_int(record, "installer_id"),
                facility_id=_positive_int(record, "facility_id"),
                station_id=_positive_int(record, "station_id"),
                activity_id=_positive_int(record, "activity_id"),
                blueprint_id=_positive_int(record, "blueprint_id"),
                blueprint_type_id=_positive_int(record, "blueprint_type_id"),
                blueprint_location_id=_positive_int(record, "blueprint_location_id"),
                output_location_id=_positive_int(record, "output_location_id"),
                runs=_positive_int(record, "runs"),
                status=status,
                duration_seconds=duration,
                start_date=_timestamp(record, "start_date"),
                end_date=_timestamp(record, "end_date"),
                completed_character_id=_optional_positive_int(record, "completed_character_id"),
                completed_date=_optional_timestamp(record, "completed_date"),
                pause_date=_optional_timestamp(record, "pause_date"),
                cost=cost,
                licensed_runs=_optional_nonnegative_int(record, "licensed_runs"),
                probability=probability,
                product_type_id=_optional_positive_int(record, "product_type_id"),
                successful_runs=_optional_nonnegative_int(record, "successful_runs"),
            )
        )
    return tuple(jobs)


def _record(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise EsiProtocolError("ESI industry job record is not an object")
    return cast(dict[str, object], value)


def _integer(record: dict[str, object], key: str) -> int:
    value = record.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise EsiProtocolError(f"ESI industry job has no valid {key}")
    return value


def _positive_int(record: dict[str, object], key: str) -> int:
    value = _integer(record, key)
    if value <= 0:
        raise EsiProtocolError(f"ESI industry job has no positive {key}")
    return value


def _optional_positive_int(record: dict[str, object], key: str) -> int | None:
    if record.get(key) is None:
        return None
    return _positive_int(record, key)


def _optional_nonnegative_int(record: dict[str, object], key: str) -> int | None:
    if record.get(key) is None:
        return None
    value = _integer(record, key)
    if value < 0:
        raise EsiProtocolError(f"ESI industry job has a negative {key}")
    return value


def _string(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise EsiProtocolError(f"ESI industry job has no valid {key}")
    return value


def _timestamp(record: dict[str, object], key: str) -> datetime:
    value = _string(record, key)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EsiProtocolError(f"ESI industry job has an invalid {key}") from error
    if parsed.tzinfo is None:
        raise EsiProtocolError(f"ESI industry job {key} has no timezone")
    return parsed


def _optional_timestamp(record: dict[str, object], key: str) -> datetime | None:
    if record.get(key) is None:
        return None
    return _timestamp(record, key)


def _optional_decimal(record: dict[str, object], key: str) -> Decimal | None:
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float, Decimal)) or isinstance(value, bool):
        raise EsiProtocolError(f"ESI industry job has no numeric {key}")
    if isinstance(value, float) and not math.isfinite(value):
        raise EsiProtocolError(f"ESI industry job has a non-finite {key}")
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise EsiProtocolError(f"ESI industry job has a non-finite {key}")
    return parsed
