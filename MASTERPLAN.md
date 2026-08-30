# EVE Dolphin — Masterplan

**Dokumentstatus:** Verbindlicher Projektentwurf

**Version:** 1.1

**Stand:** 30. August 2026

**Produktname:** EVE Dolphin

**Gesamtfortschritt:** 15 %

**Nächster Meilenstein:** Phase 2 – Live-Datenabnahme; Phase 3 – PI-MVP technisch in Arbeit

---

## 1. Zielbild

**EVE Dolphin** wird ein lokaler, modularer Python-Desktop-Client für **EVE Online**. Jeder Spieler betreibt eine eigene Installation mit seinen eigenen Charakteren und Daten. Version 1.0 verbindet klassische Industrie und Planetare Industrie (PI) in einer gemeinsamen Planung; Mining und PVE/Missionen folgen als eigenständige Module auf derselben Datenbasis.

Der Nutzer soll nicht nur erfahren, welche Materialien theoretisch benötigt werden. Das Tool soll beantworten:

- Was kann mit den vorhandenen Blueprints, Kolonien, Materialien und Charakteren produziert werden?
- Was fehlt, wo liegt es und was muss transportiert oder gekauft werden?
- Welche Zwischenprodukte sollten selbst hergestellt und welche besser gekauft werden?
- Wie viel ISK, Zeit, Frachtraum und Produktionskapazität bindet ein Projekt?
- Welcher realistische Nettogewinn bleibt nach allen Kosten?
- Welches Produkt nutzt Planeten, Produktionsslots und Kapital am besten?

### Produktversprechen

> Von der Rohstoffgewinnung auf dem Planeten bis zum verkauften Endprodukt in einem einzigen nachvollziehbaren Produktionsplan.

Dieses Versprechen gilt für Version 1.0. Langfristig wird EVE Dolphin zum persönlichen, charakterübergreifenden Informationscockpit für Industrie, Mining und PVE ausgebaut. Der aktuelle Versionsumfang bleibt dabei geschützt: Ein späteres Modul erhöht nicht rückwirkend die Abnahmekriterien der Industrie-/PI-Version.

### Leitprinzipien

1. **Reale statt geschönte Gewinne:** Gebühren, Steuern, Transport, Marktseite und gebundenes Kapital werden berücksichtigt.
2. **Ein gemeinsames Bestandsmodell:** PI, Assets, Blueprints, Einkaufslisten und Produktionsprojekte greifen auf dieselben Bestände zu.
3. **Erklärbare Berechnungen:** Jede Zahl lässt sich bis zu Quelle, Formel und Eingabewert zurückverfolgen.
4. **ESI-konform und sicher:** Das Tool liest erlaubte Daten, führt aber keine Spielaktionen automatisiert aus.
5. **Lokal und unabhängig:** Jede Installation gehört ihrem Nutzer; ein Hoster, zentrale Konten oder verkaufte Zugänge sind nicht erforderlich.
6. **Desktop zuerst:** Version 1.0 wird als eigenständiger Windows-Client ausgeliefert und bleibt technisch für weitere Desktop-Systeme portierbar.
7. **Modular erweiterbar:** Charaktere, Berechtigungen, Assets, Markt- und Statusdaten bilden einen gemeinsamen Kern; Mining und PVE bleiben fachlich getrennte Module.

---

## 2. Umfang der Version 1.0

### 2.1 Planetare Industrie

Version 1.0 unterstützt PI von **P0 bis P4**.

#### Kolonieübersicht

- mehrere eigene EVE-Charaktere
- alle aus ESI verfügbaren Kolonien
- System, Planet, Planetentyp und Charakter
- Command Center und Ausbaulevel
- Pins, Links und Routen
- Extractor Control Units und Programme
- Basic, Advanced und High-Tech Processors
- Launchpads und Storage Facilities
- letzte ESI-Aktualisierung und Datenalter

#### Überwachung und Prognose

- Restlaufzeit von Extractor-Programmen
- Status: aktiv, endet bald, abgelaufen oder Daten veraltet
- geschätzter P0-Ertrag je Stunde und Tag
- geschätzte Füllstände von Lagern und Launchpads
- erkennbare Unterversorgung von Fabriken
- möglicher Produktionsstillstand
- erwartete P1–P4-Ausgabe nach Schematic und Zyklus
- nächste sinnvolle Abhol- oder Nachfüllzeit

Prognosen werden klar als **Schätzung** gekennzeichnet, weil ESI keine sekundengenaue Live-Ansicht der Kolonie darstellt. Neben jeder Prognose stehen Zeitpunkt und Alter der zugrunde liegenden Daten.

#### PI-Produktionsplaner

Der Nutzer wählt ein Zielprodukt, eine Menge und einen Zeitraum, beispielsweise:

> 5.000 Robotics innerhalb von 30 Tagen.

Das Tool berechnet:

- benötigte P0-, P1-, P2-, P3- und P4-Vorprodukte
- erforderliche Fabrikzyklen
- Tages- und Gesamtbedarf
- vorhandene Bestände
- erwartete Erzeugung der bestehenden Kolonien
- Fehlmengen und Überschüsse
- Import- und Exportmengen je Planet
- erforderliches Transportvolumen
- POCO-Steuern und Nettokosten
- Kaufalternative am gewählten Handelsplatz

