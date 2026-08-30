from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from eve_dolphin.sde.client import EveSdeClient
from eve_dolphin.sde.importer import SdeImporter
from eve_dolphin.sde.models import SdeArchive, SdeBuildStatus, SdeImportResult, SdeRelease
from eve_dolphin.sde.repository import SdeRepository
from eve_dolphin.sde.service import SdeUpdateService

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class _Client:
    def __init__(self, release: SdeRelease | None) -> None:
        self.release = release
        self.fetch_args: tuple[str | None, str | None] | None = None
        self.downloaded = False

    def fetch_latest(
        self, *, etag: str | None = None, last_modified: str | None = None
    ) -> SdeRelease | None:
        self.fetch_args = etag, last_modified
        return self.release

    def download_archive(self, release: SdeRelease, destination_dir: Path) -> SdeArchive:
        self.downloaded = True
        raise AssertionError("download should not run for the active build")


class _Importer:
    def import_archive(self, archive: SdeArchive) -> SdeImportResult:
        raise AssertionError("import should not run for the active build")


class _Repository:
    def latest_cache_headers(self) -> tuple[str | None, str | None]:
        return '"metadata"', "Fri, 28 Aug 2026 11:07:12 GMT"

    def active_build(self) -> SdeBuildStatus:
        return SdeBuildStatus(
            build_number=101,
            release_date=NOW,
            imported_at=NOW,
            activated_at=NOW,
            archive_sha256="a" * 64,
            dataset_counts={"types": 5},
            warnings={},
        )


def test_update_uses_cache_headers_and_skips_active_build(tmp_path: Path) -> None:
    client = _Client(
        SdeRelease(
            build_number=101,
            release_date=NOW,
            archive_url="https://example.invalid/sde.zip",
        )
    )
    service = SdeUpdateService(
        cast(EveSdeClient, client),
        cast(SdeImporter, _Importer()),
        cast(SdeRepository, _Repository()),
        tmp_path,
    )

    result = service.update()

    assert result.activated is False
    assert result.status.build_number == 101
    assert client.fetch_args == ('"metadata"', "Fri, 28 Aug 2026 11:07:12 GMT")
    assert client.downloaded is False
