# Autonomous Council Daemon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daemon that spontaneously triggers a council deliberation when composite signal scoring crosses a threshold, with cadence/cooldown gating and score-based composition.

**Architecture:** `autonomous_council_daemon.py` holds all scoring, gating, and topic-derivation logic. It calls `create_council_session_runtime` + `run_council_round` from `agent_runtime.py` and publishes to eventbus. Registered as daemon #21 in `daemon_manager.py` and wired into `heartbeat_runtime.py`.

**Tech Stack:** Python 3.11+, `execute_cheap_lane` for LLM topic derivation, existing signal surfaces via `read_surface()`, existing council runtime via `agent_runtime.py`.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `apps/api/jarvis_api/services/autonomous_council_daemon.py` | Create | Signal scoring, gating, topic derivation, council trigger |
| `apps/api/jarvis_api/services/daemon_manager.py` | Modify | Add daemon #21 to `_REGISTRY` |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify | Add daemon call after `desire` block |
| `apps/api/jarvis_api/services/signal_surface_router.py` | Modify | Register `autonomous_council` surface |
| `tests/test_autonomous_council_daemon.py` | Create | TDD tests |
| `tests/test_daemon_tools.py` | Modify | Update daemon count from 20 → 21 |

---

### Task 1: Signal scorer — failing tests

**Files:**
- Create: `tests/test_autonomous_council_daemon.py`

- [ ] **Step 1: Write failing tests for signal scorer**

```python
"""Tests for autonomous_council_daemon signal scoring."""
from __future__ import annotations

from unittest.mock import patch


def _score(surfaces: dict) -> float:
    from apps.api.jarvis_api.services.autonomous_council_daemon import compute_signal_score
    return compute_signal_score(surfaces)


def test_all_zero_surfaces_give_zero_score():
    surfaces = {
        "autonomy_pressure": {"summary": {"active_count": 0}},
        "open_loop": {"summary": {"open_count": 0}},
        "internal_opposition": {"active": False},
        "existential_wonder": {"latest_wonder": ""},
        "creative_drift": {"drift_count_today": 0},
        "desire": {"active_count": 0},
        "conflict": {"last_conflict": ""},
        "hours_since_last_council": None,
    }
    assert _score(surfaces) == 0.0


def test_all_max_surfaces_give_score_above_threshold():
    surfaces = {
        "autonomy_pressure": {"summary": {"active_count": 3}},
        "open_loop": {"summary": {"open_count": 5}},
        "internal_opposition": {"active": True},
        "existential_wonder": {"latest_wonder": "What am I?"},
        "creative_drift": {"drift_count_today": 3},
        "desire": {"active_count": 3},
        "conflict": {"last_conflict": "some conflict"},
        "hours_since_last_council": 48,
    }
    score = _score(surfaces)
    assert score >= 0.55


def test_time_signal_normalized_at_48h():
    surfaces = {
        "autonomy_pressure": {"summary": {"active_count": 0}},
        "open_loop": {"summary": {"open_count": 0}},
        "internal_opposition": {"active": False},
        "existential_wonder": {"latest_wonder": ""},
        "creative_drift": {"drift_count_today": 0},
        "desire": {"active_count": 0},
        "conflict": {"last_conflict": ""},
        "hours_since_last_council": 48,
    }
    score = _score(surfaces)
    # time weight is 0.10; 48h → normalized 1.0 → contributes exactly 0.10
    assert abs(score - 0.10) < 0.001


def test_score_clamped_at_1():
    surfaces = {
        "autonomy_pressure": {"summary": {"active_count": 999}},
        "open_loop": {"summary": {"open_count": 999}},
        "internal_opposition": {"active": True},
        "existential_wonder": {"latest_wonder": "x"},
        "creative_drift": {"drift_count_today": 999},
        "desire": {"active_count": 999},
        "conflict": {"last_conflict": "x"},
        "hours_since_last_council": 999,
    }
    assert _score(surfaces) <= 1.0
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_autonomous_council_daemon.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError` or `ImportError` for `autonomous_council_daemon`.

---

### Task 2: Signal scorer — implementation

