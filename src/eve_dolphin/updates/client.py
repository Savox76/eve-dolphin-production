"""Anonymous, bounded discovery of EVE Dolphin releases on GitHub."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

import httpx

from eve_dolphin import __version__
from eve_dolphin.updates.models import AppVersion, ReleaseAsset, ReleaseInfo

RELEASES_API_URL = "https://api.github.com/repos/Savox76/eve-dolphin-releases/releases"
RELEASE_DOWNLOAD_PREFIX = "https://github.com/Savox76/eve-dolphin-releases/releases/download/"
MAX_RELEASE_METADATA_BYTES = 2 * 1024 * 1024
MAX_UPDATE_ARCHIVE_BYTES = 500 * 1024 * 1024
EXPECTED_ASSET_PREFIX = "EVE-Dolphin-Windows-"


class ReleaseMetadataError(ValueError):
    """GitHub returned release metadata outside the accepted update contract."""


class GitHubReleaseClient:
    """Find the newest usable public Windows release without authentication."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def check(
        self,
        current_version: str = __version__,
        *,
        include_prereleases: bool = True,
    ) -> ReleaseInfo | None:
        current = AppVersion.parse(current_version)
        releases = self._fetch_releases()
        candidates = tuple(
            release
            for release in releases
            if release.version > current and (include_prereleases or not release.prerelease)
        )
        return max(candidates, key=lambda release: release.version, default=None)

    def _fetch_releases(self) -> tuple[ReleaseInfo, ...]:
        owned_client = self._client is None
        client = self._client or httpx.Client(
            timeout=httpx.Timeout(15.0, connect=10.0),
            follow_redirects=False,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": f"EVE-Dolphin/{__version__} (update check)",
            },
        )
        try:
            response = client.get(RELEASES_API_URL, params={"per_page": 20})
            response.raise_for_status()
            if len(response.content) > MAX_RELEASE_METADATA_BYTES:
                raise ReleaseMetadataError("release metadata is too large")
            payload = response.json()
        finally:
            if owned_client:
                client.close()
        if not isinstance(payload, list):
            raise ReleaseMetadataError("release metadata is not a list")
        parsed: list[ReleaseInfo] = []
        for item in payload:
            if not isinstance(item, Mapping):
                continue
            release = _parse_release(item)
            if release is not None:
                parsed.append(release)
        return tuple(parsed)


def _parse_release(payload: Mapping[object, object]) -> ReleaseInfo | None:
    if payload.get("draft") is not False:
        return None
    tag_name = _required_string(payload.get("tag_name"), "tag_name")
    try:
        version = AppVersion.parse(tag_name)
    except ValueError:
        return None
    assets = payload.get("assets")
    if not isinstance(assets, Sequence) or isinstance(assets, (str, bytes)):
        raise ReleaseMetadataError("release assets are invalid")
    expected_name = f"{EXPECTED_ASSET_PREFIX}{tag_name}.zip"
    matching_assets = tuple(
        asset
        for asset in assets
        if isinstance(asset, Mapping) and asset.get("name") == expected_name
    )
    if len(matching_assets) != 1:
        return None
    asset = _parse_asset(matching_assets[0], expected_name, tag_name)
    published_at = _timestamp(payload.get("published_at"), "published_at")
    return ReleaseInfo(
        version=version,
        tag_name=tag_name,
        title=_optional_string(payload.get("name")) or tag_name,
        notes=_optional_string(payload.get("body")) or "",
        page_url=_required_https_url(payload.get("html_url"), "html_url"),
        published_at=published_at,
        prerelease=payload.get("prerelease") is True,
        asset=asset,
    )


def _parse_asset(
    payload: Mapping[object, object], expected_name: str, tag_name: str
) -> ReleaseAsset:
    size = payload.get("size")
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or not 0 < size <= MAX_UPDATE_ARCHIVE_BYTES
    ):
        raise ReleaseMetadataError("release asset size is invalid")
    download_url = _required_https_url(payload.get("browser_download_url"), "download URL")
    expected_prefix = f"{RELEASE_DOWNLOAD_PREFIX}{tag_name}/"
    if not download_url.startswith(expected_prefix):
        raise ReleaseMetadataError("release asset is hosted outside the distribution repository")
    digest = _required_string(payload.get("digest"), "digest")
    algorithm, separator, value = digest.partition(":")
    if algorithm != "sha256" or separator != ":" or len(value) != 64:
        raise ReleaseMetadataError("release asset has no valid SHA-256 digest")
    try:
        bytes.fromhex(value)
    except ValueError as error:
        raise ReleaseMetadataError("release asset digest is invalid") from error
    return ReleaseAsset(expected_name, download_url, size, value.lower())


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseMetadataError(f"release {field} is missing")
    return value.strip()


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _required_https_url(value: object, field: str) -> str:
    result = _required_string(value, field)
    url = httpx.URL(result)
    if url.scheme != "https" or not url.host:
        raise ReleaseMetadataError(f"release {field} is not HTTPS")
    return result


def _timestamp(value: object, field: str) -> datetime:
    raw = _required_string(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReleaseMetadataError(f"release {field} is invalid") from error
    if parsed.tzinfo is None:
        raise ReleaseMetadataError(f"release {field} has no timezone")
    return parsed
