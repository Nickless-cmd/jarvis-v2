# Samlet status — hvad er lukket, hvad mangler

Dato: 3/11-2026. Grundlag: ni pastes fra samtalen (16:10–18:16) gennemgået mod
koden og den levende DB. Hver linje er enten **målt** (observeret data) eller
**udledt** (kodeanalyse). Ingen linje er «forventet».

Formålet er at svare på ét spørgsmål: hvad står stadig åbent efter dagens arbejde?

---

## Lukket — verificeret

| # | Hvad | Bevis |
|---|---|---|
| 1 | **Tick-scoren læser `tick_result`, ikke `events`** | `agent_self_evaluation.py:49-96` — spor-leddet fjernet; alle fire led læses af slagets eget svar |
| 2 | **Definition B: confidence = styrken af retningen** | commit `7a0d33b50`; `gut_gate` kræver `retning == "proceed" and conf >= threshold` |
| 3 | **Counterfactual måler med samme regel** | commit `220d32455`; `caution` 0,70 giver nu RED/RED, delta 0 |
| 4 | **System-badges i Sind** | 72 systemer + 20 overflader i alle tre undertabs, målt i payloaden |
| 5 | **caution-vetoret er dokumenteret som politik** | test + fravalg i `2026-11-03-confidence-definition.md` |

---

## Åbent kl. 18:16 — det oprindelige billede

> **Læs dette som historik, ikke som nutid.** Sektionen er hvad der var åbent da
> gennemgangen blev skrevet. Siden da er A2, A6, A6b, A3, A1, A4, B1, C2, C3 og
> D1 lukket — se de fire «Lukket»-sektioner nedenfor. Det der stadig står åbent
> er opsummeret i **«Stadig åbent efter fase D»** i bunden af dokumentet.

### A. Gut-kæden (syv huller, i rækkefølge)

**A1. Preflight sender ingen observationer.**
`preflight_gut_gate` kalder `derive_gut_signal(task_description=…)` — intet
andet. `confidence=0,5`, `error=0`, `success=0` altid. Målt: tre vidt
forskellige opgaver giver identisk 0,61.

**A2. Preflight gemmer ikke sin hunch.**
`_on_started` i `gut_calibration.py` kalder `derive_gut_signal` **igen** med
`payload.get("focus")`. To beregninger, to input, den ene kasseres. Verificeret:
`preflight_gut_gate` skriver intet til state.

**A3. Afvisningen registreres — men den når ikke kalibreringen.**

Rettet 3/11 efter GPT's indvending, som holdt i kilden: `preflight_gut_gate`
skriver faktisk `record_private("cognition", "gut_gate_withhold", …)` ved en
afvisning (`gut_engine.py:330`), og `gut_gate` tæller sin afgørelse i
counterfactual-ledgeren. Min tidligere formulering «logges ikke» var forkert.

Det præcise billede, målt:

| Lag | Findes? | Når kalibreringen? |
|---|---|---|
| `record_private("gut_gate_withhold")` → trace + tidsserie | ja, i koden | **nej** |
| `gate_verdict_ledger` → `gate_verdict_counts` (persisteret) | ja | **nej** |
| `gut_calibration` (lytter på started/completed/failed/interrupted) | — | kun de tilladte |

Målt i DB: `gut_gate_withhold` findes **nul steder**. Begge nerves står på
558 green, sidst 16:33:43 — gaten har aldrig afvist, så registreringen er
aldrig blevet udløst.

**Og den dybere pointe (GPT, 3/11):** at registrere en afvisning beviser ikke at
afvisningen var rigtig. Et afvist run har intet observeret udfald — vi ved ikke
om det ville være lykkedes. Derfor skal tre lag holdes adskilt:

- **Beslutningen:** tillod eller afviste gaten opgaven?
- **Forudsigelsen:** hvad forventede den ville ske?
- **Udfaldet:** hvad skete der faktisk, hvis opgaven blev udført?

**Præciseret (GPT, 3/11):** kalibrering kræver en forudsigelse der er **låst før
handlingen**, sammenholdt med et senere observeret udfald. Et udfald alene
fortæller ikke om forudsigelsen var god — og i dag er forudsigelsen slet ikke
låst før handlingen: `_on_started` dannes ved `runtime.autonomous_run_started`,
altså *efter* runnet er begyndt, fra `payload.get("focus")` — et andet input end
gaten brugte (se A2).

Kun forudsigelse + udfald tilsammen kan kalibrere maven. En afvisning kan
derfor aldrig blive et sandhedsbevis for sig selv — kun et datapunkt om gatens
adfærd.

**A4. Kalibreringen er stadig selvbekræftende.**
`record_gut_outcome` gør `predicted_success = (hunch == "proceed")`. Hunch er
altid `proceed` i produktion → 4292/4301 måler run-succesraten, ikke om maven
havde ret. Definition B fjerner inversionen, men ikke cirklen.

**A5. Tærsklen er stadig 0,30 og bør ikke røres endnu.**
Hæves den før A1–A4, afvises alle opgaver blot **ens**.

**A6. Backstop kan overkøre gatens nej — sporet er aggregeret, ikke per-run.**
`preflight_gut_gate` har et blokerings-budget (`_MAX_BLOK_PER_TIME = 3` pr.
rullende time). Er det brugt, slipper runnet igennem med `backstop: True` —
også når gaten sagde nej. Målt:

- **Der FINDES et aggregeret spor.** `_record_backstop` (`gut_engine.py:290`)
  skriver `gut_gate_backstop`/`yellow` til den persistente ledger. En tidligere
  formulering her kaldte overkørslen «usynlig» — det var for stærkt.
