# Produkt und Betriebsmodell

## Produktidentität

- **Name:** EVE Dolphin
- **Deutsche Beschreibung:** Lokaler EVE-Begleiter für Industrie, Mining und PVE
- **Kurzbeschreibung:** Eine modulare Desktop-Anwendung, die Daten mehrerer eigener Charaktere sicher lokal zusammenführt. Version 1.0 verbindet Planetare Industrie, Blueprints, Assets, Industry Jobs, Marktpreise und Logistik in einer nachvollziehbaren Planung.

Der Name dient bewusst als Dach für mehrere Fachmodule. Dadurch bleibt die Produktidentität bestehen, wenn nach Industrie und PI weitere Bereiche wie Mining und PVE/Missionen hinzukommen.

## Modulare Produktlinie

| Stufe | Fachlicher Schwerpunkt | Abgrenzung |
|---|---|---|
| Version 1.0 | Planetare Industrie und Manufacturing | aktueller verbindlicher Projektumfang |
| Version 1.1 | Mining und Reprocessing | beginnt erst nach stabiler Version 1.0 |
| Version 1.2 | PVE und Missionen | kombiniert verfügbare ESI-Daten mit einem lokalen Missionsjournal |

Charakterverwaltung, ESI-Synchronisation, statische Daten, Marktpreise, Assets, Datenstatus und lokale Historie bilden den gemeinsamen Kern. Neue Module erhalten eigene Berechtigungen und werden nur bei ausdrücklicher Aktivierung freigeschaltet.

## Erster Betriebsmodus

Die erste nutzbare Version wird als **lokaler Python-Desktop-Client** ausgeliefert.

- Bedienung in einem eigenen Desktop-Fenster
- lokale SQLite-Datenbank ohne Hoster und ohne separaten Datenbankdienst
- keine öffentliche Registrierung und keine zentrale Benutzerverwaltung
- mehrere eigene EVE-Charaktere pro Installation
- Charaktere werden ausschließlich über EVE SSO mit Authorization Code und PKCE verbunden
- Refresh Tokens werden im sicheren Anmeldedatenspeicher des Betriebssystems abgelegt
- ESI-, SDE- und Marktdaten werden nur synchronisiert, während der Client läuft
- Windows ist die erste Release-Plattform; die Python-Codebasis bleibt für weitere Desktop-Systeme portierbar

Jeder Spieler installiert das Tool selbst und besitzt eine vollständig unabhängige Datenablage. Es gibt keine gemeinsamen Konten, keinen zentralen Server und keinen Verkauf von Zugängen.

## Lokale Profile und Charaktere

- eine Installation entspricht einem lokalen Nutzerprofil
- jeder EVE-Charakter wird einzeln über EVE SSO autorisiert
- Charakterdaten, Kolonien, Assets, Blueprints und Projekte bleiben auf dem jeweiligen Rechner
- die Anzahl eigener Charaktere erhält keine künstliche fachliche Obergrenze
- ein Charakter kann getrennt werden, ohne andere lokale Charaktere zu beeinflussen
- Export, Backup und Wiederherstellung arbeiten mit einem dokumentierten lokalen Datenpaket; Tokens werden nicht exportiert
- Logs enthalten keine Tokens oder vollständigen privaten EVE-Daten

## Produktgrenzen

EVE Dolphin ist ein Analyse-, Planungs- und Überwachungssystem. Es führt keine automatisierten Aktionen im EVE-Client aus und verändert keine Kolonien, Industry Jobs, Marktorders, Schiffe oder Missionen selbstständig. „Überwachung“ bedeutet die Auswertung verfügbarer ESI-Daten und lokaler Einträge mit sichtbarem Datenalter; sie verspricht keine lückenlose Echtzeitansicht des Spielclients.

## Veröffentlichungsmodell

- eine gemeinsame Python-Codebasis für alle unterstützten Desktop-Systeme
- betriebssystemspezifische Pakete, weil Installation, Signierung und sichere Tokenablage je System unterschiedlich sind
- Windows als erste Release-Plattform; weitere Systeme erst nach eigener Abnahme
- privates Entwicklungs-Repository
- später ein separates öffentliches Release-Repository mit Binärpaketen, Prüfsummen und Changelog, ohne Verpflichtung zur Veröffentlichung des Quellcodes

## Branding und Unabhängigkeit

EVE Dolphin ist eine unabhängige Drittanbieter-Anwendung. Gestaltung und Texte dürfen nicht den Eindruck erwecken, die Anwendung sei ein Produkt von CCP hf. oder offiziell von CCP unterstützt.

Der folgende Schutzvermerk wird in Repository, Anwendung und späterer öffentlicher Dokumentation geführt:

> © 2014 CCP hf. All rights reserved. "EVE", "EVE Online", "CCP", and all related logos and images are trademarks or registered trademarks of CCP hf.

Maßgeblich bleibt die jeweils aktuelle [CCP Developer License Agreement](https://developers.eveonline.com/license-agreement).

## Beschlossene Ausgangslage

| Entscheidung | Festlegung |
|---|---|
| Produktname | EVE Dolphin |
| Beschreibung | Lokaler EVE-Begleiter für Industrie, Mining und PVE |
| Erstbetrieb | lokaler Python-Desktop-Client |
| Zielgeräte | Windows-Desktop zuerst; weitere Desktop-Systeme später möglich |
| Nutzer | ein lokales Profil mit mehreren eigenen Charakteren |
| Datenspeicher | SQLite lokal; Tokens im Anmeldedatenspeicher des Betriebssystems |
| Hoster und Registrierung | nicht erforderlich |
| Monetarisierung | nicht Bestandteil von Version 1.0 |
| Quellcode | private Entwicklung; öffentliche Binär-Releases später getrennt möglich |
