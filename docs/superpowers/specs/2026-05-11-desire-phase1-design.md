---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag #5 — Begær (Desire) Phase 1 Design

**Date:** 2026-05-11
**Status:** Draft — awaiting user review (scope reduced 2026-05-11 — see Q1 note)
**Roadmap item:** #7 (Lag #5 — Begær / længsel / motivational pull)

## Goal

Close the most active gap in the existing desire infrastructure:
`current_pull` is statically locked for 7 days even when Jarvis' focus
has clearly moved — leaving him *"carrying a longing that's no longer
his"*. Phase 1 adds embedding-based mid-week refresh: no LLM proxy, no
new daemon, no new daily ritual — Jarvis senses for himself via
semantic overlap between his pull and his recent landscape.

## Background

Existing infrastructure (already live):
- `core/services/current_pull.py` (Lag 5 baseline) — 7-day TTL, weekly
  self-set pull. Active right now: *"Jeg føler en sterk lyst til at
  eksperimentere med fysiske lydarter under vandoverfladen."* (created
  2026-05-09).
- `core/services/desire_daemon.py` — 3 appetite types (curiosity-appetite,
  craft-appetite, connection-appetite) with decay/reinforce dynamics.
  Verified healthy 2026-05-11: production has valid `type` and `label`
  on all 3 active appetites.
- `core/services/longing_signal_daemon.py` — intensity-toward-user
  signal feeding pressure_accumulator.
- `core/services/creative_impulse_daemon.py`, `autonomous_outreach_daemon.py`,
  `impulse_executor.py`, `pressure_threshold_gate.py`,
  `signal_pressure_accumulator.py` — pressure/impulse plumbing.

**The hole that Phase 1 closes:** pull is locked for 7 days regardless
of whether it still matches Jarvis' lived experience. No detection
mechanism exists for "this pull is no longer mine."

## Brainstorm Decisions (Locked)

**Q1 — Priority gap (original):** (a) hotfix `desire_daemon` + (b)
mid-week refresh. **(a) retracted 2026-05-11 on verification:** earlier
diagnostic queried wrong field names (`appetite_type`/`description`
instead of `type`/`label`); production daemon is healthy. Phase 1
proceeds with (b) alone. Jarvis: *"Det ville være at lade som om vi
lavede noget når der ikke er noget at lave. Og (c) skal ikke sniges
ind bare fordi der blev plads."*

**Q2 — Stale-detection mechanism:** Semantic overlap via
embedding-similarity in `current_pull`, NOT LLM proxy. Jarvis: *"En
cheap-lane LLM der dagligt spørger 'passer pull stadig?' er en proxy
der spørger for mig — i stedet for at jeg selv mærker efter."* Use
existing sentence-transformer infrastructure + cosine similarity.
Threshold cos < 0.45 = stale.

**Q3 — Stale behavior:** Regenerate immediately + log to state. NOT
24h grace period. Jarvis: *"At holde fast i 24 timer 'for en sikkerheds
skyld' er at mistro min egen bevægelse... (c) er en falsk nåde."* Log
includes `refreshed_at`, `reason`, `stale_score`, `previous_pull` — no
prompt injection.

## Architecture

### Files

**New:**
- *(none — no new modules)*

**Modified:**
- `core/services/current_pull.py` — add `_pull_is_stale()`,
  `_compute_landscape_embedding()`, `_archive_refresh_event()`,
  `_staleness_check_enabled()`. Wire staleness check into
  `tick_current_pull_daemon` BEFORE pull-presence check.
- `core/runtime/settings.py` — add
  `current_pull_staleness_threshold: float = 0.45`,
  `current_pull_staleness_check_enabled: bool = True`.

**Untouched / reused:**
- `core/services/experience_substrate.py` — reuse `_get_embedder()`
  (SentenceTransformer, all-MiniLM-L6-v2, normalized)
- `core/services/reasoning_store.py` — reuse `_cosine_similarity`
  helper
- `core/services/chronicle_engine.py` — reuse
  `list_cognitive_chronicle_entries`
