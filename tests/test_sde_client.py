from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from eve_dolphin.sde.client import (
    LATEST_METADATA_URL,
    MAX_ARCHIVE_BYTES,
    EveSdeClient,
    SdeDownloadError,
    SdeMetadataError,
)
from eve_dolphin.sde.models import SdeRelease

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def test_fetch_latest_parses_release_and_sends_cache_validators() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == LATEST_METADATA_URL
        assert request.headers["If-None-Match"] == '"old"'
        assert request.headers["If-Modified-Since"] == "Fri, 28 Aug 2026 11:07:12 GMT"
        return httpx.Response(
            200,
            content=(
                b'{"_key":"sde","buildNumber":3484357,"releaseDate":"2026-08-28T11:07:12Z"}\n'
            ),
            headers={"ETag": '"new"', "Last-Modified": "Sat, 29 Aug 2026 11:07:12 GMT"},
        )

    client = EveSdeClient(httpx.Client(transport=httpx.MockTransport(handler)))

    release = client.fetch_latest(etag='"old"', last_modified="Fri, 28 Aug 2026 11:07:12 GMT")

    assert release is not None
    assert release.build_number == 3_484_357
    assert release.release_date == datetime(2026, 8, 28, 11, 7, 12, tzinfo=UTC)
    assert release.archive_url.endswith("eve-online-static-data-3484357-jsonl.zip")
    assert release.etag == '"new"'


def test_fetch_latest_returns_none_for_not_modified() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(304, request=request))
    client = EveSdeClient(httpx.Client(transport=transport))

    assert client.fetch_latest(etag='"current"') is None


def test_fetch_latest_rejects_invalid_metadata() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=b'{"_key":"sde","buildNumber":0}\n')
    )
    client = EveSdeClient(httpx.Client(transport=transport))

    with pytest.raises(SdeMetadataError):
        client.fetch_latest()


def test_download_archive_streams_atomically_and_hashes_content(tmp_path: Path) -> None:
    payload = b"valid zip bytes for transport testing"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=payload,
            headers={"ETag": '"archive"', "Last-Modified": "Sat, 29 Aug 2026 12:00:00 GMT"},
        )
    )
    client = EveSdeClient(httpx.Client(transport=transport), clock=lambda: NOW)
    release = _release()

    archive = client.download_archive(release, tmp_path)

    assert archive.path.read_bytes() == payload
    assert archive.sha256 == hashlib.sha256(payload).hexdigest()
    assert archive.size_bytes == len(payload)
    assert archive.downloaded_at == NOW
    assert archive.etag == '"archive"'
    assert not list(tmp_path.glob("*.part"))


def test_download_rejects_oversized_content_length_without_partial_file(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=b"ignored",
            headers={"Content-Length": str(MAX_ARCHIVE_BYTES + 1)},
        )
    )
    client = EveSdeClient(httpx.Client(transport=transport), clock=lambda: NOW)

    with pytest.raises(SdeDownloadError):
        client.download_archive(_release(), tmp_path)

    assert list(tmp_path.iterdir()) == []


def _release() -> SdeRelease:
    return SdeRelease(
        build_number=3_484_357,
        release_date=datetime(2026, 8, 28, 11, 7, 12, tzinfo=UTC),
        archive_url=(
            "https://developers.eveonline.com/static-data/tranquility/"
            "eve-online-static-data-3484357-jsonl.zip"
        ),
    )
