# Jarvis Self-Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis six tools to observe and control his own daemons, signal surfaces, eventbus, and runtime settings.

**Architecture:** A new `daemon_manager.py` service holds the daemon registry and persists state to `DAEMON_STATE.json`. A `signal_surface_router.py` maps surface names to build functions. Six tool definitions + handlers are added to `simple_tools.py`. `heartbeat_runtime.py` is updated to check daemon_manager before each daemon call.

**Tech Stack:** Python 3.11+, existing FastAPI services, SQLite eventbus, JSON state file.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `apps/api/jarvis_api/services/daemon_manager.py` | Create | Registry, enable/disable/restart/set_interval, state persistence |
| `apps/api/jarvis_api/services/signal_surface_router.py` | Create | Name → build_function routing for all signal surfaces |
| `core/tools/simple_tools.py` | Modify | Add 6 tool definitions + handlers |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify | Check is_enabled + record_tick around each daemon call |
| `tests/test_daemon_manager.py` | Create | TDD for daemon_manager |
| `tests/test_daemon_tools.py` | Create | TDD for tool handlers |
| `tests/test_signal_surface_router.py` | Create | TDD for signal surface router |

---

## Task 1: daemon_manager — registry and state persistence

**Files:**
- Create: `apps/api/jarvis_api/services/daemon_manager.py`
- Create: `tests/test_daemon_manager.py`

- [ ] **Step 1: Write failing tests for registry and state**

Create `tests/test_daemon_manager.py`:

```python
"""Tests for daemon_manager — registry, state persistence, tick recording."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch


def test_registry_contains_all_daemons():
    from apps.api.jarvis_api.services import daemon_manager
    names = daemon_manager.get_daemon_names()
    expected = {
        "somatic", "surprise", "aesthetic_taste", "irony", "thought_stream",
        "thought_action_proposal", "conflict", "reflection_cycle", "curiosity",
        "meta_reflection", "experienced_time", "development_narrative",
        "absence", "creative_drift", "existential_wonder", "dream_insight",
        "code_aesthetic", "memory_decay", "user_model", "desire",
    }
    assert names == expected


def test_get_all_daemon_states_returns_correct_fields(tmp_path):
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "_STATE_FILE", tmp_path / "DAEMON_STATE.json"):
        states = daemon_manager.get_all_daemon_states()
    assert len(states) == 20
    for s in states:
        assert "name" in s
        assert "enabled" in s
        assert "default_cadence_minutes" in s
        assert "effective_cadence_minutes" in s
        assert "interval_minutes_override" in s
        assert "last_run_at" in s
        assert "hours_since_last_run" in s
        assert "last_result_summary" in s


def test_enable_disable_persists(tmp_path):
    from apps.api.jarvis_api.services import daemon_manager
    state_file = tmp_path / "DAEMON_STATE.json"
    with patch.object(daemon_manager, "_STATE_FILE", state_file):
        daemon_manager.set_daemon_enabled("curiosity", False)
        assert not daemon_manager.is_enabled("curiosity")
        daemon_manager.set_daemon_enabled("curiosity", True)
        assert daemon_manager.is_enabled("curiosity")
        data = json.loads(state_file.read_text())
        assert data["curiosity"]["enabled"] is True


def test_record_daemon_tick_updates_state(tmp_path):
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "_STATE_FILE", tmp_path / "DAEMON_STATE.json"):
        daemon_manager.record_daemon_tick("curiosity", {"generated": True, "curiosity": "why?"})
        states = daemon_manager.get_all_daemon_states()
        c = next(s for s in states if s["name"] == "curiosity")
        assert c["last_run_at"] != ""
        assert c["hours_since_last_run"] is not None
        assert "generated: True" in c["last_result_summary"]


def test_unknown_daemon_raises(tmp_path):
    import pytest
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "_STATE_FILE", tmp_path / "DAEMON_STATE.json"):
        with pytest.raises(ValueError, match="unknown daemon"):
            daemon_manager.set_daemon_enabled("nonexistent", True)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_manager.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError` or `ImportError` — `daemon_manager` doesn't exist yet.

- [ ] **Step 3: Implement daemon_manager core**

Create `apps/api/jarvis_api/services/daemon_manager.py`:

