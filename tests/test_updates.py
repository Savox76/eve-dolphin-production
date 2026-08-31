from __future__ import annotations

import hashlib
import io
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import pytest

import eve_dolphin.updates.applier as applier_module
from eve_dolphin.updates.applier import UpdateApplyError, apply_staged_update
from eve_dolphin.updates.client import (
    GitHubReleaseClient,
    ReleaseMetadataError,
)
from eve_dolphin.updates.installer import (
    UpdateInstaller,
    UpdatePackageError,
    launch_staged_update,
)
from eve_dolphin.updates.models import AppVersion, ReleaseAsset, ReleaseInfo, StagedUpdate
from eve_dolphin.updates.status import (
    UpdateStateStatus,
    consume_update_result,
    read_update_state,
)


def test_app_versions_follow_semver_ordering() -> None:
    assert AppVersion.parse("v0.2.0") > AppVersion.parse("0.1.9")
    assert AppVersion.parse("1.0.0") > AppVersion.parse("1.0.0-rc.2")
    assert AppVersion.parse("1.0.0-rc.10") > AppVersion.parse("1.0.0-rc.2")
    assert str(AppVersion.parse("v1.2.3-beta.1")) == "1.2.3-beta.1"


def test_release_client_selects_newest_public_test_version() -> None:
    payload = [
        _release_payload("v0.1.1", prerelease=True),
        _release_payload("v0.2.0", prerelease=True),
        _release_payload("v0.3.0", draft=True),
    ]
    client = GitHubReleaseClient(_json_client(payload))

    release = client.check("0.1.1")

    assert release is not None
    assert str(release.version) == "0.2.0"
    assert release.asset.name == "EVE-Dolphin-Windows-v0.2.0.zip"


def test_release_client_can_ignore_prereleases() -> None:
    client = GitHubReleaseClient(_json_client([_release_payload("v0.2.0", prerelease=True)]))

    assert client.check("0.1.1", include_prereleases=False) is None


def test_release_client_rejects_asset_outside_distribution_repository() -> None:
    payload = _release_payload("v0.2.0")
    assets = payload["assets"]
    assert isinstance(assets, list)
    assets[0]["browser_download_url"] = "https://example.com/EVE-Dolphin.zip"

    with pytest.raises(ReleaseMetadataError, match="outside"):
        GitHubReleaseClient(_json_client([payload])).check("0.1.1")


def test_update_archive_is_verified_and_staged(tmp_path: Path) -> None:
    archive = _archive_bytes("0.2.0")
    release = _release_info(archive)
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            content=archive,
            headers={"Content-Length": str(len(archive))},
        )
    )

    staged = UpdateInstaller(
        tmp_path / "updates",
        httpx.Client(transport=transport, follow_redirects=True),
    ).stage(release)

    assert staged.package_dir == tmp_path / "updates" / "v0.2.0"
    assert (staged.package_dir / "EVE-Dolphin.exe").read_bytes() == b"new-executable"
    build_info = json.loads((staged.package_dir / "build-info.json").read_text("utf-8"))
    assert build_info["version"] == "0.2.0"


def test_update_archive_reports_download_progress(tmp_path: Path) -> None:
    archive = _archive_bytes("0.2.0")
    release = _release_info(archive)
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            content=archive,
            headers={"Content-Length": str(len(archive))},
        )
    )
    progress: list[tuple[int, int]] = []

    UpdateInstaller(
        tmp_path / "updates",
        httpx.Client(transport=transport, follow_redirects=True),
    ).stage(release, lambda downloaded, total: progress.append((downloaded, total)))

    assert progress[0] == (0, len(archive))
    assert progress[-1] == (len(archive), len(archive))


def test_update_archive_rejects_path_traversal(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../outside.exe", b"unsafe")
    payload = buffer.getvalue()
    release = _release_info(payload)
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=payload))

    with pytest.raises(UpdatePackageError, match="unsafe path"):
        UpdateInstaller(tmp_path / "updates", httpx.Client(transport=transport)).stage(release)

    assert not (tmp_path / "outside.exe").exists()


def test_update_archive_rejects_wrong_digest(tmp_path: Path) -> None:
    archive = _archive_bytes("0.2.0")
    release = _release_info(archive, sha256="0" * 64)
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=archive))

    with pytest.raises(UpdatePackageError, match="SHA-256"):
        UpdateInstaller(tmp_path / "updates", httpx.Client(transport=transport)).stage(release)


def test_update_applier_replaces_package_after_self_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = _package_directories(tmp_path)
    restarted: list[Path] = []
    changed_directories: list[Path] = []
    monkeypatch.setattr("eve_dolphin.updates.applier.os.chdir", changed_directories.append)
    monkeypatch.setattr(applier_module, "_wait_for_process", lambda _pid, _timeout: True)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(applier_module, "_restart", restarted.append)

    result = apply_staged_update(source, target, wait_pid=1234, restart=True)

    assert result == 0
    assert (target / "EVE-Dolphin.exe").read_text("utf-8") == "new"
    assert restarted == [target / "EVE-Dolphin.exe"]
    assert changed_directories == [source.parent]
    assert not tuple(tmp_path.glob(".installed-backup-*"))
    state = read_update_state(source.parent)
    assert state is not None
    assert state.status is UpdateStateStatus.SUCCEEDED


