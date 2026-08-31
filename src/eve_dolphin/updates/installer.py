"""Download, verify, stage and launch a packaged EVE Dolphin update."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

import httpx

from eve_dolphin import __version__
from eve_dolphin.updates.models import ReleaseInfo, StagedUpdate
from eve_dolphin.updates.status import UpdateStateStatus, write_update_state

MAX_EXTRACTED_BYTES = 1_500 * 1024 * 1024
MAX_ARCHIVE_FILES = 10_000
EXECUTABLE_NAME = "EVE-Dolphin.exe"
BUILD_INFO_NAME = "build-info.json"
DownloadProgress = Callable[[int, int], None]


class UpdatePackageError(ValueError):
    """A downloaded update package failed integrity or structure validation."""


class UpdateDownloadError(RuntimeError):
    """The release package could not be downloaded from GitHub."""


class UpdateInstaller:
    def __init__(self, update_dir: Path, client: httpx.Client | None = None) -> None:
        self._update_dir = update_dir
        self._client = client

    def stage(
        self,
        release: ReleaseInfo,
        progress: DownloadProgress | None = None,
    ) -> StagedUpdate:
        self._update_dir.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="download-", dir=self._update_dir) as temporary:
            temporary_dir = Path(temporary)
            archive_path = temporary_dir / release.asset.name
            self._download(release, archive_path, progress)
            extracted_dir = temporary_dir / "extracted"
            extracted_dir.mkdir()
            _extract_safely(archive_path, extracted_dir)
            package_dir = _find_package_root(extracted_dir)
            _verify_build_info(package_dir, str(release.version))

            final_dir = self._update_dir / release.tag_name
            if final_dir.exists():
                _safe_remove_staging(final_dir, self._update_dir)
            shutil.move(str(package_dir), final_dir)
        return StagedUpdate(release, final_dir)

    def _download(
        self,
        release: ReleaseInfo,
        destination: Path,
        progress: DownloadProgress | None,
    ) -> None:
        owned_client = self._client is None
        client = self._client or httpx.Client(
            timeout=httpx.Timeout(120.0, connect=15.0),
            follow_redirects=True,
            headers={"User-Agent": f"EVE-Dolphin/{__version__} (update download)"},
        )
        digest = hashlib.sha256()
        total = 0
        try:
            with client.stream("GET", release.asset.download_url) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        announced_size = int(content_length)
                    except ValueError as error:
                        raise UpdatePackageError("update Content-Length is invalid") from error
                    if announced_size != release.asset.size:
                        raise UpdatePackageError("update size differs from release metadata")
                if progress is not None:
                    progress(0, release.asset.size)
                with destination.open("wb") as target:
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > release.asset.size:
                            raise UpdatePackageError("update download exceeds announced size")
                        digest.update(chunk)
                        target.write(chunk)
                        if progress is not None:
                            progress(total, release.asset.size)
        except httpx.HTTPError as error:
            raise UpdateDownloadError("update download failed") from error
        finally:
            if owned_client:
                client.close()
        if total != release.asset.size:
            raise UpdatePackageError("update download is incomplete")
        if digest.hexdigest() != release.asset.sha256:
            raise UpdatePackageError("update SHA-256 verification failed")


def launch_staged_update(
    staged: StagedUpdate,
    installation_dir: Path,
    *,
    parent_pid: int | None = None,
) -> None:
    source = staged.package_dir.resolve()
    target = installation_dir.resolve()
    executable = source / EXECUTABLE_NAME
    if not executable.is_file():
        raise UpdatePackageError("staged update executable is missing")
    arguments = [
        str(executable),
        "--apply-update",
        "--update-source",
        str(source),
        "--update-target",
        str(target),
        "--wait-pid",
        str(parent_pid or os.getpid()),
        "--restart",
    ]
    update_dir = source.parent
    with suppress(OSError):
        write_update_state(
            update_dir,
            UpdateStateStatus.APPLYING,
            str(staged.release.version),
        )
    try:
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            subprocess.Popen(
                arguments,
                close_fds=True,
                creationflags=creation_flags,
                cwd=str(update_dir),
            )
        else:
            subprocess.Popen(
                arguments,
                close_fds=True,
                start_new_session=True,
                cwd=str(update_dir),
            )
    except Exception:
        with suppress(OSError):
            write_update_state(
                update_dir,
                UpdateStateStatus.FAILED,
                str(staged.release.version),
                error_code="launch",
            )
        raise


def current_installation_dir() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    executable = Path(sys.executable).resolve()
    return executable.parent if executable.name.casefold() == EXECUTABLE_NAME.casefold() else None


def _extract_safely(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if not members or len(members) > MAX_ARCHIVE_FILES:
            raise UpdatePackageError("update archive file count is invalid")
        total_size = sum(member.file_size for member in members)
        if total_size <= 0 or total_size > MAX_EXTRACTED_BYTES:
            raise UpdatePackageError("update archive expands beyond the allowed size")
        for member in members:
            relative = _safe_member_path(member)
            target = destination.joinpath(*relative.parts)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)


def _safe_member_path(member: zipfile.ZipInfo) -> PurePosixPath:
    normalized = member.filename.replace("\\", "/")
    relative = PurePosixPath(normalized)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        raise UpdatePackageError("update archive contains an unsafe path")
    if ":" in relative.parts[0]:
        raise UpdatePackageError("update archive contains a drive path")
    unix_mode = member.external_attr >> 16
    if unix_mode and stat.S_ISLNK(unix_mode):
        raise UpdatePackageError("update archive contains a symbolic link")
    return relative


def _find_package_root(extracted_dir: Path) -> Path:
    direct = extracted_dir / EXECUTABLE_NAME
    nested = extracted_dir / "EVE-Dolphin" / EXECUTABLE_NAME
    if direct.is_file():
        return extracted_dir
    if nested.is_file():
        return nested.parent
    raise UpdatePackageError("update archive has no EVE Dolphin package root")


def _verify_build_info(package_dir: Path, expected_version: str) -> None:
    path = package_dir / BUILD_INFO_NAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise UpdatePackageError("update build information is missing or invalid") from error
    if not isinstance(payload, dict) or payload.get("version") != expected_version:
        raise UpdatePackageError("update build version does not match the release")
    if payload.get("distribution_repository") != "Savox76/eve-dolphin-production":
        raise UpdatePackageError("update build has an unexpected distribution source")


def _safe_remove_staging(path: Path, staging_root: Path) -> None:
    resolved = path.resolve()
    root = staging_root.resolve()
    if resolved.parent != root or not resolved.name.startswith("v"):
        raise UpdatePackageError("refusing to remove an unsafe staging path")
    shutil.rmtree(resolved)