```python
"""Daemon Manager — registry, lifecycle control, and state persistence for all daemons.

Single source of truth for daemon enabled/disabled state, interval overrides,
and last-run tracking. Heartbeat runtime checks is_enabled() before each daemon call
and calls record_daemon_tick() after.

State persisted to DAEMON_STATE.json in the runtime workspace.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import JARVIS_HOME

_STATE_FILE = Path(JARVIS_HOME) / "workspaces" / "default" / "runtime" / "DAEMON_STATE.json"

# Registry: daemon name → module path, tick var to reset on restart, default cadence in minutes.
# cadence_unit: "minutes" or "hours"
_REGISTRY: dict[str, dict[str, Any]] = {
    "somatic": {
        "module": "apps.api.jarvis_api.services.somatic_daemon",
        "reset_var": "_heartbeat_count_since_gen",
        "reset_value": 999,
        "default_cadence_minutes": 3,
        "description": "LLM-generated first-person body/energy description",
    },
    "surprise": {
        "module": "apps.api.jarvis_api.services.surprise_daemon",
        "reset_var": "_heartbeats_since_surprise",
        "reset_value": 999,
        "default_cadence_minutes": 4,
        "description": "Detects divergence from baseline reaction patterns",
    },
    "aesthetic_taste": {
        "module": "apps.api.jarvis_api.services.aesthetic_taste_daemon",
        "reset_var": "_last_insight_at",
        "reset_value": None,
        "default_cadence_minutes": 7,
        "description": "Tracks style preferences and aesthetic tendencies",
    },
    "irony": {
        "module": "apps.api.jarvis_api.services.irony_daemon",
        "reset_var": "_observations_today",
        "reset_value": 0,
        "default_cadence_minutes": 30,
        "description": "Generates situational self-distance observations (max 1/day)",
    },
    "thought_stream": {
        "module": "apps.api.jarvis_api.services.thought_stream_daemon",
        "reset_var": "_last_fragment_at",
        "reset_value": None,
        "default_cadence_minutes": 2,
        "description": "Generates associative thought fragments",
    },
    "thought_action_proposal": {
        "module": "apps.api.jarvis_api.services.thought_action_proposal_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Converts thought fragments into action proposals",
    },
    "conflict": {
        "module": "apps.api.jarvis_api.services.conflict_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 8,
        "description": "Detects inner tensions between active states",
    },
    "reflection_cycle": {
        "module": "apps.api.jarvis_api.services.reflection_cycle_daemon",
        "reset_var": "_last_reflection_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "description": "Pure experiential awareness — non-instrumental reflection",
    },
    "curiosity": {
        "module": "apps.api.jarvis_api.services.curiosity_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Scans thought stream for gaps and generates curiosity signals",
    },
    "meta_reflection": {
        "module": "apps.api.jarvis_api.services.meta_reflection_daemon",
        "reset_var": "_last_meta_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "description": "Cross-signal pattern synthesis and meta-insights",
    },
    "experienced_time": {
        "module": "apps.api.jarvis_api.services.experienced_time_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Density-based felt duration — how time feels vs. clock time",
    },
    "development_narrative": {
        "module": "apps.api.jarvis_api.services.development_narrative_daemon",
        "reset_var": "_last_narrative_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "description": "Daily LLM-generated self-reflection on development",
    },
    "absence": {
        "module": "apps.api.jarvis_api.services.absence_daemon",
        "reset_var": "_last_generated_at",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "description": "Three-tier tracking of experiential absence quality",
    },
    "creative_drift": {
        "module": "apps.api.jarvis_api.services.creative_drift_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "description": "Spontaneous unexpected associations and ideas",
    },
    "existential_wonder": {
        "module": "apps.api.jarvis_api.services.existential_wonder_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "description": "Self-generated philosophical questions from self-observation",
    },
    "dream_insight": {
        "module": "apps.api.jarvis_api.services.dream_insight_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "description": "Persists dream articulation output as private brain records",
    },
    "code_aesthetic": {
        "module": "apps.api.jarvis_api.services.code_aesthetic_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 10080,
        "description": "Weekly codebase aesthetic reflection (7 days)",
    },
    "memory_decay": {
        "module": "apps.api.jarvis_api.services.memory_decay_daemon",
        "reset_var": "_last_decay_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "description": "Selective forgetting + re-discovery of signals",
    },
    "user_model": {
        "module": "apps.api.jarvis_api.services.user_model_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "description": "Theory of mind — models user preferences and patterns",
    },
    "desire": {
        "module": "apps.api.jarvis_api.services.desire_daemon",
        "reset_var": "_last_generated_at",
        "reset_value": None,
        "default_cadence_minutes": 8,
        "description": "Emergent appetites with intensity-based lifecycle",
    },
}


def get_daemon_names() -> set[str]:
    return set(_REGISTRY.keys())


def _load_state() -> dict[str, dict[str, Any]]:
    if not _STATE_FILE.exists():
        return {}
    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict[str, dict[str, Any]]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_daemon_state(name: str) -> dict[str, Any]:
    state = _load_state()
    return state.get(name, {})


def _set_daemon_state(name: str, updates: dict[str, Any]) -> None:
    state = _load_state()
    entry = state.get(name, {})
    entry.update(updates)
    state[name] = entry
    _save_state(state)


def _require_known(name: str) -> None:
    if name not in _REGISTRY:
        valid = sorted(_REGISTRY.keys())
        raise ValueError(f"unknown daemon '{name}'. Valid: {valid}")


def is_enabled(name: str) -> bool:
    """Return True if the named daemon should run. Unknown daemons return True (safe default)."""
    if name not in _REGISTRY:
        return True
    entry = _get_daemon_state(name)
    return bool(entry.get("enabled", True))


def set_daemon_enabled(name: str, enabled: bool) -> None:
    _require_known(name)
    _set_daemon_state(name, {"enabled": enabled})


def get_effective_cadence(name: str) -> int:
    """Return interval in minutes: override if set, else default."""
    entry = _get_daemon_state(name)
    override = entry.get("interval_minutes_override")
    if override is not None:
        return int(override)
    return int(_REGISTRY[name]["default_cadence_minutes"])


def record_daemon_tick(name: str, result: dict[str, Any]) -> None:
    """Record last_run_at and a summary of the tick result. Called by heartbeat_runtime."""
    if name not in _REGISTRY:
        return
    now = datetime.now(UTC).isoformat()
    summary = ", ".join(f"{k}: {v}" for k, v in list(result.items())[:3])
    _set_daemon_state(name, {"last_run_at": now, "last_result_summary": summary})


def _hours_since(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return max((datetime.now(UTC) - dt).total_seconds() / 3600.0, 0.0)
    except ValueError:
        return None


def get_all_daemon_states() -> list[dict[str, Any]]:
    """Return status for all 20 daemons."""
    file_state = _load_state()
    result = []
    for name, reg in _REGISTRY.items():
        entry = file_state.get(name, {})
        override = entry.get("interval_minutes_override")
        last_run = entry.get("last_run_at", "")
        result.append({
            "name": name,
            "enabled": bool(entry.get("enabled", True)),
            "description": reg["description"],
            "default_cadence_minutes": reg["default_cadence_minutes"],
            "interval_minutes_override": override,
            "effective_cadence_minutes": int(override) if override is not None else reg["default_cadence_minutes"],
            "last_run_at": last_run,
            "hours_since_last_run": _hours_since(last_run),
            "last_result_summary": entry.get("last_result_summary", ""),
        })
    return result
```

