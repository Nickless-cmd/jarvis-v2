# Decisions as Signals — Design Spec

**Date:** 2026-05-07
**Status:** Approved (Bjørn + Jarvis) — ready for implementation plan
**Owner:** Claude Code

## Problem

Jarvis's three active behavioral decisions appear as ~170 tokens of static rule-text in his prompt every visible turn, in the `[VERIFICATION]` section via `decision_enforcement.enforcement_section()`. As adherence drops, the format escalates with `⚠ DU SKAL`, `IKKE valgfrit`, `PÅKRØVEDE` language — which paradoxically makes them less effective.

Current data:

| Decision | Adherence | Pattern |
|---|---|---|
| `dec_2ac499e2de29` "Tjek om dette skal gemmes før hver svar" | 25% | broken, broken, partial, partial |
| `dec_d56d89ceec24` "Loop-nudge: tag bevidst stilling" | 33% | partial, broken, partial |
| `dec_56d4dbb03e22` "Backend issues inden 3 tool calls" | 42% | partial × 5, broken × 1 |

Jarvis's own self-evaluation notes confirm the mechanism: he's not maliciously ignoring decisions, he's not perceiving them as salient because they're drowning in static prompt text. Heed-rate on repetitive AWARENESS sections is ~1%.

## Goal

Convert behavioral decisions from always-on rule-text in the prompt to **signal-fired contextual prompting**. Decisions appear in the prompt only when a registered trigger detects relevance; otherwise the prompt is silent.

This applies the same principle Jarvis already used for tone (commit `a3160b4`: "Reduce hardcoded tone/behavior instructions — signals over form"): the system delivers raw signals, the entity interprets them itself.

## Non-goals

- Replacing or modifying nightly `consolidation_judge_daemon` review pipeline — adherence reviews continue unchanged
- Solving the broader prompt-bloat problem (signal-over-rule for SELF-MONITOR, OPERATIONAL, etc. — separate work)
- Building a natural-language classifier for `dec_2ac499e2de29` ("memorable info detected") — passive in v1
- Adding `decision_design_questionable` automatic flagging — separate concern, deferred

## Decisions (from Q&A)

| # | Decision | Choice |
|---|---|---|
| 1 | Format when fired | Strict: `decision:<id> fired (<context>)`. No directive text. |
| 2 | Trigger architecture | Hybrid registry: code-defined trigger functions registered by name; decisions reference triggers by `trigger_name` field |
| 3 | Default state when nothing fires | Total silence in prompt; `decision_review` tool is the recall path |
| 4 | Adherence escalation language | Removed entirely from prompt; adherence data lives in `decision_review` tool output |
| 5 | Multi-fire behavior | Per-decision cooldown (configurable per trigger; seconds or turns) |
| 6 | v1 trigger coverage | `dec_d56d89ceec24` and `dec_56d4dbb03e22` get triggers; `dec_2ac499e2de29` stays passive |
| 7 | Prompt section | New dedicated `[FIRED_DECISIONS]` AWARENESS category, separate from `[VERIFICATION]` |
| 8 | Implementation order | Big-bang with feature flag (no shadow-mode — owner forgets to flip switches) |

## Architecture

```
visible-turn → prompt_contract.build_visible_chat_prompt_assembly
                  │
                  ▼
              evaluate_decision_triggers(TriggerContext)
                  │
                  ├── reads behavioral_decisions where status=active
                  │   AND trigger_name IS NOT NULL
                  │
                  ├── for each: lookup TriggerSpec in _TRIGGER_REGISTRY
                  │   ├── call fire_fn(ctx) (sandboxed try/except)
                  │   ├── check cooldown via runtime_state_kv
                  │   └── if fires: write last_fired_at, publish event
                  │
                  ▼
              fired_decisions_section() → "[FIRED_DECISIONS]\n- decision:..."
                                          (or None if no fires)
                  │
                  ▼
              Inserted into AWARENESS budget alongside other categories
```

### New files

