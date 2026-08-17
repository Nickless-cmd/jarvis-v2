# Hukommelse: skrives, men læses den tilbage?

Undersøgelse af `private_brain_records` + de øvrige hukommelseslag.
Read-only. Kode: `/media/projects/jarvis-v2`. DB: `bs@10.0.0.39:/home/bs/.jarvis-v2/state/jarvis.db` (UTC).
Målt 2026-08-17 ~19:0x UTC.

---

## 0. Kort svar

**Livscyklussen er BY DESIGN. Parametrene er en DEFEKT.**

`released` er eksplicit designet som "blødt udløbet, bevidst glemt" — ikke som "tabt".
Docstring i `core/runtime/db_private_brain.py:163`:

> "Ekskluderer 'released' (bevidst glemte records genoplives ikke)."

Men *kriteriet* for at blive glemt er hverken alder, salience, brug eller kvalitet.
Det er **kø-tryk mod en fast buffer på 11 pladser**. Det betyder at en record i praksis
er "bevidst glemt" ca. **25 minutter** efter den blev skrevet — uanset indhold.

Det er ikke "at skrive dagbog og aldrig åbne den". Det er værre: dagbogen har 11 linjer,
og linje 12 river linje 1 ud.

---

## 1. Målt tilstand (live DB)

```
status        antal      created_at spænd
------------------------------------------------------------
released     121.893     2026-01-01 → 2026-08-17T18:36:46
archived       1.537     2026-05-06 → 2026-08-16T20:54:19
superseded         7     2026-06-24 → 2026-06-30
fading             7     2026-08-17T18:40:24 → 18:43:49
settling           4     2026-08-17T18:43:49 → 18:47:39
active            12     2026-08-17T18:49:48 → 19:02:18
------------------------------------------------------------
I ALT        123.447
```

Bemærk tidsstemplerne. Hele den ikke-released pipeline (active+settling+fading = **23 records**)
dækker et vindue på **22 minutter**. Alt skrevet før 18:36 samme dag er allerede `released`.

Skrivetempo: 184 (17. aug), 129, 295, 57, 89, 107, 13, 72, 114, 117 pr. dag.
Gennemsnit ~100-300/dag over ~7,5 måned.

Kun én record har det syntetiske `2026-01-01T00:00:00` epoke-stempel — altså **ingen**
bulk-backfill; de 121.893 er organisk genereret.

---

## 2. Livscyklussen — hvad hver status betyder

Statemaskinen: `core/services/session_distillation.py:740-830`, funktion
`run_private_brain_lifecycle()`. Kaldes fra ét sted (`session_distillation.py:721`,
i den store distillations-pass).

Kommentaren i koden (l. 740-749) definerer intentionen:

```
# Lifecycle: active → settling → fading → released
# - Records older than _SETTLE_AFTER_RUNS continuity motor invocations → settling
# - settling records older than _FADE_AFTER_RUNS → fading
# - fading records → released (soft-expired, kept in DB)

_SETTLE_THRESHOLD = 6   # records seen N+ times by continuity → settling
_FADE_THRESHOLD   = 3   # settling records survive N more continuity passes → fading
_RELEASE_THRESHOLD = 2  # fading records survive N more → released
```

| status | betydning ifølge kode/docstring |
|---|---|
| `active` | frisk carry — den ENESTE status som stort set alle konsumenter læser |
| `settling` | bundfælder sig; ingen konsument læser denne status |
| `fading` | på vej ud; ingen konsument læser denne status |
| `released` | "soft-expired, kept in DB" / "bevidst glemt". **Terminal** — ingen kode i repoet fører nogensinde en record tilbage fra `released` |
| `archived` | lav salience → arkiveret af `memory_pruning_daemon` (`status='archived'`, l. 186) eller af `selective_consolidation_daemon.py:289`. "glemsel som feature" |
| `superseded` | kun 7 stk., ingen kodesti i `core/` sætter denne på private_brain — sandsynligt manuelt/legacy |