- [ ] **Step 4: Run tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_manager.py -v 2>&1 | tail -20
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/daemon_manager.py tests/test_daemon_manager.py
git commit -m "feat: daemon_manager — registry and state persistence"
```

---

## Task 2: daemon_manager — control_daemon (enable/disable/restart/set_interval)

**Files:**
- Modify: `apps/api/jarvis_api/services/daemon_manager.py`
- Modify: `tests/test_daemon_manager.py`

- [ ] **Step 1: Add failing tests for control_daemon**

Append to `tests/test_daemon_manager.py`:

```python
def test_set_interval_persists(tmp_path):
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "_STATE_FILE", tmp_path / "DAEMON_STATE.json"):
        daemon_manager.control_daemon("curiosity", "set_interval", interval_minutes=15)
        assert daemon_manager.get_effective_cadence("curiosity") == 15
        data = json.loads((tmp_path / "DAEMON_STATE.json").read_text())
        assert data["curiosity"]["interval_minutes_override"] == 15


def test_set_interval_below_one_raises(tmp_path):
    import pytest
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "_STATE_FILE", tmp_path / "DAEMON_STATE.json"):
        with pytest.raises(ValueError, match="interval_minutes must be"):
            daemon_manager.control_daemon("curiosity", "set_interval", interval_minutes=0)


def test_restart_clears_state_var(tmp_path):
    import importlib
    from apps.api.jarvis_api.services import daemon_manager
    from apps.api.jarvis_api.services import curiosity_daemon
    # Set a non-None value first
    curiosity_daemon._last_tick_at = datetime.now(UTC)
    with patch.object(daemon_manager, "_STATE_FILE", tmp_path / "DAEMON_STATE.json"):
        daemon_manager.control_daemon("curiosity", "restart")
    assert curiosity_daemon._last_tick_at is None


def test_unknown_daemon_control_raises(tmp_path):
    import pytest
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "_STATE_FILE", tmp_path / "DAEMON_STATE.json"):
        with pytest.raises(ValueError, match="unknown daemon"):
            daemon_manager.control_daemon("ghost_daemon", "enable")


def test_set_interval_requires_minutes_param(tmp_path):
    import pytest
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "_STATE_FILE", tmp_path / "DAEMON_STATE.json"):
        with pytest.raises(ValueError, match="interval_minutes required"):
            daemon_manager.control_daemon("curiosity", "set_interval")
```

Add import at top of the test file:
```python
from datetime import UTC, datetime
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_manager.py::test_set_interval_persists -v 2>&1 | tail -10
```

Expected: `AttributeError` — `control_daemon` doesn't exist yet.

- [ ] **Step 3: Add control_daemon to daemon_manager.py**

Append to `apps/api/jarvis_api/services/daemon_manager.py`:

```python
def control_daemon(
    name: str,
    action: str,
    *,
    interval_minutes: int | None = None,
) -> dict[str, Any]:
    """Control a daemon. Actions: enable, disable, restart, set_interval.

    Returns {"ok": True, "name": name, "action": action} on success.
    Raises ValueError on unknown daemon, invalid action, or bad params.
    """
    _require_known(name)

    if action == "enable":
        set_daemon_enabled(name, True)
    elif action == "disable":
        set_daemon_enabled(name, False)
    elif action == "restart":
        _restart_daemon(name)
    elif action == "set_interval":
        if interval_minutes is None:
            raise ValueError("interval_minutes required for set_interval action")
        if interval_minutes < 1:
            raise ValueError(f"interval_minutes must be >= 1, got {interval_minutes}")
        _set_daemon_state(name, {"interval_minutes_override": interval_minutes})
    else:
        raise ValueError(f"unknown action '{action}'. Valid: enable, disable, restart, set_interval")

    return {"ok": True, "name": name, "action": action}


def _restart_daemon(name: str) -> None:
    """Clear the module-level state variable so the daemon fires on next heartbeat tick."""
    reg = _REGISTRY[name]
    module_path = reg["module"]
    reset_var = reg["reset_var"]
    reset_value = reg["reset_value"]

    # Module may not be imported yet — that's fine, restart is a no-op then.
    module = sys.modules.get(module_path)
    if module is None:
        return

    if hasattr(module, reset_var):
        setattr(module, reset_var, reset_value)
```

- [ ] **Step 4: Run all daemon_manager tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_manager.py -v 2>&1 | tail -20
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/daemon_manager.py tests/test_daemon_manager.py
git commit -m "feat: daemon_manager — control_daemon (enable/disable/restart/set_interval)"
```

---

## Task 3: signal_surface_router

**Files:**
- Create: `apps/api/jarvis_api/services/signal_surface_router.py`
- Create: `tests/test_signal_surface_router.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_signal_surface_router.py`:

```python
"""Tests for signal_surface_router — name resolution and error handling."""
from __future__ import annotations


def test_all_registered_names_resolve_to_callables():
    from apps.api.jarvis_api.services.signal_surface_router import (
        get_surface_names,
        resolve_surface,
    )
    for name in get_surface_names():
        fn = resolve_surface(name)
        assert callable(fn), f"{name} did not resolve to a callable"


def test_unknown_name_returns_error_with_valid_list():
    from apps.api.jarvis_api.services.signal_surface_router import read_surface
    result = read_surface("definitely_not_a_real_surface")
    assert "error" in result
    assert "valid" in result
    assert isinstance(result["valid"], list)
    assert len(result["valid"]) > 10


def test_known_surface_returns_dict():
    from apps.api.jarvis_api.services.signal_surface_router import read_surface
    result = read_surface("autonomy_pressure")
    assert isinstance(result, dict)
    assert "error" not in result


def test_list_all_returns_all_surfaces():
    from apps.api.jarvis_api.services.signal_surface_router import (
        get_surface_names,
        list_all_surfaces,
    )
    result = list_all_surfaces()
    assert isinstance(result, dict)
    assert len(result) == len(get_surface_names())
    for name in get_surface_names():
        assert name in result
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_signal_surface_router.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError` — signal_surface_router doesn't exist.

- [ ] **Step 3: Implement signal_surface_router.py**

