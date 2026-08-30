from __future__ import annotations

import pytest

from eve_dolphin.i18n import Translator
from eve_dolphin.i18n.catalog import CATALOG


def test_german_and_english_catalogs_have_identical_keys() -> None:
    assert CATALOG["de"].keys() == CATALOG["en"].keys()


def test_translator_returns_selected_language() -> None:
    assert Translator("de").text("overview") == "Übersicht"
    assert Translator("en").text("overview") == "Overview"


def test_unsupported_language_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported language"):
        Translator("fr")
