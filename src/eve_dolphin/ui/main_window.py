"""Main navigation shell for the local client."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from eve_dolphin.characters import CharacterRepository
from eve_dolphin.database import Database
from eve_dolphin.i18n import Translator
from eve_dolphin.status import DataStatusRepository, ResourceDataStatus
from eve_dolphin.sync.coordinator import CharacterSyncBatch
from eve_dolphin.ui.character_page import CharacterPage
from eve_dolphin.ui.pi_planner_page import PiPlannerPage
from eve_dolphin.ui.planetary_page import PlanetaryPage
from eve_dolphin.ui.update_dialog import (
    CheckForUpdate,
    StageUpdate,
    UpdateCheckWorker,
    UpdateDialog,
    UpdateStageWorker,
)
from eve_dolphin.updates import ReleaseInfo, StagedUpdate

LaunchUpdate = Callable[[StagedUpdate], None]


@dataclass(frozen=True, slots=True)
class Section:
    view_id: str
    translation_key: str


SECTIONS = (
    Section("overview", "overview"),
    Section("pi-colonies", "pi"),
    Section("pi-planner", "pi_planner"),
    Section("projects", "projects"),
    Section("blueprints", "blueprints"),
    Section("inventory", "inventory"),
    Section("market", "market"),
    Section("settings", "settings"),
)


class MainWindow(QMainWindow):
    """Desktop window with stable navigation and placeholder feature pages."""

    def __init__(
        self,
        database_path: Path | Database,
        translator: Translator,
        character_repository: CharacterRepository,
        sync_characters: Callable[[], CharacterSyncBatch] | None = None,
        current_version: str = "0.0.0",
        check_for_update: CheckForUpdate | None = None,
        stage_update: StageUpdate | None = None,
        launch_update: LaunchUpdate | None = None,
    ) -> None:
        super().__init__()
        self.translator = translator
        self.database = (
            database_path if isinstance(database_path, Database) else Database(database_path)
        )
        self.database_path = self.database.path
        self.data_status_repository = DataStatusRepository(self.database)
        self.character_repository = character_repository
        self.sync_characters = sync_characters
        self.current_version = current_version
        self._check_for_update = check_for_update
        self._stage_update = stage_update
        self._launch_update = launch_update
        self.navigation = QListWidget()
        self.pages = QStackedWidget()
        self.character_page: CharacterPage | None = None
        self.planetary_page: PlanetaryPage | None = None
        self.pi_planner_page: PiPlannerPage | None = None
        self._close_pending = False
        self._update_check_worker: UpdateCheckWorker | None = None
        self._update_stage_worker: UpdateStageWorker | None = None
        self._available_release: ReleaseInfo | None = None
        self._update_dialog: UpdateDialog | None = None
        self._update_notified = False
        self._manual_update_check = False

        self.setWindowTitle(self.translator.text("app.title"))
        self.setMinimumSize(960, 640)
        self.resize(1280, 800)
        self.setCentralWidget(self._build_central_widget())
        self.statusBar().showMessage(self.translator.text("local_data"))

        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.setCurrentRow(0)

    def _build_central_widget(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_pages(), 1)
        return container

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 12, 16)
        layout.setSpacing(6)

        product_name = QLabel(self.translator.text("app.title"))
        product_name.setObjectName("productName")
        product_subtitle = QLabel(self.translator.text("app.subtitle"))
        product_subtitle.setObjectName("productSubtitle")

        self.navigation.setObjectName("navigation")
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.navigation.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        for section in SECTIONS:
            item = QListWidgetItem(self.translator.text(section.translation_key))
            item.setData(Qt.ItemDataRole.UserRole, section.view_id)
            self.navigation.addItem(item)

        layout.addWidget(product_name)
        layout.addWidget(product_subtitle)
        layout.addSpacing(18)
        layout.addWidget(self.navigation, 1)
        self.version_label = QLabel(
            self.translator.text("app_version").format(version=self.current_version)
        )
        self.version_label.setObjectName("productSubtitle")
        self.update_button = QPushButton(self.translator.text("check_for_updates"))
        self.update_button.setObjectName("checkUpdateButton")
        self.update_button.setEnabled(self._check_for_update is not None)
        self.update_button.clicked.connect(self._show_or_check_update)
        layout.addWidget(self.version_label)
        layout.addWidget(self.update_button)
        return sidebar

    def _build_pages(self) -> QStackedWidget:
        for index, section in enumerate(SECTIONS):
            if index == 0:
                page = self._build_overview_page()
            elif section.view_id == "pi-colonies":
                self.planetary_page = PlanetaryPage(self.database, self.translator)
                page = self.planetary_page
            elif section.view_id == "pi-planner":
                self.pi_planner_page = PiPlannerPage(self.database, self.translator)
                page = self.pi_planner_page
            elif section.view_id == "settings":
                self.character_page = CharacterPage(
                    self.character_repository,
                    self.translator,
                    sync_characters=self.sync_characters,
                )
                self.character_page.characters_changed.connect(self._refresh_character_summary)
                self.character_page.characters_changed.connect(self._refresh_data_status)
                self.character_page.data_changed.connect(self._refresh_data_status)
                if self.planetary_page is not None:
                    self.character_page.characters_changed.connect(self.planetary_page.refresh)
                    self.character_page.data_changed.connect(self.planetary_page.refresh)
                if self.pi_planner_page is not None:
                    self.character_page.characters_changed.connect(self.pi_planner_page.refresh)
                    self.character_page.data_changed.connect(self.pi_planner_page.refresh)
                page = self.character_page
            else:
                page = self._build_placeholder_page(section)
            page.setProperty("viewId", section.view_id)
            self.pages.addWidget(page)
        return self.pages

    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(18)

        eyebrow = QLabel(self.translator.text("app.subtitle").upper())
        eyebrow.setObjectName("eyebrow")
        title = QLabel(self.translator.text("overview"))
        title.setObjectName("pageTitle")
        badge = QLabel(self.translator.text("foundation_ready"))
        badge.setObjectName("statusBadge")
        badge.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(badge)
        layout.addSpacing(8)
        summary_card = self._build_card("", "")
        summary_title = summary_card.findChild(QLabel, "cardTitle")
        summary_detail = summary_card.findChild(QLabel, "muted")
        assert summary_title is not None
        assert summary_detail is not None
        self.character_summary_title = summary_title
        self.character_summary_detail = summary_detail
        layout.addWidget(summary_card)
        status_card = self._build_card(self.translator.text("data_status"), "")
        status_detail = status_card.findChild(QLabel, "muted")
        assert status_detail is not None
        self.data_status_detail = status_detail
        layout.addWidget(status_card)
        layout.addStretch(1)
        self._refresh_character_summary()
        self._refresh_data_status()
        return page

    def _refresh_character_summary(self) -> None:
        characters = self.character_repository.list_all()
        if characters:
            title = self.translator.text("character_count").format(count=len(characters))
            detail = self.translator.text("characters_ready")
        else:
            title = self.translator.text("no_characters")
            detail = self.translator.text("phase2_note")
        self.character_summary_title.setText(title)
        self.character_summary_detail.setText(detail)

    def _refresh_data_status(self) -> None:
        overview = self.data_status_repository.overview()
        state = self.translator.text(f"data_{overview.sde.state.value}")
        if overview.sde.build_number is None or overview.sde.release_date is None:
            lines = [f"SDE · {state}"]
        else:
            lines = [
                self.translator.text("sde_status").format(
                    build=overview.sde.build_number,
                    state=state,
                    date=overview.sde.release_date.astimezone(UTC).strftime("%Y-%m-%d"),
                )
            ]
        for character in overview.characters:
            lines.append(
                " · ".join(
                    (
                        character.character_name,
                        self._resource_status_text("resource_industry", character.industry),
                        self._resource_status_text("resource_jobs", character.jobs),
                        self._resource_status_text("resource_planetary", character.planetary),
                    )
                )
            )
        self.data_status_detail.setText("\n".join(lines))

    def _resource_status_text(self, name_key: str, status: ResourceDataStatus) -> str:
        name = self.translator.text(name_key)
        state = self.translator.text(f"data_{status.state.value}")
        return f"{name}: {state}"

    def _build_placeholder_page(self, section: Section) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(18)

        title = QLabel(self.translator.text(section.translation_key))
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(
            self._build_card(
                self.translator.text("foundation_ready"),
                self.translator.text("phase2_note"),
            )
        )
        layout.addStretch(1)
        return page

    @staticmethod
    def _build_card(title_text: str, detail_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        title = QLabel(title_text)
        title.setObjectName("cardTitle")
        detail = QLabel(detail_text)
        detail.setObjectName("muted")
        detail.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(detail)
        return card

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.character_page is not None:
            self.character_page.stop_automatic_sync()
        pending_worker = self._pending_update_worker()
        character_pending = (
            self.character_page is not None and self.character_page.background_work_pending
        )
        if character_pending or pending_worker is not None:
            if not self._close_pending:
                self._close_pending = True
                if character_pending and self.character_page is not None:
                    self.character_page.authorization_stopped.connect(self.close)
                if pending_worker is not None:
                    pending_worker.finished.connect(self.close)
            if character_pending and self.character_page is not None:
                self.character_page.cancel_pending_authorization()
            if pending_worker is not None:
                pending_worker.requestInterruption()
            event.ignore()
            return
        super().closeEvent(event)

    def start_background_services(self) -> None:
        if self.character_page is not None:
            self.character_page.start_automatic_sync()
        self._start_update_check(automatic=True)

    def _pending_update_worker(self) -> QThread | None:
        if self._update_stage_worker is not None:
            return self._update_stage_worker
        return self._update_check_worker

    def _show_or_check_update(self) -> None:
        if self._available_release is not None:
            self._show_update_dialog(self._available_release)
            return
        self._start_update_check(automatic=False)

    def _start_update_check(self, *, automatic: bool) -> None:
        if self._check_for_update is None or self._update_check_worker is not None:
            return
        self._manual_update_check = not automatic
        self.update_button.setEnabled(False)
        self.update_button.setText(self.translator.text("checking_for_updates"))
        worker = UpdateCheckWorker(self._check_for_update, self)
        self._update_check_worker = worker
        worker.completed.connect(self._update_check_completed)
        worker.failed.connect(self._update_check_failed)
        worker.finished.connect(self._update_check_finished)
        worker.start()

    def _update_check_completed(self, result: object) -> None:
        if isinstance(result, ReleaseInfo):
            self._available_release = result
            self.update_button.setText(
                self.translator.text("update_button_available").format(version=str(result.version))
            )
            self.update_button.setEnabled(True)
            if not self._update_notified and not self._close_pending:
                self._update_notified = True
                self._show_update_dialog(result)
            return
        self.update_button.setText(self.translator.text("check_for_updates"))
        self.update_button.setEnabled(True)
        if self._manual_update_check:
            QMessageBox.information(
                self,
                self.translator.text("updates_title"),
                self.translator.text("update_current"),
            )

    def _update_check_failed(self) -> None:
        self.update_button.setText(self.translator.text("check_for_updates"))
        self.update_button.setEnabled(True)
        if self._manual_update_check:
            QMessageBox.warning(
                self,
                self.translator.text("updates_title"),
                self.translator.text("update_check_failed"),
            )

    def _update_check_finished(self) -> None:
        worker = self._update_check_worker
        self._update_check_worker = None
        if worker is not None:
            worker.deleteLater()

    def _show_update_dialog(self, release: ReleaseInfo) -> None:
        if self._update_dialog is not None:
            self._update_dialog.raise_()
            self._update_dialog.activateWindow()
            return
        dialog = UpdateDialog(
            release,
            self.current_version,
            self.translator,
            installation_enabled=(
                self._stage_update is not None and self._launch_update is not None
            ),
            parent=self,
        )
        self._update_dialog = dialog
        dialog.start_requested.connect(self._start_update_install)
        dialog.finished.connect(self._update_dialog_finished)
        dialog.show()

    def _update_dialog_finished(self) -> None:
        self._update_dialog = None

    def _start_update_install(self) -> None:
        if (
            self._available_release is None
            or self._stage_update is None
            or self._update_stage_worker is not None
        ):
            return
        if self._update_dialog is not None:
            self._update_dialog.set_installing()
        worker = UpdateStageWorker(self._stage_update, self._available_release, self)
        self._update_stage_worker = worker
        worker.completed.connect(self._update_staged)
        worker.failed.connect(self._update_stage_failed)
        worker.finished.connect(self._update_stage_finished)
        worker.start()

    def _update_staged(self, result: object) -> None:
        if (
            not isinstance(result, StagedUpdate)
            or self._launch_update is None
            or self._close_pending
        ):
            return
        try:
            self._launch_update(result)
        except Exception:
            self._update_stage_failed()
            return
        if self.character_page is not None:
            self.character_page.stop_automatic_sync()
        application = QApplication.instance()
        if application is not None:
            application.quit()

    def _update_stage_failed(self) -> None:
        if self._update_dialog is not None:
            self._update_dialog.set_failed()

    def _update_stage_finished(self) -> None:
        worker = self._update_stage_worker
        self._update_stage_worker = None
        if worker is not None:
            worker.deleteLater()
