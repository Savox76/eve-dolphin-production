# Verbindliche Referenzabläufe

## Zweck

Diese fünf Abläufe bilden die fachliche Grundlage für Datenmodell, Oberfläche, Golden Tests und die spätere Abnahme von Version 1.0. Sie wurden nach Funktionsabdeckung ausgewählt, weil zunächst kein einzelnes Produkt bevorzugt wird.

Die Beispiele sind keine hart codierten Sonderfälle. Gegenstands-IDs, Rezepte, Mengen je Zyklus und Blueprint-Materialien werden bei der Implementierung aus der jeweils aktiven SDE-Version geladen.

## Gemeinsame Testidentitäten und Profile

Bis reale Charaktere über EVE SSO verbunden werden, verwenden Tests ausschließlich diese anonymen Bezeichnungen:

- `Main-Char`: Manufacturing, Markt und Projektsteuerung
- `PI-Alt-A`: Extraktion und P1/P2
- `PI-Alt-B`: Factory-Planeten und P3
- `Jita-Profile`: Referenzmarkt mit klar ausgewiesener Buy-/Sell-Seite
- `Industry-Structure-A`: manuelles Produktionsprofil mit Steuer und Boni
- `J151141-Profile`: Wurmlochprofil mit manuellem POCO-/Logistikstatus

Reale Charakternamen, Tokens oder private Bestände gehören nicht in Test-Fixtures oder Issues.

---

## RF-01 – P0 zu P1: Water aus Aqueous Liquids

### Ziel

Eine einfache Extraktionskolonie überwachen, die Aqueous Liquids gewinnt und zu Water verarbeitet. Der Ablauf prüft die kleinste vollständige PI-Kette ohne Manufacturing.

### Akteur und Ausgangslage

- Charakter: `PI-Alt-A`
- ein geeigneter Planet mit Extraktor, Lager/Launchpad und Basic Industry Facilities
- Extractor-Programm läuft über einen beispielhaften Tageszeitraum
- Planet und Layout werden über ESI geladen
- Schematic- und Typdaten stammen aus SDE/öffentlichem ESI

### Ablauf

1. Nutzer verbindet `PI-Alt-A` mit PI-Berechtigung.
2. Tool lädt Kolonieliste und das Planet-Layout.
3. Pins, Links, Routen und Lagerinhalte werden aufgelöst.
4. Tool erkennt Extractor-Programm, Zykluszeit und erwartetes Ende.
5. Aqueous Liquids werden der Water-Schematic zugeordnet.
6. Tool prognostiziert P0-Eingang, mögliche P1-Ausgabe und Pufferentwicklung.
7. Dashboard zeigt nächste sinnvolle Aufmerksamkeit und Datenalter.

### Erwartete Ergebnisse

- Planet, Charakter, Extractor und Fabriken werden korrekt angezeigt.
- Restlaufzeit basiert auf ESI-Zeitpunkten und wird lokal dargestellt.
- tatsächliche ESI-Daten und Prognose sind optisch getrennt.
- eine fehlende Route oder unterversorgte Fabrik erzeugt eine verständliche Warnung.
- Produktionsprognose endet beziehungsweise wird unsicher, wenn der Extractor ausläuft.

### Grenzfälle

- ESI-Snapshot ist älter als die Extractor-Laufzeit.
- Launchpad ist voraussichtlich voll.
- Extraktor liefert weniger als die Fabriken verbrauchen könnten.
- Route ist vorhanden, Ziel-Pin aber nicht mehr auflösbar.

### Abnahmekriterien

- [ ] Koloniestruktur stimmt mit einer kontrollierten EVE-Kolonie überein.
- [ ] Extractor-Ende und Fabrikzyklen stimmen innerhalb definierter Prognosetoleranz.
- [ ] veraltete Daten werden niemals als live dargestellt.
- [ ] Water-Menge wird ausschließlich aus aktiver Schematic und Snapshot berechnet.

---

## RF-02 – P3-Zielplanung: 5.000 Robotics in 30 Tagen

### Ziel

Eine mehrstufige PI-Produktion rückwärts planen. Ziel sind 5.000 Robotics innerhalb von 30 Tagen. Der Ablauf prüft P2-Vorprodukte, Factory-Kapazität, mehrere Charaktere und Import-/Exportlogistik.

