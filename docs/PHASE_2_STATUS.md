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

## Noch offen bis zur Phase-2-Abnahme

- [ ] EVE-Developer-Anwendung mit öffentlicher Client ID und exaktem Callback registrieren
- [ ] nicht blockierende SSO-Anmeldung in die PySide6-Charakteransicht integrieren
- [ ] Refresh-Flow, Widerrufserkennung und erneute Autorisierung
- [ ] progressive Scope-Pakete für Assets, Blueprints, Jobs und PI
- [ ] SDE-Download, Prüfung, Versionierung und atomarer Import
- [ ] ESI-Client mit Kompatibilitätsdatum, Cache, ETag, Retry und Fehlerlimit-Schutz
- [ ] erste Asset-, Blueprint-, Job- und Planetensynchronisation
- [ ] parallele, voneinander isolierte Synchronisation von mindestens zwei Charakteren
- [ ] sichtbare SDE-Version sowie korrekte Kennzeichnung veralteter und fehlgeschlagener Daten
- [ ] vollständiger Windows-Paket- und Live-SSO-Abnahmetest

## Fortschritt

Der gewichtete Gesamtfortschritt bleibt bis zur vollständigen Abnahme von Phase 2 bei `15 %`. Nach bestandener Phase-2-Abnahme steigt er gemäß Masterplan auf `30 %`.
