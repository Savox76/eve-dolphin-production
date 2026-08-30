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

## Offen

### D-004 – Produktname

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Der Produktname lautet **EVE Production Tool**.
- **Beschreibung:** Die deutsche Funktionsbeschreibung lautet „Produktionsplanung für EVE Online“.
- **Branding:** Das Produkt wird deutlich als unabhängige Drittanbieter-Anwendung gekennzeichnet und verwendet den von CCP geforderten Schutzvermerk.

### D-005 – Betriebsart

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Die erste nutzbare Version wird als privat online erreichbare Web-App betrieben.
- **Zugriff:** Öffentliche Selbstregistrierung bleibt zunächst deaktiviert; nur freigegebene Nutzer erhalten Zugang.
- **Zielgeräte:** Desktop- und Mobilbrowser; die Oberfläche wird als installierbare PWA vorbereitet.

### D-006 – Technologiestack

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** TypeScript-Monorepo mit getrennten Web-, API- und Worker-Prozessen, PostgreSQL und Docker Compose.
- **Web:** React-basierte Server-/Client-Web-App mit PWA-Unterstützung.
- **API:** schlanker TypeScript-HTTP-Dienst mit typisierten Verträgen.
- **Worker:** eigener Prozess für ESI-Synchronisation, SDE-Import, Preise und Benachrichtigungen.
- **Warteschlange:** zunächst PostgreSQL-basiert; kein Redis in Version 1.0.
- **Begründung:** Eine Sprache, gemeinsam nutzbare Domänenlogik und geringe Betriebskosten bei sauberer Trennung langlebiger Hintergrundaufgaben.

### D-007 – Mehrbenutzerfähigkeit

- **Status:** beschlossen am 30.08.2026
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
