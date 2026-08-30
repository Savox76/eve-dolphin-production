"""Non-blocking update workers and the user-controlled update dialog."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from eve_dolphin.i18n import Translator
from eve_dolphin.updates import ReleaseInfo, StagedUpdate

CheckForUpdate = Callable[[], ReleaseInfo | None]
StageUpdate = Callable[[ReleaseInfo], StagedUpdate]


class UpdateCheckWorker(QThread):
    completed = Signal(object)
    failed = Signal()

    def __init__(self, check: CheckForUpdate, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._check = check

    def run(self) -> None:
        try:
            release = self._check()
        except Exception:
            self.failed.emit()
        else:
            self.completed.emit(release)


class UpdateStageWorker(QThread):
    completed = Signal(object)
    failed = Signal()

    def __init__(
        self,
        stage: StageUpdate,
        release: ReleaseInfo,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._stage = stage
        self._release = release

    def run(self) -> None:
        try:
            staged = self._stage(self._release)
        except Exception:
            self.failed.emit()
        else:
            self.completed.emit(staged)


class UpdateDialog(QDialog):
    start_requested = Signal()

    def __init__(
        self,
        release: ReleaseInfo,
        current_version: str,
        translator: Translator,
        *,
        installation_enabled: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._translator = translator
        self.setObjectName("updateDialog")
        self.setWindowTitle(translator.text("update_available_title"))
        self.setMinimumSize(580, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel(translator.text("update_available_title"))
        title.setObjectName("pageTitle")
        versions = QLabel(
            translator.text("update_versions").format(
                current=current_version,
                new=str(release.version),
            )
        )
        versions.setObjectName("cardTitle")
        metadata = QLabel(
            translator.text("update_metadata").format(
                date=release.published_at.astimezone(UTC).strftime("%Y-%m-%d"),
                size=_format_size(release.asset.size),
            )
        )
        metadata.setObjectName("muted")

        notes_title = QLabel(translator.text("update_contents"))
        notes_title.setObjectName("cardTitle")
        notes = QTextBrowser()
        notes.setObjectName("releaseNotes")
        notes.setOpenExternalLinks(False)
        notes.setMarkdown(release.notes or translator.text("update_no_notes"))

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        self.start_button = QPushButton(translator.text("update_start"))
        self.start_button.setObjectName("startUpdateButton")
        self.start_button.setEnabled(installation_enabled)
        self.later_button = QPushButton(translator.text("update_later"))
        self.later_button.clicked.connect(self.reject)
        self.start_button.clicked.connect(self.start_requested.emit)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.later_button)
        actions.addWidget(self.start_button)

        layout.addWidget(title)
        layout.addWidget(versions)
        layout.addWidget(metadata)
        layout.addWidget(notes_title)
        layout.addWidget(notes, 1)
        if not installation_enabled:
            self.status_label.setText(translator.text("update_install_unavailable"))
        layout.addWidget(self.status_label)
        layout.addLayout(actions)

    def set_installing(self) -> None:
        self.start_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.status_label.setText(self._translator.text("update_downloading"))

    def set_failed(self) -> None:
        self.start_button.setEnabled(True)
        self.later_button.setEnabled(True)
        self.status_label.setText(self._translator.text("update_failed"))


def _format_size(size: int) -> str:
    return f"{size / (1024 * 1024):.1f} MB"
