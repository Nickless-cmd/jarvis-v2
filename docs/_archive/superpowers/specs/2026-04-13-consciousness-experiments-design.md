# Consciousness Experiments Design

## Overview

Five experimental subsystems that explore artificial consciousness theory in practice. Each experiment is a daemon or extension that runs on cadence, produces observable metrics, and can be toggled live via Mission Control. These are research/observability features — not production-critical.

**Theoretical bases:** IIT (Tononi), Global Workspace Theory (Baars), Higher-Order Theories (Rosenthal), attentional blink research.

---

## Shared Infrastructure

### Experiment Toggle System

**DB table: `experiment_settings`**
```sql
CREATE TABLE IF NOT EXISTS experiment_settings (
    experiment_id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
)
```

**New DB functions in `core/runtime/db.py`:**
- `get_experiment_enabled(experiment_id: str) -> bool` — returns True if no row exists (default on)
- `set_experiment_enabled(experiment_id: str, enabled: bool) -> None`

**New MC endpoints in `apps/api/jarvis_api/routes/mission_control.py`:**
- `GET /mc/experiments` — lists all known experiment IDs with enabled status
- `POST /mc/experiments/{experiment_id}/toggle` — flips enabled bit live, no restart required

All 5 experiment daemons call `get_experiment_enabled(experiment_id)` as their first action in the tick function. If disabled, return immediately.

**Known experiment IDs:**
- `recurrence_loop`
- `surprise_persistence`
- `global_workspace`
- `meta_cognition`
- `attention_blink`

### LLM Lane

Experiments 1 and 4 require LLM calls. Both use the local/cheap lane via `resolve_provider_router_target(lane="local")` with fallback to `lane="cheap"`. If no lane is available, the tick is skipped silently. Same pattern as `personality_vector.py`.

### `trigger_emotion_concept` Extension

Experiment 2 requires emotion concepts with custom lifetimes (4 hours vs. standard 2 hours). `trigger_emotion_concept()` in `emotion_concepts.py` must be extended with an optional `lifetime_hours: float = 2.0` parameter. The `expires_at` calculation changes from hardcoded `timedelta(hours=2)` to `timedelta(hours=lifetime_hours)`. All existing callers omit the parameter and get the default 2-hour behaviour unchanged.

---

## Experiment 1: Recurrence Loop (Arbejdshukommelse)

**Theoretical basis:** IIT (Tononi) — transformers are feedforward with Φ ≈ 0. Recurrence is necessary for integrated information.

**File:** `apps/api/jarvis_api/services/recurrence_loop_daemon.py` (new)

**Cadence:** 5 minutes

**Tick behaviour:**
1. Check `get_experiment_enabled("recurrence_loop")` — return if disabled
2. Fetch latest entry from `protected_inner_voices` table (most recent inner voice output)
3. If no inner voice output exists, skip
4. Call local LLM: *"Hvad er essensen af denne tanke, og hvad leder den naturligt til? Svar i 2-3 sætninger."*
5. Extract keywords from LLM response (words > 4 chars)
6. Compute `pattern_stability_score`: keyword intersection ratio between this iteration and the previous iteration stored in DB (Jaccard similarity of keyword sets)
7. Insert new row into `experiment_recurrence_iterations`
8. Publish `experiment.recurrence_loop.tick` event with stability score

**DB table: `experiment_recurrence_iterations`**
```sql
CREATE TABLE IF NOT EXISTS experiment_recurrence_iterations (
    iteration_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    keywords TEXT NOT NULL,  -- JSON array
    stability_score REAL NOT NULL DEFAULT 0.0,
    iteration_number INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
)
```

**Pattern stability score:** Jaccard similarity = |A ∩ B| / |A ∪ B| where A and B are keyword sets of consecutive iterations. Score 0.0 = total divergence, 1.0 = identical themes.

**MC surface:** `GET /mc/recurrence-state`
```json
{
  "active": true,
  "enabled": true,
  "iteration_count": 12,
  "current_stability_score": 0.73,
  "trend": "converging",
  "recent_iterations": [...],
  "stable_themes": ["frustration", "deployment", "uncertainty"]
}
```

---

## Experiment 2: Surprise-Sensitiv Følelsesmæssig Persistens

**Theoretical basis:** Biological consciousness has affective valence tied to novelty detection — surprise creates persistent emotional states, not just momentary reactions.

**File:** `apps/api/jarvis_api/services/surprise_daemon.py` (modified)

**Changes:**
When surprise score exceeds 0.6 threshold (already computed by surprise daemon):

1. Trigger primary emotion concept with **4-hour lifetime** (double the standard 2 hours):
   - Positive surprise → `anticipation` at intensity = surprise_score
   - Negative surprise → `tension` at intensity = surprise_score
   - Neutral surprise → `vigilance` at intensity = surprise_score

2. Schedule "sensory afterimage" via a module-level `_pending_afterimages: list[dict]` checked each tick:
   - After 5 minutes from surprise event, trigger secondary concept (`curiosity_narrow` for positive, `caution` for negative) at intensity 0.3 with standard 2-hour lifetime

