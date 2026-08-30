"""German and English application-shell strings."""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_LANGUAGES = ("de", "en")

CATALOG: dict[str, dict[str, str]] = {
    "de": {
        "app.title": "EVE Dolphin",
        "app.subtitle": "Lokaler EVE-Begleiter",
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
        "phase2_note": "Verbinde den ersten Charakter unter Einstellungen & Charaktere.",
        "foundation_ready": "Python- und SQLite-Fundament aktiv",
        "characters_page_detail": (
            "Jeder Charakter wird einzeln über den Systembrowser autorisiert. "
            "Passwörter werden niemals von EVE Dolphin abgefragt."
        ),
        "connected_characters": "Verbundene Charaktere",
        "connect_character": "EVE-Charakter verbinden",
        "unlink_character": "Charakter trennen",
        "character_name": "Charakter",
        "scope_count": "Freigaben",
        "linked_at": "Verbunden am",
        "character_count": "Verbundene EVE-Charaktere: {count}",
        "characters_ready": (
            "Die verbundenen Charaktere stehen für spätere Synchronisationen bereit."
        ),
        "confirm_unlink": (
            "Soll {name} wirklich von dieser Installation getrennt werden? "
            "Das lokale Refresh Token wird dabei entfernt."
        ),
        "character_unlinked": "{name} wurde sicher getrennt.",
        "character_not_found": "Der ausgewählte Charakter ist nicht mehr vorhanden.",
        "unlink_failed": "Der Charakter konnte nicht getrennt werden.",
        "sso_preparing": "EVE SSO wird vorbereitet …",
        "sso_closing": "Die laufende EVE-Anmeldung wird sicher beendet …",
        "sso_browser_waiting": (
            "Der Systembrowser wurde geöffnet. Wähle dort den gewünschten EVE-Charakter aus."
        ),
        "sso_linked": "{name} wurde erfolgreich verbunden.",
        "sso_client_id_missing": (
            "Die öffentliche EVE-Client-ID ist noch nicht konfiguriert. "
            "Für die Entwicklung wird EVE_SSO_CLIENT_ID benötigt."
        ),
        "sso_browser_failed": "Der Systembrowser konnte nicht geöffnet werden.",
        "sso_timeout": "Die EVE-Anmeldung wurde nicht innerhalb von drei Minuten abgeschlossen.",
        "sso_cancelled": "Die EVE-Anmeldung wurde abgebrochen.",
        "sso_invalid_response": "Die Antwort von EVE SSO konnte nicht sicher bestätigt werden.",
        "sso_network_failed": (
            "EVE SSO ist gerade nicht erreichbar oder der Callback-Port ist belegt."
        ),
        "sso_keyring_failed": (
            "Der sichere Anmeldedatenspeicher des Betriebssystems ist nicht verfügbar."
        ),
        "sso_failed": "Der EVE-Charakter konnte nicht verbunden werden.",
    },
    "en": {
        "app.title": "EVE Dolphin",
        "app.subtitle": "Local EVE companion",
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
        "phase2_note": "Connect the first character under Settings & Characters.",
        "foundation_ready": "Python and SQLite foundation active",
        "characters_page_detail": (
            "Each character is authorized separately in the system browser. "
            "EVE Dolphin never asks for account passwords."
        ),
        "connected_characters": "Connected characters",
        "connect_character": "Connect EVE character",
        "unlink_character": "Disconnect character",
        "character_name": "Character",
        "scope_count": "Permissions",
        "linked_at": "Connected at",
        "character_count": "Connected EVE characters: {count}",
        "characters_ready": "Connected characters are ready for later synchronization.",
        "confirm_unlink": (
            "Disconnect {name} from this installation? The local refresh token will be removed."
        ),
        "character_unlinked": "{name} was disconnected securely.",
        "character_not_found": "The selected character no longer exists.",
        "unlink_failed": "The character could not be disconnected.",
        "sso_preparing": "Preparing EVE SSO …",
        "sso_closing": "Stopping the pending EVE sign-in safely …",
        "sso_browser_waiting": (
            "The system browser is open. Select the EVE character you want to connect."
        ),
        "sso_linked": "{name} was connected successfully.",
        "sso_client_id_missing": (
            "The public EVE client ID has not been configured yet. "
            "Development builds require EVE_SSO_CLIENT_ID."
        ),
        "sso_browser_failed": "The system browser could not be opened.",
        "sso_timeout": "The EVE sign-in was not completed within three minutes.",
        "sso_cancelled": "The EVE sign-in was cancelled.",
        "sso_invalid_response": "The EVE SSO response could not be verified safely.",
        "sso_network_failed": "EVE SSO is unavailable or the local callback port is in use.",
        "sso_keyring_failed": "The operating system credential store is unavailable.",
        "sso_failed": "The EVE character could not be connected.",
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
