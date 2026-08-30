# Projektentscheidungen

Dieses Dokument hält Entscheidungen fest, die Architektur, Funktionsumfang oder Betrieb langfristig beeinflussen.

## Beschlossen

### D-001 – Privater Start

- **Status:** beschlossen
- **Entscheidung:** Das Projekt beginnt als privates Repository und privates Tool.
- **Begründung:** Frühe Entwicklung und reale EVE-Daten sollen nicht öffentlich zugänglich sein.

### D-002 – PI ist Bestandteil von Version 1.0

- **Status:** beschlossen
- **Entscheidung:** Planetare Industrie von P0 bis P4 wird nicht als spätere Erweiterung behandelt, sondern mit Manufacturing verbunden.
- **Begründung:** Der größte Mehrwert entsteht durch eine durchgehende Kette von PI-Rohstoffen bis zum verkauften Endprodukt.

### D-003 – Nur grünes `main`

- **Status:** beschlossen
- **Entscheidung:** Feature-Arbeit erfolgt in Branches; in `main` wird nur nach erfolgreichen erforderlichen Checks übernommen.
- **Begründung:** `main` soll jederzeit einen nachvollziehbaren und lauffähigen Stand enthalten.

## Phase-0-Beschlüsse

### D-004 – Produktname

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Der Produktname lautet **EVE Production Tool**.
- **Beschreibung:** Die deutsche Funktionsbeschreibung lautet „Produktionsplanung für EVE Online“.
- **Branding:** Das Produkt wird deutlich als unabhängige Drittanbieter-Anwendung gekennzeichnet und verwendet den von CCP geforderten Schutzvermerk.

### D-005 – Betriebsart

- **Status:** ersetzt am 30.08.2026 durch D-014
- **Entscheidung:** Die erste nutzbare Version wird als privat online erreichbare Web-App betrieben.
- **Zugriff:** Öffentliche Selbstregistrierung bleibt zunächst deaktiviert; nur freigegebene Nutzer erhalten Zugang.
- **Zielgeräte:** Desktop- und Mobilbrowser; die Oberfläche wird als installierbare PWA vorbereitet.

### D-006 – Technologiestack

- **Status:** ersetzt am 30.08.2026 durch D-014
- **Entscheidung:** TypeScript-Monorepo mit getrennten Web-, API- und Worker-Prozessen, PostgreSQL und Docker Compose.
- **Web:** React-basierte Server-/Client-Web-App mit PWA-Unterstützung.
- **API:** schlanker TypeScript-HTTP-Dienst mit typisierten Verträgen.
- **Worker:** eigener Prozess für ESI-Synchronisation, SDE-Import, Preise und Benachrichtigungen.
- **Warteschlange:** zunächst PostgreSQL-basiert; kein Redis in Version 1.0.
- **Begründung:** Eine Sprache, gemeinsam nutzbare Domänenlogik und geringe Betriebskosten bei sauberer Trennung langlebiger Hintergrundaufgaben.

### D-007 – Mehrbenutzerfähigkeit

- **Status:** ersetzt am 30.08.2026 durch D-014
- **Entscheidung:** Benutzer-, Charakter-, Token- und Produktionsdaten werden von Anfang an mandantengetrennt modelliert.
- **Begründung:** Das private Tool kann später für weitere Spieler geöffnet werden, ohne die Sicherheits- und Datenarchitektur neu aufzubauen.
- **Einschränkung:** Mehrbenutzerfähigkeit bedeutet in Version 1.0 keine öffentliche Registrierung oder Bezahlfunktion.

### D-008 – ESI-Kompatibilitätsdatum

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Jede ESI-Anfrage sendet ein zentral konfiguriertes `X-Compatibility-Date`.
- **Aktualisierung:** Das Datum wird nur nach Prüfung der offiziellen Änderungen, aktualisierten Contract-Tests und erfolgreichem Testlauf angehoben.
- **Begründung:** Nicht geprüfte API-Änderungen dürfen die Anwendung nicht unbemerkt verändern.

### D-009 – Progressive EVE-Berechtigungen

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Das Tool fordert ESI-Scopes modulbezogen und so spät wie möglich an.
- **Beispiel:** PI-Berechtigung wird erst beim Aktivieren der PI-Funktionen benötigt; Corporation-Scopes gehören nicht zu Version 1.0.
- **Begründung:** Minimale Berechtigungen stärken Vertrauen und begrenzen die Folgen eines Sicherheitsvorfalls.

### D-010 – Produktneutrale Referenzfälle

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Die erste Spezifikation wird nicht auf ein persönliches Lieblingsprodukt zugeschnitten, sondern verwendet fünf breit abdeckende Referenzabläufe.
- **Referenzen:** Water/P1, Robotics/P3, Caracal/T1, Nanite Repair Paste/PI plus Manufacturing sowie J151141 ohne Customs Office.
- **Begründung:** Die spätere Engine soll sämtliche unterstützten SDE-Rezepte verarbeiten; die Referenzen decken unterschiedliche Daten-, Rechen- und Fehlerpfade ab.

### D-011 – Konservative, versionierte Wirtschaftskalkulation

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Neue Projekte bewerten vorhandene Materialien standardmäßig zu mengenabhängigen Wiederbeschaffungskosten und den Erlös als sofortige Liquidation in vorhandene Buy Orders.
- **Alternativen:** Planned Buy, Planned Sell, tatsächliche Einkaufskosten und interne Preise bleiben als ausdrücklich gewählte Szenarien verfügbar.
- **Nachvollziehbarkeit:** Jede Kalkulation speichert Preisquelle, Marktseite, Datenalter, Gebührenprofil, SDE-Build und Formelversion.
- **Begründung:** Verdeckte Mischpreise würden Gewinne überzeichnen. Ein konservativer Standard bleibt vergleichbar und kann vom Nutzer bewusst optimistischer eingestellt werden.

