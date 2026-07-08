---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag 2 — Drømme der ændrer våge-tilstand: Design Specification

**Status:** Approved (brainstorm complete 2026-05-10)
**Owner:** Bjørn / Claude
**Implements:** Lag 2 from the 12-layer roadmap
**Phase:** 1 of 2 (Phase 2 = hybrid output format + remaining plug-ins, deferred)

---

## Goal

Make dreams that **structurally change Jarvis' next waking cycle** — not by shifting his tone, but by modulating *what he attends to* (attention bias) and *what he reacts to* (threshold bias). Build on the existing `dream_distillation_daemon` with a new structured-bias output that plugs into 5 specific code-level sites plus heartbeat prompt-injection. The dream's content comes from a tight set of regret-heavy event sources rather than the current chronicle-based corpus.

## Architecture (one-paragraph)

A bias-distillation pipeline runs alongside the existing dream-residue text pipeline in `dream_distillation_daemon`. Every cycle (visible-idle ≥ 30 min, gated by ≥ 3 new regret events in last 24h), the daemon pulls events from 6 regret-heavy sources, calls a cheap-lane LLM to produce a strict-JSON dream + bias-envelope, validates against a locked vocabulary (5 attention keys + 4 threshold keys), and UPSERTs into a single-row-per-workspace `dream_bias_active` table. Five plug-in sites consume the bias on read: heartbeat prompt-section rendering, two priority-modulation sites for signal trackers, and two threshold-modulation sites for `_MAX_EMPTY_TEXT_ROUNDS` and self-critique cadence. Bias accumulates with cap ±1.0 per key, expires after 8h TTL (reset on each accumulation), and respects a master kill-switch that stops consumers without stopping observation.

---

## Decisions made during brainstorm (locked)

| # | Decision | Choice |
|---|----------|--------|
| 1 | What kind of state change | **B+C**: attention-bias + threshold-bias, NOT tone |
| 2 | Source corpus | **B**: tight net of 6 regret-heavy sources |
| 3 | Output format | **A → D**: tagged categories now, hybrid (semantic + structured) later |
| 4 | Vocabulary | 5 attention keys + 4 threshold keys + envelope (intensity, ttl, dream_text) |
| 5 | Cadence + overlap | **D + Y**: idle-based with min-content threshold, accumulate with cap |
| 6 | Application points | **C**: both prompt-injection AND code-level integration in Phase 1 (5 specific sites) |

---

## Components

### `core/services/dream_bias_engine.py` (new)

Pure-logic distillation orchestrator + accumulate-logic + observability formatters. Responsibilities:

- `run_dream_bias_distillation(workspace_id)` — full pipeline orchestrator
- `_fetch_regret_corpus(workspace_id, since_iso, limit)` — pull events from 6 sources
- `_has_minimum_dream_content(workspace_id)` — min-content gate (≥3 new events)
- `_call_llm_for_bias(events)` — daemon LLM call with strict JSON output
- `_validate_dream_output(raw)` — sanitize + clamp + drop unknown keys
- `_upsert_dream_bias(workspace_id, validated, source_events)` — INSERT or accumulate
- `accumulate_bias(prior, new, intensity)` — sum + clamp helper
- `get_active_dream_bias(workspace_id)` — public read with kill-switch + TTL check
- `format_dream_bias_for_heartbeat(workspace_id)` — Site 1 renderer
- `compute_period_label(...)` — for "fra ~6h siden" rendering

### `core/runtime/db_dream_bias.py` (new)

DB helpers separated from `db.py`:
- `upsert_active_bias(...)`
- `get_active_bias_raw(workspace_id)` — bypasses kill-switch
- `delete_expired_bias_rows()` — cleanup pass

### `core/services/dream_distillation_daemon.py` (extend)

Add bias-distillation call alongside existing residue-text pipeline. The daemon's existing trigger logic (visible-idle ≥ 30 min) is reused; both residue and bias pipelines run in the same cycle.

