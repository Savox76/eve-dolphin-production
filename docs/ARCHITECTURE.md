# Technische Architektur

## Status

Diese Architektur ist die verbindliche Ausgangsbasis für Version 1.0. Framework- und Paketversionen werden bei Beginn von Phase 1 anhand der dann unterstützten Releases festgeschrieben und durch Lockfiles reproduzierbar gehalten.

## Ziele

- privat online erreichbar
- sicherer Betrieb mit mehreren getrennten Nutzern
- responsive Web-Oberfläche und PWA-Vorbereitung
- langlebige ESI- und SDE-Hintergrundarbeiten außerhalb von Web-Anfragen
- geringe laufende Kosten und wenige Infrastrukturkomponenten
- lokal und auf einem Server identische Docker-basierte Umgebung
- gemeinsam testbare Berechnungslogik für PI und Manufacturing

## Systemübersicht

| Komponente | Verantwortung |
|---|---|
| Web | Oberfläche, serverseitiges Rendering, PWA, Session-Nutzung |
| API | Autorisierung, Projekte, Bestände, Berechnungen und Benutzeraktionen |
| Worker | ESI-Synchronisation, SDE-Import, Marktpreise, Prognosen und Warnungen |
| PostgreSQL | Anwendungsdaten, Snapshots, Warteschlange und Synchronisationsstatus |
| Reverse Proxy | HTTPS, Routing, sichere Header und Request-Limits |

Version 1.0 benötigt weder Redis noch einen externen Queue-, Such- oder Objektspeicherdienst.

## Repository-Struktur

```text
apps/
  web/                 Browser-Oberfläche und PWA
  api/                 HTTP-API und Sitzungsprüfung
  worker/              geplante und asynchrone Aufgaben
packages/
  domain/              PI-, Blueprint-, Bestands- und Gewinnlogik
  database/            Schema, Migrationen und Repositories
  esi/                 ESI-Client, Cache und Datenadapter
  sde/                 SDE-Download, Prüfung und Import
  contracts/           API-Verträge und gemeinsame Datentypen
  config/              validierte Konfiguration
  i18n/                deutsche und englische Texte
docs/                   Produkt-, Architektur- und Fachdokumentation
```

Ein TypeScript-Monorepo stellt sicher, dass Web, API und Worker dieselben validierten Verträge und Domänentypen verwenden.

## Anwendungsgrenzen

### Web

- zeigt Daten und Prognosen an
- besitzt keine EVE Client Secrets
- führt keine direkten ESI-Aufrufe mit Refresh Tokens aus
- kommuniziert ausschließlich mit der eigenen API
- kennzeichnet aktuelle, veraltete, geschätzte und manuelle Werte

### API

- authentifiziert Nutzer und prüft jede Objektberechtigung
- bietet kleine, versionierte Endpunkte
- validiert alle Eingaben an der Systemgrenze
- startet langlebige Aufgaben nur über die Warteschlange
- speichert Kalkulationssnapshots für reproduzierbare Ergebnisse

### Worker

- erneuert EVE Access Tokens serverseitig
- verarbeitet ESI-Seiten konsistent
- respektiert Cache- und Fehlerlimit-Header
- importiert SDE-Daten in eine Staging-Version
- berechnet PI-Prognosen und Markt-Snapshots
- arbeitet wiederholbar; ein Retry darf Daten nicht doppelt erzeugen

## Authentifizierung und Nutzertrennung

### Anmeldung

Die Anmeldung erfolgt über EVE SSO. Der erste freigegebene Charakter erstellt beziehungsweise findet den zugehörigen Anwendungsnutzer. Weitere eigene Charaktere werden aus einer bereits authentifizierten Sitzung verknüpft.

### Privater Zugang

- öffentliche Selbstregistrierung ist deaktiviert
- eine serverseitige Allowlist entscheidet, welche Charaktere erstmals einen Nutzer anlegen dürfen
- ein Administrator kann später weitere Nutzer freigeben oder sperren
- das Trennen eines Charakters widerruft seine lokale Tokenverwendung und löscht beziehungsweise archiviert seine privaten Daten nach festgelegter Regel

### Mandantentrennung

- private Tabellen tragen eine nicht-nullbare `user_id`
- zusammengesetzte Fremdschlüssel verhindern Verknüpfungen zwischen Nutzern
- Repository-/Service-Funktionen verlangen immer einen Nutzerkontext
- Hintergrundjobs speichern `user_id` und `character_id` explizit
- Tests versuchen gezielt, Daten eines anderen Nutzers zu lesen oder zu verändern
- Corporation-Daten erhalten später einen getrennten Zugriffsbereich mit Rollen

## Token- und Secret-Sicherheit

- EVE Client Secret, Datenbankschlüssel und Verschlüsselungsschlüssel nur als Server-Secrets
- Refresh Tokens verschlüsselt mit authentifizierter Verschlüsselung
- pro Token eigener Nonce/IV und gespeicherte Schlüsselversion
- Access Tokens nur kurzzeitig im Arbeitsspeicher beziehungsweise verschlüsselten Cache
- keine Tokens in URLs, Browser-Storage, Logs oder Fehlermeldungen
- JWT-Signatur, Aussteller, Zielgruppe, Ablauf und freigegebene Scopes werden geprüft
- `state` schützt den OAuth-Callback gegen CSRF
- Schlüsselrotation ist im Datenmodell vorgesehen

