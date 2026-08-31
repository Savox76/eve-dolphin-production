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
        "pi_overview_detail": (
            "Aktuelle Kolonien aller verbundenen Charaktere. Die Ansicht verwendet nur "
            "vollständig synchronisierte lokale Datenstände."
        ),
        "pi_colonies": "Kolonieübersicht",
        "pi_colony_details": "Ausgewählte Kolonie",
        "pi_character": "Charakter",
        "pi_planet": "Planet",
        "pi_planet_type": "Planetentyp",
        "pi_system": "System",
        "pi_pins": "Pins",
        "pi_extractors": "Extraktoren",
        "pi_factories": "Fabriken",
        "pi_last_update": "Kolonie aktualisiert",
        "pi_status": "Status",
        "pi_storage": "Lager",
        "pi_next_attention": "Nächste Aktion",
        "pi_no_colonies": (
            "Noch keine PI-Kolonien vorhanden. Verbinde einen Charakter mit PI-Freigabe "
            "und synchronisiere seine EVE-Daten."
        ),
        "pi_no_selection": "Wähle eine Kolonie aus, um ihre Details zu sehen.",
        "pi_summary": (
            "Kolonien: {colonies} · Charaktere: {characters} · Extraktoren: "
            "{active} aktiv, {expired} abgelaufen, {incomplete} unvollständig"
        ),
        "pi_identity_detail": (
            "{character} · Planet {planet} ({planet_type}) · System {system} · "
            "Kommandozentrale Stufe {level}"
        ),
        "pi_layout_detail": (
            "Anlage: {pins} Pins · {links} Links · {routes} Routen · {factories} Fabriken"
        ),
        "pi_extractor_detail": (
            "Extraktoren: {active} aktiv · {expired} abgelaufen · {incomplete} "
            "unvollständig · nächste Laufzeit endet {next_expiry}"
        ),
        "pi_extractor_compact": "{active} / {expired} / {incomplete}",
        "pi_pin_types_detail": "Pin-Typen: {values}",
        "pi_extractor_products_detail": "Extraktorprodukte: {values}",
        "pi_storage_detail": "Gelagerte Inhalte: {values}",
        "pi_extractor_rate_detail": "Geschätzter P0-Ertrag: {values}",
        "pi_rate_value": "{name}: {hourly}/h · {daily}/Tag",
        "pi_factory_forecast_detail": (
            "Fabrikprognose (24 h): {values} · {stalled} gestoppt · {constrained} unterversorgt"
        ),
        "pi_storage_forecast_detail": (
            "Lager: {used} / {capacity} m³ ({percent} %) · voraussichtlich voll: {full}"
        ),
        "pi_data_age_detail": "Datenalter: {age} · Status: {status}",
        "pi_snapshot_detail": "Lokaler vollständiger Snapshot: {snapshot}",
        "pi_none": "keine",
        "pi_unknown": "unbekannt",
        "pi_status_current": "aktuell",
        "pi_warning_data_stale": "Daten älter als 20 Minuten",
        "pi_warning_extractors_expired": "Extraktor abgelaufen",
        "pi_warning_extractors_ending_soon": "Extraktor endet binnen 24 Stunden",
        "pi_warning_pi_data_incomplete": "PI-Daten unvollständig",
        "pi_warning_factories_stalled": "Fabrik ohne Versorgung",
        "pi_warning_factories_constrained": "Fabrik unterversorgt",
        "pi_warning_storage_near_full": "Lager fast voll",
        "pi_unknown_type": "Typ {type_id}",
        "planet_type_temperate": "gemäßigt",
        "planet_type_barren": "karg",
        "planet_type_oceanic": "ozeanisch",
        "planet_type_ice": "Eis",
        "planet_type_gas": "Gas",
        "planet_type_lava": "Lava",
        "planet_type_storm": "Sturm",
        "planet_type_plasma": "Plasma",
        "pi_planner": "PI-Zielplaner",
        "pi_planner_detail": (
            "Plane P1 bis P4 rückwärts aus der aktiven EVE-SDE und verrechne die "
            "aktuellen Kolonieprognosen aller Charaktere. Ergebnisse sind Schätzungen, "
            "keine Garantie für Routen oder Marktpreise."
        ),
        "pi_plan_tab": "Zielplanung",
        "pi_profiles_tab": "Profile",
        "pi_target": "Zielprodukt",
        "pi_quantity": "Zielmenge",
        "pi_days": "Zeitraum (Tage)",
        "pi_profile": "Logistikprofil",
        "pi_calculate": "Plan berechnen",
        "pi_no_catalog": "Keine aktive PI-SDE verfügbar. Synchronisiere zuerst die EVE-Daten.",
        "pi_no_plan": "Wähle Ziel, Menge, Zeitraum und Profil aus.",
        "pi_plan_feasible": "Plan vollständig berechnet",
        "pi_plan_blocked": "Plan eingeschränkt: {reasons}",
        "pi_block_imports_require_customs_office": "Import benötigt ein Zollamt (POCO)",
        "pi_block_command_center_export_requires_multiple_launches": (
            "Export ohne POCO überschreitet 500 m³ und benötigt mehrere Starts"
        ),
        "pi_block_raw_material_shortfall": "Rohstoffbedarf ist nicht vollständig gedeckt",
        "pi_block_factory_capacity_shortfall": (
            "vorhandene Fabrikkapazität reicht im gewählten Zeitraum nicht aus"
        ),
        "pi_plan_product": "Produkt",
        "pi_plan_tier": "Stufe",
        "pi_plan_required": "Bedarf",
        "pi_plan_per_day": "pro Tag",
        "pi_plan_available": "Prognose",
        "pi_plan_output": "Produktion",
        "pi_plan_cycles": "Zyklen",
        "pi_plan_capacity": "freie Zyklen",
        "pi_plan_additional_factories": "zusätzl. Fabriken",
        "pi_plan_import": "Import",
        "pi_plan_missing": "Fehlmenge",
        "pi_plan_excess": "Überschuss",
        "pi_plan_costs": (
            "Import {import_volume} m³ · Export {export_volume} m³ · {trips} Frachtrouten · "
            "Importsteuer {import_tax} ISK · Exportsteuer {export_tax} ISK · "
            "Transport {transport} ISK · Risiko {risk} ISK · Summe {total} ISK"
        ),
        "pi_profile_name": "Profilname",
        "pi_space_kind": "Raumart",
        "pi_customs_office": "Zollamt/POCO verfügbar",
        "pi_import_tax": "Importsteuer (%)",
        "pi_export_tax": "Exportsteuer (%)",
        "pi_transport_rate": "Transport (ISK/m³)",
        "pi_cargo_capacity": "Frachtraum (m³)",
        "pi_risk_markup": "Risikozuschlag (%)",
        "pi_supply_tier": "Extern verfügbare Eingangsstufe",
        "pi_profile_save": "Profil speichern",
        "pi_profile_new": "Neues Profil",
        "pi_profile_saved": "Profil gespeichert: {name}",
        "pi_profile_error": "Profil konnte nicht gespeichert werden: {message}",
        "pi_space_highsec": "Highsec",
        "pi_space_lowsec": "Lowsec",
        "pi_space_nullsec": "Nullsec",
        "pi_space_wormhole": "Wurmloch",
        "pi_tier_0": "P0 Rohstoff",
        "pi_tier_1": "P1 Basisprodukt",
        "pi_tier_2": "P2 Veredeltes Produkt",
        "pi_tier_3": "P3 Spezialprodukt",
        "pi_tier_4": "P4 Hightech-Produkt",
        "projects": "Produktionsprojekte",
        "blueprints": "Blueprints",
        "blueprint_page_detail": (
            "Persönliche BPOs und BPCs werden mit dem Manufacturing-Rezept des aktiven "
            "SDE-Builds verbunden. Bestände am Blueprint-Ort und an anderen Orten bleiben "
            "getrennt."
        ),
        "blueprint_search": "Produkt, Blueprint, Charakter oder Standort suchen",
        "blueprint_product": "Produkt",
        "blueprint_owner": "Besitzer",
        "blueprint_kind": "Typ",
        "blueprint_runs": "Runs",
        "blueprint_location": "Standort-ID",
        "blueprint_name": "Blueprint",
        "blueprint_original": "BPO",
        "blueprint_copy": "BPC",
        "blueprint_unlimited": "unbegrenzt",
        "blueprint_empty": (
            "Noch keine nutzbaren Manufacturing-Blueprints gefunden. Synchronisiere einen "
            "Charakter mit Blueprint-Freigabe und eine aktuelle SDE."
        ),
        "manufacturing_calculation": "Manufacturing-Kalkulation",
        "manufacturing_target_quantity": "Zielmenge",
        "manufacturing_calculate": "Neu berechnen",
        "manufacturing_select_blueprint": "Wähle einen Blueprint für die Kalkulation aus.",
        "manufacturing_material": "Material",
        "manufacturing_required": "Bedarf",
        "manufacturing_at_location": "Am BP-Ort",
        "manufacturing_total": "Gesamt",
        "manufacturing_missing_local": "Lokal fehlt",
        "manufacturing_blueprint_ready": "Blueprint-Runs ausreichend",
        "manufacturing_blueprint_shortfall": "BPC fehlen {count} Runs",
        "manufacturing_materials_ready": "Materialien am Blueprint-Ort vollständig",
        "manufacturing_materials_missing": "Materialien am Blueprint-Ort unvollständig",
        "manufacturing_plan_summary": (
            "{runs} Runs · Ausgabe {output} · Überschuss {surplus} · Dauer {duration}\n"
            "{blueprint} · {materials}"
        ),
        "inventory": "Inventar & Logistik",
        "market": "Markt & Kalkulation",
        "settings": "Einstellungen & Charaktere",
        "local_data": "Lokale Datenbank bereit",
        "app_version": "Version v{version}",
        "updates_title": "EVE-Dolphin-Updates",
        "check_for_updates": "Nach Updates suchen",
        "checking_for_updates": "Updateprüfung läuft …",
        "update_button_available": "Update v{version} verfügbar",
        "update_available_title": "Neue Version verfügbar",
        "update_versions": "Installiert: v{current}  ·  Neu: v{new}",
        "update_metadata": "Veröffentlicht: {date}  ·  Download: {size}",
        "update_contents": "Inhalt des Updates",
        "update_no_notes": "Für dieses Update wurden keine zusätzlichen Hinweise hinterlegt.",
        "update_start": "Update starten",
        "update_later": "Später",
        "update_downloading": (
            "Das geprüfte Update wird heruntergeladen. EVE Dolphin startet danach neu."
        ),
        "update_download_progress": "Update wird heruntergeladen und geprüft: {percentage} %",
        "update_preparing": "Download abgeschlossen. Das Update wird geprüft und vorbereitet …",
        "update_failed": (
            "Das Update konnte nicht sicher vorbereitet werden. Die installierte Version "
            "bleibt unverändert. Grund: {reason}"
        ),
        "update_error_network": "Der Download von GitHub ist fehlgeschlagen.",
        "update_error_package": "Das heruntergeladene Paket war unvollständig oder ungültig.",
        "update_error_filesystem": "Windows konnte die Updatedateien nicht vorbereiten.",
        "update_error_launch": "Der ausgelagerte Updateprozess konnte nicht gestartet werden.",
        "update_error_unexpected": "Es ist ein unerwarteter Fehler aufgetreten.",
        "update_result_succeeded": "Update auf v{version} erfolgreich installiert.",
        "update_result_failed": (
            "Update auf v{version} fehlgeschlagen: {reason} Die vorherige Version wurde "
            "wiederhergestellt."
        ),
        "update_apply_error_parent_timeout": "EVE Dolphin wurde nicht rechtzeitig beendet.",
        "update_apply_error_self_check": "Die neue Version hat die Selbstprüfung nicht bestanden.",
        "update_apply_error_backup": "Eine frühere Updatesicherung blockiert den Austausch.",
        "update_apply_error_validation": "Quell- oder Installationsordner ist ungültig.",
        "update_apply_error_filesystem": "Windows oder ein Virenscanner blockiert eine Datei.",
        "update_apply_error_launch": "Der Updateprozess konnte nicht gestartet werden.",
        "update_apply_error_replacement": "Die Programmdateien konnten nicht ersetzt werden.",
        "update_install_unavailable": (
            "Updates lassen sich nur aus der installierten Windows-Version starten."
        ),
        "update_current": "EVE Dolphin ist bereits auf dem neuesten verfügbaren Stand.",
        "update_check_failed": ("Die Updateinformationen konnten gerade nicht abgerufen werden."),
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
        "authorize_industry": "Industrie freigeben",
        "authorize_planetary": "PI freigeben",
        "sync_data": "EVE-Daten synchronisieren",
        "character_name": "Charakter",
        "scope_count": "Freigaben",
        "authorization_status": "Anmeldestatus",
        "authorization_active": "Aktiv",
        "authorization_required": "Erneut verbinden",
        "linked_at": "Verbunden am",
        "character_count": "Verbundene EVE-Charaktere: {count}",
        "characters_ready": (
            "Die verbundenen Charaktere werden während der Laufzeit automatisch aktuell gehalten."
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
            "Die öffentliche EVE-Client-ID ist leer. Entferne eine leere "
            "EVE_SSO_CLIENT_ID-Überschreibung oder trage eine gültige Client-ID ein."
        ),
        "sso_browser_failed": "Der Systembrowser konnte nicht geöffnet werden.",
        "sso_timeout": "Die EVE-Anmeldung wurde nicht innerhalb von drei Minuten abgeschlossen.",
        "sso_cancelled": "Die EVE-Anmeldung wurde abgebrochen.",
        "sso_wrong_character": (
            "Für diese Freigabe wurde ein anderer Charakter gewählt. Bitte wiederhole den "
            "Vorgang mit dem zuvor ausgewählten Charakter."
        ),
        "sso_invalid_response": "Die Antwort von EVE SSO konnte nicht sicher bestätigt werden.",
        "sso_network_failed": (
            "EVE SSO ist gerade nicht erreichbar oder der Callback-Port ist belegt."
        ),
        "sso_keyring_failed": (
            "Der sichere Anmeldedatenspeicher des Betriebssystems ist nicht verfügbar."
        ),
        "sso_failed": "Der EVE-Charakter konnte nicht verbunden werden.",
        "sync_running": "Assets, Blueprints, Jobs und PI-Kolonien werden synchronisiert …",
        "sync_complete": "Die EVE-Daten von {count} Charakter(en) sind aktuell.",
        "sync_complete_auto": (
            "Die EVE-Daten von {count} Charakter(en) sind aktuell. Nächste Prüfung in 5 Minuten."
        ),
        "automatic_sync_waiting": (
            "Automatische Synchronisation aktiv. Nach dem Verbinden werden alle Daten sofort "
            "geladen und anschließend alle 5 Minuten geprüft."
        ),
        "sync_partial": (
            "{succeeded} von {count} Charakter(en) wurden vollständig synchronisiert. "
            "Fehlerhafte Datenstände sind in der Übersicht markiert."
        ),
        "sync_permissions_missing": (
            "Mindestens eine EVE-Freigabe fehlt. Wähle den Charakter und aktiviere "
            "Industrie und/oder PI über die sichtbaren Freigabe-Schaltflächen."
        ),
        "sync_network_failed": (
            "Die EVE-Daten konnten wegen eines Netzwerkfehlers nicht geladen werden."
        ),
        "sync_failed": "Die EVE-Datensynchronisation ist fehlgeschlagen.",
        "sync_sde_failed": (
            "Die statischen EVE-Daten konnten nicht aktualisiert werden. Der letzte gültige "
            "Stand bleibt aktiv; Details sind in der Übersicht markiert."
        ),
        "sync_closing": "Die laufende EVE-Datensynchronisation wird noch sicher abgeschlossen …",
        "data_status": "Lokaler Datenstand",
        "sde_missing": "SDE: fehlt",
        "sde_status": "SDE Build {build} · {state} · veröffentlicht {date}",
        "resource_industry": "Industrie",
        "resource_jobs": "Jobs",
        "resource_planetary": "PI",
        "data_current": "aktuell",
        "data_stale": "veraltet",
        "data_failed": "Abruf fehlgeschlagen",
        "data_missing": "fehlt",
    },
    "en": {
        "app.title": "EVE Dolphin",
        "app.subtitle": "Local EVE companion",
        "overview": "Overview",
        "pi": "Planetary Industry",
        "pi_overview_detail": (
            "Current colonies for all connected characters. This view only uses complete, "
            "locally synchronized snapshots."
        ),
        "pi_colonies": "Colony overview",
        "pi_colony_details": "Selected colony",
        "pi_character": "Character",
        "pi_planet": "Planet",
        "pi_planet_type": "Planet type",
        "pi_system": "System",
        "pi_pins": "Pins",
        "pi_extractors": "Extractors",
        "pi_factories": "Factories",
        "pi_last_update": "Colony updated",
        "pi_status": "Status",
        "pi_storage": "Storage",
        "pi_next_attention": "Next action",
        "pi_no_colonies": (
            "No PI colonies are available yet. Connect a character with PI permission and "
            "synchronize their EVE data."
        ),
        "pi_no_selection": "Select a colony to see its details.",
        "pi_summary": (
            "Colonies: {colonies} · Characters: {characters} · Extractors: "
            "{active} active, {expired} expired, {incomplete} incomplete"
        ),
        "pi_identity_detail": (
            "{character} · Planet {planet} ({planet_type}) · System {system} · "
            "Command center level {level}"
        ),
        "pi_layout_detail": (
            "Layout: {pins} pins · {links} links · {routes} routes · {factories} factories"
        ),
        "pi_extractor_detail": (
            "Extractors: {active} active · {expired} expired · {incomplete} incomplete · "
            "next expiry {next_expiry}"
        ),
        "pi_extractor_compact": "{active} / {expired} / {incomplete}",
        "pi_pin_types_detail": "Pin types: {values}",
        "pi_extractor_products_detail": "Extractor products: {values}",
        "pi_storage_detail": "Stored contents: {values}",
        "pi_extractor_rate_detail": "Estimated P0 yield: {values}",
        "pi_rate_value": "{name}: {hourly}/h · {daily}/day",
        "pi_factory_forecast_detail": (
            "Factory forecast (24 h): {values} · {stalled} stalled · {constrained} constrained"
        ),
        "pi_storage_forecast_detail": (
            "Storage: {used} / {capacity} m³ ({percent} %) · estimated full: {full}"
        ),
        "pi_data_age_detail": "Data age: {age} · Status: {status}",
        "pi_snapshot_detail": "Complete local snapshot: {snapshot}",
        "pi_none": "none",
        "pi_unknown": "unknown",
        "pi_status_current": "current",
        "pi_warning_data_stale": "data older than 20 minutes",
        "pi_warning_extractors_expired": "extractor expired",
        "pi_warning_extractors_ending_soon": "extractor ends within 24 hours",
        "pi_warning_pi_data_incomplete": "PI data incomplete",
        "pi_warning_factories_stalled": "factory without supply",
        "pi_warning_factories_constrained": "factory supply-constrained",
        "pi_warning_storage_near_full": "storage nearly full",
        "pi_unknown_type": "Type {type_id}",
        "planet_type_temperate": "temperate",
        "planet_type_barren": "barren",
        "planet_type_oceanic": "oceanic",
        "planet_type_ice": "ice",
        "planet_type_gas": "gas",
        "planet_type_lava": "lava",
        "planet_type_storm": "storm",
        "planet_type_plasma": "plasma",
        "pi_planner": "PI Target Planner",
        "pi_planner_detail": (
            "Plan P1 through P4 backwards from the active EVE SDE and account for current "
            "colony forecasts across all characters. Results are estimates, not a guarantee "
            "of routing or market prices."
        ),
        "pi_plan_tab": "Target plan",
        "pi_profiles_tab": "Profiles",
        "pi_target": "Target product",
        "pi_quantity": "Target quantity",
        "pi_days": "Timeframe (days)",
        "pi_profile": "Logistics profile",
        "pi_calculate": "Calculate plan",
        "pi_no_catalog": "No active PI SDE is available. Synchronize EVE data first.",
        "pi_no_plan": "Select a target, quantity, timeframe, and profile.",
        "pi_plan_feasible": "Plan calculated completely",
        "pi_plan_blocked": "Plan constrained: {reasons}",
        "pi_block_imports_require_customs_office": "imports require a customs office (POCO)",
        "pi_block_command_center_export_requires_multiple_launches": (
            "export without a POCO exceeds 500 m³ and requires multiple launches"
        ),
        "pi_block_raw_material_shortfall": "raw material demand is not fully covered",
        "pi_block_factory_capacity_shortfall": (
            "existing factory capacity is insufficient for the selected timeframe"
        ),
        "pi_plan_product": "Product",
        "pi_plan_tier": "Tier",
        "pi_plan_required": "Required",
        "pi_plan_per_day": "per day",
        "pi_plan_available": "Forecast",
        "pi_plan_output": "Production",
        "pi_plan_cycles": "Cycles",
        "pi_plan_capacity": "free cycles",
        "pi_plan_additional_factories": "additional factories",
        "pi_plan_import": "Import",
        "pi_plan_missing": "Shortfall",
        "pi_plan_excess": "Excess",
        "pi_plan_costs": (
            "Import {import_volume} m³ · export {export_volume} m³ · {trips} cargo trips · "
            "import tax {import_tax} ISK · export tax {export_tax} ISK · "
            "transport {transport} ISK · risk {risk} ISK · total {total} ISK"
        ),
        "pi_profile_name": "Profile name",
        "pi_space_kind": "Space type",
        "pi_customs_office": "Customs office/POCO available",
        "pi_import_tax": "Import tax (%)",
        "pi_export_tax": "Export tax (%)",
        "pi_transport_rate": "Transport (ISK/m³)",
        "pi_cargo_capacity": "Cargo capacity (m³)",
        "pi_risk_markup": "Risk markup (%)",
        "pi_supply_tier": "Externally available input tier",
        "pi_profile_save": "Save profile",
        "pi_profile_new": "New profile",
        "pi_profile_saved": "Profile saved: {name}",
        "pi_profile_error": "Profile could not be saved: {message}",
        "pi_space_highsec": "Highsec",
        "pi_space_lowsec": "Lowsec",
        "pi_space_nullsec": "Nullsec",
        "pi_space_wormhole": "Wormhole",
        "pi_tier_0": "P0 raw material",
        "pi_tier_1": "P1 basic commodity",
        "pi_tier_2": "P2 refined commodity",
        "pi_tier_3": "P3 specialized commodity",
        "pi_tier_4": "P4 advanced commodity",
        "projects": "Production Projects",
        "blueprints": "Blueprints",
        "blueprint_page_detail": (
            "Personal BPOs and BPCs are joined with the manufacturing recipe from the active "
            "SDE build. Assets at the blueprint location remain separate from other locations."
        ),
        "blueprint_search": "Search product, blueprint, character, or location",
        "blueprint_product": "Product",
        "blueprint_owner": "Owner",
        "blueprint_kind": "Type",
        "blueprint_runs": "Runs",
        "blueprint_location": "Location ID",
        "blueprint_name": "Blueprint",
        "blueprint_original": "BPO",
        "blueprint_copy": "BPC",
        "blueprint_unlimited": "unlimited",
        "blueprint_empty": (
            "No usable manufacturing blueprints found yet. Synchronize a character with "
            "blueprint permission and a current SDE."
        ),
        "manufacturing_calculation": "Manufacturing calculation",
        "manufacturing_target_quantity": "Target quantity",
        "manufacturing_calculate": "Recalculate",
        "manufacturing_select_blueprint": "Select a blueprint to calculate.",
        "manufacturing_material": "Material",
        "manufacturing_required": "Required",
        "manufacturing_at_location": "At BP location",
        "manufacturing_total": "Total",
        "manufacturing_missing_local": "Missing locally",
        "manufacturing_blueprint_ready": "Blueprint runs sufficient",
        "manufacturing_blueprint_shortfall": "BPC is short by {count} runs",
        "manufacturing_materials_ready": "Materials complete at blueprint location",
        "manufacturing_materials_missing": "Materials incomplete at blueprint location",
        "manufacturing_plan_summary": (
            "{runs} runs · Output {output} · Surplus {surplus} · Duration {duration}\n"
            "{blueprint} · {materials}"
        ),
        "inventory": "Inventory & Logistics",
        "market": "Market & Calculation",
        "settings": "Settings & Characters",
        "local_data": "Local database ready",
        "app_version": "Version v{version}",
        "updates_title": "EVE Dolphin updates",
        "check_for_updates": "Check for updates",
        "checking_for_updates": "Checking for updates …",
        "update_button_available": "Update v{version} available",
        "update_available_title": "New version available",
        "update_versions": "Installed: v{current}  ·  New: v{new}",
        "update_metadata": "Published: {date}  ·  Download: {size}",
        "update_contents": "What's included",
        "update_no_notes": "No additional notes were provided for this update.",
        "update_start": "Start update",
        "update_later": "Later",
        "update_downloading": (
            "The verified update is downloading. EVE Dolphin will restart afterwards."
        ),
        "update_download_progress": "Downloading and verifying update: {percentage}%",
        "update_preparing": "Download complete. Verifying and preparing the update …",
        "update_failed": (
            "The update could not be prepared safely. The installed version remains unchanged. "
            "Reason: {reason}"
        ),
        "update_error_network": "The download from GitHub failed.",
        "update_error_package": "The downloaded package was incomplete or invalid.",
        "update_error_filesystem": "Windows could not prepare the update files.",
        "update_error_launch": "The external update process could not be started.",
        "update_error_unexpected": "An unexpected error occurred.",
        "update_result_succeeded": "Update to v{version} installed successfully.",
        "update_result_failed": (
            "Update to v{version} failed: {reason} The previous version was restored."
        ),
        "update_apply_error_parent_timeout": "EVE Dolphin did not close in time.",
        "update_apply_error_self_check": "The new version did not pass its self-check.",
        "update_apply_error_backup": "A previous update backup is blocking replacement.",
        "update_apply_error_validation": "The source or installation directory is invalid.",
        "update_apply_error_filesystem": "Windows or antivirus software is blocking a file.",
        "update_apply_error_launch": "The update process could not be started.",
        "update_apply_error_replacement": "The application files could not be replaced.",
        "update_install_unavailable": (
            "Updates can only be started from the installed Windows version."
        ),
        "update_current": "EVE Dolphin is already on the newest available version.",
        "update_check_failed": "Update information is currently unavailable.",
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
        "authorize_industry": "Authorize industry",
        "authorize_planetary": "Authorize PI",
        "sync_data": "Synchronize EVE data",
        "character_name": "Character",
        "scope_count": "Permissions",
        "authorization_status": "Authorization",
        "authorization_active": "Active",
        "authorization_required": "Reconnect",
        "linked_at": "Connected at",
        "character_count": "Connected EVE characters: {count}",
        "characters_ready": (
            "Connected characters are kept current automatically while the app is running."
        ),
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
            "The public EVE client ID is blank. Remove an empty EVE_SSO_CLIENT_ID "
            "override or provide a valid client ID."
        ),
        "sso_browser_failed": "The system browser could not be opened.",
        "sso_timeout": "The EVE sign-in was not completed within three minutes.",
        "sso_cancelled": "The EVE sign-in was cancelled.",
        "sso_wrong_character": (
            "A different character was selected for this permission upgrade. Repeat the "
            "process with the character selected in EVE Dolphin."
        ),
        "sso_invalid_response": "The EVE SSO response could not be verified safely.",
        "sso_network_failed": "EVE SSO is unavailable or the local callback port is in use.",
        "sso_keyring_failed": "The operating system credential store is unavailable.",
        "sso_failed": "The EVE character could not be connected.",
        "sync_running": "Synchronizing assets, blueprints, jobs, and PI colonies …",
        "sync_complete": "EVE data for {count} character(s) is current.",
        "sync_complete_auto": (
            "EVE data for {count} character(s) is current. Next check in 5 minutes."
        ),
        "automatic_sync_waiting": (
            "Automatic synchronization is active. All data is loaded immediately after "
            "connection and checked every 5 minutes afterwards."
        ),
        "sync_partial": (
            "{succeeded} of {count} character(s) synchronized completely. "
            "Failed data states are marked in the overview."
        ),
        "sync_permissions_missing": (
            "At least one EVE permission is missing. Select the character and authorize "
            "industry and/or PI with the visible permission buttons."
        ),
        "sync_network_failed": "EVE data could not be loaded because of a network error.",
        "sync_failed": "EVE data synchronization failed.",
        "sync_sde_failed": (
            "Static EVE data could not be updated. The last valid version remains active; "
            "details are marked in the overview."
        ),
        "sync_closing": "Waiting for the running EVE data synchronization to finish safely …",
        "data_status": "Local data status",
        "sde_missing": "SDE: missing",
        "sde_status": "SDE build {build} · {state} · released {date}",
        "resource_industry": "Industry",
        "resource_jobs": "Jobs",
        "resource_planetary": "PI",
        "data_current": "current",
        "data_stale": "stale",
        "data_failed": "fetch failed",
        "data_missing": "missing",
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