### Akteur und Ausgangslage

- `PI-Alt-A` erzeugt oder sammelt einen Teil der Vorprodukte.
- `PI-Alt-B` betreibt einen Factory-Planeten für Robotics.
- vorhandene PI-Bestände können teilweise auf verschiedenen Planeten liegen.
- POCO-Steuern werden je Planet als Profil gepflegt.

### Ablauf

1. Nutzer wählt Robotics, Zielmenge 5.000 und Zeitraum 30 Tage.
2. Tool löst die aktive Robotics-Schematic rückwärts bis zu den benötigten Vorstufen auf.
3. Vorhandene Bestände und prognostizierte Erzeugung werden abgezogen.
4. Erforderliche Fabrikzyklen und durchschnittliche Tagesleistung werden berechnet.
5. Kapazität der vorhandenen Factory-Planeten wird mit dem Ziel verglichen.
6. Import, Export, POCO-Steuern und Frachtraum werden je Planet berechnet.
7. Fehlmengen erhalten die Optionen PI-Erzeugung oder Markteinkauf.

### Erwartete Ergebnisse

- der komplette P0–P3-Abhängigkeitsbaum ist sichtbar.
- benötigte Vorprodukte stammen aus der Schematic, nicht aus festem Anwendungscode.
- bereits vorhandene und künftig erwartete Mengen werden getrennt ausgewiesen.
- der Plan zeigt früh, wenn 5.000 Robotics mit vorhandener Kapazität nicht erreichbar sind.
- jede POCO-Buchung ist einem Import oder Export und einem Planeten zugeordnet.

### Grenzfälle

- Vorprodukt liegt auf dem falschen Planeten.
- ein Extractor endet deutlich vor Ablauf der 30 Tage.
- POCO-Steuer fehlt oder wurde geändert.
- nur ein Teil der Zielmenge ist innerhalb des Zeitraums erreichbar.
- Nutzer überschreibt „selbst erzeugen“ für ein Vorprodukt mit „kaufen“.

### Abnahmekriterien

- [ ] Rückwärtsrechnung ist mengen- und einheitentreu.
- [ ] Factory-Kapazität und Zeitraum begrenzen das Ergebnis korrekt.
- [ ] Teilmengen aus Bestand, Prognose und Kauf ergeben exakt den Bedarf.
- [ ] Steuer- und Transportkosten sind bis zum einzelnen Planeten erklärbar.

---

## RF-03 – T1-Manufacturing: zehn Caracals

### Ziel

Ein klassisches T1-Produktionsprojekt ohne PI-Abhängigkeit planen. Der Ablauf prüft Blueprint-Instanz, ME/TE, Assets, Industry Job Cost, Einkaufsliste und Gewinn.

### Akteur und Ausgangslage

- Charakter: `Main-Char`
- Ziel: zehn Caracals
- persönlicher Blueprint beziehungsweise BPC wird über ESI geladen
- ME, TE und verfügbare Runs stammen aus der Blueprint-Instanz
- Materialien liegen teilweise an mehreren Orten
- Produktionsort: `Industry-Structure-A`
- Marktprofil: `Jita-Profile`

### Ablauf

1. Nutzer erstellt ein Projekt für zehn Caracals.
2. Tool wählt einen geeigneten vorhandenen Blueprint oder zeigt fehlende Runs.
3. SDE-Materialien werden mit ME- und Rundungsregeln berechnet.
4. frei verfügbare Assets am gewählten Standort werden abgezogen.
5. Bestand an anderen Orten wird als Transportoption, nicht automatisch als lokal verfügbar behandelt.
6. System Cost Index, Adjusted Price und Standortprofil ergeben die Jobkosten.
7. fehlende Materialien werden mengenabhängig über Jita Sell Orders bewertet.
8. geplanter Verkauf wird nach gewählter Marktseite und Gebühren kalkuliert.

### Erwartete Ergebnisse

- Blueprint-Runs, ME und TE wirken nachvollziehbar auf Menge und Zeit.
- für andere Projekte reservierte Assets werden nicht doppelt verwendet.
- Einkaufsliste enthält nur lokale Fehlmengen.
- Job-, Material-, Markt- und Transportkosten werden getrennt dargestellt.
- Ergebnis zeigt Nettogewinn, Marge, ISK pro Produktionsstunde und Kapitalbindung.