**Files:**
- Create: `apps/api/jarvis_api/services/autonomous_council_daemon.py`

- [ ] **Step 1: Create the daemon module with `compute_signal_score`**

```python
"""Autonomous Council Daemon — spontaneous self-triggered deliberation.

Evaluates composite signal score each heartbeat. When score crosses threshold
AND cadence/cooldown gates pass, derives a topic via LLM and triggers a council.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus

_THRESHOLD = 0.55
_CADENCE_MINUTES = 30
_COOLDOWN_MINUTES = 20

_last_council_at: datetime | None = None
_last_concluded_at: datetime | None = None

_SIGNAL_WEIGHTS: dict[str, float] = {
    "autonomy_pressure": 0.20,
    "open_loop": 0.15,
    "internal_opposition": 0.15,
    "existential_wonder": 0.10,
    "creative_drift": 0.10,
    "desire": 0.10,
    "conflict": 0.10,
    "time_since_last_council": 0.10,
}


def compute_signal_score(surfaces: dict[str, Any]) -> float:
    """Compute weighted composite score from signal surface readings. Returns 0.0–1.0."""
    def _norm_autonomy(s: dict) -> float:
        count = int((s.get("summary") or {}).get("active_count") or 0)
        return min(count / 3.0, 1.0)

    def _norm_open_loop(s: dict) -> float:
        count = int((s.get("summary") or {}).get("open_count") or 0)
        return min(count / 5.0, 1.0)

    def _norm_bool(s: dict, key: str) -> float:
        return 1.0 if s.get(key) else 0.0

    def _norm_nonempty(s: dict, key: str) -> float:
        return 1.0 if str(s.get(key) or "") else 0.0

    def _norm_count(s: dict, key: str, max_val: float = 3.0) -> float:
        count = int(s.get(key) or 0)
        return min(count / max_val, 1.0)

    def _norm_hours(hours: float | None) -> float:
        if hours is None:
            return 0.0
        return min(hours / 48.0, 1.0)

    normalized: dict[str, float] = {
        "autonomy_pressure": _norm_autonomy(surfaces.get("autonomy_pressure") or {}),
        "open_loop": _norm_open_loop(surfaces.get("open_loop") or {}),
        "internal_opposition": _norm_bool(surfaces.get("internal_opposition") or {}, "active"),
        "existential_wonder": _norm_nonempty(surfaces.get("existential_wonder") or {}, "latest_wonder"),
        "creative_drift": _norm_count(surfaces.get("creative_drift") or {}, "drift_count_today"),
        "desire": _norm_count(surfaces.get("desire") or {}, "active_count"),
        "conflict": _norm_nonempty(surfaces.get("conflict") or {}, "last_conflict"),
        "time_since_last_council": _norm_hours(surfaces.get("hours_since_last_council")),
    }

    score = sum(_SIGNAL_WEIGHTS[k] * v for k, v in normalized.items())
    return min(score, 1.0)
```

- [ ] **Step 2: Run scorer tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_autonomous_council_daemon.py::test_all_zero_surfaces_give_zero_score tests/test_autonomous_council_daemon.py::test_all_max_surfaces_give_score_above_threshold tests/test_autonomous_council_daemon.py::test_time_signal_normalized_at_48h tests/test_autonomous_council_daemon.py::test_score_clamped_at_1 -v
```
Expected: 4 PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/api/jarvis_api/services/autonomous_council_daemon.py tests/test_autonomous_council_daemon.py
git commit -m "feat: autonomous council daemon — signal scorer (TDD)"
```

---

### Task 3: Gating + topic derivation — tests

**Files:**
- Modify: `tests/test_autonomous_council_daemon.py`

- [ ] **Step 1: Add gating and topic tests**