#### PI-Profile

- Rohstoff-/Extraktionsplanet
- P0-zu-P1-Planet
- P2-Kombinationsplanet
- P3-/P4-Factory-Planet
- minimale tägliche Pflege
- maximale Produktionsmenge
- maximale ISK pro Tag
- vollständige Versorgung eines ausgewählten Endprodukts

#### Wurmloch-Modus

- Planeten und Planetentypen eines gewählten Wurmlochsystems
- manuell bestätigtes Vorhandensein von Customs Offices/POCOs
- individuelle POCO-Steuern je Planet oder Profil
- Trennung zwischen internem Wurmlochpreis und Hub-Marktpreis
- Frachtraum für Ein- und Ausfuhr
- konfigurierbarer Risiko-/Logistikaufschlag
- Bewertung, welche PI-Ketten im System vollständig oder teilweise möglich sind

Fremde POCO-Daten oder individuelle Steuersätze, die ESI nicht zuverlässig bereitstellt, werden manuell gepflegt und sichtbar als manuelle Werte markiert.

### 2.2 Klassische Industrie

#### Produktionsprojekte

- Gegenstand und Zielmenge auswählen
- Blueprint Original oder Copy zuordnen
- ME, TE und verfügbare Runs berücksichtigen
- vollständige Materialliste erzeugen
- Zwischenprodukte rekursiv auflösen
- vorhandene Assets abziehen
- Produktionsort und Charakter auswählen
- Produktionszeit und Slotbedarf berechnen
- Projektzustände: Entwurf, geplant, einkaufen, bereit, aktiv, teilweise fertig, abgeschlossen, verkauft

#### Unterstützte Tätigkeiten in Version 1.0

- T1 Manufacturing
- Komponentenfertigung
- Blueprint-bezogene ME-/TE-Werte
- persönliche Industry Jobs
- persönliche Blueprints und Assets
- manuell konfigurierbare Struktur-, Rig- und Steuerprofile

#### Für Version 1.3 vorgesehen

- Invention und T2-Ketten
- Reactions
- Copy- und Research-Planung
- Corporation Blueprints, Assets und Jobs
- Capital- und komplexe Reaction-Ketten

Die Datenstruktur wird in Version 1.0 bereits auf diese Aktivitäten vorbereitet, ohne ihre vollständige Benutzeroberfläche vorzeitig zu bauen.

### 2.3 Gemeinsame Produktionskette

PI und klassische Fertigung dürfen keine getrennten Rechner bleiben. Ein Produktionsprojekt verwendet deshalb einen gemeinsamen Abhängigkeitsgraphen:

1. Endprodukt auswählen.
2. Blueprint-Materialien auflösen.
3. PI-Produkte erkennen.
4. Bedarf mit PI-Prognose und Lagerbestand vergleichen.
5. Für jede Stufe „Bauen, durch PI erzeugen, aus Lager nehmen oder kaufen“ bewerten.
6. Einkauf, Transporte und Jobs zeitlich ordnen.
7. Gewinn, Kapitalbindung und Fertigstellungstermin berechnen.

Jede Komponente erhält eine Entscheidung:

- **Aus Bestand**
- **Durch PI erzeugen**
- **Herstellen**
- **Kaufen**
- **Manuell festgelegt**

Automatische Empfehlungen dürfen jederzeit manuell überschrieben werden.

### 2.4 Markt, Kosten und Gewinn

- auswählbare Handelsregion und bevorzugter Hub
- sofortiger Einkauf über Sell Orders
- geplanter Einkauf über Buy Orders
- sofortiger Verkauf an Buy Orders
- geplanter Verkauf über Sell Orders
- gewichtete Preise für tatsächlich benötigte Mengen
- Marktgebühren, Broker Fee und Sales Tax
- Industry Job Cost anhand offizieller Preis- und Systemdaten
- Struktursteuer und manuelle Standortboni
- PI Import-/Exportsteuer
- Transportkosten oder eigener ISK/m³-Satz
- Sicherheits-/Logistikaufschlag für Wurmlochtransporte
- Opportunitätskosten vorhandener Materialien
- Nettogewinn und Marge
- Gewinn pro Stunde, Produktionsslot, Planet, m³ und eingesetztem ISK
- Kapitalbindungsdauer und optional annualisierte Rendite als Vergleichswert

Berechnungsansichten zeigen eine detaillierte Kostenbrücke vom Materialpreis bis zum Nettogewinn.

### 2.5 Inventar und Logistik

- persönliche Assets je Charakter
- Gruppierung nach Station, Struktur, System und Container
- reservierte Mengen für aktive Projekte
- frei verfügbarer Bestand
- PI-Bestände getrennt nach Planet und Lager
- zentrale Einkaufsliste
- Transporte zwischen Hub, Produktionsort und Planeten
- Volumen, Anzahl Flüge und frei definierbare Schiffskapazität
- CSV-Export und kopierbare kompakte Einkaufsliste

### 2.6 Dashboard und Benachrichtigungen

- aktive und demnächst fertige Industry Jobs
- PI Extractors, die bald enden
- Fabriken mit erwarteter Unterversorgung
- offene Einkaufs- und Transportaufgaben
- aktueller Kapitalbedarf
- erwarteter Projektgewinn
- veraltete ESI-Daten oder fehlgeschlagene Synchronisation
- In-App-Benachrichtigungen

