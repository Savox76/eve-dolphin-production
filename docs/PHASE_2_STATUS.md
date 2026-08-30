# Phase 2 – EVE-Datenbasis (Live-Datenabnahme offen)

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
- [x] Authorization-Code-Austausch sendet Code, Client-ID und PKCE-Verifier, aber weder
  Redirect-URL noch Client Secret im Tokenpayload

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

## Siebter Baustein: persönliche Industry Jobs

- [x] offizielles Job-Schema und `esi-industry.read_character_jobs.v1` gegen die ESI-OpenAPI-Spezifikation vom 30.08.2026 geprüft
- [x] aktive und von ESI gelieferte abgeschlossene Jobs der vergangenen 90 Tage werden gemeinsam abgerufen
- [x] Jobstatus, Aktivitäten, Blueprint-/Produktreferenzen, Runs, Laufzeiten und optionale Abschlussdaten werden validiert
- [x] Installationskosten und Erfolgswahrscheinlichkeiten werden ohne binäre Fließkomma-Zwischenstufe als `Decimal` verarbeitet
- [x] Job-Snapshots werden pro Charakter atomar aktiviert und bei einem Fehler vollständig verworfen
- [x] der letzte gültige Snapshot und alle anderen Charaktere bleiben bei einem fehlerhaften Abruf unverändert
- [x] die persistierte fünfminütige ESI-Cachezeit bleibt auch über einen Programmneustart hinweg wirksam
- [x] fehlender Job-Scope stoppt vor der ESI-Anfrage und wird als erwarteter Berechtigungszustand protokolliert

## Achter Baustein: Planetare Industrie

- [x] Kolonieliste und vollständige Layouts gegen die offizielle ESI-OpenAPI-Spezifikation vom 30.08.2026 geprüft
- [x] `esi-planets.manage_planets.v1` wird vor der ersten PI-Anfrage kontrolliert
- [x] Planeten, Pins, Inhalte, Extraktorköpfe, Fabrikschematics, Links, Routen und Wegpunkte werden validiert
- [x] Mengen und Koordinaten werden ohne unnötige binäre Fließkomma-Zwischenstufe verarbeitet
- [x] alle Kolonien eines Charakters werden gemeinsam und atomar als neuer Snapshot aktiviert
- [x] ein fehlerhaftes Planetenlayout lässt den vorherigen Gesamtstand und andere Charaktere unverändert
- [x] die offizielle zehnminütige ESI-Cachezeit bleibt auch über einen Programmneustart hinweg wirksam
- [x] Schema 6 löscht ältere charakterbezogene PI-Snapshots erst nach erfolgreicher Aktivierung

## Neunter Baustein: Bedienbarer Gesamtabruf und sichtbarer Datenstand

- [x] SDE, Assets, Blueprints, Jobs und PI können über „EVE-Daten synchronisieren“ gemeinsam gestartet werden
- [x] Netzwerk-, Token-, Datenbank- und SDE-Arbeit läuft außerhalb des Qt-UI-Threads
- [x] mehrere Charaktere werden mit begrenzter Parallelität tatsächlich gleichzeitig verarbeitet
- [x] Fehler eines Charakters oder einer Ressource stoppen die übrigen Charaktere und Ressourcen nicht
- [x] die gemeinsamen ESI-Cache- und Rate-Limit-Zustände sind threadsicher
- [x] die Übersicht zeigt die aktive SDE-Buildnummer und den Veröffentlichungstag
- [x] Industrie, Jobs und PI werden pro Charakter korrekt als aktuell, veraltet, fehlgeschlagen oder fehlend markiert
- [x] ein fehlgeschlagenes SDE-Update bleibt sichtbar, ohne die letzte gültige aktive Version zu ersetzen
- [x] „Industrie freigeben“ und „PI freigeben“ fordern nur die fehlenden Scope-Pakete über erneute Browserautorisierung an
- [x] bei einer Scope-Erweiterung wird ausschließlich der zuvor ausgewählte Charakter akzeptiert

## Zehnter Baustein: gemeinsame Freigabe und automatische Aktualisierung

- [x] die erste Charakterverbindung fordert alle vier aktuellen Industrie-/PI-Scopes an
- [x] der erste vollständige Datenabruf startet unmittelbar nach erfolgreicher Verbindung
- [x] bestehende Charaktere werden beim Programmstart im Hintergrund synchronisiert
- [x] weitere Gesamtabrufe starten während der Laufzeit alle fünf Minuten
- [x] ein noch laufender Abruf wird nicht überlappt
- [x] persistente Fünf-, Zehn- und Sechzig-Minuten-Caches verhindern unnötige ESI-Anfragen
- [x] getrennte Industrie-/PI-Schaltflächen bleiben als Reparaturweg für ältere oder
  unvollständig freigegebene Charaktere verfügbar

## Noch offen bis zur Phase-2-Abnahme

- [x] öffentliche EVE-Client-ID im distributionsfähigen Desktop-Client konfigurieren
- [x] exakte Callback-Registrierung der Developer-Anwendung im Live-SSO bestätigen
- [x] Modulaktivierung fordert fehlende Industrie-/PI-Scopes sichtbar über eine erneute Autorisierung an
- [x] SDE-Download, Prüfung, Versionierung und atomarer Import
- [x] ESI-Client mit Kompatibilitätsdatum, Cache, ETag, Retry und Fehlerlimit-Schutz
- [x] erste Asset-, Blueprint-, Job- und Planetensynchronisation
- [x] parallele, voneinander isolierte Synchronisation von mindestens zwei Charakteren
- [x] sichtbare SDE-Version sowie korrekte Kennzeichnung veralteter und fehlgeschlagener Daten
- [x] vollständiger automatisierter Windows-Pakettest
- [x] Live-SSO-Identitätstest mit registrierter öffentlicher Client-ID und echtem Charakter
- [ ] vollständigen Live-Datenabruf mit den gemeinsam erteilten Industrie-/PI-Scopes bestätigen
- [ ] zweiten echten Charakter verbinden und den parallelen Live-Abruf bestätigen

## Fortschritt

Die Implementierung von Phase 2 ist technisch vollständig und automatisiert geprüft. Der
gewichtete Gesamtfortschritt bleibt bis zum vollständigen Live-Datenabruf und echten
Zwei-Charakter-Test bei `15 %`. Callback und erster Charakterlogin sind bereits bestätigt.
Nach der verbleibenden manuellen Abnahme steigt er gemäß Masterplan auf `30 %`. Die genaue
Abnahme steht in
[`PHASE_2_ACCEPTANCE.md`](PHASE_2_ACCEPTANCE.md).