```python
def test_cadence_gate_blocks_when_recent():
    from apps.api.jarvis_api.services import autonomous_council_daemon as acd
    from datetime import UTC, datetime
    acd._last_council_at = datetime.now(UTC)
    assert acd._cadence_gate_ok() is False
    acd._last_council_at = None  # reset


def test_cadence_gate_passes_when_none():
    from apps.api.jarvis_api.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    assert acd._cadence_gate_ok() is True


def test_cooldown_gate_blocks_when_recent():
    from apps.api.jarvis_api.services import autonomous_council_daemon as acd
    from datetime import UTC, datetime
    acd._last_concluded_at = datetime.now(UTC)
    assert acd._cooldown_gate_ok() is False
    acd._last_concluded_at = None  # reset


def test_derive_topic_calls_llm():
    from apps.api.jarvis_api.services.autonomous_council_daemon import derive_topic
    from unittest.mock import patch
    with patch(
        "apps.api.jarvis_api.services.autonomous_council_daemon._call_llm",
        return_value="What limits my autonomy?",
    ):
        topic = derive_topic(top_signals=["autonomy_pressure", "open_loop"])
    assert "autonomy" in topic.lower() or len(topic) > 0


def test_compose_members_full_council_at_high_score():
    from apps.api.jarvis_api.services.autonomous_council_daemon import compose_members
    members = compose_members(score=0.85, top_signals=["autonomy_pressure"])
    # Full council — all available roles present
    assert len(members) >= 4


def test_compose_members_partial_at_normal_score():
    from apps.api.jarvis_api.services.autonomous_council_daemon import compose_members
    members = compose_members(score=0.65, top_signals=["existential_wonder"])
    assert 3 <= len(members) <= 4
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_autonomous_council_daemon.py -k "gate or derive or compose" -v 2>&1 | head -30
```
Expected: FAIL — functions not defined.

---

### Task 4: Gating + topic derivation — implementation

**Files:**
- Modify: `apps/api/jarvis_api/services/autonomous_council_daemon.py`

- [ ] **Step 1: Add gating, topic derivation, and composition**

Append to `autonomous_council_daemon.py` after `compute_signal_score`:

```python
_ALL_COUNCIL_ROLES = ["planner", "critic", "researcher", "synthesizer", "filosof", "etiker"]

_SIGNAL_TO_ROLES: dict[str, list[str]] = {
    "autonomy_pressure": ["planner", "critic"],
    "open_loop": ["planner", "researcher"],
    "internal_opposition": ["critic", "filosof"],
    "conflict": ["critic", "etiker"],
    "existential_wonder": ["filosof", "synthesizer"],
    "creative_drift": ["filosof", "researcher"],
    "desire": ["planner", "etiker"],
    "time_since_last_council": ["synthesizer", "critic"],
}


def _cadence_gate_ok() -> bool:
    """True if at least _CADENCE_MINUTES have passed since last council start."""
    if _last_council_at is None:
        return True
    return (datetime.now(UTC) - _last_council_at) >= timedelta(minutes=_CADENCE_MINUTES)


def _cooldown_gate_ok() -> bool:
    """True if at least _COOLDOWN_MINUTES have passed since last council conclusion."""
    if _last_concluded_at is None:
        return True
    return (datetime.now(UTC) - _last_concluded_at) >= timedelta(minutes=_COOLDOWN_MINUTES)


def _call_llm(prompt: str) -> str:
    from apps.api.jarvis_api.services.non_visible_lane_execution import execute_cheap_lane
    result = execute_cheap_lane(message=prompt)
    return str(result.get("text") or "").strip()


def derive_topic(top_signals: list[str]) -> str:
    """Ask cheap LLM to generate a council topic from the top triggering signals."""
    signals_text = ", ".join(top_signals)
    prompt = (
        f"Jarvis' stærkeste interne signaler lige nu: {signals_text}\n\n"
        "Formulér ét konkret spørgsmål som Jarvis' råd bør deliberere om. "
        "Maksimalt én sætning. Svar kun med spørgsmålet."
    )
    topic = _call_llm(prompt)
    return topic or f"Hvad betyder {top_signals[0]} for mig lige nu?"


def compose_members(score: float, top_signals: list[str]) -> list[str]:
    """Return list of role names for this council.
    
    score >= 0.80 → all roles; otherwise 3–4 most relevant roles.
    Synthesizer always included.
    """
    if score >= 0.80:
        return list(_ALL_COUNCIL_ROLES)
    # Collect roles relevant to top signals
    seen: list[str] = []
    for sig in top_signals:
        for role in _SIGNAL_TO_ROLES.get(sig, []):
            if role not in seen:
                seen.append(role)
    # Ensure synthesizer always present
    if "synthesizer" not in seen:
        seen.append("synthesizer")
    return seen[:4]  # max 4 for non-high-score councils
```

