# Counterfactuals — Design Spec

**Date:** 2026-05-07
**Status:** Approved (Bjørn + Jarvis) — ready for implementation plan
**Owner:** Claude Code

## Problem

Jarvis lacks **counterfactual reasoning** — the capacity to reflect on regret-events and ask "what if we had done X instead?". The original `jarvis-ai/agent/cognition/counterfactuals.py` exists, but a 1:1 port would inherit two design problems:

1. **Hardcoded what-if templates.** The original maps every regret-event to one of four pre-written sentences ("What if we had chosen a slower validation path?"). Same sentence for every regret. That's a template machine, not counterfactual thinking.
2. **Dead confidence scores.** Hardcoded values 0.59-0.68, never reaching the promotion threshold (0.72). Status field is essentially dead.

V2 has richer raw material — actual eventbus families with real friction signals — and infrastructure (cheap-lane LLM, apophenia_guard, eventbus, workspace-scoped storage) that the original didn't have access to.

## Goal

Port the **capability** of counterfactual reflection from jarvis-ai to jarvis-v2, with a v2-native design:

- Detect regret-worthy events from v2's eventbus (4 trigger families)
- Cluster related events semantically via cheap-lane LLM (not hardcoded keys)
- Generate context-rich what-if counterfactuals per cluster
- Score with separated `llm_confidence` + `apophenia_score`, take `min()` as `final_confidence`
- Store workspace-scoped, idempotent via `UNIQUE(cf_key)` constraint
- Surface passively in v1 (tool-only); active surfacing as separate v2 work

## Non-goals

- Active prompt-injection of counterfactuals (deferred — depends on v1 utility data)
- LLM-driven trigger-event selection (deferred — start with hardcoded 4 families, evolve later)
- Cross-workspace "system-wide reflection" tier (deferred — privacy boundary stays workspace-scoped in v1)
- Retention/cleanup policy (deferred — addressed when DB volume is measurable, ~3+ months out)

## Decisions (from Q&A)

| # | Decision | Choice |
|---|---|---|
| 1 | When triggers fire | Cadenced via dedicated daemon (60-min interval default), reflective not reactive. REFLECT-phase of phased_heartbeat may also call it ad-hoc. |
| 2 | Trigger event scope (v1) | Four families: `self_review_outcome.created`, `conflict.detected`, `decision_revoked`, `behavioral_decision_review.broken`. NOT the 1949 `heartbeat.conflict_resolved` (auto-resolved noise). NOT `tool.error` (mostly transient). |
| 3 | Clustering strategy | Time-window forbehandling (cf_key dedup) + LLM-driven semantic clustering in single call. Two layers, not competitors. |
| 4 | Confidence model | Three separate fields: `llm_confidence` (LLM self-rated, typically optimistic), `apophenia_score` (1.0 default = no dampening, lowered when pattern is thin), `final_confidence = min(both)` for promotion. |
| 5 | Surfacing strategy | v1: passive — stored + tool. No automatic prompt injection. Active surfacing (signal-fired or REFLECT-injection) is a separate post-v1 question. |
| 6 | Workspace scoping | Workspace-scoped storage. Source events keep their session_id/run_id as metadata. Cross-workspace reflection is deferred. |
| 7 | Implementation order | Iterative — 4 phases. Phase 1 is dry-run for 7 days (capture volume + types), Phase 2 enables LLM, Phase 3 adds apophenia, Phase 4 exposes via tool. |
| 8 | Promotion threshold | `final_confidence >= 0.6` → status="promoted", else "generated". Configurable via setting. |

## Architecture

```
counterfactual_engine_runtime daemon
    │ (60-min cycle, idempotent, per-workspace lock)
    ▼
For each active workspace:
    │
    ▼
counterfactual_engine.run(workspace_id)
    │
    ├── 1. fetch_recent_triggers(workspace_id, lookback=60min)
    │       └── reads events table for 4 trigger families
    │
    ├── 2. First-pass dedup via cf_key
    │       └── SELECT cf_key FROM counterfactuals WHERE cf_key IN (...)
    │
    ├── 3. _generate_counterfactuals_via_llm(triggers)  [Phase 2+]
    │       └── single cheap-lane call: semantic cluster + generate
    │
    ├── 4. _modulate_with_apophenia(counterfactuals)  [Phase 3+]
    │       └── per-cf: apophenia_score, then final_confidence = min(...)
    │
    ├── 5. INSERT OR IGNORE INTO counterfactuals
    │       └── UNIQUE(cf_key) makes this idempotent
    │
    ├── 6. Publish cognitive_counterfactual.generated per row
    │
    └── 7. Publish cognitive_counterfactual.cycle_complete summary

Phase 4 surfacing:
    Jarvis (or user) calls list_counterfactuals(workspace_id, status, limit)
    → returns rows from counterfactuals table
```

