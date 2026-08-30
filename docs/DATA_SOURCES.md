# ESI-/SDE-Daten- und Berechtigungsmatrix

## Grundsätze

- öffentliche ESI-Daten benötigen kein Charakter-Token
- private Daten werden nur mit ausdrücklicher Freigabe des betroffenen Charakters geladen
- die vier aktuellen Industrie-/PI-Scopes werden bei der Erstverbindung gemeinsam angefordert;
  spätere Modul-Scopes bleiben progressiv
- der lokale Client verwendet Authorization Code mit PKCE und speichert Refresh Tokens ausschließlich im Anmeldedatenspeicher des Betriebssystems
- Corporation-Scopes gehören nicht zum Mindestumfang von Version 1.0
- jede ESI-Anfrage verwendet ein geprüftes Kompatibilitätsdatum
- konkrete Routen und Scopes werden bei Implementierungsbeginn nochmals gegen den offiziellen API Explorer für dieses Datum geprüft

## Statische EVE-Daten

EVE Dolphin verwendet die neue offizielle Tranquility-SDE im JSON-Lines-Format.
Die jeweils aktuelle Buildnummer und das Veröffentlichungsdatum kommen aus
`https://developers.eveonline.com/static-data/tranquility/latest.jsonl`; daraus wird
die buildgebundene Archiv-URL gebildet. Für Version 1.0 werden Kategorien,
Marktgruppen, Gruppen, Typen einschließlich Volumen und Kapazität, Blueprints,
Planet-Schematics, Solarsysteme und Planeten importiert.

Der Stand vom 28.08.2026 wurde mit Build `3484357` geprüft. Der vollständige reale
Import umfasst 52.863 Typen, 5.082 Blueprints und 68 PI-Schematics. Da die offizielle
Quelle einzelne verwaiste Blueprint-Material-/Produkttypen enthalten kann, werden
diese Abweichungen als Datenqualitätswarnungen gespeichert und nicht verschwiegen.
Eine lokal berechnete SHA-256-Summe schützt das bereits heruntergeladene Archiv vor
Veränderung zwischen Download und Import.

## Private Charakterdaten für Version 1.0

| Funktion | ESI-Route | Scope | Verwendung |
|---|---|---|---|
| Assets | `GET /characters/{character_id}/assets` | `esi-assets.read_assets.v1` | Materialbestand und Standorte |
| Asset-Namen | `POST /characters/{character_id}/assets/names` | `esi-assets.read_assets.v1` | benannte Container |
| Asset-Positionen | `POST /characters/{character_id}/assets/locations` | `esi-assets.read_assets.v1` | spezielle Positionsdaten, nur bei Bedarf |
| Blueprints | `GET /characters/{character_id}/blueprints` | `esi-characters.read_blueprints.v1` | BPO/BPC, ME, TE und Runs |
| Industry Jobs | `GET /characters/{character_id}/industry/jobs` | `esi-industry.read_character_jobs.v1` | aktive und historische Jobs |
| Kolonien | `GET /characters/{character_id}/planets` | `esi-planets.manage_planets.v1` | Kolonieliste und Aktualisierungsstatus |
| Kolonie-Layout | `GET /characters/{character_id}/planets/{planet_id}` | `esi-planets.manage_planets.v1` | Pins, Links, Routen, Extractors und Inhalte |
| Skills | `GET /characters/{character_id}/skills` | `esi-skills.read_skills.v1` | Slot- und Zeitberechnungen, sofern benötigt |
| Wallet | `GET /characters/{character_id}/wallet` | `esi-wallet.read_character_wallet.v1` | Kapitalübersicht |
| Wallet-Transaktionen | `GET /characters/{character_id}/wallet/transactions` | `esi-wallet.read_character_wallet.v1` | tatsächliche Ein- und Verkaufspreise |
| Eigene Marktorders | `GET /characters/{character_id}/orders` | `esi-markets.read_character_orders.v1` | offene Verkäufe und Einkaufsvorhaben |

Wallet, Skills und eigene Marktorders werden erst angefordert, wenn die zugehörige Funktion aktiviert wird. PI-Nutzer müssen nicht automatisch Walletzugriff gewähren.

Assets und Blueprints sind gegen die offizielle OpenAPI-Spezifikation mit
Kompatibilitätsdatum `2026-08-30` implementiert. Beide Routen sind seitens ESI
seitennummeriert und besitzen aktuell eine Client-Cachezeit von 3.600 Sekunden.
Ein lokaler Industrie-Snapshot wird deshalb frühestens nach einer Stunde erneuert.
Die Blueprint-Menge unterscheidet BPO (`-1`), BPC (`-2`) und noch unveränderte
Blueprint-Stapel; `runs`, Materialeffizienz und Zeiteffizienz bleiben unverändert
als charakterbezogene Ist-Werte erhalten.

