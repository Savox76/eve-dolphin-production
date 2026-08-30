# Phase 2 – EVE-Datenbasis (in Arbeit)

## Ziel

Phase 2 verbindet den lokalen Client sicher mit EVE Online und baut die belastbare Datenbasis für Planetare Industrie und Manufacturing. Der Meilenstein ist erst abgeschlossen, wenn SSO, mehrere Charaktere, Token-Erneuerung, SDE und die ersten ESI-Synchronisationen gemeinsam abgenommen sind.

## Erster Baustein: SSO- und Charakterkern

- [x] öffentliche Client-Konfiguration ohne Client Secret
- [x] Authorization Code mit 32-Byte-PKCE und `S256`
- [x] kryptografisch zufällige `state`-Korrelation
- [x] offizielle OAuth-Metadaten als Quelle der Endpunkte
- [x] auf `127.0.0.1` und `/callback` begrenzter Einmal-Callback
- [x] keine Callback-Query-Daten in Logs oder Browserantworten
- [x] PKCE-Code-Exchange mit öffentlicher Client ID
- [x] JWT-Prüfung von RSA-Signatur, Algorithmus, Schlüssel-ID, Issuer, Ablauf und Audience
- [x] validierte Ableitung von Charakter-ID, Name, Owner-Hash und Scopes
- [x] SQLite-Repository für mehrere lokale Charaktere
- [x] Refresh Tokens ausschließlich über die vorhandene OS-Keyring-Grenze
- [x] Wiederherstellung des vorherigen Tokens bei fehlgeschlagener Charakterpersistenz
- [x] Trennen eines Charakters löscht zuerst sein lokales Refresh Token
- [x] isolierte Tests ohne echte EVE-Zugangsdaten

## Zweiter Baustein: sichtbare Charakterverwaltung

- [x] echte Charakterseite statt Platzhalter unter „Einstellungen & Charaktere“
- [x] lokale Tabelle mit Charaktername, Anzahl freigegebener Scopes und Verknüpfungszeit
- [x] EVE-Anmeldung über den Systembrowser, ohne Passwortabfrage durch EVE Dolphin
- [x] Netzwerk, Callback, Tokenprüfung und Keyring-Zugriff außerhalb des UI-Threads
- [x] lokaler Callback ist bereits gebunden, bevor der Browser geöffnet wird
- [x] fehlende Client-ID, Browser-, Netzwerk-, Timeout-, Token- und Keyring-Fehler werden verständlich angezeigt
- [x] ausstehende Callback-Anmeldung wird beim Schließen der Anwendung beendet
- [x] Charaktere können erst nach ausdrücklicher Bestätigung getrennt werden
- [x] Übersichtsseite zeigt die tatsächliche Anzahl lokal verbundener Charaktere
- [x] Authorization-Code-Austausch sendet Client-ID, PKCE-Verifier und die registrierte Redirect-URL, aber kein Client Secret

## Dritter Baustein: Token-Erneuerung und Berechtigungspakete

- [x] Refresh-Anfragen verwenden den form-codierten PKCE-Public-Client-Flow ohne Client Secret
- [x] jedes von EVE zurückgegebene Refresh Token ersetzt vor weiteren Metadaten-Schreibvorgängen den vorherigen Wert
- [x] parallele Refresh-Versuche desselben Charakters werden innerhalb des gemeinsamen Dienstes serialisiert
- [x] `invalid_grant` entfernt das ungültige Token und stoppt weitere automatische Versuche
- [x] temporäre OAuth- und Rate-Limit-Fehler entfernen kein weiterhin nutzbares Refresh Token
- [x] erneuerte Access Tokens werden erneut kryptografisch validiert und dem gespeicherten Charakter zugeordnet
- [x] fehlende Tokens und Identitätsabweichungen verlangen eine erneute ausdrückliche Autorisierung
- [x] der lokale Anmeldestatus ist migriert, persistent und in der Charaktertabelle sichtbar
- [x] getrennte Minimalpakete für Identität, Industrie und Planetare Industrie sind im Code festgelegt
- [x] Portalwerte, Scope-Liste, PowerShell-Konfiguration und Sicherheitsgrenzen sind in `docs/EVE_DEVELOPER_APPLICATION.md` dokumentiert

## Vierter Baustein: versionierte statische EVE-Daten