### Grenzfälle

- BPC besitzt weniger Runs als benötigt.
- Mineralien sind auf mehrere Stationen verteilt.
- Markttiefe reicht nicht zum besten sichtbaren Preis für die gesamte Menge.
- Verkaufspreis fällt unter die Gesamtkosten.
- SDE-Version ändert das Blueprint-Rezept zwischen Planung und späterer Neuberechnung.

### Abnahmekriterien

- [ ] Materialmenge stimmt mit einem kontrollierten In-Game-Job überein.
- [ ] andere Standorte und Reservierungen werden nicht als frei lokal verrechnet.
- [ ] Marktpreis berücksichtigt die benötigte Menge und gewählte Marktseite.
- [ ] gespeicherter Kalkulationssnapshot bleibt nach Preis-/SDE-Update reproduzierbar.

---

## RF-04 – Verbundprojekt: Nanite Repair Paste

### Ziel

Ein Manufacturing-Projekt planen, dessen Materialkette PI-Produkte enthält. Der Ablauf prüft die gemeinsame PI-/Blueprint-Engine und Build-or-Buy-Entscheidungen.

### Akteur und Ausgangslage

- Projektsteuerung: `Main-Char`
- PI-Zulieferung: `PI-Alt-A` und `PI-Alt-B`
- Zielmenge: 10.000 Einheiten Nanite Repair Paste
- Blueprint-Rezept und Produktionsmenge stammen aus der aktiven SDE-Version
- einige PI-Materialien sind vorhanden, weitere werden prognostiziert oder fehlen

### Ablauf

1. Nutzer erstellt ein Manufacturing-Projekt für die Zielmenge.
2. Blueprint-Engine berechnet Runs, Materialien und Produktionszeit.
3. Gegenstandskatalog erkennt Materialien, die aus PI stammen.
4. PI-Engine löst diese Materialien bis zu den gewählten Produktionsstufen auf.
5. Tool vergleicht je PI-Komponente Eigenproduktion, vorhandenen Bestand und Marktkauf.
6. Nutzer kann automatische Build-or-Buy-Empfehlungen überschreiben.
7. Zeitplan ordnet PI-Produktion, Hauling, Materialbereitstellung und Manufacturing-Job.
8. Gesamtkalkulation verbindet POCO-, Transport-, Job- und Marktgebühren.

### Erwartete Ergebnisse

- nur ein gemeinsamer Abhängigkeitsgraph; keine doppelte Materialzählung zwischen PI und Manufacturing.
- jede Komponente besitzt genau einen beschlossenen Bezugsweg.
- PI-Produkte werden erst zum verfügbaren Zeitpunkt für den Manufacturing-Job eingeplant.
- der Endgewinn verwendet Opportunitätskosten für bereits vorhandene PI-Materialien.
- Nutzer sieht den Unterschied zwischen niedrigsten Kosten und schnellster Fertigstellung.

### Grenzfälle

- PI-Prognose deckt nur einen Teilbedarf.
- Einkauf ist günstiger, blockiert aber keine eigenen Planeten.
- Eigenproduktion ist günstiger, verfehlt jedoch den Fertigstellungstermin.
- dieselbe PI-Menge wird bereits von einem anderen Projekt reserviert.
- Nutzer ändert den Bezugsweg einer Vorstufe mitten in der Planung.

### Abnahmekriterien

- [ ] Materialgraph ist vollständig und frei von Doppelzählungen.
- [ ] Bestand, Prognose, Eigenbau und Kauf summieren sich exakt zur Zielmenge.
- [ ] Zeitabhängigkeiten verhindern einen zu frühen Manufacturing-Start.
- [ ] Build-or-Buy-Empfehlung zeigt Kosten- und Zeitbegründung.

---

## RF-05 – Wurmloch-Sonderfall: J151141 ohne Customs Office

### Ziel

Ein PI-Vorhaben in einem C1-Wurmloch planen, in dem für einen oder mehrere Planeten kein Customs Office bestätigt ist. Dieser Ablauf prüft fehlende Infrastruktur, manuelle Wurmlochdaten und verhindert unrealistische Produktionspläne.

### Akteur und Ausgangslage