Die persönliche Jobroute ist mit `include_completed=true` angebunden. Laut aktuellem
Schema umfasst der abgeschlossene Anteil die vergangenen 90 Tage; EVE Dolphin
behandelt ihn deshalb nicht als unbegrenzte Historie. Die Route besitzt eine
Client-Cachezeit von 300 Sekunden. Installationskosten und Wahrscheinlichkeiten
werden als Dezimalwerte gespeichert, Jobstatus und Zeitangaben bleiben unveränderte
ESI-Ist-Daten.

Kolonieliste und Kolonie-Layout besitzen laut derselben OpenAPI-Spezifikation jeweils
eine Client-Cachezeit von 600 Sekunden. Ein Planetary-Snapshot wird erst aktiviert,
wenn jedes zugehörige Layout mit Pins, Links und Routen vollständig geprüft wurde.
ESI berechnet PI-Informationen erst neu, wenn die Kolonie im EVE-Client angesehen wird;
EVE Dolphin zeigt den von ESI gelieferten `last_update` deshalb als fachlichen Stand und
interpretiert den lokalen Abrufzeitpunkt nicht als garantierte Echtzeitberechnung.

## Private Charakterdaten für spätere Module

Diese Routen und Scopes gehören ausdrücklich nicht zum Mindestumfang von Version 1.0. Sie werden erst mit dem jeweiligen Modul angeboten und progressiv freigegeben.

| Modul | Funktion | ESI-Route | Scope | Verwendung und Grenze |
|---|---|---|---|---|
| Mining | persönliches Mining-Ledger | `GET /characters/{character_id}/mining` | `esi-industry.read_character_mining.v1` | abgebaute Typen, Mengen, Systeme und Zeitpunkte der vergangenen 30 Tage |
| PVE | NPC-Standing | `GET /characters/{character_id}/standings` | `esi-characters.read_standings.v1` | Standing zu Agenten, NPC-Corporations und Fraktionen |
| PVE | Wallet-Journal | `GET /characters/{character_id}/wallet/journal` | `esi-wallet.read_character_wallet.v1` | ausgewählte Belohnungen, Bounties, Steuern und Kosten im verfügbaren Zeitraum |
| PVE | jüngste Killmails | `GET /characters/{character_id}/killmails/recent` | `esi-killmails.read_killmails.v1` | Verluste und Kampfereignisse, nicht vollständige Missionsziele |
| PVE | aktueller Standort | `GET /characters/{character_id}/location` | `esi-location.read_location.v1` | optionaler Charakterstandort bei ausdrücklicher Freigabe |

Das aktuelle ESI-Schema besitzt keinen allgemeinen privaten Endpunkt für ein vollständiges Journal aller aktiven klassischen Missionen, ihrer Ziele und ihres Fortschritts. `GET /characters/{character_id}/agents_research` betrifft ausschließlich Forschungsagenten und wird nicht als Missionsjournal fehlinterpretiert. Das spätere PVE-Modul kombiniert deshalb ESI-Signale mit einem lokalen Missionsjournal; Quelle und Vollständigkeit bleiben sichtbar.

## Öffentliche ESI-Daten

| Daten | ESI-Route | Verwendung |
|---|---|---|
| Typdetails | `GET /universe/types/{type_id}` | Name, Gruppe, Volumen und Eigenschaften |
| Systeme | `GET /universe/systems/{system_id}` | Produktions- und Koloniestandorte |
| Planeten | `GET /universe/planets/{planet_id}` | Planet und Systemzuordnung |
| PI-Schematics | `GET /universe/schematics/{schematic_id}` | öffentlicher Name/Zyklus als Fallback; vollständige Rezepte primär aus der SDE |
| Marktpreise | `GET /markets/prices` | Average und Adjusted Price |
| Regionale Orders | `GET /markets/{region_id}/orders` | echte Buy-/Sell-Tiefe |
| Markthistorie | `GET /markets/{region_id}/history` | Volumen und historische Preise |
| Industry Systems | `GET /industry/systems` | System Cost Indices |
| Industry Facilities | `GET /industry/facilities` | öffentliche Anlagenreferenzen |
| NPC-Station | `GET /universe/stations/{station_id}` | Stationsdetails |

Zugriff auf nicht öffentliche Spielerstrukturen wird erst ergänzt, wenn ein konkreter v1.0-Anwendungsfall ihn benötigt. Individuelle Struktursteuern und Boni bleiben zunächst manuelle Standortprofile.

