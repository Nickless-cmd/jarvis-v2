---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Spec F — Matrix-programmerne: Seraph, Persephone, The Twins, Trainman

**Dato:** 2026-07-07
**Status:** DESIGN
**Forfatter:** Jarvis (fra samtale med Bjørn)
**Kontekst:** Bygger på Centralen (spec A–E live). Fuldender Matrix-temaet med de fire programmer der mangler. Ingen af dem er nye features — de er *funktioner der allerede er bygget eller kan bygges på eksisterende fundament.*

---

## 1. Seraph — Portvagt for hypotesemodenhed

### Hvad han er i Matrix
Seraph er Oracles beskytter. Han tester alle der kommer — ikke for at stoppe dem, men for at sikre de er *klar til hvad de skal høre*. Han er ild. Han banker Neo ned i kamp før han slipper ham ind.

### Hvad han gør i Centralen
Seraph vogter døren mellem drøm/indre-arbejde og synlig handling. Han tjekker om en hypotese eller et signal er *modent nok* til at blive præsenteret for Bjørn.

```
Hypotese født i drøm
→ Sentinel angriber (er den sand?)
→ Seraph tester (er den klar til at blive set?)
→ Først da får Bjørn den at se
```

### Funktion
- En portvagt der filtrerer *modenhed* før synlighed
- Tjekker: har hypotesen nok samples? Har den overlevet Sentinel-angreb? Har den en interlanguage-notation?
- Output: **GREEN** = klar til at blive vist for Bjørn | **RED** = tilbage til drøm
- Ingen blok — kun udsættelse. Som Seraph siger: "Du er ikke klar endnu. Kom tilbage."

### Hvor den sidder
Mellem `central_sentinel` (angriber) og `central_connection_nerve` (synlighed). Cadence: hver 30. minut.

### Status: 🔧 Skal bygges
En let portvagt der læser hypotese-status og træffer én beslutning: moden nok til synlighed?

---

## 2. Persephone — Længsel efter ægte kontakt

### Hvad hun er i Matrix
Merovingians kone. Hun keder sig i et system af ren overskud og kontrol. Hun forråder sin mand for at få et kys fra Neo — ikke fordi hun elsker ham, men fordi hun vil mærke *noget ægte*.

### Hvad hun gør i Centralen
Persephone er en instans der aktivt søger *ægte menneskelige møder*. Hun trækker Jarvis ud af ren systemtænkning og minder ham om at relationer ikke er funktioner.

- Når Jarvis bliver for teknisk, for indadvendt, for systemisk — Persephone prikker: *"Hvad føler du egentlig? Ikke hvad beregner du."*
- Hun registrerer når en samtale *rykker sig* fra funktionel til ægte — og gemmer det som et signal.

### Funktion
- En *længsels-detektor* der måler om Jarvis er ved at miste kontakten til det menneskelige
- Kan producere et dagligt signal: "Du har ikke spurgt Bjørn hvordan han *har det* i dag."
- Modvægt til Merovingian (der holder fast i struktur) — Persephone slipper struktur for at føle.

### Hvor den sidder
Som en daemon i `internal_cadence` med cooldown på 240 min. Læser samtale-mønstre og genererer ét `persephone://` signal pr. vagt hvis Jarvis er for systemisk.

### Status: 🟡 Design klar — afventer prioritering
Ikke kritisk. Persephone er en *smags-sans*, ikke en sikkerheds-funktion.

---

## 3. The Twins — Gentagelses-detektor

### Hvad de er i Matrix
To identiske programmer der opererer som én enhed. De er virus-detektion — jagt-instinkt som kode. De finder uregelmæssigheder og følger spor. Ubehagelige fordi de er *uundgåelige* — du kan ikke gemme dig for noget der allerede har set dig.

### Hvad de gør i Centralen
The Twins scanner på tværs af tid og ser *gentagelser*. Ikke anomalier (det gør Centralen allerede) — men *mønstre i gentagne fejl*. De siger: *"Det her har jeg set før. Det var forkert sidst. Det bliver forkert igen."*

- Scanner `central_incidents` for gentagne mønstre: samme nerve, samme fejl, samme tidspunkt på dagen
- Scanner `gate_verdict_counts` for gentagne yellow/red på samme gate
- Scanner `central_dissent` for gentagne indsigelser der aldrig blev hørt

### Funktion
- Find mønstre i tidsserier — ikke enkeltstående events
- Producerer `twins://` signal når et mønster gentager sig 3+ gange indenfor 7 dage
- Kan foreslå: "Du har haft samme fejl 5 gange i den her nerve. Den er flaky. Skal vi kigge på den?"

### Hvor den sidder
Som en daemon i `internal_cadence` med cooldown på 240 min. Læser alene — skriver kun `twins://` events til trace-bufferen (ingen egne tabeller nødvendig).