### New files

| Path | Responsibility |
|---|---|
| `core/services/counterfactual_triggers.py` | TriggerEvent dataclass, `fetch_recent_triggers()`, per-family `_key_*()` extractors, `cf_key()` hash |
| `core/services/counterfactual_engine.py` | `run()` orchestrator, `_generate_counterfactuals_via_llm()`, `_modulate_with_apophenia()`, internal storage write |
| `core/services/counterfactual_engine_runtime.py` | Daemon: `start_counterfactual_runtime()`, `_loop()`, per-workspace advisory lock |
| `core/tools/counterfactuals_tools.py` | `list_counterfactuals` + `get_counterfactual` tool definitions and handlers (Phase 4) |
| `tests/services/test_counterfactual_triggers.py` | |
| `tests/services/test_counterfactual_engine.py` | |
| `tests/services/test_counterfactual_engine_runtime.py` | |
| `tests/runtime/test_counterfactuals_migration.py` | |
| `tests/api/test_counterfactuals_tool.py` | |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/db.py` | New `_ensure_counterfactuals_table()`; called from `init_db()`; idempotent |
| `core/runtime/settings.py` | Add `counterfactual_engine_enabled`, `_interval_seconds`, `_lookback_minutes`, `_promotion_threshold` |
| `core/eventbus/events.py` | Add `cognitive_counterfactual` to `ALLOWED_EVENT_FAMILIES` |
| `apps/api/jarvis_api/app.py` | Start/stop counterfactual_runtime daemon in lifespan |
| `core/tools/simple_tools.py` | Register tool definitions + handlers (Phase 4) |
| `scripts/smoke_test_startup.py` | Verify counterfactuals table exists + daemon importable |

## Components

### `counterfactual_triggers.py`

```python
@dataclass
class TriggerEvent:
    """A regret-worthy event normalized for counterfactual processing."""
    source_event_id: int
    workspace_id: str
    event_type: str
    primary_key: str       # decision_id|review_id|conflict_id|run_id (whichever is present)
    summary: str
    payload: dict
    created_at: str


def fetch_recent_triggers(*, workspace_id: str, lookback_minutes: int = 60) -> list[TriggerEvent]:
    """Query events table for the 4 trigger families within window."""


_TRIGGER_FAMILIES = {
    "self_review_outcome.created": _key_self_review,
    "conflict.detected": _key_conflict,
    "cognitive_decision.revoked": _key_decision,
    "behavioral_decision_review.broken": _key_review,
}

def _key_self_review(payload: dict) -> str:
    return str(payload.get("review_id") or payload.get("run_id") or "")
def _key_conflict(payload: dict) -> str:
    return str(payload.get("conflict_id") or payload.get("run_id") or "")
def _key_decision(payload: dict) -> str:
    return str(payload.get("decision_id") or "")
def _key_review(payload: dict) -> str:
    return str(payload.get("review_id") or "")


def cf_key(workspace_id: str, event_type: str, primary_key: str) -> str:
    """First-pass dedup. Same workspace+type+key = same hash = skip."""
    raw = f"{workspace_id}:{event_type}:{primary_key}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]
```

If `primary_key` is empty (event missing all expected anchors), the trigger is **skipped** — we won't dedup or process events without a stable identifier.

### `counterfactual_engine.py`

```python
def run(*, workspace_id: str, dry_run: bool = False) -> dict:
    """One full pipeline cycle. Returns summary dict.

    dry_run=True: skip LLM call (Phase 1 mode). All counterfactuals get
    what_if="TODO", llm_confidence=0.0.

    Returns: {
        "workspace_id": str,
        "triggers_fetched": int,
        "triggers_unique": int,
        "trigger_breakdown": {event_type: count, ...},
        "counterfactuals_generated": int,
        "promoted": int,
        "llm_generation_failures": int,
        "elapsed_ms": int,
        "skipped": bool,        # True if killswitch off or lock held
        "skipped_reason": str,
    }
    """


def _generate_counterfactuals_via_llm(triggers: list[TriggerEvent]) -> list[dict]:
    """Single cheap-lane call. Returns list of cluster dicts:
    [{cluster_label, source_event_ids, what_if, likely_difference,
      llm_confidence (0-1), reasoning}, ...]
    On parse failure: returns [], increments error counter.
    """


def _modulate_with_apophenia(counterfactuals: list[dict]) -> list[dict]:
    """For each cf: apophenia_score = apophenia_guard.rate_hypothesis(...).
    Phase 3+: real call. Phase 1-2: returns 1.0 (no dampening).
    final_confidence = min(llm_confidence, apophenia_score).
    """
```

**LLM prompt structure** (Phase 2+):

```
You are Jarvis reflecting on recent events where things didn't go as planned.
For each cluster of related regret-events, generate ONE counterfactual:
"What if [specific alternative action] instead of [what happened]?"

