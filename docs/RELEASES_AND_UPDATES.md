# Releases und Updates

## Repositorygrenze

- `Savox76/eve-dolphin-production`: privater Quellcode, Tests und Buildworkflow
- `Savox76/eve-dolphin-releases`: öffentliche Windows-ZIP-Dateien, SHA-256-Dateien und
  nutzerseitige Release Notes

Der Desktop-Client besitzt kein GitHub-Token. Er kann das öffentliche Release-Repository
anonym lesen, während derselbe anonyme Zugriff auf das Produktions-Repository scheitert.

## Einmalige GitHub-Einrichtung

Für den Cross-Repository-Schritt benötigt der private Produktionsworkflow ein
**Fine-grained Personal Access Token** mit:

- Repositoryzugriff ausschließlich auf `Savox76/eve-dolphin-releases`
- Repository Permission `Contents: Read and write`
- keine Berechtigung für `eve-dolphin-production`

Das Token wird im privaten Produktions-Repository als Actions Secret
`EVE_DOLPHIN_RELEASES_TOKEN` gespeichert. Es darf nicht in Quellcode, Release-Repository,
EXE, Log oder lokale Konfigurationsdateien gelangen.

## Veröffentlichung

Der Workflow `Publish Windows Release` wird nach einem grünen Merge manuell gestartet. Der
angegebene Tag muss exakt der Anwendungsversion entsprechen. Der Workflow:

1. baut das Windows-Paket aus dem privaten Quellcode,
2. führt den paketierten Selbsttest aus,
3. erzeugt ZIP und SHA-256-Datei,
4. veröffentlicht nur diese beiden Dateien und die Release Notes im öffentlichen Repository.

Die erste updaterfähige Version ist `v0.2.0`. Sie muss noch über den bisherigen manuellen
Download installiert werden. Ab `v0.2.0` erkennt EVE Dolphin neuere veröffentlichte Versionen
selbst.

## Clientablauf

- Beim Start wird einmal nach neuen Versionen gesucht; die EVE-Datensynchronisation besitzt
  einen unabhängigen Fünf-Minuten-Takt.
- Ein Updatefenster zeigt installierte/neue Version, Datum, Größe und Release Notes.
- Nur der Button `Update starten` lädt das feste Windows-Asset.
- Herkunft, Dateiname, Downloadgröße, ZIP-Struktur, Buildinfo und GitHub-SHA-256-Digest werden
  geprüft.
- Das neue Paket ersetzt die Anwendung erst nach deren Ende und besteht vor dem Neustart den
  eingebauten Selbsttest.
- Bei jedem Fehler wird die alte Installation wiederhergestellt.

Lokale SQLite-Daten, Datenbanksicherungen, SDE-Dateien und Refresh Tokens liegen außerhalb des
Installationsordners und werden vom Updater nicht ersetzt.
