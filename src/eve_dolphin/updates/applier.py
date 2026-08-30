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

from eve_dolphin.updates.installer import EXECUTABLE_NAME


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
    try:
        if wait_pid <= 0 or wait_pid == os.getpid():
            raise UpdateApplyError("update parent PID is invalid")
        if not _wait_for_process(wait_pid, 90.0):
            raise UpdateApplyError("running application did not stop in time")

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        backup = target.parent / f".{target.name}-backup-{timestamp}"
        if backup.exists():
            raise UpdateApplyError("update backup path already exists")
        target.rename(backup)
    except Exception:
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
        if restart:
            _restart(target / EXECUTABLE_NAME)
        if isinstance(error, UpdateApplyError):
            raise
        raise UpdateApplyError("update replacement failed") from error

    # A successful, self-checked update must not be rolled back only because an
    # antivirus scanner temporarily retains a handle in the disposable backup.
    with suppress(OSError):
        shutil.rmtree(backup)
    if restart:
        _restart(target / EXECUTABLE_NAME)
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
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        subprocess.Popen([str(executable)], close_fds=True, creationflags=flags)
    else:
        subprocess.Popen([str(executable)], close_fds=True, start_new_session=True)
