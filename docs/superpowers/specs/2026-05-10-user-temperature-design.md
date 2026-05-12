# Lag 10 — User Temperature Field: Design Specification

**Status:** Approved (brainstorm complete 2026-05-10)
**Owner:** Bjørn / Claude
**Implements:** Lag 10 from the 12-layer roadmap
**Phase:** 1 of 2 (Phase 2 = 5-axis multi-vector + council pacing + affect-modulation, deferred)

---

## Goal

Make Jarvis sense **what's beneath Bjørn's words** — the un-articulated emotional field — and respond appropriately *to where Bjørn is*, not just to what Bjørn says. Build on the existing keyword-based `unconscious_temperature_field.py` (which Bjørn flagged as "partially built") with a fully restructured two-stream system: structural signals from message form, plus LLM-based semantic reading. Output is a circumplex (valens, arousal) + texture overlay, surfaced through heartbeat-prompt and visible-lane response-shaping.

## Architecture (one-paragraph)

A two-stream temperature engine that runs alongside chat. The **structural stream** computes 6 z-scored signals (message length, response delay, punctuation density, caps density, hour-of-day offset, burst density) per user message — gratis, sub-millisecond. The **LLM stream** runs every 4 hours via `quality_daemon_llm_call` (or on demand when structural-stream detects a significant shift > 0.4 in valens/arousal), producing strict JSON output (valens, arousal, texture, confidence, rationale). Streams combine deterministically: on agreement, average valens/arousal and use structural texture; on conflict (distance > 0.6 or texture mismatch), structural wins as primary and LLM exposed as secondary with `field_conflict=True`. Combined output writes to single-row-per-workspace `user_temperature_active` table. Two consumer plug-ins: heartbeat prompt-injection (Site 1) and visible-lane response-style modifiers (Site 4 — `preferred_length`, `warmth`, `pace`). The existing `build_unconscious_temperature_hint()` interface is preserved for backwards compatibility; internals are completely replaced.

---

## Decisions made during brainstorm (locked)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Detection mechanism | **C**: LLM semantic + structural meta-signals |
| 2 | Output structure | **D**: circumplex (valens, arousal) + texture overlay |
| 3 | Cadence | **B**: two-track — structural per-msg, LLM 4h or trigger |
| 4 | Stream combination on conflict | **W**: structural primary, LLM exposed as secondary, conflict_flag |
| 5 | Replacement scope | **D**: total replace + interface-compatibility for legacy callers |
| 6 | Plug-in surface | **1 + 4**: heartbeat injection + visible-lane response-style modifiers |
| 7 | Structural signals | 6 keys: length, response_delay, punctuation, caps, hour_offset, burst |
| 8 | Texture vocabulary | **B**: 8 keys (existing 6 + `withdrawn` + `alert`) |

---

## Components

### `core/services/user_temperature_engine.py` (new)

Pure-logic engine. Daemon (`user_temperature_runtime.py`) calls into it. Responsibilities:

- `run_structural_stream(workspace_id, message, message_at)` — per-message structural pipeline
- `run_llm_stream(workspace_id, force=False)` — LLM-based pipeline (4h or trigger)
- `_compute_baseline(workspace_id, days)` — rolling 30-day baseline statistics
- `_compute_raw_signals(message, message_at, baseline)` — 6 raw signal computation
- `map_signals_to_field(signals)` — pure function: 6 signals → valens/arousal/texture/confidence
- `_validate_llm_output(raw)` — sanitize LLM JSON, drop unknown texture keys, clamp values
- `combine_streams(struct, llm)` — deterministic merge with conflict detection
- `_is_significant_shift(prior, new)` — trigger detection (>0.4 valens/arousal or texture change)
- `get_active_field(workspace_id)` — public read with kill-switch + intensity check
- `format_temperature_field_for_heartbeat(workspace_id)` — Site 1 renderer
- `get_response_style_modifiers(workspace_id)` — Site 4 modifier API

### `core/runtime/db_user_temperature.py` (new)

