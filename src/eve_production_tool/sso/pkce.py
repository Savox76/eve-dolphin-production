"""RFC 7636 PKCE generation for public desktop clients."""

from __future__ import annotations

import base64
import hashlib
import secrets

from eve_production_tool.sso.models import PkcePair


def generate_pkce_pair(random_bytes: bytes | None = None) -> PkcePair:
    """Generate the 32-byte verifier and its unpadded S256 challenge."""

    entropy = secrets.token_bytes(32) if random_bytes is None else random_bytes
    if len(entropy) != 32:
        raise ValueError("PKCE entropy must contain exactly 32 bytes")
    verifier = _base64url(entropy)
    challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return PkcePair(verifier=verifier, challenge=challenge)


def generate_state() -> str:
    """Return an unpredictable CSRF correlation value."""

    return secrets.token_urlsafe(32)


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
