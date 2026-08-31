# Releases und Updates

## Repository und Berechtigungsgrenze

- `Savox76/eve-dolphin-production` enthält öffentlichen Quellcode, Tests, Buildworkflow,
  Windows-ZIP-Dateien, SHA-256-Dateien und nutzerseitige Release Notes.
- Releases werden im selben Repository veröffentlicht, aus dem sie gebaut wurden.

Der Desktop-Client besitzt kein GitHub-Token und liest veröffentlichte Releases anonym über
HTTPS. Der GitHub-Actions-Workflow verwendet ausschließlich das kurzlebige, auf dieses
Repository begrenzte `GITHUB_TOKEN`.

## GitHub-Einrichtung

Es ist kein Personal Access Token und kein zusätzliches Actions Secret erforderlich. Der
Workflow fordert nur für den Veröffentlichungsschritt `contents: write` an; Build und Tests
arbeiten mit `contents: read`.

## Veröffentlichung

Nach einem erfolgreichen `Python Client`-Lauf auf `main` startet der Workflow
`Publish Windows Release` automatisch. Die einzige Versionsquelle ist
`src/eve_dolphin/version.py`; Paket, Anwendung, Windows-Build und Updateprüfung lesen denselben
Wert. Der Workflow:

1. baut das Windows-Paket aus dem geprüften `main`-Stand,
2. führt den paketierten Selbsttest aus,
3. erzeugt ZIP und SHA-256-Datei,
4. übernimmt die zur Version gehörende Changelog-Sektion als Release Notes,
5. veröffentlicht Dateien und Hinweise als GitHub Release exakt am geprüften Commit.

Ist die Version bereits veröffentlicht, endet der automatische Lauf ohne erneute
Paketierung. Eine ältere Versionsnummer oder eine manuell angeforderte bereits verwendete
Version wird abgelehnt. Dadurch kann kein formal neues Paket erscheinen, das von
installierten Clients wegen identischer Versionsnummer übersehen wird. Der manuelle Start
bleibt für kontrollierte Wiederholungen mit einer noch unveröffentlichten Version erhalten.

Die erste updaterfähige Version ist `v0.2.0`. Sie muss noch über den bisherigen manuellen
Download installiert werden. Ab `v0.2.0` erkennt EVE Dolphin neuere veröffentlichte Versionen
selbst. `v0.3.0` ist die erste vollständige PI-MVP-Testversion und kann deshalb bereits über
den in `v0.2.0` enthaltenen manuellen Updatebutton installiert werden. `v0.3.1` korrigiert
den Windows-Dateiaustausch des ersten Updaters und ist auch aus `v0.2.0` oder `v0.3.0`
installierbar, weil bereits der neue, heruntergeladene Updatehelfer den geerbten
Installationsordner freigibt.

## Clientablauf

- Beim Start wird einmal nach neuen Versionen gesucht; die EVE-Datensynchronisation besitzt
  einen unabhängigen Fünf-Minuten-Takt.
- Ein Updatefenster zeigt installierte/neue Version, Datum, Größe und Release Notes.
- Nur der Button `Update starten` lädt das feste Windows-Asset.
- Während des Downloads zeigt das Fenster den Fortschritt in Prozent. Nach dem Neustart wird
  ein erfolgreicher Austausch oder ein sicher zurückgerollter Fehler im Client angezeigt.
- Herkunft, Dateiname, Downloadgröße, ZIP-Struktur, Buildinfo und GitHub-SHA-256-Digest werden
  geprüft.
- Das neue Paket ersetzt die Anwendung erst nach deren Ende und besteht vor dem Neustart den
  eingebauten Selbsttest.
- Bei jedem Fehler wird die alte Installation wiederhergestellt.

Der letzte terminale Updatestatus liegt bis zum nächsten Clientstart als kleine JSON-Datei im
benutzerspezifischen Updateordner. Er enthält nur Version, Zeitpunkt, Ergebnis und einen
technischen Fehlercode; keine Tokens, Charakterdaten oder GitHub-Zugangsdaten.

Lokale SQLite-Daten, Datenbanksicherungen, SDE-Dateien und Refresh Tokens liegen außerhalb des
Installationsordners und werden vom Updater nicht ersetzt.
