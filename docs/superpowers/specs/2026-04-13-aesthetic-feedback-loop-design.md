# Aesthetic Feedback Loop Design

## Goal

Connect Jarvis' three disconnected aesthetic systems (code_aesthetic_daemon, aesthetic_sense, aesthetic_taste_daemon) so daemon text-output accumulates motifs that activate taste-insights. Phase 1 only — accumulation + activation, no feedback into daemon prompts.

## Problem

- `code_aesthetic_daemon` produces rich aesthetic text weekly but it disappears into private_brain
- `aesthetic_sense.detect_aesthetic_signals()` exists but is never called anywhere
- `aesthetic_taste_daemon` needs 15+ `record_choice()` calls to activate, but choices contain only crude mode/style labels from visible runs — no actual aesthetic content

## Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Input scope | All LLM-producing daemons (11 total) | Broadest taste accumulation |
| 2 | Activation gate | Motif-based (unique_motifs >= 3) + 30 min time-gate | Diversity over quantity |
| 3 | Persistence | Hybrid: in-memory set + SQLite | Taste survives restarts |
| 4 | Loop closure | Phase 1 only — no feedback into prompts | Avoid echo chamber before validating forward direction |
| 5 | Implementation | Heartbeat-level wiring | Central, no individual daemon changes |

## Architecture

```
Heartbeat tick
  -> Daemon produces text (somatic, thought_stream, reflection, etc.)
  -> [after all daemons] Text runs through detect_aesthetic_signals()
  -> Detected motifs written to aesthetic_motif_log (SQLite)
  -> aesthetic_taste_daemon queries motif_log:
     - At least 3 unique motifs
     - At least 30 min since last insight
     - If both: generate taste-insight via LLM
  -> On startup: seed in-memory state from DB
```

## Text-Producing Daemons (11)

| Daemon | Text variable in heartbeat | Feeds in? |
|--------|---------------------------|-----------|
| somatic | `_somatic` | Yes |
| surprise | `_surprise` | Yes |
| thought_stream | `_fragment` | Yes |
| conflict | `_conflict` | Yes |
| reflection_cycle | `_reflection` | Yes |
| curiosity | `_curiosity` | Yes |
| meta_reflection | `_meta` | Yes |
| development_narrative | `_dev_narr` | Yes |
| creative_drift | `_drift_idea` | Yes |
| irony | `_irony` | Yes |
| code_aesthetic | `_ca_result["reflection"]` | Yes |

Not included: experienced_time (numeric), absence (label), signal_decay/memory_decay (housekeeping), desire (structured signal), dream_insight (depends on dream_hypothesis), user_model (needs user input), existential_wonder (rare, could add later), aesthetic_taste (consumer, not producer).

## DB Schema

New table in `core/runtime/db.py`:

```sql
CREATE TABLE IF NOT EXISTS aesthetic_motif_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    motif TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL
);
```

DB functions:
- `aesthetic_motif_log_insert(source, motif, confidence)` — insert one row
- `aesthetic_motif_log_unique_motifs()` — return list of distinct motif names
- `aesthetic_motif_log_summary()` — return `[{motif, count, avg_confidence}]` grouped by motif, ordered by count desc

## Accumulation Function

In `aesthetic_sense.py`, new function:

```python
def accumulate_from_daemon(source: str, text: str) -> list[dict]:
    signals = detect_aesthetic_signals(text=text)
    if signals:
        from core.runtime.db import aesthetic_motif_log_insert
        for s in signals:
            aesthetic_motif_log_insert(
                source=source, motif=s["motif"], confidence=s["confidence"]
            )
    return signals
```

Synchronous. Uses existing `detect_aesthetic_signals()` unchanged. Returns detected signals for caller inspection. Also updates `aesthetic_taste_daemon._accumulated_motifs` in-memory set so the taste-daemon's activation gate stays current without DB queries.

## Aesthetic Taste Daemon Changes

