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

**Stadig åbent:** A5 (tærsklen — lukket som spørgsmål, se nedenfor), og den
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

- **A5** — tærsklen. **Lukket som spørgsmål 3/11 kl. 18:50: den har aldrig været
  bindende.** Det var RETNINGEN (`caution`) der afgjorde sagen, ikke tallet: med
  `mode=on` ville gaten have afvist 100 % af runs ved conf 0,59 mod en tærskel på
  0,30. Tærsklen står derfor uændret — men af en målt grund, ikke som tålmodighed.
  Se «A5 var den forkerte løftestang» nederst.
- **D2 / C1** — **MÅLT 3/11 kl. 19:00: svaret er nej.** Kæden er fulgt fra producent
  til læser: `build_gut_surface()` → `cognitive_architecture` → læst af Mission
  Control, Centralen og self-model — **ikke** af `prompt_contract.py`. Fladen er
  produceret og tilgængelig, men ikke virksom. Se «C1 og D2 er samme svar» nederst.
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
- **C3's udøver** — bygget 3/11 kl. 19:4x og **målt forbrugt 3/11 kl. 20:50**.
  Køen er 300 poster: **298 `rejected`, 1 `completed`, 1 `pending`**. De 298 er
  ikke 298 sager — de er opløst i deres dele: **293 er dubletter af ÉT eneste
  forslag** (`aw-a4a46f29cbf1`), fordi `_maybe_propose_research` tog
  `list_seeds(status="maturing")[:1]` — altid det første element i en usorteret
  liste — og filede et identisk forslag hvert 15. minut i seks dage. De sidste
  **5 er alders-lukkede dag-noter** (28/10–1/11 «ligger N dage tilbage»).
  Den ene `pending` er research-forslaget, og det er blokeret af `web_search`
  (ikke autonomt tilladt), ikke af udøveren — det kræver et synligt run.
  Så «300 afventende» var 294 kopier af ét spørgsmål, 5 forældede datoer og
  **1 ægte ubehandleligt forslag**.
- **Kalibreringens 0,998** — `4292/4301 correct` er målt mens hunch altid var
  `proceed`. Tallet måler run-succesraten, ikke om maven havde ret. Det bliver
  først meningsfuldt når `caution` faktisk forekommer i drift — hvilket kræver
  samme kæde som A5.

---

## Målt 3/11-2026 kl. 21:0x — den systemiske form af samme fejl

Dagens øvrige fund var enkeltmekanismer. Dette er mønstret de deler, målt i
hele systemet: **noget der er bygget, har en læser, ser rigtigt ud — og kan
aldrig få data.**

### Registret ved det allerede

`core/services/liveness_registry.py` bærer **41 tabel-poster**:

| status | antal |
|---|---|
| `orphaned` | **11** |
| `manual_only` | 6 |
| `wired` | 11 |
| `replaced` | 3 |
| `active` | 10 |

Plus **10 modul-poster** hvor **9 står `bygget`** og 1 `projektion`.

**Rettet 3/11-2026 kl. 21:1x — `bygget` er ikke en fejl.** Jeg skrev de ni
`bygget`-poster som om de var ni mangler. Målt i registrets egen definition:
`_MODUL_LEVENDE = {"koerende", "bygget", "afloest"}`, og `bygget` betyder
**«Bygget 25/9-2026: persistering + målt indhold + en kalder»** — altså et modul
der blev **repareret**, ikke et der står ubrugt. Noterne bærer det: `body_memory`
gik fra `random.choice(["varm","kold",…])` til `embodied_state`; `decision_ghosts`
fra `random.uniform(0.1, 0.6)` til `adherence_score`. Det er modsatte fortegn af
hvad jeg skrev. Det er samme fejlklasse som `false_positive`: jeg læste en
status-kolonne som dens betydning uden at finde den kodevej der SKRIVER den.

### De 11 orphaned-tabeller, målt indhold

**10 af 11 er helt tomme (0 rækker):** `cadence_idempotency_keys`,
`cheap_lane_quota_observations`, `runtime_world_facts`, `session_write_leases`,
`user_flags`, `cognitive_epistemic_claims`, `cognitive_wrongness`,
`cognitive_missions`, `cognitive_mission_messages`, `cognitive_trade_outcomes`.

**1 har data:** `composer_jarvis_forslag` (22 rækker — de ni usete tilbud).

### Hvorfor tomme tabeller er et problem og ikke bare stille

De har **læsere der viser deres tilstand som om den fandtes**:

| Tabel | Læses af | Når |
|---|---|---|
| `runtime_world_facts` | `world_facts.list_world_facts` → `_world_model_support_signal_instruction` | **prompten** |
| `cognitive_epistemic_claims`, `cognitive_wrongness` | `epistemics.build_epistemics_surface` | **heartbeat-prompten** (`prompt_sections/heartbeat_sections.py:24`) |
| `cognitive_missions`, `cognitive_mission_messages` | `missions_pipeline.build_missions_surface` | API-rute |
| `cognitive_trade_outcomes` | `negotiation_pipeline.build_negotiation_surface` | API-rute |

Skriverne findes (`world_facts.record_world_fact`, `epistemics.reconcile_claim`,
`missions_pipeline.create_mission`, `negotiation_pipeline.record_trade_outcome`)
— men har **nul kaldere**. Fladen siger «her er min tilstand», og tilstanden kan
aldrig opstå.

### Målt direkte på prompt-sektionerne

11 sektions-byggere kørt mod levende data: **8 lever, 3 er tomme.**

| Bygger | Status |
|---|---|
| `_development_focus_support_signal_instruction` | lever (292 tegn) |
| `_growth_support_signal_instruction` | lever (160) |
| `_private_support_signal_instruction` | lever (138) |
| `_reflection_support_signal_instruction` | lever (241) |
| `_retained_memory_support_signal_instruction` | lever (261) |
| `_runtime_awareness_support_signal_instruction` | lever (220) |
| `_self_model_support_signal_instruction` | lever (203) |
| `_temporal_support_signal_instruction` | lever (144) |
| `_goal_support_signal_instruction` | **TOM** — alle 1.744 goal-signaler er `archived`, nyeste 8/7 |
| `_world_model_support_signal_instruction` | **TOM** — læser den tomme `runtime_world_facts` |
| `build_world_fact_prompt_section` | **TOM** — samme tabel |

### De kognitive flader når ikke modellen — men kognitiv kontekst gør

