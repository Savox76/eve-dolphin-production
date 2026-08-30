# Verbindlicher Formel- und Bewertungskatalog

## 1. Zweck und Gültigkeit

Dieses Dokument definiert die Rechenregeln für Version 1.0 des EVE Production Tool. Es ist die fachliche Grundlage für Domänenmodelle, API-Verträge, Oberflächenhinweise und Golden Tests.

- Katalogversion: `formula-catalog-v1.0.0`
- geprüft am: `2026-08-30`
- Geldbeträge werden intern als Dezimalzahlen und niemals als binäre Fließkommazahlen verarbeitet.
- veränderliche Spielwerte werden als datierte Profile gespeichert und nicht in Formeln versteckt.
- gespeicherte Projekte behalten Formelversion, SDE-Build, ESI-Snapshots und manuelle Eingaben.
- tatsächliche ESI-/Wallet-Werte ersetzen keine Prognose rückwirkend, sondern werden für den Soll-/Ist-Vergleich ergänzt.

Die Formeln verwenden Prozentwerte intern als Dezimalfaktoren. `7,5 %` wird beispielsweise als `0,075` gespeichert.

## 2. Herkunft und Verlässlichkeit von Eingaben

Jeder Eingabewert erhält `sourceKind`, `sourceRef`, `observedAt`, `validFrom` und optional `validUntil`.

| Quellenart | Beispiel | Behandlung |
|---|---|---|
| `SDE` | Blueprint-Materialien, Produkte, Basiszeiten | an SDE-Build gebunden |
| `ESI_PUBLIC` | Orders, Adjusted Prices, System Cost Index | an ESI-Snapshot und Cache-Zeit gebunden |
| `ESI_CHARACTER` | Blueprint-Instanz, Assets, Kolonie, Industry Job | an Nutzer und Charakter gebunden |
| `EVE_ACTUAL` | tatsächliche Jobkosten oder Wallet-Buchung | maßgeblich für Soll-/Ist, nicht rückwirkend für die Prognose |
| `MANUAL` | POCO-Steuer, Strukturbonus, Transportprofil | Nutzer, Zeitpunkt und Notiz sind Pflicht |
| `DERIVED` | Materialbedarf, Gewinn, Marge | Formelversion und alle Eingabereferenzen sind Pflicht |

Fehlt ein kritischer Wert, ist das Ergebnis `INCOMPLETE`. Ein veralteter, aber vorhandener Wert erzeugt `STALE`; eine manuelle Annahme erzeugt `ASSUMED`. Keine dieser Markierungen darf in der Oberfläche als Live-Wert erscheinen.

## 3. Gemeinsame Zahlen- und Rundungsregeln

### 3.1 Rechenkern

- interne Präzision: mindestens 28 Dezimalstellen
- Rundungsmodus für geschätzte ISK-Zeilen: `ROUND_HALF_UP` auf `0,01 ISK`
- Summen werden aus ungerundeten Einzelwerten berechnet und erst an der ausgewiesenen Buchungsgrenze gerundet.
- Mengen unteilbarer Gegenstände sind ganzzahlig.
- Zeiten werden intern in ganzen Sekunden gespeichert.
- Prozentwerte werden nicht vorzeitig gerundet.

Ein von ESI gelieferter tatsächlicher Betrag wird unverändert gespeichert. Weicht die eigene Prognose um mehr als `0,01 ISK` oder eine Einheit vom kontrollierten EVE-Client ab, wird nicht still korrigiert: Der Golden Test und die Formelversion werden aktualisiert.

### 3.2 Marktpreise

ESI-Orderpreise werden unverändert verwendet. Manuelle Limitpreise müssen die im EVE-Markt gültige Preispräzision erfüllen; neue Empfehlungen werden auf höchstens vier signifikante Stellen und höchstens zwei Nachkommastellen normalisiert.

### 3.3 Zeitpunkte

Alle gespeicherten Zeitpunkte sind UTC. Anzeige und Nutzereingabe dürfen lokalisiert werden. Dauerberechnungen verwenden UTC und sind dadurch unabhängig von Sommerzeitwechseln.