- Systemprofil: `J151141-Profile`
- Wurmlochklasse und Planetendaten stammen aus verfügbaren Universums-/SDE-Daten.
- POCO-/Customs-Office-Status wird manuell bestätigt, weil beliebige fremde POCO-Daten nicht vollständig automatisch verfügbar sind.
- Referenzziel: Robotics-Versorgung für ein späteres Manufacturing-Projekt.
- Marktvergleich und Ausfuhrziel: `Jita-Profile`

### Ablauf

1. Nutzer wählt J151141 und erfasst je Planet den bestätigten Customs-Office-Status.
2. Tool zeigt verfügbare Planetentypen und theoretisch mögliche PI-Ketten.
3. Ein Robotics-Plan wird mit vorhandenen beziehungsweise geplanten Kolonien erstellt.
4. Planeten ohne Customs Office dürfen keine normalen Import-/Exportvorgänge erhalten.
5. Nicht ausführbare Materialwege werden als Blocker statt als Kostenwert dargestellt.
6. Optionales Zukunftsszenario darf einen geplanten POCO mit angenommener Steuer verwenden, muss aber deutlich als nicht aktuell ausführbar markiert sein.
7. Für ausführbare Varianten werden Frachtraum, Wurmlochlogistik und Risikoaufschlag kalkuliert.

### Erwartete Ergebnisse

- „kein Customs Office“ ist ein fachlicher Infrastrukturstatus, kein technischer Fehler.
- theoretische Planeteneignung und aktuell ausführbare Logistik bleiben getrennt.
- blockierte PI-Mengen werden nicht als verfügbarer Manufacturing-Bestand gezählt.
- ein Zukunftsszenario verändert den Ist-Zustand nicht.
- Herkunft und Änderungszeitpunkt manueller POCO-Daten sind sichtbar.

### Grenzfälle

- Status eines Planeten ist unbekannt statt ausdrücklich „nicht vorhanden“.
- POCO wird später errichtet oder zerstört.
- Wurmlochroute nach Highsec ist nicht dauerhaft planbar.
- Material befindet sich auf einem Planeten, kann aber nicht exportiert werden.
- Risikoaufschlag wird verändert und beeinflusst Build-or-Buy.

### Abnahmekriterien

- [ ] fehlendes und unbekanntes Customs Office werden unterschieden.
- [ ] blockierte Waren fließen nicht in verfügbare Projektmengen ein.
- [ ] Zukunftsszenario ist klar als Annahme gekennzeichnet.
- [ ] Logistikkosten speichern Volumen, Annahme und Zeitpunkt.

---

## Abdeckungsmatrix

| Fähigkeit | RF-01 | RF-02 | RF-03 | RF-04 | RF-05 |
|---|:---:|:---:|:---:|:---:|:---:|
| EVE SSO/mehrere Charaktere | ✓ | ✓ | ✓ | ✓ | ✓ |
| Kolonie-Layout und Extractor-Timer | ✓ | ✓ |  | ✓ | ✓ |
| PI P0–P1 | ✓ | ✓ |  | ✓ | ✓ |
| PI P2–P3 |  | ✓ |  | ✓ | ✓ |
| Blueprint, ME/TE und Runs |  |  | ✓ | ✓ |  |
| Assets und Reservierungen |  | ✓ | ✓ | ✓ | ✓ |
| Manufacturing Job Cost |  |  | ✓ | ✓ |  |
| Build-or-Buy |  | ✓ | ✓ | ✓ | ✓ |
| Markt und Mengentiefe |  | ✓ | ✓ | ✓ | ✓ |
| POCO-Steuern |  | ✓ |  | ✓ | ✓ |
| Logistik/Frachtraum |  | ✓ | ✓ | ✓ | ✓ |
| fehlende Infrastruktur |  |  |  |  | ✓ |
| Soll-/Ist-Snapshot | ✓ | ✓ | ✓ | ✓ | ✓ |

## Versionsregel

Die Zielgegenstände bleiben feste Referenzen, die konkreten Rezepte jedoch nicht. Bei jedem unterstützten SDE-Update müssen Golden Tests prüfen, ob sich Materialien, Mengen, Zyklen oder Produkte der Referenzen geändert haben. Erwartungswerte werden dann bewusst aktualisiert und mit der SDE-Buildnummer dokumentiert.