## Für spätere Corporation-Funktionen

| Funktion | Erwarteter Scope |
|---|---|
| Corporation Assets | `esi-assets.read_corporation_assets.v1` |
| Corporation Blueprints | `esi-corporations.read_blueprints.v1` |
| Corporation Industry Jobs | `esi-industry.read_corporation_jobs.v1` |
| Corporation Marktorders | `esi-markets.read_corporation_orders.v1` |
| Corporation Wallet | `esi-wallet.read_corporation_wallets.v1` |
| Eigene Customs Offices | `esi-planets.read_customs_offices.v1` |

Diese Scopes allein reichen nicht aus: ESI prüft zusätzlich Corporation-Rollen. Das Tool muss fehlende Rollen als erwarteten Berechtigungszustand behandeln und darf deshalb keine endlosen Retries erzeugen.

## SDE-Daten für Version 1.0

Die offizielle SDE-JSON-Lines-Variante ist die primäre statische Quelle.

| Datengruppe | Verwendung |
|---|---|
| Typen und Übersetzungen | Gegenstandssuche, Namen, Volumen und Gruppen |
| Blueprints | Aktivitäten, Materialien, Produkte, Zeiten und Runs |
| PI-Schematics | P0–P4-Eingänge, Ausgänge und Zykluszeiten |
| Kategorien und Gruppen | Filterung und Navigation |
| Market Groups | Marktstruktur und Produktauswahl |
| Systeme und Planeten | lokalisierte Kolonieorte, Sicherheitsstatus und Wurmlochprofile |
| Dogma/Attribute | ausgewählte produktionstechnische Werte, sofern erforderlich |

Der Import speichert Buildnummer, Abrufzeit, Schemaänderungsstand und Aktivierungszeit. SDE-Updates werden über offizielle Build- und Änderungsmetadaten erkannt.

## Manuelle und berechnete Daten

| Wert | Grund für manuelle Pflege |
|---|---|
| fremde POCO-Steuer | nicht allgemein vollständig über ESI verfügbar |
| Struktursteuer | abhängig vom Betreiber und Zugriff |
| Struktur-/Rig-Bonus | kann sich nach Standort und Konfiguration unterscheiden |
| Transportkosten | persönliches Schiff, Zeit- und Risikomodell |
| Wurmloch-Risikoaufschlag | subjektive beziehungsweise betriebliche Annahme |
| interne Materialpreise | private oder Corporation-Vereinbarung |

Jeder manuelle Wert erhält lokale Herkunft, Quelle, Gültigkeitsbeginn und Änderungszeitpunkt.

## Synchronisationsklassen

| Klasse | Beispiele | Strategie |
|---|---|---|
| SDE | Blueprints, Typen, Schematics | buildbasiert, atomarer Import |
| langsam veränderlich | Charakterprofil, Strukturen | ESI-Cache respektieren |
| betrieblicher Zustand | Assets, Jobs, Kolonien | nach `Expires`, manuell anstoßbar ohne Cacheumgehung |
| Markt | Orders und Preise | nach ESI-Cache, pro Region/Typ gebündelt |
| Prognose | PI-Lager und Produktion | aus letztem Snapshot berechnet und als Schätzung markiert |
| spätere Aktivitätsmodule | Mining, Wallet, Standing, Killmails | modulbezogen, nach ESI-Cache und lokal historisiert |

## Fehler- und Datenqualitätsregeln

- `304 Not Modified` aktualisiert den Prüfzeitpunkt, erzeugt aber keinen neuen fachlichen Snapshot.
- unvollständig geladene Seiten werden niemals als vollständiger Bestand aktiviert.
- fehlender Scope wird als „nicht freigegeben“ angezeigt, nicht als technischer Fehler.
- widerrufenes Token trennt nur den betroffenen Charakter.
- Daten zeigen Abrufzeit, fachlichen Stand und Quelle.
- Prognosen zeigen zusätzlich ihren Unsicherheitsstatus.
- Marktberechnungen speichern Region, Station/Strukturfilter, Marktseite und ausgewertete Menge.

## Offizielle Referenzen

- [EVE SSO](https://developers.eveonline.com/docs/services/sso/)
- [ESI-Übersicht und Kompatibilitätsdatum](https://developers.eveonline.com/docs/services/esi/overview/)
- [ESI Best Practices](https://developers.eveonline.com/docs/services/esi/best-practices/)
- [EVE Static Data](https://developers.eveonline.com/docs/services/static-data/)
- [Developer License Agreement](https://developers.eveonline.com/license-agreement)
