# EVE Dolphin

**EVE Dolphin** ist ein lokaler, modularer Begleiter für **EVE Online**. Jede Installation bündelt die freigegebenen Daten der eigenen Charaktere, ohne dass dafür ein Hoster, ein zentrales Konto oder das Einloggen jedes Charakters im Spiel nötig ist. Die erste Version konzentriert sich bewusst auf Planetare Industrie (PI) und klassische Fertigung.

## Projektziel

Das erste Modul soll aus Blueprints, Kolonien, Assets, Marktpreisen und laufenden Jobs einen nachvollziehbaren Produktionsplan erstellen. Es beantwortet insbesondere:

- Welche Materialien und PI-Produkte werden benötigt?
- Was ist bereits vorhanden oder wird durch Kolonien erzeugt?
- Welche Zwischenprodukte sollten hergestellt und welche gekauft werden?
- Welche Kosten, Laufzeiten, Transporte und Produktionsslots entstehen?
- Welcher realistische Nettogewinn bleibt übrig?

Die gemeinsame Charakter-, Daten-, Markt- und Inventarbasis wird später von Mining- und PVE-/Missionsmodulen mitgenutzt. Diese Erweiterungen folgen erst nach der stabilen Industrie-/PI-Version und verändern den Umfang von Version 1.0 nicht.

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

Der vollständige Projektumfang steht im [Masterplan](MASTERPLAN.md). Ergänzend gelten [Produkt und Betriebsmodell](docs/PRODUCT.md), die [technische Architektur](docs/ARCHITECTURE.md), die [ESI-/SDE-Datenmatrix](docs/DATA_SOURCES.md), die [verbindlichen Referenzabläufe](docs/REFERENCE_WORKFLOWS.md), der [Formel- und Bewertungskatalog](docs/FORMULA_CATALOG.md), die [Seitenstruktur und Wireframes](docs/UX_STRUCTURE.md), die Abnahmen von [Phase 0](docs/PHASE_0_ACCEPTANCE.md) und [Phase 1](docs/PHASE_1_ACCEPTANCE.md) sowie der [aktuelle Stand von Phase 2](docs/PHASE_2_STATUS.md).

Die später benötigten Portalwerte, Scopes, PowerShell-Befehle und Sicherheitsregeln
stehen gesammelt in der **[Anleitung zur EVE-Developer-Anwendung](docs/EVE_DEVELOPER_APPLICATION.md)**.

## Geplante Module nach Version 1.0

- **Mining und Reprocessing:** persönliches Mining-Ledger, Ertrag, Bewertung, Aufbereitung, Ziele und lokal fortgeschriebene Historie
- **PVE und Missionen:** charakterübergreifende Sicht auf Standing, Wallet-Ereignisse, Beute, Verluste und Standortdaten sowie ein lokales Missionsjournal

ESI liefert nicht jeden aktiven Missionsschritt als vollständigen Live-Status. EVE Dolphin kombiniert deshalb später verfügbare ESI-Signale mit ausdrücklich gekennzeichneten lokalen Einträgen, statt eine nicht vorhandene Echtzeitüberwachung vorzutäuschen.

## Projektstatus

**Gesamtfortschritt: 15 %**

Nächster Meilenstein: **Phase 2 – EVE-Datenbasis**

Phase 1 ist abgeschlossen. Phase 2 ist technisch vollständig; Callback und erster echter
Charakterlogin wurden bestätigt. Ein neuer Charakter fordert die vier für Industrie und PI
benötigten Berechtigungen gemeinsam an, wird unmittelbar synchronisiert und während der
Laufzeit alle fünf Minuten erneut geprüft. Die ressourcenspezifischen ESI-Cachegrenzen
verhindern dabei unnötige Abrufe. Der formale Gesamtfortschritt bleibt bis zum vollständigen
Live-Datenabruf und Zwei-Charakter-Durchlauf gemäß
[Phase-2-Abnahme](docs/PHASE_2_ACCEPTANCE.md) bei `15 %`.

## Entwicklung und lokaler Start

Voraussetzungen für die Entwicklung sind Python 3.12 und `uv`. Endnutzer benötigen diese Werkzeuge später nicht.

```bash
uv sync --locked --all-groups
uv run eve-dolphin --self-check
uv run eve-dolphin
```

Für einen echten SSO-Test muss die vorkonfigurierte EVE-Developer-Anwendung für den
PKCE-Flow den exakten Callback `http://127.0.0.1:38636/callback` registriert haben. Die
öffentliche Client-ID ist bereits im Desktop-Client enthalten; ein Client Secret wird
nicht verwendet. Die vollständige Einrichtung steht in der
[Developer-Anwendungsanleitung](docs/EVE_DEVELOPER_APPLICATION.md). Nur für einen gezielten
Entwicklungstest kann die öffentliche Client-ID unter Windows überschrieben werden:

```powershell
$env:EVE_SSO_CLIENT_ID = "<alternative-öffentliche-client-id>"
uv run eve-dolphin
```

Ein Client Secret wird weder benötigt noch in den Desktop-Client eingebettet. Der erste
Verbindungsdialog fordert gemeinsam die vier minimalen Industrie-/PI-Scopes an, die Version
1.0 tatsächlich verwendet. Spätere Mining-, PVE- oder Corporation-Scopes werden weiterhin
erst mit dem jeweiligen Modul ergänzt.

Qualitätsprüfungen:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

Der Client legt veränderliche Daten im Anwendungsdatenverzeichnis des jeweiligen Betriebssystemnutzers ab. Ein explizites Testprofil kann mit `--data-dir <pfad>` gewählt werden. Build-Artefakte aus Pull Requests sind technische Testpakete und noch keine öffentlich signierten Releases.

## Veröffentlichung

- eine gemeinsame, plattformunabhängig strukturierte Python-Codebasis
- getrennte Installationspakete je Betriebssystem, zunächst Windows
- öffentlicher Quellcode, Tests und Buildworkflow in `Savox76/eve-dolphin-production`
- geprüfte Binärpakete, Prüfsummen und Änderungsprotokolle als
  [GitHub Releases](https://github.com/Savox76/eve-dolphin-production/releases) desselben
  Repositorys
- sichtbare Versions- und Updateprüfung; Installation beginnt nur nach dem Klick auf
  „Update starten“ und besitzt Selbsttest sowie Rollback

Der Desktop-Client benötigt für die anonyme Updateprüfung weiterhin kein GitHub-Konto und
kein GitHub-Token.

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

EVE Dolphin ist eine unabhängige Drittanbieter-Anwendung und wird weder von CCP hf. entwickelt noch unterstützt oder offiziell empfohlen.

> © 2014 CCP hf. All rights reserved. "EVE", "EVE Online", "CCP", and all related logos and images are trademarks or registered trademarks of CCP hf.

Vor einer öffentlichen Veröffentlichung werden die aktuellen Developer-, Branding- und Third-Party-Richtlinien erneut geprüft.