| Path | Responsibility |
|---|---|
| `core/services/decision_signals.py` | Trigger registry, `evaluate_decision_triggers()`, `fired_decisions_section()`, `build_trigger_context()` |
| `core/services/decision_triggers/__init__.py` | Imports all trigger modules so they self-register at app start |
| `core/services/decision_triggers/loop_nudge.py` | `loop_nudge_5_rounds` trigger function |
| `core/services/decision_triggers/backend_unresolved.py` | `backend_unresolved_3_calls` trigger function |
| `tests/services/test_decision_signals.py` | Registry, cooldown, killswitch tests |
| `tests/services/test_decision_triggers.py` | Per-trigger behavior tests |
| `tests/integration/test_decision_signals_in_prompt.py` | End-to-end via `build_visible_chat_prompt_assembly` |
| `tests/runtime/test_decision_signals_migration.py` | DB migration test |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/db.py` | Migration adds `trigger_name TEXT` column to `behavioral_decisions`; idempotent. Updates 2 existing rows with correct trigger names. |
| `core/runtime/db_decisions.py` | `list_decisions` and `get_decision` return the new field |
| `core/services/prompt_contract.py` | Replace `enforcement_section()` call with `fired_decisions_section()`. Add `fired_decisions` AWARENESS category. |
| `core/services/decision_enforcement.py` | `enforcement_section()` deprecated — returns empty string. Kept for 1-2 commits for rollback safety. |
| `core/runtime/settings.py` | Add `decision_signals_enabled: bool = True` |
| `core/eventbus/events.py` | Add `decision_signal` to `ALLOWED_EVENT_FAMILIES` |
| `core/services/visible_runs.py` | Bind `_current_trigger_context` ContextVar before prompt build |
| `core/services/decision_review` (the tool) | Extend output to include trigger_name, last_fired, recent_review_notes — adherence display moves here |

## Components

### `decision_signals.py` — registry + evaluation

```python
from dataclasses import dataclass, field
from typing import Callable, Optional

@dataclass
class TriggerContext:
    """Snapshot of state available to triggers."""
    user_message: str
    session_id: str | None
    run_id: str | None
    consecutive_tool_only_rounds: int
    recent_tool_calls: list[dict]      # last 10 in this run
    recent_assistant_text: str          # last assistant text block
    agentic_round_seq: int              # current round counter
    timestamp: str

@dataclass
class TriggerSpec:
    name: str
    fire_fn: Callable[[TriggerContext], bool]
    cooldown_seconds: int = 0
    cooldown_turns: int = 0

@dataclass
class FiredDecision:
    decision_id: str
    trigger_name: str
    context_summary: str  # short human-readable why-fired note

_TRIGGER_REGISTRY: dict[str, TriggerSpec] = {}

def register(
    name: str,
    fire_fn: Callable[[TriggerContext], bool],
    *,
    cooldown_seconds: int = 0,
    cooldown_turns: int = 0,
) -> None:
    """Trigger modules call this at import-time."""

def evaluate_decision_triggers(ctx: TriggerContext) -> list[FiredDecision]:
    """For each active decision with a registered trigger_name, evaluate
    and return those that fire (after cooldown check)."""

def fired_decisions_section(ctx: TriggerContext) -> str | None:
    """Build the [FIRED_DECISIONS] section text. Returns None if nothing fired
    or if killswitch is off."""

def build_trigger_context(*, user_message, session_id, run_id, **kwargs) -> TriggerContext:
    """Helper to build a context with sensible defaults from runtime state.
    Used when ContextVar is not set (e.g., tests)."""
