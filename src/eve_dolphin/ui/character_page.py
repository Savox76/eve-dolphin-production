"""Visible local character management and background EVE SSO handoff."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import UTC

import httpx
from keyring.errors import KeyringError
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eve_dolphin.characters import (
    AuthorizationStatus,
    BrowserLaunchError,
    CharacterLinkService,
    CharacterRepository,
    CharacterSsoFlow,
    EveCharacter,
    UnexpectedCharacterError,
)
from eve_dolphin.characters.service import SsoAuthorizationError
from eve_dolphin.i18n import Translator
from eve_dolphin.security import KeyringTokenStore
from eve_dolphin.sso.callback import (
    CallbackCancelledError,
    CallbackStateMismatchError,
    CallbackTimeoutError,
)
from eve_dolphin.sso.client import EveSsoClient
from eve_dolphin.sso.config import SsoConfig, SsoConfigurationError
from eve_dolphin.sso.scopes import ScopePackage, scopes_for_packages
from eve_dolphin.sso.transport import OAuthTokenRequestError
from eve_dolphin.sso.validation import AccessTokenValidationError, EveAccessTokenValidator
from eve_dolphin.sync.coordinator import CharacterSyncBatch

LOGGER = logging.getLogger(__name__)

ConfirmUnlink = Callable[[EveCharacter], bool]
UnlinkCharacter = Callable[[int], bool]
SyncCharacters = Callable[[], CharacterSyncBatch]
AUTOMATIC_SYNC_INTERVAL_MS = 5 * 60 * 1000


class CharacterSsoWorker(QThread):
    """Run browser authorization and token work away from the Qt UI thread."""

    authorization_ready = Signal(str)
    character_linked = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        repository: CharacterRepository,
        scopes: Sequence[str] = (),
        expected_character_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._scopes = tuple(scopes)
        self._expected_character_id = expected_character_id

    def run(self) -> None:
        try:
            config = SsoConfig.from_environment()
            sso_client = EveSsoClient()
            link_service = CharacterLinkService(
                self._repository,
                KeyringTokenStore(),
                sso_client,
                EveAccessTokenValidator(),
                expected_character_id=self._expected_character_id,
            )
            flow = CharacterSsoFlow(sso_client, link_service)
            character = flow.link_character(
                config,
                scopes=self._scopes,
                authorization_ready=self.authorization_ready.emit,
                cancelled=self.isInterruptionRequested,
            )
        except SsoConfigurationError:
            self.failed.emit("sso_client_id_missing")
        except BrowserLaunchError:
            self.failed.emit("sso_browser_failed")
        except CallbackTimeoutError:
            self.failed.emit("sso_timeout")
        except CallbackCancelledError:
            return
        except UnexpectedCharacterError:
            self.failed.emit("sso_wrong_character")
        except SsoAuthorizationError:
            self.failed.emit("sso_cancelled")
        except (CallbackStateMismatchError, AccessTokenValidationError):
            self.failed.emit("sso_invalid_response")
        except (httpx.HTTPError, OSError):
            self.failed.emit("sso_network_failed")
        except OAuthTokenRequestError:
            self.failed.emit("sso_invalid_response")
        except KeyringError:
            self.failed.emit("sso_keyring_failed")
        except Exception:
            LOGGER.exception("EVE SSO character linking failed")
            self.failed.emit("sso_failed")
        else:
            self.character_linked.emit(character)


class DataSyncWorker(QThread):
    """Run the complete multi-character synchronization away from the UI thread."""

    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, synchronize: SyncCharacters, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._synchronize = synchronize

    def run(self) -> None:
        try:
            result = self._synchronize()
        except SsoConfigurationError:
            self.failed.emit("sso_client_id_missing")
        except KeyringError:
            self.failed.emit("sso_keyring_failed")
        except (httpx.HTTPError, OSError):
            self.failed.emit("sync_network_failed")
        except Exception:
            LOGGER.exception("EVE character data synchronization failed")
            self.failed.emit("sync_failed")
        else:
            self.completed.emit(result)


class CharacterPage(QWidget):
    """List, connect and safely unlink the characters stored by this installation."""

    characters_changed = Signal()
    data_changed = Signal()
    authorization_stopped = Signal()

    def __init__(
        self,
        repository: CharacterRepository,
        translator: Translator,
        confirm_unlink: ConfirmUnlink | None = None,
        unlink_character: UnlinkCharacter | None = None,
        sync_characters: SyncCharacters | None = None,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._translator = translator
        self._confirm_unlink = confirm_unlink or self._show_unlink_confirmation
        self._unlink_character = unlink_character or self._unlink_local_character
        self._sync_characters = sync_characters
        self._worker: CharacterSsoWorker | None = None
        self._sync_worker: DataSyncWorker | None = None
        self._sync_after_authorization = False
        self._automatic_sync_active = False
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(AUTOMATIC_SYNC_INTERVAL_MS)
        self._sync_timer.timeout.connect(self._start_sync)

        self.table = QTableWidget(0, 4)
        self.table.setObjectName("characterTable")
        self.connect_button = QPushButton(self._translator.text("connect_character"))
        self.connect_button.setObjectName("connectCharacterButton")
        self.unlink_button = QPushButton(self._translator.text("unlink_character"))
        self.unlink_button.setObjectName("unlinkCharacterButton")
        self.industry_button = QPushButton(self._translator.text("authorize_industry"))
        self.industry_button.setObjectName("authorizeIndustryButton")
        self.planetary_button = QPushButton(self._translator.text("authorize_planetary"))
        self.planetary_button.setObjectName("authorizePlanetaryButton")
        self.sync_button = QPushButton(self._translator.text("sync_data"))
        self.sync_button.setObjectName("syncDataButton")
        self.status_label = QLabel()
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)

        self._build_layout()
        self.table.itemSelectionChanged.connect(self._update_selection)
        self.connect_button.clicked.connect(self._start_new_character_authorization)
        self.unlink_button.clicked.connect(self._unlink_selected)
        self.industry_button.clicked.connect(self._authorize_industry)
        self.planetary_button.clicked.connect(self._authorize_planetary)
        self.sync_button.clicked.connect(self._start_sync)
        self.refresh()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(18)

        title = QLabel(self._translator.text("settings"))
        title.setObjectName("pageTitle")
        detail = QLabel(self._translator.text("characters_page_detail"))
        detail.setObjectName("muted")
        detail.setWordWrap(True)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        card_title = QLabel(self._translator.text("connected_characters"))
        card_title.setObjectName("cardTitle")
        self.table.setHorizontalHeaderLabels(
            (
                self._translator.text("character_name"),
                self._translator.text("scope_count"),
                self._translator.text("authorization_status"),
                self._translator.text("linked_at"),
            )
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        actions = QHBoxLayout()
        actions.addWidget(self.connect_button)
        actions.addWidget(self.industry_button)
        actions.addWidget(self.planetary_button)
        actions.addWidget(self.sync_button)
        actions.addWidget(self.unlink_button)
        actions.addStretch(1)

        card_layout.addWidget(card_title)
        card_layout.addWidget(self.table)
        card_layout.addLayout(actions)
        card_layout.addWidget(self.status_label)

        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addWidget(card, 1)

    def refresh(self) -> None:
        characters = self._repository.list_all()
        self.table.setRowCount(len(characters))
        for row, character in enumerate(characters):
            name = QTableWidgetItem(character.character_name)
            name.setData(Qt.ItemDataRole.UserRole, character.character_id)
            scope_count = QTableWidgetItem(str(len(character.granted_scopes)))
            authorization_status = QTableWidgetItem(
                self._translator.text(
                    "authorization_active"
                    if character.authorization_status is AuthorizationStatus.ACTIVE
                    else "authorization_required"
                )
            )
            linked_at = QTableWidgetItem(
                character.linked_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
            )
            self.table.setItem(row, 0, name)
            self.table.setItem(row, 1, scope_count)
            self.table.setItem(row, 2, authorization_status)
            self.table.setItem(row, 3, linked_at)
        self.table.clearSelection()
        self._update_selection()
        self.status_label.setText(
            self._translator.text("character_count").format(count=len(characters))
        )

    @Slot()
    def _start_new_character_authorization(self) -> None:
        self._start_authorization(
            scopes_for_packages(ScopePackage.INDUSTRY, ScopePackage.PLANETARY_INDUSTRY),
            None,
        )

    def _start_authorization(
        self, scopes: Sequence[str], expected_character_id: int | None
    ) -> None:
        if self._worker is not None or self._sync_worker is not None:
            return
        self._set_actions_enabled(False)
        self.status_label.setText(self._translator.text("sso_preparing"))
        worker = CharacterSsoWorker(
            self._repository,
            scopes,
            expected_character_id,
            self,
        )
        self._worker = worker
        worker.authorization_ready.connect(self._authorization_ready)
        worker.character_linked.connect(self._character_linked)
        worker.failed.connect(self._authorization_failed)
        worker.finished.connect(self._authorization_finished)
        worker.start()

    @Slot()
    def _authorize_industry(self) -> None:
        self._authorize_selected(ScopePackage.INDUSTRY)

    @Slot()
    def _authorize_planetary(self) -> None:
        self._authorize_selected(ScopePackage.PLANETARY_INDUSTRY)

    def _authorize_selected(self, package: ScopePackage) -> None:
        character_id = self._selected_character_id()
        if character_id is None:
            return
        character = self._repository.get(character_id)
        if character is None:
            self.refresh()
            return
        scopes = tuple(dict.fromkeys((*character.granted_scopes, *scopes_for_packages(package))))
        self._start_authorization(scopes, character_id)

    @Slot(str)
    def _authorization_ready(self, _url: str) -> None:
        self.status_label.setText(self._translator.text("sso_browser_waiting"))

    @Slot(object)
    def _character_linked(self, character: object) -> None:
        if not isinstance(character, EveCharacter):
            self.status_label.setText(self._translator.text("sso_failed"))
            return
        self.refresh()
        self.status_label.setText(
            self._translator.text("sso_linked").format(name=character.character_name)
        )
        self._sync_after_authorization = True
        self.characters_changed.emit()

    @Slot(str)
    def _authorization_failed(self, translation_key: str) -> None:
        self.status_label.setText(self._translator.text(translation_key))

    @Slot()
    def _authorization_finished(self) -> None:
        worker = self._worker
        self._worker = None
        self._update_selection()
        if worker is not None:
            worker.deleteLater()
        self.authorization_stopped.emit()
        if self._sync_after_authorization:
            self._sync_after_authorization = False
            QTimer.singleShot(0, self._start_sync)

    @Slot()
    def _update_selection(self) -> None:
        busy = self._worker is not None or self._sync_worker is not None
        character_id = self._selected_character_id()
        character = self._repository.get(character_id) if character_id is not None else None
        granted = set(character.granted_scopes) if character is not None else set()
        industry_missing = set(scopes_for_packages(ScopePackage.INDUSTRY)) - granted
        planetary_missing = set(scopes_for_packages(ScopePackage.PLANETARY_INDUSTRY)) - granted
        self.connect_button.setEnabled(not busy)
        self.unlink_button.setEnabled(not busy and character is not None)
        self.industry_button.setEnabled(
            not busy and character is not None and bool(industry_missing)
        )
        self.planetary_button.setEnabled(
            not busy and character is not None and bool(planetary_missing)
        )
        self.sync_button.setEnabled(
            not busy and self._sync_characters is not None and self.table.rowCount() > 0
        )

    def _set_actions_enabled(self, enabled: bool) -> None:
        for button in (
            self.connect_button,
            self.unlink_button,
            self.industry_button,
            self.planetary_button,
            self.sync_button,
        ):
            button.setEnabled(enabled)

    @Slot()
    def _start_sync(self) -> None:
        if (
            self._sync_characters is None
            or self._worker is not None
            or self._sync_worker is not None
        ):
            return
        self._set_actions_enabled(False)
        self.status_label.setText(self._translator.text("sync_running"))
        worker = DataSyncWorker(self._sync_characters, self)
        self._sync_worker = worker
        worker.completed.connect(self._sync_completed)
        worker.failed.connect(self._sync_failed)
        worker.finished.connect(self._sync_finished)
        worker.start()

    @Slot(str)
    def _sync_failed(self, translation_key: str) -> None:
        self.status_label.setText(self._translator.text(translation_key))
        self.data_changed.emit()

    @Slot(object)
    def _sync_completed(self, result: object) -> None:
        if not isinstance(result, CharacterSyncBatch):
            self.status_label.setText(self._translator.text("sync_failed"))
            return
        if result.global_failures:
            message = self._translator.text("sync_sde_failed")
        elif not result.outcomes:
            message = self._translator.text("no_characters")
        elif result.missing_scopes:
            message = self._translator.text("sync_permissions_missing")
        elif result.failed_count:
            message = self._translator.text("sync_partial").format(
                succeeded=result.succeeded_count,
                count=len(result.outcomes),
            )
        else:
            key = "sync_complete_auto" if self._automatic_sync_active else "sync_complete"
            message = self._translator.text(key).format(count=result.succeeded_count)
        self.refresh()
        self.status_label.setText(message)
        self.data_changed.emit()

    @Slot()
    def _sync_finished(self) -> None:
        worker = self._sync_worker
        self._sync_worker = None
        self._update_selection()
        if worker is not None:
            worker.deleteLater()
        self.authorization_stopped.emit()

    @Slot()
    def _unlink_selected(self) -> None:
        character_id = self._selected_character_id()
        if character_id is None:
            return
        character = self._repository.get(character_id)
        if character is None or not self._confirm_unlink(character):
            return
        try:
            removed = self._unlink_character(character_id)
        except KeyringError:
            self.status_label.setText(self._translator.text("sso_keyring_failed"))
            return
        except Exception:
            LOGGER.exception("Local EVE character unlink failed")
            self.status_label.setText(self._translator.text("unlink_failed"))
            return
        if not removed:
            self.status_label.setText(self._translator.text("character_not_found"))
            return
        self.refresh()
        self.status_label.setText(
            self._translator.text("character_unlinked").format(name=character.character_name)
        )
        self.characters_changed.emit()

    def _selected_character_id(self) -> int | None:
        selected_rows = self.table.selectionModel().selectedRows()
        if len(selected_rows) != 1:
            return None
        item = self.table.item(selected_rows[0].row(), 0)
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, int) and value > 0 else None

    def _show_unlink_confirmation(self, character: EveCharacter) -> bool:
        answer = QMessageBox.question(
            self,
            self._translator.text("unlink_character"),
            self._translator.text("confirm_unlink").format(name=character.character_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _unlink_local_character(self, character_id: int) -> bool:
        KeyringTokenStore().delete_refresh_token(character_id)
        return self._repository.remove(character_id)

    def cancel_pending_authorization(self) -> None:
        self.stop_automatic_sync()
        if self._worker is not None:
            self._worker.requestInterruption()
            self.status_label.setText(self._translator.text("sso_closing"))
        elif self._sync_worker is not None:
            self.status_label.setText(self._translator.text("sync_closing"))

    @property
    def authorization_pending(self) -> bool:
        return self._worker is not None

    @property
    def background_work_pending(self) -> bool:
        return self._worker is not None or self._sync_worker is not None

    def start_automatic_sync(self) -> None:
        """Start the five-minute foreground schedule and refresh existing characters now."""

        if self._sync_characters is None or self._automatic_sync_active:
            return
        self._automatic_sync_active = True
        self._sync_timer.start()
        if self._repository.list_all():
            QTimer.singleShot(0, self._start_sync)
        else:
            self.status_label.setText(self._translator.text("automatic_sync_waiting"))

    def stop_automatic_sync(self) -> None:
        self._automatic_sync_active = False
        self._sync_timer.stop()