- [x] offizielles buildbasiertes JSON-Lines-Format der neuen EVE-SDE
- [x] gecachte Abfrage von `latest.jsonl` mit `ETag` und `Last-Modified`
- [x] begrenzter Streaming-Download in eine temporäre Datei mit lokaler SHA-256-Prüfsumme
- [x] Schutz vor fehlenden, doppelten, verschlüsselten oder übermäßig komprimierten Archivdateien
- [x] normalisierte Typen, Kategorien, Marktgruppen, Blueprints, Aktivitäten, Materialien, Produkte und PI-Schematics
- [x] versionierte Staging-Daten und atomare Aktivierung erst nach Mengen-, Referenz- und Integritätsprüfungen
- [x] fehlgeschlagene neue Builds verändern die letzte gültige aktive Version nicht
- [x] bekannte verwaiste Blueprint-Typreferenzen der offiziellen SDE werden gezählt und sichtbar als Importwarnung gespeichert
- [x] Import gegen den offiziellen Tranquility-Build `3484357` vom 28.08.2026 erfolgreich geprüft

## Fünfter Baustein: zentraler ESI-Transport

- [x] festes, zentral dokumentiertes `X-Compatibility-Date` für jede ESI-Anfrage
- [x] eindeutiger User-Agent mit Produkt und Version
- [x] frische Antworten werden bis `Expires` ohne erneute Netzwerkanfrage verwendet
- [x] abgelaufene Antworten werden mit `ETag`, `If-None-Match`, `Last-Modified` und `If-Modified-Since` revalidiert
- [x] private Cacheeinträge sind strikt nach Charakter getrennt; Tokens werden nicht Teil von URL oder Cache-Schlüssel
- [x] begrenzte Wiederholungen für Transportfehler sowie temporäre `420`, `429`, `502`, `503` und `504`
- [x] `Retry-After`, globales ESI-Fehlerlimit und neue Rate-Limit-Buckets werden ausgewertet
- [x] Authentifizierungs- und Berechtigungsfehler erzeugen keine automatischen Wiederholungsschleifen
- [x] Antwortgröße, JSON, HTTP-Daten, Seitenzahl und numerische Limitheader werden geprüft

## Sechster Baustein: Asset- und Blueprint-Snapshots

- [x] aktuelle Asset- und Blueprint-Schemas sowie Scopes gegen die offizielle ESI-OpenAPI-Spezifikation vom 30.08.2026 geprüft
- [x] vollständige Mehrseitenabfragen mit festem `X-Pages` und identischem `Last-Modified` über alle Seiten
- [x] strikte Prüfung aller Pflichtfelder, IDs, Mengen, Standorte, BPO-/BPC-Werte und Duplikate
- [x] Assets und persönliche Blueprints werden gemeinsam als neuer charakterbezogener Snapshot aktiviert
- [x] ein Fehler in einer Ressource oder Seite lässt den vorherigen vollständigen Snapshot unverändert
- [x] Snapshot- und Synchronisationsdaten eines Charakters sind von allen anderen Charakteren getrennt
- [x] der persistierte Snapshot verhindert auch nach einem Neustart erneute ESI-Abfragen vor Ablauf der einstündigen Cachezeit
- [x] erfolgreiche und fehlgeschlagene Läufe sowie der letzte erfolgreiche Synchronisationszeitpunkt werden lokal protokolliert
- [x] fehlende Asset-/Blueprint-Scopes stoppen vor der ersten ESI-Datenanfrage und nennen das benötigte Berechtigungspaket

## Noch offen bis zur Phase-2-Abnahme

- [ ] EVE-Developer-Anwendung mit öffentlicher Client ID und exaktem Callback registrieren
- [ ] Modulaktivierung fordert fehlende Industrie-/PI-Scopes sichtbar über eine erneute Autorisierung an
- [x] SDE-Download, Prüfung, Versionierung und atomarer Import
- [x] ESI-Client mit Kompatibilitätsdatum, Cache, ETag, Retry und Fehlerlimit-Schutz
- [ ] erste Asset-, Blueprint-, Job- und Planetensynchronisation
- [ ] parallele, voneinander isolierte Synchronisation von mindestens zwei Charakteren
- [ ] sichtbare SDE-Version sowie korrekte Kennzeichnung veralteter und fehlgeschlagener Daten
- [ ] vollständiger Windows-Paket- und Live-SSO-Abnahmetest

## Fortschritt

Der gewichtete Gesamtfortschritt bleibt bis zur vollständigen Abnahme von Phase 2 bei `15 %`. Nach bestandener Phase-2-Abnahme steigt er gemäß Masterplan auf `30 %`.