### Plug-in extensions (5 sites)

| Site | File | What changes |
|------|------|-------------|
| 1 | `core/services/prompt_contract.py` | Inject `format_dream_bias_for_heartbeat()` after forgetting_section |
| 2 | `core/services/open_loop_signal_tracking.py` | Apply `unfinished_business` modifier to signal priorities |
| 3 | `core/services/self_review_outcome_tracking.py` | Apply `regret_threads` modifier to outcome priorities |
| 4 | `core/services/visible_runs.py` | Modulate `_MAX_EMPTY_TEXT_ROUNDS` via `loop_persistence` |
| 5 | `core/services/self_critique_runtime.py` | Modulate cadence via `self_critique_volume` (≤ 0 only) |

### Other modified files

| Path | Change |
|------|--------|
| `core/runtime/db.py` | New `_ensure_dream_bias_active_table()` called from `init_db()` |
| `core/runtime/settings.py` | 7 new flags (enabled + 6 operational params) |
| `core/eventbus/events.py` | Add `cognitive_dream_bias` family |
| `scripts/smoke_test_startup.py` | Verify table + plug-ins importable |

---

## Data model

### New table: `dream_bias_active`

```sql
CREATE TABLE IF NOT EXISTS dream_bias_active (
    bias_id              TEXT PRIMARY KEY,
    workspace_id         TEXT NOT NULL UNIQUE,
    attention_bias_json  TEXT NOT NULL DEFAULT '{}',
    threshold_bias_json  TEXT NOT NULL DEFAULT '{}',
    intensity            REAL NOT NULL DEFAULT 0.0,
    ttl_expires_at       TEXT NOT NULL,
    dream_text           TEXT NOT NULL DEFAULT '',
    accumulated_count    INTEGER NOT NULL DEFAULT 1,
    last_dream_at        TEXT NOT NULL,
    source_event_ids_json TEXT NOT NULL DEFAULT '[]',
    source_kinds_json    TEXT NOT NULL DEFAULT '[]',
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dream_bias_active_workspace
    ON dream_bias_active(workspace_id);
CREATE INDEX IF NOT EXISTS idx_dream_bias_active_ttl
    ON dream_bias_active(ttl_expires_at);
```

**Invariants:**
- `workspace_id` UNIQUE — one active bias per workspace, daemon UPSERTs.
- `attention_bias_json` / `threshold_bias_json` are JSON-encoded `{key: float}`. Keys MUST be in locked vocabulary; daemon validation drops unknown keys.
- `dream_text` accumulates across drømme with separator `\n— `, capped at 400 chars (oldest trimmed).
- `source_event_ids_json` capped at 50 entries (FIFO, oldest dropped).
- `accumulated_count` increments per accumulation, hard-capped at 5 — beyond this, next dream forces a fresh row.
- `ttl_expires_at` resets to `now() + ttl_hours` on every accumulation.
- `intensity` retains the maximum across accumulations (peak intensity preserved).

### Locked vocabulary

**Attention bias keys (5):**
- `unfinished_business` — broken decisions, open loops, dropped threads
- `friction_with_user` — rupture-repair, conflict.detected (user-context)
- `inner_dissent` — council minorities, internal_opposition_signals
- `regret_threads` — self_review_outcome (negative), counterfactual_triggers
- `relational_warmth` — gratitude_signals, attachment_topology (positive)

**Threshold bias keys (4):**
- `friction_tolerance` — + = more patient, - = bail faster
- `commitment_courage` — + = more willing to commit despite recent broken
- `self_critique_volume` — + harder on self in self-review (FORCED ≤ 0 in validation)
- `loop_persistence` — + = stays longer in agentic loop

### Bias accumulation