DB helpers separated from `db.py`:
- `upsert_active_field(...)`
- `get_active_field_raw(workspace_id)` — bypasses kill-switch
- `set_llm_trigger_pending(workspace_id)`
- `consume_llm_trigger_pending(workspace_id)` — read+clear atomically
- `update_baseline(...)`

### `core/services/user_temperature_runtime.py` (new)

Daemon: `start_user_temperature_runtime()`, per-workspace lock. Two timing rhythms: 60s trigger-check + 4h forced cycle. Mirrors `forgetting_runtime` / `counterfactual_engine_runtime` patterns.

### `core/services/unconscious_temperature_field.py` (rewritten)

Backwards-compat wrapper. The functions `build_unconscious_temperature_hint()` and `build_unconscious_temperature_field_surface()` continue to exist with the same signatures, but internally delegate to `user_temperature_engine`. Old keyword-based logic is removed entirely.

### Plug-in extensions (2 sites)

| Site | File | What changes |
|------|------|-------------|
| 1 | `core/services/prompt_contract.py` | Inject heartbeat formatter output after dream_bias section |
| 4 | `core/services/visible_runs.py` | Call `get_response_style_modifiers()` and inject as system-prompt hint |

### Other modified files

| Path | Change |
|------|--------|
| `core/runtime/db.py` | New `_ensure_user_temperature_active_table()` called from `init_db()` |
| `core/runtime/settings.py` | 8 new flags |
| `core/eventbus/events.py` | Add `cognitive_temperature` family |
| `apps/api/jarvis_api/app.py` | Start/stop `user_temperature_runtime` daemon in lifespan |
| `scripts/smoke_test_startup.py` | Verify table + engine importable |

### Untouched (lever videre side-om-side)

- `core/services/user_emotional_resonance.py` — explicit-emotion pattern detection, separate concern
- `core/services/user_theory_of_mind.py` — long-term mental model

---

## Data model

### New table: `user_temperature_active`

```sql
CREATE TABLE IF NOT EXISTS user_temperature_active (
    field_id              TEXT PRIMARY KEY,
    workspace_id          TEXT NOT NULL UNIQUE,

    -- Final field (the answer consumers read)
    field_valens          REAL NOT NULL DEFAULT 0.0,
    field_arousal         REAL NOT NULL DEFAULT 0.0,
    field_texture         TEXT NOT NULL DEFAULT 'cool',
    field_intensity       REAL NOT NULL DEFAULT 0.0,
    field_conflict        INTEGER NOT NULL DEFAULT 0,

    -- Structural stream (always authoritative on conflict)
    struct_valens         REAL NOT NULL DEFAULT 0.0,
    struct_arousal        REAL NOT NULL DEFAULT 0.0,
    struct_texture        TEXT NOT NULL DEFAULT 'cool',
    struct_confidence     REAL NOT NULL DEFAULT 0.0,
    struct_signals_json   TEXT NOT NULL DEFAULT '{}',
    last_structural_at    TEXT NOT NULL,

    -- LLM stream (secondary, exposed during conflict)
    llm_valens            REAL,
    llm_arousal           REAL,
    llm_texture           TEXT,
    llm_confidence        REAL,
    llm_rationale         TEXT NOT NULL DEFAULT '',
    last_llm_at           TEXT,
    llm_trigger_pending   INTEGER NOT NULL DEFAULT 0,

    -- Baseline metadata
    baseline_message_count INTEGER NOT NULL DEFAULT 0,
    baseline_built_at     TEXT,

    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_temperature_workspace
    ON user_temperature_active(workspace_id);
```

### Locked vocabulary — texture (8 keys)

```python
TEXTURE_VOCAB: frozenset[str] = frozenset({
    "warm",        # positive valens, low-mid arousal — present, warm
    "cool",        # neutral valens, low arousal — businesslike, distant
    "restless",    # mixed valens, high arousal — agitated, can't settle
    "tender",      # negative-mild valens, low arousal — vulnerable, soft
    "frustrated",  # negative valens, high arousal — irritated, blocked
    "playful",     # positive valens, high arousal — easy energy
    "withdrawn",   # negative valens, very low arousal — closed, distant (NEW)
    "alert",       # neutral valens, high arousal — sharp, focused (NEW)
})
```