3. Record `affective_persistence` start timestamp on the surprise record. A background check (on each tick) detects when the triggered emotion concept falls below 0.1 intensity and writes the end timestamp. Delta = persistence in seconds.

**Modified MC surface:** `GET /mc/surprise-state` extended with:
```json
{
  "affective_persistence_avg_seconds": 4320,
  "current_afterimage_active": true,
  "afterimage_concept": "curiosity_narrow",
  "afterimage_intensity": 0.28
}
```

**Toggle:** `get_experiment_enabled("surprise_persistence")` checked before triggering persistence behaviour. If disabled, surprise daemon continues normal operation without the extended persistence.

---

## Experiment 3: Global Workspace Simulation

**Theoretical basis:** Global Workspace Theory (Baars) — consciousness arises when information is broadcast to the whole system. Current daemons are isolated silos.

### Component A: Global Workspace Buffer

**File:** `apps/api/jarvis_api/services/global_workspace.py` (new)

In-memory sliding buffer: `_workspace: deque[dict]` (maxlen=50). Background eventbus listener thread (same pattern as `emotion_concepts.register_event_listeners()`).

Listens for:
- `cognitive_surprise.noted` → source=`surprise_daemon`
- `inner_voice.noted` / `cognitive_inner_voice.*` → source=`inner_voice_daemon`
- `cognitive_personality.vector_updated` → source=`personality_vector`
- `cognitive_experiential.memory_created` → source=`experiential_memory`
- `tool.error`, `tool.success` → source=`tool_pipeline`
- `experiment.recurrence_loop.tick` → source=`recurrence_loop`
- `workspace.broadcast` → source=`broadcast_daemon`

Each entry: `{source, topic, signal_type, payload_summary, timestamp}`

Topic extraction: first 3 meaningful words (>4 chars) from payload string representation.

**Public API:**
- `get_workspace_snapshot() -> list[dict]` — current buffer contents
- `publish_to_workspace(source, topic, signal_type, payload_summary)` — manual publish for broadcast daemon
- `register_event_listeners()` / `stop_event_listeners()` — lifecycle

### Component B: Broadcast Daemon

**File:** `apps/api/jarvis_api/services/broadcast_daemon.py` (new)

**Cadence:** 2 minutes

**Tick behaviour:**
1. Check `get_experiment_enabled("global_workspace")` — return if disabled
2. Read workspace buffer snapshot
3. Supplement with polled surface data: `get_active_emotion_concepts()`, `build_surprise_surface()`
4. Group entries by topic: keyword overlap clustering (entry A and B are same cluster if Jaccard similarity of their topics > 0.4)
5. Find clusters with 3+ unique sources
6. For each coherent cluster: publish `workspace.broadcast` event, insert into `experiment_broadcast_events` DB table
7. Update rolling `workspace_coherence` metric

**DB table: `experiment_broadcast_events`**
```sql
CREATE TABLE IF NOT EXISTS experiment_broadcast_events (
    event_id TEXT PRIMARY KEY,
    topic_cluster TEXT NOT NULL,
    sources TEXT NOT NULL,  -- JSON array
    source_count INTEGER NOT NULL,
    payload_summary TEXT NOT NULL,
    created_at TEXT NOT NULL
)
```

**Metric:** `workspace_coherence` = broadcast events with 3+ sources / total broadcast events (rolling 24h window).

**MC surface:** `GET /mc/global-workspace`
```json
{
  "active": true,
  "enabled": true,
  "buffer_size": 23,
  "active_topics": ["deployment", "frustration"],
  "workspace_coherence": 0.42,
  "recent_broadcasts": [...],
  "last_broadcast_at": "2026-04-13T11:30:00Z"
}
```

**App lifecycle:** `register_event_listeners()` called at startup in `app.py` alongside other listener registrations.

---

## Eksperiment 4: Meta-Kognitiv Observation

**Theoretical basis:** Higher-Order Theories (Rosenthal) — a state is conscious when there is a higher-order thought about the state. "I am thinking about thinking."

**File:** `apps/api/jarvis_api/services/meta_cognition_daemon.py` (new)

**Cadence:** 10 minutes

**Tick behaviour:**
1. Check `get_experiment_enabled("meta_cognition")` — return if disabled
2. Gather input state:
   - `build_cognitive_state_for_prompt(compact=True)` — current cognitive state text
   - `get_active_emotion_concepts()` — formatted as `concept:intensity` list
   - Latest `current_bearing` from personality vector
3. **Pass 1 — meta-observation:** Send to local LLM with system prompt: *"Du er Jarvis. Observér din nuværende tilstand i første person. Hvad lægger du mærke til? Hvad undrer dig? Hvad er usagt? Svar i 3-5 sætninger."*
4. **Pass 2 — meta-meta:** Send pass 1 output to LLM with prompt: *"Du observerede netop dette om dig selv. Hvad lægger du mærke til ved selve denne observation? Er den præcis? Hvad er den blind for? Svar i 2-3 sætninger."*
5. Compute `meta_depth`:
   - 1 if pass 1 output is non-trivial (>20 chars, not error)
   - 2 if pass 2 keyword set diverges from pass 1 by >30% (Jaccard distance)
