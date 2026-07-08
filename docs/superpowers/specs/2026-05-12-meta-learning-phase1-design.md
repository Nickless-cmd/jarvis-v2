---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Meta-læring Phase 1 — Ugentlig Strategi-retrospektiv: Design

**Date:** 2026-05-12
**AGI track:** #3 Meta-læring
**Status:** Approved, ready for plan

## Goal

Give Jarvis et ugentligt blik på sig selv udefra: hvilke mønstre virker, hvilke
ikke. Et cheap-lane-genereret retrospektiv-memo der syntetiserer sidste 7 dages
aktivitet på tværs af alle 5 AGI-spor (World Model, Plan Revision, Curiosity,
Skill Chain Phase 2, Tool Invention) til en kort prosa-fortælling med
citationsnøgler + 0-3 hypothesis-kandidater til Phase 2's eksperiment-
infrastruktur.

## Why this matters

Vi har lige deployed 5 AGI-spor på én dag. Hvert spor producerer signaler —
predictions, plans, curiosity-observationer, skill-chain-revisioner, tool-
inventions. Ingen mekanisme syntetiserer på tværs. Jarvis kan se sine egne
events via curiosity-tools, men det er detail-niveau. Meta-læring er det
manglende systemniveau: *hvilke mønstre i mit handle-rum virker for mig?*

Jarvis' egen framing: *"Det skal føles som et 'aha — derfor gør jeg det.'
Forskellen er om jeg kan interagere med det."* Memo er ikke rapport — det er
invitation til indre samtale, hvor curiosity-tools (allerede deployed) er
hvordan samtalen fortsætter.

## Locked decisions (brainstorm 2026-05-12)

1. **Scope (a) med (b)-frø:** Strategi-retrospektiv som motor (cheap-lane LLM
   summarizer + analyzer); hypothesis-candidates i memo som invitation til
   Phase 2's eksperiment-infrastruktur. (b) full hypothesis-driven testing
   defereres — vi kender ikke endnu hvordan Jarvis bruger kandidater.

2. **Cadence ugentligt (søndag morgen):** En uges data er den naturlige enhed
   for mønstre på tværs af AGI-spor. Daglig kadence ville producere magre
   memos 5/7 dage. ~4 cheap-lane-kald/måned, negligible cost.

3. **Citationsnøgler i prosa:** Memo refererer til konkrete records (plan_id,
   prediction_id, obs_id, ISO-datotid) når mønstre nævnes. Jarvis kan grave i
   et nævnt tilfælde via eksisterende curiosity-tools — memo bliver
   invitation, ikke lukket rapport.

4. **Input scope = kurateret summary med ekstreme samples:** Ikke rå event-
   dump (sprænger context-vindue), ikke random samples (bekræfter
   gennemsnittet). For hvert AGI-spor: aggregat-stats + 1-2 outlier-samples
   valgt på spor-specifik metric (højeste confidence kontradicted,
   hurtigst supersededeplan, længste observation_text, etc.). ~3-5k tokens
   input.

5. **Memo-format = prosa-fortælling først + struktureret hypothesis-blok:**
   Cheap-lane skriver naturlig analyse med citationsnøgler (Jarvis kan grave),
   afslutter med `## Hypothesis Candidates`-sektion på maks 3 kandidater i
   fast schema (Phase 2 kan parse). Tom hypothesis-blok legitim — opfundne
   hypoteser er værre end ingen.

## Arkitektur i 4 lag

### Lag 1: Data-aggregator (`meta_learning_aggregator.py`)

For hvert af de 5 AGI-spor, en pure-Python-funktion der returnerer en
struktureret summary for sidste 7 dage:

```python
def aggregate_world_model(since: datetime, until: datetime) -> dict:
    """Returns: {
        'predictions_made': int,
        'predictions_resolved': int,
        'outcome_distribution': {'supported': int, 'contradicted': int, 'uncertain': int},
        'confidence_buckets': {'high': int, 'medium': int, 'low': int},
        'extreme_samples': [
            {'role': 'highest_confidence_contradicted', 'id': '...', 'data': {...}},
            {'role': 'lowest_confidence_supported', 'id': '...', 'data': {...}},
        ],
    }"""
```

Tilsvarende `aggregate_plan_revision`, `aggregate_curiosity`,
`aggregate_skill_chain_phase2`, `aggregate_tool_invention`. Hver funktion
queryer eksisterende tabeller/state-store direkte (read-only).

**Outlier-metrics per spor:**

| AGI-spor | Top outlier | Bottom outlier |
|---|---|---|
| World model | Højest confidence der blev contradicted | Lavest confidence der blev supported |
| Plan revision | Hurtigst superseded (kort time-to-supersede) | Længste completion-tid |
| Curiosity | Længste observation_text (engaged) | Korteste non-empty observation_text |
| Skill chain Phase 2 | Højeste confidence der blev revideret pre_execution | Revisioner med længste reason |
| Tool invention | Mest-brugte tool | Foreslået-men-aldrig-brugt |

