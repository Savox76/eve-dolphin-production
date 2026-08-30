# Abnahme Phase 0 – Produktspezifikation

## Ergebnis

Phase 0 wurde am `30.08.2026` fachlich abgeschlossen. Alle vorgesehenen Spezifikationspakete liegen versioniert im Repository, die zugehörigen Pull Requests wurden erst nach erfolgreichen Repository-Checks in `main` übernommen.

- Phasengewicht im Masterplan: `5 %`
- Gesamtfortschritt nach Abnahme: `5 %`
- nächster Meilenstein: Phase 1 – Technisches Fundament
- offene Phase-0-Blocker: keine

## Abgenommene Ergebnisse

| Ergebnis | Nachweis | Arbeitspaket |
|---|---|---|
| Produktname, Kurzbeschreibung und Betriebsmodell | [PRODUCT.md](PRODUCT.md), D-004/D-005/D-007 | #3 |
| fünf reale PI-/Manufacturing-Abläufe | [REFERENCE_WORKFLOWS.md](REFERENCE_WORKFLOWS.md), D-010 | #2 |
| Datenquellen-, ESI- und Scope-Matrix | [DATA_SOURCES.md](DATA_SOURCES.md) | #6 |
| Architektur und v1.0-Scope | [ARCHITECTURE.md](ARCHITECTURE.md), D-006/D-008/D-009 | #6 |
| Formel-, Gebühren-, Rundungs- und Bewertungskatalog | [FORMULA_CATALOG.md](FORMULA_CATALOG.md), D-011 | #4 |
| Seitenstruktur, Nutzerwege und Wireframes | [UX_STRUCTURE.md](UX_STRUCTURE.md), D-012 | #5 |
| Masterplan und initiale Repository-Struktur | [MASTERPLAN.md](../MASTERPLAN.md), README und Issues | #1 |

## Prüfung der Abnahmekriterien

- [x] Alle untergeordneten Phase-0-Aufgaben sind abgeschlossen.
- [x] Alle Phase-0-Entscheidungen sind in `docs/DECISIONS.md` als beschlossen dokumentiert.
- [x] Masterplan und README entsprechen dem beschlossenen Stand.
- [x] Die erforderlichen Pull-Request- und `main`-Checks waren erfolgreich.
- [x] Formeln besitzen feste Kontrollbeispiele für spätere Golden Tests.
- [x] Desktop- und mobile Nutzerwege sind spezifiziert.
- [x] Datenquellen, Datenalter, manuelle Annahmen und Unsicherheit sind nachvollziehbar.
- [x] Phase 0 ist für den Beginn der technischen Implementierung freigegeben.

## Bewusste Verlagerungen in spätere Phasen

Diese Punkte sind keine offenen Spezifikationsentscheidungen, sondern geplante Umsetzungs- oder Validierungsarbeit:

- EVE-Client-Parität der Golden Tests wird mit der Rechenengine in Phase 2 automatisiert kontrolliert.
- reale SSO-, ESI- und Charakterdaten werden erst nach dem sicheren Fundament angebunden.
- konkrete Hosting-Zugangsdaten und Domains werden außerhalb des Repositorys konfiguriert.
- Corporation-Scopes, öffentliche Registrierung und Monetarisierung gehören nicht zu Version 1.0.
- Live-Wurmlochrouten und fremde POCO-Daten bleiben manuell beziehungsweise zeitgebunden.

## Eintritt in Phase 1

Phase 1 darf auf den getroffenen Entscheidungen aufbauen und umfasst als Nächstes:

1. TypeScript-Monorepo und gemeinsame Toolchain
2. Web-, API- und Worker-Grundgerüste
3. PostgreSQL und Docker-Compose-Entwicklungsumgebung
4. Konfigurations- und Secret-Schema ohne echte Zugangsdaten
5. automatisierte Format-, Typ-, Test- und Build-Checks
6. erste gemeinsame Domänentypen für Quellen, Datenstatus und Formelversionen
