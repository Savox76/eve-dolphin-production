"""Visible cross-character overview of synchronized PI colonies."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eve_dolphin.database import Database
from eve_dolphin.i18n import Translator
from eve_dolphin.pi import (
    ColonyOverview,
    ForecastQuantity,
    NamedCount,
    NamedQuantity,
    PlanetaryOverviewService,
)

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
        self.table = QTableWidget(0, 11)
        self.table.setObjectName("planetaryColonyTable")
        self.detail_label = QLabel()
        self.detail_label.setObjectName("muted")
        self.detail_label.setWordWrap(True)
        self.operation_label = QLabel()
        self.operation_label.setObjectName("statusBadge")
        self.countdown_label = QLabel()
        self.countdown_label.setObjectName("piCountdown")
        self.storage_table = QTableWidget(0, 4)
        self.storage_table.setObjectName("piStorageTable")

        self._build_layout()
        self.table.itemSelectionChanged.connect(self._update_detail)
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._update_countdown)
        self._countdown_timer.start()
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
                self._translator.text("pi_status"),
                self._translator.text("pi_storage"),
                self._translator.text("pi_next_attention"),
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
        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(self.operation_label)
        status_layout.addWidget(self.countdown_label, 1)
        detail_layout.addWidget(status_row)
        detail_layout.addWidget(self.detail_label)

        self.storage_table.setHorizontalHeaderLabels(
            (
                self._translator.text("pi_storage_pin"),
                self._translator.text("pi_storage_contents"),
                self._translator.text("pi_storage_volume"),
                self._translator.text("pi_storage_fill"),
            )
        )
        self.storage_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.storage_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.storage_table.verticalHeader().setVisible(False)
        storage_header = self.storage_table.horizontalHeader()
        storage_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        storage_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        detail_layout.addWidget(self.storage_table)

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
                colony.planet_name or str(colony.planet_id),
                self._planet_type(colony.planet_type),
                colony.solar_system_name or str(colony.solar_system_id),
                str(colony.pin_count),
                self._extractor_status(colony),
                str(colony.factory_count),
                _format_datetime(colony.last_update),
                self._warning_text(colony),
                self._storage_text(colony),
                (
                    _format_datetime(colony.next_attention)
                    if colony.next_attention is not None
                    else self._translator.text("pi_none")
                ),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {1, 3, 4, 6}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
            self._color_attention_row(row, colony)

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
        self.operation_label.setText(
            self._translator.text(f"pi_mode_{colony.operation_mode.value}")
        )
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
                        planet=colony.planet_name or colony.planet_id,
                        planet_type=self._planet_type(colony.planet_type),
                        system=colony.solar_system_name or colony.solar_system_id,
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
                    self._translator.text("pi_extractor_rate_detail").format(
                        values=self._format_rates(colony)
                    ),
                    self._translator.text("pi_factory_forecast_detail").format(
                        values=self._format_forecast_quantities(colony.forecast.factory_outputs),
                        stalled=colony.forecast.stalled_factories,
                        constrained=colony.forecast.constrained_factories,
                    ),
                    self._translator.text("pi_storage_forecast_detail").format(
                        used=_format_decimal(colony.forecast.storage_used_m3),
                        capacity=_format_decimal(colony.forecast.storage_capacity_m3),
                        percent=(
                            _format_decimal(colony.forecast.storage_fill_percent)
                            if colony.forecast.storage_fill_percent is not None
                            else self._translator.text("pi_unknown")
                        ),
                        full=(
                            _format_datetime(colony.forecast.estimated_full_at)
                            if colony.forecast.estimated_full_at is not None
                            else self._translator.text("pi_none")
                        ),
                    ),
                    self._translator.text("pi_data_age_detail").format(
                        age=_format_duration(colony.data_age),
                        status=self._warning_text(colony),
                    ),
                    self._translator.text("pi_snapshot_detail").format(
                        snapshot=_format_datetime(colony.snapshot_at)
                    ),
                )
            )
        )
        self._show_storage(colony)
        self._update_countdown()

    def _show_storage(self, colony: ColonyOverview) -> None:
        self.storage_table.setRowCount(len(colony.storage_nodes))
        for row, storage in enumerate(colony.storage_nodes):
            contents = self._format_quantities(storage.contents)
            values = (
                f"{storage.name or storage.type_id} · #{storage.pin_id}",
                contents,
                f"{_format_decimal(storage.used_m3)} / {_format_decimal(storage.capacity_m3)} m³",
            )
            for column, value in enumerate(values):
                self.storage_table.setItem(row, column, QTableWidgetItem(value))
            progress = QProgressBar()
            progress.setRange(0, 1000)
            progress.setValue(int(storage.fill_percent * 10))
            progress.setFormat(f"{_format_decimal(storage.fill_percent)} %")
            if storage.fill_percent >= Decimal(90):
                progress.setStyleSheet("QProgressBar::chunk { background-color: #ef4444; }")
            self.storage_table.setCellWidget(row, 3, progress)
        self.storage_table.setVisible(bool(colony.storage_nodes))

    def _update_countdown(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._colonies):
            self.countdown_label.clear()
            return
        colony = self._colonies[row]
        deadline = colony.next_expiry
        key = "pi_countdown_extractor"
        if colony.operation_mode.value == "import":
            deadline = colony.supply_exhausted_at
            key = "pi_countdown_supply"
        if deadline is None:
            self.countdown_label.setText(self._translator.text("pi_countdown_unknown"))
            self.countdown_label.setStyleSheet("")
            return
        remaining = max(timedelta(0), deadline - datetime.now(deadline.tzinfo))
        self.countdown_label.setText(
            self._translator.text(key).format(remaining=_format_countdown(remaining))
        )
        urgent = remaining < timedelta(hours=10)
        self.countdown_label.setStyleSheet(
            "color: #ff6b6b; font-weight: 700;" if urgent else "color: #8ff0cf;"
        )

    def _color_attention_row(self, row: int, colony: ColonyOverview) -> None:
        if colony.attention_remaining is None:
            return
        color = QColor("#ff6b6b" if colony.attention_remaining < timedelta(hours=10) else "#fbbf24")
        for column in (8, 10):
            item = self.table.item(row, column)
            if item is not None:
                item.setForeground(color)

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

    def _warning_text(self, colony: ColonyOverview) -> str:
        if not colony.warning_codes:
            return self._translator.text("pi_status_current")
        return ", ".join(
            self._translator.text(f"pi_warning_{code}") for code in colony.warning_codes
        )

    def _storage_text(self, colony: ColonyOverview) -> str:
        percent = colony.forecast.storage_fill_percent
        if percent is None:
            return self._translator.text("pi_unknown")
        return f"{_format_decimal(percent)} %"

    def _format_rates(self, colony: ColonyOverview) -> str:
        if not colony.forecast.extractor_rates:
            return self._translator.text("pi_none")
        return ", ".join(
            self._translator.text("pi_rate_value").format(
                name=value.commodity.name,
                hourly=_format_decimal(value.units_per_hour),
                daily=_format_decimal(value.units_per_hour * 24),
            )
            for value in colony.forecast.extractor_rates
        )

    def _format_forecast_quantities(self, values: tuple[ForecastQuantity, ...]) -> str:
        if not values:
            return self._translator.text("pi_none")
        return ", ".join(f"{value.commodity.name} x {value.quantity:,}" for value in values)


def _format_datetime(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def _format_duration(value: timedelta) -> str:
    seconds = max(0, int(value.total_seconds()))
    if seconds >= 86400:
        return f"{seconds / 86400:.1f} d"
    if seconds >= 3600:
        return f"{seconds / 3600:.1f} h"
    return f"{seconds // 60} min"


def _format_countdown(value: timedelta) -> str:
    seconds = max(0, int(value.total_seconds()))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    prefix = f"{days}d " if days else ""
    return f"{prefix}{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):,.2f}"
