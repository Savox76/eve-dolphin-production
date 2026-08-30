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
- Refresh Tokens werden charakterbezogen im sicheren Anmeldedatenspeicher des Betriebssystems abgelegt.
- Access Tokens verbleiben nur so lange wie erforderlich im Arbeitsspeicher.
- Tokens werden niemals in SQLite, Logs, Backups oder Exporte geschrieben.
- Ein Charakter kann jederzeit getrennt und seine Daten können gelöscht werden.
- ESI-Cache-, Fehlerlimit- und Retry-Vorgaben werden respektiert.
- Das Tool automatisiert keine Aktionen im EVE-Client.

## Sicherheitsprobleme

Sicherheitsprobleme sollen nicht öffentlich in einem Issue beschrieben werden. Bis ein privater Meldeweg eingerichtet ist, werden sie direkt an den Repository-Eigentümer gemeldet.