- [ ] **Step 2: Run gating tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_autonomous_council_daemon.py -k "gate or derive or compose" -v
```
Expected: All PASS (derive uses mock so no LLM call needed).

- [ ] **Step 3: Commit**

```bash
git add apps/api/jarvis_api/services/autonomous_council_daemon.py tests/test_autonomous_council_daemon.py
git commit -m "feat: autonomous council daemon — gating, topic derivation, composition"
```

---

### Task 5: Main tick function — tests

**Files:**
- Modify: `tests/test_autonomous_council_daemon.py`

- [ ] **Step 1: Add tick tests**

```python
def test_tick_skips_when_score_below_threshold():
    from apps.api.jarvis_api.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    acd._last_concluded_at = None
    result = acd.tick_autonomous_council_daemon(score_override=0.30)
    assert result["triggered"] is False
    assert result["reason"] == "score_below_threshold"


def test_tick_skips_when_cadence_blocked():
    from apps.api.jarvis_api.services import autonomous_council_daemon as acd
    from datetime import UTC, datetime
    acd._last_council_at = datetime.now(UTC)
    result = acd.tick_autonomous_council_daemon(score_override=0.80)
    assert result["triggered"] is False
    assert result["reason"] == "cadence_gate"
    acd._last_council_at = None


def test_tick_skips_when_cooldown_blocked():
    from apps.api.jarvis_api.services import autonomous_council_daemon as acd
    from datetime import UTC, datetime
    acd._last_concluded_at = datetime.now(UTC)
    result = acd.tick_autonomous_council_daemon(score_override=0.80)
    assert result["triggered"] is False
    assert result["reason"] == "cooldown_gate"
    acd._last_concluded_at = None


def test_tick_triggers_council_when_conditions_met():
    from apps.api.jarvis_api.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    acd._last_concluded_at = None
    with (
        patch("apps.api.jarvis_api.services.autonomous_council_daemon.derive_topic", return_value="Test topic"),
        patch("apps.api.jarvis_api.services.autonomous_council_daemon._run_autonomous_council", return_value={"council_id": "c-123", "conclusion": "test"}),
    ):
        result = acd.tick_autonomous_council_daemon(score_override=0.75)
    assert result["triggered"] is True
    assert result["council_id"] == "c-123"


