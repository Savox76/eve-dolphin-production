"""Typed SDE release, archive and local status values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SdeRelease:
    build_number: int
    release_date: datetime
    archive_url: str
    etag: str | None = None
    last_modified: str | None = None

    def __post_init__(self) -> None:
        if self.build_number <= 0:
            raise ValueError("SDE build_number must be positive")
        if self.release_date.tzinfo is None:
            raise ValueError("SDE release_date must include a timezone")
        if not self.archive_url.startswith("https://"):
            raise ValueError("SDE archive_url must use HTTPS")


@dataclass(frozen=True, slots=True)
class SdeArchive:
    release: SdeRelease
    path: Path
    sha256: str
    size_bytes: int
    downloaded_at: datetime
    etag: str | None = None
    last_modified: str | None = None

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise ValueError("SDE sha256 must be a lowercase hexadecimal digest")
        if self.size_bytes <= 0:
            raise ValueError("SDE archive must not be empty")
        if self.downloaded_at.tzinfo is None:
            raise ValueError("SDE downloaded_at must include a timezone")


@dataclass(frozen=True, slots=True)
class SdeBuildStatus:
    build_number: int
    release_date: datetime
    imported_at: datetime
    activated_at: datetime
    archive_sha256: str
    dataset_counts: dict[str, int]
    warnings: dict[str, int]


@dataclass(frozen=True, slots=True)
class SdeImportResult:
    status: SdeBuildStatus
    activated: bool