## 4. Manufacturing

### 4.1 Benötigte Blueprint-Runs

```text
runs = ceil(targetQuantity / outputQuantityPerRun)
plannedOutput = runs * outputQuantityPerRun
surplus = plannedOutput - targetQuantity
```

`outputQuantityPerRun` stammt aus der aktiven SDE. BPC-Runs begrenzen `runs`; mehrere Blueprint-Instanzen dürfen nur über ausdrücklich getrennte Jobs kombiniert werden.

### 4.2 Material Efficiency und Materialrundung

Für jedes Blueprint-Material `i`:

```text
rawRequired_i = baseQuantity_i
              * runs
              * (1 - blueprintME / 100)
              * product(materialModifiers_i)

required_i = max(runs, ceil(rawRequired_i))
```

Regeln:

- `baseQuantity_i` stammt aus der SDE-Aktivität.
- ME wird auf den gesamten Job angewendet, nicht einzeln je Run.
- alle anwendbaren Materialmodifikatoren werden vor dem Aufrunden multipliziert.
- jede gelistete Materialart benötigt mindestens eine Einheit pro Run.
- Bestand, Reservierungen oder Einkauf ändern den Blueprint-Bedarf nicht; sie bestimmen nur dessen Deckung.

CCP beschreibt ME als ein Prozent Materialreduktion je Stufe, Aufrundung pro Job und mindestens eine Einheit jedes Materials pro Run.

### 4.3 Time Efficiency und Jobdauer

```text
rawJobSeconds = baseTimePerRunSeconds
              * runs
              * (1 - blueprintTE / 100)
              * product(timeModifiers)

jobSeconds = max(1, ceil(rawJobSeconds))
```

`timeModifiers` enthält nur nachweislich anwendbare Charakter-, Struktur-, Rig- und Standortfaktoren. Jeder Faktor wird einzeln angezeigt. TE reduziert die Basiszeit um zwei Prozent je Stufe bis zum Blueprint-Wert von 20 Prozent.

### 4.4 Industry Estimated Item Value

Für Manufacturing:

```text
EIV = runs * sum(baseQuantity_i * adjustedPrice_i)
```

- Blueprint-ME verändert den EIV nicht.
- `adjustedPrice_i` stammt aus `GET /markets/prices`.
- fehlt ein Adjusted Price, ist die Jobkostenprognose `INCOMPLETE`; ein Marktpreis darf ihn nicht still ersetzen.

### 4.5 Industry Job Installation Fee

```text
indexCost = EIV * systemCostIndex * product(indexCostModifiers)
facilityCost = EIV * facilityTaxRate
sccCost = EIV * sccSurchargeRate
alphaCost = EIV * alphaCloneTaxRate

totalInstallationFee = money(
  indexCost + facilityCost + sccCost + alphaCost
)
```

Das Standortprofil enthält:

- Aktivität und Sonnensystem
- System Cost Index samt Snapshot-Zeit
- Struktur-/Rig-Faktoren auf den Indexanteil
- Facility Tax
- SCC Surcharge
- Alpha-Status und gegebenenfalls Alpha Clone Tax

CCPs veröffentlichte Grundform lautet `EIV * ((SCI * bonuses) + FacilityTax + SCC + AlphaClone)`. Die im Profil initial hinterlegten SCC-, NPC- und Alpha-Sätze werden bei jeder EVE-Kompatibilitätsprüfung gegen den aktuellen Client beziehungsweise offizielle Änderungen geprüft.

## 5. Planetare Industrie

### 5.1 Schematic-Zyklen

Für ein Zielprodukt:

```text
cycles = ceil(targetQuantity / outputPerCycle)
plannedOutput = cycles * outputPerCycle
inputRequired_i = cycles * inputPerCycle_i
```

Alle Mengen und `cycleTimeSeconds` stammen aus der aktiven SDE beziehungsweise der öffentlichen Schematic-Route. Schematic-Mengen erhalten keine ME-Reduktion.