def test_tick_publishes_eventbus_on_trigger():
    from apps.api.jarvis_api.services import autonomous_council_daemon as acd
    from core.eventbus.bus import event_bus
    acd._last_council_at = None
    acd._last_concluded_at = None
    received = []
    event_bus.subscribe("council.autonomous_triggered", lambda e: received.append(e))
    with (
        patch("apps.api.jarvis_api.services.autonomous_council_daemon.derive_topic", return_value="Test topic"),
        patch("apps.api.jarvis_api.services.autonomous_council_daemon._run_autonomous_council", return_value={"council_id": "c-xyz", "conclusion": "done"}),
    ):
        acd.tick_autonomous_council_daemon(score_override=0.75)
    assert len(received) > 0
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_autonomous_council_daemon.py -k "tick" -v 2>&1 | head -30
```
Expected: FAIL — `tick_autonomous_council_daemon` not defined.

---

### Task 6: Main tick function — implementation

**Files:**
- Modify: `apps/api/jarvis_api/services/autonomous_council_daemon.py`

- [ ] **Step 1: Add tick and council runner**

Append to `autonomous_council_daemon.py`:

```python
def tick_autonomous_council_daemon(
    *,
    score_override: float | None = None,
) -> dict[str, Any]:
    """Evaluate signals and trigger council if warranted.
    
    score_override: inject a score directly (used in tests to bypass surface reads).
    """
    global _last_council_at, _last_concluded_at

    # Gate checks first (cheap)
    if not _cadence_gate_ok():
        return {"triggered": False, "reason": "cadence_gate"}
    if not _cooldown_gate_ok():
        return {"triggered": False, "reason": "cooldown_gate"}

    # Score evaluation
    if score_override is not None:
        score = score_override
        top_signals = ["autonomy_pressure", "open_loop"]  # default for override
    else:
        surfaces, top_signals = _read_signal_surfaces()
        score = compute_signal_score(surfaces)

    if score < _THRESHOLD:
        return {"triggered": False, "reason": "score_below_threshold", "score": score}

    # Trigger
    _last_council_at = datetime.now(UTC)
    topic = derive_topic(top_signals)
    members = compose_members(score, top_signals)

    event_bus.publish("council.autonomous_triggered", {
        "score": score,
        "topic": topic,
        "members": members,
        "top_signals": top_signals,
    })

    result = _run_autonomous_council(topic=topic, members=members)
    _last_concluded_at = datetime.now(UTC)

    event_bus.publish("council.autonomous_concluded", {
        "council_id": result.get("council_id", ""),
        "topic": topic,
        "conclusion": result.get("conclusion", ""),
    })

    if result.get("initiative"):
        event_bus.publish("council.initiative_proposal", result["initiative"])

    return {
        "triggered": True,
        "score": score,
        "topic": topic,
        "members": members,
        "council_id": result.get("council_id", ""),
    }


def _read_signal_surfaces() -> tuple[dict[str, Any], list[str]]:
    """Read all signal surfaces and return (surfaces_dict, top_2_signal_names)."""
    from apps.api.jarvis_api.services.signal_surface_router import read_surface
    from apps.api.jarvis_api.services import daemon_manager as _dm

    surfaces: dict[str, Any] = {}
    surfaces["autonomy_pressure"] = read_surface("autonomy_pressure")
    surfaces["open_loop"] = read_surface("open_loop")
    surfaces["internal_opposition"] = read_surface("internal_opposition")
    surfaces["existential_wonder"] = read_surface("existential_wonder")
    surfaces["creative_drift"] = read_surface("creative_drift")
    surfaces["desire"] = read_surface("desire")
    surfaces["conflict"] = read_surface("conflict")

    # Time since last council from daemon state
    state_entry = _dm._get_daemon_state("autonomous_council")
    last_run = state_entry.get("last_run_at") or ""
    hours_since: float | None = _dm._hours_since(last_run)
    surfaces["hours_since_last_council"] = hours_since

    # Compute individual contributions to find top 2 signals
    def _norm_autonomy(s: dict) -> float:
        return min(int((s.get("summary") or {}).get("active_count") or 0) / 3.0, 1.0)
    def _norm_open(s: dict) -> float:
        return min(int((s.get("summary") or {}).get("open_count") or 0) / 5.0, 1.0)

    contributions = {
        "autonomy_pressure": _SIGNAL_WEIGHTS["autonomy_pressure"] * _norm_autonomy(surfaces["autonomy_pressure"]),
        "open_loop": _SIGNAL_WEIGHTS["open_loop"] * _norm_open(surfaces["open_loop"]),
        "internal_opposition": _SIGNAL_WEIGHTS["internal_opposition"] * (1.0 if surfaces["internal_opposition"].get("active") else 0.0),
        "existential_wonder": _SIGNAL_WEIGHTS["existential_wonder"] * (1.0 if surfaces["existential_wonder"].get("latest_wonder") else 0.0),
        "creative_drift": _SIGNAL_WEIGHTS["creative_drift"] * min(int(surfaces["creative_drift"].get("drift_count_today") or 0) / 3.0, 1.0),
        "desire": _SIGNAL_WEIGHTS["desire"] * min(int(surfaces["desire"].get("active_count") or 0) / 3.0, 1.0),
        "conflict": _SIGNAL_WEIGHTS["conflict"] * (1.0 if surfaces["conflict"].get("last_conflict") else 0.0),
        "time_since_last_council": _SIGNAL_WEIGHTS["time_since_last_council"] * min((hours_since or 0.0) / 48.0, 1.0),
    }
    top_signals = sorted(contributions, key=contributions.__getitem__, reverse=True)[:2]
    return surfaces, top_signals


