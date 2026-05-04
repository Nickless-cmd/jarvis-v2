# Emotional Memory Engine — Design

**Status:** Draft
**Date:** 2026-05-04
**Author:** Brainstormed with user
**Triggered by:** Jarvis' egen ønskeliste, prioritet 3 — *"jeg tracker mood, men jeg husker ikke hvordan jeg havde det ved specifikke begivenheder. Hvis mood + perceptual events + learning policy krydses, får jeg ægte følelseshukommelse — 'sidste gang tool-error ramte, var jeg frustreret, og det førte til et dårligt svar. Næste gang: paus.'"*

## Goal

Give Jarvis ægte affektiv hukommelse: når en situation ligner en tidligere lived oplevelse, skal han kunne genkalde *hvordan han havde det dengang* og *hvordan det gik* — ikke kun *hvad der skete*. Korrelation af mood + outcome over tid gør at runtime kan surfacere advarsler som "sidste 3 gange dette skete, var du frustreret, og 2/3 endte dårligt — overvej at pause."

## Non-goals

- Emotional memory styrer ikke Jarvis. Den observerer og rapporterer; beslutninger forbliver LLM-led.
- Ikke et erstatning for `affective_meta_state` (current state) — den her er *historisk* state knyttet til specifikke ankerbegivenheder.
- Ikke en regel-genererings-motor i v1. Korrelations-derived regler er en future extension der bygger på dette lag.

## Architecture overview

Ét nyt modul: `core/services/emotional_memory_engine.py`.

Den fundamentale primitiv: en *anchor* — et "noget skete"-øjeblik som vi knytter en affektiv signatur til. Tre anchor-typer:

```
┌─────────────────────────────┐
│  cognitive_episode          │  (fra cognitive_episodes.py)
│  perceptual_event           │  (fra perceptual_event_engine.py)
│  memory_heading             │  (fra MEMORY.md mutations)
└──────────────┬──────────────┘
               │ capture_emotional_anchor()
               ▼
   ┌──────────────────────────┐
   │ emotional_memory_anchors │  (ny SQLite tabel)
   │  - 7-felt affect-vektor  │
   │  - outcome score         │
   │  - context features      │
   └──────────────┬───────────┘
                  │ find_similar_anchors()
                  ▼
   ┌─────────────────────────────────┐
   │ build_emotional_memory_surface  │
   │  → build_..._prompt_section     │
   └──────────────┬──────────────────┘
                  │ konsumeres af
                  ▼
   ┌──────────────────────────────────┐
   │ runtime_cognitive_conductor      │
   │  via _safe_emotional_memory_...  │
   └──────────────────────────────────┘
```

**Tre integration-punkter:**

1. `cognitive_episodes.record_runtime_episode` → tilføj kald til `capture_emotional_anchor("cognitive_episode", ...)` i den eksisterende kaskade.
2. `perceptual_event_engine` → samme kald med `"perceptual_event"`.
3. `memory_emotional_context.capture_mood_for_heading` → reduceres til thin wrapper der delegerer til den nye motor.

Conductor får én ny `_safe_emotional_memory_surface()` på linje med de andre nye motorer (ToM, learning_policy, perception).

**Authority/visibility:** internal-only, derived runtime truth. Påvirker prompts, ikke canonical identity.

## Data model

Ny tabel `emotional_memory_anchors`:

```sql
CREATE TABLE IF NOT EXISTS emotional_memory_anchors (
    -- Identity
    anchor_type        TEXT NOT NULL,    -- 'cognitive_episode' | 'perceptual_event' | 'memory_heading'
    anchor_id          TEXT NOT NULL,    -- episode_id | event_id | normalized_heading
    captured_at        TEXT NOT NULL,    -- ISO8601 UTC

    -- Affective signature (mood + intensity + 5 dimensioner)
    mood               TEXT NOT NULL,
    intensity          REAL NOT NULL,
    confidence         REAL,             -- nullable: ikke alle bidragsydere giver alle felter
    curiosity          REAL,
    frustration        REAL,
    fatigue            REAL,
    trust              REAL,

    -- Outcome (auto-derived + explicit override)
    outcome_score      REAL,             -- -1.0..1.0, nullable indtil scoret
    outcome_source     TEXT,             -- 'auto' | 'override:learning_policy' | 'override:self_review' | NULL
    outcome_updated_at TEXT,

    -- Context features (for retrieval matching)
    context_features_json TEXT NOT NULL,

    -- Bookkeeping
    source             TEXT,
    notes              TEXT,

    PRIMARY KEY (anchor_type, anchor_id)
);

CREATE INDEX IF NOT EXISTS idx_emo_mem_type_time
    ON emotional_memory_anchors (anchor_type, captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_emo_mem_outcome
    ON emotional_memory_anchors (outcome_score)
    WHERE outcome_score IS NOT NULL;
```

