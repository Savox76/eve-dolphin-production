# Abnahme Phase 1 – Technisches Fundament

## Ergebnis

Phase 1 wurde am `30.08.2026` technisch abgeschlossen. Der lokale Python-Client besitzt ein reproduzierbares Projektfundament, ein startfähiges Desktop-Fenster, eine migrationsfähige lokale Datenbank, sichere Token-Speichergrenzen und einen geprüften Windows-Paketbuild.

- Phasengewicht im Masterplan: `10 %`
- Gesamtfortschritt nach Abnahme: `15 %`
- nächster Meilenstein: Phase 2 – EVE-Datenbasis
- offene Phase-1-Blocker: keine

## Abgenommene Ergebnisse

| Ergebnis | Nachweis |
|---|---|
| Python-3.12-Projekt und gesperrte Abhängigkeiten | `pyproject.toml`, `.python-version`, `uv.lock` |
| lokaler PySide6-Client | `src/eve_production_tool/ui`, ausführbarer Einstiegspunkt |
| acht Hauptansichten und DE/EN-Basis | `MainWindow`, Übersetzungskatalog und UI-Tests |
| lokale SQLite-Datenbank | Verbindungspolitik, Schema 1 und transaktionale Migrationen |
| migrationssicheres Backup | automatischer Snapshot einer bestehenden Datenbank vor Änderungen |
| sichere Token-Grenze | OS-Keyring-Schnittstelle; keine Token- oder Client-Secret-Spalten in SQLite |
| automatisierte Qualität | Ruff, mypy strict, pytest, Self-Check und Repository Health |
| Windows-Paket | PyInstaller-Build auf Windows, erfolgreicher EXE-Selbsttest und CI-Artefakt |

## Prüfung der Abnahmekriterien

- [x] Eine frische lokale Datenablage wird reproduzierbar initialisiert.
- [x] Migrationen sind geordnet, wiederholbar und vor Änderungen sicherbar.
- [x] Formatierung, Lint, Typprüfung und Tests laufen automatisiert.
- [x] Das PySide6-Fenster besitzt die acht geplanten Navigationsbereiche.
- [x] Deutsche und englische Texte verwenden eine gemeinsame Übersetzungsgrenze.
- [x] Refresh Tokens sind technisch von SQLite, Logs und Exporten getrennt.
- [x] Der Windows-Paketbuild enthält die Python-Laufzeit.
- [x] Die gebaute EXE bestand den paketierten Selbsttest mit Schema 1.
- [x] PR #16 wurde erst nach vollständig grünen Checks übernommen.

## Nachweis des Windows-Pakets

Workflow `Python Client`, Lauf `33303190809`:

- `Python Quality`: erfolgreich
- `Windows Package`: erfolgreich
- Artefakt: `EVE-Production-Tool-Windows`
- komprimierte Artefaktgröße: `57.219.034 Bytes`
- SHA-256-Artefaktdigest: `9687161ff68a2613c098fa1177e931d7703e8e4677aa2d87551d5cc6ce639bb5`

Das Artefakt ist ein privates, zeitlich begrenztes CI-Testpaket und noch kein signierter öffentlicher Release-Installer.

## Eintritt in Phase 2

Phase 2 baut auf dem abgenommenen Fundament auf und umfasst als Nächstes:

1. öffentliche EVE-Client-ID und registrierte lokale Callback-Strategie konfigurieren
2. Authorization Code mit PKCE und `state` implementieren
3. Refresh Tokens über die vorhandene OS-Keyring-Grenze speichern
4. mehrere eigene Charaktere verbinden, anzeigen, aktualisieren und trennen
5. SDE herunterladen, prüfen, versionieren und atomar importieren
6. ESI-Client mit Kompatibilitätsdatum, Cache, Retry und Fehlerlimit-Schutz bauen
7. erste Assets-, Blueprint-, Job- und Koloniedaten synchronisieren

Die fachlichen PI- und Manufacturing-Berechnungen bleiben den dafür vorgesehenen Folgephasen zugeordnet.
