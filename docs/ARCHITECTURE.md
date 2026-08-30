# Technische Architektur

## Status

Diese Architektur ersetzt mit Beschluss D-014 die zuvor geplante gehostete TypeScript-/PostgreSQL-Web-App. Version 1.0 wird als lokaler Python-Desktop-Client umgesetzt. Framework- und Paketversionen werden zu Beginn von Phase 1 auf unterstützte Releases festgelegt und durch Lockfiles reproduzierbar gehalten.

## Ziele

- lokale Nutzung ohne Hoster, Domain oder Serververwaltung
- einfache Installation und eigener Programmstart unter Windows
- mehrere eigene EVE-Charaktere pro Installation
- vollständig getrennte Daten je Installation
- sichere EVE-SSO-Anbindung ohne eingebettetes Client Secret
- gemeinsame, exakt testbare Berechnungslogik für PI und Manufacturing
- modularer Kern für spätere Mining- und PVE-Funktionen
- nachvollziehbare lokale Backups und Datenexporte
- spätere Portierung auf weitere Desktop-Systeme ohne fachlichen Neubau

## Systemübersicht

| Komponente | Verantwortung |
|---|---|
| Desktop-Oberfläche | Navigation, Tabellen, Diagramme, Eingaben und Datenstatus |
| Domänenkern | PI-, Blueprint-, Bestands-, Logistik- und Gewinnberechnungen; später Mining und PVE |
| Synchronisation | EVE SSO, ESI, SDE, Marktpreise, Cache und Wiederholungen |
| Aufgabensteuerung | lokale Hintergrundaufgaben, Fortschritt und Fehlerstatus |
| SQLite | Anwendungsdaten, Snapshots, Projekte und Synchronisationshistorie |
| OS-Anmeldedatenspeicher | Refresh Tokens je EVE-Charakter |
| Release-Paket | installierbarer Windows-Client mit Python-Laufzeit und Abhängigkeiten |

Version 1.0 benötigt weder PostgreSQL noch Redis, Docker, Reverse Proxy oder einen Hintergrundserver.

## Technologiestack

- **Sprache:** Python
- **Desktop-UI:** PySide6/Qt
- **Datenbank:** SQLite mit versionierten Migrationen
- **HTTP:** HTTPX mit zentralen Timeout-, Cache- und Retry-Regeln; Aufrufe laufen in lokalen Hintergrundaufgaben
- **SSO:** Authorization Code mit PKCE über den Systembrowser und einen kurzlebigen lokalen Callback
- **Tokenablage:** sicherer Anmeldedatenspeicher des Betriebssystems
- **Tests:** pytest, Golden Tests und UI-nahe Integrationstests
- **Paketierung:** eigenständiges Windows-Release, das keine separate Python-Installation verlangt

Die Berechnungs- und Datenzugriffsschicht darf keine Abhängigkeit von Qt besitzen. Dadurch bleibt die Fachlogik unabhängig testbar und kann später auch von einer anderen Oberfläche verwendet werden.

## Repository-Struktur

```text
src/eve_dolphin/
  app/                 Programmstart, Lebenszyklus und globale Konfiguration
  ui/                  PySide6-Fenster, Ansichten, Dialoge und View-Modelle
  domain/              PI-, Blueprint-, Bestands- und Gewinnlogik
  mining/              späteres Mining- und Reprocessing-Modul
  pve/                 späteres PVE- und Missionsjournal-Modul
  database/            SQLite-Schema, Migrationen und Repositories
  esi/                 ESI-Client, Cache und Datenadapter
  sso/                 PKCE, lokaler Callback und Tokenverwaltung
  sde/                 SDE-Download, Prüfung und Import
  sync/                lokale Aufgabensteuerung und Synchronisationsläufe
  i18n/                deutsche und englische Texte
  resources/           Icons, Themes und statische Anwendungsressourcen
tests/
  unit/
  integration/
  golden/
docs/
```

## Lokales Betriebsmodell

Eine Installation entspricht einem lokalen Nutzerprofil. Es gibt keine Anwendungskonten und keine Mandantenverwaltung.

- mehrere eigene EVE-Charaktere werden einzeln verbunden
- jeder Datensatz mit Charakterbezug trägt eine `character_id`
- gemeinsame lokale Projekte können Bestände mehrerer verbundener Charaktere verwenden
- der Benutzer entscheidet pro Projekt, welche Charaktere berücksichtigt werden
- alle Daten verbleiben im Anwendungsdatenverzeichnis des angemeldeten Betriebssystemnutzers
- parallele Windows-Benutzerkonten erhalten durch getrennte Anwendungsdatenverzeichnisse unabhängige Installationsdaten