```

**Cooldown storage:** `runtime_state_kv` table, key format `decision_signal_last_fired:<decision_id>`, value ISO timestamp. For turn-based cooldowns, additionally `decision_signal_turn_seq:<decision_id>` with the agentic-round-seq integer.

**Cooldown semantics across multi-turn conditions:** `cooldown_turns=N` blocks
re-firing for the next N turns *regardless* of whether the trigger condition
still holds. Concrete examples:

- `loop_nudge_5_rounds` with `cooldown_turns=1`: fires when
  `consecutive_tool_only_rounds == 5`. Trigger function uses `==`, so it only
  matches at exactly round 5 — round 6 won't match anyway. Cooldown is
  belt-and-suspenders: even if a future trigger update changes to `>= 5`,
  cooldown=1 still ensures one-fire-per-spree.

- `backend_unresolved_3_calls` with `cooldown_seconds=0`: no cooldown. Every
  turn the streak ≥ 3 with no resolution → fires. By design (incident-style
  nagging). If first-week observation shows it firing 5+ times per session
  in normal investigation work, switch this to a streak-aware mechanism.

**Section format:**

```
[FIRED_DECISIONS]
- decision:dec_d56d89ceec24 fired (loop_nudge_5_rounds at round 5)
- decision:dec_56d4dbb03e22 fired (backend_unresolved_3_calls)
```

If no decisions fired, the section is omitted entirely (not "[FIRED_DECISIONS] (none)").

### `decision_triggers/loop_nudge.py`

```python
from core.services.decision_signals import register

def loop_nudge_5_rounds(ctx) -> bool:
    return ctx.consecutive_tool_only_rounds == 5

register("loop_nudge_5_rounds", loop_nudge_5_rounds, cooldown_turns=1)
```

Cooldown: 1 turn — after firing, must wait one full agentic round before firing again. Prevents repeated firing on round 5, 6, 7... within a single tool-spree.

### `decision_triggers/backend_unresolved.py`

The decision is "Når jeg finder problem i **min egen backend** ..." — so the trigger
must distinguish "investigating Jarvis's own runtime/code" from "reading user
files for some other reason". Two filters apply, AND'd together:

1. **Tool name** matches a backend-investigation pattern
2. **Path argument** (when present) points inside Jarvis's own project tree

```python
from core.services.decision_signals import register

# Tool-name allowlist for backend-investigation tools
_BACKEND_TOOL_PATTERNS = ("read_file", "grep", "list_dir", "glob", "git_")

# Path prefixes that indicate "Jarvis's own backend"
# Both repo root and runtime state count as backend territory.
_JARVIS_PATH_HINTS = (
    "/media/projects/jarvis-v2",
    "/home/bs/.jarvis-v2",
    "core/",
    "apps/",
)

# Minimum length for an assistant text to count as a "resolution statement".
# Below 80 chars it's likely a status/checkpoint, not a real conclusion.
_RESOLUTION_MIN_CHARS = 80

# Keywords that signal a resolution conclusion was reached. Any one of these
# in a sufficiently long assistant text suppresses the trigger.
_RESOLUTION_KEYWORDS = (
    "fixed", "found", "root cause", "fundet", "fikset", "rod", "løst",
    "deployed", "deployet", "committed", "committet",
)


def _is_jarvis_backend_call(tool_call: dict) -> bool:
    """A tool call counts as backend-investigation if BOTH:
    - tool name matches an investigation pattern
    - path argument (if any) points inside Jarvis's project/runtime
    git_* calls have no path argument; we accept them by name alone since
    they are always in the current repo by definition.
    """
    fn = tool_call.get("function") or {}
    name = str(fn.get("name") or tool_call.get("name") or "")
    if not any(name.startswith(p) for p in _BACKEND_TOOL_PATTERNS):
        return False
    if name.startswith("git_"):
        return True
    args = fn.get("arguments") or tool_call.get("arguments") or {}
    if isinstance(args, str):
        try:
            import json as _j
            args = _j.loads(args)
        except Exception:
            args = {}
    path = str((args or {}).get("path") or (args or {}).get("dir") or "")
    if not path:
        # No path arg → treat as backend (e.g., bash without explicit cwd)
        return True
    return any(hint in path for hint in _JARVIS_PATH_HINTS)


