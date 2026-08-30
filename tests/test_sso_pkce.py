from __future__ import annotations

import base64
import hashlib
import re

import pytest

from eve_production_tool.sso.pkce import generate_pkce_pair, generate_state


def test_pkce_pair_matches_unpadded_s256_definition() -> None:
    pair = generate_pkce_pair(bytes(range(32)))
    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(pair.verifier.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )

    assert len(pair.verifier) == 43
    assert len(pair.challenge) == 43
    assert "=" not in pair.verifier
    assert pair.challenge == expected_challenge
    assert re.fullmatch(r"[A-Za-z0-9_-]+", pair.verifier)


def test_pkce_requires_exactly_32_bytes_of_entropy() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        generate_pkce_pair(b"too-short")


def test_state_values_are_unpredictable_and_url_safe() -> None:
    first = generate_state()
    second = generate_state()

    assert first != second
    assert len(first) >= 43
    assert re.fullmatch(r"[A-Za-z0-9_-]+", first)
