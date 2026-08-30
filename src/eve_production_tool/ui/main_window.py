"""Main navigation shell for the local client."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
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

from eve_production_tool.i18n import Translator


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

    def __init__(self, database_path: Path, translator: Translator | None = None) -> None:
        super().__init__()
        self.translator = translator or Translator("de")
        self.database_path = database_path
        self.navigation = QListWidget()
        self.pages = QStackedWidget()

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
        layout.addWidget(
            self._build_card(
                self.translator.text("no_characters"),
                self.translator.text("phase2_note"),
            )
        )
        layout.addStretch(1)
        return page

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
