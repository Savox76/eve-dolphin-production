"""Validated values shared by release discovery and installation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from functools import total_ordering
from pathlib import Path

VERSION_PATTERN = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?$"
)


@total_ordering
@dataclass(frozen=True, slots=True)
class AppVersion:
    """Small SemVer-compatible comparator without another runtime dependency."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    @classmethod
    def parse(cls, value: str) -> AppVersion:
        match = VERSION_PATTERN.fullmatch(value.strip())
        if match is None:
            raise ValueError(f"invalid application version: {value}")
        prerelease = match.group("prerelease")
        return cls(
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
            tuple(prerelease.split(".")) if prerelease else (),
        )

    def __str__(self) -> str:
        value = f"{self.major}.{self.minor}.{self.patch}"
        return f"{value}-{'.'.join(self.prerelease)}" if self.prerelease else value

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, AppVersion):
            return NotImplemented
        own_core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if own_core != other_core:
            return own_core < other_core
        if not self.prerelease:
            return False
        if not other.prerelease:
            return True
        for own_part, other_part in zip(self.prerelease, other.prerelease, strict=False):
            if own_part == other_part:
                continue
            own_numeric = own_part.isdigit()
            other_numeric = other_part.isdigit()
            if own_numeric and other_numeric:
                return int(own_part) < int(other_part)
            if own_numeric != other_numeric:
                return own_numeric
            return own_part < other_part
        return len(self.prerelease) < len(other.prerelease)


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: AppVersion
    tag_name: str
    title: str
    notes: str
    page_url: str
    published_at: datetime
    prerelease: bool
    asset: ReleaseAsset


@dataclass(frozen=True, slots=True)
class StagedUpdate:
    release: ReleaseInfo
    package_dir: Path
