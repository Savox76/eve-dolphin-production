"""Visible PI target planner and editable local logistics profiles."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from eve_dolphin.database import Database
from eve_dolphin.i18n import Translator
from eve_dolphin.pi import (
    PiGoalMode,
    PiOperationMode,
    PiPlannerService,
    PiPlanRequest,
    PiPlanResult,
    PiProfile,
    PiProfileRepository,
    PiStorageStrategy,
    PiTier,
    SavedPiPlan,
    SavedPiPlanRepository,
    SpaceKind,
)
from eve_dolphin.ui.pi_layout_diagram import PiLayoutDiagram


class PiPlannerPage(QWidget):
    """Plan PI targets from SDE recipes and current multi-character snapshots."""

    def __init__(
        self,
        database: Database,
        translator: Translator,
        *,
        planner: PiPlannerService | None = None,
        profiles: PiProfileRepository | None = None,
        saved_plans: SavedPiPlanRepository | None = None,
    ) -> None:
        super().__init__()
        self._translator = translator
        self._planner = planner or PiPlannerService(database)
        self._profiles = profiles or PiProfileRepository(database)
        self._saved_plans = saved_plans or SavedPiPlanRepository(database)
        self._profile_values: dict[int, PiProfile] = {}
        self._editing_profile_id: int | None = None
        self._editing_plan_id: int | None = None
        self._saved_plan_values: dict[int, SavedPiPlan] = {}

        self.target_combo = QComboBox()
        self.goal_combo = QComboBox()
        self.quantity_spin = QSpinBox()
        self.days_spin = QSpinBox()
        self.launchpad_capacity_spin = _decimal_spin(1, 1_000_000, 2)
        self.input_launchpads_spin = QSpinBox()
        self.final_factories_spin = QSpinBox()
        self.command_center_combo = QComboBox()
        self.infrastructure_reserve_spin = _decimal_spin(0, 50, 1)
        self.extractor_heads_spin = QSpinBox()
        self.profile_combo = QComboBox()
        self.operation_combo = QComboBox()
        self.source_tier_combo = QComboBox()
        self.storage_strategy_combo = QComboBox()
        self.saved_plan_combo = QComboBox()
        self.plan_name = QLineEdit()
        self.new_plan_button = QPushButton(self._translator.text("pi_plan_new"))
        self.save_plan_button = QPushButton(self._translator.text("pi_plan_save"))
        self.delete_plan_button = QPushButton(self._translator.text("pi_plan_delete"))
        self.calculate_button = QPushButton(self._translator.text("pi_calculate"))
        self.result_label = QLabel(self._translator.text("pi_no_plan"))
        self.cost_label = QLabel()
        self.resource_label = QLabel()
        self.input_cargo_title = QLabel(self._translator.text("pi_input_cargo_title"))
        self.input_cargo_table = QTableWidget(0, 7)
        self.production_path_title = QLabel(self._translator.text("pi_production_path_title"))
        self.plan_table = QTableWidget(0, 7)
        self.output_launchpad_title = QLabel(self._translator.text("pi_output_launchpad_title"))
        self.output_launchpad_table = QTableWidget(0, 6)
        self.layout_table = QTableWidget(0, 4)
        self.layout_diagram = PiLayoutDiagram()
        self.tabs = QTabWidget()
        self.quantity_label = QLabel(self._translator.text("pi_quantity"))
        self.days_label = QLabel(self._translator.text("pi_days"))
        self.launchpad_capacity_label = QLabel(self._translator.text("pi_launchpad_capacity"))
        self.input_launchpads_label = QLabel(self._translator.text("pi_input_launchpads"))
        self.final_factories_label = QLabel(self._translator.text("pi_final_factories"))
        self.extractor_heads_label = QLabel(self._translator.text("pi_extractor_heads"))

        self.profile_name = QLineEdit()
        self.space_combo = QComboBox()
        self.customs_checkbox = QCheckBox(self._translator.text("pi_customs_office"))
        self.import_tax_spin = _decimal_spin(0, 100, 2)
        self.export_tax_spin = _decimal_spin(0, 100, 2)
        self.transport_spin = _decimal_spin(0, 1_000_000_000, 2)
        self.cargo_spin = _decimal_spin(1, 1_000_000_000, 2)
        self.risk_spin = _decimal_spin(0, 100, 2)
        self.supply_combo = QComboBox()
        self.new_profile_button = QPushButton(self._translator.text("pi_profile_new"))
        self.save_profile_button = QPushButton(self._translator.text("pi_profile_save"))
        self.profile_status = QLabel()

        self._configure_controls()
        self._build_layout()
        self.calculate_button.clicked.connect(self._calculate)
        self.goal_combo.currentIndexChanged.connect(self._goal_changed)
        self.operation_combo.currentIndexChanged.connect(self._operation_changed)
        self.saved_plan_combo.currentIndexChanged.connect(self._saved_plan_selected)
        self.new_plan_button.clicked.connect(self._new_plan)
        self.save_plan_button.clicked.connect(self._save_plan)
        self.delete_plan_button.clicked.connect(self._delete_plan)
        self.profile_combo.currentIndexChanged.connect(self._profile_selected)
        self.new_profile_button.clicked.connect(self._new_profile)
        self.save_profile_button.clicked.connect(self._save_profile)
        self.refresh()

    def _configure_controls(self) -> None:
        self.quantity_spin.setRange(1, 2_000_000_000)
        self.quantity_spin.setValue(100)
        self.days_spin.setRange(1, 365)
        self.days_spin.setValue(7)
        self.launchpad_capacity_spin.setValue(10_000)
        self.launchpad_capacity_spin.setSuffix(" m³")
        self.input_launchpads_spin.setRange(1, 5)
        self.input_launchpads_spin.setValue(1)
        self.final_factories_spin.setRange(1, 100)
        self.final_factories_spin.setValue(1)
        for level in range(6):
            self.command_center_combo.addItem(
                self._translator.text("pi_command_center_level_value").format(level=level), level
            )
        self.command_center_combo.setCurrentIndex(5)
        self.infrastructure_reserve_spin.setValue(10)
        self.infrastructure_reserve_spin.setSuffix(" %")
        self.extractor_heads_spin.setRange(1, 10)
        self.extractor_heads_spin.setValue(5)

        for goal_mode in PiGoalMode:
            self.goal_combo.addItem(
                self._translator.text(f"pi_goal_{goal_mode.value}"), goal_mode.value
            )

        for operation_mode in PiOperationMode:
            self.operation_combo.addItem(
                self._translator.text(f"pi_mode_{operation_mode.value}"), operation_mode.value
            )
        for tier in PiTier:
            if tier is not PiTier.ADVANCED:
                self.source_tier_combo.addItem(self._tier_text(tier), int(tier))
        for strategy in PiStorageStrategy:
            self.storage_strategy_combo.addItem(
                self._translator.text(f"pi_storage_strategy_{strategy.value}"), strategy.value
            )

        self.result_label.setWordWrap(True)
        self.result_label.setObjectName("muted")
        self.cost_label.setWordWrap(True)
        self.cost_label.setObjectName("muted")
        self.resource_label.setWordWrap(True)
        self.resource_label.setObjectName("muted")
        self.profile_status.setWordWrap(True)
        self.profile_status.setObjectName("muted")

        self.input_cargo_title.setObjectName("cardTitle")
        self.input_cargo_table.setObjectName("piInputCargoTable")
        self.input_cargo_table.setHorizontalHeaderLabels(
            (
                self._translator.text("pi_input_launchpad_column"),
                self._translator.text("pi_input_branch_column"),
                self._translator.text("pi_input_product_column"),
                self._translator.text("pi_plan_tier"),
                self._translator.text("pi_input_quantity_column"),
                self._translator.text("pi_input_volume_column"),
                self._translator.text("pi_input_fill_column"),
            )
        )
        self.input_cargo_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.input_cargo_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.input_cargo_table.verticalHeader().setVisible(False)
        self.input_cargo_table.setMinimumWidth(1_020)
        cargo_header = self.input_cargo_table.horizontalHeader()
        cargo_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cargo_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        cargo_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.input_cargo_title.hide()
        self.input_cargo_table.hide()

        self.production_path_title.setObjectName("cardTitle")

        self.output_launchpad_title.setObjectName("cardTitle")
        self.output_launchpad_table.setObjectName("piOutputLaunchpadTable")
        self.output_launchpad_table.setHorizontalHeaderLabels(
            (
                self._translator.text("pi_output_launchpad_column"),
                self._translator.text("pi_plan_product"),
                self._translator.text("pi_input_quantity_column"),
                self._translator.text("pi_input_volume_column"),
                self._translator.text("pi_output_free_column"),
                self._translator.text("pi_output_duration_column"),
            )
        )
        self.output_launchpad_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.output_launchpad_table.verticalHeader().setVisible(False)
        self.output_launchpad_table.setMinimumSize(900, 120)
        output_header = self.output_launchpad_table.horizontalHeader()
        output_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        output_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.output_launchpad_title.hide()
        self.output_launchpad_table.hide()

        self.plan_table.setObjectName("piPlanTable")
        self.plan_table.setHorizontalHeaderLabels(
            (
                self._translator.text("pi_plan_product"),
                self._translator.text("pi_plan_required"),
                self._translator.text("pi_plan_available"),
                self._translator.text("pi_plan_output"),
                self._translator.text("pi_plan_capacity"),
                self._translator.text("pi_plan_import"),
                self._translator.text("pi_plan_missing"),
            )
        )
        self.plan_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plan_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.plan_table.setMinimumSize(1_020, 340)
        self.plan_table.verticalHeader().setVisible(False)
        header = self.plan_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.layout_table.setObjectName("piLayoutTable")
        self.layout_table.setHorizontalHeaderLabels(
            (
                self._translator.text("pi_layout_stage"),
                self._translator.text("pi_layout_setup_compact"),
                self._translator.text("pi_layout_flow_compact"),
                self._translator.text("pi_layout_buffer"),
            )
        )
        self.layout_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.layout_table.setMinimumSize(900, 220)
        self.layout_table.verticalHeader().setVisible(False)
        layout_header = self.layout_table.horizontalHeader()
        layout_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        for kind in SpaceKind:
            self.space_combo.addItem(self._translator.text(f"pi_space_{kind.value}"), kind.value)
        for tier in PiTier:
            self.supply_combo.addItem(self._tier_text(tier), int(tier))
        self.supply_combo.removeItem(self.supply_combo.findData(int(PiTier.ADVANCED)))

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(18)
        title = QLabel(self._translator.text("pi_planner"))
        title.setObjectName("pageTitle")
        detail = QLabel(self._translator.text("pi_planner_detail"))
        detail.setObjectName("muted")
        detail.setWordWrap(True)

        self.tabs.addTab(
            self._scrollable(self._build_plan_tab()), self._translator.text("pi_plan_tab")
        )
        self.tabs.addTab(
            self._scrollable(self._build_profiles_tab()),
            self._translator.text("pi_profiles_tab"),
        )
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addWidget(self.tabs, 1)

    @staticmethod
    def _scrollable(content: QWidget) -> QScrollArea:
        content.setMinimumWidth(1_100)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content)
        return scroll

    def _build_plan_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(14)

        inputs = QFrame()
        inputs.setObjectName("card")
        form = QFormLayout(inputs)
        form.setContentsMargins(20, 18, 20, 18)
        form.addRow(self._translator.text("pi_saved_plan"), self.saved_plan_combo)
        form.addRow(self._translator.text("pi_plan_name"), self.plan_name)
        form.addRow(self._translator.text("pi_target"), self.target_combo)
        form.addRow(self._translator.text("pi_goal_mode"), self.goal_combo)
        form.addRow(self.quantity_label, self.quantity_spin)
        form.addRow(self.days_label, self.days_spin)
        form.addRow(self.launchpad_capacity_label, self.launchpad_capacity_spin)
        form.addRow(self.input_launchpads_label, self.input_launchpads_spin)
        form.addRow(self.final_factories_label, self.final_factories_spin)
        form.addRow(self._translator.text("pi_profile"), self.profile_combo)
        form.addRow(self._translator.text("pi_operation_mode"), self.operation_combo)
        form.addRow(self._translator.text("pi_source_tier"), self.source_tier_combo)
        form.addRow(self._translator.text("pi_command_center_level"), self.command_center_combo)
        form.addRow(
            self._translator.text("pi_infrastructure_reserve"),
            self.infrastructure_reserve_spin,
        )
        form.addRow(self.extractor_heads_label, self.extractor_heads_spin)
        form.addRow(self._translator.text("pi_storage_strategy"), self.storage_strategy_combo)
        actions = QWidget()
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.addWidget(self.calculate_button)
        action_layout.addWidget(self.new_plan_button)
        action_layout.addWidget(self.save_plan_button)
        action_layout.addWidget(self.delete_plan_button)
        action_layout.addStretch(1)
        form.addRow("", actions)

        results = QFrame()
        results.setObjectName("card")
        results_layout = QVBoxLayout(results)
        results_layout.setContentsMargins(20, 18, 20, 18)
        results_layout.setSpacing(10)
        results_layout.addWidget(self.result_label)
        results_layout.addWidget(self.resource_label)
        results_layout.addWidget(self.production_path_title)
        results_layout.addWidget(self.plan_table, 1)
        results_layout.addWidget(self.input_cargo_title)
        results_layout.addWidget(self.input_cargo_table)
        results_layout.addWidget(self.output_launchpad_title)
        results_layout.addWidget(self.output_launchpad_table)
        layout_title = QLabel(self._translator.text("pi_optimal_layout"))
        layout_title.setObjectName("cardTitle")
        results_layout.addWidget(layout_title)
        results_layout.addWidget(self.layout_table)
        diagram_title = QLabel(self._translator.text("pi_graphical_layout"))
        diagram_title.setObjectName("cardTitle")
        results_layout.addWidget(diagram_title)
        results_layout.addWidget(self.layout_diagram)
        results_layout.addWidget(self.cost_label)
        layout.addWidget(inputs)
        self.layout_diagram.setMinimumHeight(260)
        layout.addWidget(results)
        layout.addStretch(1)
        return page

    def _build_profiles_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 16, 0, 0)
        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setContentsMargins(20, 18, 20, 18)
        form.addRow(self._translator.text("pi_profile_name"), self.profile_name)
        form.addRow(self._translator.text("pi_space_kind"), self.space_combo)
        form.addRow("", self.customs_checkbox)
        form.addRow(self._translator.text("pi_import_tax"), self.import_tax_spin)
        form.addRow(self._translator.text("pi_export_tax"), self.export_tax_spin)
        form.addRow(self._translator.text("pi_transport_rate"), self.transport_spin)
        form.addRow(self._translator.text("pi_cargo_capacity"), self.cargo_spin)
        form.addRow(self._translator.text("pi_risk_markup"), self.risk_spin)
        form.addRow(self._translator.text("pi_supply_tier"), self.supply_combo)
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.addWidget(self.new_profile_button)
        actions_layout.addWidget(self.save_profile_button)
        actions_layout.addStretch(1)
        form.addRow("", actions)
        form.addRow("", self.profile_status)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def refresh(self) -> None:
        """Reload SDE targets and profiles after a completed synchronization."""

        target_id = self.target_combo.currentData()
        profile_id = self.profile_combo.currentData()
        self.target_combo.clear()
        try:
            targets = self._planner.targets(self._translator.language)
        except ValueError:
            targets = ()
        for type_id, name, tier in targets:
            self.target_combo.addItem(f"{self._tier_text(tier)} · {name}", type_id)
        _restore_combo(self.target_combo, target_id)

        profiles = self._profiles.list_all()
        self._profile_values = {
            profile.profile_id: profile for profile in profiles if profile.profile_id is not None
        }
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in profiles:
            self.profile_combo.addItem(profile.name, profile.profile_id)
        _restore_combo(self.profile_combo, profile_id)
        self.profile_combo.blockSignals(False)
        self.calculate_button.setEnabled(bool(targets and profiles))
        selected_plan_id = self.saved_plan_combo.currentData()
        saved = self._saved_plans.list_all()
        self._saved_plan_values = {plan.plan_id: plan for plan in saved if plan.plan_id is not None}
        self.saved_plan_combo.blockSignals(True)
        self.saved_plan_combo.clear()
        self.saved_plan_combo.addItem(self._translator.text("pi_plan_unsaved"), None)
        for plan in saved:
            self.saved_plan_combo.addItem(plan.name, plan.plan_id)
        _restore_combo(self.saved_plan_combo, selected_plan_id)
        self.saved_plan_combo.blockSignals(False)
        if not targets:
            self.result_label.setText(self._translator.text("pi_no_catalog"))
        self._profile_selected()
        self._operation_changed()
        self._goal_changed()

    def _calculate(self) -> None:
        request = self._current_request()
        if request is None:
            self.result_label.setText(self._translator.text("pi_no_catalog"))
            return
        try:
            result = self._planner.plan(request, self._translator.language)
        except ValueError as error:
            self.result_label.setText(str(error))
            return
        self._show_result(result)

    def _show_result(self, result: PiPlanResult) -> None:
        if result.is_feasible:
            status = self._translator.text("pi_plan_feasible")
        else:
            reasons = ", ".join(
                self._translator.text(f"pi_block_{reason}") for reason in result.blocked_reasons
            )
            status = self._translator.text("pi_plan_blocked").format(reasons=reasons)
        if result.launchpad_fill is not None:
            fill = result.launchpad_fill
            reverse_tiers = tuple(
                dict.fromkeys(
                    self._tier_text(line.commodity.tier)
                    for line in sorted(
                        result.lines,
                        key=lambda line: -int(line.commodity.tier),
                    )
                )
            )
            status = f"{status}\n" + self._translator.text("pi_reverse_summary").format(
                path=" → ".join(reverse_tiers)
            )
            status = f"{status}\n" + self._translator.text("pi_launchpad_input_result").format(
                launchpads=fill.input_launchpads,
                used=_format_decimal(fill.input_volume_m3),
                capacity=_format_decimal(fill.input_capacity_m3),
            )
            status = f"{status}\n" + self._translator.text("pi_launchpad_result").format(
                quantity=f"{fill.product_quantity:,}",
                product=result.target.name,
                used=_format_decimal(fill.product_volume_m3),
                capacity=_format_decimal(fill.capacity_m3),
                unused=_format_decimal(fill.unused_volume_m3),
                factories=fill.final_factories,
                duration=_format_duration(fill.fill_time),
            )
            totals: dict[int, Decimal] = {}
            for cargo in fill.input_cargo:
                totals[cargo.launchpad_index] = (
                    totals.get(cargo.launchpad_index, Decimal(0)) + cargo.volume_m3
                )
            self.input_cargo_table.setRowCount(len(fill.input_cargo))
            for row, cargo in enumerate(fill.input_cargo):
                cargo_values = (
                    self._translator.text("pi_input_launchpad_value").format(
                        index=cargo.launchpad_index
                    ),
                    cargo.branch_commodity.name,
                    cargo.commodity.name,
                    self._tier_text(cargo.commodity.tier),
                    f"{cargo.quantity:,}",
                    f"{_format_decimal(cargo.volume_m3)} m³",
                    self._translator.text("pi_input_fill_value").format(
                        used=_format_decimal(totals[cargo.launchpad_index]),
                        capacity=_format_decimal(fill.capacity_m3),
                    ),
                )
                for column, value in enumerate(cargo_values):
                    self.input_cargo_table.setItem(row, column, QTableWidgetItem(value))
            self.input_cargo_table.resizeRowsToContents()
            self.input_cargo_table.setMinimumHeight(
                min(340, 82 + max(1, len(fill.input_cargo)) * 34)
            )
            self.input_cargo_title.show()
            self.input_cargo_table.show()
            output_values = (
                self._translator.text("pi_output_launchpad_value"),
                result.target.name,
                f"{fill.product_quantity:,}",
                f"{_format_decimal(fill.product_volume_m3)} / "
                f"{_format_decimal(fill.capacity_m3)} m³",
                f"{_format_decimal(fill.unused_volume_m3)} m³",
                _format_duration(fill.fill_time),
            )
            self.output_launchpad_table.setRowCount(1)
            for column, value in enumerate(output_values):
                self.output_launchpad_table.setItem(0, column, QTableWidgetItem(value))
            self.output_launchpad_title.show()
            self.output_launchpad_table.show()
        else:
            self.input_cargo_table.setRowCount(0)
            self.input_cargo_title.hide()
            self.input_cargo_table.hide()
            self.output_launchpad_table.setRowCount(0)
            self.output_launchpad_title.hide()
            self.output_launchpad_table.hide()
        self.result_label.setText(status)
        self.plan_table.setRowCount(len(result.lines))
        if result.launchpad_fill is not None:
            self.production_path_title.setText(self._translator.text("pi_reverse_path_title"))
            self.plan_table.setHorizontalHeaderLabels(
                tuple(
                    self._translator.text(key)
                    for key in (
                        "pi_reverse_stage",
                        "pi_reverse_needed",
                        "pi_reverse_cycles",
                        "pi_reverse_output",
                        "pi_reverse_excess",
                        "pi_reverse_income",
                        "pi_reverse_status",
                    )
                )
            )
            display_lines = sorted(
                result.lines,
                key=lambda line: (-int(line.commodity.tier), line.commodity.name.casefold()),
            )
            for row, line in enumerate(display_lines, start=1):
                income = line.import_quantity or line.source_quantity
                if income:
                    line_status = self._translator.text("pi_reverse_income_ready")
                elif line.excess_quantity:
                    line_status = self._translator.text("pi_reverse_overproduction").format(
                        quantity=f"{line.excess_quantity:,}"
                    )
                else:
                    line_status = self._translator.text("pi_reverse_exact")
                values = (
                    f"{row}. {self._tier_text(line.commodity.tier)} · {line.commodity.name}",
                    f"{line.required:,}",
                    f"{line.cycles:,}" if line.cycles else "—",
                    f"{line.planned_output:,}" if line.planned_output else "—",
                    f"{line.excess_quantity:,}",
                    f"{income:,}" if income else "—",
                    line_status,
                )
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column in {1, 2, 3, 4, 5}:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                        )
                    self.plan_table.setItem(row - 1, column, item)
        else:
            self.production_path_title.setText(self._translator.text("pi_production_path_title"))
            self.plan_table.setHorizontalHeaderLabels(
                tuple(
                    self._translator.text(key)
                    for key in (
                        "pi_plan_product",
                        "pi_plan_required",
                        "pi_plan_available",
                        "pi_plan_output",
                        "pi_plan_capacity",
                        "pi_plan_import",
                        "pi_plan_missing",
                    )
                )
            )
            display_lines = sorted(
                result.lines,
                key=lambda line: (int(line.commodity.tier), line.commodity.name.casefold()),
            )
            for row, line in enumerate(display_lines):
                values = (
                    f"{self._tier_text(line.commodity.tier)} · {line.commodity.name}",
                    self._translator.text("pi_plan_demand_compact").format(
                        quantity=f"{line.required:,}",
                        per_day=_format_decimal(line.required_per_day),
                    ),
                    f"{line.available_at_deadline:,}",
                    self._translator.text("pi_plan_output_compact").format(
                        quantity=f"{line.planned_output:,}", cycles=f"{line.cycles:,}"
                    ),
                    self._translator.text("pi_plan_capacity_compact").format(
                        cycles=f"{line.available_factory_cycles:,}",
                        factories=f"{line.additional_factories:,}",
                    ),
                    f"{(line.import_quantity or line.source_quantity):,}",
                    self._translator.text("pi_plan_missing_compact").format(
                        missing=f"{line.unresolved_quantity:,}",
                        excess=f"{line.excess_quantity:,}",
                    ),
                )
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column > 0:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                        )
                    self.plan_table.setItem(row, column, item)
        self.plan_table.resizeRowsToContents()
        self.cost_label.setText(
            self._translator.text("pi_plan_costs").format(
                import_volume=_format_decimal(result.import_volume_m3),
                export_volume=_format_decimal(result.export_volume_m3),
                trips=result.cargo_trips,
                import_tax=_format_isk(result.import_tax_isk),
                export_tax=_format_isk(result.export_tax_isk),
                transport=_format_isk(result.transport_cost_isk),
                risk=_format_isk(result.risk_markup_isk),
                total=_format_isk(result.total_logistics_isk),
            )
        )
        budget = result.infrastructure_budget
        if budget is not None:
            resource_text = self._translator.text("pi_resource_budget_result").format(
                level=budget.command_center_level,
                used_cpu=f"{budget.used_cpu:,}",
                usable_cpu=f"{budget.total_cpu - budget.reserved_cpu:,}",
                total_cpu=f"{budget.total_cpu:,}",
                remaining_cpu=f"{budget.remaining_cpu:,}",
                used_power=f"{budget.used_power:,}",
                usable_power=f"{budget.total_power - budget.reserved_power:,}",
                total_power=f"{budget.total_power:,}",
                remaining_power=f"{budget.remaining_power:,}",
                reserve=_format_decimal(result.request.infrastructure_reserve_percent),
                launchpads=budget.launchpads,
                storage=budget.storage_facilities,
                ecus=budget.extractor_control_units,
                heads=budget.extractor_heads,
                basic=budget.basic_factories,
                advanced=budget.advanced_factories,
                high_tech=budget.high_tech_factories,
                copies=budget.maximum_layout_copies,
                final_factories=budget.maximum_final_factories,
            )
            if budget.required_planet_types:
                planet_types = " / ".join(
                    self._translator.text(f"planet_type_{planet_type}")
                    for planet_type in budget.required_planet_types
                )
                resource_text += "\n" + self._translator.text("pi_required_planet_types").format(
                    types=planet_types
                )
            self.resource_label.setText(resource_text)
        else:
            self.resource_label.clear()
        self.layout_table.setRowCount(len(result.layout))
        for row, stage in enumerate(result.layout):
            layout_values = (
                f"{self._tier_text(stage.commodity.tier)} · {stage.commodity.name}",
                self._translator.text("pi_layout_setup_value").format(
                    factories=f"{stage.factories:,}", cycles=f"{stage.cycles:,}"
                ),
                self._translator.text("pi_layout_flow_value").format(
                    input=f"{stage.input_units_per_day:,}",
                    output=f"{stage.output_units_per_day:,}",
                ),
                (
                    self._translator.text("pi_layout_storage_required")
                    if stage.buffer_storage
                    else self._translator.text("pi_layout_direct_route")
                ),
            )
            for column, value in enumerate(layout_values):
                self.layout_table.setItem(row, column, QTableWidgetItem(value))
        self.layout_table.resizeRowsToContents()
        self.layout_diagram.show_plan(
            result,
            source_label=self._translator.text(
                "pi_diagram_extractors"
                if result.request.operation_mode is PiOperationMode.EXTRACTOR
                else "pi_diagram_purchase"
            ),
            launchpad_label=self._translator.text("pi_diagram_launchpad"),
            buffer_label=self._translator.text("pi_diagram_buffer"),
            factory_label=self._translator.text("pi_diagram_factory"),
            tier_labels={tier: self._tier_text(tier) for tier in PiTier},
            input_label=self._translator.text("pi_diagram_input_launchpad"),
            extractor_label=self._translator.text("pi_diagram_extractor"),
            ecu_label=self._translator.text("pi_diagram_ecu"),
            heads_label=self._translator.text("pi_diagram_heads"),
            cycles_label=self._translator.text("pi_diagram_cycles"),
            branch_label=self._translator.text("pi_diagram_branches"),
            needed_label=self._translator.text("pi_reverse_needed").lower(),
            produced_label=self._translator.text("pi_reverse_output").lower(),
        )

    def _current_request(self) -> PiPlanRequest | None:
        target_id = self.target_combo.currentData()
        profile_id = self.profile_combo.currentData()
        mode = self.operation_combo.currentData()
        source_tier = self.source_tier_combo.currentData()
        strategy = self.storage_strategy_combo.currentData()
        goal = self.goal_combo.currentData()
        if (
            not isinstance(target_id, int)
            or not isinstance(profile_id, int)
            or not isinstance(mode, str)
            or not isinstance(source_tier, int)
            or not isinstance(strategy, str)
            or not isinstance(goal, str)
        ):
            return None
        return PiPlanRequest(
            target_type_id=target_id,
            target_quantity=(self.quantity_spin.value() if goal == PiGoalMode.MANUAL.value else 1),
            days=self.days_spin.value() if goal == PiGoalMode.MANUAL.value else 1,
            profile_id=profile_id,
            operation_mode=PiOperationMode(mode),
            source_tier=PiTier(source_tier),
            storage_strategy=PiStorageStrategy(strategy),
            goal_mode=PiGoalMode(goal),
            launchpad_capacity_m3=_spin_decimal(self.launchpad_capacity_spin),
            input_launchpads=self.input_launchpads_spin.value(),
            final_factories=self.final_factories_spin.value(),
            command_center_level=int(self.command_center_combo.currentData()),
            infrastructure_reserve_percent=_spin_decimal(self.infrastructure_reserve_spin),
            extractor_heads_per_ecu=self.extractor_heads_spin.value(),
        )

    def _goal_changed(self) -> None:
        is_launchpad = self.goal_combo.currentData() == PiGoalMode.LAUNCHPAD.value
        self.quantity_label.setVisible(not is_launchpad)
        self.quantity_spin.setVisible(not is_launchpad)
        self.days_label.setVisible(not is_launchpad)
        self.days_spin.setVisible(not is_launchpad)
        self.launchpad_capacity_label.setVisible(is_launchpad)
        self.launchpad_capacity_spin.setVisible(is_launchpad)
        self.input_launchpads_label.setVisible(is_launchpad)
        self.input_launchpads_spin.setVisible(is_launchpad)
        self.final_factories_label.setVisible(is_launchpad)
        self.final_factories_spin.setVisible(is_launchpad)

    def _operation_changed(self) -> None:
        mode = self.operation_combo.currentData()
        is_import = mode == PiOperationMode.IMPORT.value
        self.source_tier_combo.setEnabled(is_import)
        self.extractor_heads_label.setVisible(not is_import)
        self.extractor_heads_spin.setVisible(not is_import)

    def _saved_plan_selected(self) -> None:
        plan_id = self.saved_plan_combo.currentData()
        if not isinstance(plan_id, int):
            self._editing_plan_id = None
            self.delete_plan_button.setEnabled(False)
            return
        plan = self._saved_plan_values.get(plan_id)
        if plan is None:
            return
        self._editing_plan_id = plan_id
        self.delete_plan_button.setEnabled(True)
        self.plan_name.setText(plan.name)
        request = plan.request
        _restore_combo(self.target_combo, request.target_type_id)
        self.quantity_spin.setValue(request.target_quantity)
        self.days_spin.setValue(request.days)
        _restore_combo(self.profile_combo, request.profile_id)
        _restore_combo(self.operation_combo, request.operation_mode.value)
        _restore_combo(
            self.source_tier_combo,
            int(request.source_tier if request.source_tier is not None else PiTier.RAW),
        )
        _restore_combo(self.storage_strategy_combo, request.storage_strategy.value)
        _restore_combo(self.goal_combo, request.goal_mode.value)
        self.launchpad_capacity_spin.setValue(float(request.launchpad_capacity_m3))
        self.input_launchpads_spin.setValue(request.input_launchpads)
        self.final_factories_spin.setValue(request.final_factories)
        _restore_combo(self.command_center_combo, request.command_center_level)
        self.infrastructure_reserve_spin.setValue(float(request.infrastructure_reserve_percent))
        self.extractor_heads_spin.setValue(request.extractor_heads_per_ecu)
        self._operation_changed()
        self._goal_changed()
        self._calculate()

    def _new_plan(self) -> None:
        self._editing_plan_id = None
        self.saved_plan_combo.setCurrentIndex(0)
        self.plan_name.clear()
        self.delete_plan_button.setEnabled(False)
        self.plan_name.setFocus()

    def _save_plan(self) -> None:
        request = self._current_request()
        if request is None:
            return
        try:
            request = self._planner.plan(request, self._translator.language).request
            stored = self._saved_plans.save(
                SavedPiPlan(self._editing_plan_id, self.plan_name.text(), request)
            )
        except (ValueError, sqlite3.IntegrityError) as error:
            self.result_label.setText(
                self._translator.text("pi_plan_save_error").format(message=error)
            )
            return
        self._editing_plan_id = stored.plan_id
        self.refresh()
        _restore_combo(self.saved_plan_combo, stored.plan_id)
        self.result_label.setText(self._translator.text("pi_plan_saved").format(name=stored.name))

    def _delete_plan(self) -> None:
        if self._editing_plan_id is None:
            return
        self._saved_plans.delete(self._editing_plan_id)
        self._new_plan()
        self.refresh()
        self.result_label.setText(self._translator.text("pi_plan_deleted"))

    def _profile_selected(self) -> None:
        profile_id = self.profile_combo.currentData()
        if not isinstance(profile_id, int):
            return
        profile = self._profile_values.get(profile_id)
        if profile is None:
            return
        self._editing_profile_id = profile_id
        self.profile_name.setText(profile.name)
        self.space_combo.setCurrentIndex(self.space_combo.findData(profile.space_kind.value))
        self.customs_checkbox.setChecked(profile.has_customs_office)
        self.import_tax_spin.setValue(float(profile.import_tax_percent))
        self.export_tax_spin.setValue(float(profile.export_tax_percent))
        self.transport_spin.setValue(float(profile.transport_isk_per_m3))
        self.cargo_spin.setValue(float(profile.cargo_capacity_m3))
        self.risk_spin.setValue(float(profile.risk_markup_percent))
        self.supply_combo.setCurrentIndex(self.supply_combo.findData(int(profile.supply_tier)))

    def _new_profile(self) -> None:
        self._editing_profile_id = None
        self.profile_name.clear()
        self.profile_status.clear()
        self.profile_name.setFocus()

    def _save_profile(self) -> None:
        space_value = self.space_combo.currentData()
        supply_value = self.supply_combo.currentData()
        if not isinstance(space_value, str) or not isinstance(supply_value, int):
            return
        try:
            stored = self._profiles.save(
                PiProfile(
                    profile_id=self._editing_profile_id,
                    name=self.profile_name.text(),
                    space_kind=SpaceKind(space_value),
                    has_customs_office=self.customs_checkbox.isChecked(),
                    import_tax_percent=_spin_decimal(self.import_tax_spin),
                    export_tax_percent=_spin_decimal(self.export_tax_spin),
                    transport_isk_per_m3=_spin_decimal(self.transport_spin),
                    cargo_capacity_m3=_spin_decimal(self.cargo_spin),
                    risk_markup_percent=_spin_decimal(self.risk_spin),
                    supply_tier=PiTier(supply_value),
                )
            )
        except (ValueError, sqlite3.IntegrityError) as error:
            self.profile_status.setText(
                self._translator.text("pi_profile_error").format(message=error)
            )
            return
        self._editing_profile_id = stored.profile_id
        self.refresh()
        _restore_combo(self.profile_combo, stored.profile_id)
        self._profile_selected()
        self.profile_status.setText(
            self._translator.text("pi_profile_saved").format(name=stored.name)
        )

    def _tier_text(self, tier: PiTier) -> str:
        return self._translator.text(f"pi_tier_{int(tier)}")


def _decimal_spin(minimum: float, maximum: float, decimals: int) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setDecimals(decimals)
    spin.setRange(minimum, maximum)
    spin.setSingleStep(0.1)
    return spin


def _spin_decimal(spin: QDoubleSpinBox) -> Decimal:
    return Decimal(str(spin.value()))


def _restore_combo(combo: QComboBox, value: object) -> None:
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)
    elif combo.count():
        combo.setCurrentIndex(0)


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):,.2f}"


def _format_isk(value: Decimal) -> str:
    return f"{value.quantize(Decimal('1')):,.0f}"


def _format_duration(value: object) -> str:
    from datetime import timedelta

    if not isinstance(value, timedelta):
        return "-"
    total_minutes = max(0, int(value.total_seconds() // 60))
    days, remainder = divmod(total_minutes, 1440)
    hours, minutes = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days} d")
    if hours or days:
        parts.append(f"{hours} h")
    parts.append(f"{minutes} min")
    return " ".join(parts)