def backend_unresolved_3_calls(ctx) -> bool:
    """Three consecutive Jarvis-backend tool calls without a resolution-text response."""
    backend_streak = 0
    for tc in ctx.recent_tool_calls[-5:]:
        if _is_jarvis_backend_call(tc):
            backend_streak += 1
        else:
            backend_streak = 0
    if backend_streak < 3:
        return False
    last_text = (ctx.recent_assistant_text or "").strip().lower()
    if len(last_text) >= _RESOLUTION_MIN_CHARS and any(kw in last_text for kw in _RESOLUTION_KEYWORDS):
        return False
    return True

register("backend_unresolved_3_calls", backend_unresolved_3_calls, cooldown_seconds=0)
```

**Cooldown semantics:** `cooldown_seconds=0` means "fire every turn while the
condition holds". If 3 backend calls fire on turn N, and turn N+1 adds a 4th
backend call without resolution, the trigger fires *again* on N+1 (streak is
now 4 ≥ 3, no resolution). Intentional — this is an incident trigger and we
want it to keep nagging until either resolved or the streak breaks. If the
nagging proves too noisy in first-week observation, switch to a one-shot-per-
streak mechanism (track `last_fired_streak_id` derived from the streak's
starting tool_call_id).

**TriggerContext requirement:** `recent_tool_calls` must include each tool
call's `arguments` field (a dict, or JSON string). `visible_runs.py` already
captures these in `_followup_exchanges`; the context-builder must preserve
them rather than reducing to just names.

### `decision_triggers/__init__.py`

```python
"""Importing this package registers all known triggers."""
from . import loop_nudge  # noqa: F401
from . import backend_unresolved  # noqa: F401
```

App startup (or first call to `decision_signals` module) imports the package, populating `_TRIGGER_REGISTRY`.

### Modified: `prompt_contract.py`

Around line 736 (where `enforcement_section()` is called):

```python
try:
    from core.services.decision_signals import (
        fired_decisions_section,
        get_current_trigger_context_or_build,
    )
    ctx = get_current_trigger_context_or_build(
        user_message=user_message,
        session_id=session_id,
    )
    section = fired_decisions_section(ctx)
    if section:
        _awareness_add(90, "fired decisions", section)
except Exception:
    pass
```

The `enforcement_section()` call remains as a no-op (function returns `""`) for 1-2 commits as rollback safety, then removed.

A new AWARENESS category mapping:

```python
"fired_decisions": "[FIRED_DECISIONS]",
```

And rule:

```python
("fired decisions", "fired_decisions"),
```

### Modified: `decision_review` tool output

Today's output is replaced/extended:

```
decision:dec_d56d89ceec24 — "Når loop-nudge fyrer, tager jeg bevidst stilling..."
  status: active
  trigger: loop_nudge_5_rounds (cooldown 1 turn)
  adherence: 33% over 3 reviews
  last_fired: 2026-05-07T08:14:06+00:00
  last_reviewed: 2026-05-06T23:23:16+00:00
  recent_review_notes:
    - 2026-05-06 23:23: partial — "Jeg husker at have tænkt over valget..."
    - 2026-05-06 16:13: broken — "Lige siden sidste review..."
```

No "DU SKAL", no "IKKE valgfrit". Just data.

### `behavioral_decisions` migration

Add column:

```sql
ALTER TABLE behavioral_decisions ADD COLUMN trigger_name TEXT;
```

(Idempotent — wrapped in try/except since SQLite doesn't support `IF NOT EXISTS` on `ADD COLUMN`.)

Update existing rows:

```sql
UPDATE behavioral_decisions
   SET trigger_name = 'loop_nudge_5_rounds'
 WHERE decision_id = 'dec_d56d89ceec24';

UPDATE behavioral_decisions
   SET trigger_name = 'backend_unresolved_3_calls'
 WHERE decision_id = 'dec_56d4dbb03e22';

