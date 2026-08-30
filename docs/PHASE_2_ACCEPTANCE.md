# Phase 2 – Abnahmeprotokoll

## Ergebnis

Die Implementierung der EVE-Datenbasis ist **technisch vollständig und abnahmebereit**.
Alle lokal und in GitHub automatisierbaren Kriterien sind erfüllt. Die formale Abnahme
und der Sprung des Gesamtfortschritts von `15 %` auf `30 %` benötigen noch einen echten
vollständigen EVE-Datenabruf mit gemeinsam erteilten Industrie-/PI-Scopes und einen echten
Zwei-Charakter-Durchlauf. Callback und erster Charakterlogin wurden bereits bestätigt.

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

## Manuell noch auszuführen

1. Version `v0.2.0` ohne Client-ID-Umgebungsvariable starten und einen echten Charakter über
   den Systembrowser verbinden. Die vier Industrie-/PI-Scopes gemeinsam bestätigen.
2. Ohne zusätzliche Schaltfläche prüfen, dass SDE, Industrie, Jobs und PI unmittelbar geladen
   und in der Übersicht als aktuell oder durch die offizielle Cachezeit begründet markiert werden.
3. Nach mindestens fünf Minuten den erneuten Job-Abruf und die weiterhin respektierten
   Zehn-/Sechzig-Minuten-Caches prüfen.
4. Einen zweiten Charakter verbinden und den parallelen automatischen Abruf wiederholen.
5. Den Client neu starten und bestätigen, dass Charaktere, sichere Refresh Tokens und lokale
   Snapshots weiter verfügbar sind und frische Daten nicht unnötig erneut abgefragt werden.

## Abnahmegrenze

Die Client-ID ist öffentlich und darf deshalb distributionsweit im Client enthalten sein.
EVE-Zugangsdaten, Access Tokens, Refresh Tokens und ein mögliches Client Secret dürfen weder
für automatisierte Tests noch für das Repository bereitgestellt werden. Deshalb kann der
letzte Live-Schritt erst auf der Installation des Betreibers abgeschlossen werden.