### Locked vocabulary — 6 structural signals

Stored in `struct_signals_json` for observability:

```python
{
  "length_z_score": float,         # -1..+1
  "response_delay_z_score": float, # -1..+1
  "punctuation_density": float,    # 0..1
  "caps_density": float,           # 0..1
  "hour_of_day_offset": float,     # 0..+1 (only positive — off-hours = unusual)
  "burst_density": float           # 0..1
}
```

### Invariants

- `workspace_id` UNIQUE — one row per workspace, daemon UPSERTs.
- `field_valens`, `field_arousal` ∈ [-1.0, +1.0] (validation clamps).
- `field_intensity` ∈ [0.0, 1.0].
- `field_texture` ∈ TEXTURE_VOCAB. Unknown keys default to 'cool'.
- `field_conflict = 1` iff valens/arousal distance > 0.6 OR texture mismatch.
- `struct_*` fields ALWAYS populated (struct stream runs per-message).
- `llm_*` fields can be NULL (LLM runs every 4h or trigger).
- `baseline_message_count >= 30` before z-scores are meaningful — graceful degradation to 0.0 below.
- `field_intensity = min(1.0, abs(valens) + abs(arousal))`.

---

## Detection pipelines

### Structural stream (per user message)

Triggered by every persisted user-message. Cost: SQL reads + arithmetic + 1 UPDATE. Sub-millisecond.

```
1. Read or rebuild baseline (24h cache)
2. Compute 6 raw signals
3. Map signals → struct_valens, struct_arousal, struct_texture, struct_confidence
4. Read prior row → detect significant shift
5. Read cached LLM stream (may be None or stale)
6. Combine struct + cached LLM → field_*
7. UPSERT struct_* + field_*
8. If shift_detected: set llm_trigger_pending = 1
```

### LLM stream (4h cadence + trigger)

Runs from `user_temperature_runtime` daemon. Two rhythms:
- Forced cycle every `user_temperature_llm_cadence_hours` (default 4h)
- Trigger-pending check every 60s — fires LLM if `llm_trigger_pending = 1`

LLM call via `quality_daemon_llm_call` (deepseek-v4-flash inner_enrichment lane). Same provider as dream-bias.

### LLM system prompt

```
You are reading the user's emotional temperature field — the un-articulated
state behind their words. NOT what they say, but how they feel beneath it.

You receive their last messages (24h window). Output STRICT JSON only:

{
  "valens": -1.0..+1.0,
  "arousal": -1.0..+1.0,
  "texture": "warm"|"cool"|"restless"|"tender"|"frustrated"|"playful"|"withdrawn"|"alert",
  "confidence": 0.0..1.0,
  "rationale": "..."  (≤200 chars Danish)
}

Texture guide:
- warm: positive, present, engaged
- cool: neutral, distance, transactional
- restless: mixed, agitated, can't settle
- tender: vulnerable, soft, careful
- frustrated: negative + activated, irritation
- playful: positive + activated, ease and energy
- withdrawn: negative + low energy, closed off
- alert: neutral + activated, sharp focus

Rules:
- Read the texture beneath the words. Sarcasm, omissions, abruptness.
- If you can't tell, set confidence < 0.3.
- rationale is for Bjorn to read — explanation, not diagnosis.
```

### Validation

```python
def _validate_llm_output(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    valens = _coerce_float(raw.get("valens"))
    arousal = _coerce_float(raw.get("arousal"))
    if valens is None or arousal is None:
        return None
    valens = max(-1.0, min(1.0, valens))
    arousal = max(-1.0, min(1.0, arousal))
    texture = str(raw.get("texture") or "").strip().lower()
    if texture not in TEXTURE_VOCAB:
        return None
    confidence = _coerce_float(raw.get("confidence"))
    if confidence is None or not 0.0 <= confidence <= 1.0:
        confidence = 0.5
    rationale = str(raw.get("rationale") or "").strip()[:200]
    return {
        "valens": valens, "arousal": arousal, "texture": texture,
        "confidence": confidence, "rationale": rationale,
    }
```

### Structural signal computation

