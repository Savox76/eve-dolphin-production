from __future__ import annotations

from eve_dolphin.sso.scopes import SCOPE_PACKAGES, ScopePackage, scopes_for_packages


def test_identity_package_requests_no_business_permissions() -> None:
    assert scopes_for_packages(ScopePackage.IDENTITY) == ()


def test_industry_and_pi_packages_are_minimal_and_composable() -> None:
    scopes = scopes_for_packages(
        ScopePackage.INDUSTRY,
        ScopePackage.PLANETARY_INDUSTRY,
        ScopePackage.INDUSTRY,
    )

    assert scopes == (
        "esi-assets.read_assets.v1",
        "esi-characters.read_blueprints.v1",
        "esi-industry.read_character_jobs.v1",
        "esi-planets.manage_planets.v1",
    )
    assert set(SCOPE_PACKAGES) == set(ScopePackage)
