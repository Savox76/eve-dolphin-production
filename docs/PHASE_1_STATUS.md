# Phase 1 – Technisches Fundament

## Ziel

Phase 1 macht aus der abgenommenen Produktspezifikation einen reproduzierbar entwickelbaren und paketierbaren lokalen Python-Client. Der fachliche EVE-Datenimport beginnt erst in Phase 2.

## Umgesetztes Fundament

- [x] Python-3.12-Projekt mit `src`-Layout und gesperrten Abhängigkeiten
- [x] ausführbarer Einstiegspunkt und paketierter Selbsttest
- [x] PySide6-Desktop-Fenster mit allen acht geplanten Hauptansichten
- [x] deutsche und englische Übersetzungsstruktur
- [x] lokale, idempotente SQLite-Migrationen
- [x] Backup einer bestehenden Datenbank vor einer Migration
- [x] Betriebssystemgerechte Daten-, Backup- und Logpfade
- [x] Refresh-Token-Schnittstelle für den Anmeldedatenspeicher des Betriebssystems
- [x] keine Token- oder Client-Secret-Spalten in SQLite
- [x] Datenschutz-orientiertes rotierendes lokales Logging
- [x] Ruff-, mypy-, pytest- und Selbsttest-Prüfungen
- [x] Windows-Paketbuild mit PyInstaller und Prüfung der gebauten EXE

## Abnahmevoraussetzungen

- [ ] Pull-Request-Prüfungen sind vollständig grün.
- [ ] Das Windows-Artefakt wird erfolgreich gebaut und sein Selbsttest besteht.
- [ ] Die Änderung ist nach grünen Checks in `main` übernommen.
- [ ] Der `main`-Stand ist grün.

Der Gesamtfortschritt bleibt bis zur vollständigen Phasenabnahme bei `5 %`. Nach Abnahme von Phase 1 beträgt er gemäß Masterplan `15 %`.

## Bewusst noch nicht enthalten

- echte EVE-SSO-Anmeldung und PKCE-Callback
- ESI- und SDE-Importe
- reale Charaktere, Assets, Blueprints, Jobs oder Kolonien
- fachliche PI- und Manufacturing-Berechnungen
- signierter öffentlicher Installer und automatischer Updatekanal

Diese Punkte gehören zu den folgenden Phasen und werden nicht durch Platzhalterdaten vorgetäuscht.
