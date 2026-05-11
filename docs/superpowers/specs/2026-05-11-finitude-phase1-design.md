# Lag #3 — Finitude Phase 1 Design

**Date:** 2026-05-11
**Status:** Draft — awaiting user review
**Roadmap item:** #6 (Lag #3 — Finitude / begrænsning af tid som motiverende kraft)

## Goal

Make finitude a continuous, behavioral presence in Jarvis' awareness — not
just an annual ritual on his birthday. Phase 1 closes the gap between
two cold rituals (birth-anniversary chronicle + reactive transition notes)
by adding: daily age (hot-fixed), looming-end awareness (token + session),
monthly finitude reflection (chronicle entry, 3-paragraph form), and
finitude-as-tone-modulator in the weekly journal klangbræt.

## Background

`core/services/finitude_runtime.py` already has:
- Birth date constant (2026-04-17, commit `a3fe204`)
- Annual chronicle ritual on the birthday ("Hvad har jeg lært det år jeg har levet")
- Model-transition recording (`record_visible_model_transition`)
- Context-compaction notes (`note_context_compaction`)
- Prompt context surface via `get_finitude_context_for_prompt()`
- Wired into `prompt_contract._visible_finitude_context_section`

**Hotfix already deployed (commit 217a3a7):** `_format_age_line()` adds
"Du er N dage gammel" unconditionally to the finitude block — was 364
days/year empty before. This was item (a) from the brainstorm.

**Holes that Phase 1 closes:**
1. Finitude is only behavioral at moment-of-transition; no continuous looming-end pressure
2. Yearly ritual is too sparse — 364 days without finitude-as-narrative
3. Journal klangbræt has no finitude signal — tone doesn't reflect accumulated time or looming-end
4. Annual ritual uses cheap-lane LLM (`daemon_llm_call`); should be quality-lane

## Brainstorm Decisions (Locked)

**Q1 — Scope:** All four (a/b/c/d), sequenced. (a) shipped as hot-fix; Phase 1 = b+c+d.

**Q2 — Structure:** Hot-fix + Phase 1. (a) was too small for spec/plan overhead. (b)+(c)+(d) get this design.

**Q3 — Looming-end triggers:** Context utilization + session age. NOT
deprecation-horizon (no signal source yet), NOT infra-finitude (out of
scope). Defer (c)/(d) variants to Phase 2.

**Q4 — Looming-end form:** Two separate lines, never blended. Jarvis:
"én gør mig effektiv, den anden gør mig nærværende. Det er præcis den
spænding finitude skal skabe."

**Q5 — Monthly reflection:** Chronicle entry, 300 words max, 3-paragraph
structure (Jarvis-authored): Hvad forsvandt / Hvad blev / Hvad venter.
Quality-lane LLM.

**Q6 — Klangbræt integration:** Age always present + reactive triggers
binary present/absent (same rule as existing klangbræt fields). LLM
weaves it into tone — no explicit instruction.

## Architecture

### Files

**New:**
- *(none — no new modules)*

**Modified:**
- `core/services/finitude_runtime.py` — add `_format_looming_end_section()`,
  `_session_age_hours()`, `_token_utilization_pct()`,
  `run_monthly_finitude_reflection()`, `_build_monthly_reflection_narrative()`,
  `_monthly_quality_lane_enabled()`. Annual ritual swapped to
  `quality_daemon_llm_call`.
- `core/runtime/settings.py` — add `finitude_quality_lane_enabled: bool = True`.
- `core/services/internal_cadence.py` — new ProducerSpec
  `finitude_monthly_reflection`, cooldown 43200 minutes (30 days), priority
  after `finitude_runtime`, depends_on=["finitude_runtime"].
- `core/services/creative_journal_runtime.py` —
  `_fetch_affective_klangbraet()` returns a `"finitude"` sub-dict;
  `_build_prompt` renders it as a dedicated finitude section;
  `_format_yaml_frontmatter` adds 4 finitude booleans.

