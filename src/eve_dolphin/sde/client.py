"""HTTP-cached download of the official EVE JSON Lines SDE."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import httpx

from eve_dolphin import __version__
from eve_dolphin.sde.models import SdeArchive, SdeRelease

LATEST_METADATA_URL = "https://developers.eveonline.com/static-data/tranquility/latest.jsonl"
ARCHIVE_URL_TEMPLATE = (
    "https://developers.eveonline.com/static-data/tranquility/"
    "eve-online-static-data-{build_number}-jsonl.zip"
)
MAX_METADATA_BYTES = 64 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024


class SdeMetadataError(ValueError):
    """The official latest-build document is missing required values."""


class SdeDownloadError(RuntimeError):
    """An SDE archive could not be downloaded within the safety limits."""


class EveSdeClient:
    """Fetch official build metadata and stream archives into the local SDE directory."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            follow_redirects=False,
            headers={"User-Agent": f"EVE-Dolphin/{__version__} (local desktop client)"},
        )
        self._owns_client = client is None
        self._clock = clock or (lambda: datetime.now(UTC))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def fetch_latest(
        self,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> SdeRelease | None:
        headers = _conditional_headers(etag, last_modified)
        response = self._client.get(LATEST_METADATA_URL, headers=headers)
        if response.status_code == 304:
            return None
        response.raise_for_status()
        if len(response.content) > MAX_METADATA_BYTES:
            raise SdeMetadataError("SDE metadata document exceeds the size limit")
        return _parse_release(
            response.content,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
        )

    def download_archive(self, release: SdeRelease, destination_dir: Path) -> SdeArchive:
        destination_dir.mkdir(parents=True, exist_ok=True)
        archive_name = f"eve-online-static-data-{release.build_number}-jsonl.zip"
        archive_path = destination_dir / archive_name
        temporary_path = destination_dir / f".{archive_name}.part"
        digest = hashlib.sha256()
        downloaded_size = 0

        try:
            with self._client.stream("GET", release.archive_url) as response:
                response.raise_for_status()
                _validate_content_length(response.headers)
                with temporary_path.open("wb") as destination:
                    for chunk in response.iter_bytes():
                        downloaded_size += len(chunk)
                        if downloaded_size > MAX_ARCHIVE_BYTES:
                            raise SdeDownloadError("SDE archive exceeds the size limit")
                        digest.update(chunk)
                        destination.write(chunk)
                    destination.flush()
                    os.fsync(destination.fileno())
                response_etag = response.headers.get("ETag")
                response_last_modified = response.headers.get("Last-Modified")
            if downloaded_size == 0:
                raise SdeDownloadError("SDE archive is empty")
            os.replace(temporary_path, archive_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        downloaded_at = self._clock()
        if downloaded_at.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return SdeArchive(
            release=release,
            path=archive_path,
            sha256=digest.hexdigest(),
            size_bytes=downloaded_size,
            downloaded_at=downloaded_at,
            etag=response_etag,
            last_modified=response_last_modified,
        )


def _conditional_headers(etag: str | None, last_modified: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return headers


def _parse_release(
    content: bytes,
    *,
    etag: str | None,
    last_modified: str | None,
) -> SdeRelease:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SdeMetadataError("SDE metadata is not UTF-8") from error

    matching_records: list[Mapping[str, object]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            payload = cast(object, json.loads(line))
        except json.JSONDecodeError as error:
            raise SdeMetadataError("SDE metadata contains invalid JSON Lines") from error
        if not isinstance(payload, dict):
            raise SdeMetadataError("SDE metadata record is not an object")
        record = cast(dict[str, object], payload)
        if record.get("_key") == "sde":
            matching_records.append(record)
    if len(matching_records) != 1:
        raise SdeMetadataError("SDE metadata must contain exactly one sde record")

    release_record = matching_records[0]
    build_number = _positive_int(release_record.get("buildNumber"), "buildNumber")
    release_date = _timestamp(release_record.get("releaseDate"))
    return SdeRelease(
        build_number=build_number,
        release_date=release_date,
        archive_url=ARCHIVE_URL_TEMPLATE.format(build_number=build_number),
        etag=etag,
        last_modified=last_modified,
    )


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SdeMetadataError(f"SDE metadata has no valid {name}")
    return value


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise SdeMetadataError("SDE metadata has no valid releaseDate")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SdeMetadataError("SDE releaseDate is invalid") from error
    if parsed.tzinfo is None:
        raise SdeMetadataError("SDE releaseDate must include a timezone")
    return parsed


def _validate_content_length(headers: Mapping[str, str]) -> None:
    raw_length = headers.get("Content-Length")
    if raw_length is None:
        return
    try:
        content_length = int(raw_length)
    except ValueError as error:
        raise SdeDownloadError("SDE Content-Length is invalid") from error
    if content_length <= 0 or content_length > MAX_ARCHIVE_BYTES:
        raise SdeDownloadError("SDE Content-Length is outside the safety limit")
