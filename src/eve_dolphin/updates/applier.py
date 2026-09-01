"""Out-of-process replacement with packaged self-check and rollback."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from eve_dolphin import __version__
from eve_dolphin.updates.installer import EXECUTABLE_NAME
from eve_dolphin.updates.status import UpdateStateStatus, write_update_state

PARENT_EXIT_TIMEOUT_SECONDS = 10 * 60.0


class UpdateApplyError(RuntimeError):
    """The staged package could not safely replace the active installation."""


def apply_staged_update(
    source_dir: Path,
    target_dir: Path,
    *,
    wait_pid: int,
    restart: bool,
) -> int:
    source, target = _validate_directories(source_dir, target_dir)
    update_dir = source.parent
    _record_state(update_dir, UpdateStateStatus.APPLYING)
    try:
        # A v0.3.0 launcher can start this helper with the installation directory
        # as its inherited CWD. Windows then refuses to rename that directory.
        os.chdir(update_dir)
        if wait_pid <= 0 or wait_pid == os.getpid():
            raise UpdateApplyError("update parent PID is invalid")
        # Older clients can still have an EVE synchronization in progress after
        # staging. The downloaded helper is already the new version, so give
        # that legacy client enough time to finish cleanly instead of restoring
        # and relaunching the old installation after only 90 seconds.
        if not _wait_for_process(wait_pid, PARENT_EXIT_TIMEOUT_SECONDS):
            raise UpdateApplyError("running application did not stop in time")

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        backup = target.parent / f".{target.name}-backup-{timestamp}"
        if backup.exists():
            raise UpdateApplyError("update backup path already exists")
        target.rename(backup)
    except Exception as error:
        _record_state(
            update_dir,
            UpdateStateStatus.FAILED,
            error_code=_error_code(error),
        )
        if restart and (target / EXECUTABLE_NAME).is_file():
            _restart(target / EXECUTABLE_NAME)
        raise

    installed = False
    try:
        shutil.copytree(source, target)
        installed = True
        result = subprocess.run(
            [str(target / EXECUTABLE_NAME), "--self-check"],
            check=False,
            timeout=180,
        )
        if result.returncode != 0:
            raise UpdateApplyError("updated application failed its packaged self-check")
    except Exception as error:
        if installed and target.exists():
            shutil.rmtree(target)
        backup.rename(target)
        _record_state(
            update_dir,
            UpdateStateStatus.FAILED,
            error_code=_error_code(error),
        )
        if restart:
            _restart(target / EXECUTABLE_NAME)
        if isinstance(error, UpdateApplyError):
            raise
        raise UpdateApplyError("update replacement failed") from error

    # A successful, self-checked update must not be rolled back only because an
    # antivirus scanner temporarily retains a handle in the disposable backup.
    with suppress(OSError):
        shutil.rmtree(backup)
    _record_state(update_dir, UpdateStateStatus.SUCCEEDED)
    if restart:
        try:
            _restart(target / EXECUTABLE_NAME)
        except OSError as error:
            _record_state(update_dir, UpdateStateStatus.FAILED, error_code="launch")
            raise UpdateApplyError("updated application could not be restarted") from error
    return 0


def _validate_directories(source_dir: Path, target_dir: Path) -> tuple[Path, Path]:
    source = source_dir.resolve()
    target = target_dir.resolve()
    if not source.is_dir() or not (source / EXECUTABLE_NAME).is_file():
        raise UpdateApplyError("staged update directory is invalid")
    if not target.is_dir() or not (target / EXECUTABLE_NAME).is_file():
        raise UpdateApplyError("installation directory is invalid")
    if source == target or source in target.parents or target in source.parents:
        raise UpdateApplyError("update source and target directories overlap")
    anchor = Path(target.anchor).resolve()
    if target == anchor or target == Path.home().resolve():
        raise UpdateApplyError("installation directory is too broad")
    return source, target


def _wait_for_process(pid: int, timeout_seconds: float) -> bool:
    if sys.platform == "win32":
        synchronize = 0x00100000
        wait_object_0 = 0x00000000
        wait_timeout = 0x00000102
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(synchronize, False, pid)
        if not handle:
            return True
        try:
            milliseconds = max(1, min(int(timeout_seconds * 1000), 0xFFFFFFFE))
            result = kernel32.WaitForSingleObject(handle, milliseconds)
            if result == wait_object_0:
                return True
            if result == wait_timeout:
                return False
            raise UpdateApplyError("could not wait for the running application")
        finally:
            kernel32.CloseHandle(handle)

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            pass
        time.sleep(0.1)
    return False


def _restart(executable: Path) -> None:
    if sys.platform == "win32":
        _shell_execute_windows(executable)
    else:
        subprocess.Popen(
            [str(executable)],
            close_fds=True,
            start_new_session=True,
            cwd=str(executable.parent),
        )


def _shell_execute_windows(executable: Path) -> None:
    """Start the installed GUI through Explorer's normal application launch path."""

    result = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
        None,
        "open",
        str(executable),
        None,
        str(executable.parent),
        1,
    )
    if int(result) <= 32:
        raise OSError(f"Windows could not restart the updated application ({result})")


def _record_state(
    update_dir: Path,
    status: UpdateStateStatus,
    *,
    error_code: str | None = None,
) -> None:
    with suppress(OSError):
        write_update_state(
            update_dir,
            status,
            __version__,
            error_code=error_code,
        )


def _error_code(error: BaseException) -> str:
    if isinstance(error, OSError):
        return "filesystem"
    message = str(error)
    if "did not stop" in message:
        return "parent-timeout"
    if "self-check" in message:
        return "self-check"
    if "backup" in message:
        return "backup"
    if "directory" in message or "PID" in message:
        return "validation"
    return "replacement"