Ein anderer Spieler erhält keine Zugangsdaten zu einer gemeinsamen Instanz. Er installiert seinen eigenen Client und verbindet ausschließlich seine eigenen Charaktere.

## EVE SSO und Tokens

Desktop-Anwendungen können kein dauerhaftes Client Secret geheim halten. Deshalb verwendet der Client den für Desktop-Anwendungen vorgesehenen Authorization-Code-Flow mit PKCE.

1. Der Client erzeugt einen kryptografisch zufälligen Code Verifier, Code Challenge und `state`.
2. Die EVE-Anmeldung öffnet sich im Systembrowser.
3. EVE SSO leitet auf einen registrierten lokalen Loopback-Callback zurück.
4. Der Client akzeptiert genau den erwarteten Callback und prüft `state`.
5. Der Authorization Code wird mit Code Verifier und öffentlicher Client ID eingelöst.
6. Das Access Token wird vollständig validiert.
7. Das Refresh Token wird unter einer charakterbezogenen Kennung im OS-Anmeldedatenspeicher abgelegt.

Die sichtbare Charakterverknüpfung läuft in einem eigenen kurzlebigen Qt-Arbeitsthread. Der lokale Callback wird gebunden, bevor der Systembrowser geöffnet wird. Netzwerkzugriffe, Warten auf den Callback, Code-Austausch, JWT-Prüfung und Keyring-Zugriff blockieren dadurch nicht die Oberfläche. Beim Schließen der Anwendung wird ein noch wartender Callback kontrolliert abgebrochen.

Weitere Regeln:

- Scopes werden modulbezogen und so spät wie möglich angefordert.
- Refresh Tokens stehen niemals in SQLite, Logs, Exporten oder Fehlerberichten.
- Access Tokens bleiben nur so lange wie nötig im Arbeitsspeicher.
- Ein zurückgegebenes Refresh Token ersetzt den bisherigen Keyring-Wert, bevor nachrangige Charaktermetadaten aktualisiert werden; gleichzeitige Refresh-Versuche desselben Charakters werden serialisiert.
- `invalid_grant` und sichere Identitätsabweichungen markieren nur den betroffenen Charakter als „erneut verbinden“ und entfernen dessen ungültiges Token. Temporäre OAuth-Fehler behalten es.
- Ein entfernter Charakter löscht seinen lokalen Tokenverweis und die gespeicherte Berechtigung.
- Widerrufene oder abgelaufene Berechtigungen verlangen eine neue ausdrückliche Anmeldung.
- OAuth-Endpunkte und Signaturschlüssel werden aus den offiziellen Metadaten ermittelt und angemessen gecacht.

Der Standard-Callback lautet `http://127.0.0.1:38636/callback` und muss exakt so in der EVE-Developer-Anwendung registriert werden. Für Entwicklungs- und Testinstallationen kann er vollständig überschrieben werden, bleibt aber auf IPv4-Loopback, HTTP, einen festen Port und den Pfad `/callback` beschränkt. Der Callback ist pro Anmeldeversuch kurzlebig, akzeptiert nur eine korrelierte Antwort und schreibt keine Query-Daten in Logs.

## SQLite und lokale Daten

SQLite speichert:

- lokale Einstellungen und Charaktermetadaten
- Assets, Blueprints und Industry Jobs
- Kolonie-Snapshots mit Pins, Links und Routen
- Markt-, Preis- und Systemkosten-Snapshots
- SDE-Importstatus und aktive Datenversion
- Produktionsprojekte, Kalkulationssnapshots und manuelle Profile
- Synchronisations- und Fehlerhistorie

Schreibvorgänge verwenden kurze Transaktionen. Lange Downloads und Berechnungen finden außerhalb einer offenen Schreibtransaktion statt. Migrationen werden vor dem Start der neuen Programmversion ausgeführt; davor legt der Client eine wiederherstellbare Sicherung an.

SQLite selbst wird in Version 1.0 nicht als Ersatz für den sicheren Token-Speicher behandelt. Der Schutz der übrigen lokalen Daten beruht auf dem Benutzerkonto und den Datenträger-Schutzfunktionen des Betriebssystems.

## Lokale Hintergrundaufgaben

ESI-Synchronisation, SDE-Import, Marktpreisabrufe und Prognosen laufen in der Anwendung im Hintergrund, damit die Oberfläche bedienbar bleibt.

