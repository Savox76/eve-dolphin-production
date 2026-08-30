"""Visible cross-character overview of synchronized PI colonies."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eve_dolphin.database import Database
from eve_dolphin.i18n import Translator
from eve_dolphin.pi import ColonyOverview, NamedCount, NamedQuantity, PlanetaryOverviewService

ListColonies = Callable[[str], tuple[ColonyOverview, ...]]


class PlanetaryPage(QWidget):
    """Show the latest complete PI snapshot for every connected character."""

    def __init__(
        self,
        database: Database,
        translator: Translator,
        *,
        list_colonies: ListColonies | None = None,
    ) -> None:
        super().__init__()
        self._translator = translator
        self._list_colonies = list_colonies or PlanetaryOverviewService(database).list_colonies
        self._colonies: tuple[ColonyOverview, ...] = ()

        self.summary_label = QLabel()
        self.summary_label.setObjectName("planetarySummary")
        self.summary_label.setWordWrap(True)
        self.table = QTableWidget(0, 8)
        self.table.setObjectName("planetaryColonyTable")
        self.detail_label = QLabel()
        self.detail_label.setObjectName("muted")
        self.detail_label.setWordWrap(True)

        self._build_layout()
        self.table.itemSelectionChanged.connect(self._update_detail)
        self.refresh()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(18)

        title = QLabel(self._translator.text("pi"))
        title.setObjectName("pageTitle")
        detail = QLabel(self._translator.text("pi_overview_detail"))
        detail.setObjectName("muted")
        detail.setWordWrap(True)

        overview_card = QFrame()
        overview_card.setObjectName("card")
        overview_layout = QVBoxLayout(overview_card)
        overview_layout.setContentsMargins(20, 18, 20, 18)
        overview_layout.setSpacing(12)
        overview_title = QLabel(self._translator.text("pi_colonies"))
        overview_title.setObjectName("cardTitle")

        self.table.setHorizontalHeaderLabels(
            (
                self._translator.text("pi_character"),
                self._translator.text("pi_planet"),
                self._translator.text("pi_planet_type"),
                self._translator.text("pi_system"),
                self._translator.text("pi_pins"),
                self._translator.text("pi_extractors"),
                self._translator.text("pi_factories"),
                self._translator.text("pi_last_update"),
            )
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

        overview_layout.addWidget(overview_title)
        overview_layout.addWidget(self.summary_label)
        overview_layout.addWidget(self.table, 1)

        detail_card = QFrame()
        detail_card.setObjectName("card")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(20, 18, 20, 18)
        detail_layout.setSpacing(8)
        detail_title = QLabel(self._translator.text("pi_colony_details"))
        detail_title.setObjectName("cardTitle")
        detail_layout.addWidget(detail_title)
        detail_layout.addWidget(self.detail_label)

        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addWidget(overview_card, 1)
        layout.addWidget(detail_card)

    def refresh(self) -> None:
        """Reload the overview after an atomic synchronization or character change."""

        self._colonies = self._list_colonies(self._translator.language)
        self.table.setRowCount(len(self._colonies))
        for row, colony in enumerate(self._colonies):
            values = (
                colony.character_name,
                str(colony.planet_id),
                self._planet_type(colony.planet_type),
                str(colony.solar_system_id),
                str(colony.pin_count),
                self._extractor_status(colony),
                str(colony.factory_count),
                _format_datetime(colony.last_update),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {1, 3, 4, 6}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)

        self._update_summary()
        if self._colonies:
            self.table.selectRow(0)
        else:
            self.detail_label.setText(self._translator.text("pi_no_colonies"))

    def _update_summary(self) -> None:
        if not self._colonies:
            self.summary_label.setText(self._translator.text("pi_no_colonies"))
            return
        self.summary_label.setText(
            self._translator.text("pi_summary").format(
                colonies=len(self._colonies),
                characters=len({colony.character_id for colony in self._colonies}),
                active=sum(colony.active_extractors for colony in self._colonies),
                expired=sum(colony.expired_extractors for colony in self._colonies),
                incomplete=sum(colony.incomplete_extractors for colony in self._colonies),
            )
        )

    def _update_detail(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._colonies):
            self.detail_label.setText(self._translator.text("pi_no_selection"))
            return
        colony = self._colonies[row]
        next_expiry = (
            _format_datetime(colony.next_expiry)
            if colony.next_expiry is not None
            else self._translator.text("pi_none")
        )
        self.detail_label.setText(
            "\n".join(
                (
                    self._translator.text("pi_identity_detail").format(
                        character=colony.character_name,
                        planet=colony.planet_id,
                        planet_type=self._planet_type(colony.planet_type),
                        system=colony.solar_system_id,
                        level=colony.upgrade_level,
                    ),
                    self._translator.text("pi_layout_detail").format(
                        pins=colony.pin_count,
                        links=colony.link_count,
                        routes=colony.route_count,
                        factories=colony.factory_count,
                    ),
                    self._translator.text("pi_extractor_detail").format(
                        active=colony.active_extractors,
                        expired=colony.expired_extractors,
                        incomplete=colony.incomplete_extractors,
                        next_expiry=next_expiry,
                    ),
                    self._translator.text("pi_pin_types_detail").format(
                        values=self._format_counts(colony.pin_types)
                    ),
                    self._translator.text("pi_extractor_products_detail").format(
                        values=self._format_counts(colony.extractor_products)
                    ),
                    self._translator.text("pi_storage_detail").format(
                        values=self._format_quantities(colony.stored_contents)
                    ),
                    self._translator.text("pi_snapshot_detail").format(
                        snapshot=_format_datetime(colony.snapshot_at)
                    ),
                )
            )
        )

    def _extractor_status(self, colony: ColonyOverview) -> str:
        return self._translator.text("pi_extractor_compact").format(
            active=colony.active_extractors,
            expired=colony.expired_extractors,
            incomplete=colony.incomplete_extractors,
        )

    def _planet_type(self, planet_type: str) -> str:
        return self._translator.text(f"planet_type_{planet_type}")

    def _format_counts(self, values: tuple[NamedCount, ...]) -> str:
        if not values:
            return self._translator.text("pi_none")
        return ", ".join(
            f"{self._type_name(value.type_id, value.name)} x {value.count}" for value in values
        )

    def _format_quantities(self, values: tuple[NamedQuantity, ...]) -> str:
        if not values:
            return self._translator.text("pi_none")
        return ", ".join(
            f"{self._type_name(value.type_id, value.name)} x {value.quantity:,}" for value in values
        )

    def _type_name(self, type_id: int, name: str | None) -> str:
        return name or self._translator.text("pi_unknown_type").format(type_id=type_id)


def _format_datetime(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")