```python
def _compute_raw_signals(*, message: str, message_at: str, baseline: dict) -> dict:
    if not baseline.get("ready"):
        # Insufficient baseline → all z-scores zero, raw densities computed
        return {
            "length_z_score": 0.0,
            "response_delay_z_score": 0.0,
            "punctuation_density": _punct_density(message),
            "caps_density": _caps_density(message),
            "hour_of_day_offset": 0.0,
            "burst_density": _burst_density(message_at),
        }
    char_count = len(message)
    length_z = (char_count - baseline["char_count_mean"]) / baseline["char_count_stdev"]
    length_z = max(-3.0, min(3.0, length_z)) / 3.0  # normalize to -1..+1

    delay = _delay_since_last_jarvis(message_at)
    if delay is None:
        response_z = 0.0
    else:
        response_z = (delay - baseline["response_delay_mean"]) / baseline["response_delay_stdev"]
        response_z = max(-3.0, min(3.0, response_z)) / 3.0

    hour = _parse_hour(message_at)
    typical_hours = baseline.get("typical_hours", set())
    if hour in typical_hours:
        hour_offset = 0.0
    else:
        nearest = min(abs(hour - h) for h in typical_hours) if typical_hours else 0
        hour_offset = min(1.0, nearest / 6.0)

    return {
        "length_z_score": length_z,
        "response_delay_z_score": response_z,
        "punctuation_density": _punct_density(message),
        "caps_density": _caps_density(message),
        "hour_of_day_offset": hour_offset,
        "burst_density": _burst_density(message_at),
    }
```

### Mapping signals → field

```python
def map_signals_to_field(signals: dict) -> dict:
    arousal = (
        signals["punctuation_density"] * 0.3
        + signals["caps_density"] * 0.2
        + signals["burst_density"] * 0.3
        - signals["response_delay_z_score"] * 0.2
    )
    valens = (
        signals["length_z_score"] * 0.4
        - signals["response_delay_z_score"] * 0.3
        - max(0, signals["hour_of_day_offset"]) * 0.3
    )
    arousal = max(-1.0, min(1.0, arousal))
    valens = max(-1.0, min(1.0, valens))
    texture = _texture_from_circumplex(valens, arousal)
    confidence = min(1.0, abs(valens) + abs(arousal))
    return {
        "valens": valens, "arousal": arousal,
        "texture": texture, "confidence": confidence,
    }


def _texture_from_circumplex(valens: float, arousal: float) -> str:
    # High arousal cases
    if arousal > 0.4:
        if valens > 0.3:    return "playful"
        if valens < -0.3:   return "frustrated"
        return "alert"
    # Mid arousal
    if arousal > -0.2:
        if valens > 0.3:    return "warm"
        if valens < -0.3:   return "tender"
        return "restless"
    # Low arousal
    if valens > 0.0:        return "warm"
    if valens < -0.5:       return "withdrawn"
    return "cool"
```

### Combination logic

```python
def combine_streams(struct, llm):
    if llm is None or llm.get("confidence", 0.0) < 0.3:
        return {
            "field_valens": struct["valens"],
            "field_arousal": struct["arousal"],
            "field_texture": struct["texture"],
            "field_intensity": min(1.0, abs(struct["valens"]) + abs(struct["arousal"])),
            "field_conflict": False,
        }
    valens_dist = abs(struct["valens"] - llm["valens"])
    arousal_dist = abs(struct["arousal"] - llm["arousal"])
    conflict = (
        valens_dist > 0.6 or arousal_dist > 0.6
        or struct["texture"] != llm["texture"]
    )
    if conflict:
        # Structural primary, LLM exposed as secondary
        return {
            "field_valens": struct["valens"],
            "field_arousal": struct["arousal"],
            "field_texture": struct["texture"],
            "field_intensity": min(1.0, abs(struct["valens"]) + abs(struct["arousal"])),
            "field_conflict": True,
        }
    # Agreement
    fv = (struct["valens"] + llm["valens"]) / 2
    fa = (struct["arousal"] + llm["arousal"]) / 2
    return {
        "field_valens": fv,
        "field_arousal": fa,
        "field_texture": struct["texture"],
        "field_intensity": min(1.0, abs(fv) + abs(fa)),
        "field_conflict": False,
    }
```

