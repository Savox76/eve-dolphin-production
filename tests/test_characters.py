from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from eve_dolphin.characters import CharacterRepository, EveCharacter
from eve_dolphin.database import Database


def test_repository_supports_multiple_characters_and_relinking(tmp_path: Path) -> None:
    database = Database(tmp_path / "client.sqlite3")
    database.initialize()
    repository = CharacterRepository(database)
    linked_at = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    first = EveCharacter(1002, "Zulu Pilot", None, ("scope-b",), linked_at)
    second = EveCharacter(1001, "Alpha Pilot", "owner", ("scope-a",), linked_at)

    repository.upsert(first)
    repository.upsert(second)

    assert repository.list_all() == (second, first)

    relinked = EveCharacter(
        1001,
        "Alpha Pilot Renamed",
        "new-owner",
        ("scope-a", "scope-c"),
        linked_at + timedelta(hours=1),
    )
    repository.upsert(relinked)

    assert repository.get(1001) == relinked
    assert repository.remove(1002)
    assert not repository.remove(1002)
    assert repository.list_all() == (relinked,)
