"""Orchestration of the cached SDE update, download and atomic import."""

from __future__ import annotations

from pathlib import Path

from eve_dolphin.sde.client import EveSdeClient
from eve_dolphin.sde.importer import SdeImporter, SdeImportError
from eve_dolphin.sde.models import SdeImportResult
from eve_dolphin.sde.repository import SdeRepository


class SdeUpdateService:
    """Run one complete local update without replacing a valid build prematurely."""

    def __init__(
        self,
        client: EveSdeClient,
        importer: SdeImporter,
        repository: SdeRepository,
        destination_dir: Path,
    ) -> None:
        self._client = client
        self._importer = importer
        self._repository = repository
        self._destination_dir = destination_dir

    def update(self) -> SdeImportResult:
        etag, last_modified = self._repository.latest_cache_headers()
        release = self._client.fetch_latest(etag=etag, last_modified=last_modified)
        active = self._repository.active_build()
        if release is None:
            if active is None:
                raise SdeImportError("SDE metadata is unchanged but no active build exists")
            return SdeImportResult(status=active, activated=False)
        if active is not None and active.build_number == release.build_number:
            return SdeImportResult(status=active, activated=False)

        archive = self._client.download_archive(release, self._destination_dir)
        return self._importer.import_archive(archive)
