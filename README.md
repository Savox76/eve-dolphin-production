# EVE Production Tool

Privat betriebenes Produktions-Cockpit für **EVE Online**, das Planetare Industrie (PI) und klassische Fertigung in einer gemeinsamen Planung verbindet. Die erste Version ist nur für freigegebene Nutzer erreichbar, wird technisch aber von Beginn an mehrbenutzerfähig aufgebaut.

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
- responsive Oberfläche auf Deutsch und Englisch

Der vollständige Projektumfang steht im [Masterplan](MASTERPLAN.md). Die beschlossene Produkt- und Betriebsdefinition steht in [Produkt und Betriebsmodell](docs/PRODUCT.md).

## Projektstatus

**Gesamtfortschritt: 0 %**

Nächster Meilenstein: **Phase 0 – Produktspezifikation**

## Entwicklungsgrundsätze

- `main` enthält nur geprüfte und lauffähige Änderungen.
- Funktionen werden in eigenen Branches entwickelt.
- Ein Merge erfolgt erst nach vollständig grünen erforderlichen Checks.
- EVE-Zugangsdaten und Secrets gehören niemals in das Repository.
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