Discord, E-Mail oder Push-Benachrichtigungen werden nach Version 1.0 als optionale Kanäle ergänzt.

---

## 3. Nicht Bestandteil von Version 1.0

- automatisches Starten oder Verändern von Extractor-Programmen
- automatisches Verschieben, Importieren oder Exportieren von PI-Waren
- automatische In-Game-Produktion oder Markthandel
- Eingriff in den EVE-Client, Cache-Scraping oder Client-Automation
- garantierte Vorhersage zukünftiger Marktpreise oder Ressourcen-Hotspots
- vollständige Corporation-Verwaltung
- native Android- oder iOS-App
- öffentliche Bezahlversion

Das Tool bleibt ein Planungs-, Analyse- und Überwachungssystem. Aktionen im Spiel führt der Spieler selbst aus.

---

## 4. Hauptansichten der Anwendung

### 4.1 Übersicht

- wichtigste Warnungen
- aktive Projekte
- PI-Status aller Charaktere
- nächste fertige Jobs
- gebundenes Kapital und erwarteter Gewinn

### 4.2 Planetare Industrie

- Charakter- und Planetenfilter
- Koloniekarten bzw. strukturierte Pin-Ansicht
- Extractor-Timer
- Produktionsfluss je Planet
- Lagerprognose
- Gewinn je Planet und Produkt

### 4.3 PI-Planer

- Zielprodukt, Menge und Zeitraum
- P0–P4-Baum
- benötigte Planeten/Fabriken
- vorhandene Kapazität
- Defizite und Optimierungsvorschläge

### 4.4 Produktionsprojekte

- Projektliste
- Materialbaum
- Build-or-Buy-Entscheidungen
- Zeitplan
- Einkauf und Logistik
- Soll-/Ist-Kosten

### 4.5 Blueprints

- BPO/BPC
- Besitzer und Standort
- ME/TE
- Runs
- nutzbare Produkte

### 4.6 Inventar

- Gesamtbestand
- reserviert/frei
- Standort und Container
- Marktwert
- fehlende Materialien

### 4.7 Markt und Kalkulation

- Preisquelle und Datenalter
- Marktseite und Mengentiefe
- Gebührenprofile
- Gewinnvergleich

### 4.8 Einstellungen

- EVE-Charaktere und Berechtigungen
- Produktionsorte
- Handelsplätze
- POCO- und Steuerprofile
- Transportkosten
- Aktualisierungsintervalle
- Datenschutz und Datenlöschung

---

## 5. Datenquellen und Integrationen

### 5.1 Offizielle Quellen

- **EVE SSO / OAuth 2.0:** Charakteranmeldung und ausdrücklich erteilte Berechtigungen
- **ESI:** Charaktere, Kolonien, Blueprint-/Asset-/Industry-/Wallet-/Marktdaten, soweit der jeweilige Scope und die Rolle dies erlauben
- **EVE Static Data Export (SDE):** Typen, Blueprints, Schematics, Materialien, Zeiten und statische Universumsdaten

### 5.2 ESI-Datenklassen

Für Version 1.0 werden mindestens benötigt:

- Charakteridentität
- persönliche Assets
- persönliche Blueprints
- persönliche Industry Jobs
- persönliche Kolonieliste
- Layout einer einzelnen Kolonie
- öffentliche Planet-, System- und Typdaten
- öffentliche Schematics
- öffentliche Marktorders und Marktpreise
- Industry Systems/Cost Indices

Corporation-Endpunkte werden erst aktiviert, wenn Corporation-Funktionen umgesetzt und die erforderlichen Rollen sauber geprüft sind.

### 5.3 Aktualisierung und Cache

- ESI-Cache-Header und ETags werden respektiert.
- Das Tool zeigt den Zeitpunkt der letzten erfolgreichen Aktualisierung.
- Veraltete Daten bleiben sichtbar, werden aber deutlich markiert.
- Hintergrundjobs verwenden begrenzte Parallelität, Backoff und Retry.
- ESI-Fehlerlimits werden überwacht.
- SDE-Version und Importdatum werden gespeichert.
- Ein SDE-Update wird zuerst validiert und anschließend atomar aktiviert.

### 5.4 Manuelle Daten

Manuell gepflegt werden insbesondere:

- fremde oder nicht verfügbare POCO-Steuern
- individuelle Struktursteuern und Rig-/Standortboni
- Transportkosten und Risikoaufschläge
- interne Ankauf- oder Corporation-Preise
- gewünschte Sicherheitsreserven

Jeder manuelle Wert trägt Quelle, Änderungsdatum und optional eine Notiz.

---

## 6. Berechnungsmodell

### 6.1 Grundsatz

Alle Berechnungen verwenden versionierte Eingaben. Ein gespeicherter Produktionsplan behält seine damaligen Preise, Gebühren und Formeln, auch wenn sich aktuelle Marktdaten später verändern. Dadurch bleibt ein Soll-/Ist-Vergleich möglich.

### 6.2 Materialbedarf

