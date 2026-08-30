# Phase 3 – PI-MVP (in Arbeit)

## Ziel

Phase 3 macht aus den vollständig synchronisierten PI-Rohdaten eine belastbare
Kolonieüberwachung und danach einen erklärbaren PI-Zielplaner. Die technische Arbeit läuft
bereits parallel zur noch ausstehenden manuellen Live-Abnahme von Phase 2. Der formale
Gesamtfortschritt bleibt bis zu dieser Abnahme bei `15 %`.

## Erster Baustein: charakterübergreifende Kolonieübersicht

- [x] aktive vollständige PI-Snapshots aller verbundenen Charaktere gemeinsam lesen
- [x] Pins, Links, Routen, Fabriken und Lagerinhalte pro Kolonie zusammenfassen
- [x] aktive, abgelaufene und unvollständige Extraktorprogramme unterscheiden
- [x] nächsten bekannten Extraktor-Ablaufzeitpunkt bestimmen
- [x] Pin- und Produktnamen gegen den atomar aktiven SDE-Build auflösen
- [x] deutsche SDE-Namen mit kontrolliertem englischem beziehungsweise Type-ID-Fallback
- [x] echte Qt-Kolonieübersicht anstelle des bisherigen PI-Platzhalters
- [x] Aktualisierung der Ansicht nach Charakteränderungen und vollständigen Datenabrufen
- [x] deutsche und englische Oberflächentexte
- [x] isolierte Fachtests und Qt-Oberflächentests

Planet- und Systembezeichnungen stehen in diesem ersten Baustein bewusst als stabile IDs in
der Tabelle. Ihre Namensauflösung folgt mit dem nächsten Phase-3-Datensatz, ohne den bereits
funktionierenden Koloniestatus zu blockieren.

## Nächste Bausteine

- [ ] Planet- und Solarsystemnamen sowie Datenalter und Warnstufen sichtbar ergänzen
- [ ] Extraktor-Restlaufzeit und geschätzten P0-Ertrag pro Stunde/Tag berechnen
- [ ] Fabrikschematics, Eingänge, Ausgänge und erwartete Produktionszyklen auswerten
- [ ] Lagerfüllstände und erkennbare Unterversorgung prognostizieren
- [ ] PI-Produktionsgraph von P0 bis P4 aufbauen
- [ ] Zielprodukt, Menge und Zeitraum rückwärts planen
- [ ] vorhandene Kolonien und Lagerbestände gegen den Zielbedarf rechnen
- [ ] POCO-, Transport- und Wurmlochprofile integrieren
- [ ] Prognosen mit Quelle, Datenzeitpunkt und Unsicherheitsstatus kennzeichnen

## Abnahmegrenze

Phase 3 ist erst abgeschlossen, wenn die Kolonieüberwachung und der PI-Zielplaner anhand der
Referenzfälle im Masterplan geprüft sind. Dann steigt der Gesamtfortschritt nach vorheriger
Phase-2-Abnahme von `30 %` auf `50 %`.
