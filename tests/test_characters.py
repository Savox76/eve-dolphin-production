from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from eve_dolphin.characters import AuthorizationStatus, CharacterRepository, EveCharacter
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


def test_repository_marks_revoked_character_and_relink_resets_status(tmp_path: Path) -> None:
    database = Database(tmp_path / "client.sqlite3")
    database.initialize()
    repository = CharacterRepository(database)
    linked_at = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    character = EveCharacter(1001, "Industrial Pilot", "owner", (), linked_at)
    repository.upsert(character)

    failed_at = linked_at + timedelta(hours=1)
    assert repository.mark_reauthorization_required(1001, failed_at)
    revoked = repository.get(1001)

    assert revoked is not None
    assert revoked.authorization_status is AuthorizationStatus.REAUTHORIZATION_REQUIRED
    assert revoked.authorization_error_at == failed_at

    repository.upsert(character)
    assert repository.get(1001) == character
