# Änderungsprotokoll

## Unveröffentlicht

## v0.4.6 – Verzweigte PI-Koloniegrafik

- Eingangs-Launchpads verbindlich auf ein bis fünf erweitert und alle gültigen
  Ziel-/Startstufen-Kombinationen für jede dieser Anzahlen geprüft
- bestehende gespeicherte Werte über fünf werden mit Datenbankschema 12 sicher auf fünf
  begrenzt
- Fabrikplanetengrafik beginnt bei jedem Eingangs-Launchpad samt gemischtem Inhalt und
  verbindet die Güter mit ihren tatsächlich abhängigen Fabriken bis zum Ziel-Launchpad
- Extraktorplanetengrafik beginnt je Rohstoff bei ECU und gewählter Kopfzahl und bildet
  anschließend dieselben realen Rezeptabhängigkeiten ab
- Grafik wird nicht mehr in die Fensterbreite skaliert; eine wachsende Zeichenfläche mit
  eigenen Scrollleisten hält alle Launchpads, Fabriken und Verbindungen lesbar

## v0.4.5 – Vollständige PI-Startbeladung

- alle Kombinationen aus P1- bis P4-Ziel, gültiger Zukaufstufe und einem bis fünf
  Eingangs-Launchpads automatisiert gegen Ein- und Ausgangsvolumen geprüft
- Startgüter werden über beliebig viele Eingangs-Launchpads verteilt; ein Launchpad kann
  mehrere unterschiedliche Güter aufnehmen
- neue übersichtliche Startbeladungstabelle je Launchpad mit Produkt, Stufe, Menge,
  Einzelvolumen und gesamter Launchpad-Belegung
- maximale Endmenge bleibt auf vollständige Chargen begrenzt und wird sowohl gegen alle
  Eingangskapazitäten als auch gegen das Ausgangs-Launchpad geprüft

## v0.4.4 – Scrollbarer PI-Zielplaner

- Zielplanung und Logistikprofile liegen in einer horizontal und vertikal scrollbaren
  Ansicht statt alle Inhalte in das normale Fenster zu pressen
- sinnvolle Mindestbreiten und -höhen für Planungs-, Aufbau- und Grafikbereiche
- Tabellen behalten lesbare Spaltenbreiten und besitzen bei Bedarf eigene Scrollleisten

## v0.4.3 – P4-Planetentypen und automatischer Updater-Neustart

- kompakte Planungs- und Aufbautabellen mit sieben beziehungsweise vier Spalten für die
  vollständige Darstellung bereits im normalen Anwendungsfenster
- einstellbare Zahl der Eingangs-Launchpads auf Fabrikplaneten
- automatische Startbeladung anhand der gewählten Zukaufstufe sowie daraus berechnete
  vollständige Produktionszyklen, Endmenge, Ausgangsvolumen und Laufzeit
- Ressourcenbudget berücksichtigt Eingangs- und Ausgangs-Launchpads getrennt
- Datenbankschema 11 für gespeicherte Eingangs-Launchpads
- P4-Produktionspläne weisen darauf hin, dass High-Tech-Fabriken nur auf kargen
  (Barren) oder gemäßigten (Temperate) Planeten errichtet werden können
- der Windows-Updater wartet auf das saubere Ende des Staging-Threads, beendet die laufende
  Anwendung selbstständig und startet die aktualisierte Version anschließend neu
- automatisierte Tests für die P4-Planeteneinschränkung und den Update-Shutdown

## v0.4.2 – PI-Ressourcenbudget und Zykluskorrektur

- maximale PI-Planbarkeit nach Command-Center-Upgrades-Stufe sowie CPU und Energie
- getrennte Gebäudezählung für Launchpads, Lager, ECUs, Extraktorköpfe und Fabriktypen
- einstellbare Infrastrukturreserve für entfernungsabhängige Links und Wege
- sichtbare maximale Zahl vollständiger Produktionsketten und Endfabriken
- klare Trennung zwischen Soll-Zyklen und nach vorhandenen Beständen noch nötigen Zyklen
- korrigierte Launchpad-Automatik: ausschließlich vollständige, garantiert passende Chargen
- gespeicherte Ressourcenparameter und Datenbankschema 10