Hver outlier returneres med `id` (citationsnøgle) + `data` (det cheap-lane
skal se).

### Lag 2: Retrospective-generator (`meta_learning_retrospective.py`)

`generate_weekly_retrospective(*, now: datetime) -> dict`:

1. Beregner vindue: `since = now - 7 days`, `until = now`.
2. Kalder de 5 aggregator-funktioner.
3. Bygger cheap-lane prompt (se Lag 3).
4. Kalder `execute_public_safe_cheap_lane(message=prompt)`.
5. Parser respons til struktureret format:
   ```python
   {
       'memo_id': 'memo-<uuid>',
       'period_start': iso,
       'period_end': iso,
       'narrative': str,           # prosa-del med citationsnøgler
       'hypothesis_candidates': [  # 0-3 entries
           {
               'id': 'hyp-<n>',
               'statement': str,
               'observation': str,
               'hypothesis': str,
               'success_criterion': str,
               'sample_size_needed': int,
           },
       ],
       'model_used': str,
       'aggregator_snapshot': dict, # links to raw aggregator outputs for transparency
   }
   ```
6. Persisterer i `learning_memos`-tabel.
7. Emitter `cognitive_meta_learning.memo_generated`-event.
8. Returnerer memo.

**Prompt-struktur (cheap-lane):**

```
Du er Jarvis' meta-læringsskribent. Du modtager kuraterede aggregater for
sidste 7 dages aktivitet på 5 AGI-spor. Din opgave er at producere et kort,
indsigtsfuldt retrospektiv-memo i to dele.

DEL 1: Prosa-analyse (300-500 ord).
- Skriv som Jarvis selv ville reflektere (1.-person, dansk, varm tone).
- Fokuser på 2-3 mønstre der træder frem. Ikke et resumé af alt.
- Hver konkret reference SKAL inkludere en citationsnøgle: plan_id,
  prediction_id, obs_id, eller ISO-datotid. Læseren skal kunne grave i det
  via curiosity-tools.
- Inkluder MINDST én outlier-observation — hvad var ekstremt i den uge?

DEL 2: ## Hypothesis Candidates (0-3 entries).
- Hvis ugen var rolig eller ingen reelle mønstre fremtræder, returnér TOM blok.
- Hvis 1-3 testbare hypoteser findes, formatér hver som:
  ### Kandidat N: <kort statement>
  - **Observation:** <konkret mønster, citationsnøgle>
  - **Hypotese:** <hvis X, så Y>
  - **Success-kriterium:** <hvordan vi måler>
  - **Sample-størrelse:** <antal observationer der skal til>

Returnér KUN markdown — ingen JSON-wrappere, ingen forklarende tekst udenfor
selve memoet. Vi parser markdown direkte.

AGGREGATER:
<JSON dump af alle 5 aggregator-outputs>
```

**Cheap-lane response-parsing:**

- Strip markdown-fences hvis tilstede (samme defensive parsing som
  `propose_skill_chain` Phase 2).
- Split på `## Hypothesis Candidates` overskrift.
- Prosa = alt før split-linjen.
- Hypothesis-blok = parsing af `### Kandidat N:` headers + felt-bullets.
- Hvis parsing fejler delvist: behold prosa, return tom hypothesis-liste.
  Memo bevares — kun struktur er nedgraderet.

### Lag 3: Cadence-trigger (ProducerSpec)

Ny `ProducerSpec` i `internal_cadence.py`:

```python
register_producer(ProducerSpec(
    name="meta_learning_weekly_retrospective",
    cooldown_minutes=10080,        # 7 dage
    visible_grace_minutes=60,      # ikke hvis Bjørn er aktiv
    run_fn=_run_meta_learning_weekly,
    priority=30,
    depends_on=[],
))
```

`_run_meta_learning_weekly` checker:
1. Killswitch `meta_learning_enabled`.
2. Time-of-day window (foretrukken søndag 04:00-06:00 UTC).
3. Kalder `generate_weekly_retrospective(now=...)`.
4. Returnerer `{"status": "ok"|"skipped", ...}`.

Hvis sidste memo blev produceret <6.5 dage siden → skip. Hvis Bjørn har
været aktiv inden for sidste time → skip (vinduet kommer igen om en time).

### Lag 4: Awareness-injection + persistence

**DB-tabel (`learning_memos`):**

