from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from eve_dolphin.characters import AuthorizationStatus, CharacterRepository, EveCharacter
from eve_dolphin.database import Database
from eve_dolphin.i18n import Translator
from eve_dolphin.pi import (
    ColonyForecast,
    ColonyOverview,
    ForecastQuantity,
    NamedCount,
    NamedQuantity,
    PiCommodity,
    PiTier,
)
from eve_dolphin.sso.scopes import ScopePackage, scopes_for_packages
from eve_dolphin.sync.coordinator import CharacterSyncBatch, CharacterSyncOutcome
from eve_dolphin.ui.blueprint_page import BlueprintPage
from eve_dolphin.ui.character_page import (
    AUTOMATIC_SYNC_INTERVAL_MS,
    CharacterPage,
    CharacterSsoWorker,
)
from eve_dolphin.ui.main_window import SECTIONS, MainWindow
from eve_dolphin.ui.pi_planner_page import PiPlannerPage
from eve_dolphin.ui.planetary_page import PlanetaryPage
from eve_dolphin.updates import UpdateState, UpdateStateStatus


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
    assert isinstance(window.planetary_page, PlanetaryPage)
    assert window.planetary_page.property("viewId") == "pi-colonies"
    assert isinstance(window.pi_planner_page, PiPlannerPage)
    assert window.pi_planner_page.property("viewId") == "pi-planner"
    assert isinstance(window.blueprint_page, BlueprintPage)
    assert window.blueprint_page.property("viewId") == "blueprints"

    window.close()