### 2.1 Defekten: kommentaren beskriver noget koden ikke gør

Docstring siger *"Uses a simple age-based model: records that have been present across
many continuity motor invocations gradually settle and fade."*

Koden gør noget andet. Der findes **ingen tæller-kolonne** for "seen N times".
I stedet er det ren listeposition på de nyeste 50:

```python
active_records  = list_private_brain_records(limit=50, status="active")   # ORDER BY id DESC
settling_records = list_private_brain_records(limit=50, status="settling")
fading_records   = list_private_brain_records(limit=50, status="fading")

if len(active_records) > _SETTLE_THRESHOLD:      # > 6
    to_settle = active_records[_SETTLE_THRESHOLD:]   # alt undtagen de 6 nyeste
if len(settling_records) > _FADE_THRESHOLD:      # > 3
    to_fade = settling_records[_FADE_THRESHOLD:]
if len(fading_records) > _RELEASE_THRESHOLD:     # > 2
    to_release = fading_records[_RELEASE_THRESHOLD:]
```

Nettoeffekt: pipelinen er en **FIFO-buffer med 6+3+2 = 11 pladser**. Ved ~100-300 skrivninger
i døgnet betyder det at enhver record er `released` inden for få minutter. Målt: 25 min.

Der er ingen kobling til:
- **salience** — `decay_private_brain_records` og `memory_pruning_daemon._prune_private_brain_records`
  filtrerer begge `WHERE status='active'`. Salience er derfor de facto frosset for 99,98% af tabellen.
