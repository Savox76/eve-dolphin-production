"""Application composition root and executable entry point."""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from eve_dolphin import __version__
from eve_dolphin.app.logging import configure_logging
from eve_dolphin.app.paths import AppPaths
from eve_dolphin.characters import CharacterRepository
from eve_dolphin.database import Database
from eve_dolphin.i18n import Translator
from eve_dolphin.sso.pkce import generate_pkce_pair
from eve_dolphin.sync.runtime import PhaseTwoSyncRunner
from eve_dolphin.updates import (
    GitHubReleaseClient,
    UpdateInstaller,
    apply_staged_update,
    consume_update_result,
    launch_staged_update,
)
from eve_dolphin.updates.installer import current_installation_dir

LOGGER = logging.getLogger(__name__)
BACKGROUND_SERVICES_DELAY_MS = 500
INSTANCE_LOCK_NAME = "eve-dolphin.instance.lock"


@dataclass(frozen=True, slots=True)
class AppContext:
    paths: AppPaths
    database: Database
    characters: CharacterRepository
    translator: Translator


def build_context(paths: AppPaths, language: str = "de") -> AppContext:
    """Prepare all local services before the UI is shown."""

    paths.ensure_directories()
    database = Database(paths.database_path, paths.backup_dir)
    database.initialize()
    return AppContext(
        paths=paths,
        database=database,
        characters=CharacterRepository(database),
        translator=Translator(language),
    )


def run_self_check(paths: AppPaths) -> int:
    """Validate a packaged build without opening a desktop window."""

    context = build_context(paths)
    if not context.database.is_current():
        return 1
    with context.database.connect() as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    if result is None or result[0] != "ok":
        return 1
    pkce = generate_pkce_pair(bytes(range(32)))
    if len(pkce.verifier) != 43 or len(pkce.challenge) != 43:
        return 1
    print(f"EVE Dolphin {__version__}: OK (schema {context.database.schema_version()})")
    return 0


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="eve-dolphin")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--language", choices=("de", "en"), default="de")
    parser.add_argument("--apply-update", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--update-source", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--update-target", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--wait-pid", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--restart", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_arguments(sys.argv[1:] if arguments is None else arguments)

    if options.apply_update:
        if (
            options.update_source is None
            or options.update_target is None
            or options.wait_pid is None
        ):
            return 2
        try:
            return apply_staged_update(
                options.update_source,
                options.update_target,
                wait_pid=options.wait_pid,
                restart=options.restart,
            )
        except Exception:
            LOGGER.exception("Packaged update application failed")
            return 1

    if options.self_check and options.data_dir is None:
        with TemporaryDirectory(prefix="eve-dolphin-check-") as temporary_dir:
            return run_self_check(AppPaths.in_directory(Path(temporary_dir)))

    paths = (
        AppPaths.in_directory(options.data_dir)
        if options.data_dir is not None
        else AppPaths.for_current_user()
    )
    if options.self_check:
        return run_self_check(paths)

    paths.ensure_directories()
    from PySide6.QtCore import QLockFile, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox

    from eve_dolphin.ui import MainWindow
    from eve_dolphin.ui.theme import apply_theme

    application = QApplication([sys.argv[0]])
    application.setApplicationName("EVE Dolphin")
    application.setApplicationVersion(__version__)
    apply_theme(application)

    instance_lock = QLockFile(str(paths.data_dir / INSTANCE_LOCK_NAME))
    if not instance_lock.tryLock(0):
        translator = Translator(options.language)
        QMessageBox.information(
            None,
            translator.text("app_already_running_title"),
            translator.text("app_already_running"),
        )
        return 0

    configure_logging(paths.log_dir)
    try:
        context = build_context(paths, options.language)
    except sqlite3.Error:
        LOGGER.exception("Local database initialization failed")
        return 1

    installation_dir = current_installation_dir()
    update_installer = UpdateInstaller(context.paths.update_dir)
    window = MainWindow(
        context.database,
        context.translator,
        context.characters,
        sync_characters=PhaseTwoSyncRunner(
            context.database, context.characters, context.paths.sde_dir
        ).sync_all,
        current_version=__version__,
        check_for_update=GitHubReleaseClient().check,
        stage_update=update_installer.stage,
        launch_update=(
            (lambda staged: launch_staged_update(staged, installation_dir))
            if installation_dir is not None
            else None
        ),
        startup_update_result=consume_update_result(context.paths.update_dir),
    )
    window.show()
    QTimer.singleShot(BACKGROUND_SERVICES_DELAY_MS, window.start_background_services)
    return application.exec()
