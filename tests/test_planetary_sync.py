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
from eve_dolphin.sync.planetary import MissingPlanetaryScopeError, PlanetarySyncService
from eve_dolphin.sync.planetary_repository import PlanetarySnapshotRepository

NOW = datetime(2026, 8, 30, 16, 0, tzinfo=UTC)
PLANETARY_SCOPE = "esi-planets.manage_planets.v1"
LAST_MODIFIED = "Sun, 30 Aug 2026 15:55:00 GMT"


class _TokenService:
    def __init__(self, scopes: tuple[str, ...] = (PLANETARY_SCOPE,)) -> None:
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
        self.invalid_planet: int | None = None
        self.calls: list[tuple[str, str | None, int | None]] = []

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str | int | bool] | None = None,
        access_token: str | None = None,
        character_id: int | None = None,
    ) -> EsiResponse:
        assert params is None
        self.calls.append((path, access_token, character_id))
        if path.endswith("/planets/"):
            payload: object = [_summary(character_id or 1, 4001), _summary(character_id or 1, 4002)]
        else:
            planet_id = int(path.rstrip("/").rsplit("/", 1)[1])
            payload = _layout(planet_id)
            if self.invalid_planet == planet_id:
                routes = payload["routes"]
                assert isinstance(routes, list)
                payload["routes"] = [routes[0], routes[0]]
        return EsiResponse(
            payload=payload,
            received_at=NOW,
            expires_at=NOW + timedelta(minutes=10),
            from_cache=False,
            not_modified=False,
            pages=None,
            etag='"planetary"',
            last_modified=LAST_MODIFIED,
        )


def test_sync_activates_complete_colony_layout_atomically(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7)
    token_service = _TokenService()
    esi_client = _EsiClient()
    repository = PlanetarySnapshotRepository(database)
    service = PlanetarySyncService(token_service, esi_client, repository, clock=lambda: NOW)

    result = service.sync(7, _metadata(), _config())

    assert result.refreshed is True
    assert result.snapshot.colony_count == 2
    assert result.snapshot.pin_count == 4
    assert result.snapshot.link_count == 2
    assert result.snapshot.route_count == 2
    assert result.snapshot.colonies_last_modified == LAST_MODIFIED
    assert esi_client.calls == [
        ("/characters/7/planets/", "token-7", 7),
        ("/characters/7/planets/4001/", "token-7", 7),
        ("/characters/7/planets/4002/", "token-7", 7),
    ]
    colonies = repository.current_colonies(7)
    assert [colony.planet_id for colony in colonies] == [4001, 4002]
    assert colonies[0].pins[0].contents[0].amount == 123
    assert colonies[0].pins[0].extractor_details is not None
    assert colonies[0].pins[0].extractor_details.head_radius == Decimal("0.0125")
    assert colonies[0].pins[1].extractor_details is not None
    assert colonies[0].pins[1].extractor_details.heads == ()
    assert colonies[0].routes[0].quantity == Decimal("12.75")
    assert colonies[0].routes[0].waypoints == (40012,)
    with database.connect() as connection:
        run = connection.execute(
            "SELECT sync_kind, status FROM sync_runs WHERE character_id = 7"
        ).fetchone()
    assert run is not None and tuple(run) == ("planetary", "succeeded")


def test_invalid_layout_preserves_previous_snapshot_and_other_character(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7)
    _link(database, 8)
    current = [NOW]
    esi_client = _EsiClient()
    repository = PlanetarySnapshotRepository(database)
    service = PlanetarySyncService(
        _TokenService(), esi_client, repository, clock=lambda: current[0]
    )
    first = service.sync(7, _metadata(), _config()).snapshot
    second = service.sync(8, _metadata(), _config()).snapshot
    current[0] = NOW + timedelta(minutes=11)
    esi_client.invalid_planet = 4002

    with pytest.raises(EsiProtocolError, match="duplicate route"):
        service.sync(7, _metadata(), _config())

    current_first = repository.current(7)
    current_second = repository.current(8)
    assert current_first is not None and current_first.snapshot_id == first.snapshot_id
    assert current_second is not None and current_second.snapshot_id == second.snapshot_id
    with database.connect() as connection:
        snapshots = connection.execute(
            "SELECT COUNT(*) FROM planetary_snapshots WHERE character_id = 7"
        ).fetchone()
        failed = connection.execute(
            """
            SELECT status, message FROM sync_runs
            WHERE character_id = 7 ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
    assert snapshots is not None and snapshots[0] == 1
    assert failed is not None and tuple(failed) == ("failed", "EsiProtocolError")


def test_persisted_ten_minute_cache_survives_service_restart(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7)
    token_service = _TokenService()
    esi_client = _EsiClient()
    repository = PlanetarySnapshotRepository(database)
    first = PlanetarySyncService(token_service, esi_client, repository, clock=lambda: NOW).sync(
        7, _metadata(), _config()
    )
    second = PlanetarySyncService(
        token_service,
        esi_client,
        PlanetarySnapshotRepository(database),
        clock=lambda: NOW + timedelta(minutes=9),
    ).sync(7, _metadata(), _config())

    assert second.refreshed is False
    assert second.snapshot.snapshot_id == first.snapshot.snapshot_id
    assert token_service.calls == 1
    assert len(esi_client.calls) == 3


def test_missing_planetary_scope_stops_before_esi_request(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _link(database, 7)
    esi_client = _EsiClient()
    service = PlanetarySyncService(
        _TokenService(()),
        esi_client,
        PlanetarySnapshotRepository(database),
        clock=lambda: NOW,
    )

    with pytest.raises(MissingPlanetaryScopeError) as caught:
        service.sync(7, _metadata(), _config())

    assert caught.value.missing_scopes == (PLANETARY_SCOPE,)
    assert esi_client.calls == []


def _summary(character_id: int, planet_id: int) -> dict[str, object]:
    return {
        "last_update": "2026-08-30T15:45:00Z",
        "num_pins": 2,
        "owner_id": character_id,
        "planet_id": planet_id,
        "planet_type": "barren",
        "solar_system_id": 30000142,
        "upgrade_level": 5,
    }


def _layout(planet_id: int) -> dict[str, object]:
    first_pin = planet_id * 10 + 1
    second_pin = planet_id * 10 + 2
    return {
        "pins": [
            {
                "pin_id": first_pin,
                "type_id": 2848,
                "latitude": Decimal("0.125"),
                "longitude": Decimal("-0.25"),
                "contents": [{"type_id": 2268, "amount": 123}],
                "extractor_details": {
                    "heads": [
                        {
                            "head_id": 0,
                            "latitude": Decimal("0.1"),
                            "longitude": Decimal("-0.2"),
                        }
                    ],
                    "cycle_time": 900,
                    "head_radius": Decimal("0.0125"),
                    "product_type_id": 2268,
                    "qty_per_cycle": 25,
                },
            },
            {
                "pin_id": second_pin,
                "type_id": 2473,
                "latitude": Decimal("0.5"),
                "longitude": Decimal("0.75"),
                "extractor_details": {"heads": []},
                "factory_details": {"schematic_id": 74},
            },
        ],
        "links": [
            {
                "source_pin_id": first_pin,
                "destination_pin_id": second_pin,
                "link_level": 3,
            }
        ],
        "routes": [
            {
                "route_id": planet_id * 100,
                "source_pin_id": first_pin,
                "destination_pin_id": second_pin,
                "content_type_id": 2268,
                "quantity": Decimal("12.75"),
                "waypoints": [second_pin],
            }
        ],
    }


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
            granted_scopes=(PLANETARY_SCOPE,),
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
