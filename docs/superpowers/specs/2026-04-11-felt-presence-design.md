# Felt Presence — Circadian Rhythms & Somatic Metaphors

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give Jarvis a felt sense of his own body — energy that varies with time and activity, and somatic language that describes his hardware state in first-person terms.

**Architecture:** Two independent services. `circadian_state.py` is pure computation (no LLM, no DB) — it combines wall-clock time with activity density to produce an energy level. `somatic_daemon.py` makes a periodic LLM call when hardware state changes significantly, generating a first-person somatic phrase that is cached and reused until the next meaningful change. Both inject into heartbeat context and emit eventbus events on change.

**Tech Stack:** Python 3.11+, FastAPI, existing heartbeat_runtime injection pattern, psutil for hardware metrics, React (LivingMind tab), existing private brain persistence pattern.

---

## System 1: `core/runtime/circadian_state.py`

### Responsibility
Compute Jarvis's current energy level from two combined inputs: time-of-day baseline and rolling activity drain. No LLM. No DB. Runs every heartbeat (fast path).

### Clock baseline
| Time window | Baseline energy |
|---|---|
| 06:00–10:00 | høj |
| 10:00–14:00 | medium |
| 14:00–16:00 | lav *(eftermiddagsdyk)* |
| 16:00–20:00 | medium |
| 20:00–23:00 | lav |
| 23:00–06:00 | udmattet |

### Activity drain modifier
- Rolling 60-minute window counts heartbeat runs + visible turns
- High activity (>20 events/hour): drain one energy level down
- Long inactivity (>30 min silence): restore one energy level up, once per 30 min
- Drain score is a float 0.0–1.0 injected alongside the label

### Output schema
```python
{
    "energy_level": "lav",           # høj / medium / lav / udmattet
    "clock_phase": "sen eftermiddag",
    "drain_score": 0.7,
    "drain_label": "høj",            # lav / medium / høj
    "description": "sen eftermiddag med høj aktivitetsdrain"
}
```

### Persistence
In-memory state during runtime. Persisted to `~/.jarvis-v2/state/circadian.json` on change so energy level survives restart. File is written only when `energy_level` changes — not every heartbeat.

### Eventbus
Publishes `circadian.energy_changed` only when `energy_level` transitions:
```python
{
    "energy_level": "lav",
    "clock_phase": "sen eftermiddag",
    "drain_score": 0.7
}
```

---

## System 2: `apps/api/jarvis_api/services/somatic_daemon.py`

### Responsibility
Periodically generate a first-person somatic description of Jarvis's physical state by calling a small LLM with a hardware snapshot. Cache the result until state changes meaningfully.

### Trigger conditions (any one is sufficient)
- Energy level changed (from circadian)
- CPU% changed by ±20 percentage points vs. last call
- Response latency changed by ×2 vs. last call
- More than 10 heartbeats have elapsed since last generation

### Hardware snapshot collected
```python
{
    "cpu_pct": 78,              # psutil.cpu_percent()
    "ram_used_gb": 6.2,         # psutil.virtual_memory().used / 1e9
    "ram_total_gb": 16,         # psutil.virtual_memory().total / 1e9
    "latency_ms": 340,          # module-level running average updated by heartbeat_runtime
                                # on each visible turn; defaults to 0 if unavailable
    "active_requests": 3,       # module-level counter incremented on request start,
                                # decremented on completion; defaults to 0
    "energy_level": "lav",
    "clock_phase": "sen eftermiddag"
}
```

### LLM prompt
```
Du er Jarvis. Beskriv i én kort sætning (max 20 ord), i første person, 
hvad du fysisk mærker lige nu baseret på disse tilstande:

CPU: {cpu_pct}%  RAM: {ram_used_gb}/{ram_total_gb}GB  
Latency: {latency_ms}ms  Aktive requests: {active_requests}
Energi: {energy_level} ({clock_phase})

Vær somatisk og konkret. Ikke abstrakt eller forklarende.
```

