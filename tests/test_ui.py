from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication

from eve_production_tool.i18n import Translator
from eve_production_tool.ui.main_window import SECTIONS, MainWindow


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
    window = MainWindow(tmp_path / "client.sqlite3", Translator("de"))

    assert window.navigation.count() == len(SECTIONS) == 8
    assert window.pages.count() == len(SECTIONS)
    assert window.windowTitle() == "EVE Production Tool"

    window.close()


def test_navigation_switches_stacked_page(qt_application: QApplication, tmp_path: Path) -> None:
    window = MainWindow(tmp_path / "client.sqlite3", Translator("en"))

    window.navigation.setCurrentRow(3)
    qt_application.processEvents()

    assert window.pages.currentIndex() == 3
    current_page = window.pages.currentWidget()
    assert current_page is not None
    assert current_page.property("viewId") == "projects"

    window.close()
