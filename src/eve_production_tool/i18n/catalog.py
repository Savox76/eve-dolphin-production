"""German and English application-shell strings."""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_LANGUAGES = ("de", "en")

CATALOG: dict[str, dict[str, str]] = {
    "de": {
        "app.title": "EVE Production Tool",
        "app.subtitle": "Lokaler Produktions-Client",
        "overview": "Übersicht",
        "pi": "Planetare Industrie",
        "pi_planner": "PI-Zielplaner",
        "projects": "Produktionsprojekte",
        "blueprints": "Blueprints",
        "inventory": "Inventar & Logistik",
        "market": "Markt & Kalkulation",
        "settings": "Einstellungen & Charaktere",
        "local_data": "Lokale Datenbank bereit",
        "no_characters": "Noch keine EVE-Charaktere verbunden",
        "phase2_note": "Die sichere EVE-SSO-Verknüpfung folgt in Phase 2.",
        "foundation_ready": "Python- und SQLite-Fundament aktiv",
    },
    "en": {
        "app.title": "EVE Production Tool",
        "app.subtitle": "Local production client",
        "overview": "Overview",
        "pi": "Planetary Industry",
        "pi_planner": "PI Target Planner",
        "projects": "Production Projects",
        "blueprints": "Blueprints",
        "inventory": "Inventory & Logistics",
        "market": "Market & Calculation",
        "settings": "Settings & Characters",
        "local_data": "Local database ready",
        "no_characters": "No EVE characters connected yet",
        "phase2_note": "Secure EVE SSO linking follows in Phase 2.",
        "foundation_ready": "Python and SQLite foundation active",
    },
}


@dataclass(frozen=True, slots=True)
class Translator:
    language: str = "de"

    def __post_init__(self) -> None:
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unsupported language: {self.language}")

    def text(self, key: str) -> str:
        try:
            return CATALOG[self.language][key]
        except KeyError as error:
            raise KeyError(f"missing translation: {self.language}.{key}") from error