## PostgreSQL und Hintergrundaufgaben

PostgreSQL ist in Version 1.0 zugleich:

- relationale Anwendungsdatenbank
- Speicher für versionierte ESI-/Markt-/Kalkulationssnapshots
- Job-Warteschlange für Worker-Aufgaben
- Synchronisations- und Fehlerhistorie

Eine PostgreSQL-basierte Warteschlange vermeidet einen zusätzlichen Redis-Dienst. Erst gemessene Last oder Funktionsgrenzen rechtfertigen später eine weitere Infrastrukturkomponente.

## ESI-Client

Jede Anfrage verwendet:

- zentral festgelegtes `X-Compatibility-Date`
- eindeutigen User-Agent mit Anwendungsversion und Kontaktmöglichkeit
- Timeout und begrenzte Retry-Regeln
- `ETag`/`If-None-Match`, `Expires` und `Last-Modified`
- Auswertung von ESI-Fehlerlimit- und Bucket-Headern
- exponentielles Backoff mit Zufallsanteil bei geeigneten temporären Fehlern
- kein Retry bei fehlender Berechtigung oder fachlich ungültigen Anfragen

Paginated Resources werden als konsistenter Abruf behandelt. Wenn sich relevante Cache-/Änderungsheader zwischen Seiten widersprechen, wird der Snapshot verworfen und später neu geladen.

## SDE-Import

1. Aktuelle Build-Metadaten mit HTTP-Caching prüfen.
2. JSON-Lines-Archiv nur bei neuer Version herunterladen.
3. Prüfsumme, Dateistruktur und erwartete Kerndatensätze validieren.
4. Daten in versionierte Staging-Tabellen importieren.
5. Referenzen, Mengen und Pflichtfelder prüfen.
6. Golden Tests gegen bekannte Blueprints und Schematics ausführen.
7. Neue SDE-Version atomar aktivieren.
8. Vorherige Version für einen begrenzten Rollback-Zeitraum behalten.

Ein fehlgeschlagener Import verändert niemals die aktive SDE-Version.

## Daten- und Rechenmodell

### Statische Daten

- Typen und Übersetzungen
- Blueprints, Aktivitäten, Materialien, Produkte und Zeiten
- PI-Schematics
- Systeme, Planeten, Stationen und weitere Universumsdaten

### Dynamische Daten

- Charaktere und erteilte Scopes
- Assets, Blueprints und Industry Jobs
- Kolonie-Snapshots mit Pins, Links und Routen
- Marktorder-, Preis- und Systemkosten-Snapshots
- manuelle Standort-, POCO- und Logistikprofile

### Kalkulationssnapshots

Ein gespeicherter Produktionsplan verweist nicht nur auf „den aktuellen Preis“, sondern hält verwendete Mengen, Preise, Gebühren, SDE-Version, ESI-Datenalter und manuelle Eingaben fest. Dadurch bleiben spätere Soll-/Ist-Vergleiche nachvollziehbar.

## Bereitstellung

Die Zielumgebung wird mit Docker Compose betrieben:

- Web-Container
- API-Container
- Worker-Container
- PostgreSQL-Container beziehungsweise verwaltete PostgreSQL-Instanz
- Reverse Proxy mit automatischem HTTPS

Entwicklung und Produktion verwenden dieselben Containerdefinitionen mit getrennten Konfigurationen. Produktions-Secrets werden nicht in Compose-Dateien oder das Repository geschrieben.

## Backup und Wiederherstellung

- tägliches verschlüsseltes PostgreSQL-Backup
- Aufbewahrungsregeln nach Generationen
- Backup außerhalb der laufenden Datenbankinstanz
- regelmäßiger automatisierter Integritätstest
- dokumentierter Wiederherstellungstest vor Version 1.0
- SDE-Daten müssen nicht vollständig gesichert werden, wenn sie reproduzierbar neu importierbar sind

## Architekturregeln

1. Domänenlogik kennt weder HTTP noch konkrete Datenbanktabellen.
2. ESI- und SDE-Payloads werden an Adaptern in interne Typen übersetzt.
3. Geldbeträge verwenden eine dezimal sichere Darstellung, keine unkontrollierten Fließkommazahlen.
4. Zeitpunkte werden intern in UTC gespeichert und in der Oberfläche lokal dargestellt.
5. Berechnungen erhalten explizite Einheiten.
6. Manuelle, geschätzte und automatisch geladene Werte tragen Herkunft und Zeitstempel.
7. Fehler in einem Charakter dürfen die Synchronisation anderer Charaktere nicht blockieren.

## Offene Detailentscheidungen für Phase 1

- konkrete Framework- und Paketversionen
- konkreter PostgreSQL-Queue-Adapter
- Hostinganbieter und Domain
- Backupziel
- genaue Sitzungsbibliothek

Diese Punkte verändern die beschlossene Systemarchitektur nicht und werden erst bei der technischen Initialisierung festgelegt.