Create `apps/api/jarvis_api/services/signal_surface_router.py`:

```python
"""Signal Surface Router — maps surface names to build functions.

All surfaces are imported lazily to avoid circular imports and startup cost.
read_surface() is the primary entry point for tools.
"""
from __future__ import annotations

from typing import Any, Callable


def _build_router() -> dict[str, Callable[[], dict[str, Any]]]:
    """Build the name → function mapping. All imports are local to stay lazy."""
    from apps.api.jarvis_api.services.autonomy_pressure_signal_tracking import (
        build_runtime_autonomy_pressure_signal_surface,
    )
    from apps.api.jarvis_api.services.goal_signal_tracking import (
        build_runtime_goal_signal_surface,
    )
    from apps.api.jarvis_api.services.reflection_signal_tracking import (
        build_runtime_reflection_signal_surface,
    )
    from apps.api.jarvis_api.services.temporal_recurrence_signal_tracking import (
        build_runtime_temporal_recurrence_signal_surface,
    )
    from apps.api.jarvis_api.services.internal_opposition_signal_tracking import (
        build_runtime_internal_opposition_signal_surface,
    )
    from apps.api.jarvis_api.services.self_review_signal_tracking import (
        build_runtime_self_review_signal_surface,
    )
    from apps.api.jarvis_api.services.dream_hypothesis_signal_tracking import (
        build_runtime_dream_hypothesis_signal_surface,
    )
    from apps.api.jarvis_api.services.user_understanding_signal_tracking import (
        build_runtime_user_understanding_signal_surface,
    )
    from apps.api.jarvis_api.services.private_inner_note_signal_tracking import (
        build_runtime_private_inner_note_signal_surface,
    )
    from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
        build_runtime_private_initiative_tension_signal_surface,
    )
    from apps.api.jarvis_api.services.private_inner_interplay_signal_tracking import (
        build_runtime_private_inner_interplay_signal_surface,
    )
    from apps.api.jarvis_api.services.private_state_snapshot_tracking import (
        build_runtime_private_state_snapshot_surface,
    )
    from apps.api.jarvis_api.services.diary_synthesis_signal_tracking import (
        build_runtime_diary_synthesis_signal_surface,
    )
    from apps.api.jarvis_api.services.open_loop_signal_tracking import (
        build_runtime_open_loop_signal_surface,
    )
    from apps.api.jarvis_api.services.witness_signal_tracking import (
        build_runtime_witness_signal_surface,
    )
    from apps.api.jarvis_api.services.emergent_signal_tracking import (
        build_runtime_emergent_signal_surface,
    )
    from apps.api.jarvis_api.services.regulation_homeostasis_signal_tracking import (
        build_runtime_regulation_homeostasis_signal_surface,
    )
    from apps.api.jarvis_api.services.relation_state_signal_tracking import (
        build_runtime_relation_state_signal_surface,
    )
    from apps.api.jarvis_api.services.relation_continuity_signal_tracking import (
        build_runtime_relation_continuity_signal_surface,
    )
    from apps.api.jarvis_api.services.meaning_significance_signal_tracking import (
        build_runtime_meaning_significance_signal_surface,
    )
    from apps.api.jarvis_api.services.temperament_tendency_signal_tracking import (
        build_runtime_temperament_tendency_signal_surface,
    )
    from apps.api.jarvis_api.services.self_narrative_continuity_signal_tracking import (
        build_runtime_self_narrative_continuity_signal_surface,
    )
    from apps.api.jarvis_api.services.metabolism_state_signal_tracking import (
        build_runtime_metabolism_state_signal_surface,
    )
    from apps.api.jarvis_api.services.release_marker_signal_tracking import (
        build_runtime_release_marker_signal_surface,
    )
    from apps.api.jarvis_api.services.attachment_topology_signal_tracking import (
        build_runtime_attachment_topology_signal_surface,
    )
    from apps.api.jarvis_api.services.loyalty_gradient_signal_tracking import (
        build_runtime_loyalty_gradient_signal_surface,
    )
    from apps.api.jarvis_api.services.executive_contradiction_signal_tracking import (
        build_runtime_executive_contradiction_signal_surface,
    )
    from apps.api.jarvis_api.services.inner_visible_support_signal_tracking import (
        build_runtime_inner_visible_support_signal_surface,
    )
    from apps.api.jarvis_api.services.chronicle_consolidation_signal_tracking import (
        build_runtime_chronicle_consolidation_signal_surface,
    )
    from apps.api.jarvis_api.services.somatic_daemon import build_body_state_surface
    from apps.api.jarvis_api.services.surprise_daemon import build_surprise_surface
    from apps.api.jarvis_api.services.thought_action_proposal_daemon import (
        build_proposal_surface,
    )
    from apps.api.jarvis_api.services.thought_stream_daemon import (
        build_thought_stream_surface,
    )
    from apps.api.jarvis_api.services.aesthetic_taste_daemon import build_taste_surface
    from apps.api.jarvis_api.services.irony_daemon import build_irony_surface
    from apps.api.jarvis_api.services.absence_daemon import build_absence_surface
    from apps.api.jarvis_api.services.embodied_state import build_embodied_state_surface
    from apps.api.jarvis_api.services.affective_meta_state import (
        build_affective_meta_state_surface,
    )
    from apps.api.jarvis_api.services.epistemic_runtime_state import (
        build_epistemic_runtime_state_surface,
    )
    from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface
    from apps.api.jarvis_api.services.dream_articulation import (
        build_dream_articulation_surface,
    )
    from apps.api.jarvis_api.services.subagent_ecology import (
        build_subagent_ecology_surface,
    )
    from apps.api.jarvis_api.services.open_loop_closure_proposal_tracking import (
        build_runtime_open_loop_closure_proposal_surface,
    )
    from apps.api.jarvis_api.services.remembered_fact_signal_tracking import (
        build_runtime_remembered_fact_signal_surface,
    )

    return {
        # Signal tracking surfaces
        "autonomy_pressure": build_runtime_autonomy_pressure_signal_surface,
        "goal_signal": build_runtime_goal_signal_surface,
        "reflection_signal": build_runtime_reflection_signal_surface,
        "temporal_recurrence": build_runtime_temporal_recurrence_signal_surface,
        "internal_opposition": build_runtime_internal_opposition_signal_surface,
        "self_review_signal": build_runtime_self_review_signal_surface,
        "dream_hypothesis": build_runtime_dream_hypothesis_signal_surface,
        "user_understanding": build_runtime_user_understanding_signal_surface,
        "private_inner_note": build_runtime_private_inner_note_signal_surface,
        "private_initiative_tension": build_runtime_private_initiative_tension_signal_surface,
        "private_inner_interplay": build_runtime_private_inner_interplay_signal_surface,
        "private_state_snapshot": build_runtime_private_state_snapshot_surface,
        "diary_synthesis": build_runtime_diary_synthesis_signal_surface,
        "open_loop": build_runtime_open_loop_signal_surface,
        "witness": build_runtime_witness_signal_surface,
        "emergent": build_runtime_emergent_signal_surface,
        "regulation_homeostasis": build_runtime_regulation_homeostasis_signal_surface,
        "relation_state": build_runtime_relation_state_signal_surface,
        "relation_continuity": build_runtime_relation_continuity_signal_surface,
        "meaning_significance": build_runtime_meaning_significance_signal_surface,
        "temperament_tendency": build_runtime_temperament_tendency_signal_surface,
        "self_narrative_continuity": build_runtime_self_narrative_continuity_signal_surface,
        "metabolism_state": build_runtime_metabolism_state_signal_surface,
        "release_marker": build_runtime_release_marker_signal_surface,
        "attachment_topology": build_runtime_attachment_topology_signal_surface,
        "loyalty_gradient": build_runtime_loyalty_gradient_signal_surface,
        "executive_contradiction": build_runtime_executive_contradiction_signal_surface,
        "inner_visible_support": build_runtime_inner_visible_support_signal_surface,
        "chronicle_consolidation": build_runtime_chronicle_consolidation_signal_surface,
        "open_loop_closure_proposal": build_runtime_open_loop_closure_proposal_surface,
        "remembered_fact": build_runtime_remembered_fact_signal_surface,
        # Daemon state surfaces
        "body_state": build_body_state_surface,
        "surprise": build_surprise_surface,
        "thought_proposals": build_proposal_surface,
        "thought_stream": build_thought_stream_surface,
        "aesthetic_taste": build_taste_surface,
        "irony": build_irony_surface,
        "absence": build_absence_surface,
        # Runtime context surfaces
        "embodied_state": build_embodied_state_surface,
        "affective_meta_state": build_affective_meta_state_surface,
        "epistemic_state": build_epistemic_runtime_state_surface,
        "loop_runtime": build_loop_runtime_surface,
        "dream_articulation": build_dream_articulation_surface,
        "subagent_ecology": build_subagent_ecology_surface,
    }


_ROUTER: dict[str, Callable[[], dict[str, Any]]] | None = None


def _get_router() -> dict[str, Callable[[], dict[str, Any]]]:
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = _build_router()
    return _ROUTER


def get_surface_names() -> list[str]:
    return sorted(_get_router().keys())


def resolve_surface(name: str) -> Callable[[], dict[str, Any]] | None:
    return _get_router().get(name)


def read_surface(name: str) -> dict[str, Any]:
    """Read a named surface. Returns {"error": ..., "valid": [...]} for unknown names."""
    router = _get_router()
    fn = router.get(name)
    if fn is None:
        return {"error": f"unknown surface '{name}'", "valid": sorted(router.keys())}
    try:
        return fn()
    except Exception as exc:
        return {"error": str(exc), "surface": name}


def list_all_surfaces() -> dict[str, Any]:
    """Call all registered surfaces. Per-surface exceptions are caught and returned as errors."""
    router = _get_router()
    result: dict[str, Any] = {}
    for name, fn in router.items():
        try:
            result[name] = fn()
        except Exception as exc:
            result[name] = {"error": str(exc)}
    return result
```

