"""Owned blueprint catalog and first classical manufacturing calculator."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eve_dolphin.database import Database
from eve_dolphin.i18n import Translator
from eve_dolphin.manufacturing import (
    BlueprintKind,
    ManufacturingPlan,
    ManufacturingPlannerService,
    OwnedManufacturingBlueprint,
)


class BlueprintPage(QWidget):
    def __init__(
        self,
        database: Database,
        translator: Translator,
        *,
        planner: ManufacturingPlannerService | None = None,
    ) -> None:
        super().__init__()
        self._translator = translator
        self._planner = planner or ManufacturingPlannerService(database)
        self._blueprints: tuple[OwnedManufacturingBlueprint, ...] = ()
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(16)

        title = QLabel(self._translator.text("blueprints"))
        title.setObjectName("pageTitle")
        detail = QLabel(self._translator.text("blueprint_page_detail"))
        detail.setObjectName("muted")
        detail.setWordWrap(True)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self._translator.text("blueprint_search"))
        self.search_input.textChanged.connect(self._apply_filter)

        self.blueprint_table = QTableWidget(0, 8)
        self.blueprint_table.setHorizontalHeaderLabels(
            [
                self._translator.text("blueprint_product"),
                self._translator.text("blueprint_owner"),
                self._translator.text("blueprint_kind"),
                "ME",
                "TE",
                self._translator.text("blueprint_runs"),
                self._translator.text("blueprint_location"),
                self._translator.text("blueprint_name"),
            ]
        )
        self.blueprint_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.blueprint_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.blueprint_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.blueprint_table.verticalHeader().setVisible(False)
        header = self.blueprint_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.blueprint_table.itemSelectionChanged.connect(self._selection_changed)

        planner_card = QFrame()
        planner_card.setObjectName("card")
        planner_layout = QVBoxLayout(planner_card)
        planner_layout.setContentsMargins(20, 18, 20, 18)
        planner_layout.setSpacing(10)
        planner_title = QLabel(self._translator.text("manufacturing_calculation"))
        planner_title.setObjectName("cardTitle")
        controls = QHBoxLayout()
        target_label = QLabel(self._translator.text("manufacturing_target_quantity"))
        self.target_input = QSpinBox()
        self.target_input.setRange(1, 1_000_000_000)
        self.target_input.setValue(1)
        self.calculate_button = QPushButton(self._translator.text("manufacturing_calculate"))
        self.calculate_button.clicked.connect(self._calculate)
        controls.addWidget(target_label)
        controls.addWidget(self.target_input)
        controls.addWidget(self.calculate_button)
        controls.addStretch(1)
        self.plan_summary = QLabel(self._translator.text("manufacturing_select_blueprint"))
        self.plan_summary.setObjectName("muted")
        self.plan_summary.setWordWrap(True)
        self.material_table = QTableWidget(0, 5)
        self.material_table.setHorizontalHeaderLabels(
            [
                self._translator.text("manufacturing_material"),
                self._translator.text("manufacturing_required"),
                self._translator.text("manufacturing_at_location"),
                self._translator.text("manufacturing_total"),
                self._translator.text("manufacturing_missing_local"),
            ]
        )
        self.material_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.material_table.verticalHeader().setVisible(False)
        material_header = self.material_table.horizontalHeader()
        material_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        material_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        planner_layout.addWidget(planner_title)
        planner_layout.addLayout(controls)
        planner_layout.addWidget(self.plan_summary)
        planner_layout.addWidget(self.material_table)

        self.empty_label = QLabel("")
        self.empty_label.setObjectName("muted")
        self.empty_label.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addWidget(self.search_input)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.blueprint_table, 1)
        layout.addWidget(planner_card, 1)

    def refresh(self) -> None:
        selected_id = self._selected_blueprint_id()
        self._blueprints = self._planner.list_blueprints(self._translator.language)
        self.blueprint_table.setRowCount(len(self._blueprints))
        for row_index, blueprint in enumerate(self._blueprints):
            values = (
                blueprint.product_name,
                blueprint.character_name,
                self._kind_text(blueprint.kind),
                str(blueprint.material_efficiency),
                str(blueprint.time_efficiency),
                (
                    self._translator.text("blueprint_unlimited")
                    if blueprint.available_runs is None
                    else str(blueprint.available_runs)
                ),
                str(blueprint.location_id),
                blueprint.blueprint_name,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, blueprint.item_id)
                self.blueprint_table.setItem(row_index, column, item)
        has_blueprints = bool(self._blueprints)
        self.empty_label.setText("" if has_blueprints else self._translator.text("blueprint_empty"))
        self.blueprint_table.setVisible(has_blueprints)
        self.calculate_button.setEnabled(has_blueprints)
        self.target_input.setEnabled(has_blueprints)
        self._apply_filter()
        if has_blueprints:
            row = next(
                (
                    index
                    for index, blueprint in enumerate(self._blueprints)
                    if blueprint.item_id == selected_id
                ),
                0,
            )
            self.blueprint_table.selectRow(row)
            self._calculate()
        else:
            self.material_table.setRowCount(0)
            self.plan_summary.setText(self._translator.text("manufacturing_select_blueprint"))

    def _apply_filter(self) -> None:
        query = self.search_input.text().strip().casefold()
        for row, blueprint in enumerate(self._blueprints):
            haystack = " ".join(
                (
                    blueprint.product_name,
                    blueprint.blueprint_name,
                    blueprint.character_name,
                    str(blueprint.location_id),
                )
            ).casefold()
            self.blueprint_table.setRowHidden(row, bool(query and query not in haystack))

    def _selection_changed(self) -> None:
        if self._selected_blueprint() is not None:
            self._calculate()

    def _calculate(self) -> None:
        blueprint = self._selected_blueprint()
        if blueprint is None:
            return
        plan = self._planner.calculate(blueprint, self.target_input.value())
        self._show_plan(plan)

    def _show_plan(self, plan: ManufacturingPlan) -> None:
        blueprint_state = (
            self._translator.text("manufacturing_blueprint_ready")
            if plan.can_run_with_blueprint
            else self._translator.text("manufacturing_blueprint_shortfall").format(
                count=plan.blueprint_run_shortfall
            )
        )
        material_state = (
            self._translator.text("manufacturing_materials_ready")
            if plan.materials_available_at_location
            else self._translator.text("manufacturing_materials_missing")
        )
        self.plan_summary.setText(
            self._translator.text("manufacturing_plan_summary").format(
                runs=plan.runs,
                output=plan.planned_output,
                surplus=plan.surplus,
                duration=_format_duration(plan.duration_seconds),
                blueprint=blueprint_state,
                materials=material_state,
            )
        )
        self.material_table.setRowCount(len(plan.materials))
        for row, line in enumerate(plan.materials):
            values = (
                line.name,
                _quantity(line.required_quantity),
                _quantity(line.available_at_location),
                _quantity(line.available_total),
                _quantity(line.missing_at_location),
            )
            for column, value in enumerate(values):
                self.material_table.setItem(row, column, QTableWidgetItem(value))

    def _selected_blueprint(self) -> OwnedManufacturingBlueprint | None:
        item_id = self._selected_blueprint_id()
        return next(
            (blueprint for blueprint in self._blueprints if blueprint.item_id == item_id),
            None,
        )

    def _selected_blueprint_id(self) -> int | None:
        row = self.blueprint_table.currentRow()
        item = self.blueprint_table.item(row, 0) if row >= 0 else None
        value = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return int(value) if isinstance(value, int) else None

    def _kind_text(self, kind: BlueprintKind) -> str:
        return self._translator.text(f"blueprint_{kind.value}")


def _format_duration(seconds: int) -> str:
    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def _quantity(value: int) -> str:
    return f"{value:,}"
