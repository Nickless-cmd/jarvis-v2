# Jarvis Self-Tools Design

**Date:** 2026-04-12  
**Status:** Approved  
**Topic:** Daemon introspection, signal access, eventbus observation, and runtime control tools for Jarvis

## Problem

Jarvis has ~21 daemons, 50+ signal surfaces, and a full eventbus — but no tools to observe or control any of it. He can read source code and files, but has no live nervous-system connection to his own internal states. Mission Control has all of this; Jarvis needs the bridge.

## Scope

Six new tools added to Jarvis' visible lane, backed by a new `daemon_manager` service.

## Architecture

### New file: `apps/api/jarvis_api/services/daemon_manager.py`

Single responsibility: daemon registry, lifecycle control, and state persistence.

**Registry** — static dict over all 21 daemons:
```python
_DAEMON_REGISTRY = {
    "curiosity":  {"tick_fn": tick_curiosity_daemon,  "default_cadence_minutes": 5,  "description": "..."},
    "conflict":   {"tick_fn": tick_conflict_daemon,   "default_cadence_minutes": 10, "description": "..."},
    # ... alle 21
}
```

**State file** — `~/.jarvis-v2/workspaces/default/runtime/DAEMON_STATE.json`:
```json
{
  "curiosity": {
    "enabled": true,
    "interval_minutes_override": null,
    "last_run_at": "2026-04-12T08:00:00Z",
    "last_result_summary": "generated: true, gap_type: question"
  }
}
```

**Exposed functions:**
- `get_all_daemon_states()` → list of all daemons with name, enabled, effective_cadence_minutes, last_run_at, hours_since_last_run, last_result_summary
- `control_daemon(name, action, interval_minutes?)` — actions: `enable`, `disable`, `restart`, `set_interval`
- `record_daemon_tick(name, result)` — called by heartbeat_runtime after each daemon call
- `is_enabled(name)` → bool

**`restart` semantics:** clears the module-level `_last_tick_at` attribute in the daemon module directly, so the daemon fires on the next heartbeat tick.

### Modified: `apps/api/jarvis_api/services/heartbeat_runtime.py`

Before each daemon call, check daemon_manager:
```python
if daemon_manager.is_enabled("curiosity"):
    result = tick_curiosity_daemon(fragments)
    daemon_manager.record_daemon_tick("curiosity", result)
```

No other changes to heartbeat logic.

### New tool definitions in `core/tools/simple_tools.py`

#### 1. `daemon_status()`
Returns all 21 daemons: name, enabled, default_cadence_minutes, interval_override, last_run_at, hours_since_last_run, last_result_summary. No parameters.

#### 2. `control_daemon(name, action, interval_minutes?)`
- `action`: one of `enable`, `disable`, `restart`, `set_interval`
- `interval_minutes`: required only for `set_interval`, must be ≥ 1
- Unknown `name` → `{"error": "unknown daemon", "valid": [...]}`
- `set_interval` with `interval_minutes < 1` → rejected with error

#### 3. `list_signal_surfaces()`
Calls all ~50 `build_runtime_*_surface()` functions. Returns compact overview — surface name + key fields per surface. Catches exceptions per surface and returns `{"error": "..."}` for failed ones without aborting the rest. No parameters.

#### 4. `read_signal_surface(name)`
Routes `name` → `build_runtime_*_surface()`. Returns full surface for the named signal. Unknown `name` → `{"error": "unknown surface", "valid": [...]}`.

#### 5. `eventbus_recent(kind?, limit?)`
Wrapper around `event_bus.recent(limit)`. Filters by `kind` (event family) if provided. Default limit: 20, max: 100.

#### 6. `update_setting(key, value)`
Loads settings, updates key, writes back. Returns `{"old": ..., "new": ..., "key": ...}`.

**Approval gating:** keys matching `provider.*credential`, `approval.*`, or `auth.*` are routed through the existing `tool_intent_approval_runtime` flow and block until approved or rejected.

## Signal Surface Router

A dict in `apps/api/jarvis_api/services/signal_surface_router.py` maps surface names to their build functions:
```python
_SIGNAL_SURFACE_ROUTER = {
    "autonomy_pressure": build_runtime_autonomy_pressure_signal_surface,
    "relation_state": build_runtime_relation_state_signal_surface,
    # ... all ~50
}
```

## Testing

Three new test files following TDD (red → green):

**`tests/test_daemon_manager.py`**
- Registry contains all 21 known daemons
- `get_all_daemon_states()` returns correct fields
- `enable`/`disable` updates state and persists to JSON
- `restart` clears `_last_tick_at` on the target module
- `set_interval` with valid value persists override
- `set_interval` with `interval_minutes < 1` raises error
- `record_daemon_tick` updates `last_run_at` and `last_result_summary`

**`tests/test_daemon_tools.py`**
- `daemon_status` returns list with all 21 daemons
- `control_daemon` with unknown name returns error + valid list
- `list_signal_surfaces` returns dict keyed by surface name
- `read_signal_surface` with unknown name returns error + valid list
- `eventbus_recent` with kind filter returns only matching events
- `update_setting` for sensitive key triggers approval flow
- `update_setting` for non-sensitive key returns old + new values

**`tests/test_signal_surface_router.py`**
- All registered surface names resolve to callable functions
- Unknown name returns error with valid names list

## Error Handling Summary

| Scenario | Response |
|---|---|
| Unknown daemon name | `{"error": "unknown daemon", "valid": [...]}` |
| Unknown signal surface | `{"error": "unknown surface", "valid": [...]}` |
| `set_interval` with `< 1` | `{"error": "interval_minutes must be >= 1"}` |
| `restart` on never-run daemon | no-op, success |
| Signal surface build failure | `{"error": "..."}` for that surface, rest delivered |
| Sensitive setting update | Routed to approval flow, blocked until resolved |

## Files Changed

| File | Change |
|---|---|
| `apps/api/jarvis_api/services/daemon_manager.py` | New |
| `apps/api/jarvis_api/services/signal_surface_router.py` | New |
| `core/tools/simple_tools.py` | Add 6 tool definitions + handlers |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Add daemon_manager checks around each daemon call |
| `tests/test_daemon_manager.py` | New |
| `tests/test_daemon_tools.py` | New |
| `tests/test_signal_surface_router.py` | New |
