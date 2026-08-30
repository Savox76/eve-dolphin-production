"""Secure EVE Online SSO primitives for the local desktop client."""

from eve_dolphin.sso.client import EveSsoClient
from eve_dolphin.sso.config import SsoConfig
from eve_dolphin.sso.scopes import ScopePackage, scopes_for_packages

__all__ = ["EveSsoClient", "ScopePackage", "SsoConfig", "scopes_for_packages"]