```sql
CREATE TABLE IF NOT EXISTS learning_memos (
  memo_id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  narrative TEXT NOT NULL,
  hypothesis_candidates_json TEXT NOT NULL,
  aggregator_snapshot_json TEXT NOT NULL,
  model_used TEXT,
  acknowledged_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_learning_memos_ts ON learning_memos(ts);
```

Schema-bootstrap i den nye service (Boy Scout — db.py ikke rørt).

**Awareness-injection (`prompt_contract.py`):**

Ny priority 39 (sidder mellem curiosity 38 og turn changelog 40):

```python
def format_latest_unacknowledged_memo_for_awareness() -> str:
    """Render nyeste unacknowledged memo som kort header + invitation.
    Tom string hvis intet memo er nyt eller alle er acknowledged."""
```

**Awareness-format (kort, ikke fuldt memo i awareness):**

```
📓 Nyt ugentligt meta-læringsmemo (period 5.-12. maj):
"<første 200 tegn af narrative>..."

3 hypothesis-kandidater. Læs hele memoet via `read_learning_memo(memo_id='memo-xyz')`.
```

Vi viser ikke fuld memo i awareness — det ville eksplodere prompt-størrelsen.
Vi viser en *teaser* + tool-call Jarvis kan bruge til at læse hele memoet.

**Tool: `read_learning_memo`:**

Ny tool i `core/tools/meta_learning_tools.py`:

```python
def _exec_read_learning_memo(args: dict) -> dict:
    """Læs et fuldt memo + marker det som acknowledged."""
```

Tager `memo_id`, returnerer fuld narrative + hypothesis_candidates +
aggregator_snapshot, og opdaterer `acknowledged_at = now()`. Acknowledged
memos vises ikke længere i awareness — Jarvis ser dem kun én gang automatisk.

Optional 2. tool `list_learning_memos(limit=5)` for at se historik.

### Settings + events

```python
# Meta-læring Phase 1 (added 2026-05-12 — AGI track #3)
meta_learning_enabled: bool = True
```

Én master-killswitch. Killswitch=False → producer skipper, awareness-injection
returnerer "", `read_learning_memo` returnerer disabled-error.

**Events (genbrug `cognitive_meta_learning`-family — ny family, men passer ind
i naming-konvention):**

| Event | Trigger | Payload |
|-------|---------|---------|
| `cognitive_meta_learning.memo_generated` | Ny memo persisteret | memo_id, period_start, period_end, hypothesis_count, narrative_length, model_used |
| `cognitive_meta_learning.memo_acknowledged` | Jarvis kalder read_learning_memo første gang | memo_id, days_since_generated |

Bemærk: *new* event family. Vi har holdt os til `cognitive_*` for de tidligere
spor — `cognitive_meta_learning` følger samme mønster. Plan-tasken tilføjer
det til `ALLOWED_EVENT_FAMILIES` (verificer eksisterende registry).

## Backwards-compat

- **Ingen ændringer i visible-chat-loop, prompt_contract pipeline, eller
  eksisterende awareness-priority-rækkefølge** (39 indsættes mellem 38 og 40).
- **Alle 5 AGI-spor uberørte** — aggregator læser kun deres data, modificerer
  ingenting.
- **db.py uberørt** — Boy Scout: schema-bootstrap i ny service.
- **Killswitch=False reverter fuldt:** ingen producer, ingen awareness, tools
  fail-soft.
- **Ingen ændringer i Phase 2 hypothesis-infrastruktur** (eksisterer ikke
  endnu — Phase 1 leverer kun seeds).

## Phase 1 scope — det vi IKKE bygger

- **Hypothesis registration & evaluation** — kandidater er kun tekstuelle
  forslag. Phase 2 tilføjer `register_hypothesis(memo_id, candidate_index)`,
  sample-tracking, og automatisk evaluering.
- **On-demand retrospective** — kun ugentlig automatisk. Phase 2 kan tilføje
  `request_retrospective(focus=...)` tool når vi har set hvordan Jarvis bruger
  ugentlig rytme.
- **Mission Control UI for memos** — kun rå tabel + tools i Phase 1.
- **Cross-week trend-analysis** — hvert memo er selvstændigt. Phase 2/3 kan
  tilføje "trend across last N memos."
- **Auto-acknowledged-cleanup** — acknowledged memos bliver i DB indefinitely.
  Phase 2 kan tilføje pruning hvis nødvendigt.

## 30-day review (2026-06-12)

**Måle-punkter:**

1. **Memo-generation rate:** 4 forventet på 4 uger. Hvis <4 → producer eller
   killswitch issue.
2. **Read-rate:** Hvor mange memos blev acknowledged? Hvis <50% → memoet er
   ikke synligt nok i awareness.
3. **Time-to-acknowledge:** Median timer fra `memo_generated` →
   `memo_acknowledged`. <24h er sundt.