- **Men sporet har nul rækker** i `gate_verdict_counts`, ligesom
  `gut_gate_withhold`. Ingen af stierne er nogensinde udløst. Sporet er kodet,
  ikke observeret.
- **Det sammenkædes ikke med det enkelte run.** `backstop`-flaget læses ingen
  steder: begge produktionskaldesteder (`autonomous_stream_run.py:97`,
  `visible_autonomous_run.py:276`) bruger `preflight_allows()`, som kun
  returnerer `bool` og kaster `confidence`, `hunch` og `backstop` væk. Bagefter
  kan man tælle *at* der blev overkørt — ikke *hvilket* run.
- **Budgettet er 3 pr. rullende time pr. proceslevetid**, ikke ubegrænset.
  `_blok_tider` er en in-memory modul-global liste (`gut_engine.py:279`), så
  tælleren nulstilles ved genstart. Under normal drift er grænsen reel;
  gentagne genstarter kan omgå den.

**A6b. `blokeret` tæller gatens nej — ikke faktisk stoppede runs.**
`build_gut_counterfactual_surface` beregner `blokeret = total - pass_med`
(`gut_engine.py:412`), hvor `pass_med` er *gatens* grønne. En backstop-
overkørsel står derfor som «stoppet» i samme flade, mens `backstop_overkoersler`
ved siden af viser den som «sluppet igennem». Summary-linjen kan derfor sige
«4 stoppet, 1 sluppet igennem af bagkanten» om fire runs hvor kun tre blev
stoppet. Matematisk korrekt for gate-nej, forkert som beskrivelse af
handlingen. Ingen faktiske overkørsler er observeret (0 rækker), så fejlen er
påvist i koden, ikke i driften.