- Mengen und Aktivitäten stammen aus dem SDE.
- ME- und Rundungsregeln werden in einer zentralen, getesteten Engine implementiert.
- Zwischenprodukte werden als gerichteter Abhängigkeitsgraph aufgelöst.
- Zyklische oder ungültige Abhängigkeiten werden abgefangen.
- BPC-Runs und Projektmengen begrenzen mögliche Produktionslose.

### 6.3 Build-or-Buy

Für jede Komponente werden mindestens verglichen:

- vollständige Eigenproduktionskosten
- sofortige Einkaufskosten
- geplante Buy-Order-Kosten
- Produktionszeit und Slotverbrauch
- bereits verfügbarer Bestand
- Logistik und Gebühren

Die Empfehlung kann nach mehreren Zielen erfolgen:

- niedrigste Gesamtkosten
- schnellste Fertigstellung
- höchster Gewinn
- höchste ISK pro Produktionsstunde
- geringster Kapitalbedarf

### 6.4 PI-Prognose

- ESI-Snapshot als Ausgangszustand
- Extractor-Menge und Zykluszeit
- Schematic-Eingänge, Ausgänge und Zykluszeiten
- Puffer- und Lagerkapazitäten
- bekannte Routen zwischen Pins
- Import-/Exportpläne

Prognosen enden oder werden unsicher markiert, sobald unbekannte Spielereingriffe, erschöpfte Lager, abgelaufene Extractors oder veraltete Daten die Aussagekraft begrenzen.

### 6.5 Gewinn

**Nettogewinn = Verkaufserlös − Materialwert − Jobkosten − Marktgebühren − PI-Steuern − Logistikkosten − sonstige Kosten**

Der Materialwert kann wahlweise bewertet werden als:

- tatsächlicher Einkaufspreis
- aktueller Wiederbeschaffungspreis
- sofortiger Verkaufspreis
- eigener interner Preis

Die gewählte Bewertungsmethode wird im Ergebnis angezeigt.

---

## 7. Technische Architektur

### 7.1 Zielarchitektur

- **Client:** lokaler Python-Desktop-Client mit PySide6/Qt
- **Domänenkern:** UI-unabhängige Python-Dienste und Berechnungslogik
- **Hintergrundaufgaben:** lokale ESI-Synchronisation, Preisaktualisierung, SDE-Import und Prognosen während der Client läuft
- **Datenbank:** lokale SQLite-Datenbank mit versionierten Migrationen
- **SSO:** Authorization Code mit PKCE über Systembrowser und lokalen Callback
- **Tokenablage:** sicherer Anmeldedatenspeicher des Betriebssystems
- **Bereitstellung:** eigenständiges Windows-Release inklusive Python-Laufzeit
- **Repository:** privates GitHub-Repository

Für Endnutzer sind weder Python, Docker, PostgreSQL noch ein Hoster erforderlich. Framework- und Paketversionen werden zu Beginn von Phase 1 festgeschrieben und durch Lockfiles reproduzierbar gehalten.

### 7.2 Kernkomponenten

1. lokales Profil und Charakterverwaltung
2. EVE-SSO- und Tokenverwaltung mit PKCE
3. ESI-Client mit Cache, Retry und Rate-Limit-Schutz
4. SDE-Importer
5. gemeinsamer Gegenstands- und Bestandskatalog
6. PI-Snapshot- und Prognose-Engine
7. Blueprint-/Material-Engine
8. Produktionsgraph und Build-or-Buy-Optimierer
9. Markt- und Kosten-Engine
10. Projekt-, Aufgaben- und Benachrichtigungssystem

### 7.3 Datenmodell – Hauptobjekte

- LocalProfile
- EveCharacter
- EveAuthorization
- Location
- InventoryItem und InventorySnapshot
- BlueprintInstance und BlueprintType
- IndustryJob
- Colony und ColonySnapshot
- PlanetPin, PlanetLink und PlanetRoute
- ExtractorProgram
- Schematic
- MarketPriceSnapshot
- FacilityProfile
- PocoTaxProfile
- ProductionProject
- ProductionNode
- MaterialReservation
- PurchaseTask
- HaulingTask
- Notification
- AuditEvent

### 7.4 Trennung von statischen und dynamischen Daten

- SDE-Daten sind versioniert und weitgehend unveränderlich.
- ESI-Daten werden als aktueller Zustand plus ausgewählte Snapshots gespeichert.
- Nutzerwerte liegen in eigenen Tabellen und werden durch SDE-Updates nicht überschrieben.
- Produktionspläne speichern ihre verwendeten Eingaben als Kalkulationssnapshot.

---

## 8. Sicherheit, Datenschutz und EVE-Konformität

### 8.1 Authentifizierung

- Anmeldung ausschließlich über den offiziellen EVE-SSO-Prozess
- Authorization Code mit PKCE für den lokalen Desktop-Client
- minimale erforderliche Scopes
- getrennte Freigabe pro Charakter
- Prüfung von `state`, Token-Signatur, Aussteller, Zielgruppe und Ablaufzeit
- Refresh Tokens nur im sicheren Anmeldedatenspeicher des Betriebssystems ablegen
- kein Client Secret in Release-Paket, SQLite, Repository oder Logs
- Widerruf und vollständige Trennung eines Charakters jederzeit möglich

### 8.2 Datenzugriff