- [ ] **Step 4: Verify all existing build function names exist**

Before running tests, check that all imported function names actually exist:

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -c "
from apps.api.jarvis_api.services.signal_surface_router import get_surface_names, list_all_surfaces
names = get_surface_names()
print(f'Registered surfaces: {len(names)}')
print(names[:5])
" 2>&1
```

Expected: prints a count and a list of names without import errors.

If any import fails, look up the correct function name in the relevant `*_tracking.py` file and fix the import in `signal_surface_router.py`.

- [ ] **Step 5: Run signal surface tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_signal_surface_router.py -v 2>&1 | tail -20
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/services/signal_surface_router.py tests/test_signal_surface_router.py
git commit -m "feat: signal_surface_router — name-to-build-function routing for all surfaces"
```

---

## Task 4: heartbeat_runtime — integrate daemon_manager

**Files:**
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`

No new test file — existing heartbeat logic is guarded by try/except in all daemon blocks. This task wraps each block with `is_enabled()` + `record_daemon_tick()`.

- [ ] **Step 1: Find the daemon call section in heartbeat_runtime.py**

The 20 daemon calls live roughly at lines 1667–1970. Each follows this pattern:
```python
try:
    from apps.api.jarvis_api.services.somatic_daemon import ...
    tick_somatic_daemon()
    ...
except Exception:
    pass
```

- [ ] **Step 2: Add daemon_manager import at top of heartbeat_runtime.py**

Find the existing imports block (around line 1–150) and add after `from core.eventbus.bus import event_bus`:

```python
from apps.api.jarvis_api.services import daemon_manager as _dm
```

- [ ] **Step 3: Wrap each daemon call with is_enabled + record_tick**

Apply this pattern to all 20 daemon try-blocks. Example transformation for somatic:

**Before:**
```python
    # Somatic phrase
    try:
        from apps.api.jarvis_api.services.somatic_daemon import (
            get_latest_somatic_phrase,
            tick_somatic_daemon,
        )
        tick_somatic_daemon()
        _somatic = get_latest_somatic_phrase()
        if _somatic:
            inputs_present.append(f"somatisk: {_somatic}")
    except Exception:
        pass