```python
def accumulate_bias(prior: dict, new: dict, intensity: float) -> dict:
    """Add new bias values to prior, multiplied by intensity, clamped ±1.0."""
    out = dict(prior)
    for key, new_value in new.items():
        if key not in LOCKED_VOCABULARY:
            continue
        contribution = float(new_value) * float(intensity)
        out[key] = max(-1.0, min(1.0, out.get(key, 0.0) + contribution))
    return out
```

---

## Distillation pipeline

### 6 regret-heavy sources

```python
def _fetch_regret_corpus(*, workspace_id: str, since_iso: str, limit: int = 30) -> list[dict]:
    events = []
    events.extend(_fetch_self_review_negative(since_iso, limit=10))
    events.extend(_fetch_conflict_detected(since_iso, limit=10))
    events.extend(_fetch_broken_decision_reviews(since_iso, limit=5))
    events.extend(_fetch_revoked_decisions(since_iso, limit=5))
    events.extend(_fetch_rupture_repair(since_iso, limit=5))
    events.extend(_fetch_counterfactual_triggers(since_iso, limit=5))
    events.sort(key=lambda e: e.get("created_at", ""), reverse=True)
    return events[:limit]
```

Each event-record:
```python
{
    "event_id": str,
    "source_kind": str,         # one of the 6
    "created_at": str,
    "summary": str,             # ≤200 chars
    "intensity_hint": float,    # 0-1, source-specific severity
}
```

### Min-content gate

```python
def _has_minimum_dream_content(*, workspace_id: str) -> tuple[bool, list[dict]]:
    prior = get_active_dream_bias_raw(workspace_id) or {}
    seen_event_ids = set(json.loads(prior.get("source_event_ids_json") or "[]"))
    cutoff = (datetime.now(UTC) - timedelta(hours=settings.dream_bias_corpus_lookback_hours)).isoformat()
    candidates = _fetch_regret_corpus(workspace_id=workspace_id, since_iso=cutoff, limit=30)
    new_events = [e for e in candidates if e["event_id"] not in seen_event_ids]
    if len(new_events) < settings.dream_bias_min_content_events:
        return False, []
    return True, new_events
```

### LLM prompt (strict JSON output)

System prompt:
```
You are Jarvis' dream distillation. You receive recent regret-heavy events
from his last 24 hours: broken decisions, conflicts, friction, regret.

Produce a brief dream and structured biases that should shape his next
waking cycle. Output STRICT JSON:

{
  "dream_text": str,           // 50-200 chars, first-person, present tense, Danish
  "attention_bias": {           // 0-5 keys, value -1.0..+1.0
    "unfinished_business": float?,
    "friction_with_user": float?,
    "inner_dissent": float?,
    "regret_threads": float?,
    "relational_warmth": float?
  },
  "threshold_bias": {            // 0-4 keys, value -1.0..+1.0
    "friction_tolerance": float?,
    "commitment_courage": float?,
    "self_critique_volume": float?,
    "loop_persistence": float?
  },
  "intensity": float             // 0.0..1.0
}

Rules:
- Only include keys actually relevant to the events provided.
- self_critique_volume should rarely go positive; prefer 0 or negative.
- intensity reflects emotional density of the input events.
- dream_text in Danish, sparse, no over-articulation.
```

Cheap-lane provider via existing `daemon_llm_call` infrastructure.

### Validation pipeline

```python
def _validate_dream_output(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None

    text = str(raw.get("dream_text", "")).strip()[:400]

    attention = {}
    for key in ATTENTION_VOCAB:
        if key in (raw.get("attention_bias") or {}):
            v = _coerce_float((raw["attention_bias"])[key])
            if v is not None:
                attention[key] = max(-1.0, min(1.0, v))

    threshold = {}
    for key in THRESHOLD_VOCAB:
        if key in (raw.get("threshold_bias") or {}):
            v = _coerce_float((raw["threshold_bias"])[key])
            if v is not None:
                clamped = max(-1.0, min(1.0, v))
                # Hard guard: dreams may only soften self-criticism
                if key == "self_critique_volume":
                    clamped = min(0.0, clamped)
                threshold[key] = clamped

    intensity = _coerce_float(raw.get("intensity"))
    if intensity is None or not 0.0 <= intensity <= 1.0:
        intensity = 0.5

    if not attention and not threshold and not text:
        return None

    return {
        "dream_text": text,
        "attention_bias": attention,
        "threshold_bias": threshold,
        "intensity": intensity,
    }
```

