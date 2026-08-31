# Änderungsprotokoll

## Unveröffentlicht

- persönliche BPO-/BPC-Übersicht mit Produkt, Besitzer, Standort, ME, TE und Runs
- Manufacturing-Kalkulation für Zielmenge, Ausgabe, Überschuss, Materialien und Dauer
- getrennte Anzeige von Bestand am Blueprint-Ort und Gesamtbestand aller Charaktere
- sichtbare Blocker für fehlende BPC-Runs und lokale Materialfehlmengen

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