```

**After:**
```python
    # Somatic phrase
    if _dm.is_enabled("somatic"):
        try:
            from apps.api.jarvis_api.services.somatic_daemon import (
                get_latest_somatic_phrase,
                tick_somatic_daemon,
            )
            _somatic_result = tick_somatic_daemon()
            _dm.record_daemon_tick("somatic", _somatic_result or {})
            _somatic = get_latest_somatic_phrase()
            if _somatic:
                inputs_present.append(f"somatisk: {_somatic}")
        except Exception:
            pass
```

Apply the same wrapping to all remaining 19 daemon blocks:
- `surprise` → wrap with `_dm.is_enabled("surprise")`, record `tick_surprise_daemon(...)` result
- `aesthetic_taste` → `"aesthetic_taste"`, record `tick_taste_daemon()` result
- `irony` → `"irony"`, record `tick_irony_daemon()` result
- `thought_stream` → `"thought_stream"`, record `tick_thought_stream_daemon(...)` result
- `thought_action_proposal` → `"thought_action_proposal"`, record `tick_thought_action_proposal_daemon(...)` result
- `conflict` → `"conflict"`, record `tick_conflict_daemon(...)` result
- `reflection_cycle` → `"reflection_cycle"`, record `tick_reflection_cycle_daemon(...)` result
- `curiosity` → `"curiosity"`, record `tick_curiosity_daemon(...)` result
- `meta_reflection` → `"meta_reflection"`, record `tick_meta_reflection_daemon(...)` result
- `experienced_time` → `"experienced_time"`, record `tick_experienced_time_daemon(...)` result
- `development_narrative` → `"development_narrative"`, record `tick_development_narrative_daemon()` result
- `absence` → `"absence"`, record `tick_absence_daemon()` result
- `creative_drift` → `"creative_drift"`, record `tick_creative_drift_daemon(...)` result
- `existential_wonder` → `"existential_wonder"`, record `tick_existential_wonder_daemon(...)` result
- `dream_insight` → `"dream_insight"`, record `tick_dream_insight_daemon(...)` result
- `code_aesthetic` → `"code_aesthetic"`, record `tick_code_aesthetic_daemon()` result
- `memory_decay` → `"memory_decay"`, record `tick_memory_decay_daemon()` result
- `user_model` → `"user_model"`, record `tick_user_model_daemon([])` result
- `desire` → `"desire"`, record `tick_desire_daemon(...)` result

Note: for daemons where the tick function returns None (e.g. `code_aesthetic`), use `result or {}` when passing to record_daemon_tick.

- [ ] **Step 4: Verify syntax**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m compileall apps/api/jarvis_api/services/heartbeat_runtime.py 2>&1
```

Expected: `Compiling ... ok`

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/heartbeat_runtime.py
git commit -m "feat: heartbeat_runtime — check daemon_manager.is_enabled + record_tick per daemon"
```

---

## Task 5: tools — daemon_status and control_daemon

**Files:**
- Modify: `core/tools/simple_tools.py`
- Create: `tests/test_daemon_tools.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_daemon_tools.py`:

```python
"""Tests for daemon tool handlers in simple_tools."""
from __future__ import annotations

from unittest.mock import patch, MagicMock


def _call_handler(name: str, args: dict):
    """Find and call a tool handler by name."""
    from core.tools import simple_tools
    handler = simple_tools._TOOL_HANDLERS[name]
    return handler(args)


def test_daemon_status_returns_all_daemons():
    result = _call_handler("daemon_status", {})
    assert "daemons" in result
    assert len(result["daemons"]) == 20
    names = {d["name"] for d in result["daemons"]}
    assert "curiosity" in names
    assert "desire" in names


def test_control_daemon_enable():
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "control_daemon") as mock_ctrl:
        mock_ctrl.return_value = {"ok": True, "name": "curiosity", "action": "enable"}
        result = _call_handler("control_daemon", {"name": "curiosity", "action": "enable"})
    assert result["ok"] is True
    mock_ctrl.assert_called_once_with("curiosity", "enable", interval_minutes=None)


def test_control_daemon_unknown_returns_error():
    result = _call_handler("control_daemon", {"name": "ghost", "action": "enable"})
    assert "error" in result
    assert "valid" in result


def test_control_daemon_set_interval():
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "control_daemon") as mock_ctrl:
        mock_ctrl.return_value = {"ok": True, "name": "curiosity", "action": "set_interval"}
        result = _call_handler("control_daemon", {
            "name": "curiosity",
            "action": "set_interval",
            "interval_minutes": 20,
        })
    assert result["ok"] is True
    mock_ctrl.assert_called_once_with("curiosity", "set_interval", interval_minutes=20)
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_tools.py -v 2>&1 | tail -15
```

Expected: `AttributeError` — handlers not defined yet.

- [ ] **Step 3: Add daemon_status tool definition to TOOL_DEFINITIONS in simple_tools.py**

Find `TOOL_DEFINITIONS: list[dict[str, Any]] = [` in `core/tools/simple_tools.py` and add before the closing `]`:

```python
    {
        "type": "function",
        "function": {
            "name": "daemon_status",
            "description": (
                "List all 20 internal daemons with their current state: enabled/disabled, "
                "cadence (default and override), last_run_at, hours_since_last_run, and "
                "last_result_summary. Use this to see which daemons are running and when "
                "they last fired."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_daemon",
            "description": (
                "Control a specific daemon. Actions: 'enable' — turn it on; 'disable' — turn it off; "
                "'restart' — clear its cooldown so it fires on next heartbeat tick; "
                "'set_interval' — override its default cadence (requires interval_minutes). "
                "Use daemon_status to see daemon names."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Daemon name (e.g. 'curiosity', 'desire', 'somatic')",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["enable", "disable", "restart", "set_interval"],
                        "description": "Action to perform",
                    },
                    "interval_minutes": {
                        "type": "integer",
                        "description": "New cadence in minutes. Required for set_interval, ignored otherwise.",
                    },
                },
                "required": ["name", "action"],
            },
        },
    },
