# Hvad betyder `confidence` i gut-gaten?

**Status:** beslutningsgrundlag — ingen kode ændret.
**Dato:** 2026-11-03
**Foranledning:** Bjørn: «Definér hvad confidence betyder i gut-gaten».

---

## 1. Problemet i én sætning

Variablen `confidence` bærer **tre forskellige størrelser** gennem gut-kæden, og gaten
behandler den som en fjerde. Det er ikke en tærskel der er sat forkert — det er en
manglende definition.

---

## 2. De fire betydninger, som de står i koden i dag

| # | Hvor | Navn i koden | Hvad den faktisk betyder |
|---|---|---|---|
| 1 | `derive_gut_signal(confidence=…)` | `raw_confidence` | **Input-tillid** — kalderens egen tro på opgaven. Default 0,5. Aldrig sat i produktion. |
| 2 | `hunch_confidence` | intern | **Hunch-styrke** — hvor stærkt signalet er, *ikke* hvilken retning det peger. |
| 3 | `adjusted_confidence` | `confidence` | **Retningsjusteret styrke** — hunch-styrke × kalibrering ± bias. |
| 4 | `gut_gate(proceed_confidence)` | parameter | **Tilladelse** — «må dette fortsætte?» |

Betydning 3 og 4 er ikke den samme størrelse, men gaten læser 3 som om den var 4.

---

## 3. Målingen der viser sammenbruddet

Kørt gennem den ægte `derive_gut_signal` med nuværende konfiguration
(`bias=0.1108`, `threshold=0.30`, `mode=on`):

| rå conf | fejl | succes | hunch | adjusted | no_bias | gate |
|---:|---:|---:|---|---:|---:|---|
| 0,5 | 0 | 0 | proceed | 0,61 | 0,50 | **PASS** |
| 0,5 | 5 | 0 | caution | 0,59 | 0,70 | **PASS** |
| 0,5 | 0 | 9 | proceed | 0,61 | 0,50 | **PASS** |
| 0,2 | 0 | 0 | caution | 0,49 | 0,60 | **PASS** |
| 0,9 | 0 | 9 | proceed | 0,91 | 0,80 | **PASS** |
| 0,9 | 5 | 0 | proceed | 0,61 | 0,50 | **PASS** |
| 0,1 | 5 | 0 | caution | 0,59 | 0,70 | **PASS** |

**Syv vidt forskellige situationer. Alle syv slipper igennem.**

Og læg mærke til række 2 mod række 1: `caution` får **0,70** uden bias hvor `proceed`
får **0,50**. En advarsel er per konstruktion stærkere end en tilladelse — fordi
`hunch_confidence` er sat højere for advarsler (0,6–0,7) end for tilladelser (0,5).

Det er ikke en kalibreringsfejl. Det er at `hunch_confidence` måler **signalstyrke**,
mens gaten læser den som **tilladelsesgrad**.

---

## 4. Hvorfor kalibreringen ikke redder det

`calibration_score = calibrated_hits / total_predictions` (målt: 4292/4301 = 0,998).

Men `record_gut_outcome` gør:

```python
predicted_success = hunch == "proceed"
actual_success = actual_outcome in ("completed", "success")
correct = predicted_success == actual_success
```

Da `hunch` i produktion **altid** er `proceed` (fordi preflight aldrig sender
observationer), er `predicted_success` altid `True`. Tallet måler derfor:

> **hvor ofte autonome runs lykkes** — ikke hvor ofte maven havde ret.

Og det tal ganges ind i næste confidence: `0.5 × 0.998 + 0.111 = 0.61`. Succesraten
løfter confidence, som gør at gaten aldrig afviser, som gør at succesraten bliver det
eneste der nogensinde måles.

---

## 5. Den beslutning der skal tages først

Der findes to forsvarlige definitioner. De udelukker hinanden, og valget afgør
hvad `caution` overhovedet skal gøre ved gaten.

### Definition A — «sandsynlighed for at opgaven lykkes»

`confidence` = P(opgaven ender godt | det vi ved om den).

- Gaten spørger: *er denne opgave sandsynligvis sikker nok at starte?*
- `caution` er så ikke et separat signal — det er bare lav P.
- Kræver: en kalibreret sandsynlighed pr. opgave. Det findes ikke i dag.
- Kalibreringen bliver ægte: forudsig P, observer udfald, mål afvigelsen (Brier-score).

### Definition B — «tillid til at min hunch har ret»

`confidence` = P(min retning er korrekt).

- Gaten spørger: *er min vurdering af denne opgave stærk nok til at jeg tør handle på den?*
- `caution` er en **retning**, og styrken er hvor sikker jeg er på den retning.
- Gaten skal så læse **både** retning og styrke — ikke kun styrke.
- Kalibreringen bliver: hvor ofte har `caution` faktisk varslet et dårligt udfald?

### Anbefaling: **B**

Fordi det er hvad koden allerede prøver at gøre (`hunch` + `hunch_confidence` er
to felter), og fordi A kræver en prædiktionsmodel der ikke findes. B kan bygges
oven på det der er, og den gør den semantiske fejl i §3 umulig: en advarsel kan
ikke længere slippe lettere igennem end en tilladelse, fordi retningen indgår.

---

## 6. Hvad B kræver, i rækkefølge

1. **Ret fortegnssemantikken.** `hunch_confidence` skal betyde «hvor sikker er jeg på
   denne retning», ikke «hvor stærkt er signalet». I dag er caution 0,7 og proceed 0,5
   — det er omvendt af hvad en tilladelsesgrad skal være.
