from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from eve_dolphin.characters.models import EveCharacter
from eve_dolphin.characters.repository import CharacterRepository
from eve_dolphin.characters.token_service import CharacterAccessToken
from eve_dolphin.database import Database
from eve_dolphin.esi.errors import EsiProtocolError
from eve_dolphin.esi.models import EsiResponse
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import SsoMetadata
from eve_dolphin.sync.jobs import IndustryJobSyncService, MissingIndustryJobScopeError
from eve_dolphin.sync.jobs_repository import IndustryJobSnapshotRepository

NOW = datetime(2026, 8, 30, 16, 0, tzinfo=UTC)
JOB_SCOPE = "esi-industry.read_character_jobs.v1"
LAST_MODIFIED = "Sun, 30 Aug 2026 15:55:00 GMT"


class _TokenService:
    def __init__(self, scopes: tuple[str, ...] = (JOB_SCOPE,)) -> None:
        self.scopes = scopes
        self.calls = 0

    def refresh(
        self, character_id: int, metadata: SsoMetadata, config: SsoConfig
    ) -> CharacterAccessToken:
        self.calls += 1
        return CharacterAccessToken(
            character_id=character_id,
            access_token=f"token-{character_id}",
            expires_at=NOW + timedelta(minutes=20),
            granted_scopes=self.scopes,
        )


class _EsiClient:
    def __init__(self) -> None:
        self.invalid = False
        self.calls: list[
            tuple[str, Mapping[str, str | int | bool] | None, str | None, int | None]
        ] = []

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str | int | bool] | None = None,
        access_token: str | None = None,
        character_id: int | None = None,
    ) -> EsiResponse:
        self.calls.append((path, params, access_token, character_id))
        payload: object
        if self.invalid:
            duplicate = _job(character_id or 1, 1001, "active")
            payload = [duplicate, duplicate]
        else:
            payload = [
                _job(character_id or 1, 1001, "active"),
                _job(character_id or 1, 1002, "delivered", completed=True),
            ]
        return EsiResponse(
            payload=payload,
            received_at=NOW,
            expires_at=NOW + timedelta(minutes=5),
            from_cache=False,
            not_modified=False,
            pages=None,
            etag='"jobs"',
            last_modified=LAST_MODIFIED,
        )


def test_sync_activates_current_and_completed_jobs_atomically(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7)
    token_service = _TokenService()
    esi_client = _EsiClient()
    repository = IndustryJobSnapshotRepository(database)
    service = IndustryJobSyncService(token_service, esi_client, repository, clock=lambda: NOW)

    result = service.sync(7, _metadata(), _config())

    assert result.refreshed is True
    assert result.snapshot.job_count == 2
    assert result.snapshot.last_modified == LAST_MODIFIED
    assert esi_client.calls == [
        (
            "/characters/7/industry/jobs/",
            {"include_completed": True},
            "token-7",
            7,
        )
    ]
    jobs = repository.current_jobs(7)
    assert [job.status for job in jobs] == ["active", "delivered"]
    assert jobs[0].cost == Decimal("1234.56")
    assert jobs[0].probability == Decimal("0.42")
    assert jobs[1].completed_date == datetime(2026, 8, 30, 15, 30, tzinfo=UTC)
    with database.connect() as connection:
        run = connection.execute(
            "SELECT sync_kind, status FROM sync_runs WHERE character_id = 7"
        ).fetchone()
    assert run is not None and tuple(run) == ("industry_jobs", "succeeded")


def test_invalid_new_jobs_preserve_previous_snapshot_and_other_character(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7)
    _link(database, 8)
    current = [NOW]
    esi_client = _EsiClient()
    repository = IndustryJobSnapshotRepository(database)
    service = IndustryJobSyncService(
        _TokenService(), esi_client, repository, clock=lambda: current[0]
    )
    first = service.sync(7, _metadata(), _config()).snapshot
    second = service.sync(8, _metadata(), _config()).snapshot
    current[0] = NOW + timedelta(minutes=6)
    esi_client.invalid = True

    with pytest.raises(EsiProtocolError, match="duplicate"):
        service.sync(7, _metadata(), _config())

    current_first = repository.current(7)
    current_second = repository.current(8)
    assert current_first is not None and current_first.snapshot_id == first.snapshot_id
    assert current_second is not None and current_second.snapshot_id == second.snapshot_id
    with database.connect() as connection:
        snapshots = connection.execute(
            "SELECT COUNT(*) FROM industry_job_snapshots WHERE character_id = 7"
        ).fetchone()
        failed = connection.execute(
            """
            SELECT status, message FROM sync_runs
            WHERE character_id = 7 ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
    assert snapshots is not None and snapshots[0] == 1
    assert failed is not None and tuple(failed) == ("failed", "EsiProtocolError")


def test_persisted_five_minute_cache_survives_service_restart(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7)
    token_service = _TokenService()
    esi_client = _EsiClient()
    repository = IndustryJobSnapshotRepository(database)
    first = IndustryJobSyncService(token_service, esi_client, repository, clock=lambda: NOW).sync(
        7, _metadata(), _config()
    )
    second = IndustryJobSyncService(
        token_service,
        esi_client,
        IndustryJobSnapshotRepository(database),
        clock=lambda: NOW + timedelta(minutes=4),
    ).sync(7, _metadata(), _config())

    assert second.refreshed is False
    assert second.snapshot.snapshot_id == first.snapshot.snapshot_id
    assert token_service.calls == 1
    assert len(esi_client.calls) == 1


def test_missing_job_scope_stops_before_esi_request(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7)
    esi_client = _EsiClient()
    service = IndustryJobSyncService(
        _TokenService(()),
        esi_client,
        IndustryJobSnapshotRepository(database),
        clock=lambda: NOW,
    )

    with pytest.raises(MissingIndustryJobScopeError) as caught:
        service.sync(7, _metadata(), _config())

    assert caught.value.missing_scopes == (JOB_SCOPE,)
    assert esi_client.calls == []


def _job(
    character_id: int,
    job_id: int,
    status: str,
    *,
    completed: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "job_id": job_id,
        "installer_id": character_id,
        "facility_id": 1028858195912,
        "station_id": 60003760,
        "activity_id": 1,
        "blueprint_id": 900000000001,
        "blueprint_type_id": 681,
        "blueprint_location_id": 60003760,
        "output_location_id": 60003760,
        "runs": 10,
        "status": status,
        "duration": 3600,
        "start_date": "2026-08-30T14:00:00Z",
        "end_date": "2026-08-30T15:00:00Z",
        "cost": 1234.56,
        "probability": 0.42,
        "product_type_id": 587,
    }
    if completed:
        payload.update(
            {
                "completed_character_id": character_id,
                "completed_date": "2026-08-30T15:30:00Z",
                "successful_runs": 8,
            }
        )
    return payload


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "eve-dolphin.sqlite3")
    database.initialize()
    return database


def _link(database: Database, character_id: int) -> None:
    CharacterRepository(database).upsert(
        EveCharacter(
            character_id=character_id,
            character_name=f"Pilot {character_id}",
            owner_hash=f"owner-{character_id}",
            granted_scopes=(JOB_SCOPE,),
            linked_at=NOW,
        )
    )


def _metadata() -> SsoMetadata:
    return SsoMetadata(
        issuer="https://login.eveonline.com",
        authorization_endpoint="https://login.eveonline.com/v2/oauth/authorize",
        token_endpoint="https://login.eveonline.com/v2/oauth/token",
        jwks_uri="https://login.eveonline.com/oauth/jwks",
    )


def _config() -> SsoConfig:
    return SsoConfig(client_id="client-id")