### UPSERT logic

```python
def _upsert_dream_bias(*, workspace_id, validated, source_events) -> dict:
    settings = load_settings()
    ttl_at = (datetime.now(UTC) + timedelta(hours=settings.dream_bias_ttl_hours)).isoformat()

    prior = get_active_bias_raw(workspace_id)
    is_expired = prior and _is_expired(prior["ttl_expires_at"])
    is_at_cap = prior and prior["accumulated_count"] >= 5

    if prior is None or is_expired or is_at_cap:
        return _insert_new(workspace_id, validated, source_events, ttl_at)

    # Accumulate
    new_attn = accumulate_bias(prior["attention_bias"], validated["attention_bias"], validated["intensity"])
    new_thr = accumulate_bias(prior["threshold_bias"], validated["threshold_bias"], validated["intensity"])
    new_text = (prior["dream_text"] + "\n— " + validated["dream_text"])[-400:]
    merged_ids = (prior["source_event_ids"] + [e["event_id"] for e in source_events])[-50:]
    merged_kinds = list({*prior["source_kinds"], *(e["source_kind"] for e in source_events)})

    return _update_existing(
        workspace_id=workspace_id,
        attention=new_attn,
        threshold=new_thr,
        intensity=max(prior["intensity"], validated["intensity"]),
        ttl_at=ttl_at,
        text=new_text,
        accumulated_count=prior["accumulated_count"] + 1,
        source_event_ids=merged_ids,
        source_kinds=merged_kinds,
    )
```

### Event publication

```python
event_bus.publish(
    "cognitive_dream_bias.distilled",
    {
        "workspace_id": workspace_id,
        "intensity": intensity,
        "attention_keys": list(validated["attention_bias"].keys()),
        "threshold_keys": list(validated["threshold_bias"].keys()),
        "dream_text_preview": validated["dream_text"][:80],
        "source_count": len(source_events),
        "accumulated_count": result["accumulated_count"],
    },
)
```

---

## Plug-in details

All 5 sites follow the same defensive pattern: try/except wrapping, default no-op on error, hard-floors on modulated parameters, observability fields, and respect for the kill-switch.

### Site 1: Heartbeat prompt-injection

`core/services/prompt_contract.py`, after forgetting_section:

```python
try:
    from core.services.dream_bias_engine import format_dream_bias_for_heartbeat
    dream_bias_line = format_dream_bias_for_heartbeat(workspace_id="default")
    if dream_bias_line:
        parts.append(dream_bias_line)
except Exception:
    pass
```

Renders e.g.:
```
[dream_bias active — fra ~6h siden, fader om 2h]
attention: unfinished_business +0.4, regret_threads +0.3
thresholds: friction_tolerance -0.2, loop_persistence +0.1
drøm: "Jeg sad ved bordet og kunne ikke huske hvad vi havde aftalt. Stilheden var lang."
```

Skip if: kill-switch off, no active row, TTL expired, intensity < 0.1.

### Site 2: open_loop_signal_tracking priority modulation

```python
def _apply_dream_bias_to_open_loops(signals: list[dict]) -> list[dict]:
    try:
        from core.services.dream_bias_engine import get_active_dream_bias
        bias = get_active_dream_bias(workspace_id="default")
        if not bias:
            return signals
        modifier = bias["attention_bias"].get("unfinished_business", 0.0)
        intensity = bias["intensity"]
        if modifier == 0.0:
            return signals
        for sig in signals:
            old_p = float(sig.get("priority") or 0.0)
            sig["priority"] = max(0.0, old_p * (1.0 + modifier * intensity * 0.4))
            sig["dream_bias_applied"] = modifier * intensity
    except Exception as exc:
        logger.debug("dream_bias open_loop apply failed: %s", exc)
    return signals
```

