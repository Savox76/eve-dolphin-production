"""Scrollable dependency graph for PI extractor and factory-colony plans."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from eve_dolphin.pi import (
    PiLaunchpadCargo,
    PiLayoutStage,
    PiOperationMode,
    PiPlanResult,
    PiTier,
)


@dataclass(frozen=True, slots=True)
class _DiagramNode:
    key: str
    title: str
    detail: str
    kind: str


class PiLayoutDiagram(QGraphicsView):
    """Render exact dependencies without shrinking a large graph into the viewport."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("piLayoutDiagram")
        self.setMinimumSize(900, 320)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setScene(QGraphicsScene(self))

    def show_plan(
        self,
        result: PiPlanResult,
        *,
        source_label: str,
        launchpad_label: str,
        buffer_label: str,
        factory_label: str,
        tier_labels: dict[PiTier, str],
        input_label: str = "Input launchpad",
        extractor_label: str = "Extractor",
        ecu_label: str = "ECU",
        heads_label: str = "heads",
        cycles_label: str = "cycles",
        branch_label: str = "Production branches",
        needed_label: str = "needed",
        produced_label: str = "produced",
    ) -> None:
        scene = self.scene()
        scene.clear()
        columns, edges = _graph(
            result,
            source_label=source_label,
            launchpad_label=launchpad_label,
            buffer_label=buffer_label,
            factory_label=factory_label,
            tier_labels=tier_labels,
            input_label=input_label,
            extractor_label=extractor_label,
            ecu_label=ecu_label,
            heads_label=heads_label,
            cycles_label=cycles_label,
            branch_label=branch_label,
            needed_label=needed_label,
            produced_label=produced_label,
        )

        box_width = 240.0
        column_gap = 110.0
        row_gap = 30.0
        top_margin = 58.0
        margin = 28.0
        node_heights = {
            node.key: max(104.0, 58.0 + 18.0 * len(node.detail.splitlines()))
            for _heading, nodes in columns
            for node in nodes
        }
        column_heights = {
            heading: sum(node_heights[node.key] for node in nodes)
            + max(0, len(nodes) - 1) * row_gap
            for heading, nodes in columns
        }
        canvas_height = max(
            300.0,
            top_margin + margin + max(column_heights.values()),
        )
        rects: dict[str, QRectF] = {}

        for column, (heading, nodes) in enumerate(columns):
            x = margin + column * (box_width + column_gap)
            heading_item = scene.addText(heading)
            heading_font = QFont(heading_item.font())
            heading_font.setBold(True)
            heading_item.setFont(heading_font)
            heading_item.setDefaultTextColor(QColor("#9fb5d8"))
            heading_item.setTextWidth(box_width)
            heading_item.setPos(x, 12)
            total_height = column_heights[heading]
            y = top_margin + max(0.0, (canvas_height - top_margin - margin - total_height) / 2)
            top = y
            for node in nodes:
                height = node_heights[node.key]
                rects[node.key] = QRectF(x, top, box_width, height)
                top += height + row_gap

        for start_key, end_key in edges:
            start_rect = rects.get(start_key)
            end_rect = rects.get(end_key)
            if start_rect is not None and end_rect is not None:
                _add_arrow(
                    scene,
                    QPointF(start_rect.right(), start_rect.center().y()),
                    QPointF(end_rect.left(), end_rect.center().y()),
                )

        for _heading, nodes in columns:
            for node in nodes:
                rect = rects[node.key]
                color = {
                    "source": "#24445a",
                    "factory": "#17345a",
                    "target": "#28523f",
                }[node.kind]
                scene.addRect(rect, QPen(QColor("#4f7fb3"), 1.5), QBrush(QColor(color)))
                title_item = scene.addText(node.title)
                title_font = QFont(title_item.font())
                title_font.setBold(True)
                title_item.setFont(title_font)
                title_item.setDefaultTextColor(QColor("#f1f6ff"))
                title_item.setTextWidth(box_width - 16)
                title_item.setPos(rect.left() + 8, rect.top() + 7)
                detail_item = scene.addText(node.detail)
                detail_item.setDefaultTextColor(QColor("#c8d8eb"))
                detail_item.setTextWidth(box_width - 16)
                detail_item.setPos(rect.left() + 8, rect.top() + 34)

        canvas_width = margin * 2 + len(columns) * box_width + (len(columns) - 1) * column_gap
        scene.setSceneRect(0, 0, canvas_width, canvas_height)
        self.resetTransform()
        self.horizontalScrollBar().setValue(0)
        self.verticalScrollBar().setValue(0)

    def clear_plan(self) -> None:
        self.scene().clear()