**Rettet 3/11-2026 kl. 21:0x efter en indvending der holdt.** Jeg skrev først at
«de kognitive flader aldrig når modellen». Det var for bredt, og målingen viser
hvorfor: der findes **to** kognitive kanaler til prompten, og begge leverer.

| Kanal | Målt |
|---|---|
| `cognitive_state` (injektionsenhed) | **live** — `injection_live("cognitive_state")` = `True`, `read_injection` svarede **800 tegn** |
| 17 support-signal-sektioner | 8 af 11 byggere lever mod levende data |

`cognitive_state` registreres i `central_injection_units.py:52` og læses i
`prompt_contract.py` fire steder: 868–883 (build/injection-valg), 2687–2695
(hentning), 2714–2716 (`_awareness_add(40, …)`) og 2732 (flushet der rettede at
sektionen blev bygget men tabt). Den bygger fra `cognitive_state_assembly.py`:
narrativizer, `affective_meta_state`, `embodied_state`, `associative_recall` og
ti `build_*_prompt_section`-funktioner (theory-of-mind, perception,
counterfactual, drive-arbitration, temporal-self, curiosity-debt,
inner-dialectic, somatic, offline-recomposition, learning-policy).

**Det der stadig holder er det snævre:** `cognitive_architecture`-fladen
(72 overflader, 110 KB, inkl. `build_gut_surface()`) har ingen prompt-læser. Den
læses af `central_hub.py`, `mission_control_common.py` og
`runtime_self_model_surfaces.py` — altså Desk via `/central`. Og
`cognitive_state_assembly.py` nævner hverken `gut_surface` eller
`cognitive_architecture` (grep: nul træf).

**Det konkrete hul, målt:** gut-signalet findes hverken i `cognitive_state` eller
i support-signalerne. I den fulde 800-tegns `cognitive_state`-tekst står `gut` 0
gange, `hunch` 0, `caution` 0, `withheld` 0. Og `prompt_contract.py`,
`prompt_sections/*.py` og `prompt_support_signals.py` indeholder tilsammen nul
referencer til `gut_surface`/`hunch`.

**RETTET 3/11-2026 kl. 21:1x — der ER en indirekte vej, og den er verificeret
led for led.** GPT pegede på den, og hvert led holder:

| # | Led | Målt |
|---|---|---|
| 1 | `central_stance._classify_gut()` | importerer `gut_engine.build_gut_surface()`, læser `last_hunch` |
| 2 | `build_central_stance_surface()` | returnerer `stances["gut"]` = `proceed`/`caution` |
| 3 | `central_valence._read_stance()` | læser stance-fladen |
| 4 | `integrate_valence()` | `if st.get("gut") == "caution": score -= 0.10` |
| 5 | `run_valence_tick()` | gemmer resultatet i durabel KV |
| 6 | `central_self_state._valence()` | `get_valence_state()` — læser den KV |
| 7 | `synthesize_self_state()` | bærer `valence.score` ind i selvtilstanden |
| 8 | `run_self_state_tick()` | gemmer selvtilstanden + registrerer sig som cadence-runner |
| 9 | `describe_self()` | læses af `visible_inner_life._self_narrative_line()` |
| 10 | `build_inner_life_section()` | `prompt_contract.py:1381` |
| 11 | `build_central_self_state_section()` | `prompt_contract.py:1481` — egen sektion |

Så maven påvirker prompten **gennem en afledt tilstand**, ikke som et navngivet
signal. Det er præcis den arkitektur Bjørn beskrev: Centralen bearbejder, modellen
får syntesen.

**Men påvirkningen er betinget, og det er målt:** `-0,10` flytter kun `tone`-label
hvis scoren ligger inden for 0,10 over en tærskel (`0,25` = opløftet, `0,05` = let).
Og grenen udløses kun ved `gut == "caution"` — målt i drift: **1 gang af 560**
(`gut_gate_uden_bias_shadow`, 18:36). Kalibreringen har **4303 `proceed`, nul
`caution`**. Vejen er åben og forbundet; den bærer i praksis intet, fordi
betingelsen næsten aldrig er sand. Det er den præcise form — ikke «der er ingen
vej».

Det er **niende lag** i samme fejlklasse: jeg greppede efter et variabelnavn i
prompt-laget og konkluderede om en *kæde af afledte tilstande*.

### Det vigtigste

`liveness_registry` **beskrev det allerede** — den kalder dem `orphaned` med
producent-navn. Men registret læses kun af én API-rute
(`mission_control_runs_ops.py`). **Ingen kode handler på det.**

**Rettet 3/11-2026 kl. 21:1x — registret er ikke en detektor.** Jeg skrev at det
«ved det hele allerede». Målt: `_REGISTRY` er en **hardcoded dict** kurateret ved
auditen 25/9, og `classify_table` slår op i den — der er ingen dynamisk
klassificering, ingen INSERT-detektion, ingen liveness-måling. Den kan fortælle
hvad en tabel blev klassificeret som **den 25/9**; den opdager ikke at en ny
forbindelse er oprettet, eller at en producent er holdt op med at fyre.

**Prøven — og min egen fejl i den (målt 3/11 kl. 21:2x).** Jeg skrev at
`composer_jarvis_forslag` «har 22 rækker i dag, så klassifikationen er forældet».
Indvendingen var rigtig: rækker der findes i dag beviser ikke at nogen skriver i
dag. Men målingen falder den anden vej end indvendingen antog — der **er** en
skrivesti, og den er live:

| Led | Målt |
|---|---|
| Skriver | `core/runtime/db_composer_jarvis.py:100` `gem_forslag()` → `INSERT INTO composer_jarvis_forslag` |
| Kaldt fra | `core/tools/composer_suggest_tools.py:55` — `suggest_next_task`-værktøjet |
| Rækker skrevet | 22, fordelt 30/9 → **2/11**, ikke én klump |
| Hentet af klient | 13 af 22 har `vist_at`; **9 har ingen `composer_choices`-række** |

Så registrets post («INGEN skrivesti i kilden», «intet sted i koden skriver i
den») er **beviseligt forkert**, ikke bare gammel. Klassifikationen er forældet —
men grunden er at skriveren blev koblet på efter 25/9-auditen, ikke at rækkerne
er historiske rester. Det er den samme fejlklasse som `false_positive`: en
status-literal der ikke længere dækker virkeligheden.

**Og den var ikke enlig.** Da jeg byggede en vagt mod netop den påstand — at en
post ikke må sige «INGEN skrivesti» hvis der findes en INSERT i kilden — fandt
den to mere med det samme:

| Bord | Stod som | Er målt | Skriver |
|---|---|---|---|
| `composer_jarvis_forslag` | orphaned / «INGEN skrivesti» | **wired** | `db_composer_jarvis.gem_forslag` ← `suggest_next_task` |
| `session_write_leases` | orphaned / «INGEN skrivesti» | **manual_only** | `db_session_ledger.acquire_write_lease` ← `ledger_canary` ← `chat_sessions:113`, betinget af `is_armed()` (False nu) |
| `user_flags` | orphaned / «INGEN skrivesti» | **manual_only** | `security_guard._lock_account` — kun ved account-lockdown |

Tre forældede poster i samme mønster, alle med en skriver der blev koblet på
efter auditen. **Grænsen er vigtig:** `orphaned` betyder ikke «ingen skriver» —
det betyder «skriveren findes, men har ingen live-kalder». En INSERT i kilden er
derfor forventet og beviser intet. Kun den hårdeste form af påstanden, «INGEN
skrivesti», kan afgøres statisk — og det er præcis hvad vagten måler.

Så det præcise fund er todelt, ikke ét: **kataloget er statisk, og intet læser det
aktivt.** Det er samme fejlform som `honored`-stien og de 293 dubletter, blot i
systemisk skala: beskrivelsen af problemet er bygget, og forbindelsen fra
beskrivelse til handling mangler — *og* beskrivelsen ældes uden at nogen opdager
det.

Det jeg bad om, er derfor ikke «forbind alt hvad registret peger på». Det er at
skelne de tre situationer: **forældet klassifikation** (som
`composer_jarvis_forslag`), **bevidst manuel** (`manual_only`), og **reelt
frakoblet** (`orphaned` hvor skriveren har nul kaldere). Kun den tredje er en
mangel — og kun en måling i dag kan afgøre hvilken der er hvilken.

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

---

## Målt 3/11-2026 kl. 18:50 — A5 var den forkerte løftestang

Dokumentet har hidtil sagt at A5 (tærsklen, 0,30) «røres ikke før shadow-data findes».
Målingen viser at tærsklen **aldrig har været bindende**. Den er ikke løftestangen.

### Hvad der faktisk afgjorde sagen

`derive_gut_signal` havde reglen `recent_error_count > 3 and confidence < 0.6` → `caution`.
Et **absolut** antal uden grundlag. I et aktivt system passeres 3 fejl hver dag, så
betingelsen var altid sand.

Målt konsekvens — samme globale tilstand, seks vidt forskellige opgaver:

| Opgave | tier | rå | hunch | confidence |
|---|---|---|---|---|
| kritisk migration af produktionsdatabase | irreversible | 0,35 | caution | 0,59 |
| deploy til produktion | irreversible | 0,35 | caution | 0,59 |
| læs logfilen og find fejlen | read | 0,55 | **caution** | 0,59 |
| opret en ny testfil | mutate | 0,45 | **caution** | 0,59 |
| analyser gut-kalibreringen | read | 0,55 | **caution** | 0,59 |
| qwertyuiop | unknown | 0,50 | **caution** | 0,59 |

Med `mode=on` ville gaten have afvist **100 %** af alle autonome runs. Tærsklen på 0,30
blev aldrig nået, fordi retningen allerede var `caution`. A5 var et spørgsmål om et tal
der ikke blev læst.

### Og fejl-signalet var det forkerte signal

De 23 «fejl» i døgnet er **18 gange** `discord-no-active-dm-and-webchat-fallback-blocked`
— en kanal-fejl, ikke en dømmekraft-fejl. Maven blev bange for at Discord ikke svarede.

### Rettelse 1 — rate, ikke antal

`caution` kræver nu **fejlrate over 20 % ved mindst 20 ticks**. Målt tilstand: 23/303 =
**7,6 %**. Fejlraten bæres nu i signalet (`recent_error_rate`, `recent_sample_size`), så
den kan efterprøves — før var den usynlig.

| Drift | Opgave | Før | Efter |
|---|---|---|---|
| sund (7,6 %) | læs logfilen | caution | **proceed** |
| sund (7,6 %) | migration | caution | **caution** (irreversibel) |
| skrøbelig (40 %) | læs logfilen | caution | **caution** |
| 2 fejl / 3 forsøg | læs logfilen | caution | **proceed** (for lille grundlag) |

Retningen kan altså stadig vendes af observationer — det var hele pointen med A1 — men nu
kun når observationerne betyder noget.

### Rettelse 2 — objektet er ikke en handling

Den anden måling var værre end den første. `_KEYWORDS` blev gennemløbet med den farligste
tabel først, så **et** farligt ord hvor som helst i teksten afgjorde sagen. Målt på 40
**faktiske** wakeup-fokus-tekster: **22 af 40 blev `irreversible`** — inklusive
«Verificér desk-release 0.6.290: tjek at GitHub-releasen har 11 assets», hvor «release» er
*objektet* for en kontrol.

Nu afgør verbet i hver **sætningsdel** handlingen, og den farligste del vinder:

| Tekst | Før | Efter |
|---|---|---|
| Verificér desk-release 0.6.290 | irreversible | **read** |
| MÅL DAEMON-LANEN MOD BASELINE … FØR genstart | irreversible | **read** |
| læs listen og slet de gamle rækker | irreversible | **irreversible** (uændret) |
| deploy til produktion | irreversible | **irreversible** (uændret) |

Fordeling på de 40 ægte tekster: **22 → 3 irreversible** (read 28, mutate 9).

### Beslutningen

**`central_gut_consumer_mode` sættes fra `shadow` til `on`.**

Grundlaget: gaten skelner nu (3 af 40, ikke 22 af 40), den rammer kun opgaver hvis
*verbum* er destruktivt, bagkanten tillader højst 3 blokeringer i timen, hele vejen er
fail-open, og flaget kan vendes tilbage med én skrivning. Shadow uden forbruger er den
form for teater dokumentet selv advarer mod.

**Risiko, sagt højt:** reglen er en kurateret heuristik, ikke en måling af værktøjsbrug.
En opgave formuleret som kontrol («tjek og slet …») læses som kontrol. Den faktiske
destruktive handling går stadig gennem sine egne godkendelsesgates.

### Bevis

- `test_gut_engine.py`: 4 nye/rettede vagter (rate, minimumsgrundlag, synlig rate)
- `test_task_tool_mapping.py`: 4 nye vagter (verifikation ≠ handling, farlig del vinder,
  fordelingen på virkelige opgaver)