**Udvidet 3/11 (GPT's tredje indvending, verificeret i kilden):** `blokeret`
blander **tre** forhold, ikke to. `_record_counterfactual` kaldes i `gut_gate`
**før** `if mode == "on"` (`gut_engine.py:230` mod `:253`), så i `shadow`-mode
registreres en simuleret afvisning som `red` — og gaten returnerer alligevel
`True`. Derfor:

| Hændelse | Gate-tælling | Faktisk handling |
|---|---|---|
| `on`, gaten afviser | RED | blokeret |
| `on`, backstop overkører | RED | **tilladt** |
| `shadow`, gaten ville afvise | RED | **tilladt** |

At trække `backstop` fra er derfor **nødvendigt, men ikke tilstrækkeligt** — den
tredje række har ingen bagkant at trække fra.

**Og den strukturelle grund, målt i kilden:** akkumulatoren i
`gate_verdict_ledger.py` er nøglet på `(nerve, decision)`. `mode` findes **ikke
som dimension** — den lever kun som fri tekst i `last_reason`, som overskrives
ved hvert nyt kald. `gate_verdict_counts` har kolonnerne `nerve, cluster,
decision, count, last_ts, last_reason`; ingen mode-kolonne. Så de tre forhold er
smeltet sammen **før** de når tabellen, og informationen kan ikke gendannes
bagefter. Det er samme fejlform som resten af dagen: data registreres i et
fritekstfelt og går tabt i den aggregering der læses.

Rettelsen er at gøre `mode` til en **dimension i ledgerens nøgle** — `mode` er
kendt på registreringstidspunktet, så den kan indgå. Men `backstop` kan **ikke**:
den beslutning eksisterer ikke endnu. Målt rækkefølge i `preflight_gut_gate`
(`gut_engine.py:300-341`): `derive_gut_signal` → `gut_gate(...)` (registrerer
counterfactual inde i sig selv) → `if tillad: return` → `if
_blok_budget_brugt(): _record_backstop(...)`. Altså registreres counterfactual
**før** backstop-vurderingen findes (GPT, 3/11 — han havde ret, og min første
formulering var forkert).

`backstop` skal derfor være en **særskilt hændelse efter** den endelige
beslutning — ikke et felt i den første nøgle. `_record_backstop` er allerede en
separat registrering; det der mangler er at den kobles til counterfactual-tællingen
og til det enkelte run. Ellers flyttes fejlen blot fra én tæller til en anden.

Konsekvens: udfaldet kalibrerer den hunch `_on_started` dannede — ikke den
gatens anbefaling backstop overkørte.

**De fire størrelser der skal holdes adskilt** (GPT, 3/11):

| Størrelse | Hvad den fortæller | Findes adskilt i dag? |
|---|---|---|
| Forudsigelse | hvad forventede Jarvis? | nej — dannes efter start, fra andet input |
| Gate-vurdering | hvad anbefalede intuitionen? | nej — kasseres af `preflight_allows` |
| Endelig beslutning | hvad fik lov at ske? | nej — `backstop`-flaget læses ikke |
| Observeret udfald | hvad skete der bagefter? | ja |

Først når de fire er kædet sammen, kan man måle om intuitionen **forbedrer**
beslutningerne — ikke bare om den svarer.

### B. Tick-dispatchen

**B1. `tick_dispatched` er historisk.**
Målt i `heartbeat_runtime_ticks`: 1.155 rækker, men **seneste 09:49 i dag** —
7,5 timer siden. Alle seks seneste ticks er `productive_idle`. Der er altså
ingen dispatch at evaluere nyhed på.

### C. Forbrug vs. produktion

**C1. Niveau 2 er umålt.**
GPT's tre niveauer: produceret / tilgængeligt / virksomt. Målt: `prompt_contract.py`
nævner **2 af 72** systemnavne; `heartbeat_runtime.py` nævner 71 — men det er
**produktion**, ikke forbrug. Det tidligere «60 forbundet / 12 isolerede» kunne
ikke reproduceres og er trukket tilbage.

**C2. Glemslen: to systemer med samme navn.**
`forgetting_curve` skriver til et JSON-register via `state_store`.
`get_relevant_experiential_memories` filtrerer `WHERE decay_score < 0,9` i
SQL-tabellen `cognitive_experiential_memories`. Ingen forbindelse. Et tredje
decay-system ligger i `associative_recall` med egen rate.

**C3. «300 afventende forslag» er sandt — for den forkerte kilde.**
`autonomous_work_daemon` læser `shared/runtime/autonomous_work_log.json`:
300 rækker, alle `pending`. Tabellen `autonomy_proposals` har 1 pending,
397 executed, 1.133 dismissed. To systemer, samme navn, ingen forbindelse.

**Forbehold (GPT, 3/11 — taget til efterretning):** C2 og C3 påviser
**forskellige kilder bag beslægtede statusbegreber**. De beviser ikke at nogen
af kilderne er død eller irrelevant. Det kræver at den konkrete forbrugskæde
følges til ende — og det er ikke gjort for nogen af de to.

### D. Ikke-målte påstande fra GPT

- ~~At reboot-awareness, silence-listener og continuity-kernel beskriver **samme**
  afbrydelse.~~ **MÅLT 3/11 kl. 19:0x — påstanden holder.** Se «Fase D» nedenfor.
- Om en systemværdi (ikke bare navnet) når ind i prompten. **Ikke gjort.**
  `prompt_contract.py` nævner 22 forekomster af «system», men det er ikke det
  samme som at en system*værdi* følges fra producent til prompt.
- Om der findes en opgave→værktøj-mapping. **Ikke gjort — og det er den samme
  mangel som A5's forudsætning.** `pattern_strength` giver data pr. værktøj, men
  ingen kobling fra en opgavebeskrivelse til hvilke værktøjer den vil bruge.

---

## Rækkefølgen der giver mening

1. **A2** — én forudsigelse hele vejen (mindst arbejde, størst ærlighed)
2. **A6 + A6b** — gør `mode` til **dimension i ledgerens nøgle** (i dag er nøglen
   `(nerve, decision)`, så shadow-simulerede og håndhævede afvisninger er smeltet
   sammen før tabellen). `backstop` kan **ikke** være i samme nøgle — den opstår
   efter `gut_gate` har returneret. Den skal registreres som en **særskilt
   hændelse efter** den endelige beslutning, koblet til runnet. Først da kan
   `blokeret` trække overkørslerne fra uden at flytte fejlen
3. **A3** — registrér afvisningen i kalibreringslivscyklussen, adskilt fra udfaldet
4. **A1** — kobl observationer på, målt i shadow-mode
5. **A4** — gør kalibreringen til noget der kan tage fejl
6. **A5** — først da en tærskel

A6 kommer før A3 fordi den rydder den samme livscyklus: uden et felt for
«gaten sagde nej, bagkanten sagde ja» kan A3's registrering ikke skelne en
ægte afvisning fra en overkørt.

C1–C3 er et selvstændigt spor: de er navnekollisioner og forbrugshuller, ikke
gut-kæden. De skal ikke blandes ind i den rækkefølge.

---

## Lukket 3/11-2026 (aften) — faserne A2 → A6 → A6b → A3 → A1 → A4

Rækkefølgen fra afsnittet ovenfor blev fulgt. Alt nedenstående er målt i den kørende
kode, ikke planlagt.

**Fase 1 — forudsigelsens livscyklus (A2 + A6 + A6b)**

| Hvad | Hvordan | Bevis |
|---|---|---|
| A2: én forudsigelse hele vejen | `preflight_gut_gate` lægger sin hunch + beslutning i en TTL-begrænset FIFO (`_stash_preflight_prediction`); `gut_calibration._on_started` tager den via `take_preflight_prediction()` | Målt: samme hunch og samme task-tekst før og efter; slotten tømmes ved forbrug |
| A6b: `mode` skelnes i ledgeren | Shadow-afgørelser tælles på deres EGEN nerve (`gut_gate_shadow`, `gut_gate_uden_bias_shadow`), fordi ledgerens nøgle er `(nerve, decision)` | Målt: akkumulatoren får seks nøgler hvor shadow står separat |
| A6: `blokeret` er faktisk stoppede runs | `blokeret = max(0, total − pass_med − backstop)`; `shadow_afgoerelser` vises særskilt | Målt: 3 nej − 2 overkørt = 1; uden backstop = 4 |

At gøre `mode` til en rigtig nøgle-dimension ville kræve en migrering af
`gate_verdict_counts`. Nerve-navnet løser samme problem reversibelt og uden skemaændring.

**Fase 2 — A3: afvisningen som beslutning**

`_record_withheld_decision` skriver nu `gut_gate_withheld`/`withheld` til ledgeren, adskilt
fra de evaluerede udfald. `build_gut_surface` viser de tre lag side om side:

```
Calibration: 1.00 (4292/4301 correct); 4 afvist (intet udfald), 1 overkørt af bagkanten
```

En afvisning kan aldrig kalibrere maven — den har intet udfald at måles mod.

**Fase 3 — A1: ægte observationer**

`_recent_tick_signals()` læser `blocked` / `ok`+`completed` fra `heartbeat_runtime_ticks`
(24 t, 60 s cache) og sender dem til `derive_gut_signal`. Målt 3/11 kl. 18:5x:
**23 blocked mod 270 ok/completed**.

Effekt, målt på samme opgave:

| Input | hunch | confidence |
|---|---|---|
| Før: hårdkodede nuller | `proceed` | 0,61 |
| Nu: ægte observationer | **`caution`** | 0,59 |

**Grænse, som skal stå her:** det er GLOBALE observationer, ikke opgavespecifikke.
`confidence` er stadig 0,5, fordi der ikke findes en mapping fra `task_description` til
hvilke værktøjer opgaven vil bruge. Gaten kan altså se *at* systemet har mange blokeringer
— ikke *om netop denne opgave* er risikabel.

**Fase 4 — A4: kalibreringen kan nu tage fejl**

Med `caution` mulig kan `record_gut_outcome` producere alle fire kombinationer:

| hunch | udfald | correct |
|---|---|---|
| proceed | completed | ✓ |
| proceed | failed | ✗ |
| caution | completed | **✗** |
| caution | failed | **✓** |

De to nederste rækker fandtes ikke før A1, fordi hunch altid var `proceed`.

**Driftsændring foretaget:** `central_gut_consumer_mode` er sat fra `on` til **`shadow`**.
Grund: med A1 kan hunch blive `caution`, og med `on` ville gaten afvise **alle** autonome
runs (målt: `gut_gate` returnerede `False` for den testede opgave). `shadow` bevarer den
reelle adfærd indtil nu — ingen blokering — mens den måler. Reversibelt: sæt flaget til
`on` når data er set.

**Tests:** 54 i gut-suiten (46 → 54), 68 i det bredere gut/ledger/adaptation-batteri.

**Stadig åbent:** A5 (tærsklen — røres ikke før der er set shadow-data), og den
opgave→værktøj-mapping der skal gøre observationerne opgavespecifikke. B1, C2 og C3
blev lukket senere samme aften (næste sektion); C1 er stadig umålt.

---

## Lukket 3/11-2026 (aften, faser B + C) — B1, C2, C3

### B1 — tick-dispatch var ikke «historisk», den var brudt

Den oprindelige formulering var forkert. `tick_dispatched` havde **128
forekomster i døgnet**, ikke nul — men de stoppede brat.

**Målt:** dispatch kørte hvert 16. minut fra 00:08 til **09:49**, derefter intet.
Siden da er hvert eneste tik `productive_idle` (12 i træk målt).

**Rod-årsag, med tidsstempel:** `long_horizon_goals` har 8 `abandoned` + 7
`completed` og **nul aktive**. Det sidste aktive mål blev `abandoned`
**09:50:27** — mindre end et minut efter den sidste dispatch.

`_identify_priorities` tilføjede `advance_goals` **kun** hvis `active_goals` var
ikke-tom. Uden mål → tom prioritetsliste → `productive_idle`. Og koden antog det
modsatte: kommentaren ved `advance_goals`-grenen sagde at `active_goals` «altid
er ikke-tom (ét aktivt mål)». Den antagelse holdt indtil målene løb ud — så faldt
hele dispatch-stien tavst tilbage til tomgang, og den gren der skulle foreslå
arbejde blev uopnåelig.

**Rettelse:** et tomt mål-loft giver nu prioriteten `goal_starvation`. Et tomt
mål-loft er et signal om at der skal handles, ikke bevis på at der intet er at
lave. Kommentaren der bar den falske antagelse er rettet til at sige hvad der
faktisk skete.

**Målt efter:** tomt mål-loft → `['goal_starvation']` → dispatch. Levende
sansning giver nu `['verify_recent_mutations', 'goal_starvation']`.

**BEVIST I DRIFT kl. 18:22 UTC.** Efter otte timers `productive_idle` kom der
**to dispatches i træk** — `18:16:03` og `18:18:02` — begge med
`action_type=tick_dispatched`, og det første blev efterfulgt af
`run_mirror_reflection` med et ægte resultat kl. `18:16:05`.
`heartbeat_runtime_state` står på `last_result: tick_dispatched`,
`scheduler_active: 1`, trigger `self-wakeup-fire`. Og `long_horizon_goals` har
**stadig nul aktive mål** (8 abandoned, 7 completed) — så det var
`goal_starvation` der udløste dispatch, ikke et nyt mål. Det er præcis den
betingelse rettelsen skulle fange.

### C2 — glemsels-filteret var en no-op

`get_relevant_experiential_memories` filtrerede på `WHERE decay_score < 0.9` i
`cognitive_experiential_memories`. Kolonnen skrives **kun ét sted** i hele koden
(`db_experiential_memory.py:71`), og den sætter den til `0.0` ved forstærkning.

**Målt:** 9 rækker, **nul** med `decay_score > 0`, max 0,0. Filteret matchede
hver eneste række og udelukkede intet — det påstod en glemsel der ikke fandtes i
den tabel.

Den ægte henfald bor i `forgetting_curve`-registret: 500 poster, **301 faldet**
(≥ 0,9), nøglet på `sha256(focus|summary)[:16]` med `content_preview` som første
100 tegn.

**Rettelse:** recall læser nu registeret og bruger den ægte decay. Broen er
`content_preview` matchet mod rækkens egen tekst; en post med decay ≥ 0,9
udelades for alvor, og den returnerede `decay_score` er registerets tal.

**Forbehold, målt:** **0 af 9** SQL-rækker matcher et register-preview. De to
systemer sporer helt forskellige erindringer — registeret har content-hashes,
tabellen har `exp-`-id'er. Rettelsen er korrekt wiring, men udelukker **intet i
praksis** før noget begynder at registrere de samme erindringer i begge.
Det ændrer ikke konklusionen: filteret løj før, det gør det ikke nu.

### C3 — 300 forslag uden forbruger

`autonomous_work_daemon.tick` kaldes ved hvert heartbeat og skriver forslag ind i
`autonomous_work_log.json`. `resolve_proposal` findes og virker, men kaldes kun
manuelt — der er **ingen automatisk forbruger**.

**Målt:** 300 poster (loggens loft), **alle** `pending`, ældste 28/10 (6 dage).
`_save` trimmer til de nyeste 300, så gamle forslag blev ikke afvist — de blev
**stille kasseret** ved rotation, mens fladen meldte «300 afventende af 300
total» som om det var en travl kø.

**Rettelse:** to dele.

1. `tick` standser når køen er fuld af ubehandlede forslag (`queue-full-unconsumed`).
   Det er ærligere at sige «jeg har 300 ubesvarede og laver ikke flere» end at
   blive ved med at skrive dem ind i en roterende fil der skjuler dem.
2. Fladen siger det højt: *«Køen er FULD og uforbrugt: 300 afventende, ældste 6
   dage. Intet forslag er behandlet.»* Og en ikke-fuld kø viser også den ældstes
   alder, fordi alderen er det der afslører om køen behandles eller bare fyldes.

**Ikke løst (på dette tidspunkt):** der var stadig ingen forbruger. Rettelsen
standsede kun produktionen og gjorde tilstanden synlig. **Forbrugeren blev bygget
senere samme aften — se «fase C3» nederst.**

### Teste

- `tests/test_heartbeat_phases.py` — 27 grønne; `test_priorities_empty_when_calm`
  erstattet af to der udtrykker den nye semantik (rolig *med* mål → `advance_goals`,
  rolig *uden* mål → `goal_starvation`). Den gamle test håndhævede præcis den
  antagelse der brød.
- `tests/test_autonomous_work_daemon.py` — ny, 4 vagter: kø-grænse, produktion
  under loftet, fuld-kø-rapportering, alders-rapportering.
- `tests/test_experiential_decay_wiring.py` — ny, 4 vagter: faldet post udelades,
  decay kommer fra registeret, usporet række får 0, manglende register gør ikke
  recall blind.
- Bredt batteri (heartbeat/forgetting/experiential/autonomous/gut): **647 grønne**.
  Én fejl er netværksvagten der stoppede en test der ville kalde en rigtig model —
  miljømæssig, ikke fra disse ændringer.

---

## Lukket 3/11-2026 (aften, fase D) — D1 målt

D-sporet var det eneste der stod helt urørt. Det første af de tre punkter er nu
målt, og resultatet er skarpere end «de tre er enige».

### D1 — de tre kilder beskriver samme afbrydelse (påstanden holder, med en nuance)

| Kilde | Felt | Værdi |
|---|---|---|
| `reboot_markers.json` | `last_boot_event` | `reboot.unexpected`, `downtime_seconds: 904`, `graceful: false` |
| | `at` | **2026-11-03T17:59:14.409630+00:00** |
| | `prev_pid` → `current_pid` | 1665026 → 1683093 |
| `silence_listener.json` | post | `duration: 904.5`, `texture: "fyldt"` |
| | `timestamp` | **2026-11-03T17:59:14.909182+00:00** |
| `continuity_kernel.json` | `last_tick_at` | **2026-11-03T18:03:52.197640+00:00** |
| | `tick_count` | 6762 |
| | `last_gap_seconds` | **0.0487** |

**Målt:** reboot-awareness og silence-listener mødes på **samme sekund**
(17:59:14, adskilt af 0,5 s) med **samme varighed** (904 s). To uafhængige
systemer har registreret samme afbrydelse med samme tal. GPT's påstand holder
for deres vedkommende.

**Nuancen der skal siges højt:** continuity-kernen beskriver **ikke** afbrydelsen
— den beskriver **genopstarten**. `last_tick_at` ligger 4 minutter efter, og
`last_gap_seconds` er **0,05 s**, altså så den slet ikke nedetiden. Det er ikke
en fejl i continuity-kernen (den måler gap mellem ticks i sin egen levetid), men
det betyder at den **ikke kan bruges som vidne om nedetid**. Skal man måle
afbrydelser, er `reboot_markers` og `silence_listener` kilderne; continuity-kernen
er blind for dem.

Det gør D1 færdig: påstanden er **bekræftet for to af tre kilder**, og den
tredje er målt til at være strukturelt ude af stand til at bekræfte den.

### B1's rettelse — bevist i drift

**Målt kl. 18:22 UTC.** Dette afsnit hed tidligere «ikke bevist i drift endnu»,
og det var sandt kl. 18:09:14, hvor der var nul ticks efter genstartet. Det er
ikke sandt længere.

Forløbet var: seneste tick før genstartet `18:03:50`, altså **før** både commit
(18:03:30) og processtart (18:04:23). Scheduleren stod korrekt `active` med
`next_tick_at 18:18:52`. Så kom `18:16:03` — `tick_dispatched` — og `18:18:02`
igen, begge efter den nye kode var levende.

Det er den ægte prøve, og den faldt ud som rettelsen forudsagde: dispatch skete
**fordi** mål-loftet er tomt, ikke på trods af det.

### Stadig åbent efter fase D

- **A5** — tærsklen. Røres ikke før der er set nok shadow-data. Blokeringen var
  strukturel indtil kl. 18:36:25 UTC, hvor gaten blev kaldt for første gang siden
  16:33. **Ventetiden løber nu.** Se «A5's kæde VAR brudt — den virker nu» nedenfor.
- **D2** — om en system*værdi* (ikke bare navnet) når ind i prompten. Ikke fulgt
  fra producent til prompt for nogen værdi.
- **C1** — niveau 2 (virksomt) er stadig umålt.
- **C3's forbruger** — de 300 forslag er stadig ubehandlede; produktionen er
  standset og køen gjort synlig, intet mere. → **LUKKET 3/11 kl. 19:28.** Se
  «C3-forbrugeren» nedenfor.
- **C2's overlap** — 0 af 9 rækker matcher registeret; korrekt wiring, ingen
  praktisk effekt endnu.

**Lukket siden:** opgave→værktøj-mappingen var det største punkt her og er nu
bygget — se «A7» nedenfor.

---

## Lukket 3/11-2026 (aften, fase A7) — opgave → værktøj-mappingen

Dette var dokumentets «ægte mangel»: `confidence` var 0,5 for enhver opgave, fordi
`task_description` kun blev klippet til en label. Nu findes koblingen.

### Hvad der blev målt FØR den blev bygget

To nærliggende veje blev målt og forkastet — det er grunden til at løsningen er kurateret:

| Vej | Måling | Konklusion |
|---|---|---|
| `tool_embeddings.top_k_similar()` | 0,09–0,19 s, men «læs logfilen og find fejlen» → `phone_location`; simulariteter i et snævert 0,60–0,69-bånd | **Ubrugelig.** Modellen kan ikke skelne; indekset har 800 poster mod 514 katalognavne |
| `heartbeat_runtime_ticks` som indlært historik | `action_type` findes, men **ikke hvilke værktøjer**; `action_summary` er for de fleste `productive_idle` | **Umulig** med de data der findes |
| `AUTONOMOUS_TOOLS` som risiko-akse | 414 af 514 katalognavne står udenfor, inkl. harmløse `analyze_image` | Det er en **tilladelses**-akse, ikke en risiko-akse |

### Hvad den gør

`core/services/task_tool_mapping.py` klassificerer opgavens tekst i tre tiers —
`read` / `mutate` / `irreversible` — og giver en `confidence_delta` (+0,05 / −0,05 /
−0,15). Ukendt tekst giver `unknown` med delta 0,0, ikke en gættet neutralværdi.

Koblet i `derive_gut_signal`: delta'et justerer den RÅ confidence (før grenene), og en
`irreversible` opgave tvinger `hunch = "caution"`.

**Målt effekt** (`recent_error_count=0`, altså sund drift — den svære prøve):

| Opgave | Tier | hunch |
|---|---|---|
| kritisk migration af produktionsdatabase | irreversible | **caution** |
| deploy til produktion | irreversible | **caution** |
| opret en ny testfil | mutate | proceed |
| læs logfilen og find fejlen | read | proceed |

Før denne ændring blev en migration klassificeret som `proceed` når blot døgnet havde
haft nul fejl — den globale fejlrate afgjorde retningen, ikke opgaven.

### Grænsen, som skal siges højt

**Der er BEVIDST ingen kontinuert skalering af styrken.** Jeg prøvede
`adjusted_confidence * (confidence / 0.5)` og målte den: den gav fire opgaver fire
forskellige tal — men tallene var **opdigtede**. Der findes ingen data der siger at en
læseopgave er 0,66 sikker og en skriveopgave 0,52; det var multiplikatoren der opfandt
dem, og ved rå 0,1 gjorde den styrken næsten nul. Den blev fjernet igen.

Opgavespecificiteten bæres derfor af **retningen** (caution/proceed) og af delta'et på
den rå confidence, som flytter grenvalget ved 0,6 og 0,3 — ikke af en skala jeg ikke kan
forsvare. Det er den ærlige grænse: jeg ved **om** opgaven er farlig, ikke **hvor** farlig
den er på en kontinuert skala.

Klassifikationen er desuden en heuristik over *teksten*, ikke en forudsigelse af hvilke
værktøjer runnet faktisk kalder. Den kan narres af en opgavebeskrivelse der lyder harmløs.
A5 (tærsklen) er stadig urørt.

### En test der ikke testede det den hed

`test_preflight_forudsigelse_overlever_til_kalibrering` forbrugte slotten med
`take_preflight_prediction()` **før** den kaldte `_on_started` — så der var intet at tage,
og `_on_started` regnede en ny. Testen var kun grøn fordi begge sider tilfældigt gav
`proceed`. Nu lægges en frisk slot, og fokus-teksten er bevidst i `proceed`-klassen, så
testen faktisk beviser at slotten bruges.

**Tests:** 54 i gut-suiten (54 → 54, én rettet), 17 nye i `test_task_tool_mapping.py`.

---

## Lukket 3/11-2026 (aften, fase C3) — forbrugeren til de autonome forslag

### Det jeg troede, og det der faktisk stod

Jeg havde skrevet at der lå «300 forslag uden forbruger». Det var sandt, men det
skjulte den vigtigste detalje. **Målt før forbrugeren blev bygget: de 300 poster
var 7 unikke forslag.** 294 af dem var det SAMME research-forslag om
`seed-616b2bc12b`, fil'et hvert 15. minut i seks dage.

Årsagen var ikke iver. `_maybe_propose_research` tog
`list_seeds(status="maturing")[:1]` — **altid det første element i en usorteret
liste**. Der var 12 maturing seeds; de 11 andre blev aldrig foreslået. Planneren
var fastlåst, og loggen skjulte det ved at se travl ud.

Så der var to fejl, ikke én: ingen forbruger, og ingen deduplikering.

### Forbrugeren (`consume_proposals`)

Kaldes fra `tick()` **før** produktions-gaten — ellers kan en fuld kø af dubletter
låse daemonen fast for evigt. Den gør tre ting, og kun det den kan gøre ærligt:

1. **Deduplikere** — én repræsentant per `(type, grundlag)`, resten lukkes som
   `rejected` med en note der peger på repræsentanten.
2. **Verificere grundlaget** — findes seed'et? er det `withered`/`adopted`? ligger
   konsolideringsdagen mere end et døgn tilbage? blev handlingen allerede udført?
3. **Bevare det levende** — men nu som ÉT synligt forslag i stedet for 294.

Et grundlag der **ikke kan måles** (seed-butikken kaster) lukker ikke forslaget:
en manglende måling må ikke ligne en afvisning.

### `incubator_seed` var en løgn

`_maybe_nudge_incubator` kalder `ci_tick` på linjen **ovenover** `_file_proposal`.
Handlingen var altså udført *før* posten blev skrevet — `pending` var forkert fra
fødslen. Forbrugeren lukker dem som afvist med grunden «handlingen blev udført ved
oprettelsen».

### Målt på den levende log

| | Før | Efter |
|---|---|---|
| Poster | 300 | 300 |
| `pending` | 300 | **2** |
| Unikke | 7 | 2 |
| Lukket med begrundelse | 0 | **298** (293 dubletter + 5 forældede dags-konsolideringer) |

De to overlevende er ét research-forslag om et seed der stadig er `maturing`, og
ét `memory_consolidate` for i går. Fladen siger nu: *«2 afventende, 2 unikke,
ældste 6 dage. 298 behandlet.»* Backup af den oprindelige fil ligger ved siden af
(`autonomous_work_log.json.bak-20261103-1928`).

### Planneren blev frigjort

`_maybe_propose_research` vælger nu et maturing seed **uden** et ventende forslag.
Har alle 12 et forslag, svarer den `None` — det er ikke et signal om at producere
et mere, det er køen der venter på behandling.

### Den ærlige grænse

Forbrugeren **udfører ikke** netværksarbejde. Et `research`-forslag er en
beslutning om hvad der er værd at undersøge, ikke en rutine — et automatisk
`web_search` ville være en ekstern handling ingen har set. De to overlevende
forslag bliver derfor stående, nu synlige i prompten, og lukkes som forældede hvis
de passerer 14 dage.

**Tests:** 17 i `test_autonomous_work_daemon.py` (4 → 17), 114 i det berørte
batteri. Fixturen til kø-gaten stubbede `_grundlag_findes`, fordi de gamle
test-poster ingen seeds har — uden stubben målte testen forbrugeren i stedet for
gaten.

---

## Målt 3/11-2026 kl. 19:35 — A5's kæde VAR brudt. Den virker nu.

> **OPDATERET kl. 18:40 UTC (19:40 lokal).** Målingen nedenfor var sand kl. 19:35
> og er det ikke længere. Kl. **18:36:25 UTC** startede
> `autonomous-1ab9aff248864f929988d94001894318`, og gaten blev kaldt for første
> gang siden 16:33. Se «Kæden virker» nederst i dette afsnit.

Dokumentet har hidtil sagt at A5 «venter på shadow-data». Målingen viste noget
andet: **der kom ingen shadow-data, fordi der ikke kørte autonome runs.**

### Kæden, som den så ud kl. 19:35

```
tick-dispatch  →  ???  →  autonomt run  →  preflight_gut_gate  →  shadow-data  →  A5
     ✅ virker              ❌ ingen            ❌ nul kald
```

`preflight_gut_gate` kaldes **kun** fra `preflight_allows()`, og den kaldes kun
fra to steder: `autonomous_stream_run.py:97` og `visible_autonomous_run.py:276`.
Det er autonome run-startere — ikke tick-dispatchen.

### Hvad der blev målt kl. 19:35

| Måling | Resultat |
|---|---|
| `central_gut_consumer_mode` | `"shadow"` (sat 17:51) |
| `gate_verdict_counts`: `gut_gate` | 558 tællinger, **sidst 16:33:43**, `last_reason` = `mode=on conf=0.610` |
| `gut_gate_shadow` | **fandtes ikke** i tabellen |
| `gut_gate_withheld` | **fandtes ikke** i tabellen |
| `visible_runs` siden 17:00 | 14 runs — **alle** `lane=primary`, `capability_id=None` |
| `build_gut_surface()` | `evaluated=4301`, `withheld=0`, `backstop_overkoersler=0`, uændret siden 16:34 |

De 14 runs var **mine egne synlige ture** i samtalen, ikke autonome runs. Ingen af
dem går gennem gaten — hvilket er korrekt, for gaten er kun for autonome runs.

### Kæden virker — målt kl. 18:36:25 UTC

Kl. 18:36:25 startede et ægte autonomt run
(`autonomous-1ab9aff248864f929988d94001894318`), og gaten blev kaldt:

| Nerve | Afgørelse | `last_reason` |
|---|---|---|
| `gut_gate_shadow` | **red** | `mode=shadow conf=0.590 thr=0.30` |
| `gut_gate_uden_bias_shadow` | **red** | `hunch=caution conf=0.700 thr=0.30` |

Tre ting står klart af det ene datapunkt:

1. **Gaten blev kaldt.** `gut_gate_shadow` findes nu i tabellen — den gjorde ikke
   kl. 19:35. Årsag 1 og 3 fra listen ovenfor er dermed afgjort: starteren fyrer,
   og gaten fejler ikke stille.
2. **Den ville have afvist.** `red` betyder at `confidence` lå under tærsklen. I
   `shadow` slap runnet igennem alligevel — præcis den adfærd `shadow` skal have.
3. **Bias trak ned, ikke op.** Uden bias var `confidence` 0,700; med bias 0,590.
   Forskellen er 0,11, hvilket matcher `central_gut_proceed_bias` = 0,1109 målt
   samme dag. Bias sænker tilliden — den gør gaten mere forsigtig, ikke mindre.

**Det ændrer ikke A5's svar, men dets begrundelse.** A5 kan stadig ikke besvares
på ét datapunkt: tærsklen skal først justeres når der er set nok shadow-data til
at vide hvad gaten *ville* have gjort over tid. Forskellen er at ventetiden nu
løber — den var før uendelig.

### Hvad der ellers stadig står åbent

- **D2** — om en system*værdi* (ikke bare navnet) når ind i prompten. Målbar nu;
  ingen værdi er fulgt fra producent til prompt.
- **C1** — niveau 2 (virksomt). Målbar nu.
- **C2's overlap** — 0 af 9 rækker matcher registeret. Korrekt wiring, nul
  praktisk effekt indtil noget registrerer samme erindring i begge systemer.
- **C3's udøver** — bygget 3/11 kl. 19:4x. Se «Udøveren» nedenfor. Den udfører
  hvad policyen tillader og siger højt hvad den ikke må; den research-post der
  står tilbage er blokeret af `web_search`, ikke af mig.
- **Kalibreringens 0,998** — `4292/4301 correct` er målt mens hunch altid var
  `proceed`. Tallet måler run-succesraten, ikke om maven havde ret. Det bliver
  først meningsfuldt når `caution` faktisk forekommer i drift — hvilket kræver
  samme kæde som A5.

---

## Bygget 3/11-2026 kl. 19:4x — C3's udøver, og to forslag der aldrig ventede

Forbrugeren lukkede det døde. Men målt kl. 19:36 stod **to forslag stadig
`pending`** — deres grundlag levede, og ingen ville nogensinde gøre noget ved
dem. Forbrugeren var halvdelen af en mekanisme.

### Det jeg fandt, før jeg byggede den

Begge de to overlevende forslag viste sig **allerede udført ad andre veje**:

| Forslag | Målt | Konklusion |
|---|---|---|
| `memory_consolidate` for 2026-11-02 | `2026-11-02-daily.md` lå i `jarvis_brain/observation/` | kvittering, ikke arbejde |
| `research` på `seed-616b2bc12b` | `web_search` er **ikke** i `AUTONOMOUS_TOOLS` (målt: `False`) | kan ikke udføres autonomt |

Det er tredje gang samme mønster i dag: `incubator_seed` var også en kvittering
(`ci_tick` kaldes på linjen ovenover `_file_proposal`). `pending` var i alle tre
tilfælde en løgn om at noget ventede.

### Hvad udøveren gør

Den deler efter hvad policyen **faktisk** tillader, ikke efter hvad der ville
være pænt:

- **`memory_consolidate`** → intern. `synthesize_daily_journal(day)` skriver en
  lokal fil. Er journalen der allerede, lukkes forslaget som `completed` med
  stien som bevis — **uden** at kalde modellen forgæves.
- **`research`** → kræver `web_search`, som ikke er autonomt tilladt. Forslaget
  bliver `pending` med et `blocked_by`-felt der bærer den faktiske grund.

Et forslag hvis grundlag **ikke kan måles** lukkes ikke. En manglende udfører må
ikke ligne en afvisning.

### Målt på den ægte log

| | Før | Efter |
|---|---|---|
| `pending` | 2 | **1** |
| Udført | 0 | **1** (`completed`, journalen fandtes) |
| Blokeret med grund | 0 | **1** (`web_search` ikke autonomt tilladt) |

Fladen siger nu: *«1 afventende, 1 unikke, ældste 6 dage. 299 behandlet. 1 af dem
er BLOKERET (research) — de venter på en tilladelse, ikke på mig.»*

### Prompt-sektionen løj også

Målt: den skrev «Consolidate **today's** memory notes» om et forslag der gjaldt
**2. november**, og nævnte ét af to forslag. Titlen var skrevet den dag forslaget
blev fil'et; «today» blev aldrig oversat til en dato.

Nu bærer linjen den faktiske dato, viser op til tre forslag, og siger `BLOKERET`
med grunden når der er en.

### Bevis

- `test_autonomous_work_daemon.py`: **25 grønne** (17 → 25, otte nye vagter)
- Bredt batteri (autonomous/heartbeat/experiential/gut/forgetting): **126 grønne**

### Den ærlige grænse

Udøveren **løser ikke** hvem der kører et research-forslag. Den gør køen ærlig
og udfører det interne arbejde. Et research-forslag skal køres som et **synligt
run** — det er en beslutning om at handle i omverdenen, og den kræver at nogen
ser det. Det er ikke en mangel i udøveren; det er hvad policyen bestemmer.
