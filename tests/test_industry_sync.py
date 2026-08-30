from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from eve_dolphin.characters.models import EveCharacter
from eve_dolphin.characters.repository import CharacterRepository
from eve_dolphin.characters.token_service import CharacterAccessToken
from eve_dolphin.database import Database
from eve_dolphin.esi.errors import EsiProtocolError
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.models import SsoMetadata
from eve_dolphin.sync.industry import IndustrySyncService, MissingIndustryScopesError
from eve_dolphin.sync.repository import IndustrySnapshotRepository

NOW = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
ASSET_SCOPE = "esi-assets.read_assets.v1"
BLUEPRINT_SCOPE = "esi-characters.read_blueprints.v1"


class _TokenService:
    def __init__(self, scopes: tuple[str, ...] = (ASSET_SCOPE, BLUEPRINT_SCOPE)) -> None:
        self.scopes = scopes

    def refresh(
        self, character_id: int, metadata: SsoMetadata, config: SsoConfig
    ) -> CharacterAccessToken:
        return CharacterAccessToken(
            character_id=character_id,
            access_token=f"token-{character_id}",
            expires_at=NOW + timedelta(minutes=20),
            granted_scopes=self.scopes,
        )


class _Paginator:
    def __init__(self) -> None:
        self.invalid_blueprints = False
        self.calls: list[tuple[str, str, int]] = []

    def get_list(
        self,
        path: str,
        *,
        access_token: str,
        character_id: int,
        params: Mapping[str, str | int | bool] | None = None,
    ) -> tuple[tuple[object, ...], str | None]:
        self.calls.append((path, access_token, character_id))
        if path.endswith("/assets/"):
            return (_asset(character_id * 100),), "Sun, 30 Aug 2026 13:00:00 GMT"
        blueprint = _blueprint(character_id * 100 + 1)
        if self.invalid_blueprints:
            return (blueprint, blueprint), "Sun, 30 Aug 2026 13:00:00 GMT"
        return (blueprint,), "Sun, 30 Aug 2026 13:00:00 GMT"


def test_sync_atomically_activates_assets_and_blueprints(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7, "Industrial Pilot")
    paginator = _Paginator()
    repository = IndustrySnapshotRepository(database)
    service = IndustrySyncService(_TokenService(), paginator, repository, clock=lambda: NOW)

    result = service.sync(7, _metadata(), _config())

    assert result.snapshot.character_id == 7
    assert result.refreshed is True
    assert result.snapshot.asset_count == 1
    assert result.snapshot.blueprint_count == 1
    assert paginator.calls == [
        ("/characters/7/assets/", "token-7", 7),
        ("/characters/7/blueprints/", "token-7", 7),
    ]
    assert repository.current_assets(7)[0].quantity == 1000
    assert repository.current_blueprints(7)[0].material_efficiency == 10
    with database.connect() as connection:
        asset = connection.execute(
            "SELECT item_id, type_id, quantity FROM character_assets"
        ).fetchone()
        blueprint = connection.execute(
            "SELECT item_id, type_id, quantity, runs FROM character_blueprints"
        ).fetchone()
        run = connection.execute("SELECT status FROM sync_runs WHERE character_id = 7").fetchone()
        character = connection.execute(
            "SELECT last_sync_at FROM eve_characters WHERE character_id = 7"
        ).fetchone()
    assert asset is not None and tuple(asset) == (700, 34, 1000)
    assert blueprint is not None and tuple(blueprint) == (701, 681, -1, -1)
    assert run is not None and run[0] == "succeeded"
    assert character is not None and character[0] == NOW.isoformat()


