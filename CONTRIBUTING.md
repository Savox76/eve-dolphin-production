# Mitarbeit und Entwicklungsablauf

## Branches

- `main` bleibt jederzeit lauffähig.
- Neue Funktionen: `feature/<kurzer-name>`
- Fehlerbehebungen: `fix/<kurzer-name>`
- Dokumentation: `docs/<kurzer-name>`
- Wartung: `chore/<kurzer-name>`

Direkte Entwicklungscommits auf `main` werden nach der Ersteinrichtung vermieden.

## Lokale Python-Umgebung

```bash
uv sync --locked --all-groups
uv run eve-production-tool --self-check
```

Vor einem Pull Request müssen lokal mindestens Formatierung, Lint, Typprüfung und Tests ausgeführt werden:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

Die Benutzeroberfläche verwendet für headless Tests `QT_QPA_PLATFORM=offscreen`. Der Windows-Paketbuild wird auf einem Windows-Runner ausgeführt, weil PyInstaller keine Cross-Compilation unterstützt.

## Pull Requests

Vor dem Merge müssen:

- alle erforderlichen Checks grün sein,
- die Abnahmekriterien erfüllt sein,
- neue oder geänderte Funktionen getestet sein,
- Dokumentation und DE/EN-Texte angepasst sein,
- Migrationen und Sicherheitsauswirkungen beschrieben sein,
- keine Secrets oder personenbezogenen Daten enthalten sein.

## Commits

Commits sollen klein und nachvollziehbar bleiben. Bevorzugte Präfixe:

- `feat:` neue Funktion
- `fix:` Fehlerbehebung
- `docs:` Dokumentation
- `test:` Tests
- `refactor:` interne Überarbeitung
- `chore:` Wartung und Konfiguration

## Abnahme

Eine Phase wird erst als abgeschlossen und im Fortschritt angerechnet, wenn ihre Kriterien im Masterplan erfüllt und die zugehörigen Änderungen in `main` übernommen wurden.
