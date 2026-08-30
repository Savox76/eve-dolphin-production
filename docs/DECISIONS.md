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

- **Status:** offen
- **Vorläufig:** EVE Production Tool

### D-005 – Betriebsart

- **Status:** offen
- **Optionen:** privat gehostete Web-App oder ausschließlich lokale Installation

### D-006 – Technologiestack

- **Status:** offen
- **Tendenz:** möglichst kompakter TypeScript-Stack mit PostgreSQL und Docker Compose