### New activation gate

Replace `_choices_since_insight < 15` with:

```python
if len(_accumulated_motifs) < 3:
    return {"generated": False, "reason": "needs 3+ unique motifs"}

if _last_insight_at and (now - _last_insight_at) < timedelta(minutes=30):
    return {"generated": False, "reason": "30min time-gate"}
```

### New prompt context

Instead of showing "your last 15 choices (mode + style)", show accumulated motif data:

```
Her er dine aesthetiske tendenser:
- clarity: 12 observationer, confidence 0.72
- craft: 8 observationer, confidence 0.54
- calm-focus: 5 observationer, confidence 0.38

Hvad siger disse tendenser om din smag?
```

### Seed from DB

`_accumulated_motifs: set[str]` seeded from DB on first tick (lazy init). Updated by `accumulate_from_daemon()` calls.

```python
_accumulated_motifs: set[str] = set()
_seeded: bool = False

def _seed_from_db() -> None:
    global _accumulated_motifs, _seeded
    if _seeded:
        return
    from core.runtime.db import aesthetic_motif_log_unique_motifs
    _accumulated_motifs = set(aesthetic_motif_log_unique_motifs())
    _seeded = True
```

### record_choice() retained

`record_choice()` still runs in the heartbeat aesthetic_taste block. It no longer drives the activation gate but remains as secondary data (mode + style from visible runs) available for prompt context.

## Heartbeat Wiring

After all daemon groups complete (after Group 4, before `end_tick()`), one block collects all text outputs and runs them through motif detection:

```python
# --- Aesthetic motif accumulation ---
try:
    from apps.api.jarvis_api.services.aesthetic_sense import accumulate_from_daemon
    _aesthetic_texts = {
        "somatic": _somatic if "_somatic" in dir() else "",
        "surprise": _surprise if "_surprise" in dir() else "",
        "thought_stream": _fragment if "_fragment" in dir() else "",
        "conflict": _conflict if "_conflict" in dir() else "",
        "reflection_cycle": _reflection if "_reflection" in dir() else "",
        "curiosity": _curiosity if "_curiosity" in dir() else "",
        "meta_reflection": _meta if "_meta" in dir() else "",
        "development_narrative": _dev_narr if "_dev_narr" in dir() else "",
        "creative_drift": _drift_idea if "_drift_idea" in dir() else "",
        "irony": _irony if "_irony" in dir() else "",
        "code_aesthetic": _ca_result.get("reflection", "") if "_ca_result" in dir() else "",
    }
    for daemon_name, text in _aesthetic_texts.items():
        if text:
            accumulate_from_daemon(daemon_name, text)
except Exception:
    pass
```

Single collection point, not spread across 11 daemon blocks. Follows existing `"_xxx" in dir()` guard pattern.

## Observability

`build_taste_surface()` extended with motif data:

```python
{
    "latest_insight": "...",
    "accumulated_motifs": {"clarity": 12, "craft": 8, "calm-focus": 5},
    "unique_motif_count": 3,
    "last_insight_at": "2026-04-13T20:30:00Z",
    # existing fields retained
}
```

## Testing

- `aesthetic_sense.py`: test `accumulate_from_daemon()` calls `detect_aesthetic_signals()` and writes to DB
- `aesthetic_taste_daemon.py`: test motif-gate (< 3 = no generate, >= 3 + 30 min = generate), test seed from DB, test new prompt includes motif summary
- `core/runtime/db.py`: test CRUD for `aesthetic_motif_log` (insert, unique_motifs, summary)
- Integration: verified manually by running Jarvis and observing in Mission Control

## What We Do NOT Build (Phase 2)

- Injecting taste-insights back into code_aesthetic_daemon's prompt
- Injecting taste-insights back into any other daemon's prompt
- Automatic motif weighting or decay
- Motif visualisation in Mission Control beyond `build_taste_surface()`
