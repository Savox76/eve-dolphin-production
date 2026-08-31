"""Non-blocking update workers and the user-controlled update dialog."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from eve_dolphin.i18n import Translator
from eve_dolphin.updates import (
    ReleaseInfo,
    StagedUpdate,
    UpdateDownloadError,
    UpdatePackageError,
)

CheckForUpdate = Callable[[], ReleaseInfo | None]
DownloadProgress = Callable[[int, int], None]
StageUpdate = Callable[[ReleaseInfo, DownloadProgress], StagedUpdate]
LOGGER = logging.getLogger(__name__)


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
    failed = Signal(str)
    progress = Signal(int)

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
            staged = self._stage(self._release, self._report_progress)
        except Exception as error:
            LOGGER.exception("Update download or staging failed")
            self.failed.emit(_failure_code(error))
        else:
            self.completed.emit(staged)

    def _report_progress(self, downloaded: int, total: int) -> None:
        percentage = 0 if total <= 0 else min(100, max(0, int(downloaded * 100 / total)))
        self.progress.emit(percentage)


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
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
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
        layout.addWidget(self.progress_bar)
        layout.addLayout(actions)

    def set_installing(self) -> None:
        self.start_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.status_label.setText(self._translator.text("update_downloading"))
        self.progress_bar.setValue(0)
        self.progress_bar.show()

    def set_progress(self, percentage: int) -> None:
        self.progress_bar.setValue(percentage)
        if percentage >= 100:
            self.status_label.setText(self._translator.text("update_preparing"))
        else:
            self.status_label.setText(
                self._translator.text("update_download_progress").format(percentage=percentage)
            )

    def set_failed(self, reason: str) -> None:
        self.start_button.setEnabled(True)
        self.later_button.setEnabled(True)
        self.progress_bar.hide()
        detail_key = {
            "network": "update_error_network",
            "package": "update_error_package",
            "filesystem": "update_error_filesystem",
            "launch": "update_error_launch",
        }.get(reason, "update_error_unexpected")
        self.status_label.setText(
            self._translator.text("update_failed").format(reason=self._translator.text(detail_key))
        )


def _format_size(size: int) -> str:
    return f"{size / (1024 * 1024):.1f} MB"


def _failure_code(error: BaseException) -> str:
    if isinstance(error, UpdateDownloadError):
        return "network"
    if isinstance(error, UpdatePackageError):
        return "package"
    if isinstance(error, OSError):
        return "filesystem"
    return "unexpected"