-- dec_2ac499e2de29 stays NULL (passive in v1)
```

## Data flow per turn

1. User sends message → `start_visible_run`
2. Inside `visible_runs.py`, build `TriggerContext`:
   - `user_message`, `session_id`, `run_id` from run state
   - `consecutive_tool_only_rounds` from existing tracker
   - `recent_tool_calls` from `_followup_exchanges` (last 10)
   - `recent_assistant_text` from last assistant content block
   - `agentic_round_seq` from current round counter
3. Bind context as `_current_trigger_context` ContextVar
4. `_build_visible_input` → `build_visible_chat_prompt_assembly` runs
5. Inside prompt assembly, `fired_decisions_section(ctx)` is called:
   - `evaluate_decision_triggers(ctx)` queries `behavioral_decisions WHERE status='active' AND trigger_name IS NOT NULL`
   - For each: lookup in `_TRIGGER_REGISTRY`, call `fire_fn(ctx)` in sandbox
   - If fires AND cooldown passed: append to `fired`, write `last_fired_at`, publish `decision_signal.fired` event
6. If `fired` is non-empty, `[FIRED_DECISIONS]` section added to AWARENESS budget; otherwise section omitted
7. Prompt assembled, sent to provider
8. Run completes; existing `consolidation_judge_daemon` (nightly) reviews decisions against transcripts as before — unchanged

## Error handling

| Failure | Detection | Response |
|---|---|---|
| Trigger function raises | Try/except per-trigger | Log warning, treat as not-fired, continue with next |
| Trigger name on decision not in registry | Lookup miss | Decision treated as passive (no-op). Log debug at first miss per session |
| `behavioral_decisions` table query fails | DB error | `fired_decisions_section()` returns `None`, prompt continues |
| Cooldown KV write fails | DB error | Trigger fires (event published), cooldown not written → may fire next turn. Acceptable degradation |
| `TriggerContext` field missing | AttributeError in `fire_fn` | Caught by sandbox wrapper, treat as not-fired |
| Killswitch off | Settings flag | `fired_decisions_section()` returns `None` immediately, no evaluation, no events |
| Empty directive on decision | n/a | Trigger evaluates normally — directive text not used in prompt |
| ContextVar not bound | None on get | Use `build_trigger_context_fallback` with empty defaults; runtime-state-dependent triggers won't fire |

### Hard guarantees

1. **Prompt assembly never blocked by signal pipeline.** All entry points wrapped in try/except.
2. **Triggers are sandboxed.** A broken trigger doesn't prevent other triggers from firing.
3. **Cooldown failures cause more noise, not less.** Better to fire twice than to lose the signal.
4. **Migration is reversible.** `decision_signals_enabled = False` in `runtime.json` immediately restores old behavior; `enforcement_section()` runs as before.
5. **`trigger_name` column is optional.** Decisions without it are passive forpligtelser, fully supported.

### Logging

- `decision_signals.evaluate failed for <decision_id>: <err>` (warning) on trigger exception
- `decision_signals.unknown_trigger <trigger_name> for <decision_id>` (debug, once per session) on registry miss
- `decision_signals.fired <decision_id> via <trigger_name>` (info) on fire

## Testing

### Unit tests (`tests/services/test_decision_signals.py`)

- `register()` adds to registry; duplicate name overwrites with warning
- `evaluate_decision_triggers()` returns empty when no decisions have `trigger_name`
- Trigger raises → caught, others still evaluated
- Unknown `trigger_name` → silent skip
- Cooldown by seconds: fires once, blocked within window, fires after window
- Cooldown by turns: fires at round N, blocked at N+1, fires at N+1+cooldown
- `fired_decisions_section()` returns `None` when no fires
- Killswitch off → returns `None` without evaluation
- Killswitch off → no events published

### Trigger tests (`tests/services/test_decision_triggers.py`)

- `loop_nudge_5_rounds`: fires at exactly 5; not 4, not 6
- `backend_unresolved_3_calls`:
  - Fires after 3 backend tool calls in a row
  - Not after 2
  - Reset on non-backend tool
  - Suppressed by resolution-text in last assistant message
  - Fires again on next 3-streak after suppression

### Integration test (`tests/integration/test_decision_signals_in_prompt.py`)

- Build a real `TriggerContext`, run `fired_decisions_section()`
- Verify `[FIRED_DECISIONS]` appears in `build_visible_chat_prompt_assembly` output
- Verify `decision_signal.fired` event published with correct payload
- Verify `decision_signal_last_fired:<id>` written to `runtime_state_kv`

### Migration test (`tests/runtime/test_decision_signals_migration.py`)

- `behavioral_decisions` gets `trigger_name` column
- Existing rows updated for the 2 known decision IDs (third stays NULL)
- Re-running migration is idempotent

### Smoke test extension

`scripts/smoke_test_startup.py` already drives full lifespan. Add: import `decision_signals`, verify registry has at least the 2 expected triggers after import-time registration.

## Rollout

### Pre-deploy

1. All tests green
2. `compileall` clean
3. Smoke test passes
4. Manual sanity: confirm `_TRIGGER_REGISTRY` populates correctly after `from core.services import decision_triggers`

### Deploy (big-bang with feature flag)

1. Restart `jarvis-runtime` and `jarvis-api`
2. Watch first 3 visible turns: confirm `[FIRED_DECISIONS]` appears only when expected
3. Confirm `enforcement_section()` no longer in prompt (no `🤝 AKTIVE FORPLIGTELSER` text)
4. Tail eventbus for `decision_signal.fired` events

### First-day observation

- Trigger fire counts per day per decision (via `events` table query)
- Adherence in nightly `consolidation_judge_daemon` review
- Any `decision_signals.evaluate failed` warnings

### First-week measurement

- Compare adherence-scores 7-day before vs 7-day after deploy
- Target: at least one decision moves from <40% to >60%
- If all three stay <40%: signal-mechanism alone isn't sufficient; revisit with consolidation_judge providing better evidence

### Killswitch

`decision_signals_enabled: bool = True` in `RuntimeSettings`. Flippable via `~/.jarvis-v2/config/runtime.json` without restart (settings reloader picks up within 30s).

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Trigger evaluation adds prompt-build latency | Each trigger sandboxed, cheap operations only; full pipeline target <50ms |
| `dec_2ac499e2de29` adherence stays at 25% with no trigger to support it | Acceptable for v1; revisit when we have classifier infrastructure |
| Triggers fire too often, become new background noise | Per-decision cooldown; first-week observation will catch this |
| Triggers fire too rarely, decisions effectively never present | First-week measurement; if no firings observed, broaden trigger conditions |
| Removing escalation language reduces perceived urgency | Acceptable — the data shows escalation reduced adherence |
| Migration fails on existing DB | Wrapped in try/except; absence of `trigger_name` column means decisions all behave as passive (graceful degradation) |
| `recent_tool_calls` not available when ContextVar isn't bound | Triggers requiring it return False; section omitted; no error |

## Success criteria

- `[FIRED_DECISIONS]` section present in prompt only when at least one trigger fires
- No `🤝 AKTIVE FORPLIGTELSER` / `DU SKAL` / `IKKE valgfrit` text in prompt
- `decision_signal.fired` events visible in MC events stream
- After 7 days: at least one decision's adherence score improves vs pre-deploy baseline
- Killswitch tested: setting `decision_signals_enabled=False` restores old behavior within 30s
- No regression in `consolidation_judge_daemon` nightly review (still produces verdicts for active decisions)

## Out of scope (deferred)

- NL-classifier or heuristic for `dec_2ac499e2de29` ("memorable info detected") — requires real classifier infrastructure; revisit after first-week measurement
- `decision_design_questionable` event from `consolidation_judge_daemon` — separate concern
- Auto-suggestion of triggers in `decision_create` tool — UX work for v2
- Multi-trigger per decision (OR-logic across multiple `trigger_name`s) — current schema supports single; extend to JSON array later if needed
- Generalizing the signal-over-rule refactor to other AWARENESS sections (SELF-MONITOR, OPERATIONAL, etc.) — separate work
- Visualization in MC of fired-decisions over time — when we have data worth showing
