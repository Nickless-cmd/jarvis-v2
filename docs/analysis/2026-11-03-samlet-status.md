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

## Åbent — målt åbent lige nu

### A. Gut-kæden (seks huller, i rækkefølge)

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

**A6. Backstop kan overkøre gatens nej — og forskellen bevares ingen steder.**
`preflight_gut_gate` har et blokerings-budget (`_MAX_BLOK_PER_TIME = 3` pr.
time). Er det brugt, slipper runnet igennem med `backstop: True` — også når
gaten sagde nej. Målt:

- `backstop`-flaget **læses ingen steder**. Begge produktionskaldesteder
  (`autonomous_stream_run.py:97`, `visible_autonomous_run.py:276`) bruger
  `preflight_allows()`, som kun returnerer `bool` og kaster hele returværdien
  (`confidence`, `hunch`, `backstop`) væk.
- `_blok_tider` er en **in-memory modul-global liste** (`gut_engine.py:279`).
  Budgettet nulstilles ved hver genstart — og backenden er genstartet to gange
  i dag. «3 pr. time» er derfor reelt ubegrænset over tid.
- `gut_gate_backstop` og `gut_gate_withhold` har **nul rækker** i
  `gate_verdict_counts`. Ingen af stierne er nogensinde udløst.

Konsekvens: en overkørsel er usynlig bagefter. Udfaldet kalibrerer den hunch
`_on_started` dannede — ikke den gatens anbefaling backstop overkørte.

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

- At reboot-awareness, silence-listener og continuity-kernel beskriver **samme**
  afbrydelse. Kræver tidsstempel-sammenligning på tværs af tre tabeller. Ikke gjort.
- Om en systemværdi (ikke bare navnet) når ind i prompten. Ikke gjort.
- Om der findes en opgave→værktøj-mapping. `pattern_strength` giver data pr.
  værktøj, men ingen kobling fra en opgavebeskrivelse til hvilke værktøjer den
  vil bruge.

---

## Rækkefølgen der giver mening

1. **A2** — én forudsigelse hele vejen (mindst arbejde, størst ærlighed)
2. **A6** — bevar gate-anbefalingen og den endelige beslutning som to felter,
   så en backstop-overkørsel kan ses bagefter
3. **A3** — registrér afvisningen i kalibreringslivscyklussen, adskilt fra udfaldet
4. **A1** — kobl observationer på, målt i shadow-mode
5. **A4** — gør kalibreringen til noget der kan tage fejl
6. **A5** — først da en tærskel

A6 kommer før A3 fordi den rydder den samme livscyklus: uden et felt for
«gaten sagde nej, bagkanten sagde ja» kan A3's registrering ikke skelne en
ægte afvisning fra en overkørt.

C1–C3 er et selvstændigt spor: de er navnekollisioner og forbrugshuller, ikke
gut-kæden. De skal ikke blandes ind i den rækkefølge.