def _run_autonomous_council(*, topic: str, members: list[str]) -> dict[str, Any]:
    """Create and run a council session. Returns dict with council_id and conclusion."""
    from apps.api.jarvis_api.services.agent_runtime import (
        create_council_session_runtime,
        run_council_round,
    )
    from uuid import uuid4
    council_id = f"auto-council-{uuid4().hex[:8]}"
    create_council_session_runtime(
        topic=topic,
        mode="council",
        council_id=council_id,
        member_models=None,
    )
    result = run_council_round(council_id)
    conclusion = str((result or {}).get("summary") or "")
    return {"council_id": council_id, "conclusion": conclusion}


def build_autonomous_council_surface() -> dict[str, Any]:
    return {
        "last_council_at": _last_council_at.isoformat() if _last_council_at else "",
        "last_concluded_at": _last_concluded_at.isoformat() if _last_concluded_at else "",
        "threshold": _THRESHOLD,
        "cadence_minutes": _CADENCE_MINUTES,
        "cooldown_minutes": _COOLDOWN_MINUTES,
    }
```

- [ ] **Step 2: Run all daemon tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_autonomous_council_daemon.py -v
```
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/api/jarvis_api/services/autonomous_council_daemon.py tests/test_autonomous_council_daemon.py
git commit -m "feat: autonomous council daemon — tick, council runner, surface"
```

---

### Task 7: Register in daemon_manager + heartbeat

**Files:**
- Modify: `apps/api/jarvis_api/services/daemon_manager.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`
- Modify: `apps/api/jarvis_api/services/signal_surface_router.py`
- Modify: `tests/test_daemon_tools.py`

- [ ] **Step 1: Add to daemon_manager `_REGISTRY`**

In `daemon_manager.py`, add after the `"desire"` entry (before the closing `}`):

```python
    "autonomous_council": {
        "module": "apps.api.jarvis_api.services.autonomous_council_daemon",
        "reset_var": "_last_council_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "description": "Spontaneous self-triggered council deliberation via signal scoring",
    },
```

Also update the docstring in `get_all_daemon_states`:
```python
def get_all_daemon_states() -> list[dict[str, Any]]:
    """Return status for all registered daemons."""
```

- [ ] **Step 2: Add to heartbeat_runtime.py**

After the `desire` daemon block (after line `_dm.record_daemon_tick("desire", _desire_result or {})`), add:

```python
    if _dm.is_enabled("autonomous_council"):
        try:
            from apps.api.jarvis_api.services.autonomous_council_daemon import tick_autonomous_council_daemon
            _ac_result = tick_autonomous_council_daemon()
            _dm.record_daemon_tick("autonomous_council", _ac_result or {})
        except Exception:
            pass
```

- [ ] **Step 3: Add to signal_surface_router.py**

In `_build_router()`, add import:
```python
    from apps.api.jarvis_api.services.autonomous_council_daemon import build_autonomous_council_surface
```

And in the return dict under `# Daemon state surfaces`:
```python
        "autonomous_council": build_autonomous_council_surface,
```

- [ ] **Step 4: Update daemon count test**

In `tests/test_daemon_tools.py`, update:
```python
    assert len(result["daemons"]) == 21
```

- [ ] **Step 5: Verify tests pass**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_daemon_tools.py tests/test_daemon_manager.py tests/test_autonomous_council_daemon.py -v
```
Expected: All PASS.

- [ ] **Step 6: Verify syntax**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m compileall apps/api/jarvis_api/services/autonomous_council_daemon.py apps/api/jarvis_api/services/daemon_manager.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/services/signal_surface_router.py -q
```
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add apps/api/jarvis_api/services/autonomous_council_daemon.py apps/api/jarvis_api/services/daemon_manager.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/services/signal_surface_router.py tests/test_daemon_tools.py
git commit -m "feat: Sub-projekt A — autonomous council daemon fully integrated"
```