- eine Installation verarbeitet ausschließlich die lokal verbundenen Charaktere
- Corporation-Daten erfordern später eigene Berechtigungs- und Rollenprüfung
- sensible Werte werden nicht in Logs geschrieben
- lokale Datenexporte enthalten keine Tokens
- Backup vor Migrationen sowie Wiederherstellungstest vor Version 1.0

### 8.3 Spielregeln

- keine Client-Manipulation
- keine Eingabesimulation
- keine automatisierten Spielaktionen
- keine Cache- oder Paketmanipulation
- nur offizielle Schnittstellen und zulässige manuelle Eingaben
- Developer License Agreement, Branding-Regeln und Third Party Policies werden vor Veröffentlichung erneut geprüft

---

## 9. Entwicklungs- und Qualitätsprozess

### 9.1 Git-Workflow

- `main` enthält nur geprüfte, lauffähige Versionen.
- Jede Funktion entsteht in einem Feature-Branch.
- Änderungen werden über Pull Requests geprüft.
- Übernahme in `main` erfolgt nur, wenn alle automatischen Prüfungen grün sind.
- Datenbankmigrationen sind versioniert und rückwärts nachvollziehbar.
- Releases erhalten Versionsnummer, Changelog und Migrationshinweise.

### 9.2 Definition of Done

Eine Funktion ist erst fertig, wenn:

- Anforderungen und Grenzfälle dokumentiert sind,
- Implementierung und Datenmigration vorliegen,
- Unit- und Integrationstests bestehen,
- Fehlerzustände sinnvoll angezeigt werden,
- Desktop-Ansicht, unterschiedliche Fenstergrößen und Skalierungsstufen geprüft sind,
- sicherheitsrelevante Daten nicht geloggt werden,
- Nutzertext auf Deutsch und Englisch vorhanden ist,
- Abnahmekriterien erfüllt wurden.

### 9.3 Teststrategie

- Unit-Tests für ME-/TE-, PI-, Gebühren- und Gewinnformeln
- Golden Tests mit fest eingefrorenen SDE-/ESI-Beispieldaten
- Integrationstests für ESI-Cache, Token-Erneuerung und Fehlerbehandlung
- Vergleich ausgewählter Berechnungen mit dem EVE-Client
- Tests mit leeren, sehr großen und teilweise verfügbaren Beständen
- Tests mit mehreren Charakteren und gleichen Gegenständen an mehreren Orten
- End-to-End-Test vom Login bis zum abgeschlossenen Produktionsprojekt
- lokaler Backup-/Restore-Test

### 9.4 Beobachtbarkeit

- Gesundheitsstatus für Client, lokale Datenbank und ESI-Synchronisation
- strukturierte, datensparsame Logs
- Fehler-ID für verständliche Fehlermeldungen
- Synchronisationshistorie
- Anzeige von ESI-Datenalter und SDE-Version

---

## 10. Entwicklungsphasen und Fortschrittsgewichtung

Die Prozentanzeige beschreibt den gewichteten Gesamtfortschritt bis Version 1.0. Eine Phase gilt nur nach erfüllter Abnahme als vollständig.

| Phase | Ergebnis | Gewicht | Gesamtstand nach Abnahme |
|---|---|---:|---:|
| 0. Produktspezifikation | Entscheidungen, UX-Skizze, Daten- und Formelvertrag | 5 % | 5 % |
| 1. Fundament | Repository, App, Datenbank, CI, Migrationen, Grundlayout | 10 % | 15 % |
| 2. EVE-Datenbasis | SSO, mehrere Charaktere, SDE, ESI-Sync, Cache | 15 % | 30 % |
| 3. PI-MVP | Kolonien, P0–P4, Timer, Prognosen, POCO-Profile | 20 % | 50 % |
| 4. Manufacturing-MVP | Blueprints, Assets, Jobs, Materialien, Projekte | 20 % | 70 % |
| 5. Integrierter Planer | PI + Manufacturing + Bestand + Build-or-Buy | 15 % | 85 % |
| 6. Wirtschaft und Betrieb | Markt, Kosten, Gewinn, Logistik, Warnungen | 10 % | 95 % |
| 7. Härtung und Release | E2E, Sicherheit, Backup, Dokumentation, v1.0 | 5 % | 100 % |

### Phase 0 – Produktspezifikation

**Aufgaben**

- endgültigen Namen und visuelle Richtung festlegen
- privat gehostete oder rein lokale Installation entscheiden
- erste Handelsplätze und Produktionsorte bestimmen
- PI- und Manufacturing-Beispielfälle dokumentieren
- Gebühren- und Bewertungsmethoden festlegen
- erste Wireframes erstellen
- Datenfelder und Formeln als Vertrag festschreiben

**Abnahme**

- fünf reale Beispielszenarien sind vollständig beschrieben
- alle Eingaben und erwarteten Ergebnisse sind definiert
- Architekturentscheidung ist dokumentiert
- Scope von v1.0 ist eingefroren

### Phase 1 – Fundament

**Aufgaben**

- privates Repository und Branch-Regeln
- Python-Projektstruktur und reproduzierbare Entwicklungsumgebung
- PySide6-Anwendungsgerüst und lokale SQLite-Migrationen
- CI für Formatierung, Typprüfung, Tests und Build
- deutsch/englische Übersetzungsstruktur
- Grundnavigation und skalierbares Desktop-Dark-UI
- lokale Datenpfade, OS-Anmeldedatenspeicher und Konfigurationsmanagement
- erster reproduzierbarer Windows-Paketbuild