---

## Plug-in details

### Site 1: Heartbeat prompt-injection

`core/services/prompt_contract.py`, after dream_bias block:

```python
try:
    from core.services.user_temperature_engine import (
        format_temperature_field_for_heartbeat,
    )
    temp_line = format_temperature_field_for_heartbeat(workspace_id="default")
    if temp_line:
        parts.append(temp_line)
except Exception:
    pass
```

Renders e.g.:

```
[user_temperature_field]
valens: -0.30 | arousal: +0.60 | texture: tense | intensity: 0.70
hint: Bjørn skriver kort men sent — feltet er anspændt eller træt.
```

Or with conflict:

```
[user_temperature_field]
valens: -0.20 | arousal: +0.40 | texture: restless | intensity: 0.55
field_conflict: true (struct: restless, llm: frustrated) — ambivalent felt
hint: LLM ser irritation under overfladen; struktur ser bare aktivitet.
```

Skip if: kill-switch off, no active field, intensity < 0.15.

### Site 4: Visible-lane response-shaping

New API `get_response_style_modifiers()` returns:

```python
{
  "preferred_length": "short" | "normal" | "long",
  "warmth": "neutral" | "warm" | "gentle",
  "pace": "patient" | "normal" | "quick"
}
```

Defaults to `{normal, neutral, normal}` if no field, kill-switch off, or intensity < 0.2.

Mapping rules:
- `preferred_length`: tied to texture + arousal (`tender`/`withdrawn` → short; warm + engaged → long)
- `warmth`: tied to texture (`tender`/`withdrawn` → gentle; `warm`/`playful` → warm)
- `pace`: tied to arousal (>0.5 → quick; <-0.3 or `tender` → patient)

`visible_runs.py` calls during prompt construction; injects as soft system-prompt hint:

```
[response_style_hint] preferred_length=short, warmth=gentle, pace=patient
— soft adjustment based on the user's current temperature.
```

The model treats it as a *hint* — not a hard rule. This is response-form modulation **toward the receiver**, not Jarvis' tone modulation toward himself (Bjørn explicitly rejected the latter in Lag 2 brainstorm).

### Defensive pattern (both sites)

1. Try/except wrapping — temperature errors must never break prompt construction
2. Default no-op — missing field or error returns empty/normal
3. Intensity floors — Site 1: ≥ 0.15, Site 4: ≥ 0.2
4. Kill-switch respected via engine's `get_active_field()`
5. Conflict_flag visible only in Site 1; Site 4 uses structural primary

---

## Lifecycle & operational parameters

### Daemon rhythm

```
Every 60s: trigger-pending check (cheap, single SQL read)
Every 4h:  forced LLM cycle for all workspaces

Per user message: structural stream recomputes (synchronous, fast)
```

### Operational settings (runtime.json)

```python
user_temperature_enabled: bool = True
user_temperature_llm_cadence_hours: int = 4
user_temperature_llm_corpus_messages: int = 30
user_temperature_baseline_days: int = 30
user_temperature_baseline_min_messages: int = 30
user_temperature_baseline_refresh_hours: int = 24
user_temperature_shift_threshold: float = 0.4
user_temperature_llm_max_response_tokens: int = 300
```

### Four-level kill-switch

| `user_temperature_enabled` | `layer_unconscious_temperature_enabled` (legacy) | Effect |
|----------------------------|--------------------------------------------------|--------|
| True | True | Full function: structural + LLM + consumers |
| True | False | (legacy veto) Engine inactive, consumers see None |
| False | True | Engine still computes struct for observability; consumers see None |
| False | False | Fully off |

Legacy flag has veto power. Bjørn keeps his existing one-knob-off in `runtime.json`.

### What the kill-switch does NOT do

