from __future__ import annotations

from pathlib import Path

import pytest

import eve_dolphin.sync.runtime as runtime_module
from eve_dolphin.characters import CharacterRepository
from eve_dolphin.database import Database
from eve_dolphin.status import DataFreshness, DataStatusRepository
from eve_dolphin.sync.runtime import PhaseTwoSyncRunner


class _FakeSdeClient:
    closed = False

    def close(self) -> None:
        type(self).closed = True


class _SuccessfulUpdateService:
    def __init__(self, *args: object) -> None:
        pass

    def update(self) -> object:
        return object()


class _FailingUpdateService(_SuccessfulUpdateService):
    def update(self) -> object:
        raise RuntimeError("download failed")


def test_runtime_updates_sde_even_without_linked_characters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = _database(tmp_path)
    _FakeSdeClient.closed = False
    monkeypatch.setattr(runtime_module, "EveSdeClient", _FakeSdeClient)
    monkeypatch.setattr(runtime_module, "SdeUpdateService", _SuccessfulUpdateService)

    batch = PhaseTwoSyncRunner(database, CharacterRepository(database), tmp_path / "sde").sync_all()

    assert batch.outcomes == ()
    assert batch.global_failures == ()
    assert _FakeSdeClient.closed is True
    with database.connect() as connection:
        run = connection.execute(
            "SELECT status, message FROM sync_runs WHERE sync_kind = 'sde'"
        ).fetchone()
    assert run is not None and tuple(run) == ("succeeded", None)


def test_runtime_records_sde_download_failure_and_keeps_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = _database(tmp_path)
    monkeypatch.setattr(runtime_module, "EveSdeClient", _FakeSdeClient)
    monkeypatch.setattr(runtime_module, "SdeUpdateService", _FailingUpdateService)

    batch = PhaseTwoSyncRunner(database, CharacterRepository(database), tmp_path / "sde").sync_all()

    assert batch.global_failures == ("RuntimeError",)
    assert DataStatusRepository(database).overview().sde.state is DataFreshness.FAILED


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "eve-dolphin.sqlite3")
    database.initialize()
    return database
