# Sicherheit

## Umgang mit Zugangsdaten

Folgende Daten dürfen niemals committed, in Issues eingefügt oder in Logs ausgegeben werden:

- EVE Client Secrets
- Access Tokens und Refresh Tokens
- private Schlüssel
- vollständige `.env`-Dateien
- lokale Datenbank- oder Backup-Dateien mit privaten EVE-Daten

Ein Desktop-Release darf kein EVE Client Secret enthalten. Die öffentliche Client ID ist kein Geheimnis, wird aber zentral und nachvollziehbar konfiguriert.

## EVE SSO und ESI

- Es werden nur die tatsächlich benötigten Scopes angefordert.
- Der Desktop-Client verwendet Authorization Code mit PKCE und öffnet EVE SSO im Systembrowser.
- EVE Dolphin fragt selbst niemals nach dem EVE-Passwort; Anmeldung und Charakterauswahl erfolgen ausschließlich auf der EVE-SSO-Seite im Systembrowser.
- Der lokale Callback bindet ausschließlich an `127.0.0.1`, prüft Pfad und kryptografisches `state` exakt und protokolliert keine Callback-Parameter.
- Access Tokens werden vor jeder Charakterverknüpfung anhand der offiziellen JWKS-Signatur, eines fest erlaubten RSA-Algorithmus, Issuer, Ablauf, Charakter-Subject und beider Audience-Werte validiert.
- Refresh Tokens werden charakterbezogen im sicheren Anmeldedatenspeicher des Betriebssystems abgelegt.
- Beim Erneuern wird ein von EVE rotiertes Refresh Token sofort im sicheren Anmeldedatenspeicher ersetzt.
- `invalid_grant`, ein fehlendes lokales Token oder eine abweichende Charakteridentität stoppt weitere automatische Refresh-Versuche und verlangt eine neue Autorisierung.
- Temporäre SSO- und Rate-Limit-Fehler löschen keine weiterhin gültige Freigabe.
- Access Tokens verbleiben nur so lange wie erforderlich im Arbeitsspeicher.
- Tokens werden niemals in SQLite, Logs, Backups oder Exporte geschrieben.
- Ein Charakter kann jederzeit getrennt und seine Daten können gelöscht werden.
- ESI-Cache-, Fehlerlimit- und Retry-Vorgaben werden respektiert.
- Das Tool automatisiert keine Aktionen im EVE-Client.
- Das Trennen eines Charakters verlangt eine sichtbare Bestätigung und entfernt dessen Refresh Token, bevor der lokale Charakterdatensatz gelöscht wird.

## Sicherheitsprobleme

Sicherheitsprobleme sollen nicht öffentlich in einem Issue beschrieben werden. Bis ein privater Meldeweg eingerichtet ist, werden sie direkt an den Repository-Eigentümer gemeldet.
