# Phase 3 – PI-MVP (technisch vollständig)

## Ziel und Stand

Phase 3 macht aus den atomaren PI-Snapshots eine charakterübergreifende
Kolonieüberwachung und einen erklärbaren Zielplaner. Die Implementierung und die
automatisierten Referenzfälle sind vollständig. Da die neue Oberfläche erst mit `v0.3.0`
ausgeliefert wird, bleibt der formale Gesamtfortschritt bis zur manuellen Live-Abnahme bei
`30 %`; nach dieser Abnahme steigt er auf `50 %`.

## Kolonieüberwachung

- [x] aktive vollständige PI-Snapshots aller verbundenen Charaktere gemeinsam lesen
- [x] Pins, Links, Routen, Fabriken und Lagerinhalte pro Kolonie zusammenfassen
- [x] Planet- und Solarsystemnamen aus dem atomar aktiven SDE-Build auflösen
- [x] aktive, bald endende, abgelaufene und unvollständige Extraktorprogramme unterscheiden
- [x] Datenalter und nächste bekannte Handlungszeit sichtbar ausweisen
- [x] P0-Ertrag je Stunde und für den 24-Stunden-Horizont schätzen
- [x] Fabrikschematics, Eingänge, Ausgänge und mögliche Zyklen auswerten
- [x] gestoppte, unterversorgte und unvollständige Fabriken warnend markieren
- [x] Lagerinhalte, Kapazität, Füllstand und erkennbaren Vollzeitpunkt prognostizieren
- [x] jede Prognose als Schätzung mit Snapshot-Zeitpunkt kennzeichnen
- [x] deutsche und englische Oberfläche mit kontrollierten Namensfallbacks
- [x] Lager und Launchpads einzeln mit Inhalt, Volumen und Füllstand darstellen
- [x] Extraktor- und Zukaufkolonien getrennt erkennen und ihre Restlaufzeit berechnen
- [x] unter zehn Stunden verbleibende Laufzeit sichtbar rot markieren

## PI-Zielplaner

- [x] vollständigen Produktionsgraph aus den aktiven SDE-Schematics ableiten
- [x] P0 bis P4 zyklusgenau und ohne fest codierte Rezepte rückwärts auflösen
- [x] Zielprodukt, Menge und Zeitraum als Nutzereingabe unterstützen
- [x] aktuelle Lagerbestände und Kolonieprognosen aller Charaktere gegenrechnen
- [x] Bedarf pro Tag, Zyklen, geplante Ausgabe, Import, Fehlmenge und Überschuss erklären
- [x] Import-/Exportvolumen und Frachtrouten berechnen
- [x] POCO-Import-/Exportsteuer sowie Transport- und Risikokosten ausweisen
- [x] editierbare Highsec-, Lowsec-, Nullsec- und Wurmlochprofile speichern
- [x] Wurmlochprofile mit und ohne POCO unterscheiden und nicht ausführbare Transporte blockieren
- [x] exakte automatisierte P2-, P3- und P4-Rückwärtsreferenzen prüfen
- [x] Eigenextraktion und Zukauf bis zu einer wählbaren PI-Stufe unterscheiden
- [x] empfohlenen Aufbau mit direkten Routen oder Pufferlagern ausweisen
- [x] Zielplanungen lokal speichern, laden, ändern und löschen

## Daten- und Sicherheitsgrenzen

- Die Produktionsrezepte, Typnamen, Volumen, Lagerkapazitäten, Systeme und Planeten stammen
  aus demselben geprüften und atomar aktivierten SDE-Build.
- Ein bestehender SDE-Build aus `v0.2.0` wird mit denselben Archiv- und Digestprüfungen atomar
  um die Phase-3-Daten ergänzt; ein Fehler lässt den bisherigen Stand unverändert.
- ESI liefert keine sekundengenaue Planetensimulation. Die Prognose simuliert deshalb einen
  gemeinsamen lokalen Bestand ohne vorzutäuschen, jede In-Game-Route sekundengenau zu kennen.
- Marktpreise und Build-or-Buy gehören zu den späteren Phasen. Phase 3 weist die benötigten
  Importmengen und lokalen Logistikkosten aus, erfindet aber keinen Marktwert.

## Manuelle Live-Abnahme

Mit `v0.3.0` sind noch folgende Betreiberprüfungen auszuführen:

1. Die Kolonien der zwei bereits verbundenen Charaktere zeigen richtige Planet-/Systemnamen,
   Datenalter, Extraktorstatus und erkennbare Warnungen.
2. Mindestens eine reale Fabrikkolonie wird mit ihrem Schematic und plausibler
   24-Stunden-Ausgabe angezeigt.
3. Je ein reales P2-, P3- und P4-Ziel wird mit einer manuellen EVE-Schematic-Prüfung
   verglichen.
4. Ein POCO-/Transportprofil wird angepasst und die Kostenänderung nachvollzogen.
5. Das Profil „Wurmloch ohne POCO“ blockiert einen Plan mit erforderlichem Import.

Nach Bestätigung dieser Punkte ist Phase 3 formal abgenommen und der Gesamtfortschritt
beträgt `50 %`.