### 5.2 Kapazität mehrerer identischer Fabriken

Bei `factoryCount` identischen, gleichzeitig verfügbaren Fabriken:

```text
batches = ceil(cycles / factoryCount)
minimumElapsedSeconds = batches * cycleTimeSeconds
outputPerDay = factoryCount * outputPerCycle
             * (86400 / cycleTimeSeconds)
```

Das ist nur eine Kapazitätsuntergrenze. Fehlende Inputs, Routen, Lagerraum oder unterschiedlich verfügbare Fabriken verlängern die reale Zeit und werden separat simuliert.

### 5.3 Extractor-Prognose

Version 1.0 verwendet eine bewusst sichtbare Schätzung auf Basis des ESI-Snapshots:

```text
forecastStart = max(snapshotAt, installTime)
remainingCycles = max(
  0,
  floor((expiryTime - forecastStart) / cycleTimeSeconds)
)

baselineOutput = remainingCycles * esiQuantityPerCycle
lowOutput = floor(baselineOutput * (1 - uncertaintyRate))
highOutput = ceil(baselineOutput * (1 + uncertaintyRate))
```

- `uncertaintyRate` ist ein versionierter Prognoseparameter.
- `baselineOutput` ist nie ein garantierter Ertrag.
- Prognosen werden nach Ablauf, fehlender Route, vollem Puffer oder veraltetem Snapshot `UNCERTAIN` beziehungsweise `EXPIRED`.
- tatsächliche neue Extractor-Programme oder manuelle Umlagerungen werden nicht erfunden.

### 5.4 PI Import- und Exportsteuer

Für jede Transferzeile `i`:

```text
taxableValue_i = quantity_i * taxBase_i

playerTax_i = taxableValue_i * effectivePlayerRate_i
npcTax_i = taxableValue_i * effectiveNpcRate_i

transferTax = money(sum(playerTax_i + npcTax_i))
```

Das POCO-/Skyhook-Profil speichert Import- und Exportraten getrennt. Ein angezeigter Besitzersatz wird nicht automatisch halbiert oder verdoppelt; verwendet wird der effektiv im Client bestätigte Satz.

Für Highsec wird der NPC-Anteil initial so abgebildet:

```text
npcExportRate = 0.10 * (1 - 0.10 * customsCodeExpertiseLevel)
npcImportRate = 0.05 * (1 - 0.10 * customsCodeExpertiseLevel)
```

Der Skill reduziert nur den NPC-Anteil. Lowsec, Nullsec und Wurmloch verwenden standardmäßig `0` als NPC-Anteil, solange ein datiertes Regelprofil nichts anderes festlegt.

Initiales, versioniertes PI-Steuerbasisprofil:

| Stufe | Steuerbasis je Einheit |
|---|---:|
| P0 | 5 ISK |
| P1 | 400 ISK |
| P2 | 7.200 ISK |
| P3 | 60.000 ISK |
| P4 | 1.200.000 ISK |

Die Werte werden nicht im Rechenkern hartcodiert. P1 bis P4 entsprechen CCPs veröffentlichten Steuerbasen; P0 wird mit dem aktiven Typ-/Client-Snapshot kontrolliert.

Fehlt ein Customs Office oder Skyhook, ist normaler Import/Export `BLOCKED`. Ein Command-Center-Launch darf nur als eigener manueller Transportweg mit bestätigter Kapazität und Kosten geplant werden.

## 6. Markt und Preisermittlung

### 6.1 Mengengewichteter Sofortkauf

Sell Orders am zulässigen Standort werden nach Preis aufsteigend verbraucht:

```text
take_j = min(remainingQuantity, orderRemaining_j)
grossBuyCost = sum(take_j * orderPrice_j)
buyVWAP = grossBuyCost / filledQuantity
```

### 6.2 Mengengewichteter Sofortverkauf

Erreichbare Buy Orders werden nach Preis absteigend verbraucht:

```text
take_j = min(remainingQuantity, orderRemaining_j)
grossSales = sum(take_j * orderPrice_j)
sellVWAP = grossSales / filledQuantity
```

