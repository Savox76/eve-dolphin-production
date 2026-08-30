"""Main navigation shell for the local client."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from eve_dolphin.characters import CharacterRepository
from eve_dolphin.i18n import Translator
from eve_dolphin.ui.character_page import CharacterPage


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
        database_path: Path,
        translator: Translator,
        character_repository: CharacterRepository,
    ) -> None:
        super().__init__()
        self.translator = translator
        self.database_path = database_path
        self.character_repository = character_repository
        self.navigation = QListWidget()
        self.pages = QStackedWidget()
        self.character_page: CharacterPage | None = None
        self._close_pending = False

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
        return sidebar

    def _build_pages(self) -> QStackedWidget:
        for index, section in enumerate(SECTIONS):
            if index == 0:
                page = self._build_overview_page()
            elif section.view_id == "settings":
                self.character_page = CharacterPage(
                    self.character_repository,
                    self.translator,
                )
                self.character_page.characters_changed.connect(self._refresh_character_summary)
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
        layout.addStretch(1)
        self._refresh_character_summary()
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
        if self.character_page is not None and self.character_page.authorization_pending:
            if not self._close_pending:
                self._close_pending = True
                self.character_page.authorization_stopped.connect(self.close)
            self.character_page.cancel_pending_authorization()
            event.ignore()
            return
        super().closeEvent(event)