- Aufgaben besitzen Status, Fortschritt, Abbruchsignal und verständliche Fehlerausgabe.
- Netzwerk- und Datenbankarbeit blockiert niemals den UI-Thread.
- Aufgaben sind wiederholbar; ein erneuter Lauf darf keine Duplikate erzeugen.
- Fehler eines Charakters blockieren andere Charaktere nicht.
- Beim Schließen kann der Client einen sicheren Abschluss laufender Schreibvorgänge abwarten.
- Ist der Client geschlossen oder der Rechner ausgeschaltet, findet keine Synchronisation statt.

Ein separater dauerhaft laufender Worker oder Systemdienst ist für Version 1.0 nicht vorgesehen.

## ESI-Client

Jede Anfrage verwendet:

- zentral festgelegtes `X-Compatibility-Date`
- eindeutigen User-Agent mit Anwendungsversion und Kontaktmöglichkeit
- Timeout und begrenzte Retry-Regeln
- `ETag`/`If-None-Match`, `Expires` und `Last-Modified`
- Auswertung von ESI-Fehlerlimit- und Bucket-Headern
- exponentielles Backoff mit Zufallsanteil bei geeigneten temporären Fehlern
- kein Retry bei fehlender Berechtigung oder fachlich ungültigen Anfragen

Seitennummerierte Ressourcen werden als konsistenter Abruf behandelt. Widersprechen sich relevante Cache- oder Änderungshinweise zwischen Seiten, wird der Snapshot verworfen und später neu geladen.

Der gemeinsame Transport verwendet das geprüfte Kompatibilitätsdatum `2026-08-30`.
Sein Prozesscache respektiert `Expires` und revalidiert erst danach bedingt. Private
Einträge tragen die Charakter-ID als Cachepartition; Access Tokens erscheinen weder
in URLs noch in Cache-Schlüsseln. Wiederholungen sind auf zwei Versuche nach der
ersten Anfrage begrenzt und gelten nur für Transportfehler sowie temporäre
Server-/Limitantworten. `401` und `403` gehen direkt an die Berechtigungslogik.

Der Transport unterstützt sowohl das ältere globale Fehlerbudget über
`X-ESI-Error-Limit-*` als auch die neuen gruppenbezogenen
`X-Ratelimit-*`-Header. Bei niedrigem Restbudget pausiert der zentrale Client weitere
Anfragen, statt den Server bis zur Sperre weiter zu belasten. Die folgende
Seitensynchronisation baut auf dem bereits zurückgegebenen `X-Pages`-Wert auf und
prüft die von CCP geforderte gemeinsame `Last-Modified`-Version aller Seiten.

## Charakterbezogene Industrie-Snapshots

Assets und persönliche Blueprints werden als ein gemeinsamer, unveränderlicher
Snapshot pro Charakter behandelt. EVE Dolphin erneuert dafür einmalig das Access
Token, prüft die beiden ausdrücklich benötigten Scopes und lädt anschließend alle
Seiten beider Ressourcen. `X-Pages` darf sich während eines Abrufs nicht ändern und
alle Seiten einer Ressource müssen denselben `Last-Modified`-Stand besitzen.

Erst nach erfolgreicher Payload-Prüfung schreibt eine einzelne SQLite-Transaktion
den Snapshot, alle Asset-/Blueprint-Zeilen, die aktive Snapshotreferenz, den
erfolgreichen Synchronisationslauf und `last_sync_at`. Der bisherige Snapshot wird
innerhalb derselben Transaktion erst nach dem Wechsel entfernt. Bei Netzwerk-,
Berechtigungs-, Seiten-, Validierungs- oder Datenbankfehlern bleibt er vollständig
aktiv. Ein Fehler eines Charakters verändert niemals den Snapshot eines anderen.

Die ESI-Routen besitzen aktuell eine Client-Cachezeit von einer Stunde. Der
Zeitpunkt des aktiven Snapshots liegt in SQLite, sodass ein Neustart diese Grenze
nicht umgeht. Dieser erste Snapshot enthält bewusst noch keine Asset-Namen,
Industry Jobs oder Planeten; diese Ressourcen folgen in getrennten Bausteinen.

## Industry-Job-Snapshots

Persönliche Industry Jobs besitzen wegen ihrer offiziellen fünfminütigen Cachezeit
einen eigenen Snapshotzyklus. Ein Abruf schließt `include_completed=true` ein; ESI
liefert dabei neben aktiven Jobs abgeschlossene Jobs der vergangenen 90 Tage. Der
Job-Scope wird erst unmittelbar vor diesem Abruf verlangt.

