# Phase 4 – Manufacturing-MVP (in Arbeit)

## Ziel und aktueller Stand

Phase 4 verbindet persönliche Blueprints und Assets mit den Manufacturing-Rezepten des
atomar aktiven SDE-Builds. Der erste vertikale Baustein ist technisch umgesetzt: Nutzer
können einen eigenen BPO oder BPC auswählen, eine Zielmenge eingeben und den unmittelbaren
Material- und Zeitbedarf nachvollziehen. Der formale Gesamtfortschritt bleibt bis zur
Phase-3-Live-Abnahme bei `30 %`.

## Blueprint- und Rezeptgrundlage

- [x] aktive persönliche Blueprint-Snapshots aller Charaktere gemeinsam lesen
- [x] nur Manufacturing-Aktivitäten aus dem atomar aktiven SDE verwenden
- [x] Produkt, Ausgabemenge, Basiszeit und vollständige Materialliste verbinden
- [x] BPO/BPC, Besitzer, Standort, ME, TE und verfügbare Runs sichtbar machen
- [x] deutsche Namen mit englischem SDE-Fallback verwenden
- [x] ohne aktiven SDE- oder Blueprint-Snapshot einen erklärbaren Leerzustand zeigen

## Direkte Manufacturing-Kalkulation

- [x] Zielmenge in erforderliche Runs, geplante Ausgabe und Überschuss umrechnen
- [x] ME auf die gesamte Jobmenge anwenden und erst danach regelkonform aufrunden
- [x] mindestens eine Einheit jeder Materialart je Run erzwingen
- [x] TE auf die gesamte Basisdauer anwenden und sekundengenau aufrunden
- [x] fehlende BPC-Runs als eigenen Blocker ausweisen
- [x] Bestand am Blueprint-Ort und charakterübergreifenden Gesamtbestand trennen
- [x] lokale Materialfehlmenge je Material anzeigen

## Noch offen bis zur Phase-4-Abnahme

- Produktionsstandorte mit Struktur-, Rig-, Steuer- und Zeitprofilen
- gespeicherte Produktionsprojekte mit Zuständen und reproduzierbarem Kalkulationssnapshot
- Reservierungen, damit Materialien nicht von mehreren Projekten doppelt verwendet werden
- persönliche Industry Jobs einem Projekt und Zeitplan zuordnen
- Komponenten rekursiv auflösen und die Caracal-T1-Referenz vollständig abnehmen
- reale Blueprint-/In-Game-Jobprüfung mit mindestens einem verbundenen Charakter

Marktpreise, mengenabhängiger Build-or-Buy-Vergleich und Nettogewinn bleiben Phase 5 und 6
vorbehalten. Phase 4 erfindet für fehlende Preisdaten keinen Ersatzwert.