### D-012 – Arbeitsorientierte responsive Navigation

- **Status:** für den Desktop-Client durch D-014 angepasst
- **Desktop:** Alle acht Hauptansichten bleiben in einer linken Navigation sichtbar; Datenstatus und „Neues Projekt“ stehen global bereit.
- **Kompaktes Fenster:** Die Navigation wird schmaler und mehrspaltige Inhalte werden geordnet gestapelt, ohne Funktionen auszublenden.
- **Historie:** Die ursprünglich beschlossene mobile Bottom Navigation ist durch den lokalen Desktop-Betrieb nicht mehr Bestandteil von Version 1.0.
- **Datenqualität:** Aktuelle, veraltete, geschätzte, manuelle, unvollständige und blockierte Daten werden durch Text, Symbol und Farbe unterschieden.
- **Begründung:** Die wichtigsten Kontrollen müssen unterwegs schnell erreichbar sein, ohne dass Desktop-Nutzer Übersicht oder Kontext verlieren.

### D-013 – Phase 0 ist abgenommen

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Die Produktspezifikation ist vollständig genug, um mit dem technischen Fundament zu beginnen.
- **Nachweis:** Produkt, Referenzabläufe, Datenmatrix, Architektur, Formelkatalog und UX-Spezifikation sind dokumentiert; die Repository-Checks waren erfolgreich.
- **Fortschritt:** Phase 0 entspricht `5 %` des Gesamtprojekts.
- **Nächster Schritt:** Phase 1 baut nach der Architekturänderung D-014 den lokalen Python-Client, seine lokale Infrastruktur und die automatisierte Qualitätsprüfung auf.

### D-014 – Lokaler Python-Desktop-Client

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Version 1.0 wird als eigenständiger lokaler Python-Desktop-Client umgesetzt; ein Hoster ist nicht erforderlich.
- **Oberfläche:** PySide6/Qt mit eigener Desktop-Navigation; Windows ist die erste Release-Plattform.
- **Daten:** SQLite speichert lokale Anwendungs-, Charakter-, ESI-, PI-, Produktions- und Projektdaten.
- **Charaktere:** Jede Installation kann mehrere eigene EVE-Charaktere verbinden; es gibt keine zentrale Benutzerverwaltung oder gemeinsamen Zugänge.
- **SSO:** Authorization Code mit PKCE, öffentlicher Client ID, Systembrowser und registriertem lokalem Callback; ein Client Secret wird nicht in die Anwendung eingebettet.
- **Tokens:** Refresh Tokens werden im sicheren Anmeldedatenspeicher des Betriebssystems und nicht in SQLite abgelegt.
- **Hintergrundarbeit:** ESI-, SDE- und Marktaktualisierungen laufen lokal, solange der Client geöffnet ist; ein dauerhafter Worker-Dienst ist nicht vorgesehen.
- **Auslieferung:** Das Windows-Release enthält die erforderliche Python-Laufzeit, sodass Nutzer weder Python, Docker noch eine Datenbank separat installieren müssen.
- **Verteilung:** Jeder Spieler installiert eine unabhängige Kopie und verbindet ausschließlich seine eigenen Charaktere. Zugangshandel und zentrale Monetarisierung sind kein Projektziel.
- **Ersetzt:** D-005, D-006 und D-007. Die Desktop-Struktur aus D-012 bleibt fachliche Grundlage; die mobile PWA gehört nicht mehr zu Version 1.0.
- **Begründung:** Das Tool soll ohne laufende Hostingkosten und Serverwartung persönlich nutzbar und als eigenständiger Client an andere Spieler weitergebbar sein.

### D-015 – Technische Basis des lokalen Clients

- **Status:** beschlossen am 30.08.2026
- **Python:** Python 3.12 ist die Entwicklungs- und Paketierungsbasis von Version 1.0.
- **Oberfläche:** PySide6 `6.11.2`.
- **Lokale Integration:** `platformdirs` `4.11.5` für Betriebssystempfade und `keyring` `25.7.0` für den Anmeldedatenspeicher.
- **Datenbank:** Standardbibliothek `sqlite3` mit eigenen geordneten, transaktionalen Migrationen; vor einer Migration einer bestehenden Datenbank wird eine lokale Sicherung erstellt.
- **Qualität:** pytest `9.1.1`, Ruff `0.16.5` und mypy `2.3.1`.
- **Paketierung:** PyInstaller `6.22.2`; Windows-Pakete werden auf einem Windows-Runner gebaut und durch einen paketierten Selbsttest geprüft.
- **Reproduzierbarkeit:** Direkte und transitive Python-Abhängigkeiten werden in `uv.lock` festgeschrieben.
- **Begründung:** Der Client erhält eine kleine, lokal wartbare Laufzeit ohne externen Datenbank- oder Serverdienst und kann trotzdem als eigenständiges Windows-Paket ausgeliefert werden.

### D-016 – Phase 1 ist abgenommen

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Das technische Fundament des lokalen Python-Clients erfüllt die Abnahmekriterien der Phase 1.
- **Nachweis:** PR #16 wurde erst nach erfolgreichen Repository-, Python-, UI- und Windows-Paketprüfungen in `main` übernommen.
- **Windows-Paket:** Die gebaute EXE bestand ihren SQLite-Selbsttest; das zugehörige private CI-Artefakt wurde erfolgreich hochgeladen.
- **Fortschritt:** Phase 1 erhöht den gewichteten Gesamtfortschritt von `5 %` auf `15 %`.
- **Nächster Schritt:** Phase 2 implementiert EVE SSO mit PKCE, mehrere eigene Charaktere, SDE-Import und den ESI-Synchronisationskern.