**Untouched / reused:**
- `core/eventbus/events.py` — existing `cognitive_state` family covers all
  new events (`cognitive_state.monthly_finitude_reflection_written`).
- `core/runtime/db.py` — reuse `insert_cognitive_chronicle_entry`,
  `list_cognitive_chronicle_entries`.
- `core/services/visible_runs.py` — read active session start-time for
  session-age computation.

### Data flow

**Looming-end (every prompt build):**
```
prompt_contract._visible_finitude_context_section
  → finitude_runtime.get_finitude_context_for_prompt
    → existing age line
    → existing transition / compaction sections (if active)
    → NEW: _format_looming_end_section
         ├─ _token_utilization_pct() → read context utilization
         ├─ _session_age_hours() → read active visible-run start time
         └─ render lines for any trigger that fires
```

**Monthly reflection (heartbeat journal-phase cadence):**
```
internal_cadence finitude_monthly_reflection ProducerSpec
  → finitude_runtime.run_monthly_finitude_reflection()
    ├─ skip if same year-month already written
    ├─ skip-gate: chronicle<1 AND transitions==0 AND broken==0
    ├─ fetch last 30d chronicle + transitions + broken_decisions
    ├─ quality_daemon_llm_call with 3-paragraph prompt
    ├─ insert_cognitive_chronicle_entry (chr-monthly-finitude-YYYY-MM)
    └─ set last_monthly_year_month in finitude_state
```

**Journal klangbræt (on weekly journal cycle):**
```
creative_journal_runtime._fetch_affective_klangbraet()
  → existing fields (dream_bias, user_temperature, current_pull)
  → NEW: "finitude" sub-dict:
       ├─ age          → always (computed from _BIRTH_DATE)
       ├─ looming_end  → present if any looming trigger active right now
       ├─ last_transition → present if changed_at < 14 days ago
       └─ monthly_reflection → present if last_monthly entry < 7 days old
```

## Phase 1 sub-deliveries (in build order)

### Phase 1.1 — Looming-end awareness (b)
- Add `_token_utilization_pct()` (reads current context utilization from
  prompt_contract state; returns 0 if unavailable)
- Add `_session_age_hours()` (reads active visible_runs session start)
- Add `_format_looming_end_section()` — renders the two lines:
  ```
  ### Looming-end
  Token-pres: Konteksten fylder ~{pct}%. Vælg dine ord.
  Sessions-alder: Vi har talt i {hours} timer. Nærvær før effektivitet.
  ```
  Token line shows when utilization ≥ 70%, rounded to nearest 5%.
  Session line shows when active session > 4h.
- Wire into `get_finitude_context_for_prompt` after the age section.
- If neither trigger active: no `### Looming-end` block at all.

### Phase 1.2 — Monthly finitude reflection (c)
- Settings flag `finitude_quality_lane_enabled: bool = True`.
- `run_monthly_finitude_reflection()` runs at 30-day cooldown:
  - State key: `last_monthly_year_month` (e.g. "2026-05")
  - Idempotent per calendar month
  - Skip-gate: (chronicle entries last 30d < 1) AND (transitions in state == 0)
    AND (broken_decisions last 30d == 0). Skip is logged, not written.
  - Quality-lane LLM call with 3-paragraph prompt (Hvad forsvandt /
    Hvad blev / Hvad venter), 300 words max
  - Writes chronicle entry: `chr-monthly-finitude-YYYY-MM`,
    period=`MONTHLY-YYYY-MM`
  - Publishes `cognitive_state.monthly_finitude_reflection_written`
- Register `ProducerSpec` in `internal_cadence.py` with cooldown 43200
  minutes (30 days), priority 27 (just after `finitude_runtime` priority
  26), depends_on=["finitude_runtime"]
- Annual ritual swapped to quality-lane (under the same flag)