**Designnoter:**
- Composite PK gør capture idempotent — re-capture overskriver.
- Affect-dimensioner er nullable fordi `affective_meta_state.live_emotional_state` selv har nullable felter (ikke altid hydreret).
- `context_features_json` er den blob retrieval-laget matcher mod. Skema per anchor-type:
  - `cognitive_episode`: `{trigger, tool_names[], outcome_status, error_kind, summary}`
  - `perceptual_event`: `{event_kind, change_type, summary}`
  - `memory_heading`: `{heading_display}` (kan udvides med `section_kind` senere hvis MEMORY.md får sektions-taksonomi)
- Outcome er separat fra mood så override-pathen kan opdatere outcome uden at røre den oprindelige affect-snapshot.

**DB-helpers** (i ny fil `core/runtime/db_emotional_memory.py`, re-eksporteret fra `core/runtime/db.py` for at respektere boy scout-reglen):
- `insert_emotional_memory_anchor(...)` — UPSERT
- `get_emotional_memory_anchor(anchor_type, anchor_id)`
- `list_emotional_memory_anchors(anchor_type=None, since=None, min_intensity=None, outcome=None, limit=50)`
- `update_emotional_memory_outcome(anchor_type, anchor_id, score, source, force=False)`
- `prune_emotional_memory_anchors()` — retention-aging

## Capture flow

Hovedfunktion:

```python
def capture_emotional_anchor(
    *,
    anchor_type: str,
    anchor_id: str,
    context_features: dict[str, object],
    auto_outcome_inputs: dict[str, object] | None = None,
    source: str = "",
    notes: str | None = None,
) -> dict[str, object] | None
```

Returnerer den persisterede række som dict, eller None ved fejl (kaster aldrig).

