# EVE-Developer-Anwendung für EVE Dolphin

Diese Datei enthält alle Werte, die für die lokale Entwicklung und den späteren
Windows-Client benötigt werden. Refresh Tokens, Access Tokens, EVE-Zugangsdaten und
ein mögliches Client Secret gehören **niemals** in dieses Repository.

## 1. Anwendung im EVE-Portal anlegen

1. [EVE Developers – My Applications](https://developers.eveonline.com/applications)
   öffnen und mit dem eigenen EVE-Konto anmelden.
2. Eine neue Anwendung für Authentifizierung und ESI-Zugriff anlegen.
3. Falls das Portal einen Client-Typ oder OAuth-Flow abfragt, einen
   **Desktop-/Native-/Public Client mit Authorization Code und PKCE** wählen.
4. Die folgenden Werte übernehmen.

| Feld | Wert |
|---|---|
| Name | `EVE Dolphin` |
| Beschreibung | `Local desktop companion for EVE Online with PI, industry, mining and PVE modules.` |
| Callback/Redirect URL | `http://127.0.0.1:38636/callback` |
| OAuth-Flow | Authorization Code mit PKCE (`S256`) |
| Client-Typ | Desktop/Native/Public Client |

Die Redirect URL muss einschließlich Schema, IP-Adresse, Port und Pfad exakt
übereinstimmen. `localhost` ist daher kein Ersatz für `127.0.0.1`.

Das Portal kann die Bezeichnungen der Felder ändern. Maßgeblich sind die oben
genannten Werte und der PKCE-Flow für einen lokalen Desktop-Client. Die
[offizielle SSO-Dokumentation](https://developers.eveonline.com/docs/services/sso/)
beschreibt PKCE ausdrücklich für Anwendungen, die kein Client Secret sicher
speichern können.

## 2. Berechtigungen der Anwendung

Die Developer-Anwendung darf nur Scopes enthalten, die EVE Dolphin tatsächlich
benötigt. Die Anmeldung eines Charakters fordert diese Berechtigungen später
modulweise an; die bloße Zuordnung im Developer-Portal erteilt noch keinen Zugriff.

| Paket | Scopes im Developer-Portal | Verwendung |
|---|---|---|
| Identität | keine zusätzlichen Scopes | Charakter sicher verbinden |
| Industrie | `esi-assets.read_assets.v1`<br>`esi-characters.read_blueprints.v1`<br>`esi-industry.read_character_jobs.v1` | Assets, Blueprints und persönliche Industry Jobs |
| Planetare Industrie | `esi-planets.manage_planets.v1` | eigene Planeten und Koloniedetails lesen |

Weitere Pakete für Mining, Markt/Wirtschaft und PVE werden erst ergänzt, wenn das
jeweilige Modul implementiert wird. Es ist nicht nötig und nicht erwünscht, jetzt
pauschal alle ESI-Scopes freizuschalten.

## 3. Öffentliche Client-ID des Clients

Die öffentliche Client-ID `6eb6e51acc67412ba266189b7ceb8e16` ist im Desktop-Client
vorkonfiguriert. Nutzer müssen deshalb keine Umgebungsvariable setzen. Diese Kennung ist
kein Geheimnis; ein Client Secret wird weiterhin weder benötigt noch gespeichert.

Nur für Tests mit einer alternativen Developer-Anwendung kann die Client-ID lokal
überschrieben werden.

PowerShell, nur für das aktuelle Terminal:

```powershell
$env:EVE_SSO_CLIENT_ID = "<alternative-öffentliche-client-id>"
uv run eve-dolphin
```

PowerShell, dauerhaft für den aktuellen Windows-Benutzer:

```powershell
[Environment]::SetEnvironmentVariable(
    "EVE_SSO_CLIENT_ID",
    "<alternative-öffentliche-client-id>",
    "User"
)
```

Danach ein neues Terminal öffnen. Der Standard-Callback ist bereits im Programm
hinterlegt. Nur für gezielte lokale Tests kann er überschrieben werden:

```powershell
$env:EVE_SSO_REDIRECT_URI = "http://127.0.0.1:38636/callback"
```

Die im Portal registrierte URL und `EVE_SSO_REDIRECT_URI` müssen immer identisch sein.

## 4. Sicherheitsgrenzen

- EVE Dolphin fragt niemals nach dem EVE-Passwort; die Anmeldung läuft im Systembrowser.
- Der PKCE-Desktop-Flow benötigt kein Client Secret. Ein vom Portal angezeigtes Secret
  darf nicht in den Client, Quellcode, Build, Log oder Issue-Text kopiert werden.
- Access Tokens bleiben kurzlebig im Arbeitsspeicher.
- Refresh Tokens werden pro Charakter im Anmeldedatenspeicher des Betriebssystems
  abgelegt, nicht in SQLite.
- Rotiert EVE beim Erneuern ein Refresh Token, ersetzt EVE Dolphin den alten Wert.
- Widerruft der Spieler den Zugriff, entfernt EVE Dolphin das ungültige lokale Token
  und kennzeichnet den Charakter für eine erneute Autorisierung.

## 5. Kurzer Abnahmetest

1. `uv run eve-dolphin` starten; die öffentliche Client-ID ist bereits enthalten.
2. „Einstellungen & Charaktere“ öffnen und „EVE-Charakter verbinden“ wählen.
3. Im Browser anmelden, einen Charakter auswählen und zustimmen.
4. Prüfen, dass der Charakter lokal erscheint und kein Passwort im Client abgefragt wurde.
5. Den Charakter auswählen und nacheinander „Industrie freigeben“ sowie „PI freigeben“ wählen.
6. Bei beiden Browserfreigaben exakt denselben Charakter auswählen.
7. „EVE-Daten synchronisieren“ starten und auf der Übersicht SDE, Industrie, Jobs und PI prüfen.
8. Einen zweiten Charakter verbinden, erneut synchronisieren und die getrennten Datenstände prüfen.
9. EVE Dolphin neu starten und prüfen, dass Charaktere und Snapshots weiterhin gelistet sind.

Der Client liest die Konfiguration in
[`src/eve_dolphin/sso/config.py`](../src/eve_dolphin/sso/config.py). Der Implementierungs-
und Abnahmestand steht in [`docs/PHASE_2_STATUS.md`](PHASE_2_STATUS.md). Das ausführbare
Live-Protokoll steht in [`docs/PHASE_2_ACCEPTANCE.md`](PHASE_2_ACCEPTANCE.md).