def test_main_window_shows_successful_update_after_restart(
    qt_application: QApplication, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    result = UpdateState(
        UpdateStateStatus.SUCCEEDED,
        "0.3.1",
        datetime(2026, 8, 31, 12, 0, tzinfo=UTC),
    )

    window = MainWindow(
        tmp_path / "client.sqlite3",
        Translator("de"),
        repository,
        startup_update_result=result,
    )

    assert window.update_result_label.isVisibleTo(window)
    assert window.update_result_label.text() == "Update auf v0.3.1 erfolgreich installiert."
    window.close()


def test_planetary_page_shows_colony_status_and_sde_names(
    qt_application: QApplication, tmp_path: Path
) -> None:
    database = Database(tmp_path / "client.sqlite3", tmp_path / "backups")
    database.initialize()
    colony = _colony_overview()
    page = PlanetaryPage(
        database,
        Translator("de"),
        list_colonies=lambda language: (colony,) if language == "de" else (),
    )
    qt_application.processEvents()

    assert page.table.rowCount() == 1
    character_item = page.table.item(0, 0)
    planet_type_item = page.table.item(0, 2)
    extractor_item = page.table.item(0, 5)
    assert character_item is not None
    assert planet_type_item is not None
    assert extractor_item is not None
    assert character_item.text() == "Industrial Pilot"
    assert planet_type_item.text() == "gemäßigt"
    assert extractor_item.text() == "1 / 1 / 0"
    assert "Kolonien: 1 · Charaktere: 1" in page.summary_label.text()
    assert "Wässrige Flüssigkeiten x 2" in page.detail_label.text()
    assert "Water x 1,250" in page.detail_label.text()

    page.close()


def test_planetary_page_has_actionable_empty_state(
    qt_application: QApplication, tmp_path: Path
) -> None:
    database = Database(tmp_path / "client.sqlite3", tmp_path / "backups")
    database.initialize()
    page = PlanetaryPage(
        database,
        Translator("en"),
        list_colonies=lambda language: (),
    )

    assert page.table.rowCount() == 0
    assert "Connect a character with PI permission" in page.summary_label.text()
    assert page.detail_label.text() == page.summary_label.text()
    page.close()


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
    status_item = page.table.item(0, 2)
    assert status_item is not None
    assert status_item.text() == "Aktiv"
    assert not page.unlink_button.isEnabled()

    page.table.selectRow(0)
    qt_application.processEvents()
    assert page.unlink_button.isEnabled()

    page.unlink_button.click()
    qt_application.processEvents()
    assert page.table.rowCount() == 0
    assert repository.list_all() == ()

    page.close()


def test_settings_page_shows_reauthorization_required(
    qt_application: QApplication, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    failed_at = datetime(2026, 8, 30, 13, 0, tzinfo=UTC)
    repository.upsert(
        EveCharacter(
            1001,
            "Industrial Pilot",
            "owner",
            (),
            datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
            authorization_status=AuthorizationStatus.REAUTHORIZATION_REQUIRED,
            authorization_error_at=failed_at,
        )
    )

    page = CharacterPage(repository, Translator("en"))

    status_item = page.table.item(0, 2)
    assert status_item is not None
    assert status_item.text() == "Reconnect"

    page.close()


def test_settings_page_exposes_progressive_industry_and_pi_authorization(
    qt_application: QApplication, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    repository.upsert(
        EveCharacter(
            1001,
            "Industrial Pilot",
            "owner",
            (),
            datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
        )
    )
    page = CharacterPage(repository, Translator("de"))

    assert not page.industry_button.isEnabled()
    assert not page.planetary_button.isEnabled()
    page.table.selectRow(0)
    qt_application.processEvents()

    assert page.industry_button.isEnabled()
    assert page.planetary_button.isEnabled()
    assert page.industry_button.text() == "Industrie freigeben"
    assert page.planetary_button.text() == "PI freigeben"

    repository.upsert(
        EveCharacter(
            1001,
            "Industrial Pilot",
            "owner",
            scopes_for_packages(ScopePackage.INDUSTRY, ScopePackage.PLANETARY_INDUSTRY),
            datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
        )
    )
    page.refresh()
    page.table.selectRow(0)
    qt_application.processEvents()

    assert not page.industry_button.isEnabled()
    assert not page.planetary_button.isEnabled()
    page.close()


def test_settings_page_runs_multi_character_sync_in_background(
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
    page = CharacterPage(
        repository,
        Translator("en"),
        sync_characters=lambda: CharacterSyncBatch(
            (CharacterSyncOutcome(1001, ("industry", "industry_jobs", "planetary"), ()),)
        ),
    )

    assert page.sync_button.isEnabled()
    page.sync_button.click()
    for _attempt in range(100):
        qt_application.processEvents()
        if page.sync_button.isEnabled():
            break
        QThread.msleep(10)

    assert page.sync_button.isEnabled()
    assert page.status_label.text() == "EVE data for 1 character(s) is current."
    page.close()


def test_new_character_login_requests_every_supported_data_scope(
    qt_application: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = CharacterPage(_repository(tmp_path), Translator("de"))
    requested: list[tuple[tuple[str, ...], int | None]] = []

    def capture(scopes: tuple[str, ...], character_id: int | None) -> None:
        requested.append((scopes, character_id))

    monkeypatch.setattr(page, "_start_authorization", capture)

    page.connect_button.click()

    assert requested == [
        (
            scopes_for_packages(ScopePackage.INDUSTRY, ScopePackage.PLANETARY_INDUSTRY),
            None,
        )
    ]
    page.close()


def test_automatic_sync_starts_immediately_and_repeats_every_five_minutes(
    qt_application: QApplication, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    repository.upsert(
        EveCharacter(
            1001,
            "Industrial Pilot",
            None,
            scopes_for_packages(ScopePackage.INDUSTRY, ScopePackage.PLANETARY_INDUSTRY),
            datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
        )
    )
    calls: list[bool] = []

    def synchronize() -> CharacterSyncBatch:
        calls.append(True)
        return CharacterSyncBatch(
            (CharacterSyncOutcome(1001, ("industry", "industry_jobs", "planetary"), ()),)
        )

    page = CharacterPage(repository, Translator("de"), sync_characters=synchronize)
    page.start_automatic_sync()
    for _attempt in range(100):
        qt_application.processEvents()
        if calls and page.sync_button.isEnabled():
            break
        QThread.msleep(10)

    assert calls == [True]
    assert page._sync_timer.interval() == AUTOMATIC_SYNC_INTERVAL_MS
    assert "Nächste Prüfung in 5 Minuten" in page.status_label.text()
    page.stop_automatic_sync()
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


def test_main_window_shows_sde_and_character_data_freshness(
    qt_application: QApplication, tmp_path: Path
) -> None:
    database = Database(tmp_path / "client.sqlite3", tmp_path / "backups")
    database.initialize()
    repository = CharacterRepository(database)
    repository.upsert(
        EveCharacter(
            1001,
            "Industrial Pilot",
            None,
            (),
            datetime(2020, 1, 1, 12, 0, tzinfo=UTC),
        )
    )
    with database.connect() as connection, connection:
        connection.execute(
            """
            INSERT INTO industry_snapshots(
                character_id, fetched_at, asset_count, blueprint_count
            ) VALUES (1001, '2020-01-01T12:00:00+00:00', 1, 1)
            """
        )

    window = MainWindow(database, Translator("de"), repository)

    status = window.data_status_detail.text()
    assert "SDE · fehlt" in status
    assert "Industrial Pilot · Industrie: veraltet · Jobs: fehlt · PI: fehlt" in status
    window.close()


def test_character_login_reports_missing_public_client_id_without_blocking_ui(
    qt_application: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVE_SSO_CLIENT_ID", "")
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


def _colony_overview() -> ColonyOverview:
    return ColonyOverview(
        character_id=1001,
        character_name="Industrial Pilot",
        planet_id=4001,
        solar_system_id=30000142,
        solar_system_name="Jita",
        planet_name="Jita IV",
        security_status=Decimal("0.9459"),
        planet_type="temperate",
        snapshot_at=datetime(2026, 8, 30, 12, 5, tzinfo=UTC),
        last_update=datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
        upgrade_level=4,
        pin_count=5,
        link_count=2,
        route_count=1,
        factory_count=1,
        active_extractors=1,
        expired_extractors=1,
        incomplete_extractors=0,
        ending_soon_extractors=1,
        next_expiry=datetime(2026, 8, 30, 14, 0, tzinfo=UTC),
        next_attention=datetime(2026, 8, 30, 14, 0, tzinfo=UTC),
        data_age=timedelta(minutes=5),
        warning_codes=("extractors_ending_soon",),
        forecast=ColonyForecast(
            horizon=timedelta(hours=24),
            extractor_rates=(),
            extracted=(),
            factory_outputs=(
                ForecastQuantity(PiCommodity(3645, "Water", Decimal("0.38"), PiTier.BASIC), 40),
            ),
            projected_inventory=(),
            stalled_factories=0,
            constrained_factories=0,
            incomplete_factories=0,
            storage_used_m3=Decimal("475"),
            storage_capacity_m3=Decimal("12000"),
            storage_fill_percent=Decimal("3.9583"),
            estimated_full_at=None,
        ),
        pin_types=(NamedCount(2848, "Extraktorkontrolleinheit", 2),),
        extractor_products=(NamedCount(2268, "Wässrige Flüssigkeiten", 2),),
        stored_contents=(NamedQuantity(3645, "Water", 1_250),),
    )