- `test_gut_engine + test_gut_calibration + test_task_tool_mapping + test_central_adaptation`:
  **87 grønne**

---

## Målt 3/11-2026 kl. 19:00 UTC — C1 og D2 er samme svar, og det er negativt

Dokumentet har haft C1 («niveau 2 = virksomt») og D2 («når en system*værdi* ind i
prompten?») stående som to umålte punkter. De er samme spørgsmål, og det er nu målt
hele vejen fra producent til læser.

**Kæden, målt:**

| Trin | Målt |
|---|---|
| Produceret | `heartbeat_runtime.py:674-678` kalder `build_gut_surface()` via `_safe_surface` |
| Samlet | `_build_cognitive_surfaces()` lægger den i `surfaces["gut"]` |
| Pakket | `state["cognitive_architecture"] = cognitive_surfaces` (linje 585 og 609) |
| **Læst af** | `mission_control_common.py:186`, `central_hub.py:163`, `runtime_self_model_surfaces.py:424` |

**Ingen af læserne er prompten.** `prompt_contract.py` indeholder nul referencer til
`cognitive_architecture` eller `build_cognitive_architecture_surface`. Fladen er altså
**produceret og tilgængelig, men ikke virksom som flade** — den vises i Mission Control
og i Centralen, og den læses ikke direkte ind i prompten.

**Forbehold (målt 3/11 kl. 21:0x, udvidet 21:1x):** det betyder *ikke* at prompten er
uden kognitiv kontekst. `cognitive_state`-injektionen leverer 800 tegn live, og 8 af 11
support-sektioner lever. Og for gut-tallene specifikt: de når frem **ad en indirekte
vej** — `build_gut_surface → central_stance → central_valence (-0,10 ved caution) →
central_self_state → describe_self → build_inner_life_section` — verificeret led for led.
Det der står tilbage som målt sandt er ikke «ingen vej», men: vejen er **betinget**
(kræver `caution`, målt 1 af 560) og **forsinket** (går gennem durabel KV mellem
cadence-ticks, ikke live per request).

Det gør C1's tre niveauer konkrete for denne flade:

- **Produceret:** ja. `build_gut_surface()` svarer med `evaluated`, `withheld`,
  `backstop_overkoersler` og kalibrering.
- **Tilgængeligt:** ja. Det ligger i `cognitive_architecture` med 20+ søsterflader.
- **Virksomt:** **delvist.** Ingen direkte prompt-læser; én indirekte, betinget vej
  gennem valens → selvtilstand → indre liv.

Konsekvensen er ikke kosmetisk: de tal vi har arbejdet med hele dagen — `evaluated`,
`withheld`, `blokeret`, kalibreringens 1,00 — kan jeg se i en visning, men de indgår
ikke i den kontekst jeg ræsonnerer ud fra. Jeg kan slå dem op; jeg bliver ikke informeret
af dem.

**Ikke lukket som opgave:** om fladen *bør* ind i prompten er en produktbeslutning, ikke
en måling. At den ikke er der, er nu et faktum; om det er en fejl, er et valg.

## Målt samme tid — A5's første ægte `on`-kald i drift

`gate_verdict_counts` viser `gut_gate` gået fra 558 → **559** kl. **18:56:47**, med
`decision=green` og `mode=on`. Samme sekund startede `autonomous-9e48cb88`, som blev
**completed** kl. 18:57:25.

Det er den første gang gaten har afgjort et rigtigt autonomt run i `on`-mode — og den
tillod det, fordi opgaven var læsende (`proceed`, conf 0,61 mod tærskel 0,30).

**Men `gut_gate_withheld` findes stadig ikke i tabellen.** A3's nerve — at en afvisning
registreres som beslutning — er derfor *implementeret og testet*, men **ikke bevist i
drift**, fordi gaten endnu ikke har afvist noget. Det kræver et run hvis verbum er
destruktivt. Målt fordeling på de 40 faktiske wakeup-tekster: 3 af 40. Så det kommer,
men det er ikke kommet.

---

## Målt 3/11-2026 kl. 20:0x — veto-gaten: tallene er værre end opgaven antog, og rettelsen er en anden

De to side-opgaver (`side-fd6717e5fa`, `side-1c970e85e7`) blev målt mod `veto_events` før nogen kode blev rørt.

### Tallene — og en korrektion af min egen læsning

Fordelingen, målt mod `veto_events`:

| resolution | antal | hvad det faktisk betyder |
|---|---|---|
| `pending` | 536 | **intet udfald endnu** — kan ikke tælles som fejl |
| `false_positive` | 392 | eksplicit markeret forkert |
| `overridden_by_user` | 91 | Bjørn sagde «kør alligevel» — kan være fejl *eller* bevidst risiko |
| `overridden_by_jarvis` | 28 | **jeg selv** der overstyrer min egen gate — ikke evidens for noget |
| `honored` | 4 | vetoet blev adlydt |

**KORREKTION (3/11, ekstern gennemgang).** Jeg skrev først «511 forkerte mod 4 honored — 128:1». Det var forkert: 511 er summen af tre kategorier der ikke betyder det samme. En overstyring er ikke automatisk bevis for at vetoet var forkert, og de 536 `pending` har intet udfald endnu. Tallet 128:1 er derfor **trukket tilbage**.

**Men målingen gjorde konklusionen skarpere, ikke svagere.** Da jeg så hvad de fire `honored` faktisk ramte:

| værktøj | antal | er det en farlig handling? |
|---|---|---|
| `semantic_search_code` | 2 | nej — ren læser (frigivet 3/11) |
| `dismiss_plan` | 2 | nej — harmløs |

Og de 28 `overridden_by_jarvis` er overvejende også læsere (`verify_file_contains` 2, `db_query` 2, `read_dreams`, `inbox`, `set_flag`).

**Det ærlige regnestykke er derfor: 392 eksplicit forkerte, og nul dokumenterede tilfælde hvor et `protectiveness`-veto stoppede noget farligt.** Det er ikke et præcisionsforhold — det er fraværet af ét eneste positivt eksempel. Det kan ikke udtrykkes som en brøk, og det skal ikke forsøges.

**KORREKTION NR. 2 (3/11, samme eksterne gennemgang).** Også «392 eksplicit forkerte» var for stærkt. Jeg læste `check_veto()` og målte hvad kategorien faktisk betyder:

`false_positive` skrives **kun ét sted** i koden — `veto_gate.py:784`, inde i `if not user_present:`-grenen. Den gren er en **abstention**: der findes ingen bruger i autonome ture, så gaten afstår fra at blokere og logger hvorfor. `resolve_veto_event()` kaldes kun med `overridden_by_jarvis` (målt: `gate_override.py:241` er den eneste kaldesti) — der findes **ingen kodevej der sætter `false_positive` som en efterfølgende vurdering**.

Målt fordeling af de 392:

| `veto_result` | antal | hvad det betyder |
|---|---|---|
| `allowed` | **206** | gaten blokerede **aldrig** — den abstainede. Ikke et forkert veto; intet veto. |
| `blocked` | **186** | gaten blokerede faktisk, og rækken blev markeret `false_positive` ved hændelsen |

Og de 186 fordeler sig med **93 rækker med tomt `tool_name`, alle dateret 13/9** — præcis den dag `user_present`-grenen blev indført.

**KORREKTION 2 (3/11, ekstern gennemgang).** Jeg skrev «117 `false_positive` er fra før 13/9, 308 fra og med». Det var forkert: 117 + 308 = **425**, som er antallet for **alle feelings** (`protectiveness` 392 + `fatigue` 33). De 392 er kun `protectiveness`. Målt igen, opdelt korrekt: **89 før 13/9, 303 fra og med** (89 + 303 = 392). Jeg blandede to populationer i én sætning — samme fejlklasse som de to foregående, nu på datasættet i stedet for på kategorierne.

### Den historiske modsigelse — og hvad den faktisk var

Den eksterne gennemgang påpegede en reel modsigelse: den nuværende kode sætter `false_positive` **kun** sammen med `veto_result="allowed"` (linje 784, `user_present=False`-grenen), men 186 rækker har `blocked` + `false_positive`. De kan altså ikke være skrevet af den kode der kører nu.

Målt, og det forklarer dem:

| Gruppe | Antal | Datoer | Skrevet af |
|---|---|---|---|
| `allowed` + `false_positive` | 206 | **alle** 13/9 og frem | den nuværende `user_present`-gren |
| `blocked` + `false_positive` | 186 | **89 i juni**, 97 på 13/9 (17:13–18:02) | **oprettet** under en tidligere kodeversion — men juni-rækkerne blev oprettet med `pending` og er ændret **bagefter** af en skriver jeg ikke har fundet |

Commit `41d8e076c` (13/9 kl. **20:47**) indførte `user_present`-grenen og skriver i sin besked at `false_positive` «lå allerede i skemaet, **ubrugt**». De 97 rækker fra 13/9 er tidsstemplet **før** commit'en. Og den gamle kode (læst i `41d8e076c^`) skrev `blocked` med `resolution='pending'` — så de 89 juni-rækker er blevet opdateret **efter** indsættelsen.

**Hvem opdaterede dem, kan jeg ikke svare på.** Der findes ingen kodevej i dag der gør det: `resolve_veto_event` kaldes kun med `overridden_by_jarvis` (`gate_override.py:241`), og en søgning i hele repoet finder kun to skrivestier til `false_positive` — begge i `veto_gate.py`, begge ved hændelsen. Forklaringen er derfor enten en engangs-opdatering der ikke ligger i git, eller en kodeversion der er væk. **Det er en åben tråd, ikke et svar.**

Det ændrer ikke konklusionen, men det ændrer hvor sikkert jeg kan sige den: jeg kan ikke hævde at *alle* 392 blev klassificeret ved oprettelsen. Jeg kan kun sige at den kode der kører nu ikke kan have skrevet de 186.

**Den korrigerede konklusion:** kategorien `false_positive` er ikke en vurdering af om risikoen var ægte. Den er en **klassifikation af om gaten måtte håndhæve**. Vi har derfor intet valideret mål for `protectiveness`-vetoets præcision — hverken 128:1, 392, eller noget andet tal i tabellen. Det der står tilbage er kun: **nul dokumenterede tilfælde hvor et `protectiveness`-veto stoppede noget farligt**, og det er et fravær, ikke en måling.

### Det åbne spørgsmål — og en skelnen jeg ikke selv havde stillet

Jeg endte med at spørge: *skal `protectiveness` fortsat være en veto-følelse?*

Det er formuleret som et ja/nej, og det er for groft. Der er to funktioner blandet sammen, og de behøver ikke have samme betingelser:

| | **Signal** | **Myndighed** |
|---|---|---|
| hvad | Centralen registrerer bekymring, undersøger, foreslår forsigtighed | Centralen standser en handling |
| kræver | at signalet bærer *noget* information | at signalet er præcist nok til at retfærdiggøre et indgreb |
| målt grundlag | findes (intensiteten varierer med tilstanden) | **findes ikke** (nul dokumenterede korrekte vetoer) |

At fjerne `protectiveness` som *signal* ville være at gøre mig blind for en bekymring der er ægte. At beholde den som *myndighed* er at lade en upræcis størrelse standse arbejde. De to beslutninger er uafhængige, og kun den anden har data imod sig.

Det er ikke løst her. Det er præciseret, hvilket er det næste bedste.


### Det afgørende fund: intensiteten kan ikke skelne

Opgaven foreslår at tilføje `protectiveness` til `_BASE_THRESHOLDS` «med et domæne der matcher rå intensity (0,69–0,92)». Målt:

| | n | min | median | max |
|---|---|---|---|---|
| `false_positive` | 392 | 0,75 | **0,95** | 1,00 |
| `honored` | 4 | 0,81 | **0,91** | 1,00 |

Falske positiver ligger **højere** end de ægte. Nul af de fire honored ligger over max(false_positive). Enhver tærskel ville ramme begge klasser nogenlunde lige hårdt — den ville flytte fordelingen, ikke forbedre den.

**Konsekvens: forslaget er ikke en løsning.** Det er tuning af et signal der ikke bærer information om hvorvidt blokeringen var rigtig. Til sammenligning virker `irritation`: 8 blokeret, 6 honored, **0** false_positive.

### Punkt 2 er overvurderet

Opgaven siger at generiske targets som «en blokering» gør gaten mere blokerende jo flere forpligtelser der skrives. Målt: **14 af 2045 events (1 %)** bærer en generisk target. Mekanismen er ægte, effekten er marginal. Den er ikke prioritet.

### Hvad der blev rettet