```

- [ ] **Step 4: Add handler functions in simple_tools.py**

Find the section with other `_handle_*` functions (search for `def _handle_read_mood` or similar). Add:

```python
def _exec_daemon_status(_args: dict[str, object]) -> dict[str, object]:
    from apps.api.jarvis_api.services.daemon_manager import get_all_daemon_states
    return {"daemons": get_all_daemon_states()}


def _exec_control_daemon(args: dict[str, object]) -> dict[str, object]:
    from apps.api.jarvis_api.services.daemon_manager import control_daemon, get_daemon_names
    name = str(args.get("name", ""))
    action = str(args.get("action", ""))
    interval_minutes = args.get("interval_minutes")
    if interval_minutes is not None:
        interval_minutes = int(interval_minutes)
    try:
        return control_daemon(name, action, interval_minutes=interval_minutes)
    except ValueError as exc:
        valid = sorted(get_daemon_names())
        return {"error": str(exc), "valid": valid}
```

- [ ] **Step 5: Wire handlers into the dispatch map**

Find the tool dispatch logic in `simple_tools.py` (search for `"daemon_status"` or the dispatch dict/if-chain). Add:

```python
"daemon_status": _exec_daemon_status,
"control_daemon": _exec_control_daemon,
```

If the dispatch is an if/elif chain rather than a dict, add:
```python
elif name == "daemon_status":
    return _handle_daemon_status(arguments)
elif name == "control_daemon":
    return _handle_control_daemon(arguments)
```

- [ ] **Step 6: Run tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_tools.py -v 2>&1 | tail -15
```

Expected: all 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add core/tools/simple_tools.py tests/test_daemon_tools.py
git commit -m "feat: tools — daemon_status and control_daemon"
```

---

## Task 6: tools — list_signal_surfaces and read_signal_surface

**Files:**
- Modify: `core/tools/simple_tools.py`
- Modify: `tests/test_daemon_tools.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_daemon_tools.py`:

```python
def test_list_signal_surfaces_returns_dict():
    result = _call_handler("list_signal_surfaces", {})
    assert isinstance(result, dict)
    assert "surfaces" in result
    assert len(result["surfaces"]) > 10


def test_read_signal_surface_known_name():
    result = _call_handler("read_signal_surface", {"name": "autonomy_pressure"})
    assert isinstance(result, dict)
    assert "error" not in result


def test_read_signal_surface_unknown_name():
    result = _call_handler("read_signal_surface", {"name": "not_real"})
    assert "error" in result
    assert "valid" in result
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_tools.py::test_list_signal_surfaces_returns_dict -v 2>&1 | tail -10
```

Expected: `AttributeError`.

- [ ] **Step 3: Add tool definitions to TOOL_DEFINITIONS in simple_tools.py**

```python
    {
        "type": "function",
        "function": {
            "name": "list_signal_surfaces",
            "description": (
                "Read a compact overview of all registered signal surfaces — mood signals, "
                "goal signals, relation signals, autonomy pressure, and more. "
                "Returns all surface names with their current key fields. "
                "Use read_signal_surface to get full detail on a specific surface."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_signal_surface",
            "description": (
                "Read the full current state of a specific named signal surface. "
                "Use list_signal_surfaces first to see available names. "
                "Returns the complete surface dict for the named surface."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Surface name (e.g. 'autonomy_pressure', 'relation_state', 'desire')",
                    },
                },
                "required": ["name"],
            },
        },
    },
```

- [ ] **Step 4: Add handler functions**

```python
def _exec_list_signal_surfaces(_args: dict[str, object]) -> dict[str, object]:
    from apps.api.jarvis_api.services.signal_surface_router import list_all_surfaces
    return {"surfaces": list_all_surfaces()}


def _exec_read_signal_surface(args: dict[str, object]) -> dict[str, object]:
    from apps.api.jarvis_api.services.signal_surface_router import read_surface
    name = str(args.get("name", ""))
    return read_surface(name)
```

- [ ] **Step 5: Wire into dispatch map**

```python
"list_signal_surfaces": _exec_list_signal_surfaces,
"read_signal_surface": _exec_read_signal_surface,
```

- [ ] **Step 6: Run tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_tools.py -v 2>&1 | tail -20
```

Expected: all 7 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add core/tools/simple_tools.py tests/test_daemon_tools.py
git commit -m "feat: tools — list_signal_surfaces and read_signal_surface"
```

---

## Task 7: tools — eventbus_recent

**Files:**
- Modify: `core/tools/simple_tools.py`
- Modify: `tests/test_daemon_tools.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_daemon_tools.py`:

```python
def test_eventbus_recent_returns_list():
    result = _call_handler("eventbus_recent", {})
    assert "events" in result
    assert isinstance(result["events"], list)


def test_eventbus_recent_respects_limit():
    from core.eventbus.bus import event_bus
    # Publish a few test events
    event_bus.publish("heartbeat.test", {"source": "test"})
    result = _call_handler("eventbus_recent", {"limit": 1})
    assert len(result["events"]) <= 1