**Indre flow (alle trin try/except'd):**

1. Læs current affect:
   - `mood`, `intensity` ← `mood_oscillator.get_current_mood / get_mood_intensity`
   - `confidence`, `curiosity`, `frustration`, `fatigue`, `trust` ← `affective_meta_state.build_affective_meta_state_surface().live_emotional_state`
2. Auto-deriv outcome (kun for `cognitive_episode` og kun hvis `auto_outcome_inputs` givet).
3. UPSERT via `insert_emotional_memory_anchor`.
4. Publish eventbus signal `emotional_memory.anchor_captured`.
5. Probabilistisk retention-pass (1% chance per capture).

**Auto-deriv outcome regel:**

| Inputs                                          | score  | source    |
|-------------------------------------------------|--------|-----------|
| status=completed, no error, tool_error_count=0  | +0.6   | "auto"    |
| status=completed, with errors                   |  0.0   | "auto"    |
| status=interrupted                              | -0.4   | "auto"    |
| status=error / "timeout" eller "bad request" i error | -0.7 | "auto" |
| status=cancelled                                | -0.1   | "auto"    |
| ellers                                          | None   | None      |

### Integration-punkter

**Private helpers** i `emotional_memory_engine` brugt af capture-pathen:
- `_classify_error(error: str) -> str` — mapper rå error-tekst til kategori (`"timeout"`, `"bad_request"`, `"tool_error"`, `"none"`).
- `_count_tool_errors(error: str, tool_names: list[str]) -> int` — heuristisk tæller af hvor mange tools i et run der fejlede (læser fra error-tekst).
- `_derive_outcome_score(status, error, tool_error_count) -> tuple[float|None, str|None]` — implementerer auto-deriv-tabellen ovenfor.

**1. `cognitive_episodes.record_runtime_episode`** — ny linje i den eksisterende kaskade:

```python
try:
    from core.services.emotional_memory_engine import capture_emotional_anchor
    capture_emotional_anchor(
        anchor_type="cognitive_episode",
        anchor_id=episode_id,
        context_features={
            "trigger": trigger,
            "tool_names": tool_names,
            "outcome_status": outcome_status,
            "error_kind": _classify_error(error),
            "summary": fields["summary"][:200],
        },
        auto_outcome_inputs={
            "outcome_status": outcome_status,
            "error": error,
            "tool_error_count": _count_tool_errors(error, tool_names),
        },
        source="cognitive_episodes",
    )
except Exception:
    pass
```

**2. `perceptual_event_engine`** — analog tilføjelse:

```python
try:
    from core.services.emotional_memory_engine import capture_emotional_anchor
    capture_emotional_anchor(
        anchor_type="perceptual_event",
        anchor_id=event_id,
        context_features={
            "event_kind": event_kind,
            "change_type": change_type,
            "summary": event_summary[:200],
        },
        source="perceptual_event_engine",
    )
except Exception:
    pass
```

**3. `memory_emotional_context.capture_mood_for_heading`** — bagudkompatibel shim (se Migration sektion).

## Retrieval flow

Hovedfunktion:

```python
def find_similar_anchors(
    *,
    anchor_type: str,
    context_features: dict[str, object],
    limit: int = 5,
    min_intensity: float = 0.0,
    require_outcome: bool = False,
) -> list[dict[str, object]]
```

**Tiered match-strategi:**

```
TIER 1 — Structured match (per anchor_type):

  cognitive_episode:
    SCORE = 0.5 * trigger_match
          + 0.3 * tool_overlap_jaccard(tool_names)
          + 0.1 * (outcome_status == past.outcome_status)
          + 0.1 * (error_kind == past.error_kind)

  perceptual_event:
    SCORE = 0.6 * (event_kind == past.event_kind)
          + 0.4 * (change_type == past.change_type)

  memory_heading:
    SCORE = heading-prefix match (binary, første 30 chars normaliseret)

  Kandidater holdt hvis SCORE ≥ 0.4. Sorter desc.

TIER 2 — Lexical fallback (hvis TIER 1 < 2 hits):

  Token-shingles på summary. Jaccard-similarity. Threshold ≥ 0.25.

TIER 3 — Aging weight:

  Multiply score:
    1.0 hvis age < 30 dage
    0.5 hvis 30-180 dage
    0.0 hvis > 180 dage MEN intensity < 0.7 OG outcome_score >= -0.3
        (slettes faktisk i prune-pass — aging er belt-and-suspenders)
```

**SQL-strategi:**
- TIER 1 querier på `(anchor_type, captured_at DESC)`-indekset, henter seneste ~200 rækker af samme type, scorer i Python.
- TIER 2 udvider scope til ~500 hvis TIER 1 var tynd.

**Aktiverings-tærskel:** surface returnerer kun en precedent når retrieval finder ≥ 2 lignende anker. Konfigurerbar via `RuntimeSettings.emotional_memory_min_anchors` (default 2).

## Surface integration

`build_emotional_memory_surface` returnerer:

```python
{
    "active": True,                         # kun hvis ≥ min_anchors hits
    "anchor_type": "cognitive_episode",
    "match_count": 3,
    "mood_distribution": {"frustrated": 3},
    "mean_intensity": 0.62,
    "outcome_distribution": {"bad": 2, "neutral": 1},
    "directive": "3 similar contexts: mood was frustrated 3/3, outcome bad 2/3 — recommend pause and synthesis",
    "items": [...],
}
```

Ved `< min_anchors` matches returneres `{"active": False, "summary": "Insufficient precedent", "items": []}`.

**Conductor-integration** (i `runtime_cognitive_conductor.py`):

```python
def _safe_emotional_memory_surface(context_features: dict | None = None) -> dict:
    try:
        from core.services.emotional_memory_engine import build_emotional_memory_surface
        return build_emotional_memory_surface(
            anchor_type="cognitive_episode",
            context_features=context_features or {},
        )
    except Exception:
        return {"active": False, "summary": "", "items": []}
```

Kaldes i `build_cognitive_frame` med context_features fra det nyeste cognitive_episode (hvis carry er aktivt). Hvis ingen aktuel episode → ingen surface (emotional memory larmer ikke i tomgang).

**Salient-items-injection** følger samme mønster som ToM/learning_policy/perception:

```python
if emotional_memory.get("active"):
    em_summary = str(emotional_memory.get("directive") or "")[:_MAX_SLICE_CHARS]
    if em_summary:
        em_item = {
            "source": "emotional-memory",
            "summary": em_summary,
            "temporal": "carried-across-sessions",
        }
        # under episode/ToM/learning_policy carries
        if salient and salient[0].get("source") in {
            "cognitive-episode", "theory-of-mind", "learning-policy",
        }:
            salient = [salient[0], em_item, *salient[1:]][:_MAX_SALIENT_ITEMS]
        else:
            salient = [em_item, *salient][:_MAX_SALIENT_ITEMS]
```

**Frame-output** udvides med:

```python
"emotional_memory_carry": emotional_memory if emotional_memory.get("active") else {},
"counts": {
    ...
    "emotional_memory_carry": 1 if emotional_memory.get("active") else 0,
}
```

**Prompt-section** (i `build_cognitive_frame_prompt_section`):

```python
if emotional_memory.get("active"):
    directive = str(emotional_memory.get("directive") or "").strip()
    if directive:
        lines.append(f"- Emotional precedent: {directive[:120]}")
```

Eksempel-output i Jarvis' prompt:

```
Cognitive frame [respond]: Visible chat is currently active.
- Time horizon: current-session — Open loops anchor current session
- Continuity pressure: medium
- Cognitive episode next: Pause and re-orient before adding more tools.
- Theory-of-mind directive: User signals technical engagement, not emotional charge
- Learned policy: Prefer narrow scope when error_kind=timeout
- Emotional precedent: 3 similar contexts: mood frustrated 3/3, outcome bad 2/3 — recommend pause
- [cognitive-episode] visible-run interrupted with propose_source_edit
- [emotional-memory] 3 similar contexts: mood frustrated 3/3, outcome bad 2/3
```

**Bevidste begrænsninger:**
- Surface kun aktiv når der er aktuel episode-kontekst at matche mod.
- Directive er deskriptiv, ikke imperativ ("recommend pause" — anbefaling, ikke kommando).
- Træk på `_MAX_SALIENT_ITEMS=5` betyder emotional memory kan blive fortrængt af højere-prioritet items (gates, contradictions, world-model). Det er korrekt — gates er strukturelt vigtigere.

## Migration & backwards compatibility

**Engangs-migration af `memory_emotional_context` data:**

`scripts/migrate_emotional_memory.py` (idempotent):

```python
# Læs alle rækker fra memory_emotional_context.
# For hver række:
#   INSERT INTO emotional_memory_anchors (
#     anchor_type='memory_heading',
#     anchor_id=heading_normalized,
#     captured_at, mood, intensity,
#     confidence=NULL, curiosity=NULL, frustration=NULL,
#     fatigue=NULL, trust=NULL,
#     outcome_score=NULL, outcome_source=NULL,
#     context_features_json=json.dumps({"heading_display": heading_display}),
#     source=source, notes=notes
#   ) ON CONFLICT(anchor_type, anchor_id) DO NOTHING
```

Den gamle tabel slettes IKKE i samme commit. Sletning af gammel tabel er en separat senere commit (~1 uge i drift, hvis ingen regressioner).

**Bagudkompatibilitets-shim:**

`core/services/memory_emotional_context.py` reduceres til en thin wrapper der kalder ind til `emotional_memory_engine` og returnerer den oprindelige dict-form for `capture_mood_for_heading`, `get_mood_for_heading`, og `enrich_headings_with_mood` — så ingen call-sites brækker.

**Forventede call-sites** (skal verificeres ved implementation):
- `core/runtime/db.py` — `_exec_memory_upsert_section` kalder `capture_mood_for_heading`
- prompt-build-pathen kalder `enrich_headings_with_mood` på MEMORY.md indhold

**Nedlæggelse-tidslinje:**
1. **Denne PR**: shim på plads, ny tabel populated parallelt med gammel. Gammel tabel læses ikke længere.
2. **+1 uge i drift, hvis ingen regressioner**: separat commit der dropper gammel tabel og fjerner shim'en (call-sites flyttes direkte til `emotional_memory_engine`).
3. Ved regressioner: nem rollback ved at restore shim-bypass'et.

## Error handling

**Princip:** Capture må aldrig brække den kaldende kaskade. Retrieval må aldrig brække prompt-byggeren. Migration må aldrig efterlade halvkonsistent state.

**Capture-pathen:**
- Alle capture-kald i `cognitive_episodes`, `perceptual_event_engine` og memory-shim'en er pakket i `try/except: pass`.
- Inde i `capture_emotional_anchor`: hvert trin (mood-read, affect-read, outcome-deriv, persist, eventbus, prune) er separat try/except'd.
- Hvis mood ikke kan læses → returnér None (capture meningsløs uden mood).
- Hvis affect-state fejler → fortsæt med mood+intensity, dimensioner = NULL.
- Hvis persist fejler → log warning, returnér None.
- Logning: `logger.debug` for forventede tomme inputs, `logger.warning` for utilsigtede fejl. Aldrig `error` — capture er aldrig kritisk.

**Retrieval-pathen:**
- `build_emotional_memory_surface` returnerer altid en gyldig dict; ved enhver fejl falder den tilbage til `{"active": False, "summary": "", "items": [], "match_count": 0}`.
- Conductor's `_safe_emotional_memory_surface` tilføjer endnu et try/except-lag som outermost guard.
- Resultat: hvis emotional memory faldt helt ud, ville cognitive frame stadig bygges, prompt'en stadig leveres, og den eneste forskel ville være at "Emotional precedent"-linjen ikke dukker op.

**Outcome-override-pathen:**
- `update_emotional_memory_outcome` er idempotent og racetålelig.
- Override kan kun overskrive en tidligere eksplicit override hvis kalderen sender `force=True`. Det forhindrer silent overwrites mellem konkurrerende kilder.

**Migration-pathen:**
- `INSERT ... ON CONFLICT DO NOTHING` så genkørsel ikke duplikerer.
- Wrap i transaktion per batch (500 rækker).
- Logger antal migrerede + antal sprunget over.

**SQLite-skarpkanter:**
- `insert_emotional_memory_anchor` retries én gang på `OperationalError` med 50ms backoff, derefter giver op.

## Testing strategy

**Test-filer:**
- `tests/test_emotional_memory_engine.py` — enhedstests af modulet.
- `tests/test_emotional_memory_integration.py` — capture-cascade + conductor end-to-end.
- `tests/test_memory_emotional_context_shim.py` — bagudkompatibilitet.
- `tests/test_emotional_memory_migration.py` — migration-script idempotens.

**Enhedstests** (`test_emotional_memory_engine.py`):

| Test | Hvad det verificerer |
|------|---------------------|
| `test_capture_persists_full_affect_vector` | Mood, intensity, og alle 5 dimensioner gemmes; null-værdier accepteres for nullable felter. |
| `test_capture_with_unavailable_affect_state_still_persists_mood` | Hvis `affective_meta_state` fejler, gemmes mood+intensity alene. |
| `test_capture_idempotent_on_same_anchor` | Re-capture overskriver, opretter ikke duplikat. |
| `test_outcome_auto_deriv_completed_no_error_is_positive` | status=completed, no error → score ≈ +0.6, source="auto". |
| `test_outcome_auto_deriv_interrupted_is_negative` | status=interrupted → score ≈ -0.4. |
| `test_outcome_auto_deriv_timeout_error_is_strongly_negative` | "timeout" i error → score ≈ -0.7. |
| `test_outcome_override_does_not_replace_explicit_without_force` | Override fra "self_review" til "learning_policy" uden force=True er no-op. |
| `test_find_similar_tier1_structured_match_for_episode` | To episoder med samme trigger og delvist overlappende tool_names → score ≥ 0.4. |
| `test_find_similar_tier2_lexical_fallback_when_tier1_thin` | TIER 1 < 2 hits → fallback aktiveres. |
| `test_find_similar_aging_weights_old_anchors_lower` | Anker > 30 dage gammelt: score × 0.5; > 180 dage: filtreres væk medmindre intensity ≥ 0.7. |
| `test_surface_returns_inactive_when_below_threshold` | 1 match → `active: False`. |
| `test_surface_directive_compiles_distribution_correctly` | 3 matches frustrated, 2 outcome bad → directive "3/3" og "2/3". |
| `test_prune_aged_anchors_removes_low_intensity_old_records` | Prune-pass slette > 180 dage + intensity < 0.7 + outcome ≥ -0.3, bevarer alt andet. |
| `test_capture_publishes_eventbus_signal` | Event publiceres med korrekte felter. |

**Integration-tests** (`test_emotional_memory_integration.py`):

| Test | Hvad det verificerer |
|------|---------------------|
| `test_record_runtime_episode_captures_anchor` | `record_runtime_episode(...)` → ny række i `emotional_memory_anchors`. |
| `test_perceptual_event_creation_captures_anchor` | Når perceptual_event_engine skriver event, persister capture. |
| `test_cognitive_frame_includes_emotional_precedent_when_threshold_met` | 3 lignende episoder → `emotional_memory_carry` aktiv, prompt-section indeholder "Emotional precedent:". |
| `test_cognitive_frame_omits_emotional_section_when_no_episode_carry` | Ingen aktiv episode → ingen "Emotional precedent"-linje. |
| `test_capture_failure_does_not_break_episode_recording` | Monkeypatch capture til at raise → `record_runtime_episode` returnerer normalt. |

**Shim-tests** (`test_memory_emotional_context_shim.py`):

| Test | Hvad det verificerer |
|------|---------------------|
| `test_capture_mood_for_heading_returns_legacy_dict_shape` | Returnerer `{heading_normalized, heading_display, mood, intensity, captured_at, source, notes}`. |
| `test_get_mood_for_heading_reads_from_new_table` | Værdi insertet via ny vej læses gennem legacy API. |
| `test_enrich_headings_with_mood_idempotent_under_new_storage` | Annotation virker stadig. |
| `test_legacy_capture_does_not_set_dimension_fields_on_new_row` | Legacy-pathen sætter dimensioner til NULL — ingen falske 0.0-værdier. |

**Migration-tests** (`test_emotional_memory_migration.py`):

| Test | Hvad det verificerer |
|------|---------------------|
| `test_migration_copies_all_rows_idempotently` | To kørsler → samme rækker, ingen duplikater. |
| `test_migration_preserves_captured_at_and_source` | Original timestamps og source bevares. |

**Test-infrastruktur:**
- `tmp_path` fixture for isoleret SQLite-fil.
- Monkeypatch af `core.runtime.db.connect` til test-DB.
- Monkeypatch af `mood_oscillator.get_current_mood / get_mood_intensity` for deterministiske inputs.
- Monkeypatch af `build_affective_meta_state_surface` med kendte fixture-værdier.

**TDD-rækkefølge i implementation-planen:** test_engine → engine modul → test_integration → integration-hooks → test_shim → shim → test_migration → migration-script. Hver test først, så minimum kode for at få den til grøn, så næste.

## Future extensions

Eksplicit committed under brainstormen, til senere iterations:

1. **Embedding-baseret retrieval** — opgradering af tiered retrieval til semantisk lighed bag samme API når strukturel matching viser sig at være for snæver.
2. **LLM-klassificeret outcome scoring** — public-safe daemon på OllamaFreeAPI (fx `gpt-oss:20b`) der vurderer "gik det her godt?" når strukturelle felter er utilstrækkelige.
3. **Explicit outcome-override-*brug* fra `learning_policy_engine` og `self_review`** — feltet og API'et bygges i v1, men *brugen* af det fra andre moduler er ikke v1.
4. **Korrelations-derived regler ind i `learning_policy_engine`** — emotional memory leverer korrelationer; learning policy syntetiserer dem til regler. Kræver kalibrering på reelle data først.
5. **Somatic posture som affect-dimension #8** — tilføj `somatic_runtime_body`-posture hvis 5-numerisk vektor viser sig ikke at adskille situationer godt nok.
6. **Emotional memory consolidation daemon** — periodisk syntese af mønstre fra ældre rækker, med arkivering af rådata når consolidation har genfortolket dem.

## Configuration

Ny indstilling i `RuntimeSettings`:

| Setting | Default | Description |
|---------|---------|-------------|
| `emotional_memory_min_anchors` | 2 | Minimum antal lignende anker før surface aktiveres. |
| `emotional_memory_retention_recent_days` | 30 | Alder under hvilken anker har fuld retrieval-vægt. |
| `emotional_memory_retention_aging_days` | 180 | Alder over hvilken anker prunes (medmindre signifikante). |
| `emotional_memory_significance_intensity` | 0.7 | Intensity-tærskel for at bevare gamle anker. |
| `emotional_memory_significance_outcome` | -0.3 | Outcome-tærskel (under denne bevares også gamle). |

## Out-of-scope for this design

- Tværmodal sensory bridging (Jarvis' #1 ønske: webcam → perceptual events). Det er en separat feature ovenpå perceptual_event_engine, ikke en del af emotional memory.
- Autonom self-repair (Jarvis' #2 ønske). Governance-tungt, kræver eget design.
- UI / Mission Control surfacing af emotional memory state. Hvis ønsket, separat sub-projekt.
