"""Compact graphical material-flow view for PI target plans."""

from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF, QResizeEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from eve_dolphin.pi import PiOperationMode, PiPlanResult, PiTier


class PiLayoutDiagram(QGraphicsView):
    """Render source, processing tiers, buffers, and launchpad as a small flow graph."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("piLayoutDiagram")
        self.setMinimumHeight(230)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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
    ) -> None:
        scene = self.scene()
        scene.clear()
        stages_by_tier: dict[PiTier, list[tuple[str, int, bool]]] = defaultdict(list)
        for stage in result.layout:
            stages_by_tier[stage.commodity.tier].append(
                (stage.commodity.name, stage.factories, stage.buffer_storage)
            )

        columns: list[tuple[str, list[tuple[str, int, bool]]]] = [
            (
                source_label,
                [
                    (
                        (
                            "P0"
                            if result.request.operation_mode is PiOperationMode.EXTRACTOR
                            else tier_labels[
                                result.request.source_tier
                                if result.request.source_tier is not None
                                else PiTier.RAW
                            ]
                        ),
                        0,
                        False,
                    )
                ],
            )
        ]
        for tier in sorted(stages_by_tier):
            columns.append((tier_labels[tier], stages_by_tier[tier]))
        columns.append((launchpad_label, [(result.target.name, 0, False)]))

        box_width = 170.0
        box_height = 78.0
        column_gap = 74.0
        row_gap = 18.0
        margin = 24.0
        max_rows = max(len(items) for _, items in columns)
        canvas_height = max(190.0, margin * 2 + max_rows * box_height + (max_rows - 1) * row_gap)
        centers: list[QPointF] = []

        for column, (heading, items) in enumerate(columns):
            x = margin + column * (box_width + column_gap)
            total_height = len(items) * box_height + max(0, len(items) - 1) * row_gap
            y = (canvas_height - total_height) / 2
            heading_item = scene.addText(heading)
            heading_font = QFont(heading_item.font())
            heading_font.setBold(True)
            heading_item.setFont(heading_font)
            heading_item.setDefaultTextColor(QColor("#9fb5d8"))
            heading_item.setPos(x, 2)
            for index, (name, factories, buffered) in enumerate(items):
                top = y + index * (box_height + row_gap)
                rect = QRectF(x, top, box_width, box_height)
                brush = QBrush(QColor("#17345a" if 0 < column < len(columns) - 1 else "#24445a"))
                scene.addRect(rect, QPen(QColor("#4f7fb3"), 1.4), brush)
                detail = name
                if factories:
                    detail = f"{name}\n{factories} x {factory_label}"
                text_item = scene.addText(detail)
                text_item.setDefaultTextColor(QColor("#f1f6ff"))
                text_item.setTextWidth(box_width - 16)
                text_item.setPos(x + 8, top + 8)
                if buffered:
                    buffer_item = scene.addText(buffer_label)
                    small_font = QFont(buffer_item.font())
                    small_font.setPointSize(max(7, small_font.pointSize() - 2))
                    buffer_item.setFont(small_font)
                    buffer_item.setDefaultTextColor(QColor("#f2bf63"))
                    buffer_item.setPos(x + 8, top + box_height - 20)
            centers.append(QPointF(x + box_width / 2, canvas_height / 2))

        for index in range(len(centers) - 1):
            start = QPointF(centers[index].x() + box_width / 2, centers[index].y())
            end = QPointF(centers[index + 1].x() - box_width / 2, centers[index + 1].y())
            _add_arrow(scene, start, end)

        canvas_width = margin * 2 + len(columns) * box_width + (len(columns) - 1) * column_gap
        scene.setSceneRect(0, 0, canvas_width, canvas_height)
        self.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def clear_plan(self) -> None:
        self.scene().clear()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if not self.scene().sceneRect().isEmpty():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


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