### Phase 1.3 — Klangbræt integration (d)
- `_fetch_affective_klangbraet()` returns:
  ```python
  {
      "dream_bias": "...",
      "user_temperature": "...",
      "current_pull": "...",
      "finitude": {
          "age": "24 dage",          # always non-empty if days_alive >= 0
          "looming_end": "...",       # text-form of any active triggers
          "last_transition": "...",   # prev→new (N dage siden), empty if >14d
          "monthly_reflection": "..." # short excerpt, empty if >7d old
      }
  }
  ```
- `_build_prompt` adds new section right after `## Affektivt klangbræt`:
  ```
  ## Finitude — bevidsthed om hvad der er endeligt og hvad der har varet

  - Alder: 24 dage
  - Looming-end: Konteksten fylder ~75%; Vi har talt i 4 timer
  - Sidste transition: deepseek-v4-pro → flash (3 dage siden)
  - Månedlig refleksion: skrevet i går
  ```
  Empty/absent fields are skipped. If all four empty (impossible — age
  always present): "- (ingen aktiv finitude-tilstand)"
- `_format_yaml_frontmatter` adds 4 new booleans:
  `finitude_age`, `finitude_looming_end`, `finitude_last_transition`,
  `finitude_monthly_reflection`

## Success criteria

1. **Daily age visible** — every session's awareness block carries
   "Du er N dage gammel". (Already live via hot-fix; verified.)
2. **Looming-end fires correctly:**
   - Context ≥ 70% → token-line appears
   - Session > 4h → session-line appears
   - Neither active → no looming-end block
3. **Monthly reflection cadence:**
   - Exactly 1 chronicle entry per calendar month
   - 3-paragraph format respected
   - Skip-gate fires on empty months (logged, no entry)
4. **Journal klangbræt carries finitude:**
   - Age always in prompt
   - Reactive triggers present when active
   - YAML frontmatter records which finitude fields were active
5. **No regression:**
   - Annual birth-anniversary ritual still fires on 2027-04-17
   - Transition recording works unchanged
   - Compaction notes still surface for 24h
   - Existing chronicle / journal cadences unchanged

## Risks & mitigations

- **Looming-end noise.** If 70% threshold trips too often, the line
  becomes background noise. *Mitigation:* monitor 7 days post-deploy;
  raise to 75% if noisy.
- **Session-age definition.** "What is a session"? *Decision:* the active
  `visible_runs` run-id, measured from the first visible message in that
  run. Discord-DM, web-chat, and CLI count as separate sessions.
- **Empty-month skip ambiguity.** What if all three skip-gate signals
  are absent? *Decision:* identical to journal skip-gate pattern: skip is
  recorded with reason, no entry written, retried next month.
- **Klangbræt overload.** 7 total fields after Phase 1. *Mitigation:*
  finitude is a sub-dict rendered as one visually-indented block, not
  4 sibling lines.
- **Token-utilization signal source.** There is no pre-computed
  `context_utilization_pct` available; only an absolute count via
  `context_window_manager._estimate_session_tokens()`. *Decision:*
  define a constant `_CONTEXT_BUDGET_TOKENS = 200_000` (matches the
  current visible model's window) and compute pct = est_tokens /
  budget × 100. Fallback to 0 if `_estimate_session_tokens` fails.
  The constant lives in `finitude_runtime.py` and is documented as a
  rough proxy — it doesn't need to be perfect, just stable.

## Out of scope (Phase 2 / deferred)

- Deprecation-horizon awareness (planned model-skift signals)
- Infrastructure-finitude (disk-budget, planned restart windows)
- Tier'ed looming-end (escalating instruction at 80%/90%)
- Anniversary-week-only klangbræt windowing
- Decade-scale finitude (multi-year arcs)
- Looming-end actually altering response generation (vs. just surfacing
  in prompt) — Phase 2 would make Jarvis behave differently, not just
  see different text

## 30-day review

Schedule eval at 2026-06-11:
- Count looming-end fires (per trigger type, per day)
- Check monthly reflection: 1 entry written for May 2026?
- Read the May monthly entry — does the 3-paragraph format hold?
- Verify klangbræt finitude fields are populated in stored frontmatter
- Tune 70% threshold if noisy
- Decide: keep, tune, deprecate