**Abnahme**

- frische Installation startet reproduzierbar
- Tests laufen automatisch
- `main` ist geschützt und grün
- Grundansichten funktionieren bei den unterstützten Desktop-Auflösungen und Skalierungsstufen
- Testpaket startet auf einem Windows-System ohne separat installiertes Python

### Phase 2 – EVE-Datenbasis

**Aufgaben**

- EVE-Developer-Anwendung konfigurieren
- SSO-Anmeldung und Charakterverknüpfung
- verschlüsselte Tokenablage und Erneuerung
- mehrere Charaktere je lokaler Installation
- SDE-Download, Prüfung, Import und Versionierung
- ESI-Client mit ETag, Cache, Retry und Fehlerlimit-Schutz
- erste Asset-, Blueprint-, Job- und Planetensynchronisation

**Abnahme**

- Charakter lässt sich verbinden und widerrufen
- zwei oder mehr eigene Charaktere können parallel synchronisiert werden
- SDE-Version ist sichtbar
- veraltete und fehlgeschlagene Daten werden korrekt markiert

### Phase 3 – PI-MVP

**Aufgaben**

- Kolonie- und Layoutimport
- Auflösung von Planet-, Pin- und Produkttypen
- Extractor-Timer
- Schematic- und Fabrikfluss
- P0–P4-Abhängigkeitsbaum
- Lager- und Produktionsprognose
- POCO-Steuerprofile
- PI-Zielplaner
- Wurmlochprofil

**Abnahme**

- reale Kolonien mehrerer Charaktere werden korrekt angezeigt
- ausgewählte Produktionsmengen stimmen mit manueller EVE-Prüfung überein
- abgelaufene Extractors und erwartete Engpässe werden erkannt
- ein P2-, P3- und P4-Ziel lässt sich vollständig rückwärts planen
- POCO- und Transportkosten erscheinen in der Kalkulation

### Phase 4 – Manufacturing-MVP

**Aufgaben**

- persönliche Blueprints und ME/TE
- Blueprint-Suche und Produktwahl
- rekursive Materialauflösung
- Asset-Abgleich und Reservierungen
- Industry Jobs und Laufzeiten
- Produktionsprojekte und Statusworkflow
- Standort-/Strukturprofile

**Abnahme**

- drei unterschiedliche T1-/Komponentenprojekte stimmen mit dem Spiel überein
- BPC-Runs und Bestände werden korrekt begrenzt
- aktive Jobs und reservierte Materialien werden nicht doppelt verplant
- Einkaufsliste enthält nur tatsächliche Fehlmengen

### Phase 5 – Integrierter Planer

**Aufgaben**

- gemeinsamer Produktionsgraph
- PI-Produkte in Manufacturing-Projekten
- Build-or-Buy je Komponente
- alternative Produktionswege
- Zeit- und Abhängigkeitsplanung
- manuelle Overrides
- Erkläransicht für Empfehlungen

**Abnahme**

- ein Endprodukt mit PI-Anteilen wird lückenlos geplant
- Bestand, PI-Ertrag, Eigenbau und Kauf werden korrekt kombiniert
- jede Empfehlung ist bis zu Preisen und Formeln nachvollziehbar
- Änderung eines Inputs aktualisiert alle abhängigen Ergebnisse

### Phase 6 – Wirtschaft und Betrieb

**Aufgaben**

- Marktorder- und Preis-Snapshots
- mengenabhängige Preisermittlung
- Gebühren, Steuern und Jobkosten
- Gewinn-, Slot- und Kapitalanalyse
- Transportaufgaben und Frachtraum
- Dashboard und Warnungen
- Soll-/Ist-Auswertung

**Abnahme**

- Kostenbrücke stimmt mit manuellen Kontrollrechnungen überein
- Marktseite und Datenalter sind immer sichtbar
- PI- und Manufacturing-Gewinn lassen sich getrennt und gemeinsam auswerten
- Einkauf und Transporte ergeben eine ausführbare Aufgabenliste

### Phase 7 – Härtung und Release

**Aufgaben**

- vollständige End-to-End-Szenarien
- Sicherheits- und Datenschutzprüfung
- Backup und Restore
- Installations- und Nutzerhandbuch
- Fehlermeldungen und Supportdiagnose
- Performanceprüfung mit großen Assets und mehreren Charakteren
- Version 1.0 und Changelog

**Abnahme**

- keine offenen kritischen oder hohen Fehler
- Neuinstallation und Update sind dokumentiert und getestet
- Backup lässt sich wiederherstellen
- alle v1.0-Szenarien sind erfolgreich abgenommen

---

## 11. Abnahmeszenarien für Version 1.0