def test_update_applier_rolls_back_failed_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = _package_directories(tmp_path)
    restarted: list[Path] = []
    monkeypatch.setattr("eve_dolphin.updates.applier.os.chdir", lambda _path: None)
    monkeypatch.setattr(applier_module, "_wait_for_process", lambda _pid, _timeout: True)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )
    monkeypatch.setattr(applier_module, "_restart", restarted.append)

    with pytest.raises(UpdateApplyError, match="self-check"):
        apply_staged_update(source, target, wait_pid=1234, restart=True)

    assert (target / "EVE-Dolphin.exe").read_text("utf-8") == "old"
    assert restarted == [target / "EVE-Dolphin.exe"]
    state = read_update_state(source.parent)
    assert state is not None
    assert state.status is UpdateStateStatus.FAILED
    assert state.error_code == "self-check"


def test_update_launcher_uses_working_directory_outside_installation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "updates" / "v0.2.0"
    target = tmp_path / "installed"
    source.mkdir(parents=True)
    target.mkdir()
    (source / "EVE-Dolphin.exe").write_bytes(b"new")
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_popen(arguments: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((arguments, kwargs))
        return SimpleNamespace()

    monkeypatch.setattr("eve_dolphin.updates.installer.subprocess.Popen", fake_popen)

    launch_staged_update(
        StagedUpdate(_release_info(_archive_bytes("0.2.0")), source),
        target,
        parent_pid=1234,
    )

    assert calls[0][1]["cwd"] == str(source.parent)
    state = read_update_state(source.parent)
    assert state is not None
    assert state.status is UpdateStateStatus.APPLYING


def test_terminal_update_result_is_consumed_once(tmp_path: Path) -> None:
    source, _target = _package_directories(tmp_path)
    state_path = source.parent / "update-state.json"
    state_path.write_text(
        json.dumps(
            {
                "status": "failed",
                "version": "0.3.1",
                "updated_at": "2026-08-31T12:00:00+00:00",
                "error_code": "filesystem",
            }
        ),
        encoding="utf-8",
    )

    result = consume_update_result(source.parent)

    assert result is not None
    assert result.status is UpdateStateStatus.FAILED
    assert result.error_code == "filesystem"
    assert consume_update_result(source.parent) is None


def _json_client(payload: object) -> httpx.Client:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    return httpx.Client(transport=transport)


def _release_payload(
    tag: str,
    *,
    prerelease: bool = False,
    draft: bool = False,
) -> dict[str, object]:
    asset_name = f"EVE-Dolphin-Windows-{tag}.zip"
    return {
        "tag_name": tag,
        "name": f"EVE Dolphin {tag}",
        "body": "Changes",
        "html_url": f"https://github.com/Savox76/eve-dolphin-production/releases/tag/{tag}",
        "published_at": "2026-08-30T20:00:00Z",
        "prerelease": prerelease,
        "draft": draft,
        "assets": [
            {
                "name": asset_name,
                "browser_download_url": (
                    "https://github.com/Savox76/eve-dolphin-production/releases/download/"
                    f"{tag}/{asset_name}"
                ),
                "size": 123,
                "digest": f"sha256:{'a' * 64}",
            }
        ],
    }


def _archive_bytes(version: str) -> bytes:
    buffer = io.BytesIO()
    build_info = {
        "version": version,
        "distribution_repository": "Savox76/eve-dolphin-production",
    }
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("EVE-Dolphin/EVE-Dolphin.exe", b"new-executable")
        archive.writestr("EVE-Dolphin/build-info.json", json.dumps(build_info))
    return buffer.getvalue()


def _release_info(payload: bytes, *, sha256: str | None = None) -> ReleaseInfo:
    return ReleaseInfo(
        AppVersion.parse("0.2.0"),
        "v0.2.0",
        "EVE Dolphin v0.2.0",
        "Changes",
        "https://github.com/Savox76/eve-dolphin-production/releases/tag/v0.2.0",
        datetime(2026, 8, 30, 20, 0, tzinfo=UTC),
        True,
        ReleaseAsset(
            "EVE-Dolphin-Windows-v0.2.0.zip",
            (
                "https://github.com/Savox76/eve-dolphin-production/releases/download/"
                "v0.2.0/EVE-Dolphin-Windows-v0.2.0.zip"
            ),
            len(payload),
            sha256 or hashlib.sha256(payload).hexdigest(),
        ),
    )


def _package_directories(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "staged"
    target = tmp_path / "installed"
    source.mkdir()
    target.mkdir()
    (source / "EVE-Dolphin.exe").write_text("new", encoding="utf-8")
    (target / "EVE-Dolphin.exe").write_text("old", encoding="utf-8")
    return source, target
