# Phase 2 – Abnahmeprotokoll

## Ergebnis

Die Implementierung der EVE-Datenbasis ist **technisch vollständig und abnahmebereit**.
Alle lokal und in GitHub automatisierbaren Kriterien sind erfüllt. Die formale Abnahme
und der Sprung des Gesamtfortschritts von `15 %` auf `30 %` benötigen noch einen echten
EVE-SSO-Durchlauf mit einer vom Betreiber registrierten öffentlichen Client-ID.

## Automatisiert bestanden

- Datenbankschema 6 einschließlich atomarer Industrie-, Job- und PI-Snapshots
- offizieller, versionierter JSON-Lines-SDE-Import mit sicherer Aktivierung
- ESI-Transport mit festem Kompatibilitätsdatum, Cache, ETag, Retry und Limit-Schutz
- vollständige Assets, persönliche Blueprints und aktive sowie jüngere abgeschlossene Jobs
- PI-Kolonien einschließlich Pins, Inhalte, Extraktorköpfe, Fabriken, Links, Routen und Wegpunkte
- isolierte parallele Verarbeitung mehrerer Charaktere
- progressive Industrie- und PI-Berechtigungen im lokalen Client
- sichtbare SDE-Version und pro Ressource die Zustände aktuell, veraltet, fehlgeschlagen und fehlend
- Python-Formatierung, Linting, strikte Typprüfung, Tests, Wheel/sdist und Selbstprüfung
- Windows-Paketworkflow einschließlich Start-/Selbstprüfung des erzeugten Clients

## Manuell noch auszuführen

1. Im EVE-Developer-Portal die in
   [`EVE_DEVELOPER_APPLICATION.md`](EVE_DEVELOPER_APPLICATION.md) dokumentierte Anwendung
   registrieren.
2. Die öffentliche Client-ID als `EVE_SSO_CLIENT_ID` setzen; kein Client Secret verwenden.
3. Den Windows-Client starten und einen echten Charakter über den Systembrowser verbinden.
4. Für denselben ausgewählten Charakter „Industrie freigeben“ und „PI freigeben“ ausführen.
5. „EVE-Daten synchronisieren“ starten und in der Übersicht SDE-Build, Industrie, Jobs und PI prüfen.
6. Einen zweiten Charakter verbinden und den gemeinsamen Abruf wiederholen.
7. Den Client neu starten und bestätigen, dass Charaktere, sichere Refresh Tokens und lokale
   Snapshots weiter verfügbar sind und frische Daten nicht unnötig erneut abgefragt werden.

## Abnahmegrenze

Die Client-ID ist öffentlich, bleibt aber installationsspezifische Betreiberkonfiguration.
EVE-Zugangsdaten, Access Tokens, Refresh Tokens und ein mögliches Client Secret dürfen weder
für automatisierte Tests noch für das Repository bereitgestellt werden. Deshalb kann der
letzte Live-Schritt erst auf der Installation des Betreibers abgeschlossen werden.