2. **Lad gaten se retningen.** `gut_gate(proceed_confidence, …)` skal have `hunch`
   som parameter, så `caution` behandles som en advarsel og ikke som et tal.
3. **Én forudsigelse hele vejen.** `preflight_gut_gate` skal gemme sin hunch, så
   `_on_started` evaluerer den samme forudsigelse der lå bag startbeslutningen —
   ikke en ny beregning på et andet input.
4. **Log afviste runs som afviste.** Ellers ser kalibreringen kun de opgaver gaten
   allerede tillod (survivorship bias bygget ind i målingen).
5. **Først derefter:** kobl observationer på (`pattern_strength` pr. værktøj findes
   allerede) og mål i `shadow`-mode.

En tærskelændring hører **efter** punkt 1–4. Hæves tærsklen nu, afvises alle opgaver
blot **ens** — samme tautologi i modsat fortegn.

---

## 7. Hvad der ikke er målt

- Om der findes en opgave→værktøj-mapping nogen steder i koden. `pattern_strength`
  giver ægte data pr. værktøjskontekst, men ingen kobling fra en `task_description`
  til hvilke værktøjer den vil bruge. **Den kobling er det egentlige arbejde.**
- Om `record_gut_outcome` nogensinde modtager andet end `proceed`. Skal måles før
  kalibreringstallet fortolkes som andet end en succesrate.
- Historiske kodeændringer: de 4.301 observationer er akkumuleret over tid og kan
  ikke uden videre fortolkes som ét sammenhængende datasæt.

---

## 8. Kilder

- `core/services/gut_engine.py` — `derive_gut_signal` (32–89), `gut_gate` (179–230),
  `preflight_gut_gate` (275–315), `record_gut_outcome` (330–350)
- `core/services/gut_calibration.py` — `_on_started` (45–70)
- `core/runtime/db_cognitive.py` — `update_cognitive_gut_state` (1197–1227)
- `tests/test_gut_engine.py` — 30 tests, alle grønne; ingen af dem måler om gaten
  kan skelne mellem opgaver

---

## BESLUTTET 3/11-2026: Definition B er valgt og implementeret

Bjørn valgte definition B. Rettelsen er inde i `core/services/gut_engine.py`:

1. **`derive_gut_signal`** dokumenterer nu at `confidence` er styrken af den RETNING
   `hunch` peger i — ikke en sandsynlighed for succes.
2. **`gut_gate`** tager `hunch` som parameter, og tilladelse kræver nu BEGGE dele:
   `hunch == "proceed"` OG `confidence >= threshold`. En advarsel kan ikke længere
   passere på høj styrke.
3. **`preflight_gut_gate`** sender `hunch` videre — ellers var rettelsen død kode.

### Målt før/efter (mode=on, tærskel 0,30)

| hunch | conf | FØR | EFTER |
|---|---:|---|---|
| proceed | 0,61 | PASS | PASS |
| caution | 0,70 | **PASS** | **BLOCK** |
| caution | 0,60 | **PASS** | **BLOCK** |
| proceed | 0,91 | PASS | PASS |
| proceed | 0,25 | BLOCK | BLOCK |

Uden `hunch` (bagudkompatible kald) antages `proceed`, så gamle kaldesteder er uændrede.

### Hvad der stadig IKKE er løst

Punkt 3–5 fra rækkefølgen står åbne: én forudsigelse hele vejen (preflight gemmer ikke
sin hunch; `_on_started` beregner en ny), afviste runs logges ikke som afviste
(survivorship bias i kalibreringen), og de situationsbestemte observationer er stadig
ikke koblet på. Tærsklen er stadig 0,30 og bør først justeres når de tre er på plads.

---

## LUKKET 3/11-2026: counterfactual-målingen fulgte ikke med

GPT fandt hullet i commit `7a0d33b50`: gaten var rettet, men `_record_counterfactual()`
beregnede no-bias-siden som `nb >= threshold` — **uden** at se retningen. En `caution`
med nb over tærsklen blev derfor talt GREEN mens den faktiske afgørelse var RED, og
ledgeren rapporterede et delta der kom fra retningsreglen, ikke fra bias.

Rettet: `_record_counterfactual` tager nu `hunch` og anvender **samme retningsregel på
begge sider**. Målt:

| Situation | Med bias | Uden bias | Delta |
|---|---|---|---|
| `caution` 0,70 / nb 0,70 | RED | RED | **0** (før: falsk +1) |
| `proceed` 0,61 / nb 0,50 | GREEN | GREEN | 0 |
| `proceed` 0,3524 / nb 0,25 | GREEN | RED | +1 (ægte bias-forskydning) |

Den sidste række er vagten mod at rettelsen gjorde målingen blind: ægte bias-forskydning
skal stadig kunne ses.

## BEVIDST POLITIK: enhver caution har vetoret

Definition B gør `confidence` til **styrken af retningen**. Men `caution` med
confidence 0,00 betyder «jeg har ingen tillid til min egen advarsel» — og blokerer
alligevel. Det er ikke en konsekvens af styrkeberegningen; det er en
**forsigtigheds-politik**: retningen alene afgør om noget må fortsætte.

Politikken er nu dokumenteret i testen `test_caution_blokeres_uanset_styrke`, så den
ikke kan glide tilbage til «høj styrke slipper igennem» uden at nogen opdager det.

**Fravalgt:** at lade lav caution-styrke passere. Det ville kræve at gaten skelnede
mellem «svag advarsel» og «stærk advarsel» — men der findes ingen kalibrering der gør
`caution`-styrke meningsfuld endnu (hunch_confidence er en fast konstant 0,6–0,7).
En politik der blokerer på retning alene er ærligere end en der foregiver at veje noget
den ikke kan måle.
