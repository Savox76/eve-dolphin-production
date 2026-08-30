from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from eve_dolphin.characters import CharacterRepository, EveCharacter
from eve_dolphin.database import Database
from eve_dolphin.i18n import Translator
from eve_dolphin.ui.character_page import CharacterPage, CharacterSsoWorker
from eve_dolphin.ui.main_window import SECTIONS, MainWindow


@pytest.fixture(scope="session")
def qt_application() -> Iterator[QApplication]:
    application = QApplication.instance()
    owns_application = application is None
    if application is None:
        application = QApplication([])
    assert isinstance(application, QApplication)
    yield application
    if owns_application:
        application.quit()


def test_main_window_contains_all_planned_sections(
    qt_application: QApplication, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    window = MainWindow(tmp_path / "client.sqlite3", Translator("de"), repository)

    assert window.navigation.count() == len(SECTIONS) == 8
    assert window.pages.count() == len(SECTIONS)
    assert window.windowTitle() == "EVE Dolphin"

    window.close()


def test_navigation_switches_stacked_page(qt_application: QApplication, tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    window = MainWindow(tmp_path / "client.sqlite3", Translator("en"), repository)

    window.navigation.setCurrentRow(3)
    qt_application.processEvents()

    assert window.pages.currentIndex() == 3
    current_page = window.pages.currentWidget()
    assert current_page is not None
    assert current_page.property("viewId") == "projects"

    window.close()


def test_settings_page_lists_and_unlinks_local_character(
    qt_application: QApplication, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    character = EveCharacter(
        1001,
        "Industrial Pilot",
        "owner",
        ("scope-a", "scope-b"),
        datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
    )
    repository.upsert(character)
    page = CharacterPage(
        repository,
        Translator("de"),
        confirm_unlink=lambda selected: selected == character,
        unlink_character=repository.remove,
    )

    assert page.table.rowCount() == 1
    name_item = page.table.item(0, 0)
    scope_item = page.table.item(0, 1)
    assert name_item is not None
    assert scope_item is not None
    assert name_item.text() == "Industrial Pilot"
    assert scope_item.text() == "2"
    assert not page.unlink_button.isEnabled()

    page.table.selectRow(0)
    qt_application.processEvents()
    assert page.unlink_button.isEnabled()

    page.unlink_button.click()
    qt_application.processEvents()
    assert page.table.rowCount() == 0
    assert repository.list_all() == ()

    page.close()


def test_main_window_summary_uses_stored_character_count(
    qt_application: QApplication, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    repository.upsert(
        EveCharacter(
            1001,
            "Industrial Pilot",
            None,
            (),
            datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
        )
    )

    window = MainWindow(tmp_path / "client.sqlite3", Translator("de"), repository)

    assert window.character_summary_title.text() == "Verbundene EVE-Charaktere: 1"
    assert isinstance(window.character_page, CharacterPage)
    assert issubclass(CharacterSsoWorker, QThread)

    window.close()


def test_character_login_reports_missing_public_client_id_without_blocking_ui(
    qt_application: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EVE_SSO_CLIENT_ID", raising=False)
    page = CharacterPage(_repository(tmp_path), Translator("en"))

    page.connect_button.click()
    for _attempt in range(100):
        qt_application.processEvents()
        if page.connect_button.isEnabled():
            break
        QThread.msleep(10)

    assert page.connect_button.isEnabled()
    assert "public EVE client ID" in page.status_label.text()

    page.close()


def _repository(tmp_path: Path) -> CharacterRepository:
    database = Database(tmp_path / "client.sqlite3", tmp_path / "backups")
    database.initialize()
    return CharacterRepository(database)
