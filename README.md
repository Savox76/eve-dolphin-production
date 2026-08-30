# EVE Production Tool

Lokal betriebenes Produktions-Cockpit für **EVE Online**, das Planetare Industrie (PI) und klassische Fertigung in einer gemeinsamen Planung verbindet. Jede Installation verwaltet ausschließlich die eigenen Charaktere und Daten des jeweiligen Spielers.

## Projektziel

Das Tool soll aus Blueprints, Kolonien, Assets, Marktpreisen und laufenden Jobs einen nachvollziehbaren Produktionsplan erstellen. Es beantwortet insbesondere:

- Welche Materialien und PI-Produkte werden benötigt?
- Was ist bereits vorhanden oder wird durch Kolonien erzeugt?
- Welche Zwischenprodukte sollten hergestellt und welche gekauft werden?
- Welche Kosten, Laufzeiten, Transporte und Produktionsslots entstehen?
- Welcher realistische Nettogewinn bleibt übrig?

## Geplanter Umfang von Version 1.0

- mehrere eigene EVE-Charaktere über EVE SSO
- Planetare Industrie von P0 bis P4
- Kolonieübersicht, Extractor-Timer und Produktionsprognosen
- PI-Zielplanung und Wurmloch-/POCO-Profile
- T1- und Komponentenfertigung
- Blueprints, Assets und Industry Jobs
- gemeinsamer PI-/Manufacturing-Produktionsgraph
- Build-or-Buy-Vergleich
- Markt-, Gebühren-, Gewinn- und Logistikkalkulation
- lokale Python-Desktop-Oberfläche auf Deutsch und Englisch
- lokale SQLite-Datenbank ohne Hoster oder separaten Datenbankdienst
- eigenständige Installation für jeden Spieler

Der vollständige Projektumfang steht im [Masterplan](MASTERPLAN.md). Ergänzend gelten [Produkt und Betriebsmodell](docs/PRODUCT.md), die [technische Architektur](docs/ARCHITECTURE.md), die [ESI-/SDE-Datenmatrix](docs/DATA_SOURCES.md), die [verbindlichen Referenzabläufe](docs/REFERENCE_WORKFLOWS.md), der [Formel- und Bewertungskatalog](docs/FORMULA_CATALOG.md), die [Seitenstruktur und Wireframes](docs/UX_STRUCTURE.md) sowie die Abnahmen von [Phase 0](docs/PHASE_0_ACCEPTANCE.md) und [Phase 1](docs/PHASE_1_ACCEPTANCE.md).

## Projektstatus

**Gesamtfortschritt: 15 %**

Nächster Meilenstein: **Phase 2 – EVE-Datenbasis**

Phase 1 ist abgeschlossen. Das technische Fundament enthält den lokalen Python-Client, die SQLite-Migrationsbasis, sichere Token-Speichergrenzen, automatisierte Qualitätsprüfungen und einen validierten Windows-Paketbuild. Phase 2 bindet als Nächstes EVE SSO, mehrere eigene Charaktere, SDE und ESI an.

## Entwicklung und lokaler Start

Voraussetzungen für die Entwicklung sind Python 3.12 und `uv`. Endnutzer benötigen diese Werkzeuge später nicht.

```bash
uv sync --locked --all-groups
uv run eve-production-tool --self-check
uv run eve-production-tool
```

Qualitätsprüfungen:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

Der Client legt veränderliche Daten im Anwendungsdatenverzeichnis des jeweiligen Betriebssystemnutzers ab. Ein explizites Testprofil kann mit `--data-dir <pfad>` gewählt werden. Build-Artefakte aus Pull Requests sind technische Testpakete und noch keine öffentlich signierten Releases.

## Entwicklungsgrundsätze

- `main` enthält nur geprüfte und lauffähige Änderungen.
- Funktionen werden in eigenen Branches entwickelt.
- Ein Merge erfolgt erst nach vollständig grünen erforderlichen Checks.
- EVE-Zugangsdaten und Secrets gehören niemals in das Repository.
- Refresh Tokens gehören in den sicheren Anmeldedatenspeicher des Betriebssystems und nicht in die SQLite-Datenbank.
- Das Tool führt keine automatisierten Aktionen im EVE-Client aus.
- Offizielle EVE-Schnittstellen und veröffentlichte statische Daten bilden die Grundlage.

## Geplanter Entwicklungsablauf

| Phase | Schwerpunkt | Gesamtstand nach Abnahme |
|---|---|---:|
| 0 | Produktspezifikation | 5 % |
| 1 | Technisches Fundament | 15 % |
| 2 | EVE-Datenbasis | 30 % |
| 3 | PI-MVP | 50 % |
| 4 | Manufacturing-MVP | 70 % |
| 5 | Integrierter Planer | 85 % |
| 6 | Wirtschaft und Betrieb | 95 % |
| 7 | Härtung und Release | 100 % |

## Rechtlicher Hinweis

EVE Production Tool ist eine unabhängige Drittanbieter-Anwendung und wird weder von CCP hf. entwickelt noch unterstützt oder offiziell empfohlen.

> © 2014 CCP hf. All rights reserved. "EVE", "EVE Online", "CCP", and all related logos and images are trademarks or registered trademarks of CCP hf.

Vor einer öffentlichen Veröffentlichung werden die aktuellen Developer-, Branding- und Third-Party-Richtlinien erneut geprüft.