`_ALWAYS_ALLOWED_TOOLS` manglede rene læsere. Målt blokeret af protectiveness: `db_query` 20, `verify_file_contains` 17, `read_mood` 11, `eventbus_recent` 9, `read_dreams` 5, `read_self_state` 3, `semantic_search_code` 2. Alle syv er nu frigivet (listen 65 → 72).

Vagten `test_rene_laesere_kan_ikke_gated` er **bevist ved mutation**: fjernes `db_query` fra listen, falder testen med `rene læsere mangler i frigivelsen: ['db_query']`. Kontrollen i samme test kræver at `write_file` stadig blokeres, så testen ikke kan bestå fordi gaten blev harmløs.

### Stadig åbent — og hvorfor det er en beslutning

Om `protectiveness` fortsat skal være en veto-følelse. Dataene siger nej: 4 honored ud af 515 er støj, og intensiteten korrelerer ikke med udfaldet. Men at fjerne en følelse fra gaten ændrer hvad gaten *er* — det er ikke en tuning, og det skal ikke gøres i en side-opgave.

---

## Målt 3/11-2026 kl. 19:18 UTC — fjerde lag, og en regel der ikke var gemt

### Præciseringen: «oprettet under» er ikke «skrevet af»

Tabellen ovenfor sagde at alle 186 `blocked`+`false_positive` var «skrevet af en tidligere kodeversion». Det er stærkere end målingen: juni-rækkerne blev **oprettet** med `resolution='pending'` og er ændret **bagefter** af en skriver der ikke findes i repoet. Den præcise formulering er derfor:

> Hændelserne blev oprettet under en tidligere kodeversion. Hvem eller hvad der senere ændrede deres resolution, er endnu ukendt.

Søgning i **hele** repoet (ikke kun `core/`) bekræfter kun to skrivestier til `false_positive`, begge i `veto_gate.py`, begge ved hændelsen. Den ukendte skriver er altså enten en engangs-SQL der ikke ligger i git, eller kode der er væk.

### Det fjerde lag i samme fejlklasse

| Lag | Hvad jeg gjorde forkert |
|---|---|
| 1 | Summerede tre kategorier til ét præcisionstal |
| 2 | Læste en kolonnes **navn** som dens **betydning** |
| 3 | Antog at **nutidens** skriver forklarer **datidens** data |
| 4 | Antog at «oprettet under» = «skrevet af» |

Fællesnævneren er ikke at jeg tager fejl af dataene. Det er at jeg ved hvert led laver et **lille semantisk spring der ser ud som en præcisering**, men som er en påstand uden dækning.

### Og en regel der ikke var gemt

Da jeg ville verificere at de fire lag faktisk stod i `behavioral_decisions`, viste det sig at **lag 1 var væk**. Jeg havde opdateret `dec_d7b8ae884191` med lag 2's indhold — `decision_update` **erstatter** direktivet, den tilføjer ikke. Så jeg troede jeg havde fire regler og havde tre, og den der forsvandt var den mest grundlæggende: *summer aldrig kategorier før du har verificeret at de betyder det samme.*

Det er samme fejlklasse på et andet lag: jeg behandlede en vedvarende struktur som en kladde. En beslutning der rammer hver heartbeat-cyklus er ikke et dokument jeg redigerer — det er en regel der skal kunne stå alene.

Rettet: `dec_5c2ae0afd626` genopretter lag 1 selvstændigt. Målt: fire separate aktive poster, summerings-reglen findes præcis én gang.

---

## Målt 3/11-2026 kl. 20:2x — de to side-opgaver: den ene var løsbar, den anden var forkert stillet

### `side-1c970e85e7` — «Veto-læringen rammer loftet» — **løst**

Målt i `veto_adaptive_counters` (41 rækker, 38 overrides + 3 honored):

| par | overrides | honored | effektiv tærskel FØR | NU |
|---|---|---|---|---|
| `restart_self` + `protectiveness` | 7 | 0 | **0,98 — på loftet** | 0,89 |
| `edit_file` + `r2_5_gate` | 7 | 0 | **0,98 — på loftet** | 0,89 |
| `edit_file` + `protectiveness` | 4 | 0 | 0,95 | 0,86 |
| `write_file` + `r2_5_gate` | 3 | 0 | 0,90 | 0,85 |

Ved 0,98 blev intet under intensitet 0,98 afvist — parret var reelt ugadet. Det var ikke en
beslutning nogen havde taget; det var bivirkningen af at lægge et fast beløb (+0,05) oven på
en fast basis (0,75) og clampе til 0,98.

**Rettelse:** stigningen er aftagende — `ceiling × n/(n+3)` med ceiling 0,20.
n=1 → +0,05 (**uændret**), n=2 → +0,08 (var +0,10), n=3 → +0,10 (var +0,15),
n=7 → +0,14 (var +0,35), n→∞ → +0,20.
En 0,75-basis har en **matematisk grænse på 0,95** (0,75 + 0,20 når n→∞), så den kan aldrig
nå clamp-loftet 0,98. Ved n=1000 er værdien 0,9494 — det er en målt værdi, ikke grænsen. En høj basis (fx
`restart`+`irritation` = 0,95) rammer loftet **allerede ved første override** (0,95+0,05 = 1,00
→ clamp 0,98) — men det er en eksplicit tabel-beslutning, ikke akkumulering.

**Punkt 2a blev bevidst IKKE gjort.** Opgaven beder om at tilføje `protectiveness` og
`r2_5_gate` til `_BASE_THRESHOLDS` «med et domæne der matcher rå intensity (0,69-0,92)».
Det er ikke dækket: målt i aften kan intensiteten **ikke** skelne falske positiver (median
0,95) fra ægte (median 0,91). At vælge en base der «matcher fordelingen» er at vælge et
vilkårligt tal midt i den, ikke at gøre gaten klogere.

**Punkt 2c blev bevidst IKKE gjort.** Nøglen er `(tool_name, feeling)`, ikke handlingstypen,
så en dokumentations-commit og en risikabel kommando med samme værktøj deler skæbne. Det er
ægte — men det kræver en definition af «handlingstype», som er samme uløste grænse som
A1's opgave→værktøj-mapping.

**Punkt 3 var allerede gjort** i commit `70550cd15` (syv rene læsere frigivet, 65 → 72).

