# Sicherheit

## Umgang mit Zugangsdaten

Folgende Daten dürfen niemals committed, in Issues eingefügt oder in Logs ausgegeben werden:

- EVE Client Secrets
- Access Tokens und Refresh Tokens
- Datenbankkennwörter
- private Schlüssel
- Session-Cookies
- vollständige `.env`-Dateien

Nur dokumentierte Platzhalter gehören in eine spätere `.env.example`.

## EVE SSO und ESI

- Es werden nur die tatsächlich benötigten Scopes angefordert.
- Tokens werden serverseitig verschlüsselt gespeichert.
- Ein Charakter kann jederzeit getrennt und seine Daten können gelöscht werden.
- ESI-Cache-, Fehlerlimit- und Retry-Vorgaben werden respektiert.
- Das Tool automatisiert keine Aktionen im EVE-Client.

## Sicherheitsprobleme

Sicherheitsprobleme sollen nicht öffentlich in einem Issue beschrieben werden. Bis ein privater Meldeweg eingerichtet ist, werden sie direkt an den Repository-Eigentümer gemeldet.