## v0.4.1 – Automatische Launchpad-Zielplanung

- neue Berechnungsart „Launchpad automatisch füllen“ mit editierbarer Kapazität
- automatische Stückzahl aus SDE-Produktvolumen und freiem Launchpad-Volumen
- exakte Füllzeit aus SDE-Zykluszeit und gewählter Zahl der Endfabriken
- zeitlich ausbalancierte Empfehlungen für alle vorgelagerten Fabrikstufen
- kompakter grafischer Materialfluss von Extraktion oder Zukauf bis zum Launchpad
- gespeicherter Launchpad-Modus einschließlich Kapazität und Endfabrikzahl
- Datenbankschema 9 für die neuen Planungsparameter
- automatische Windows-Veröffentlichung nach erfolgreichem `main`-CI-Lauf und neuer Version

## v0.4.0 – PI-Betriebsplanung und Manufacturing-Grundlage

- persönliche BPO-/BPC-Übersicht mit Produkt, Besitzer, Standort, ME, TE und Runs
- Manufacturing-Kalkulation für Zielmenge, Ausgabe, Überschuss, Materialien und Dauer
- getrennte Anzeige von Bestand am Blueprint-Ort und Gesamtbestand aller Charaktere
- sichtbare Blocker für fehlende BPC-Runs und lokale Materialfehlmengen
- grafische Lager-/Launchpad-Übersicht mit Inhalt, Volumen und Füllstand
- sekündlicher Restlaufzeit-Countdown für Extraktoren und Zukauf-Fabrikplaneten
- rote Warnstufe bei weniger als zehn Stunden Extraktor- oder Materiallaufzeit
- PI-Zielplanung wahlweise aus Eigenextraktion oder Zukauf bis P3
- empfohlener Planetenaufbau mit direkten Routen oder Pufferlagern
- speicherbare, editierbare und löschbare PI-Planungen
- zentrale Anwendungsversion und Release-Sperre gegen gleiche oder ältere Versionsnummern
- Datenbankschema 8 für gespeicherte PI-Planungen

## v0.3.1 – Updater-Korrektur

- Windows-Installationsordner wird vor dem Austausch zuverlässig freigegeben
- sicherer Arbeitsordner für Updatehelfer und neu gestartete Anwendung
- sichtbarer Downloadfortschritt bei manuellen Updates
- persistente Erfolgs- und Fehlermeldung nach dem Neustart
- detaillierte Fehlerklassen für Download, Paketprüfung und Windows-Dateiaustausch

## v0.3.0 – Phase-3-Testversion

- vollständige charakterübergreifende PI-Kolonieübersicht mit Planet- und Systemnamen
- sichtbares Datenalter sowie Warnungen für abgelaufene Extractors, fehlende Versorgung und
  fast volle Lager
- 24-Stunden-Prognosen für P0-Ertrag, Fabrikausgabe und Lagerfüllstand
- vollständiger SDE-basierter P0–P4-Abhängigkeitsgraph und Rückwärtsplaner
- Vergleich des Zielbedarfs mit Beständen, Kolonieprognosen und vorhandener Fabrikkapazität
- editierbare POCO-, Transport-, Frachtraum-, Risiko- und Wurmlochprofile
- blockierte Importe bei fehlendem POCO sowie transparente Steuer- und Logistikkosten
- Datenbankschema 7 mit atomarer Erweiterung vorhandener SDE-Builds um Systeme, Planeten und
  Pin-Kapazitäten

## v0.2.0 – Automatische Datenpflege und Updater

- gemeinsame Industrie-/PI-Freigabe bei der ersten Charakterverbindung
- unmittelbare Synchronisation und Fünf-Minuten-Prüfung während der Laufzeit
- sichtbare Version und anonyme Updateprüfung gegen öffentliche GitHub Releases
- manueller, prüfsummenvalidierter Windows-Updater mit Selbsttest und Rollback

## v0.1.1 – SSO-Korrektur

- kompatibler PKCE-Tokenaustausch und robuste Identitätsprüfung nach der Charakterauswahl

## v0.1.0 – Erste Windows-Testversion

- lokaler Desktop-Client mit EVE SSO, SDE sowie Asset-, Blueprint-, Job- und PI-Synchronisation