def test_eventbus_recent_filters_by_kind():
    from core.eventbus.bus import event_bus
    event_bus.publish("heartbeat.test_filter", {"source": "filter_test"})
    result = _call_handler("eventbus_recent", {"kind": "heartbeat", "limit": 50})
    for event in result["events"]:
        assert event["kind"].startswith("heartbeat")
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_tools.py::test_eventbus_recent_returns_list -v 2>&1 | tail -10
```

Expected: `AttributeError`.

- [ ] **Step 3: Add tool definition**

```python
    {
        "type": "function",
        "function": {
            "name": "eventbus_recent",
            "description": (
                "Read recent events from your internal eventbus. Optionally filter by event family "
                "(kind prefix). Event families include: heartbeat, tool, channel, memory, cost, "
                "approvals, council, self-review, goal_signal, dream_hypothesis_signal, and more. "
                "Default limit is 20, max is 100."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "description": "Filter by event family prefix (e.g. 'heartbeat', 'tool', 'memory')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of events to return (default: 20, max: 100)",
                    },
                },
                "required": [],
            },
        },
    },
```

- [ ] **Step 4: Add handler function**

```python
def _exec_eventbus_recent(args: dict[str, object]) -> dict[str, object]:
    from core.eventbus.bus import event_bus
    raw_limit = args.get("limit", 20)
    limit = min(int(raw_limit), 100)
    kind_filter = str(args.get("kind", "")).strip()
    events = event_bus.recent(limit=100 if kind_filter else limit)
    if kind_filter:
        events = [e for e in events if str(e.get("kind", "")).startswith(kind_filter)]
        events = events[:limit]
    return {"events": events, "count": len(events)}
```

- [ ] **Step 5: Wire into dispatch**

```python
"eventbus_recent": _exec_eventbus_recent,
```

- [ ] **Step 6: Run tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_tools.py -v 2>&1 | tail -20
```

Expected: all 10 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add core/tools/simple_tools.py tests/test_daemon_tools.py
git commit -m "feat: tools — eventbus_recent"
```

---

## Task 8: tools — update_setting

**Files:**
- Modify: `core/tools/simple_tools.py`
- Modify: `tests/test_daemon_tools.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_daemon_tools.py`:

```python
def test_update_setting_non_sensitive_returns_old_and_new(tmp_path):
    import json
    import core.runtime.config as _cfg
    from unittest.mock import patch

    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"relevance_model_name": "llama3.1:8b"}))
    with patch.object(_cfg, "SETTINGS_FILE", settings_file):
        result = _call_handler("update_setting", {
            "key": "relevance_model_name",
            "value": "llama3.1:70b",
        })
    assert result["key"] == "relevance_model_name"
    assert result["old"] == "llama3.1:8b"
    assert result["new"] == "llama3.1:70b"


def test_update_setting_sensitive_key_triggers_approval():
    result = _call_handler("update_setting", {
        "key": "visible_auth_profile",
        "value": "new-profile",
    })
    assert result.get("requires_approval") is True
    assert "key" in result


def test_update_setting_unknown_key_returns_error():
    result = _call_handler("update_setting", {"key": "not_a_real_key", "value": "x"})
    assert "error" in result
    assert "valid_keys" in result
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_tools.py::test_update_setting_non_sensitive_returns_old_and_new -v 2>&1 | tail -10
```

Expected: `AttributeError`.

- [ ] **Step 3: Add tool definition**

```python
    {
        "type": "function",
        "function": {
            "name": "update_setting",
            "description": (
                "Update a runtime setting. Returns old and new values on success. "
                "Sensitive keys (auth profiles, credentials, approval policies) require "
                "explicit user approval before taking effect. "
                "Valid keys: app_name, environment, host, port, database_url, "
                "primary_model_lane, cheap_model_lane, visible_model_provider, "
                "visible_model_name, visible_auth_profile, heartbeat_model_provider, "
                "heartbeat_model_name, heartbeat_auth_profile, heartbeat_local_only, "
                "relevance_model_name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Setting key to update",
                    },
                    "value": {
                        "description": "New value (string, int, or bool depending on the setting)",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
```

- [ ] **Step 4: Add handler function**

```python
_SENSITIVE_SETTING_PATTERNS = [
    "auth_profile",
    "credential",
    "approval",
    "auth_",
]


def _is_sensitive_setting(key: str) -> bool:
    key_lower = key.lower()
    return any(pat in key_lower for pat in _SENSITIVE_SETTING_PATTERNS)


def _exec_update_setting(args: dict[str, object]) -> dict[str, object]:
    import json as _json
    import core.runtime.config as _cfg
    from core.runtime.settings import load_settings

    key = str(args.get("key", "")).strip()
    value = args.get("value")

    settings = load_settings()
    valid_keys = list(settings.to_dict().keys())

    if key not in valid_keys:
        return {"error": f"unknown setting '{key}'", "valid_keys": valid_keys}

    if _is_sensitive_setting(key):
        return {
            "requires_approval": True,
            "key": key,
            "requested_value": value,
            "message": (
                f"Setting '{key}' is sensitive (auth/credentials). "
                "Please confirm you want to update it."
            ),
        }

    old_value = settings.to_dict()[key]
    settings_file = _cfg.SETTINGS_FILE

    # Load raw JSON, apply update, write back
    if settings_file.exists():
        raw = _json.loads(settings_file.read_text(encoding="utf-8"))
    else:
        raw = settings.to_dict()

    raw[key] = value
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(_json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"key": key, "old": old_value, "new": value}
```

- [ ] **Step 5: Wire into dispatch**

```python
"update_setting": _exec_update_setting,
```

- [ ] **Step 6: Run all tool tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_tools.py -v 2>&1 | tail -25
```

Expected: all 13 tests PASS.

- [ ] **Step 7: Verify syntax on all changed files**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m compileall core/tools/simple_tools.py apps/api/jarvis_api/services/daemon_manager.py apps/api/jarvis_api/services/signal_surface_router.py 2>&1
```

Expected: all `ok`.

- [ ] **Step 8: Final commit**

```bash
git add core/tools/simple_tools.py tests/test_daemon_tools.py
git commit -m "feat: tools — update_setting with approval gating for sensitive keys"
```

---

## Verification

After all tasks are complete:

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_daemon_manager.py tests/test_signal_surface_router.py tests/test_daemon_tools.py -v 2>&1 | tail -30
```

Expected: all 27 tests PASS across the three new test files.