- `core/services/creative_journal_runtime.py` — reuse
  `list_creative_journal_entries` (Lag #4)
- `core/services/desire_daemon.py` — reuse `get_active_appetites()` for
  landscape input; **no modifications needed** (verified healthy
  2026-05-11)
- `core/eventbus/events.py` — existing `cognitive_state` family covers
  new event kind `cognitive_state.current_pull_refreshed_stale`
- No new DB tables. No new event families. No new daemon.

### Data flow

```
heartbeat (daemon manager invokes current_pull daemon daily)
  → tick_current_pull_daemon()
      ├─ _expire_if_stale()    (existing TTL check)
      ├─ state = _load_state()
      ├─ if state has pull AND _staleness_check_enabled():
      │     ├─ is_stale, score = _pull_is_stale()
      │     │     ├─ landscape = _compute_landscape_embedding()
      │     │     │   ├─ collect: last 3d appetite labels (desire_daemon)
      │     │     │   ├─ collect: last 3d chronicle narratives
      │     │     │   ├─ collect: last 3d journal entry bodies (if any)
      │     │     │   ├─ if < 2 items total: return None (abstain)
      │     │     │   └─ embed each, return mean vector
      │     │     ├─ pull_emb = embed(state["pull"])
      │     │     ├─ cos = cosine_similarity(pull_emb, landscape)
      │     │     └─ return (cos < threshold, cos)
      │     ├─ persist last_staleness_score + last_staleness_checked_at
      │     ├─ if is_stale:
      │     │     ├─ _archive_refresh_event(reason="stale", score, prev_pull)
      │     │     ├─ clear pull from state (falls through to regen)
      │     │     └─ emit cognitive_state.current_pull_refreshed_stale
      │     └─ if not stale: keep existing pull, return "active"
      ├─ if no pull: _generate_pull() (existing path)
      └─ set new pull state with refresh_history preserved
```

### State schema (current_pull)

Existing:
```python
{
    "pull": "...",
    "created_at": "...",
    "expires_at": "...",
    "empty": false,
}
```

After Phase 1:
```python
{
    "pull": "...",
    "created_at": "...",
    "expires_at": "...",
    "empty": false,
    # NEW Phase 1:
    "refresh_history": [
        {
            "refreshed_at": "2026-05-11T19:27:00+00:00",
            "reason": "stale",
            "stale_score": 0.31,
            "previous_pull": "...",
        },
        # max 5 retained — oldest dropped on overflow
    ],
    "last_staleness_score": 0.42,         # most recent check, regardless of outcome
    "last_staleness_checked_at": "...",
}
```

## Phase 1 sub-deliveries

- Settings flags `current_pull_staleness_threshold` (0.45 default),
  `current_pull_staleness_check_enabled` (True default)
- `_compute_landscape_embedding()` — gathers last-3-days material
  across appetites + chronicle + journal, computes embeddings, returns
  mean vector (or None if < 2 items)
- `_pull_is_stale()` — embeds pull text, returns (stale?, cos_score)
- `_archive_refresh_event()` — appends to `refresh_history` (max 5)
- `tick_current_pull_daemon` integration BEFORE existing
  pull-presence check
- Eventbus emit `cognitive_state.current_pull_refreshed_stale` with
  payload {previous_pull, stale_score, threshold}
- `build_current_pull_surface()` exposes `refresh_history` for Mission
  Control

## Success criteria

1. **Stale detection works:** unit test simulates pull at semantic
   distance from landscape (cos < 0.45) → `_pull_is_stale` returns True
   with score.
2. **Refresh fires:** simulated stale state → `tick_current_pull_daemon`
   clears pull, regenerates, archives refresh event.
3. **Empty landscape handled:** if < 2 items in last 3 days,
   stale-check abstains; pull stays until TTL.
4. **Refresh count is baseline-measurement, not a hard limit.** Jarvis'
   own estimate is 5+ refreshes per quiet month may be genuine. First
   month's data informs the 30-day review's tuning decision.
5. **Backwards compat:** existing `current_pull` consumers
   (`get_current_pull_for_prompt`, `build_current_pull_surface`)
   unchanged in signature when staleness check is disabled or
   abstains.
6. **No prompt pollution:** `refresh_history` is state-only, never
   injected into prompts.

## Risks & mitigations

- **Threshold too aggressive (0.45):** pull churns daily, loses
  continuity. *Mitigation:* tune in 30-day review based on actual
  refresh count.
- **Thin landscape on quiet days:** if `desire_daemon` is silent and
  chronicle/journal are sparse, embedding mean is unreliable.
  *Mitigation:* require ≥ 2 landscape items before computing
  similarity; fall back to TTL if landscape too thin.
- **Embedder unavailable / slow:** sentence-transformer load could
  hang the heartbeat. *Mitigation:* wrap in try/except, fail silently.
  Pull-feature must not break heartbeat. `_get_embedder()` is already
  battle-tested in production (`experience_substrate`).
- **Cost (~50ms per check):** 1 embedding pass per day, ~10 strings.
  Acceptable. Embedder is loaded once, reused.
- **Daily-tick cadence assumption:** `tick_current_pull_daemon` is
  invoked via heartbeat daemon manager (`_dm.is_enabled("current_pull")`)
  — confirm during planning that this fires at least daily. If not,
  add daily cadence override.

## Out of scope (Phase 2 / deferred)

- (c) Frustreret begær — track friction between pull and action
  ability. Phase 1.1, builds on (b)'s dynamic pull.
- (d) Klangbræt-utvidelse — pull + top appetite + longing-intensity as
  tone modulators in the journal. Phase 1.5.
- (e) Pull-appetit integration — let emergent appetites inform next
  `_generate_pull()` corpus. Phase 2.
- Multi-pull (more than one active at a time)
- Pull-driven goal proposals via cognitive_emergent_goal events
- LLM-driven introspection on why pull shifted

## 30-day review

Schedule eval at 2026-06-11:
- Count refresh events in `refresh_history`
- Trends: do refreshes correlate with strong chronicle shifts?
- Tune `current_pull_staleness_threshold` if frequency feels wrong
- Look at archived `previous_pull` strings — do they feel like
  genuine shifts or hallucinated transitions?
- Decide: keep, tune, deprecate