1. **PI-Überwachung:** Zwei Charaktere verbinden, alle Kolonien laden und bald endende Extractors erkennen.
2. **P3-Zielplanung:** Zielmenge festlegen, Vorprodukte, Fabrikzyklen, Import/Export und POCO-Steuer korrekt berechnen.
3. **T1-Produktion:** Blueprint auswählen, ME/TE anwenden, Bestand abziehen und reale Fehlmengen bestimmen.
4. **Verbundprojekt:** Endprodukt mit PI-Anteilen planen und Bedarf zwischen Kolonie, Lager, Eigenbau und Einkauf aufteilen.
5. **Build-or-Buy:** Mehrere Zwischenprodukte anhand derselben Markt- und Kostenbasis korrekt vergleichen.
6. **Wurmlochlogistik:** POCO-Steuer, Frachtraum und Risikoaufschlag in die Nettokalkulation aufnehmen.
7. **Soll/Ist:** Produktionsplan speichern, später tatsächliche Kosten und Erlöse eintragen und Abweichung ausweisen.

---

## 12. Zusammenarbeit und Verantwortlichkeiten

### Projektinhaber

- reale Produktionsziele und Arbeitsabläufe erklären
- Prioritäten und Produktentscheidungen treffen
- EVE-Developer-Anwendung im eigenen Konto registrieren
- Charaktere selbst über EVE SSO autorisieren
- Berechnungen mit ausgewählten In-Game-Werten gegenprüfen
- Funktionen in verständlichen Etappen abnehmen

Passwörter, Client Secrets und Refresh Tokens werden niemals im Chat oder Repository geteilt.

### Entwicklung

- Architektur, Datenmodell und UX ausarbeiten
- Funktionen implementieren
- Tests und Dokumentation pflegen
- Sicherheits- und ESI-Regeln einhalten
- Fortschritt nach der gewichteten Tabelle berichten
- Änderungen erst nach grünen Prüfungen in `main` übernehmen
- Risiken, Abweichungen und notwendige Entscheidungen früh sichtbar machen

### Gemeinsamer Arbeitsrhythmus

1. Ein klar abgegrenztes Paket auswählen.
2. Akzeptanzkriterien bestätigen.
3. Paket in Feature-Branch umsetzen.
4. Automatisch und manuell testen.
5. Ergebnis anhand eines realen EVE-Falls prüfen.
6. Nach grüner Abnahme in `main` übernehmen.
7. Fortschrittsstand und nächste Aufgabe aktualisieren.

---

## 13. Hauptrisiken und Gegenmaßnahmen

| Risiko | Auswirkung | Gegenmaßnahme |
|---|---|---|
| Änderungen an ESI oder SDE | Import oder Synchronisation bricht | Adapter, Versionierung, Contract-Tests, sichtbarer Datenstatus |
| Falsche Rundungs- oder Gebührenformel | falsche Gewinne/Materialmengen | zentrale Engine, Golden Tests, Vergleich mit dem EVE-Client |
| ESI-Daten sind verzögert | PI-Prognose wirkt aktueller als sie ist | Zeitstempel, Unsicherheitsstatus, Snapshot-Modell |
| Zu großer Funktionsumfang | v1.0 wird nie stabil | klare Phasen, Nach-v1.0-Liste, keine Scope-Erweiterung ohne Tausch |
| Token- oder Datenleck | Kontodaten gefährdet | minimale Scopes, Verschlüsselung, Secret-Trennung, Log-Filter |
| Marktpreis verzerrt | unrealistische Kalkulation | Mengentiefe, Marktseite, Datenalter, manuelle Preisprofile |
| Wurmloch-/POCO-Daten fehlen | Kosten nicht automatisch bestimmbar | manuelle Profile mit Quelle und Änderungsdatum |
| Öffentliche Nutzung wird zu früh begonnen | Sicherheits- und Betriebsaufwand steigt | zuerst private v1.0, danach eigener Public-Readiness-Check |
| ESI zeigt klassische Missionen nicht vollständig | scheinbare Live-Ansicht wäre unzuverlässig | ESI-Signale mit lokalem Missionsjournal kombinieren und Datenquelle sichtbar machen |

---

## 14. Erweiterungen nach Version 1.0

### Version 1.1 – Mining und Reprocessing

- persönliches Mining-Ledger aller freigegebenen Charaktere
- Auswertung nach Erz, Eis, Gas, System, Charakter und Zeitraum
- Ertrags-, Marktwert- und Zielauswertung
- Aufbereitungsprofile und Vergleich von Rohverkauf, Reprocessing und Weiterverarbeitung
- manuell erfasste Flotten- und Mining-Sessions, wenn ESI den Kontext nicht liefert
- lokale Snapshots für eine eigene Historie über das jeweils von ESI gelieferte Zeitfenster hinaus

Das aktuelle ESI-Mining-Ledger liefert persönliche Mining-Einträge der vergangenen 30 Tage. EVE Dolphin kann ältere Daten erst ab dem ersten eigenen Abruf lokal fortschreiben und stellt fehlende Historie nicht nachträglich her.

### Version 1.2 – PVE und Missionen

- charakterübergreifende Übersicht über NPC-Standing und ausgewählte Wallet-Ereignisse
- Missionsbelohnungen, Bounties und PVE-Einnahmen soweit aus ESI-Daten zuverlässig ableitbar
- Loot-/Asset-Auswertung, Verluste und jüngste Killmails
- optionaler Charakterstandort nur mit ausdrücklich freigegebenem Scope
- lokales Missionsjournal mit Agent, Mission, Ziel, Status, Ablaufzeit und Notizen
- lokale PVE-Sessions mit Einnahmen, Kosten, Beute, Verlusten und Zeitaufwand

