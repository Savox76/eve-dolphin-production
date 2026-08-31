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
        self.quantity_spin = QSpinBox()
        self.days_spin = QSpinBox()
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
        self.plan_table = QTableWidget(0, 12)
        self.layout_table = QTableWidget(0, 6)

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

        for mode in PiOperationMode:
            self.operation_combo.addItem(self._translator.text(f"pi_mode_{mode.value}"), mode.value)
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
        self.profile_status.setWordWrap(True)
        self.profile_status.setObjectName("muted")

        self.plan_table.setObjectName("piPlanTable")
        self.plan_table.setHorizontalHeaderLabels(
            (
                self._translator.text("pi_plan_product"),
                self._translator.text("pi_plan_tier"),
                self._translator.text("pi_plan_required"),
                self._translator.text("pi_plan_per_day"),
                self._translator.text("pi_plan_available"),
                self._translator.text("pi_plan_output"),
                self._translator.text("pi_plan_cycles"),
                self._translator.text("pi_plan_capacity"),
                self._translator.text("pi_plan_additional_factories"),
                self._translator.text("pi_plan_import"),
                self._translator.text("pi_plan_missing"),
                self._translator.text("pi_plan_excess"),
            )
        )
        self.plan_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plan_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.plan_table.verticalHeader().setVisible(False)
        header = self.plan_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.layout_table.setObjectName("piLayoutTable")
        self.layout_table.setHorizontalHeaderLabels(
            (
                self._translator.text("pi_layout_stage"),
                self._translator.text("pi_layout_factories"),
                self._translator.text("pi_plan_cycles"),
                self._translator.text("pi_layout_input_day"),
                self._translator.text("pi_layout_output_day"),
                self._translator.text("pi_layout_buffer"),
            )
        )
        self.layout_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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

        tabs = QTabWidget()
        tabs.addTab(self._build_plan_tab(), self._translator.text("pi_plan_tab"))
        tabs.addTab(self._build_profiles_tab(), self._translator.text("pi_profiles_tab"))
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addWidget(tabs, 1)

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
        form.addRow(self._translator.text("pi_quantity"), self.quantity_spin)
        form.addRow(self._translator.text("pi_days"), self.days_spin)
        form.addRow(self._translator.text("pi_profile"), self.profile_combo)
        form.addRow(self._translator.text("pi_operation_mode"), self.operation_combo)
        form.addRow(self._translator.text("pi_source_tier"), self.source_tier_combo)
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
        results_layout.addWidget(self.plan_table, 1)
        layout_title = QLabel(self._translator.text("pi_optimal_layout"))
        layout_title.setObjectName("cardTitle")
        results_layout.addWidget(layout_title)
        results_layout.addWidget(self.layout_table)
        results_layout.addWidget(self.cost_label)
        layout.addWidget(inputs)
        layout.addWidget(results, 1)
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
            self.result_label.setText(self._translator.text("pi_plan_feasible"))
        else:
            reasons = ", ".join(
                self._translator.text(f"pi_block_{reason}") for reason in result.blocked_reasons
            )
            self.result_label.setText(
                self._translator.text("pi_plan_blocked").format(reasons=reasons)
            )
        self.plan_table.setRowCount(len(result.lines))
        for row, line in enumerate(result.lines):
            values = (
                line.commodity.name,
                self._tier_text(line.commodity.tier),
                f"{line.required:,}",
                _format_decimal(line.required_per_day),
                f"{line.available_at_deadline:,}",
                f"{line.planned_output:,}",
                f"{line.cycles:,}",
                f"{line.available_factory_cycles:,}",
                f"{line.additional_factories:,}",
                f"{(line.import_quantity or line.source_quantity):,}",
                f"{line.unresolved_quantity:,}",
                f"{line.excess_quantity:,}",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column > 0:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.plan_table.setItem(row, column, item)
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
        self.layout_table.setRowCount(len(result.layout))
        for row, stage in enumerate(result.layout):
            layout_values = (
                f"{self._tier_text(stage.commodity.tier)} · {stage.commodity.name}",
                f"{stage.factories:,}",
                f"{stage.cycles:,}",
                f"{stage.input_units_per_day:,}",
                f"{stage.output_units_per_day:,}",
                (
                    self._translator.text("pi_layout_storage_required")
                    if stage.buffer_storage
                    else self._translator.text("pi_layout_direct_route")
                ),
            )
            for column, value in enumerate(layout_values):
                self.layout_table.setItem(row, column, QTableWidgetItem(value))

    def _current_request(self) -> PiPlanRequest | None:
        target_id = self.target_combo.currentData()
        profile_id = self.profile_combo.currentData()
        mode = self.operation_combo.currentData()
        source_tier = self.source_tier_combo.currentData()
        strategy = self.storage_strategy_combo.currentData()
        if (
            not isinstance(target_id, int)
            or not isinstance(profile_id, int)
            or not isinstance(mode, str)
            or not isinstance(source_tier, int)
            or not isinstance(strategy, str)
        ):
            return None
        return PiPlanRequest(
            target_type_id=target_id,
            target_quantity=self.quantity_spin.value(),
            days=self.days_spin.value(),
            profile_id=profile_id,
            operation_mode=PiOperationMode(mode),
            source_tier=PiTier(source_tier),
            storage_strategy=PiStorageStrategy(strategy),
        )

    def _operation_changed(self) -> None:
        mode = self.operation_combo.currentData()
        is_import = mode == PiOperationMode.IMPORT.value
        self.source_tier_combo.setEnabled(is_import)

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
        self._operation_changed()
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