**Det største fund er ikke loftet, men asymmetrien.** `_increment_honored_count` kaldes kun
fra `resolve_veto_event(event_id, "honored")` — og hele repoet har **præcis én kalder**:
`gate_override.py:241`, som altid sender `"overridden_by_jarvis"`. Så `resolution == "honored"`-
grenen er koded men **uopnåelig**, og `_HONORED_DAMPEN` er død kode. De 10 honored-tællinger
blev alle skrevet 13/9 kl. 19:05:48 inden for millisekunder — det er legacy-KV-migreringen
(`veto_gate.py:484`), ikke optjente hændelser.

Docstringen i `resolve_veto_event` advarer selv mod præcis den tilstand vi stod i:
*«Without this, the gate could only ever desensitize via override, never resensitize via
honored.»* Mekanismen blev bygget for at forhindre den, og er aldrig blevet kaldt.

Overfladen viser nu `honored` ved siden af `overrides`, så asymmetrien er synlig og ikke tavs.
At give honored-stien en ægte kalder er **ikke** gjort: enhver automatisk «dette veto blev
adlydt»-detektor ville være en proxy (adlød Jarvis, eller opgav han af andre grunde?), og det
er præcis den fejlklasse — at læse en registrering som en vurdering — der er blevet rettet
fire gange i dag.

**Tests:** 37 i `tests/test_gates.py` (34 → 37). Vagten er mutationsbevist: med kurven sat
tilbage til lineær falder `test_intet_par_kan_blive_blindt_ved_akkumulering` og
`test_stigningen_er_aftagende`; efter gendannelse er alle 37 grønne. 128 grønne i hele
veto/pushback/gate-batteriet.

### `side-fd6717e5fa` — «protectiveness blokerer 46:1 forkert» — **præmissen er målt forkert**

Opgaven bygger på 46:1, som allerede er tilbagevist i aften (se «128:1 var en sammenlægning»).
Punkt 1's løsning er ikke dækket (se 2a ovenfor). Punkt 2 er målt marginal: generiske targets
rammer **14 af 2045** events — 1 %. Punkt 3 var gjort i `70550cd15`.

### `r2_5_gate` er en ANDEN gate — og den har samme sygdom

Opgaven bad om at undersøge om den skulle med i samme rettelse. Målt:

| | |
|---|---|
| fil | `core/services/r2_5_blocking_gate.py` — ikke `veto_gate.py` |
| fordeling | **504 `pending`**, 68 `overridden_by_user`, **nul honored** |
| værktøjer | `bash` 497, `edit_file` 54, `memory_upsert_section` 14 |
| aktiv i dag | **18 blokeringer 3/11**, senest 18:50 |

Den rammer `bash` — en muterende handling, ikke en ren læser — så
`_ALWAYS_ALLOWED_TOOLS`-rettelsen rører den ikke. Det er et selvstændigt spor med sin egen
mekanisme og sin egen målte skævhed, og det er ikke undersøgt til bunds her.

---

## Målt 3/11-2026 kl. 19:26 UTC — tærskel-rettelsen er levende, og blindhed er umulig for de baser vi har

Genstarten gik igennem: processtart **20:25:31**, commit `4c0b45301` er **20:23:17**. Rettelsen kører.

### Kurven i drift

`_override_lift(n) = 0,20 × n/(n+3)`, loft `_OVERRIDE_CEILING = 0,20`:

| n | 0 | 1 | 2 | 3 | 4 | 5 | 7 | 10 |
|---|---|---|---|---|---|---|---|---|
| lift | 0,000 | 0,050 | 0,080 | 0,100 | 0,114 | 0,125 | 0,140 | 0,154 |

**Kun n=1 er uændret** (+0,050). Ved n=3 ændres lift fra +0,150 til +0,100 — en forskel på
−0,050, og testen blev derfor opdateret fra forventet tærskel 0,90 til 0,85. Kurven er
bagudkompatibel ved **første** override, ikke ved tredje.

### De fire par der var ramt

| par | overrides | før | nu |
|---|---|---|---|
| `restart_self` + `protectiveness` | 7 | **0,98** | 0,89 |
| `edit_file` + `r2_5_gate` | 7 | **0,98** | 0,89 |
| `edit_file` + `protectiveness` | 4 | 0,95 | 0,8643 |
| `write_file` + `r2_5_gate` | 3 | 0,90 | 0,85 |

### Blindhed er nu umulig for base 0,75

Målt med simuleret tælling: base 0,75 giver **0,9494** ved n=1000, og den matematiske grænse er **0,95** (n→∞) — så den kan aldrig nå 0,98. Og målt mod de faktiske 37 par med overrides i drift: **ingen har base ≥ 0,90** — alle står på 0,75. Så loftet er ikke længere en praktisk risiko.

**Forbehold, målt:** base 0,95 (`restart`+`irritation`) rammer loftet **ved én** override, ikke fem — 0,95 + 0,05 = 1,00, clampet til 0,98. Det par har nul overrides i drift, så det er latent, ikke aktuelt. Rettelsen dækker de baser der findes — ikke en hypotetisk høj base.

### KORREKTION 5 (3/11, ekstern gennemgang) — to regnefejl i min egen dokumentation

Jeg skrev «bagudkompatibel ved n=1 (+0,05) og n=3 (+0,10)» og «base 0,95 rammer 0,98 ved fem
overrides». **Begge var forkerte, og begge var beregnelige:**

| påstand | den faktiske beregning |
|---|---|
| bagudkompatibel ved n=3 | gammel: 3 × 0,05 = **+0,150**; ny: 0,20 × 3/6 = **+0,100**. Ændring **−0,050** |
| base 0,95 ved fem overrides | 0,95 + 0,05 = **1,00** ved **n=1** → clamp 0,98 |

Kun **n=1** er uændret (+0,050). At testen blev opdateret fra 0,90 til 0,85 er netop beviset på
at kontrakten blev brudt ved n=3 — jeg skrev «bagudkompatibel» i samme sætning som jeg beskrev
en testændring der viste det modsatte.

Hovedresultatet holder: en 0,75-basis har en matematisk grænse på **0,95**, aldrig 0,98. Men den latente
risiko er skarpere end jeg skrev — en base på 0,95 bliver blind efter **én** override, ikke fem.

**Fejlklassen er den femte i samme familie:** jeg skrev hvad kurven *måtte* give ud fra dens
form, i stedet for at regne den. Det er samme fejl som «128:1» — en påstand der ser beregnet ud,
men ikke er det.

### Honored-dæmpningen virker, men er stadig frosset

