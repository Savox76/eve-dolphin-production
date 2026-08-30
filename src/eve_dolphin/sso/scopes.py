"""Progressive, least-privilege ESI permission packages."""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType


class ScopePackage(StrEnum):
    IDENTITY = "identity"
    INDUSTRY = "industry"
    PLANETARY_INDUSTRY = "planetary_industry"


SCOPE_PACKAGES: MappingProxyType[ScopePackage, tuple[str, ...]] = MappingProxyType(
    {
        ScopePackage.IDENTITY: (),
        ScopePackage.INDUSTRY: (
            "esi-assets.read_assets.v1",
            "esi-characters.read_blueprints.v1",
            "esi-industry.read_character_jobs.v1",
        ),
        ScopePackage.PLANETARY_INDUSTRY: ("esi-planets.manage_planets.v1",),
    }
)


def scopes_for_packages(*packages: ScopePackage) -> tuple[str, ...]:
    """Combine packages deterministically while removing duplicate scopes."""

    return tuple(dict.fromkeys(scope for package in packages for scope in SCOPE_PACKAGES[package]))