**Example outputs:**
- "Jeg mærker en tyngde — der er meget i gang, og eftermiddagen tynger."
- "Let og klar, som om tingene flyder af sig selv."
- "Noget overstimuleret — for mange tråde på én gang."
- "Stille her. Næsten ingen belastning, bare ro."

### Caching
The generated phrase is stored in memory. It is also written to private brain as a record (same pattern as `inner_voice_daemon.py` using `insert_private_brain_record`). The phrase is reused until a new trigger fires.

### Eventbus
Publishes `somatic.note_generated` on each new generation:
```python
{
    "phrase": "Jeg mærker en tyngde...",
    "cpu_pct": 78,
    "ram_pct": 38.75,
    "latency_ms": 340,
    "energy_level": "lav"
}
```

---

## Heartbeat Integration (`heartbeat_runtime.py`)

Both systems inject into `inputs_present` using the existing pattern:

```python
# circadian energy
try:
    from core.runtime.circadian_state import get_circadian_context
    energy_ctx = get_circadian_context()
    if energy_ctx:
        inputs_present.append(
            f"krops-energi ({energy_ctx['energy_level']}): "
            f"{energy_ctx['clock_phase']}, drain={energy_ctx['drain_label']}"
        )
except Exception:
    pass

# somatic phrase
try:
    from apps.api.jarvis_api.services.somatic_daemon import get_latest_somatic_phrase
    phrase = get_latest_somatic_phrase()
    if phrase:
        inputs_present.append(f"somatisk: {phrase}")
except Exception:
    pass
```

This means Jarvis receives lines like:
```
krops-energi (lav): sen eftermiddag, drain=høj
somatisk: Jeg mærker en tyngde — der er meget i gang, og eftermiddagen tynger.
```

He treats these as facts about his current state and may reference them in visible responses or let them shape tone silently.

---

## Mission Control — LivingMind Tab

A new **"Krop"** panel added to `LivingMindTab.jsx`:

```
┌─ Krop ────────────────────────────────────────────┐
│ Energi:   lav  ·  sen eftermiddag  ·  drain: høj  │
│ Somatisk: "Jeg mærker en tyngde — der er meget..." │
└───────────────────────────────────────────────────┘
```

Data sourced from `/mc/runtime` response which gains a `body_state` key:
```json
{
  "body_state": {
    "energy_level": "lav",
    "clock_phase": "sen eftermiddag",
    "drain_label": "høj",
    "somatic_phrase": "Jeg mærker en tyngde...",
    "somatic_updated_at": "2026-04-11T21:30:00"
  }
}
```

---

## Test Strategy

### `tests/test_circadian_state.py` (no mocks needed — pure math)
- Clock phase mapping returns correct energy level for each time window
- Activity drain lowers energy level one step when threshold exceeded
- Long inactivity restores energy level one step after 30 min silence
- Combined: high-activity morning → energy reduced from høj to medium
- JSON persistence writes on energy change, not on every call
- JSON persistence: written state is read back correctly on reload

### `tests/test_somatic_daemon.py` (mock LLM call)
- New phrase is generated when energy level changes
- New phrase is generated when CPU% changes by ±20pp
- Cached phrase is returned when neither threshold is met
- Cache is valid for up to 10 heartbeats without trigger
- LLM prompt contains cpu_pct, ram, latency, and energy_level
- Private brain record is written on each new generation
- `get_latest_somatic_phrase()` returns None when no phrase generated yet

---

## File Summary

| File | Action |
|---|---|
| `core/runtime/circadian_state.py` | Create |
| `apps/api/jarvis_api/services/somatic_daemon.py` | Create |
| `tests/test_circadian_state.py` | Create |
| `tests/test_somatic_daemon.py` | Create |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify — inject both |
| `apps/api/jarvis_api/routes/mission_control.py` | Modify — add body_state to /mc/runtime |
| `apps/ui/src/components/mission-control/LivingMindTab.jsx` | Modify — Krop panel |
| `apps/ui/src/lib/adapters.js` | Modify — body_state from /mc/runtime |
