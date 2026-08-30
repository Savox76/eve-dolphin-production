# Phase 2 – Abnahmeprotokoll

## Ergebnis

Die EVE-Datenbasis ist **vollständig abgenommen**. Alle automatisierbaren Kriterien sind
erfüllt. Der Betreiber hat am 30.08.2026 den vollständigen Live-Datenweg und zwei echte,
parallel verbundene Charaktere bestätigt. Der Gesamtfortschritt steigt damit von `15 %`
auf `30 %`.

## Automatisiert bestanden

- Datenbankschema 6 einschließlich atomarer Industrie-, Job- und PI-Snapshots
- offizieller, versionierter JSON-Lines-SDE-Import mit sicherer Aktivierung
- ESI-Transport mit festem Kompatibilitätsdatum, Cache, ETag, Retry und Limit-Schutz
- vollständige Assets, persönliche Blueprints und aktive sowie jüngere abgeschlossene Jobs
- PI-Kolonien einschließlich Pins, Inhalte, Extraktorköpfe, Fabriken, Links, Routen und Wegpunkte
- isolierte parallele Verarbeitung mehrerer Charaktere
- gemeinsame Industrie- und PI-Erstfreigabe mit sichtbaren Reparaturaktionen
- Sofortabruf nach Verbindung und anschließende Fünf-Minuten-Prüfung
- sichtbare SDE-Version und pro Ressource die Zustände aktuell, veraltet, fehlgeschlagen und fehlend
- Python-Formatierung, Linting, strikte Typprüfung, Tests, Wheel/sdist und Selbstprüfung
- Windows-Paketworkflow einschließlich Start-/Selbstprüfung des erzeugten Clients

## Manuell bestätigt

- SSO mit der registrierten öffentlichen Client-ID und dem Loopback-Callback funktioniert.
- Die gemeinsamen Industrie-/PI-Scopes werden akzeptiert und die Daten werden geladen.
- Zwei echte Charaktere sind in derselben Installation verbunden und synchronisierbar.
- Refresh Tokens oder Zugangsdaten wurden für die Abnahme nicht offengelegt.

## Abnahmegrenze

Die Client-ID ist öffentlich und darf distributionsweit im Client enthalten sein.
EVE-Zugangsdaten, Access Tokens, Refresh Tokens und ein mögliches Client Secret bleiben
ausschließlich beim Betreiber und wurden für diese Abnahme nicht bereitgestellt.
