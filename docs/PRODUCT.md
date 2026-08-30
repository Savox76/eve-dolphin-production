# Produkt und Betriebsmodell

## Produktidentität

- **Name:** EVE Production Tool
- **Deutsche Beschreibung:** Produktionsplanung für EVE Online
- **Kurzbeschreibung:** Ein Produktions-Cockpit, das Planetare Industrie, Blueprints, Assets, Industry Jobs, Marktpreise und Logistik in einer nachvollziehbaren Planung verbindet.

Der Name ist bewusst funktional. Nutzer sollen ohne zusätzliche Erklärung erkennen, wofür das Tool gedacht ist.

## Erster Betriebsmodus

Die erste nutzbare Version wird **privat online erreichbar** betrieben.

- Zugriff über HTTPS im Desktop- und Mobilbrowser
- responsive Oberfläche und PWA-Vorbereitung
- keine öffentliche Registrierung
- Zugang nur für ausdrücklich freigegebene Nutzer
- EVE-Charaktere werden ausschließlich über EVE SSO verbunden
- Secrets und Refresh Tokens verbleiben serverseitig
- reproduzierbare Bereitstellung mit Docker Compose

Der konkrete Hostinganbieter und die Domain werden erst ausgewählt, wenn die technische Grundlage und der Ressourcenbedarf feststehen. Dadurch entstehen in der Spezifikationsphase keine unnötigen laufenden Kosten.

## Mehrbenutzerfähigkeit

Obwohl die erste Version privat bleibt, wird die Anwendung von Anfang an mehrbenutzerfähig modelliert:

- jeder Nutzer besitzt einen getrennten Anwendungsbereich
- jeder EVE-Charakter gehört genau einem freigegebenen Nutzerkonto
- EVE-Tokens, Kolonien, Assets, Blueprints und Projekte werden benutzerbezogen gespeichert
- gemeinsame Corporation-Daten erhalten später ein eigenes Rollen- und Freigabemodell
- Hintergrundjobs dürfen Daten verschiedener Nutzer nicht vermischen
- Logs enthalten keine Tokens oder vollständigen privaten EVE-Daten

Eine spätere Öffnung für weitere Spieler erfordert damit vor allem Betriebs-, Support- und Registrierungsfunktionen, aber keinen grundlegenden Umbau der Datenarchitektur.

## Produktgrenzen

EVE Production Tool ist ein Analyse-, Planungs- und Überwachungssystem. Es führt keine automatisierten Aktionen im EVE-Client aus und verändert keine Kolonien, Industry Jobs oder Marktorders selbstständig.

## Branding und Unabhängigkeit

EVE Production Tool ist eine unabhängige Drittanbieter-Anwendung. Gestaltung und Texte dürfen nicht den Eindruck erwecken, die Anwendung sei ein Produkt von CCP hf. oder offiziell von CCP unterstützt.

Der folgende Schutzvermerk wird in Repository, Anwendung und späterer öffentlicher Dokumentation geführt:

> © 2014 CCP hf. All rights reserved. "EVE", "EVE Online", "CCP", and all related logos and images are trademarks or registered trademarks of CCP hf.

Maßgeblich bleibt die jeweils aktuelle [CCP Developer License Agreement](https://developers.eveonline.com/license-agreement).

## Beschlossene Ausgangslage

| Entscheidung | Festlegung |
|---|---|
| Produktname | EVE Production Tool |
| Beschreibung | Produktionsplanung für EVE Online |
| Erstbetrieb | privat online erreichbar |
| Zielgeräte | Desktop- und Mobilbrowser, PWA vorbereitet |
| Nutzer | zunächst freigegebener privater Nutzerkreis |
| Architektur | von Anfang an mehrbenutzerfähig |
| Öffentliche Registrierung | nicht Bestandteil von Version 1.0 |
| Monetarisierung | nicht Bestandteil von Version 1.0 |