Reicht die Markttiefe nicht für die gesamte Menge, wird nur die gefüllte Menge bewertet und das Ergebnis `INCOMPLETE_DEPTH`. Ein Fallback auf Durchschnittspreise ist nur als sichtbares manuelles Szenario zulässig.

### 6.3 Preis- und Bewertungsmodi

| Modus | Preisquelle | Typische Verwendung |
|---|---|---|
| `REPLACEMENT` | sofortiger Einkauf aus Sell Orders | Standardwert vorhandener Materialien |
| `LIQUIDATION` | sofortiger Verkauf in Buy Orders | konservativer Erlös oder Opportunität |
| `PLANNED_BUY` | eigene Buy Order | günstigere, zeitlich unsichere Beschaffung |
| `PLANNED_SELL` | eigene Sell Order | höherer, zeitlich unsicherer Verkauf |
| `ACQUISITION` | tatsächliche Wallet-Transaktionen | historische Ausgaben und Soll-/Ist |
| `INTERNAL` | manueller Corp-/Transferpreis | interne Abrechnung |

Der Standard für neue Projekte ist konservativ: Materialkosten nach `REPLACEMENT`, Erlös nach `LIQUIDATION`. Nutzer können ein anderes Szenario wählen; Kosten- und Erlösseite bleiben getrennt sichtbar.

### 6.4 Broker Fee und Sales Tax

```text
orderValue = quantity * limitPrice
brokerFee = money(orderValue * effectiveBrokerRate)
salesTax = money(actualGrossSales * effectiveSalesTaxRate)
```

- sofort vollständig ausgeführte Orders tragen keine Listing-Brokergebühr.
- Sales Tax entsteht beim tatsächlichen Verkauf.
- NPC-Stationen verwenden den effektiven Charakter-/Standing-Satz.
- Upwell-Profile speichern Besitzergebühr und SCC-Anteil getrennt; Broker Relations wird dort nicht angewendet.

Der aktuelle offizielle NPC-Broker-Grundsatz startet bei `3 %`:

```text
npcBrokerRate = max(
  0.01,
  0.03
  - 0.003 * brokerRelationsLevel
  - 0.0003 * unmodifiedFactionStanding
  - 0.0002 * unmodifiedCorporationStanding
)
```

Der veröffentlichte Sales-Tax-Grundsatz startet bei `7,5 %` und kann mit Accounting bis `3,37 %` sinken. Für Kalkulationen wird der effektive, datiert geprüfte Satz aus dem Charakterprofil verwendet, damit eine geänderte Skillformel nicht unbemerkt alte Projekte verändert.

### 6.5 Orderänderung

Für optionale Relist-Szenarien:

```text
relistFee = money(
  max(0, brokerRate * (newPrice - oldPrice))
  + (1 - relistDiscountRate) * brokerRate * newPrice
)
```

Ohne explizite Anzahl geplanter Änderungen wird keine Relist Fee erfunden.

## 7. Bestand und Opportunitätskosten

```text
available = max(0, owned - reserved - inaccessible)
fromStock = min(required, available)
shortage = required - fromStock

stockOpportunityCost = fromStock * selectedValuationPrice
purchaseCost = shortage * selectedPurchasePrice
materialCost = stockOpportunityCost + purchaseCost
```

- `inaccessible` umfasst falsche Standorte oder nicht rechtzeitig verfügbare Mengen.
- ein Material aus eigenem Bestand ist nicht kostenlos.
- Standardbewertung für Bestand ist `REPLACEMENT`.
- tatsächliche historische Einkaufskosten werden zusätzlich angezeigt, aber nicht mit Wiederbeschaffungskosten vermischt.

## 8. Transport und Wurmlochrisiko

```text
trips = ceil(totalVolume / usableCargoCapacity)

baseHaulingCost = fixedCost
                 + trips * costPerTrip
                 + totalVolume * costPerM3
                 + trips * routeJumps * costPerJump

riskSurcharge = exposedReplacementValue * riskRate
totalLogisticsCost = money(baseHaulingCost + riskSurcharge)
```