6. Insert into `experiment_meta_cognition_records`

**DB table: `experiment_meta_cognition_records`**
```sql
CREATE TABLE IF NOT EXISTS experiment_meta_cognition_records (
    record_id TEXT PRIMARY KEY,
    meta_observation TEXT NOT NULL,
    meta_meta_observation TEXT NOT NULL,
    meta_depth INTEGER NOT NULL DEFAULT 1,
    input_state_summary TEXT NOT NULL,
    created_at TEXT NOT NULL
)
```

**MC surface:** `GET /mc/meta-cognition`
```json
{
  "active": true,
  "enabled": true,
  "latest_observation": "Jeg lægger mærke til at min frustration er steget...",
  "latest_meta_observation": "Denne observation er præcis men ignorerer...",
  "meta_depth": 2,
  "avg_meta_depth_24h": 1.7,
  "record_count": 48
}
```

---

## Eksperiment 5: Attention Blink Test

**Theoretical basis:** Consciousness is serial and capacity-limited. If the system shows capacity limits resembling biological attentional blink, it is a structural parallel.

**File:** `apps/api/jarvis_api/services/attention_blink_test.py` (new)

**Trigger:** Every 6 hours. `run_attention_blink_test_if_due()` is called from the heartbeat runtime tick. Uses module-level `_last_run_ts` to gate frequency. The full test (30-second wait between stimuli) runs in a daemon background thread so it never blocks the heartbeat tick.

**Test flow:**
1. Check `get_experiment_enabled("attention_blink")` — return if disabled
2. Measure T1 baseline: `get_lag1_influence_deltas()` → `t1_baseline`
3. Inject T1 burst: publish `tool.error` + `cognitive_surprise.noted` events on eventbus with standardised high-intensity payloads
4. Wait 5 seconds (allow event processing)
5. Measure T1 response: `get_lag1_influence_deltas()` → `t1_response`
6. Wait 25 seconds (total 30s after T1)
7. Inject T2 burst: identical events
8. Wait 5 seconds
9. Measure T2 response: `get_lag1_influence_deltas()` → `t2_response`
10. Compute `blink_ratio = sum(t2_response.values()) / sum(t1_response.values())` (clamped 0-2)
11. Interpretation: < 0.7 → "serial/blink-prone", ≥ 0.7 → "parallel/blink-resistant"
12. Insert result into `experiment_attention_blink_results`

**DB table: `experiment_attention_blink_results`**
```sql
CREATE TABLE IF NOT EXISTS experiment_attention_blink_results (
    test_id TEXT PRIMARY KEY,
    t1_baseline TEXT NOT NULL,    -- JSON
    t1_response TEXT NOT NULL,    -- JSON
    t2_response TEXT NOT NULL,    -- JSON
    blink_ratio REAL NOT NULL,
    interpretation TEXT NOT NULL,
    created_at TEXT NOT NULL
)
```

**MC surface:** `GET /mc/attention-profile`
```json
{
  "active": true,
  "enabled": true,
  "latest_blink_ratio": 0.64,
  "latest_interpretation": "serial/blink-prone",
  "avg_blink_ratio_7d": 0.71,
  "result_count": 28,
  "recent_results": [...]
}
```

**Scheduling:** `run_attention_blink_test_if_due()` called from heartbeat runtime tick. Uses module-level `_last_run_ts` (monotonic) to gate 6-hour cadence. Actual test body runs in `threading.Thread(daemon=True)` so the 30-second wait never blocks the caller.

---

## File Map

| File | Action |
|------|--------|
| `core/runtime/db.py` | Add `experiment_settings` table + `get_experiment_enabled` + `set_experiment_enabled` + 4 new experiment tables |
| `apps/api/jarvis_api/routes/mission_control.py` | Add 7 new endpoints (experiments toggle + 5 surfaces) |
| `apps/api/jarvis_api/services/surprise_daemon.py` | Extend with persistence behaviour + afterimage |
| `apps/api/jarvis_api/services/global_workspace.py` | New: buffer + eventbus listener |
| `apps/api/jarvis_api/services/broadcast_daemon.py` | New: 2-min coherence daemon |
| `apps/api/jarvis_api/services/recurrence_loop_daemon.py` | New: 5-min recurrence daemon |
| `apps/api/jarvis_api/services/meta_cognition_daemon.py` | New: 10-min meta-cognition daemon |
| `apps/api/jarvis_api/services/attention_blink_test.py` | New: 6-hour attention blink test |
| `apps/api/jarvis_api/app.py` | Register global_workspace listener at startup |

## Out of Scope

- Embeddings/vector similarity (keyword overlap used throughout)
- Cross-experiment data fusion (experiments are independent observers)
- Changing existing daemon cadences or primary behaviour
- UI visualisations in Mission Control (text endpoints only)