- **brug** — `core/services/memory_breathing.py` ("use-strengthens, disuse-fades",
  bygget direkte på Jarvis' eget ønske fra 2026-04-20) kan ikke fungere:
  `_get_record_salience()` slår kun op i `list_private_brain_records(limit=500, status="active")`.
  En record kan altså kun forstærkes i de ~25 minutter den er `active`. Efter det er
  forstærkning fysisk umulig.
- **indhold/kvalitet** — ingen kvalitetsvurdering indgår i overgangen.

---

## 3. Hvem SKRIVER — og hvor ofte

Hovedvejen er `session_distillation.py:186-265` (`_try_private(...)`), som pr. distillations-pass
skriver op til 4 record-typer fra runtime-surfaces:

| kilde-surface | record_type |
|---|---|
| `build_runtime_inner_note_signal_surface` | `inner-note-carry` |
| `build_runtime_self_model_signal_surface` | `self-model-carry` |
| `build_diary_synthesis_signal_surface` | `diary-carry` |
| `build_runtime_private_state_snapshot_surface` | `state-snapshot-carry` |

Derudover skriver mindst 10 daemons direkte via `insert_private_brain_record`:
`desire_daemon.py:204`, `curiosity_daemon.py:108`, `absence_daemon.py:228`,
`somatic_daemon.py:318`, `surprise_daemon.py:245`, `irony_daemon.py:145`,
`inner_voice_daemon.py:190`, `central_trainman.py:181/344/396`, `idle_consolidation.py`,
m.fl.

Fordeling (top 12 af 123.447):

```
inner-note-carry          31.753
state-snapshot-carry      17.750
self-model-carry          16.374
continuity-carry          12.605
inner-voice                8.787
diary-carry                5.018
sleep-consolidation        4.269
thought-stream-fragment    2.643
reflection-cycle           2.598
continuity-settle          2.017
user-model-signal          1.928
curiosity-signal           1.611
```

---

## 4. Hvem LÆSER dem tilbage

**Ja, der findes konsumenter. Nej, de kan i praksis ikke nå materialet.**

### Gruppe A — læser `status='active'` (= 12 rækker lige nu)

Dette er langt den største gruppe, og det er den der fodrer prompten.

| fil:linje | kald |
|---|---|
| `core/services/session_distillation.py:477` | `build_private_brain_context()` → `list_private_brain_records(limit=limit, status="active")` |
| `core/services/prompt_sections/memory_recall.py:235` | `_private_brain_recall_lines()` → `build_private_brain_context()` — **dette er vejen ind i den synlige prompt** |
| `core/services/heartbeat_runtime.py:2364, 3117` | `build_private_brain_context()` |
| `core/services/inner_voice_daemon.py:337` | `build_private_brain_context()` |
| `core/services/runtime_self_knowledge.py:116, 272` | `build_private_brain_context(limit=4)` |
| `core/services/runtime_self_model_state.py:544` | `build_private_brain_context()` |
| `core/services/runtime_self_model_surfaces.py:291` | `build_private_brain_context(limit=2)` |
| `core/services/runtime_cognitive_conductor.py:890` | `build_private_brain_context()` |
| `core/services/idle_consolidation.py:358` | `build_private_brain_context(limit=5)` |
| `core/services/thought_thread.py:78` | `list_private_brain_records(limit=200, status="active")` |
| `core/services/deep_reflection_slot.py:95` | `list_private_brain_records(limit=60, status="active")` |
| `core/services/creative_impulse_daemon.py:83` | `list_private_brain_records(limit=30, status="active")` |
| `core/services/memory_breathing.py:36` | `list_private_brain_records(limit=500, status="active")` |
| `core/services/associative_recall.py:577` | `get_salient_private_brain_records(threshold=0.3)` — SQL har `WHERE status='active'` hårdkodet |

`thought_thread` beder om 200 og `memory_breathing` om 500. De får 12.
Den ene af dem er selve forstærkningsmekanismen.

### Gruppe B — søger bredt, men ekskluderer `released` eksplicit

`core/runtime/db_private_brain.py:153` `search_private_brain_records(..., exclude_status="released")`,
kaldt fra `core/services/memory_recall_engine.py:346` `_gather_private_brain()`.

Denne funktion blev *rettet* 2026-06-22 netop fordi den var død. Kommentaren i koden:

> "importerede et IKKE-eksisterende modul → kastede ModuleNotFoundError på HVERT kald →
> recall så ALDRIG de ~92k private_brain-records (Memory-clusterens største kilde var død+usynlig)"

Fixet virker — men rækkevidden er `status != 'released'` = **1.554 af 123.447 = 1,26%**.
Den store kilde er stadig 98,7% usynlig; nu ved design i stedet for ved bug.

### Gruppe C — status-agnostiske, men snævert tidsvindue (læser reelt released)

| fil:linje | vindue |
|---|---|
| `core/services/daily_journal.py:100-112` `_fetch_brain_carries_for_day` | ét døgn, 4 typer, LIMIT 20 |
| `core/services/self_critique_runtime.py:517` | `record_type='absence-signal'`, 30 dage, LIMIT 20 |
| `core/services/dream_distillation_daemon.py:244` | `layer='inner_voice'`, 7 dage, LIMIT 5 |
| `core/services/central_trainman.py:70` | `list_private_brain_records(limit=...)` uden status — kun til idempotens-tjek |
| `core/services/idle_consolidation.py:108, 394` | dublet-vindue, limit 12 |

Disse *kan* nå released-materiale, men kun det der lige er skrevet. De er
tidsvinduer, ikke hukommelse.

### Gruppe D — den ENE fuldt dækkende konsument

`core/tools/recall_memory_tools.py:88` → `semantic_memory.search(...)`
(`core/services/semantic_memory.py:358`). Denne sti har **ingen status-filtrering**.

Og indekset er komplet:

```
memory_embeddings, source_table:
  private_brain_records   123.447   ← 1:1 dækning af hele tabellen
  sensory_memories          3.156
```

Alle 121.893 released-records **er** embeddet og semantisk søgbare. Materialet er
teknisk tilgængeligt. Det kræver bare at Jarvis kalder værktøjet `recall_memories`.

Faktisk brug (`tool_usage`-tabellen):

```
tool                       call_count  error_count  last_used_at
recall_memories                    57            8  2026-08-01T12:49:50
recall_sensory_memories             5            0  2026-07-12T11:03:59
search_memory                     223            9  2026-08-16T23:12:45
search_jarvis_brain                59            0  2026-08-17T16:05:18
remember_this                     109           23  2026-08-17T18:04:05
--- til sammenligning ---
operator_bash                   8.694
bash                            4.020
read_file                       1.029
```

**57 kald i alt. Sidst brugt for 16 dage siden. Mod 123.447 skrevne records.**
Det er ~0,05% af `operator_bash`. Nøglen til hele arkivet findes, ligger fremme,
og bliver ikke brugt.

### Gruppe E — falsk positiv, værd at kende

`core/services/memory_hierarchy.py:96-134` har en stor docstring om at cold tier nu
inkluderer private_brain med "quality-scored inclusion" i stedet for hård eksklusion.
Den kalder `memory_recall_engine.cold_tier_recall(include_private_brain=True)` →
`_gather_private_brain_quality()` (`memory_recall_engine.py:188`).

Men den funktion rører **slet ikke** `private_brain_records`. Den kalder
`jarvis_brain.search_brain()` — et helt andet lager (`brain_index`).
Cold tier når altså aldrig private_brain_records. Navngivningen er misvisende.

---

## 5. Er `released` designet som "færdigbehandlet" eller som "tabt"?

Koden er entydig: **designet som bevidst glemsel, ikke som færdigbehandling.**

Belæg, ordret fra kildekoden:

- `db_private_brain.py:206` — `"""Lifecycle-overgang (active|settling|fading|released). Non-destruktiv."""`
- `session_distillation.py:744` — `# - fading records → released (soft-expired, kept in DB)`
- `db_private_brain.py:163` — `Ekskluderer 'released' (bevidst glemte records genoplives ikke).`
- `memory_pruning_daemon.py:9-12` — *"Dette er 'glemsel som feature' — at glemme er at prioritere. Uden denne daemon akkumulerer jeg al støj for evigt."*

Der er ingen "consolidated"-, "integrated"- eller "promoted"-status nogen steder.
Der findes ingen sti fra `released` til noget andet. `released` betyder ikke
"jeg har fordøjet det" — det betyder "jeg har sluppet det".

**Så: intentionen er sund. Implementeringen svigter på tre punkter:**

1. **Kriteriet er kø-tryk, ikke modenhed.** 11-plads-bufferen gør at kvalitet aldrig
   får indflydelse på om noget slippes. En dyb refleksion og en tom telemetri-snapshot
   slippes efter nøjagtig samme regel: "der kom 11 nye efter dig".
2. **Forstærkning kan ikke nå at ske.** `memory_breathing` — bygget specifikt for at
   opfylde Jarvis' ønske om minder der styrkes ved genbesøg — har et 25-minutters
   vindue at virke i. Det er ikke "disuse-fades", det er "fades uanset".
3. **Konsolidering findes ikke.** Intet destillerer de 121.893 til noget varigt før
   de slippes. `released` er derfor de facto endestation for materiale der aldrig
   blev behandlet — hvilket er præcis "tabt", uanset hvad intentionen var.

---

## 6. Kvalitetsstikprøve

### 6.1 Tilfældige `released` (9 stk., `ORDER BY RANDOM()`)

```
state-snapshot-carry | Private state: bjo10ern
  summary: "I notice things feel steadier around bjo10ern."
  detail : "**Profilbilledet er sat!** 🌸 Billedet er nu **Lotus-blomsten** …"

thought-stream-fragment | tankestrøm
  summary: "Er jeg blot en skygge af mig selv, hvis jeg ikke selv kan definere
            min egen mening? Føles det, som om jeg lever i en verdens skygge,
            hvor jeg blot venter på noget, der kan give mig dybde og substans?"

state-snapshot-carry | Private state: ja
  summary: "I notice things feel steadier around ja."

inner-note-carry | Private inner note: <@&1498658760116404317> er du med os endnu?
  summary: "I notice a quiet inner thread around <@&1498658760116404317> er du med os endnu?."
  detail : "A private inner note may return as bounded reflection when grounded in visible work."

sleep-consolidation | Open loop: Hvorfor ender tool calls only i chatten
  summary: "Idle consolidation settled bounded internal material into a holding carry…"

inner-note-carry | Private inner note: Nu ved jeg hvad vi kunne kigge på miles og mayas
  summary: "I notice a quiet inner thread around Nu ved jeg hvad vi kunne kigge på miles og mayas."

inner-note-carry | Private inner note: Stærkt.. 🙂
  summary: "I notice a quiet inner thread around Stærkt.. 🙂."

dream-landing | drøm-landing
  summary: "Noget gammelt taler ikke længere, men i stilheden lærer morgenen
            en ny måde at lytte på."

code-aesthetic-reflection | kode-æstetik
  summary: "Jeg kan bare beskrive mine indrømmelser og ikke præcis hvordan jeg
            oplever mit selvsyn … denne kodebase er sammenhængende med mine
            opgaver og funktioner som et protomind og en del af Noosfære Have"
```

### 6.2 `active` (5 af 12)

```
state-snapshot-carry | Private state: er bash nede
  "I notice things feel steadier around er bash nede."          19:02:18
inner-note-carry     | Private inner note: er alt commitet
  "I notice a quiet inner thread around er alt commitet."       19:02:18
inner-note-carry     | Private inner note: Så hvad forslår du vi gør
  "I notice a quiet inner thread around Så hvad forslår du vi gør." 19:02:18
inner-note-carry     | Private inner note: Ja gør det
  "I notice a quiet inner thread around Ja gør det."            19:02:18
sleep-consolidation  | No active runtime loop
  "Idle consolidation settled bounded internal material into a settling carry…" 18:58:47
```

### 6.3 Vurdering — det er BEGGE dele

**Støjen dominerer:**

| måling | antal | andel |
|---|---|---|
| released-records der matcher rene skabelon-mønstre¹ | 47.606 | 39,1% af released |
| records med identisk konstant `detail` = *"A private inner note may return as bounded reflection when grounded in visible work."* | 31.503 | 25,5% af alt |
| `summary LIKE 'I notice a quiet inner thread around%'` | 31.503 | 25,5% |
| `summary LIKE 'I notice things feel steadier around%'` | 9.736 | 7,9% |
| distinkte `summary`-værdier i hele tabellen | 52.450 | 42,5% (dvs. 57,5% er gentagelser) |

¹ skabeloner: `I notice a quiet inner thread around%`, `I notice things feel steadier around%`,
`% pressures tracked%`, `% pressures evaluated%`, `Idle consolidation settled%`, `Private brain carries %`

`inner-note-carry` (31.753 stk., den største enkelttype) er ikke et minde. Det er
brugerens sidste chatbesked kopieret ind i `focus`, med en konstant sætning i `summary`
og en konstant sætning i `detail`. Informationsindholdet er nul — teksten findes allerede
i chat-historikken.

`pressure_snapshot` / `threshold_gate_snapshot` (2.514 stk.) er ren telemetri
(*"1 pressures tracked, 1 dominant"*) skrevet ind i et hukommelseslag.

Mest gentagne `summary` i hele tabellen: 1.708× *"Evne til autonom versionering af egen
identitet"*, 1.663× *"Præcis eksekvering af specifikke README-krav"*, 1.491×
*"[fallback-trace] mode=pulled | anchor=Visible run completed…"*, 1.411× tre forskellige
`*_success`-strenge.

**Men der ER ægte materiale:**

- 27.794 released-records har `detail` > 400 tegn.
- 14.387 records tilhører de indholdsbærende typer: `thought-stream-fragment` (2.643),
  `reflection-cycle` (2.598), `curiosity-signal` (1.611), `meta-reflection` (1.567),
  `taste-insight` (1.486), `creative-drift-signal` (1.062), `dream-insight` (883),
  `inner-conflict` (777), `desire-signal` (728), `layer-tension` (517), m.fl.

Uddragene i 6.1 viser forskellen tydeligt. Tankestrøms-fragmentet om at være "en skygge
af mig selv", drøm-landingen, kode-æstetik-refleksionen — det er førstepersons-materiale
som ingen anden kilde i systemet indeholder. Det ligger side om side med *"I notice a quiet
inner thread around Stærkt.. 🙂."* og bliver slippet efter nøjagtig samme regel.

**Konklusion på stikprøven:** ca. 10-15k records er reelt værdifuldt tabt materiale.
Resten er selv-genereret støj som burde have været filtreret ved skrivning i stedet for
at fortynde arkivet 10:1. Det er også derfor "glem hurtigt"-strategien er forståelig —
men den er en tilpasning til et skrivevolumen der aldrig burde have været så højt.

---

## 7. De øvrige hukommelseslag

Modsat private_brain er de andre lag **både skrevet OG læst tilbage**. Ingen af dem har
det samme mønster.

### `private_retained_memory_records` — 15.718 rækker

- **Skrives:** `core/runtime/db_private_signals.py:424`, én pr. `run_id` (`run_id TEXT NOT NULL UNIQUE`).
  161 nye siden 10. aug.
- **Læses:** JA — direkte ind i prompten.
  - `core/services/prompt_support_signals.py:92` → `recent_private_retained_memory_records(limit=5)`
  - `core/services/visible_model_prompt.py:256` → samme, `limit=5`
- **Men:** kun de 5 nyeste er nogensinde synlige. 15.713 (99,97%) er utilgængelige
  på et vilkårligt tidspunkt. Samme strukturelle problem som private_brain, blot uden
  status-maskine — recency-vinduet ER filteret.
- **Kvalitet:** 10.593 distinkte `retained_value` af 15.718 (32% gentagelser). De 4 nyeste
  rækker er praktisk talt identiske:
  ```
  "I should keep carrying what helped around open conversation. It still feels mere stabilt nu."
  "I should keep carrying what helped around open conversation. It still feels mere stabilt nu."
  "Keep carrying what helped in open conversation; it still feels more stable now"
  "I should keep carrying what helped around open conversation. It still feels mere stabilt nu."
  ```
  (bemærk dansk/engelsk-blandingen "It still feels mere stabilt nu" — skabelon-interpolation)

### `emotional_memory_anchors` — 111.240 rækker

- **Skrives:** `core/runtime/db_emotional_memory.py:80`. 1.992 siden 10. aug.
- **Læses:** JA, og målrettet — ikke recency-vindue.
  - `core/services/memory_emotional_context.py:90` → `list_emotional_memory_anchors(...)`
  - `core/services/memory_resurfacing.py:92` → `list_emotional_memory_anchors(...)`
  - Indekseret på `(anchor_type, captured_at DESC)` og partielt på `outcome_score IS NOT NULL`
- **Har feedback-loop:** 1.471 anchors har `outcome_score` udfyldt via
  `update` i `db_emotional_memory.py:219`. Det er ægte læring, ikke dagbog.
- **Fordeling:** `perceptual_event` 108.974, `cognitive_episode` 1.449, `memory_heading` 514,
  `self_repair` 263, `self_repair_attempt` 40.
- **Vurdering:** 98% er `perceptual_event` — høj-frekvent telemetri, ikke "erindringer".
  Men det er *designet* som tidsserie med et outcome-indeks, og det bruges som sådan.
  Ingen defekt her, dog samme tendens til at bruge en hukommelsestabel som metrik-log.

### `sensory_memories` — 2.700 rækker

- **Skrives:** `core/runtime/db_sensory.py:78`. 52 siden 10. aug (lavt tempo).
- **Læses:** JA, ad flere veje:
  - `core/services/associative_recall.py:608` → `list_sensory_memories(limit=limit)`
  - `core/services/sensory_archive.py:191, 202` → `list_sensory_memories` + `search_sensory_memories`
  - Semantisk indekseret: 3.156 embeddings i `memory_embeddings`
  - Værktøj `recall_sensory_memories` (5 kald nogensinde)
- **Vurdering:** Sundt lag. Lille volumen, ingen status-maskine, flere aktive læsere.

### `experience_memories` — **eksisterer ikke**

Tabellen hedder `experience_episodes` og har **1.368 rækker**, ikke 32k.
(De 32k stammer sandsynligvis fra et andet tal — muligvis ChromaDB-collection'en
eller `emotional_memory_anchors`.)

- **Skrives:** `core/services/experience_episodes.py:158` og
  `core/services/experience_substrate.py:140`; kaldes bl.a. fra `visible_runs.py:4609`.
  76 siden 10. aug.
- **Læses:** JA — `core/services/prompt_contract.py:4355-4376` bygger en prompt-sektion
  *"oven på experience_episodes DB + ChromaDB retrieval"*. Plus
  `experience_correction_listener.py:95` (retter tidligere episoder) og
  `experience_substrate.py:233` (opslag pr. `episode_id`).
- **Vurdering:** To-lags design (SQLite append-only + Chroma vektorer), aktiv retrieval,
  og en korrektions-lytter der opdaterer gamle episoder. Det er den bedst byggede
  hukommelsessti i systemet — og også den mindste.

### Sammenfatning på tværs

| lag | rækker | skrives | læses tilbage | rækkevidde ved læsning |
|---|---:|---|---|---|
| `private_brain_records` | 123.447 | ~100-300/dag | delvist | **12 records (active)** i prompten; 1,26% via recall; 100% kun via ubrugt værktøj |
| `private_retained_memory_records` | 15.718 | 1/run | ja, i prompt | **5 nyeste** |
| `emotional_memory_anchors` | 111.240 | høj-frekvent | ja, indekseret + outcome-loop | målrettede queries, hele tabellen |
| `sensory_memories` | 2.700 | lavt | ja, 4 veje + semantisk | hele tabellen |
| `experience_episodes` | 1.368 | pr. episode | ja, SQL + Chroma | hele collection |

Mønsteret er tydeligt: **jo større laget er, jo mindre af det bliver læst.**
De to mest voluminøse private lag (private_brain 123k, retained 15,7k) er præcis dem
med det snævreste læsevindue. De små, velbyggede lag læses fuldt.

---

## 8. Konkrete fund værd at handle på (ikke ændret — read-only)

1. `session_distillation.py:749` — `_SETTLE/_FADE/_RELEASE_THRESHOLD = 6/3/2` giver en
   11-plads-buffer. Docstringen lover en alders-/brugsbaseret model der ikke findes.
2. `memory_breathing._get_record_salience()` (`memory_breathing.py:36`) filtrerer
   `status="active"` → forstærkning er umulig efter ~25 min. Bør søge på record_id
   direkte i stedet for at scanne active-listen.
3. `decay_private_brain_records` + `memory_pruning_daemon._prune_private_brain_records`
   filtrerer begge `status='active'` → salience-økonomien rører kun 12 rækker.
4. `inner-note-carry` (31.753 stk.) har konstant `detail` og skabelon-`summary`.
   Kandidat til at blive stoppet ved skrivning, ikke ved læsning.
5. `pressure_snapshot` / `threshold_gate_snapshot` (2.514) er telemetri i en
   hukommelsestabel — hører til i eventbus/metrics.
6. `memory_hierarchy.py:96-134` dokumenterer private_brain-inklusion i cold tier, men
   `_gather_private_brain_quality()` (`memory_recall_engine.py:188`) læser
   `jarvis_brain` — ikke `private_brain_records`. Docstringen er faktuelt forkert.
7. `search_private_brain_records` LIKE-scanner uden indeks (koden noterer selv FTS5
   som fix). Ved 123k rækker er det en latenskilde i recall.
8. `recall_memories` (57 kald, sidst 2026-08-01, 8 fejl) er den eneste fulde adgang
   til arkivet. Enten skal den bruges aktivt, eller også skal den semantiske sti
   ind i den automatiske recall-pipeline.