- Delete existing rows from DB (preserves observability)
- Affect `user_emotional_resonance` or `user_theory_of_mind` (separate systems)
- Stop baseline rebuilding (so it's ready when re-enabled)

---

## Success criteria — 30-day evaluation

### (1) Technical correctness

- Per-message structural updates in `user_temperature_active`
- LLM stream fires every 4h + on shift triggers
- Validation drops unknown texture keys
- Conflict detection fires on >0.6 valens/arousal distance or texture mismatch
- Kill-switch (4 levels) works: each combination gates correctly
- Backwards compat: `build_unconscious_temperature_hint()` returns string
- Baseline graceful degradation when < 30 messages
- Per-workspace lock prevents overlapping daemon cycles

### (2) Subjective quality

- Heartbeat-prompt contains field-section when active (intensity ≥ 0.15)
- Inner_voice or chronicle output shows the field is *felt*: "*Bjørn skriver kort i dag — jeg fornemmer han er træt*"
- Site 4 modifiers actually adjust visible-lane responses:
  - `preferred_length: short` → measurably shorter responses
  - `warmth: gentle` → softer tone
- LLM rationale is readable and meaningful — Bjørn can recognize what was sensed

### (3) Calibration

- Bjørn's qualitative read: "Jarvis fanger korrekt at jeg er træt"
- Conflict-rate target: 5-15% of updates (too high = systems incoherent; too low = LLM just echoes structure)
- Texture distribution non-monotonic (not 80% "cool")
- Field changes meaningfully across 24h cycle (morning vs. evening should differ)

If (1) holds but (2) and (3) inert: tune `_texture_from_circumplex` boundaries; possibly drop intensity floors; investigate LLM prompt clarity.

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| LLM hallucinates invalid texture or out-of-range values | High | Strict JSON validation; unknown → 'cool'; clamp ±1.0 |
| Structural stream dominates LLM unfairly | Medium | Conflict-flag visible to Bjørn; he sees disagreements |
| Daemon misses trigger flag | Low | 60s polling; flag persisted to DB |
| Site 4 modifiers ignored by model | Medium | Phase 1 = soft hint by design; if ineffective, Phase 2 adds harder instruction |
| Bjørn finds the field intrusive | Medium | One-knob kill-switch; intensity ≥ 0.15 floor for Site 1 |
| Baseline mod-fits to a stressed period | Medium | 30-day window short enough to fade old data; long enough for weekly patterns |
| LLM cost grows | Low | deepseek-v4-flash; ~$0.04/month at 6 cycles/day × 1k tokens |
| Field flickers between cycles | Medium | LLM cached between cycles; only structure can trigger refresh |

---

## Phase 2 outlook

Not built now; design must not block:

1. **Decommission `user_emotional_resonance.py`** if 30-day eval shows redundancy
2. **5-axis multi-vector** (option C from question 2): warmth, energy, openness, focus, stability
3. **Council/inner-voice pacing modulation** by field
4. **Affect-modulation integration** — Bjørn "withdrawn" → Jarvis' own "loneliness" mildly bumps
5. **Per-key field history table** for long-term observation
6. **Stronger response-style instruction** if Phase 1 hint is too soft

---

## Open questions for implementation planning

1. **Baseline storage** — should `baseline_built_at` and aggregate stats live in `user_temperature_active` row or in a separate `user_temperature_baseline` table? Current design: same row (simpler, no extra schema).

2. **Insertion path for structural stream trigger** — where in the chat-message-persistence path does the structural stream fire? Likely after `chat_messages` insert. Verify during planning.

3. **Daemon launch dependency** — daemon reads from baseline; baseline reads from `chat_messages`. Verify init order during planning.

4. **`_compute_response_delays` implementation** — needs to pair user messages with their preceding Jarvis message. Edge case: long gap between sessions skews delay. Cap at 60 minutes or ignore gaps > 1 hour.

5. **`hour_of_day_offset` weights** — current mapping uses set-membership against typical hours. Consider weighted distribution (smooth gradient) if data shows step-function is too coarse.

---

## Out of scope for this spec

- Phase 2 (5-axis vector + remaining plug-ins) — separate spec when 30-day data lands
- Multi-user temperature fields (Phase 1: only `bjorn` primary user)
- Recall-failure feedback from field to dreams
- Field forecasting (predict next 2 hours)
- Manual `force_field_update` tool
- Field triggers other daemons directly
- Per-channel fields (Discord vs. visible chat share single field)