IDs, Status, Aktivität, Runs, Laufzeit, Zeitpunkte und optionale Ergebnisfelder
werden vor dem Schreiben geprüft. Kosten und Wahrscheinlichkeiten werden bereits
beim JSON-Parsing als `Decimal` gelesen und als Dezimaltext gespeichert. Dadurch
läuft kein verbindlicher ISK-Wert durch eine binäre Fließkommazahl. Auch hier
wechseln Snapshot, aktive Referenz, Laufstatus und `last_sync_at` gemeinsam in einer
SQLite-Transaktion; die vorige gültige Version bleibt bei jedem Fehler aktiv.

## PI-Lesemodell und Kolonieübersicht

Die sichtbare PI-Übersicht liest ausschließlich die atomar aktivierten
`planetary_current`-Snapshots. Ein charakterübergreifender, Qt-unabhängiger Dienst verdichtet
jede Kolonie zu Pin-, Link-, Routen-, Fabrik- und Lagerzahlen und klassifiziert
Extraktorprogramme anhand ihrer Ablaufzeit als aktiv, abgelaufen oder unvollständig. Der
nächste bekannte Ablaufzeitpunkt wird aus den aktiven Programmen bestimmt.

Alle referenzierten Pin-, Rohstoff- und Produkt-IDs werden in einer gebündelten Abfrage gegen
den aktiven, freigegebenen SDE-Build aufgelöst. Ein inaktiver Import kann dadurch keine Namen
in die Oberfläche mischen. Deutsche Namen verwenden den englischen SDE-Namen als Fallback;
fehlt auch dieser Datensatz, bleibt die Type-ID sichtbar. Die Qt-Seite aktualisiert sich nach
einem vollständigen Datenabruf oder einer Charakteränderung, führt aber selbst keine ESI-
oder SDE-Netzwerkanfrage aus.

Der Phase-3-Prognosedienst kombiniert den letzten vollständigen Kolonie-Snapshot mit den
Schematics, Volumen und Pin-Kapazitäten desselben aktiven SDE-Builds. Extraktoren werden bis
zum kleineren Wert aus Prognosehorizont und Ablaufzeit simuliert. Fabriken verbrauchen den
erkennbaren gemeinsamen Bestand in aufsteigender Produktstufe. Da ESI keine sekundengenaue
Route- und Pufferhistorie liefert, bleibt dieses Ergebnis ausdrücklich eine Schätzung.

Der PI-Zielplaner löst ein Ziel in absteigender Produktstufe rückwärts auf. Zunächst werden
pro Stufe die zum Zielzeitpunkt prognostizierten Bestände angerechnet; erst danach entstehen
Fabrikzyklen, Eingangsbedarf oder profilabhängige Importmengen. POCO-Steuern, Transport,
Frachtraum und Wurmlochrisiko stammen aus lokalen `pi_profiles`. Ein Profil ohne POCO
blockiert normale Importe, statt eine nicht ausführbare Kette als vollständig darzustellen.

## SDE-Import

1. Aktuelle Build-Metadaten mit HTTP-Caching prüfen.
2. Archiv nur bei einer neuen Version herunterladen.
3. Prüfsumme, Dateistruktur und erwartete Kerndatensätze validieren.
4. Daten in eine neue lokale Importversion schreiben.
5. Referenzen, Mengen und Pflichtfelder prüfen.
6. Golden Tests gegen bekannte Blueprints und Schematics ausführen.
7. Neue SDE-Version atomar aktivieren.
8. Vorherige Version bis zum erfolgreichen Abschluss beziehungsweise für einen begrenzten Rollback-Zeitraum behalten.

Ein fehlgeschlagener Import verändert niemals die aktive SDE-Version.

Der Import verwendet das aktuelle offizielle JSON-Lines-Archiv und liest Datensätze
zeilenweise, damit das vollständige Archiv nicht im Arbeitsspeicher liegen muss. Die
Download-Prüfsumme wird lokal während des Streamings berechnet; CCP veröffentlicht
im aktuellen Metadatensatz keine separate SHA-256-Summe. Metadaten- und Archiv-
Cachevalidatoren werden getrennt gespeichert. Offizielle verwaiste Referenzen in
Blueprint-Materialien oder -Produkten werden als gezählte Warnungen übernommen,
während gebrochene Kernreferenzen von Gruppen, Typen, Blueprints, PI-Schematics,
Solarsystemen und Planeten
die Aktivierung weiterhin verhindern.