def _graph(
    result: PiPlanResult,
    *,
    source_label: str,
    launchpad_label: str,
    buffer_label: str,
    factory_label: str,
    tier_labels: dict[PiTier, str],
    input_label: str,
    extractor_label: str,
    ecu_label: str,
    heads_label: str,
    cycles_label: str,
    branch_label: str,
    needed_label: str,
    produced_label: str,
) -> tuple[list[tuple[str, list[_DiagramNode]]], list[tuple[str, str]]]:
    source_nodes: list[_DiagramNode] = []
    source_outputs: dict[str, set[int]] = {}
    branch_nodes: list[_DiagramNode] = []
    branch_outputs: dict[str, set[int]] = {}
    branch_roots: dict[str, int] = {}
    branch_edges: list[tuple[str, str]] = []
    fill = result.launchpad_fill
    if result.request.operation_mode is PiOperationMode.IMPORT and fill is not None:
        cargo_by_launchpad: dict[int, list[PiLaunchpadCargo]] = defaultdict(list)
        for cargo in fill.input_cargo:
            cargo_by_launchpad[cargo.launchpad_index].append(cargo)
        for index in range(1, fill.input_launchpads + 1):
            cargo_items = cargo_by_launchpad.get(index, [])
            key = f"source-{index}"
            by_branch: dict[int, list[PiLaunchpadCargo]] = defaultdict(list)
            for cargo in cargo_items:
                by_branch[cargo.branch_commodity.type_id].append(cargo)
            detail_lines: list[str] = []
            for branch_items in by_branch.values():
                branch = branch_items[0].branch_commodity
                detail_lines.append(branch.name)
                detail_lines.extend(
                    f"  {cargo.commodity.name} x {cargo.quantity:,}" for cargo in branch_items
                )
                branch_key = f"branch-{index}-{branch.type_id}"
                branch_nodes.append(
                    _DiagramNode(
                        branch_key,
                        branch.name,
                        f"{input_label} {index}\n"
                        + "\n".join(
                            f"{cargo.commodity.name} x {cargo.quantity:,}" for cargo in branch_items
                        ),
                        "source",
                    )
                )
                branch_outputs[branch_key] = {cargo.commodity.type_id for cargo in branch_items}
                branch_roots[branch_key] = branch.type_id
                branch_edges.append((key, branch_key))
            source_nodes.append(
                _DiagramNode(
                    key,
                    f"{input_label} {index}",
                    "\n".join(detail_lines) or "-",
                    "source",
                )
            )
            source_outputs[key] = {cargo.commodity.type_id for cargo in cargo_items}
    elif result.request.operation_mode is PiOperationMode.EXTRACTOR:
        for index, line in enumerate(
            (line for line in result.lines if line.source_quantity > 0), start=1
        ):
            key = f"source-{index}"
            source_nodes.append(
                _DiagramNode(
                    key,
                    f"{extractor_label} · {line.commodity.name}",
                    f"1 {ecu_label} · {result.request.extractor_heads_per_ecu} {heads_label}\n"
                    f"{line.source_quantity:,} units",
                    "source",
                )
            )
            source_outputs[key] = {line.commodity.type_id}
    else:
        for index, line in enumerate(
            (line for line in result.lines if line.import_quantity > 0 or line.source_quantity > 0),
            start=1,
        ):
            key = f"source-{index}"
            quantity = line.import_quantity or line.source_quantity
            source_nodes.append(
                _DiagramNode(key, line.commodity.name, f"{quantity:,} units", "source")
            )
            source_outputs[key] = {line.commodity.type_id}

    routed_outputs = source_outputs
    routing_nodes: list[_DiagramNode] = []
    routing_edges: list[tuple[str, str]] = []
    if result.request.operation_mode is PiOperationMode.IMPORT and fill is not None:
        routed_outputs = branch_outputs
        routing_nodes = branch_nodes
        routing_edges = branch_edges

    stages_by_tier: dict[PiTier, list[_DiagramNode]] = defaultdict(list)
    stages = {stage.commodity.type_id: stage for stage in result.layout}
    lines = {line.commodity.type_id: line for line in result.lines}
    for stage in result.layout:
        plan_line = lines.get(stage.commodity.type_id)
        quantities = (
            f"{plan_line.required:,} {needed_label}\n"
            f"{stage.cycles:,} {cycles_label} → "
            f"{plan_line.planned_output:,} {produced_label}\n"
            if plan_line is not None
            else f"{stage.cycles:,} {cycles_label}\n"
        )
        detail = (
            quantities
            + f"{stage.factories} x {factory_label}"
            + (f"\n{buffer_label}" if stage.buffer_storage else "")
        )
        stages_by_tier[stage.commodity.tier].append(
            _DiagramNode(
                f"stage-{stage.commodity.type_id}", stage.commodity.name, detail, "factory"
            )
        )

    branch_ranks: dict[int, int] = {}
    for rank, branch_key in enumerate(routed_outputs):
        root_type_id = branch_roots.get(branch_key)
        if root_type_id is None:
            continue
        for stage_type_id in _branch_stage_ids(root_type_id, stages):
            branch_ranks[stage_type_id] = min(branch_ranks.get(stage_type_id, rank), rank)
    changed = True
    while changed:
        changed = False
        for producer_type_id, producer_rank in tuple(branch_ranks.items()):
            for consumer in result.layout:
                if producer_type_id not in consumer.input_type_ids:
                    continue
                current = branch_ranks.get(consumer.commodity.type_id)
                if current is None or producer_rank < current:
                    branch_ranks[consumer.commodity.type_id] = producer_rank
                    changed = True

    columns: list[tuple[str, list[_DiagramNode]]] = [(source_label, source_nodes)]
    if routing_nodes:
        columns.append((branch_label, routing_nodes))
    columns.extend(
        (
            tier_labels[tier],
            sorted(
                nodes,
                key=lambda node: (
                    branch_ranks.get(int(node.key.removeprefix("stage-")), 1_000_000),
                    node.title.casefold(),
                ),
            ),
        )
        for tier, nodes in sorted(stages_by_tier.items(), key=lambda item: int(item[0]))
    )
    target_key = "target"
    columns.append(
        (
            launchpad_label,
            [
                _DiagramNode(
                    target_key,
                    result.target.name,
                    f"{result.request.target_quantity:,} units\n"
                    f"{result.target.volume_m3} m³ / unit",
                    "target",
                )
            ],
        )
    )

    edges = list(routing_edges)
    for source_key, output_types in routed_outputs.items():
        root_type_id = branch_roots.get(source_key)
        eligible_stage_ids = (
            _branch_stage_ids(root_type_id, stages) if root_type_id is not None else set(stages)
        )
        for stage in result.layout:
            if stage.commodity.type_id in eligible_stage_ids and output_types.intersection(
                stage.input_type_ids
            ):
                edges.append((source_key, f"stage-{stage.commodity.type_id}"))
    for producer_type_id in stages:
        for consumer in result.layout:
            if producer_type_id in consumer.input_type_ids:
                edges.append((f"stage-{producer_type_id}", f"stage-{consumer.commodity.type_id}"))
    if result.target.type_id in stages:
        edges.append((f"stage-{result.target.type_id}", target_key))
    return columns, edges


def _branch_stage_ids(
    root_type_id: int,
    stages: dict[int, PiLayoutStage],
) -> set[int]:
    if root_type_id not in stages:
        return {
            type_id for type_id, stage in stages.items() if root_type_id in stage.input_type_ids
        }
    result = {root_type_id}
    pending = [root_type_id]
    while pending:
        type_id = pending.pop()
        stage = stages[type_id]
        for input_type_id in stage.input_type_ids:
            if input_type_id in stages and input_type_id not in result:
                result.add(input_type_id)
                pending.append(input_type_id)
    return result


def _add_arrow(scene: QGraphicsScene, start: QPointF, end: QPointF) -> None:
    color = QColor("#75a7df")
    scene.addLine(start.x(), start.y(), end.x(), end.y(), QPen(color, 2))
    arrow = QPolygonF(
        (
            end,
            QPointF(end.x() - 9, end.y() - 5),
            QPointF(end.x() - 9, end.y() + 5),
        )
    )
    scene.addPolygon(arrow, QPen(color), QBrush(color))