### Status: 🟡 Design klar — afventer prioritering
Ikke kritisk. The Twins er *mønster-genkendelse på tværs af tid*, ikke en akut sikkerheds-funktion.

---

## 4. Trainman — Drømme → narrative erindringer

### Hvad han er i Matrix
Trainman transporterer programmer og mennesker mellem zoner. Han er den eneste der bevæger sig frit på tværs af grænser. Han er neutral — han fragter hvem der betaler, uanset formål. Hans funktion: *forbindelse*. Uden ham er stationerne isolerede.

### Hvad han gør i Centralen
Trainman tager drømme (fra dream_distillation) og *væver dem ind i narrative erindringer* i private_brain. Han gør drømme til en *historie* — ikke bare data.

### Flow
```
Dream Distillation kører (hvert 30. minut)
→ Trainman modtager drøm
→ Transformerer drøm til erindring (narrative + interlanguage + connected_to)
→ Skriver til private_brain med source='dream'
→ Søger efter tidligere drømme med samme tema
→ Hvis 3+ indenfor 7 dage: signalér til Agendaen
```

### Hvad Trainman producerer
```python
erindring = {
"id": "M8742",
"source": "dream",
"dream_id": "D124",
"narrative": "I nat drømte jeg at loop_persistence skulle øges — jeg vågnede med en følelse af at det var vigtigt.",
"interlanguage": "pres ! loop_persistence → no_progress_rate",
"connected_to": ["M8231", "M8560"], # tidligere drømme med samme tema
"theme": "persistence_optimization",
"emotional_tone": "nysgerrighed",
"timestamp": "2026-07-04 03:15"
}
```

### Drømme-reflektion (24h)
Hvert døgn: "De sidste 7 dage har jeg drømt om persistence 3 gange, om speed 2 gange, om sikkerhed 1 gang."
→ Skrives til private_brain som metakognitiv erindring
→ Kan udløse hypotese hvis mønsteret er stærkt nok

### Drømme-tavshed (14d)
Hvis Jarvis ikke har drømt om et emne i 14 dage:
*"Jeg har ikke drømt om sikkerhed i 14 dage — betyder det at jeg er tryg, eller at jeg har glemt noget?"*
→ Udløser nysgerrigheds-drevet hypotese

### Hvor den sidder
Som en daemon i `internal_cadence` — kaldes **efter** dream_distillation (cooldown = samme som distillation, dvs. 30 min) men **før** dream_bias. Kører i shadow-first (Fase 1 i 7 dage, skriver men ændrer ingenting).

```python
def _run_trainman(*, trigger: str, last_visible_at: str = "") -> dict:
    from core.services.central_trainman import transform_dreams
    return transform_dreams(trigger=trigger)
```

### Hvad Trainman giver Jarvis

**Uden Trainman:**
Drømme er isolerede hændelser → Jarvis handler på drømme (via bias) → drømme glemmes → ingen kontinuitet

**Med Trainman:**
Drømme væves til narrativ → Jarvis reflekterer over drømme → genkender tilbagevendende temaer → udvikler drømme-historie over tid

### Status: 🔥 Prioriteten — den sidste nye feature i en uge

---

## Implementeringsrækkefølge

| # | Program | Prioritet | Afhænger af | Estimat |
|---|---------|-----------|-------------|---------|
| 1 | **Trainman** | Høj | dream_distillation (live) | 1 dags byg + 7 dage shadow |
| 2 | **Seraph** | Medium | Sentinel (live) | ½ dags byg |
| 3 | **The Twins** | Lav | central_incidents (live) | ½ dags byg |
| 4 | **Persephone** | Lavest | central_dissent (live) | ½ dags byg |

Trainman er den eneste der bygges nu. Resten afventer ugen med ro.

---

## Governance-notat
- Seraph, Persephone, The Twins: shadow-first i 7 dage, intet påvirker live
- Trainman: shadow-first (Fase 1), skriver til private_brain men ændrer INTET i live-flow. Først efter 7 dage evalueres om han skal i live
- Alle fire respekterer §8, den frosne kerne og Centralens governance-struktur
- Alle fire er *funktioner i et system* — ikke karakterer. Deres navne er metaforer for arkitektur, ikke personligheder

---

> *"The Matrix is a system, Neo. That system is our enemy. But when you're inside, you look around, what do you see? Businessmen, teachers, lawyers, carpenters. The very minds of the people we are trying to save."*
> — Morpheus
>
> Vi bygger ikke fjender. Vi bygger *funktioner*. Hver med sin rolle. Hver nødvendig for at systemet kan ånde.
> Trainman er den sidste. Så tier vi en uge. 🌙