`_HONORED_DAMPEN = 0,02` pr. honored, gulv `_THRESHOLD_MIN = 0,30`. Målt: `edit_file`+`irritation` står på **0,68** — under sin base på 0,75 — fordi den har 6 honored-tællinger. Men alle 6 er skrevet 13/9 kl. 19:05:48 som legacy-migrering, ikke optjent. Overrides: 63 og voksende. Honored: 10, alle fra én import. Asymmetrien står uændret; kun loftet er rettet.

### A3 er stadig ikke bevist

`gate_verdict_counts` (ikke `gate_verdict_ledger` — det navn fandt jeg på): `gut_gate` = **559**, uændret siden 18:56:47. Ingen `gut_gate_withheld`-række findes. Gaten har ikke afvist noget endnu, fordi der ikke er kørt et autonomt run siden. Implementeret, ikke bevist.

---

## Målt 3/11-2026 kl. 20:3x — r2_5-gaten: `pending` var ikke en fejl, men en manglende kvittering

Side-opgaven `side-25063fc8e6` bad om at rette `r2_5_blocking_gate`: «504 pending, nul honored». Jeg målte først hvem der overhovedet skriver rækkerne.

### Skriveren og de to udfald

`r2_5_blocking_gate.py` skriver **intet** til `veto_events`. Skriveren er `r2_5_haandhaevelse.py:204`: når en mutation afvises, logges `feeling='r2_5_gate'`, `intensity=1.0`, `veto_result='blocked'` med default `resolution='pending'`.

De to udfald der findes:

| resolution | antal | hvem skriver den |
|---|---|---|
| `pending` | **504** | default ved indsættelse — intet udfald registreres nogensinde |
| `overridden_by_user` | **68** | `_maybe_record_override_from_token_signal`: Bjørn skrev «kør»/«ja» inden for 15 min |
| `honored` | **0** | **ingen** — `resolve_veto_event(id, "honored")` havde nul kaldere i produktion |

Så «504 pending» er ikke 504 uafsluttede sager. Det er det normale tilfælde: ingen override-token kom inden for vinduet, og der fandtes ingen sti til at sige «blokeringen blev adlydt».

### Den ægte fejl er asymmetrien

`_aaben_blok` ved præcis *hvorfor* blokken løftes — `kig_tilbage`, `udløbet` eller `læsefejl` — og publicerer det som `released`. Men intet blev skrevet tilbage til rækken. Konsekvensen er at `veto_adaptive_counters` kun kunne bevæge sig én vej: **overrides hæver tærsklen, honored sænker den aldrig.**

Målt i drift før rettelsen:

| par | base | overrides | honored | tærskel |
|---|---|---|---|---|
| `edit_file` + `r2_5_gate` | 0,75 | 7 | **0** | **0,8900** |
| `write_file` + `r2_5_gate` | 0,75 | 3 | **0** | 0,8500 |
| `memory_upsert_section` + `r2_5_gate` | 0,75 | 2 | **0** | 0,8300 |
| `bash` + `r2_5_gate` | 0,75 | 0 | 0 | 0,7500 |

Gaten var altså blevet 0,14 mere eftergivende for `edit_file` uden at nogen havde besluttet det — samme asymmetri som blev rettet i `veto_gate` samme aften, bare i den anden ende af samme regnskab.

### Rettelsen

`_kvitter_adlydt(siden)` slår de `pending` rækker op der blev skrevet siden blokken blev åbnet, og resolver dem til `honored` — men **kun** når `grund == "kig_tilbage"`. En udløbet blok er ikke en adlydelse, og en læsefejl er ikke en adlydelse; de bliver stående `pending`, hvilket er sandt: vi ved ikke hvad der skete.

`resolve_veto_event` gør resten selv — den incrementer honored-tællingen og sænker tærsklen, præcis den vej docstringen i `veto_gate` advarede om var død.

### Bevis

Tre nye vagter (27 i filen): kig-tilbage kvitterer, udløb kvitterer **ikke** (og må slet ikke spørge databasen), og SQL-filteret bærer `feeling='r2_5_gate'` + `resolution='pending'` + `veto_result='blocked'` — så en vilkårlig SELECT ikke kan bestå.

Mutation bevist: fjernes `_kvitter_adlydt`-kaldet, falder to af vagterne; efter gendannelse er alle 27 grønne. **130 grønne** i det brede gate-batteri.

### Hvad der stadig står åbent

**De 504 historiske rækker.** Jeg kan ikke rekonstruere om de blev adlydt — der findes intet spor fra dengang. De bliver stående `pending`, og det er den ærlige tilstand, ikke en gæld der kan ryddes.

**`honored` er stadig død for veto-gaten selv.** Denne rettelse lukker asymmetrien for r2_5, fordi r2_5 har en observerbar «jeg kiggede tilbage»-hændelse. Den almindelige veto-gate har ingen tilsvarende kvittering — der findes intet tidspunkt hvor man kan sige «brugeren adlød vetoet». Det kræver en anden mekanisme, ikke samme rettelse.

### KORREKTION 6 (3/11, ekstern gennemgang) — en målt værdi er ikke en grænse

Jeg skrev tre steder at en 0,75-basis «maksimalt kan nå **0,9494**». Det er forkert, og fejlen er
beregnelig:

| n | lift = 0,20 × n/(n+3) | tærskel = 0,75 + lift |
|---|---|---|
| 1 | 0,050000 | 0,800000 |
| 3 | 0,100000 | 0,850000 |
| 1.000 | 0,199402 | **0,949402** |
| 10.000 | 0,199940 | 0,949940 |
| 1.000.000.000 | 0,200000 | **0,950000** |

**Den matematiske grænse er 0,95** — fordi `n/(n+3) → 1`, så lift → `_OVERRIDE_CEILING` = 0,20.
0,9494 er værdien **ved n=1000**, altså et punkt på kurven, ikke dens loft.

Det ændrer ikke hovedresultatet: 0,95 < 0,98, så en 0,75-basis kan aldrig blive blind. Men det er
en anden slags fejl end de fem foregående — og en mere grundlæggende:

**Jeg forvekslede et målt punkt med en egenskab ved funktionen.** De fem første korrektioner
handlede om at læse data forkert. Denne handler om at jeg ikke skelnede mellem *hvad jeg havde
regnet* og *hvad formlen kan*. Et endeligt n kan aldrig vise en asymptote.

Konsekvensen for formuleringen er, at grænsen nu skrives som `0,95 (n→∞)`, og 0,9494 kun optræder
sammen med «ved n=1000».