Input: {N} regret-candidates from the last 60 minutes.
Format: JSON array of {
  cluster_label: short string,
  source_event_ids: [int, ...] (ids from input below),
  what_if: "What if ...",
  likely_difference: "Outcome would have been ...",
  llm_confidence: 0.0-1.0,
  reasoning: brief explanation
}

Events:
[1] self_review_outcome at 12:34: '<summary>' (review_id=rev_abc, run_id=visible-xxx)
[2] decision_revoked at 12:18: 'dec_56d4...' (directive: '<directive>')
[3] conflict.detected at 11:50: '<summary>'
...
```

Cheap-lane call uses `task_kind="counterfactual_gen"`. JSON-only response;
prose responses cause `json.JSONDecodeError` → counted in
`llm_generation_failures`, cycle continues with placeholder values.

### `counterfactual_engine_runtime.py`

Daemon mirrors `tool_router_runtime.py`:

```python
_INTERVAL_S = 60 * 60  # default; overridable via settings
_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_WORKSPACE_LOCKS: dict[str, threading.Lock] = {}

def start_counterfactual_runtime() -> None: ...
def stop_counterfactual_runtime() -> None: ...

def _get_workspace_lock(workspace_id: str) -> threading.Lock:
    """Lazy per-workspace lock. Used to prevent overlapping cycles per workspace."""

def _loop():
    while not _STOP.is_set():
        try:
            for ws in _list_active_workspaces():
                lock = _get_workspace_lock(ws)
                if not lock.acquire(blocking=False):
                    logger.info("counterfactual_runtime: skipping %s, lock held", ws)
                    continue
                try:
                    counterfactual_engine.run(workspace_id=ws)
                except Exception as exc:
                    logger.warning(
                        "counterfactual_runtime: cycle failed for %s: %s", ws, exc
                    )
                finally:
                    lock.release()
        except Exception as exc:
            logger.warning("counterfactual_runtime: outer loop error: %s", exc)
        _STOP.wait(_INTERVAL_S)
```

### `counterfactuals` DB-table

```sql
CREATE TABLE IF NOT EXISTS counterfactuals (
    cf_id TEXT PRIMARY KEY,                      -- "cf-<hex>"
    cf_key TEXT NOT NULL UNIQUE,                 -- first-pass dedup hash
    workspace_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,                    -- LLM-assigned cluster label
    trigger_event_ids_json TEXT NOT NULL,        -- JSON array of source_event_ids
    trigger_types_json TEXT NOT NULL,            -- JSON array of distinct event_types
    what_if TEXT NOT NULL,
    likely_difference TEXT,
    reasoning TEXT,                              -- LLM's brief explanation
    llm_confidence REAL DEFAULT 0.0,
    apophenia_score REAL DEFAULT 1.0,            -- 1.0 = no dampening
    final_confidence REAL DEFAULT 0.0,           -- min(llm, apophenia)
    status TEXT NOT NULL,                        -- "generated" | "promoted" | "archived"
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_counterfactuals_workspace_created
  ON counterfactuals(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_counterfactuals_status
  ON counterfactuals(status);
```

Storage uses `INSERT OR IGNORE`. UNIQUE constraint on `cf_key` makes the
pipeline idempotent: re-runs of the same trigger event are no-ops.

### `counterfactuals_tools.py` (Phase 4)

```python
def _exec_list_counterfactuals(arguments: dict) -> dict:
    """list_counterfactuals(workspace_id, status='all', limit=20)"""

def _exec_get_counterfactual(arguments: dict) -> dict:
    """get_counterfactual(cf_id)"""

LIST_COUNTERFACTUALS_DEF = {
    "type": "function",
    "function": {
        "name": "list_counterfactuals",
        "description": "List counterfactual reflections for the current workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "default": "default"},
                "status": {
                    "type": "string",
                    "enum": ["all", "generated", "promoted", "archived"],
                    "default": "all",
                },
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
            },
        },
    },
}
```

Cross-workspace isolation: `list_counterfactuals(workspace_id="default")` returns only rows where `workspace_id = 'default'`.

### Settings + event family

```python
# core/runtime/settings.py
counterfactual_engine_enabled: bool = True
counterfactual_engine_interval_seconds: int = 3600
counterfactual_engine_lookback_minutes: int = 60
counterfactual_engine_promotion_threshold: float = 0.6

