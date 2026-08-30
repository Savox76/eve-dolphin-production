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

- **Status:** offen
- **Tendenz:** möglichst kompakter TypeScript-Stack mit PostgreSQL und Docker Compose

### D-007 – Mehrbenutzerfähigkeit

- **Status:** beschlossen am 30.08.2026
- **Entscheidung:** Benutzer-, Charakter-, Token- und Produktionsdaten werden von Anfang an mandantengetrennt modelliert.
- **Begründung:** Das private Tool kann später für weitere Spieler geöffnet werden, ohne die Sicherheits- und Datenarchitektur neu aufzubauen.
- **Einschränkung:** Mehrbenutzerfähigkeit bedeutet in Version 1.0 keine öffentliche Registrierung oder Bezahlfunktion.