def test_failed_refresh_preserves_previous_snapshot_and_other_character(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7, "First Pilot")
    _link(database, 8, "Second Pilot")
    paginator = _Paginator()
    repository = IndustrySnapshotRepository(database)
    current = [NOW]
    service = IndustrySyncService(_TokenService(), paginator, repository, clock=lambda: current[0])
    first = service.sync(7, _metadata(), _config()).snapshot
    second = service.sync(8, _metadata(), _config()).snapshot
    paginator.invalid_blueprints = True
    current[0] = NOW + timedelta(hours=2)

    with pytest.raises(EsiProtocolError, match="duplicate"):
        service.sync(7, _metadata(), _config())

    current_first = repository.current(7)
    current_second = repository.current(8)
    assert current_first is not None and current_first.snapshot_id == first.snapshot_id
    assert current_second is not None and current_second.snapshot_id == second.snapshot_id
    with database.connect() as connection:
        runs = connection.execute(
            "SELECT status, message FROM sync_runs WHERE character_id = 7 ORDER BY id"
        ).fetchall()
        snapshots = connection.execute(
            "SELECT COUNT(*) FROM industry_snapshots WHERE character_id = 7"
        ).fetchone()
    assert [tuple(run) for run in runs] == [
        ("succeeded", None),
        ("failed", "EsiProtocolError"),
    ]
    assert snapshots is not None and snapshots[0] == 1


def test_missing_scope_stops_before_esi_and_records_failure(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7, "Industrial Pilot")
    paginator = _Paginator()
    service = IndustrySyncService(
        _TokenService((ASSET_SCOPE,)),
        paginator,
        IndustrySnapshotRepository(database),
        clock=lambda: NOW,
    )

    with pytest.raises(MissingIndustryScopesError) as caught:
        service.sync(7, _metadata(), _config())

    assert caught.value.missing_scopes == (BLUEPRINT_SCOPE,)
    assert paginator.calls == []
    with database.connect() as connection:
        run = connection.execute("SELECT status, message FROM sync_runs").fetchone()
    assert run is not None and tuple(run) == ("failed", "MissingIndustryScopesError")


def test_persisted_snapshot_prevents_early_refresh_after_restart(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7, "Industrial Pilot")
    paginator = _Paginator()
    repository = IndustrySnapshotRepository(database)
    first_service = IndustrySyncService(_TokenService(), paginator, repository, clock=lambda: NOW)
    first = first_service.sync(7, _metadata(), _config())
    paginator.calls.clear()
    second_service = IndustrySyncService(
        _TokenService(),
        paginator,
        IndustrySnapshotRepository(database),
        clock=lambda: NOW + timedelta(minutes=30),
    )

    second = second_service.sync(7, _metadata(), _config())

    assert second.refreshed is False
    assert second.snapshot.snapshot_id == first.snapshot.snapshot_id
    assert paginator.calls == []
    with database.connect() as connection:
        run_count = connection.execute("SELECT COUNT(*) FROM sync_runs").fetchone()
    assert run_count is not None and run_count[0] == 1


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "eve-dolphin.sqlite3")
    database.initialize()
    return database


def _link(database: Database, character_id: int, name: str) -> None:
    CharacterRepository(database).upsert(
        EveCharacter(
            character_id=character_id,
            character_name=name,
            owner_hash=f"owner-{character_id}",
            granted_scopes=(ASSET_SCOPE, BLUEPRINT_SCOPE),
            linked_at=NOW,
        )
    )


def _asset(item_id: int) -> dict[str, object]:
    return {
        "item_id": item_id,
        "type_id": 34,
        "quantity": 1000,
        "location_id": 60003760,
        "location_type": "station",
        "location_flag": "Hangar",
        "is_singleton": False,
    }


def _blueprint(item_id: int) -> dict[str, object]:
    return {
        "item_id": item_id,
        "type_id": 681,
        "location_id": 60003760,
        "location_flag": "Hangar",
        "quantity": -1,
        "time_efficiency": 20,
        "material_efficiency": 10,
        "runs": -1,
    }


def _metadata() -> SsoMetadata:
    return SsoMetadata(
        issuer="https://login.eveonline.com",
        authorization_endpoint="https://login.eveonline.com/v2/oauth/authorize",
        token_endpoint="https://login.eveonline.com/v2/oauth/token",
        jwks_uri="https://login.eveonline.com/oauth/jwks",
    )


def _config() -> SsoConfig:
    return SsoConfig(client_id="client-id")