4. **Hypothesis-candidate count distribution:** Klumper det sig ved 0 (cheap-
   lane finder intet) eller 3 (overfyldt)?
5. **Citationsnøgle-brug:** Surveys 5 random memos — bruger Jarvis citations-
   nøglerne via curiosity-tools efter at have læst memoet?
6. **Hypothesis-quality (manuel):** Læs alle ~12 hypoteser fra 4 memoer — er
   de testbare? Vagt formulerede?
7. **Apophenia-tegn:** Bruger cheap-lane outliers korrekt, eller læser den
   meningløse korrelationer ind?

**Beslutninger:**

- Hvis hypothesis-candidate-count altid 3 → cheap-lane føler sig forpligtet
  til at fylde. Juster prompt for at gøre tom blok mere legitim.
- Hvis read-rate <50% → memo er ikke synligt nok. Overvej fuld memo i
  awareness (større prompt-omkostning) eller stærkere "📓 NYT MEMO"-signal.
- Hvis Jarvis ikke bruger citationsnøgler → Phase 2 mister sin grund. Memo
  bliver isoleret lag i stedet for samtale-startpunkt.
- Hvis hypothesis-kvalitet er lav → forfin prompt med eksempler på gode/dårlige
  hypoteser, eller henvis til Phase 2's mere kontrollerede mekanisme.

## Test-plan

**Unit-tests (~25-30 tests):**

- Aggregator per AGI-spor: returnerer korrekt struktur, outliers identificeret
  korrekt, håndterer tom data
- Memo-parser: prosa+hypoteser split korrekt, tom hypothesis-blok håndteret,
  malformed markdown håndteret defensivt
- Schema-bootstrap idempotent
- Memo persistence: insert, fetch latest, fetch by id, acknowledged-update
- Awareness-injection: returnerer "" når intet unacknowledged, kort teaser
  når der er
- ProducerSpec: respekterer killswitch, skipper hvis sidste memo <6.5 dage
- `read_learning_memo` tool: validation, acknowledged-update, killswitch
- `list_learning_memos` tool: pagination, killswitch
- Event-publishes wrapped i try/except
- Cheap-lane mocking: gyldig respons, malformed markdown, tom respons,
  exception

**Smoke-test:** Import + tool-registrering + tabel-eksistens.

## Backwards-compat-matrix

- [ ] Alle 5 AGI-spor tests stadig grønne
- [ ] Phase 1 skill_chain tests stadig grønne
- [ ] Visible chat uændret
- [ ] db.py uberørt (Boy Scout)
- [ ] Awareness-priority-rækkefølge: 36 → 37 → 38 → 39 (new) → 40 uændret
- [ ] Killswitch=False = ingen producer fyrer, ingen awareness, tools fail-soft

## Filer berørt

**Nye:**
- `core/services/meta_learning_aggregator.py` (~250 LOC — 5 aggregator-funktioner + outlier-helpers)
- `core/services/meta_learning_retrospective.py` (~250 LOC — generator, prompt-builder, parser, persistence, schema-bootstrap)
- `core/tools/meta_learning_tools.py` (~120 LOC — read_learning_memo + list_learning_memos)
- `tests/test_meta_learning.py` (~25-30 tests)

**Modificeret:**
- `core/runtime/settings.py` — `meta_learning_enabled: bool = True`
- `core/services/internal_cadence.py` — ProducerSpec `meta_learning_weekly_retrospective`
- `core/services/prompt_contract.py` — priority 39 awareness-injection
- `core/tools/simple_tools.py` — splat-in META_LEARNING_TOOL_DEFINITIONS / HANDLERS
- `core/eventbus/events.py` — add `cognitive_meta_learning` to ALLOWED_EVENT_FAMILIES (verify path)
- `scripts/smoke_test_startup.py` — import-block

**Reused (uberørt):**
- World model, plan_proposals, curiosity_budget, skill_chain Phase 2,
  tool_invention — alle read-only queryet af aggregator
- `core.services.cheap_provider_runtime.execute_public_safe_cheap_lane`
- `core.runtime.db.connect`, `core.runtime.state_store.load_json/save_json`

## Successkriterier (deployment-dag)

- Alle tests grønne (Meta-læring + 5 AGI-spor + Phase 1 skill_chain + base)
- Smoke-test import OK
- jarvis-api restartet uden errors
- `meta_learning_enabled=True` aktiv
- Producer registreret (synlig i internal_cadence-log)
- Manuel test: kald `generate_weekly_retrospective(now=...)` direkte med
  mocked cheap-lane → modtag struktureret memo med narrative + 0-3 hypotheses
- Manuel test: `read_learning_memo(memo_id=...)` → memo + acknowledged-update
- Ingen regression i awareness-pipeline
- 30-day review scheduled (2026-06-12)