ESI besitzt keinen allgemeinen Endpunkt, der alle aktiven klassischen Missionen und ihre Ziele vollständig als Live-Journal liefert. Deshalb kombiniert das Modul vorhandene ESI-Daten mit lokalen Eingaben und kennzeichnet Quelle, Abrufzeit und Vollständigkeit.

### Version 1.3 – Advanced Industry

- Invention
- T2 Manufacturing
- Reactions
- Copy-, ME- und TE-Research
- Decryptors und Erfolgswahrscheinlichkeiten
- komplexe Capital-Ketten

### Version 1.4 – Corporation

- Corporation Assets, Blueprints und Industry Jobs
- rollenbasierte Sichtbarkeit
- gemeinsame Projekte
- Aufgabenverteilung
- interne Preise und Abrechnungen
- eigene Customs Offices

### Version 1.5 – Optimierung

- automatische PI-Koloniekonzepte
- Szenarien nach Pflegeaufwand oder Profit
- Produktionsslot-Optimierung
- mehrere Standorte und Hubs
- Routen- und Transportvergleich
- Marktliquidität und erwartete Verkaufsdauer

### Spätere Client-Erweiterungen

- weitere Desktop-Betriebssysteme
- signierte Installer und komfortabler Updatekanal
- getrenntes öffentliches Release-Repository für Binärpakete, Prüfsummen und Changelog
- portable Datenexporte ohne Tokens
- zusätzliche Backupziele
- erneute CCP-Lizenz-, Branding- und Sicherheitsprüfung vor einer öffentlichen Release-Verteilung

---

## 15. Abgeschlossene Entscheidungen aus Phase 0

1. **Produktname:** EVE Dolphin
2. **Betrieb:** lokaler Python-Desktop-Client ohne Hoster oder zentrale Konten
3. **Markt:** Jita als erstes Profil; weitere Hubs und Marktseiten konfigurierbar
4. **Produktionsorte:** kein hartcodierter Primärort; versionierte Standort- und Strukturprofile
5. **Charaktere:** mehrere eigene Charaktere von Beginn an, ohne feste fachliche Obergrenze
6. **Wurmlochreferenz:** J151141 mit manuell bestätigtem POCO- und Logistikstatus
7. **Abnahmeszenarien:** Water, Robotics, Caracal, Nanite Repair Paste und J151141
8. **Optimierungsziel:** pro Projekt auswählbar; konservative Wirtschaftsbewertung als Standard
9. **Oberflächensprache:** Deutsch und Englisch in derselben Codebasis
10. **Weitere Nutzer:** Jeder installiert einen eigenen Client und verbindet nur seine eigenen Charaktere; Corporation-Funktionen folgen nach Version 1.0
11. **Produktdach:** EVE Dolphin bleibt der Name für Industrie, Mining und PVE; Version 1.0 bleibt auf PI und Manufacturing begrenzt
12. **Veröffentlichung:** eine gemeinsame private Codebasis, aber getrennte Pakete je Betriebssystem und später ein öffentliches Binär-Release-Repository

### Empfohlene Ausgangsentscheidungen

- lokaler Python-Desktop-Client mit SQLite und eigenständigem Windows-Paket
- mehrere eigene Charaktere von Beginn an
- Deutsch und Englisch in derselben Codebasis
- PI P0–P4 vollständig in v1.0
- T1 und Komponenten in v1.0; T2/Reactions in v1.3
- Jita als erster Markt, weitere Hubs konfigurierbar
- Wurmlochprofil mit manuellen POCO- und Logistikwerten
- Gewinnberechnung nach Wiederbeschaffungskosten als Standard, weitere Bewertungen auswählbar

---

## 16. Startpaket

Das Startpaket aus Phase 0 wurde am 30.08.2026 abgenommen:

1. [x] Produktname und Kurzbeschreibung
2. [x] fünf konkrete Nutzerabläufe
3. [x] erste Seitenstruktur und Wireframes
4. [x] Datenquellen- und Scope-Matrix
5. [x] verbindlicher Formel- und Rundungskatalog
6. [x] Architekturentscheidung
7. [x] initialer Issue- und Meilensteinplan für das Repository

Die technische Implementierung beginnt mit Phase 1 auf diesem versionierten Stand.

---

## 17. Offizielle Referenzen

- EVE Developer Documentation: https://developers.eveonline.com/
- EVE Single Sign-On: https://developers.eveonline.com/docs/services/sso/
- EVE Community Resources und SDE-Verweise: https://developers.eveonline.com/docs/community/
- CCP Third Party Policies: https://support.eveonline.com/hc/en-us/articles/8564030965660-Third-Party-Policies
- CCP EULA und Policies: https://support.eveonline.com/hc/en-us/sections/8413327523612-EULA-ToS-Policies

---

## 18. Erfolgsdefinition

Version 1.0 ist erfolgreich, wenn der Nutzer mit seinen realen Charakteren und Kolonien ein kombiniertes PI-/Manufacturing-Projekt planen, die fehlenden Materialien und Transporte erkennen, die Kosten nachvollziehen und nach Abschluss den tatsächlichen Nettogewinn mit der ursprünglichen Planung vergleichen kann.