# core/eventbus/events.py — ALLOWED_EVENT_FAMILIES
"cognitive_counterfactual",
```

## Data flow per cycle

(Detailed flow already laid out in design section 3 — included verbatim above
in the Architecture diagram. Not duplicated here to keep the spec scannable.)

## Error handling

Documented in design section 4. Hard guarantees:

1. **Daemon never crashes** — all `run()` calls wrapped in try/except inside `_loop()`
2. **Pipeline is idempotent** — `UNIQUE(cf_key)` + `INSERT OR IGNORE` + per-workspace lock
3. **Per-failure graceful degradation** — corrupt event, LLM fail, apophenia fail all have no-op defaults; pipeline continues
4. **Killswitch lives in settings** — runtime-flippable without restart, checked per-cycle
5. **Cross-workspace isolation** — failure in workspace A doesn't block workspace B

## Testing

(Documented in design section 5.) Tests cover unit (per-component), integration
(end-to-end via `run()` with mocked LLM and apophenia), migration, smoke,
and per-workspace isolation. **The `INSERT OR IGNORE` idempotency test —
"run same batch twice = identical DB state" — is mandatory.**

## Rollout — four phases

### Phase 1 (week 1, ~7 days): Capture with placeholders

Deploy:
- Settings, migration, trigger detection, dedup
- `counterfactual_engine.run(dry_run=True)` (LLM disabled)
- Daemon at 60-min cadence
- Event family `cognitive_counterfactual` allowed

Verification (after 7 days):
```bash
# Trigger volume distribution by type
SELECT json_extract(payload_json, '$.trigger_breakdown') FROM events
 WHERE kind = 'cognitive_counterfactual.cycle_complete'
 ORDER BY id DESC LIMIT 50;

# Per-cycle volume
SELECT json_extract(payload_json, '$.triggers_fetched'),
       json_extract(payload_json, '$.triggers_unique')
FROM events WHERE kind='cognitive_counterfactual.cycle_complete';
```

Expected: 5-15 triggers/cycle, dedup → 3-8 unique. Distribution check: which trigger family dominates? If one is >95%, consider throttling that family in Phase 2 prompt-prep. **`trigger_breakdown` field added to summary specifically to enable this analysis.**

### Phase 2 (~3-5 days): LLM generation

Deploy:
- `dry_run=False`
- LLM-prompt as documented
- `llm_generation_failures` counter live

Verification:
- Read 10 random counterfactuals — meaningful what-ifs? Generic?
- LLM-failure-rate < 5%?
- Latency: cycle completes in < 30s?

### Phase 3 (~3-5 days): Apophenia modulation

Deploy:
- `_modulate_with_apophenia` enabled
- `final_confidence = min(...)` computed
- Promotion threshold active

Verification:
- Compare `llm_confidence` vs `apophenia_score` on 20 cfs
- Promoted-rate: 20-40%? If 0%: threshold too high or apophenia too strict. If 80%+: apophenia not doing its job.

### Phase 4 (continuous): Tool exposition

Deploy:
- `list_counterfactuals` + `get_counterfactual` registered
- Tool definitions in `TOOL_DEFINITIONS`

Verification:
- Does Jarvis use the tool organically in REFLECT?
- Does tool_router select it when relevant?
- Org-test: if he never uses it, the question of whether counterfactuals are useful is answered.

### Killswitch (any phase)

```json
// ~/.jarvis-v2/config/runtime.json
{"counterfactual_engine_enabled": false}
```

Settings reload picks it up within 30s. Daemon loop continues but each `run()` is no-op.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| LLM generates generic what-ifs | Phase 2 verification reads samples; iterate prompt before Phase 3 |
| One trigger family dominates volume | Phase 1 `trigger_breakdown` field catches this; throttle in Phase 2 |
| Apophenia dampens too aggressively | Phase 3 verifies promoted-rate 20-40% band; tune threshold or apophenia inputs |
| Daemon overlaps cycles | Per-workspace advisory lock |
| LLM-lane down for hours | `llm_generation_failures` counter visible in MC; alarm threshold can be added |
| Counterfactuals accumulate without cleanup | Deferred — addressed when DB volume measurable |
| Cross-workspace data leak | Isolation test mandatory; tool filters by `workspace_id` |

## Success criteria

- After 7 days of Phase 1: trigger detection produces 5-15/cycle with reasonable distribution
- After Phase 2: LLM-failure-rate < 5%, latency < 30s, what-ifs are specific (not generic templates)
- After Phase 3: 20-40% of generated counterfactuals get promoted (final_confidence ≥ 0.6)
- After Phase 4: tool used organically by Jarvis at least 1×/week, OR clear evidence the capability isn't valuable enough to keep
- Killswitch verified: setting `counterfactual_engine_enabled=False` makes all `run()` calls no-op within 30s
- Per-workspace isolation verified: workspace A's tool calls never see workspace B's data

## Out of scope (deferred)

- Active surfacing — signal-fired on new decisions matching past counterfactuals
- LLM-driven trigger-event selection (vs hardcoded 4 families)
- Cross-workspace "system-wide reflection" tier
- Retention/cleanup policy
- Visualization in MC dashboard
- Importing the other 3 cognition modules (aesthetics, dream_engine, immune_system) — separate plans per module