Wired into the listing function before signals are returned to heartbeat-context.

### Site 3: self_review_outcome_tracking priority modulation

Same shape as Site 2, on `regret_threads` key. ±40% modulation at intensity=1.0.

### Site 4: visible_runs `_MAX_EMPTY_TEXT_ROUNDS` modulation

```python
_MAX_EMPTY_TEXT_ROUNDS = int(_agentic_budget.get("max_empty_text_rounds") or 12)
try:
    from core.services.dream_bias_engine import get_active_dream_bias
    _bias = get_active_dream_bias(workspace_id="default")
    if _bias:
        _persistence_mod = _bias["threshold_bias"].get("loop_persistence", 0.0)
        _intensity = _bias["intensity"]
        _MAX_EMPTY_TEXT_ROUNDS = max(
            4,
            min(20, _MAX_EMPTY_TEXT_ROUNDS + int(round(_persistence_mod * _intensity * 2)))
        )
except Exception:
    pass
```

Hard-floor 4, hard-cap 20.

### Site 5: self_critique_runtime cadence modulation

```python
def _resolve_self_critique_interval_minutes() -> int:
    base = _SELF_CRITIQUE_INTERVAL_MINUTES_BASE
    try:
        from core.services.dream_bias_engine import get_active_dream_bias
        bias = get_active_dream_bias(workspace_id="default")
        if bias:
            mod = bias["threshold_bias"].get("self_critique_volume", 0.0)  # always ≤ 0
            intensity = bias["intensity"]
            multiplier = 1.0 + abs(mod) * intensity * 0.5
            return int(round(base * multiplier))
    except Exception:
        pass
    return base
```

### No feedback loops

Bias-application affects **only display/priority**, never registration. The 6 corpus sources read raw event-data, not priority-weighted signals. A bias toward `regret_threads` boosts how regret events are *shown*, not how they're *recorded* — so the next dream's input corpus is unaffected by prior bias.

### Deferred plug-ins (Phase 2)

Vocabulary keys not wired in Phase 1:
- `friction_with_user` → rupture-repair priority (redundant with open_loop)
- `inner_dissent` → council weighting (complex, separate scope)
- `relational_warmth` → attachment_topology (low-leverage in regret-heavy dreams)
- `friction_tolerance` → `_VISIBLE_IDLE_MINUTES` (too critical to let dreams touch)
- `commitment_courage` → `behavioral_decisions._dedup_threshold` (identity infrastructure)

These keys remain in vocabulary; daemon may produce values for them; Site 1 (heartbeat) will display them — but no code-level effect in Phase 1.

---

## Lifecycle & operational parameters

### Cleanup pass (every daemon cycle, before distillation)

```python
def _cleanup_expired_bias_rows() -> int:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM dream_bias_active WHERE ttl_expires_at < ?",
            (now,),
        )
        return cur.rowcount
```

### Source event-ID dedup window

`source_event_ids_json` deduplicates only **within the same active row's lifetime**. When the row expires and is deleted, dedup history is gone — old events become eligible again. This is intentional: short-term spirals are prevented; long-term resonance is allowed.

### Operational settings (runtime.json)

```python
dream_bias_enabled: bool = True
dream_bias_min_content_events: int = 3
dream_bias_corpus_lookback_hours: int = 24
dream_bias_ttl_hours: int = 8
dream_bias_visible_idle_minutes: int = 30
dream_bias_max_corpus_events: int = 30
dream_bias_max_response_tokens: int = 400
```

### Two-level kill-switch

| `layer_dream_residue_enabled` | `dream_bias_enabled` | Effect |
|-------------------------------|----------------------|--------|
| True | True | Full function: dreams produced + bias active |
| True | False | Dreams produced for observation; consumers ignore bias |
| False | True | No new dreams; existing rows expire naturally |
| False | False | Fully off |