Alle Raten sind manuelle Profile. `riskSurcharge` ist ein betrieblicher Aufschlag, keine behauptete Verlustwahrscheinlichkeit. Für Wurmlochrouten müssen Route, Sprungzahl, verfügbare Masse und Gültigkeitszeit manuell oder durch eine später ausdrücklich freigegebene Quelle bestätigt sein. Ohne bestätigte Route ist der Transport `UNROUTED`.

## 9. Gewinn- und Leistungskennzahlen

### 9.1 Kostenbrücke

```text
netSales = grossSales - brokerFees - salesTaxes - relistFees

totalProjectCost = materialCost
                 + installationFees
                 + piTaxes
                 + logisticsCost
                 + otherExplicitCosts

netProfit = netSales - totalProjectCost
```

Broker Fees werden nur dort abgezogen, wo das gewählte Verkaufsszenario tatsächlich eine gelistete Order vorsieht.

### 9.2 Marge und Rendite

```text
salesMargin = netProfit / grossSales
returnOnCost = netProfit / totalProjectCost
```

Bei Nenner `0` ist die Kennzahl nicht definiert. Die Oberfläche zeigt immer die verwendete Definition; „Marge“ bedeutet in Version 1.0 `salesMargin`.

### 9.3 Zeit- und Slotkennzahlen

```text
iskPerElapsedHour = netProfit / criticalPathHours
iskPerManufacturingSlotHour = netProfit / manufacturingSlotHours
iskPerPlanetHour = attributablePiProfit / planetOccupiedHours
```

- `criticalPathHours` ist die reale Projektlaufzeit vom ersten gebundenen Input bis zum geplanten Verkauf.
- `manufacturingSlotHours` ist die Summe aller belegten Manufacturing-Slotstunden.
- PI-Gewinn wird nur dann einem Planeten zugerechnet, wenn Kosten und Erlöse eindeutig zugeordnet sind.

### 9.4 Kapitalbindung

Aus allen datierten Zahlungsströmen wird die kumulierte Kapitalbindung gebildet:

```text
capitalAtRisk(t) = max(0, cumulativeOutflows(t) - cumulativeInflows(t))
peakCapital = max_t(capitalAtRisk(t))

capitalDays = sum(
  capitalAtRisk(interval) * intervalDurationDays
)
```

`capitalDays` ist eine ISK-Tage-Fläche und erlaubt den Vergleich unterschiedlich langer Projekte. Optional:

```text
capitalWeightedDurationDays = capitalDays / peakCapital
annualizedReturn = (1 + returnOnCost)^(365 / durationDays) - 1
```

Die annualisierte Rendite wird nur bei positiver Dauer und `returnOnCost > -1` angezeigt und ausdrücklich als Vergleichswert, nicht als Prognose bezeichnet.

## 10. Golden-Test-Kontrollbeispiele

Alle Beispiele verwenden exakt die angegebenen Eingaben, unabhängig von aktuellen Live-Preisen.

### GT-MFG-001 – ME pro Job

- Basis: `1.000` Einheiten, `3` Runs, ME `10`, keine weiteren Modifier
- Rechnung: `ceil(1000 * 3 * 0,90)`
- Erwartung: `2.700` Einheiten

### GT-MFG-002 – Mindestmenge pro Run

- Basis: `1` unteilbares Material, `10` Runs, ME `10`
- Prozentrechnung: `9`
- Erwartung wegen Mindestregel: `10` Einheiten

### GT-TIME-001 – TE und Zeitmodifier

- Basiszeit: `3.600 s`, `10` Runs, TE `20`, Zeitmodifier `0,95`
- Rechnung: `ceil(3600 * 10 * 0,80 * 0,95)`
- Erwartung: `27.360 s`

### GT-PI-001 – Water

- Schematic-Fixture: `3.000 Aqueous Liquids -> 20 Water`, Zyklus `1.800 s`
- Ziel: `1.000 Water`
- Erwartung: `50` Zyklen, `150.000 Aqueous Liquids`, `90.000 s` auf einer Fabrik