## Kalkulationssnapshots

Ein gespeicherter Produktionsplan verweist nicht nur auf aktuelle Werte, sondern hält verwendete Mengen, Preise, Gebühren, SDE-Version, ESI-Datenalter, Formelversion und manuelle Eingaben fest. Dadurch bleiben spätere Soll-/Ist-Vergleiche nachvollziehbar.

Geldbeträge und Mengen verwenden Python `Decimal` beziehungsweise explizite ganzzahlige Einheiten. Unkontrollierte binäre Fließkommazahlen werden nicht für verbindliche ISK- oder Materialwerte eingesetzt.

## Installation und Updates

- Der normale Nutzer installiert ein signiertes beziehungsweise prüfbar veröffentlichtes Release-Paket und benötigt weder Python noch Docker.
- Anwendungsdateien und veränderliche Nutzerdaten liegen in getrennten Verzeichnissen.
- Ein Update darf die lokale Datenbank nicht ungefragt ersetzen.
- Vor einer Datenmigration wird automatisch eine Sicherung erzeugt.
- Ein späterer Update-Check darf eine neue Version melden; Download und Installation benötigen eine Bestätigung.
- Entwicklung erfolgt in einer reproduzierbaren Python-Umgebung mit gesperrten Abhängigkeiten.

Die Python-Codebasis bleibt gemeinsam und wird nicht pro Betriebssystem aufgeteilt. Installation, Signierung, OS-Anmeldedatenspeicher und Paketprüfung erzeugen dennoch getrennte Release-Pakete. Windows wird zuerst abgenommen; weitere Desktop-Systeme erhalten eigene Builds und Tests.

Quellcode, CI und Releases liegen gemeinsam im öffentlichen Repository
`Savox76/eve-dolphin-production`. Der manuell gestartete Releaseworkflow baut aus dem
geprüften `main`-Stand und veröffentlicht Windows-Paket, Prüfsumme und Änderungsprotokoll mit
dem kurzlebigen, auf dieses Repository begrenzten `GITHUB_TOKEN`.

## Backup und Wiederherstellung

- manueller Export eines lokalen Backup-Pakets
- optionaler automatischer Generationen-Backup beim Programmstart und vor Migrationen
- Datenbank-Integritätsprüfung vor dem Verpacken
- Refresh Tokens sind ausdrücklich nicht Bestandteil eines Backups
- Wiederherstellung prüft Schema-, App- und Datenversion
- SDE-Daten dürfen bei Bedarf neu importiert werden, um Backup-Größe zu reduzieren

## Architekturregeln

1. Domänenlogik kennt weder Qt-Widgets noch konkrete ESI-Payloads.
2. ESI- und SDE-Payloads werden an Adaptern in interne Modelle übersetzt.
3. Geldbeträge verwenden `Decimal`; Rundung erfolgt nur an fachlich festgelegten Grenzen.
4. Zeitpunkte werden intern in UTC gespeichert und lokal angezeigt.
5. Berechnungen erhalten explizite Einheiten.
6. Manuelle, geschätzte und automatisch geladene Werte tragen Herkunft und Zeitstempel.
7. Netzwerkzugriffe blockieren niemals den UI-Thread.
8. Tokens werden weder protokolliert noch in SQLite oder Exporte geschrieben.
9. Datenpfade werden über die Betriebssystem-APIs ermittelt und nicht relativ zum Installationsordner angenommen.
10. Jede Datenmigration ist getestet und besitzt einen klaren Fehler- und Wiederherstellungsweg.
11. Fachmodule verwenden den gemeinsamen Charakter-, Berechtigungs-, Asset-, Markt- und Datenstatuskern, bleiben aber untereinander lose gekoppelt.
12. Ein Modul fordert seine ESI-Scopes erst bei ausdrücklicher Aktivierung an.

## Offene Releaseentscheidungen

- signierter Release- und Updatekanal
- finaler Installer und Code-Signing-Prozess
- unterstützte zusätzliche Desktop-Betriebssysteme nach Version 1.0

Diese Punkte verändern die beschlossene lokale Client-Architektur nicht.

## Offizielle Referenzen

- [EVE SSO und Authorization Code mit PKCE](https://developers.eveonline.com/docs/services/sso/)
- [ESI Best Practices](https://developers.eveonline.com/docs/services/esi/best-practices/)