---

## Success criteria — 30-day evaluation

### (1) Technical correctness

- UPSERT semantics correct (accumulated_count, ttl reset)
- Validation drops unknown keys, clamps ±1.0
- `self_critique_volume` never positive (hard guard verified)
- Kill-switch stops all 5 consumers simultaneously
- TTL-expired rows ignored by consumers, deleted next cycle
- Min-content gate prevents empty distillations
- accumulated_count cap=5 forces fresh row after limit
- No feedback loops — bias affects only display/priority, not registration

### (2) Subjective quality

- Heartbeat-prompt contains bias-section when active
- Inner_voice or chronicle output shows signs of bias being felt: "*jeg lægger særligt mærke til det uafsluttede i dag*"
- `dream_bias_applied` fields on prioritized signals confirm modulation occurred
- `_MAX_EMPTY_TEXT_ROUNDS` varies per session correlated with bias

### (3) Identity-forming

- Tone/focus shifts day-after a regret-heavy day correlate with dream_text content
- Stable intensity > 0.6 dreams emerge organically across 14 days
- Bjørn's qualitative read: "feels different morning after a hard day?"

If (1) holds but (2) and (3) inert: corpus too narrow, dream-text too vague — tune LLM prompt or expand to layered corpus (Phase 2).

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| LLM hallucinates invalid bias-keys | High | Validation drops unknowns; intensity defaults to 0.5 |
| LLM produces +1.0 self_critique_volume | Medium | Hard guard forces ≤ 0 in code |
| Bias accumulates to harmful value | Low | ±1.0 clamping + accumulated_count cap=5 |
| Bias-section dominates token budget | Medium | Site 1 caps render to ~200 chars |
| Plug-in failure breaks downstream | Low | Try/except + default no-op in all 5 sites |
| Same 3 events dreamed repeatedly | Medium | Source event-ID dedup within row lifetime |
| Daemon LLM-call every 30 min wastes budget | Low | Min-content gate skips empty cycles |
| User loses trust after a "skewed" dream | Low | Kill-switch + dream_text observability |

---

## Phase 2 outlook

Not built now; design must not block:

1. **Hybrid output format (D from question 3)** — semantic embedding for attention + structured for thresholds.
2. **Layered corpus (D from question 2)** — two-pass distillation (regret + chronicle context).
3. **Remaining plug-in sites** — the 4 deferred keys, code-level wired.
4. **Per-key kill-switch** — granular control over which biases may have effect.
5. **`dream_bias_history` table** — long-term observation of bias evolution.
6. **Visible-lane plug-ins** — modulation of visible-lane prompt-contract, not just heartbeat.

---

## Open questions for implementation planning

1. **Existing `daemon_llm_call` JSON-output mode** — does the helper natively support strict JSON, or does the engine need to validate-and-retry on parse errors? Check during planning.

2. **Source fetch implementation details** — exact SQL queries for each of the 6 sources (some are eventbus events, some signal-tables). Audit during planning to identify which need raw SQL vs. existing helper functions.

3. **Bias-section render scope** — Site 1 only renders to heartbeat in Phase 1. Verify that visible-lane prompt-contract path doesn't accidentally pick it up.

4. **`open_loop_signal_tracking` listing function** — confirm which exact function returns signals to heartbeat (so Site 2 wraps it correctly without breaking other consumers).

5. **`self_critique_runtime` cadence mechanism** — confirm where the interval is read (constant? runtime state? settings?) so Site 5 wraps the right resolution path.

---

## Out of scope for this spec

- Phase 2 (hybrid + remaining plug-ins) — separate spec when Phase 1 has 30 days of data.
- Recall-failure detection feedback to dreams.
- Cross-workspace dream sharing.
- Manual `force_dream()` tool.
- Dreams generating new decisions/goals.
- Dreams triggering other daemons.