### GT-PI-002 – Parallele Robotics-Fabriken

- Schematic-Fixture: `10 Consumer Electronics + 10 Mechanical Parts -> 3 Robotics`, Zyklus `3.600 s`
- Ziel: `5.000 Robotics`, fünf Fabriken
- Erwartung: `1.667` Zyklen, je `16.670` Inputs, `5.001` Output, `334 h` Mindestdauer

### GT-POCO-001 – Highsec-P1-Export

- `1.000` P1-Einheiten, Steuerbasis `400 ISK`
- Customs Code Expertise V: NPC-Export `5 %`
- bestätigter effektiver Besitzer-Export `5 %`
- Erwartung: `20.000 ISK` NPC + `20.000 ISK` Besitzer = `40.000 ISK`

### GT-JOB-001 – Installation Fee

- EIV `100.000.000 ISK`, SCI `2 %`, Indexmodifier `0,90`
- Facility Tax `0,5 %`, SCC `0,25 %`, Omega
- Erwartung: `1.800.000 + 500.000 + 250.000 = 2.550.000 ISK`

### GT-MARKET-001 – Mengentiefe beim Einkauf

- Bedarf `100`, Sell Orders: `60 @ 10 ISK`, `40 @ 12 ISK`
- Erwartung: `1.080 ISK`, VWAP `10,80 ISK`

### GT-MARKET-002 – Mengentiefe beim Verkauf

- Menge `100`, Buy Orders: `30 @ 9 ISK`, `70 @ 8 ISK`
- Erwartung: `830 ISK`, VWAP `8,30 ISK`

### GT-PROFIT-001 – Kostenbrücke

- Gross Sales `1.000.000`, Broker `20.000`, Sales Tax `40.000`
- Material `600.000`, Job `50.000`, PI-Steuer `10.000`, Logistik `30.000`
- Erwartung: Net Sales `940.000`, Gesamtkosten ohne Marktgebühren `690.000`, Nettogewinn `250.000`, Marge `25 %`

## 11. Abnahme- und Änderungsregeln

- Jede implementierte Formel referenziert eine Kennung dieses Katalogs.
- Golden Tests nutzen feste Fixtures; Live-ESI ist in Unit-Tests verboten.
- Mindestens ein kontrollierter EVE-Client-Vergleich deckt Material, Zeit, Jobkosten, POCO-Steuer und Marktgebühren ab.
- Abweichungen werden als Daten- oder Formelproblem sichtbar gemacht.
- Eine Spieländerung erzeugt ein neues datiertes Regelprofil; semantische Formeländerungen erhöhen die Katalogversion.
- Bereits gespeicherte Pläne bleiben mit ihrer ursprünglichen Version reproduzierbar.

## 12. Offizielle Referenzen

- [CCP: EVE Industry – ME, TE und Rundung](https://www.eveonline.com/news/view/eve-industry-all-you-want-to-know)
- [CCP: Industry-Berechnungen für Drittentwickler](https://www.eveonline.com/news/view/industry-3rd-party-developers)
- [CCP: Viridian-Steuerreform und Industry Job Fee](https://www.eveonline.com/news/view/viridian-expansion-notes)
- [EVE Support: Broker Fee and Sales Tax](https://support.eveonline.com/hc/en-us/articles/203218962-Broker-Fee-and-Sales-Tax)
- [EVE Support: Buy and Sell Orders](https://support.eveonline.com/hc/en-us/articles/203218932-Buy-and-Sell-Orders)
- [EVE Support: Customs Offices](https://support.eveonline.com/hc/en-us/articles/203269921-Customs-Offices)
- [EVE Support: Planetary Interaction](https://support.eveonline.com/hc/en-us/articles/203269871-Planetary-Interaction)
- [CCP: Highsec-POCO-Steuern und PI-Steuerbasen](https://www.eveonline.com/news/view/player-owned-customs-offices-in-hi-sec)
