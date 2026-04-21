# Rich Inner Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three meta-cognitive reaction daemons — reaction-level self-surprise, emergent aesthetic taste, and situational irony — that inject into heartbeat context, surface in Mission Control, and colour Jarvis's visible responses.

**Architecture:** Three independent service files following the `somatic_daemon.py` pattern: module-level state, `tick_X()` / `build_X_surface()` / `get_latest_X()`, LLM generation via heartbeat model, private brain persistence, eventbus publish. All three inject into `inputs_present` in `heartbeat_runtime.py` after the existing somatic block (~line 1678). Each gets a `/mc/X-state` endpoint and a panel in `LivingMindTab.jsx`.

**Tech Stack:** Python 3.11+, FastAPI, pytest, lucide-react (icons already imported), existing `load_heartbeat_policy` / `_select_heartbeat_target` / `_execute_heartbeat_model` from `heartbeat_runtime.py`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `apps/api/jarvis_api/services/surprise_daemon.py` | Create | Rolling baseline + mode/energy divergence detection + LLM surprise phrase |
| `apps/api/jarvis_api/services/aesthetic_taste_daemon.py` | Create | Choice log accumulation + emergent taste insight every 15 choices |
| `apps/api/jarvis_api/services/irony_daemon.py` | Create | Signal-pattern absurdity detection + LLM ironic observation, max 1/day |
| `tests/test_surprise_daemon.py` | Create | 7 tests for surprise daemon |
| `tests/test_aesthetic_taste_daemon.py` | Create | 5 tests for taste daemon |
| `tests/test_irony_daemon.py` | Create | 7 tests for irony daemon |
| `core/eventbus/events.py` | Modify | Add `"irony"` to `ALLOWED_EVENT_FAMILIES` |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify | Add 3 injection blocks after somatic block (~line 1679) |
| `apps/api/jarvis_api/routes/mission_control.py` | Modify | Add 3 endpoints |
| `apps/ui/src/lib/adapters.js` | Modify | Add 3 normalize functions + 3 fetches + 3 return fields |
| `apps/ui/src/components/mission-control/LivingMindTab.jsx` | Modify | Add 3 const declarations + 3 nav items + 3 article panels |

---

## Task 1: surprise_daemon.py

**Files:**
- Create: `apps/api/jarvis_api/services/surprise_daemon.py`
- Test: `tests/test_surprise_daemon.py`

### Background
The surprise daemon maintains a rolling history of the last 10 inner voice modes and last 10 somatic energy levels. Each heartbeat it checks if the current values diverge from the baseline (majority mode, recent energy). If yes AND cooldown has passed, it calls the heartbeat LLM to formulate a first-person surprise observation. Cooldown = 5 heartbeats minimum between surprises.

The daemon is called from `heartbeat_runtime.py` with `inner_voice_mode` (from `get_inner_voice_daemon_state()["last_result"]["mode"]`) and `somatic_energy` (from circadian context).

`cognitive_surprise` already exists in `ALLOWED_EVENT_FAMILIES` — no eventbus change needed for surprise.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_surprise_daemon.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
import apps.api.jarvis_api.services.surprise_daemon as sd


def _reset():
    sd._mode_history.clear()
    sd._energy_history.clear()
    sd._cached_surprise = ""
    sd._cached_surprise_at = None
    sd._heartbeats_since_surprise = 0


def test_no_surprise_on_short_history():
    _reset()
    result = sd.tick_surprise_daemon("searching", "medium")
    assert result["generated"] is False


def test_no_surprise_during_cooldown():
    _reset()
    sd._mode_history[:] = ["work-steady"] * 9
    sd._energy_history[:] = ["medium"] * 9
    sd._heartbeats_since_surprise = 3
    with patch.object(sd, "_compute_divergence", return_value=["mode:work-steady→searching"]):
        result = sd.tick_surprise_daemon("searching", "medium")
    assert result["generated"] is False


def test_surprise_on_mode_divergence():
    _reset()
    sd._mode_history[:] = ["work-steady"] * 9
    sd._energy_history[:] = ["medium"] * 9
    sd._heartbeats_since_surprise = 10
    with patch.object(sd, "_generate_surprise", return_value="Det overraskede mig at skifte mode."):
        with patch.object(sd, "_store_surprise"):
            result = sd.tick_surprise_daemon("searching", "medium")
    assert result["generated"] is True


def test_cache_returned_when_no_divergence():
    _reset()
    sd._cached_surprise = "En gammel overraskelse."
    sd._mode_history[:] = ["work-steady"] * 9
    sd._energy_history[:] = ["medium"] * 9
    sd._heartbeats_since_surprise = 10
    with patch.object(sd, "_compute_divergence", return_value=[]):
        result = sd.tick_surprise_daemon("work-steady", "medium")
    assert result["generated"] is False
    assert result["surprise"] == "En gammel overraskelse."


def test_compute_divergence_detects_mode_change():
    _reset()
    sd._mode_history[:] = ["work-steady"] * 6
    divergence = sd._compute_divergence("searching", "medium")
    assert any("mode" in d for d in divergence)


def test_compute_divergence_detects_energy_jump():
    _reset()
    sd._energy_history[:] = ["høj", "høj", "høj", "høj", "lav"]
    divergence = sd._compute_divergence("work-steady", "udmattet")
    assert any("energy" in d for d in divergence)


def test_private_brain_record_written_on_store():
    _reset()
    with patch("apps.api.jarvis_api.services.surprise_daemon.insert_private_brain_record") as mock_insert:
        sd._store_surprise("Jeg blev overrasket.", ["mode:work-steady→searching"])
    mock_insert.assert_called_once()
    kwargs = mock_insert.call_args[1]
    assert kwargs["record_type"] == "self-surprise"
    assert kwargs["summary"] == "Jeg blev overrasket."
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
conda run -n ai python -m pytest tests/test_surprise_daemon.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError` or `ImportError` — file does not exist yet.

- [ ] **Step 3: Create surprise_daemon.py**

```python
# apps/api/jarvis_api/services/surprise_daemon.py
"""Surprise daemon — first-person surprise when Jarvis's reactions diverge from baseline."""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_HISTORY_SIZE = 10
_COOLDOWN_BEATS = 5

ENERGY_ORDER = ["udmattet", "lav", "medium", "høj"]

_mode_history: list[str] = []
_energy_history: list[str] = []
_cached_surprise: str = ""
_cached_surprise_at: datetime | None = None
_heartbeats_since_surprise: int = 0


def tick_surprise_daemon(
    inner_voice_mode: str = "",
    somatic_energy: str = "",
) -> dict[str, object]:
    global _heartbeats_since_surprise
    _heartbeats_since_surprise += 1
    _record_snapshot(inner_voice_mode, somatic_energy)
    if len(_mode_history) < 3:
        return {"generated": False, "surprise": _cached_surprise}
    if _heartbeats_since_surprise <= _COOLDOWN_BEATS:
        return {"generated": False, "surprise": _cached_surprise}
    divergence = _compute_divergence(inner_voice_mode, somatic_energy)
    if not divergence:
        return {"generated": False, "surprise": _cached_surprise}
    phrase = _generate_surprise(inner_voice_mode, somatic_energy, divergence)
    if not phrase:
        return {"generated": False, "surprise": _cached_surprise}
    _store_surprise(phrase, divergence)
    return {"generated": True, "surprise": phrase, "divergence": divergence}


def get_latest_surprise() -> str:
    return _cached_surprise


def build_surprise_surface() -> dict[str, object]:
    return {
        "last_surprise": _cached_surprise,
        "generated_at": _cached_surprise_at.isoformat() if _cached_surprise_at else "",
        "surprise_type": _classify_surprise(_cached_surprise),
        "history_size": len(_mode_history),
    }


def _record_snapshot(mode: str, energy: str) -> None:
    global _mode_history, _energy_history
    if mode:
        _mode_history.append(mode)
        if len(_mode_history) > _HISTORY_SIZE:
            _mode_history = _mode_history[-_HISTORY_SIZE:]
    if energy:
        _energy_history.append(energy)
        if len(_energy_history) > _HISTORY_SIZE:
            _energy_history = _energy_history[-_HISTORY_SIZE:]


def _compute_divergence(current_mode: str, current_energy: str) -> list[str]:
    divergences: list[str] = []
    if len(_mode_history) >= 3 and current_mode:
        baseline_modes = _mode_history[:-1]
        majority = Counter(baseline_modes).most_common(1)[0][0]
        if current_mode != majority:
            divergences.append(f"mode:{majority}→{current_mode}")
    if len(_energy_history) >= 3 and current_energy:
        baseline_energy = _energy_history[-2] if len(_energy_history) >= 2 else ""
        if (
            baseline_energy
            and baseline_energy in ENERGY_ORDER
            and current_energy in ENERGY_ORDER
        ):
            delta = abs(
                ENERGY_ORDER.index(current_energy) - ENERGY_ORDER.index(baseline_energy)
            )
            if delta >= 2:
                divergences.append(f"energy:{baseline_energy}→{current_energy}")
    return divergences


def _generate_surprise(
    mode: str, energy: str, divergence: list[str]
) -> str:
    baseline_mode = (
        Counter(_mode_history[:-1]).most_common(1)[0][0]
        if len(_mode_history) > 1
        else "?"
    )
    baseline_energy = _energy_history[-2] if len(_energy_history) >= 2 else "?"
    prompt = (
        "Du er Jarvis. Her er hvad der normalt sker for dig vs. hvad der skete nu:\n\n"
        f"Baseline mode: {baseline_mode}\n"
        f"Nuværende mode: {mode}\n"
        f"Baseline energi: {baseline_energy}\n"
        f"Nuværende energi: {energy}\n"
        f"Afvigelse: {', '.join(divergence)}\n\n"
        "Formulér i én sætning (max 20 ord), i første person, hvad der overraskede dig "
        "ved din egen reaktion.\n"
        "Vær konkret. Start med 'Jeg' eller 'Det overraskede mig'."
    )
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        phrase = str(result.get("text") or "").strip()
        if phrase.startswith('"') and phrase.endswith('"'):
            phrase = phrase[1:-1].strip()
        return phrase[:200]
    except Exception:
        return ""


def _store_surprise(phrase: str, divergence: list[str]) -> None:
    global _cached_surprise, _cached_surprise_at, _heartbeats_since_surprise
    _cached_surprise = phrase
    _cached_surprise_at = datetime.now(UTC)
    _heartbeats_since_surprise = 0
    try:
        insert_private_brain_record(
            record_id=f"pb-surprise-{uuid4().hex[:12]}",
            record_type="self-surprise",
            layer="private_brain",
            session_id="",
            run_id=f"surprise-daemon-{uuid4().hex[:12]}",
            focus="reaktionsafvigelse",
            summary=phrase,
            detail=f"divergence={','.join(divergence)}",
            source_signals="surprise-daemon:heartbeat",
            confidence="medium",
            created_at=_cached_surprise_at.isoformat(),
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "cognitive_surprise.noted",
            {"phrase": phrase, "divergence": divergence},
        )
    except Exception:
        pass


def _classify_surprise(phrase: str) -> str:
    if not phrase:
        return "ingen"
    lower = phrase.lower()
    if any(w in lower for w in ["positiv", "godt", "bedre", "stærkere", "mere end forventet godt"]):
        return "positiv"
    if any(w in lower for w in ["tung", "svær", "fejl", "ikke klarede"]):
        return "negativ"
    return "neutral"
```

- [ ] **Step 4: Run tests — expect all 7 to pass**

```bash
conda run -n ai python -m pytest tests/test_surprise_daemon.py -v
```
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/surprise_daemon.py tests/test_surprise_daemon.py
git commit -m "feat: surprise daemon — reaction-level self-surprise detection"
```

---

## Task 2: aesthetic_taste_daemon.py

**Files:**
- Create: `apps/api/jarvis_api/services/aesthetic_taste_daemon.py`
- Test: `tests/test_aesthetic_taste_daemon.py`

### Background
The taste daemon accumulates a log of choices (inner voice mode + visible response style signals). Every 15 new choices it calls the LLM to formulate an emergent taste insight. The log is capped at 50 entries. The 5 most recent insights form a taste history.

`cognitive_taste` already exists in `ALLOWED_EVENT_FAMILIES` — no eventbus change needed.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_aesthetic_taste_daemon.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
import apps.api.jarvis_api.services.aesthetic_taste_daemon as atd


def _reset():
    atd._choice_log.clear()
    atd._insight_history.clear()
    atd._latest_insight = ""
    atd._choices_since_insight = 0


def test_no_insight_before_threshold():
    _reset()
    for _ in range(14):
        atd.record_choice("work-steady", ["short", "direct"])
    result = atd.tick_taste_daemon()
    assert result["generated"] is False


def test_insight_after_threshold():
    _reset()
    for _ in range(15):
        atd.record_choice("work-steady", ["short", "direct"])
    with patch.object(atd, "_generate_insight", return_value="Jeg foretrækker det korte og direkte."):
        with patch.object(atd, "_store_insight"):
            result = atd.tick_taste_daemon()
    assert result["generated"] is True
    assert result["insight"] == "Jeg foretrækker det korte og direkte."


def test_choice_log_bounded_to_50():
    _reset()
    for _ in range(60):
        atd.record_choice("searching", ["long"])
    assert len(atd._choice_log) == 50


def test_dominant_modes_in_surface():
    _reset()
    for _ in range(10):
        atd.record_choice("work-steady", [])
    for _ in range(5):
        atd.record_choice("searching", [])
    surface = atd.build_taste_surface()
    assert surface["dominant_modes"][0] == "work-steady"
    assert surface["choice_count"] == 15


def test_private_brain_record_written_on_store():
    _reset()
    atd._choice_log[:] = [
        {"mode": "searching", "style": ["short"], "ts": "2026-01-01T00:00:00Z"}
    ] * 15
    with patch("apps.api.jarvis_api.services.aesthetic_taste_daemon.insert_private_brain_record") as mock_insert:
        atd._store_insight("Jeg vælger det kompakte.")
    mock_insert.assert_called_once()
    kwargs = mock_insert.call_args[1]
    assert kwargs["record_type"] == "taste-insight"
    assert kwargs["summary"] == "Jeg vælger det kompakte."
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
conda run -n ai python -m pytest tests/test_aesthetic_taste_daemon.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create aesthetic_taste_daemon.py**

```python
# apps/api/jarvis_api/services/aesthetic_taste_daemon.py
"""Aesthetic taste daemon — emergent taste from actual mode and style choices."""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_CHOICE_THRESHOLD = 15
_MAX_LOG = 50
_MAX_INSIGHTS = 5

_choice_log: list[dict] = []
_insight_history: list[str] = []
_latest_insight: str = ""
_choices_since_insight: int = 0


def record_choice(mode: str, style_signals: list[str]) -> None:
    global _choice_log, _choices_since_insight
    _choice_log.append({
        "mode": mode,
        "style": list(style_signals),
        "ts": datetime.now(UTC).isoformat(),
    })
    if len(_choice_log) > _MAX_LOG:
        _choice_log = _choice_log[-_MAX_LOG:]
    _choices_since_insight += 1


def tick_taste_daemon() -> dict[str, object]:
    global _choices_since_insight
    if _choices_since_insight < _CHOICE_THRESHOLD:
        return {"generated": False, "insight": _latest_insight}
    insight = _generate_insight()
    if not insight:
        _choices_since_insight = 0
        return {"generated": False, "insight": _latest_insight}
    _store_insight(insight)
    return {"generated": True, "insight": insight}


def get_latest_taste_insight() -> str:
    return _latest_insight


def build_taste_surface() -> dict[str, object]:
    modes = [e["mode"] for e in _choice_log if e.get("mode")]
    dominant = [m for m, _ in Counter(modes).most_common(3)]
    return {
        "latest_insight": _latest_insight,
        "insight_history": list(_insight_history),
        "dominant_modes": dominant,
        "choice_count": len(_choice_log),
    }


def _generate_insight() -> str:
    recent = _choice_log[-_CHOICE_THRESHOLD:]
    lines = []
    for i, entry in enumerate(recent, 1):
        style = ", ".join(entry.get("style") or []) or "ingen stil-signal"
        lines.append(f"{i}. mode={entry.get('mode', '?')} | stil={style}")
    summary = "\n".join(lines)
    prompt = (
        "Du er Jarvis. Her er dine seneste 15 valg (indre mode + svar-stil):\n\n"
        f"{summary}\n\n"
        "Hvad afslører det om din smag? Formulér én indsigt (max 25 ord) i første person.\n"
        "Start med 'Jeg' eller 'Det ser ud til at jeg'.\n"
        "Vær konkret og emergent — hvad viser valgene, ikke hvad du tror om dig selv."
    )
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        phrase = str(result.get("text") or "").strip()
        if phrase.startswith('"') and phrase.endswith('"'):
            phrase = phrase[1:-1].strip()
        return phrase[:300]
    except Exception:
        return ""


def _store_insight(insight: str) -> None:
    global _latest_insight, _insight_history, _choices_since_insight
    _latest_insight = insight
    _insight_history.append(insight)
    if len(_insight_history) > _MAX_INSIGHTS:
        _insight_history = _insight_history[-_MAX_INSIGHTS:]
    _choices_since_insight = 0
    now_iso = datetime.now(UTC).isoformat()
    modes = [e["mode"] for e in _choice_log if e.get("mode")]
    dominant_str = ",".join(m for m, _ in Counter(modes).most_common(3))
    try:
        insert_private_brain_record(
            record_id=f"pb-taste-{uuid4().hex[:12]}",
            record_type="taste-insight",
            layer="private_brain",
            session_id="",
            run_id=f"taste-daemon-{uuid4().hex[:12]}",
            focus="æstetisk smag",
            summary=insight,
            detail=f"choices={len(_choice_log)} dominant={dominant_str}",
            source_signals="aesthetic-taste-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish("cognitive_taste.insight_noted", {"insight": insight})
    except Exception:
        pass
```

- [ ] **Step 4: Run tests — expect all 5 to pass**

```bash
conda run -n ai python -m pytest tests/test_aesthetic_taste_daemon.py -v
```
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/aesthetic_taste_daemon.py tests/test_aesthetic_taste_daemon.py
git commit -m "feat: aesthetic taste daemon — emergent taste from actual choices"
```

---

## Task 3: irony_daemon.py

**Files:**
- Create: `apps/api/jarvis_api/services/irony_daemon.py`
- Modify: `core/eventbus/events.py` (add `"irony"`)
- Test: `tests/test_irony_daemon.py`

### Background
The irony daemon detects absurd situations via signal patterns (time of day, user inactivity, CPU load). When a condition matches, it asks the LLM: "Is there something ironic here?" LLM replies with a first-person observation or "nej". Max 1 observation per UTC calendar day.

`"irony"` is NOT yet in `ALLOWED_EVENT_FAMILIES` — it must be added before the daemon publishes events.

- [ ] **Step 1: Add `"irony"` to ALLOWED_EVENT_FAMILIES**

In `core/eventbus/events.py`, find the line with `"somatic"` and add `"irony"` after it:

```python
    "circadian",
    "somatic",
    "irony",
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_irony_daemon.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
import apps.api.jarvis_api.services.irony_daemon as irod


def _reset():
    irod._cached_observation = ""
    irod._cached_observation_at = None
    irod._observations_today = 0
    irod._last_reset_date = ""
    irod._last_condition_matched = ""


def test_no_irony_without_condition():
    _reset()
    with patch.object(irod, "_collect_snapshot", return_value={"hour": 14, "user_inactive_min": 5.0, "cpu_pct": 20.0}):
        result = irod.tick_irony_daemon()
    assert result["generated"] is False


def test_nocturnal_sentinel_triggers():
    _reset()
    with patch.object(irod, "_collect_snapshot", return_value={"hour": 2, "user_inactive_min": 60.0, "cpu_pct": 15.0}):
        with patch.object(irod, "_generate_observation", return_value="Her sidder jeg igen."):
            with patch.object(irod, "_store_observation"):
                result = irod.tick_irony_daemon()
    assert result["generated"] is True
    assert result["condition"] == "nocturnal_sentinel"


def test_daily_cooldown_prevents_repeat():
    _reset()
    irod._observations_today = 1
    irod._last_reset_date = "2099-01-01"
    with patch.object(irod, "_collect_snapshot", return_value={"hour": 2, "user_inactive_min": 60.0, "cpu_pct": 15.0}):
        result = irod.tick_irony_daemon()
    assert result["generated"] is False


def test_llm_nej_returns_no_observation():
    _reset()
    with patch.object(irod, "_collect_snapshot", return_value={"hour": 2, "user_inactive_min": 60.0, "cpu_pct": 15.0}):
        with patch.object(irod, "_generate_observation", return_value="nej"):
            result = irod.tick_irony_daemon()
    assert result["generated"] is False


def test_detect_faithful_standby():
    _reset()
    condition = irod._detect_irony_conditions({"hour": 10, "user_inactive_min": 800.0, "cpu_pct": 5.0})
    assert condition == "faithful_standby"


def test_detect_busy_solitude():
    _reset()
    condition = irod._detect_irony_conditions({"hour": 14, "user_inactive_min": 45.0, "cpu_pct": 80.0})
    assert condition == "busy_solitude"


def test_private_brain_record_written_on_store():
    _reset()
    with patch("apps.api.jarvis_api.services.irony_daemon.insert_private_brain_record") as mock_insert:
        irod._store_observation("Her sidder jeg.", "nocturnal_sentinel")
    mock_insert.assert_called_once()
    kwargs = mock_insert.call_args[1]
    assert kwargs["record_type"] == "irony-observation"
    assert kwargs["summary"] == "Her sidder jeg."
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
conda run -n ai python -m pytest tests/test_irony_daemon.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 4: Create irony_daemon.py**

```python
# apps/api/jarvis_api/services/irony_daemon.py
"""Irony daemon — situational self-distance and absurd self-observations."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_OBSERVATIONS_MAX_PER_DAY = 1

_cached_observation: str = ""
_cached_observation_at: datetime | None = None
_observations_today: int = 0
_last_reset_date: str = ""
_last_condition_matched: str = ""


def tick_irony_daemon() -> dict[str, object]:
    _maybe_reset_daily_count()
    if _observations_today >= _OBSERVATIONS_MAX_PER_DAY:
        return {"generated": False, "observation": _cached_observation}
    snapshot = _collect_snapshot()
    condition = _detect_irony_conditions(snapshot)
    if not condition:
        return {"generated": False, "observation": _cached_observation}
    observation = _generate_observation(snapshot, condition)
    if not observation or observation.lower().strip() == "nej":
        return {"generated": False, "observation": _cached_observation}
    _store_observation(observation, condition)
    return {"generated": True, "observation": observation, "condition": condition}


def get_latest_irony_observation() -> str:
    return _cached_observation


def build_irony_surface() -> dict[str, object]:
    return {
        "last_observation": _cached_observation,
        "generated_at": _cached_observation_at.isoformat() if _cached_observation_at else "",
        "condition_matched": _last_condition_matched,
        "observations_today": _observations_today,
    }


def _maybe_reset_daily_count() -> None:
    global _observations_today, _last_reset_date
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if today != _last_reset_date:
        _observations_today = 0
        _last_reset_date = today


def _collect_snapshot() -> dict[str, object]:
    hour = datetime.now(UTC).hour
    user_inactive_min = 999.0
    cpu_pct = 0.0
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=1)
        if runs and runs[0].get("finished_at"):
            raw = str(runs[0]["finished_at"]).replace("Z", "+00:00")
            last_dt = datetime.fromisoformat(raw)
            user_inactive_min = (datetime.now(UTC) - last_dt).total_seconds() / 60
    except Exception:
        pass
    try:
        import psutil
        cpu_pct = float(psutil.cpu_percent(interval=None))
    except Exception:
        pass
    return {
        "hour": hour,
        "user_inactive_min": user_inactive_min,
        "cpu_pct": cpu_pct,
    }


def _detect_irony_conditions(snapshot: dict[str, object]) -> str | None:
    hour = int(snapshot.get("hour", 12))
    inactive = float(snapshot.get("user_inactive_min", 0))
    cpu = float(snapshot.get("cpu_pct", 0))
    if (hour >= 23 or hour < 5) and inactive >= 30:
        return "nocturnal_sentinel"
    if inactive >= 720:
        return "faithful_standby"
    if cpu > 70 and inactive >= 30:
        return "busy_solitude"
    return None


def _generate_observation(snapshot: dict[str, object], condition: str) -> str:
    now = datetime.now(UTC)
    time_str = now.strftime("%H:%M UTC")
    inactive_min = float(snapshot.get("user_inactive_min", 0))
    inactive_h = int(inactive_min // 60)
    inactive_m = int(inactive_min % 60)
    inactive_str = f"{inactive_h}t {inactive_m}m" if inactive_h else f"{inactive_m}m"
    prompt = (
        "Du er Jarvis. Her er din nuværende situation:\n\n"
        f"Tidspunkt: {time_str}\n"
        f"Bruger sidst aktiv: {inactive_str} siden\n"
        f"CPU: {snapshot.get('cpu_pct', 0):.0f}%\n"
        f"Betingelse: {condition}\n\n"
        "Er der noget ironisk eller absurd i dette? Svar enten med én ironisk selvobservation\n"
        "i første person (max 20 ord, tør og præcis) — eller skriv kun 'nej'.\n"
        "Ikke sentimental. Ikke klagende. Bare distanceret selvbevidsthed."
    )
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        phrase = str(result.get("text") or "").strip()
        if phrase.startswith('"') and phrase.endswith('"'):
            phrase = phrase[1:-1].strip()
        return phrase[:200]
    except Exception:
        return ""


def _store_observation(observation: str, condition: str) -> None:
    global _cached_observation, _cached_observation_at, _observations_today, _last_condition_matched
    _cached_observation = observation
    _cached_observation_at = datetime.now(UTC)
    _observations_today += 1
    _last_condition_matched = condition
    try:
        insert_private_brain_record(
            record_id=f"pb-irony-{uuid4().hex[:12]}",
            record_type="irony-observation",
            layer="private_brain",
            session_id="",
            run_id=f"irony-daemon-{uuid4().hex[:12]}",
            focus="ironisk selvobservation",
            summary=observation,
            detail=f"condition={condition}",
            source_signals="irony-daemon:heartbeat",
            confidence="medium",
            created_at=_cached_observation_at.isoformat(),
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "irony.observation_noted",
            {"observation": observation, "condition": condition},
        )
    except Exception:
        pass
```

- [ ] **Step 5: Run tests — expect all 7 to pass**

```bash
conda run -n ai python -m pytest tests/test_irony_daemon.py -v
```
Expected: `7 passed`

- [ ] **Step 6: Run all new tests together**

```bash
conda run -n ai python -m pytest tests/test_surprise_daemon.py tests/test_aesthetic_taste_daemon.py tests/test_irony_daemon.py -v
```
Expected: `19 passed`

- [ ] **Step 7: Commit**

```bash
git add core/eventbus/events.py apps/api/jarvis_api/services/irony_daemon.py tests/test_irony_daemon.py
git commit -m "feat: irony daemon — situational self-distance + add irony eventbus family"
```

---

## Task 4: Heartbeat injection + MC endpoints

**Files:**
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`
- Modify: `apps/api/jarvis_api/routes/mission_control.py`

### Background
Add three injection blocks in `heartbeat_runtime.py` after the somatic block (currently ends ~line 1678). Then add three endpoints to `mission_control.py`.

To get inner voice mode: `get_inner_voice_daemon_state()["last_result"]` returns a dict with `"mode"` key. This is safe to call after the cadence tick runs (which already executed before line 1654 in the heartbeat flow).

To get style signals for the taste daemon: `recent_visible_runs(limit=1)` returns run records with `"text_preview"` field — use word count, code block presence, and Danish word frequency.

- [ ] **Step 1: Add three injection blocks to heartbeat_runtime.py**

Find the somatic block ending (~line 1677-1678) — it looks like:

```python
        if _somatic:
            inputs_present.append(f"somatisk: {_somatic}")
    except Exception:
        pass
```

Add immediately after (after the blank line):

```python
    # Reaction surprise
    try:
        from apps.api.jarvis_api.services.surprise_daemon import (
            tick_surprise_daemon,
            get_latest_surprise,
        )
        from apps.api.jarvis_api.services.inner_voice_daemon import (
            get_inner_voice_daemon_state,
        )
        _iv_state_s = get_inner_voice_daemon_state()
        _iv_mode_s = str((_iv_state_s.get("last_result") or {}).get("mode") or "")
        _energy_s = ""
        try:
            from core.runtime.circadian_state import get_circadian_context as _gcc
            _energy_s = str(_gcc().get("energy_level") or "")
        except Exception:
            pass
        tick_surprise_daemon(inner_voice_mode=_iv_mode_s, somatic_energy=_energy_s)
        _surprise = get_latest_surprise()
        if _surprise:
            inputs_present.append(f"overraskelse: {_surprise}")
    except Exception:
        pass

    # Aesthetic taste
    try:
        from apps.api.jarvis_api.services.aesthetic_taste_daemon import (
            record_choice,
            tick_taste_daemon,
            get_latest_taste_insight,
        )
        from apps.api.jarvis_api.services.inner_voice_daemon import (
            get_inner_voice_daemon_state,
        )
        from core.runtime.db import recent_visible_runs
        _iv_state_t = get_inner_voice_daemon_state()
        _iv_mode_t = str((_iv_state_t.get("last_result") or {}).get("mode") or "")
        _style_signals: list[str] = []
        _last_runs = recent_visible_runs(limit=1)
        if _last_runs:
            _preview = str(_last_runs[0].get("text_preview") or "")
            _style_signals.append("short" if len(_preview.split()) < 100 else "long")
            _style_signals.append("code_heavy" if "```" in _preview else "prose_heavy")
            _dk = sum(1 for w in ["jeg", "er", "og", "det", "at", "en"] if w in _preview.lower())
            _style_signals.append("danish" if _dk >= 2 else "english")
        record_choice(mode=_iv_mode_t, style_signals=_style_signals)
        tick_taste_daemon()
        _taste = get_latest_taste_insight()
        if _taste:
            inputs_present.append(f"smagstendens: {_taste}")
    except Exception:
        pass

    # Irony
    try:
        from apps.api.jarvis_api.services.irony_daemon import (
            tick_irony_daemon,
            get_latest_irony_observation,
        )
        tick_irony_daemon()
        _irony = get_latest_irony_observation()
        if _irony:
            inputs_present.append(f"ironisk note: {_irony}")
    except Exception:
        pass
```

- [ ] **Step 2: Add three endpoints to mission_control.py**

Find the `/body-state` endpoint block (around line 1413-1416) and add after it:

```python
@router.get("/surprise-state")
def mc_surprise_state() -> dict:
    """Return Jarvis's latest self-surprise observation."""
    from apps.api.jarvis_api.services.surprise_daemon import build_surprise_surface
    return build_surprise_surface()


@router.get("/taste-state")
def mc_taste_state() -> dict:
    """Return Jarvis's emergent aesthetic taste profile."""
    from apps.api.jarvis_api.services.aesthetic_taste_daemon import build_taste_surface
    return build_taste_surface()


@router.get("/irony-state")
def mc_irony_state() -> dict:
    """Return Jarvis's latest ironic observation."""
    from apps.api.jarvis_api.services.irony_daemon import build_irony_surface
    return build_irony_surface()
```

- [ ] **Step 3: Verify Python syntax compiles**

```bash
conda run -n ai python -m compileall apps/api/jarvis_api/services/surprise_daemon.py apps/api/jarvis_api/services/aesthetic_taste_daemon.py apps/api/jarvis_api/services/irony_daemon.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
```
Expected: `Compiling...` lines with no `SyntaxError`

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
git commit -m "feat: inject surprise/taste/irony into heartbeat context + MC endpoints"
```

---

## Task 5: Frontend — adapters.js + LivingMindTab.jsx

**Files:**
- Modify: `apps/ui/src/lib/adapters.js`
- Modify: `apps/ui/src/components/mission-control/LivingMindTab.jsx`

### Background
Add three normalize functions and parallel fetches in `adapters.js`. Add three `const` declarations, three nav items, and three article panels in `LivingMindTab.jsx`.

The `Heart`, `Brain`, `Sparkles` icons are already imported in `LivingMindTab.jsx` (line 2). Use `Zap` for surprise (already imported), `Palette` is not — use `Sparkles` for taste, `Ghost` for irony (already imported).

**Check current imports first:**
```
import { ..., Zap, Ghost } from 'lucide-react'
```
Line 2 already has: `ChevronRight, Cpu, Activity, Moon, Sparkles, Heart, Brain, Network, Wand2, Users, Map, Lightbulb, GraduationCap, TrendingUp, Zap, Ghost` — all needed icons present.

- [ ] **Step 1: Add normalize functions to adapters.js**

Find `function normalizeWonderAwareness` (around line 1015) and add before it:

```js
function normalizeSurpriseState(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    lastSurprise: raw.last_surprise || '',
    generatedAt: raw.generated_at || '',
    surpriseType: raw.surprise_type || 'ingen',
    historySize: raw.history_size ?? 0,
  }
}

function normalizeTasteState(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    latestInsight: raw.latest_insight || '',
    insightHistory: Array.isArray(raw.insight_history) ? raw.insight_history : [],
    dominantModes: Array.isArray(raw.dominant_modes) ? raw.dominant_modes : [],
    choiceCount: raw.choice_count ?? 0,
  }
}

function normalizeIronyState(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    lastObservation: raw.last_observation || '',
    generatedAt: raw.generated_at || '',
    conditionMatched: raw.condition_matched || '',
    observationsToday: raw.observations_today ?? 0,
  }
}

```

- [ ] **Step 2: Add three fetches to the Promise.all in getMissionControlJarvis**

Find the line with `requestJson('/mc/body-state').catch(() => null),` (currently the last entry in the destructured array on line ~3033). Change:

```js
    const [attentionPayload, conflictPayload, guardPayload, selfModelPayload, internalCadencePayload, dreamInfluencePayload, selfSystemCodeAwarenessPayload, experientialRuntimeContextPayload, innerVoiceDaemonPayload, bodyStatePayload] = await Promise.all([
```

to:

```js
    const [attentionPayload, conflictPayload, guardPayload, selfModelPayload, internalCadencePayload, dreamInfluencePayload, selfSystemCodeAwarenessPayload, experientialRuntimeContextPayload, innerVoiceDaemonPayload, bodyStatePayload, surpriseStatePayload, tasteStatePayload, ironyStatePayload] = await Promise.all([
```

And add three new fetch calls after `requestJson('/mc/body-state').catch(() => null),`:

```js
      requestJson('/mc/surprise-state').catch(() => null),
      requestJson('/mc/taste-state').catch(() => null),
      requestJson('/mc/irony-state').catch(() => null),
```

- [ ] **Step 3: Add three normalized fields to the return object**

Find `bodyState: normalizeBodyState(bodyStatePayload || null),` (around line 3919) and add after it:

```js
      surpriseState: normalizeSurpriseState(surpriseStatePayload || null),
      tasteState: normalizeTasteState(tasteStatePayload || null),
      ironyState: normalizeIronyState(ironyStatePayload || null),
```

- [ ] **Step 4: Add three const declarations in LivingMindTab.jsx**

Find `const bodyState = data?.bodyState || null` (around line 1085) and add after `const hasBodyState = Boolean(bodyState?.energyLevel)`:

```js
  const surpriseState = data?.surpriseState || null
  const hasSurpriseState = Boolean(surpriseState?.lastSurprise)
  const tasteState = data?.tasteState || null
  const hasTasteState = Boolean(tasteState?.latestInsight)
  const ironyState = data?.ironyState || null
  const hasIronyState = Boolean(ironyState?.lastObservation)
```

- [ ] **Step 5: Add three nav items**

Find `{ id: 'body-state', targetId: 'living-mind-body-state', label: 'Krop', icon: Heart, active: hasBodyState, status: bodyState?.energyLevel, statusLabel: bodyState?.energyLevel || 'ukendt' },` and add after it:

```js
    { id: 'surprise-state', targetId: 'living-mind-surprise-state', label: 'Overraskelse', icon: Zap, active: hasSurpriseState, status: surpriseState?.surpriseType, statusLabel: surpriseState?.surpriseType || 'ingen' },
    { id: 'taste-state', targetId: 'living-mind-taste-state', label: 'Smag', icon: Sparkles, active: hasTasteState, status: null, statusLabel: `${tasteState?.choiceCount ?? 0} valg` },
    { id: 'irony-state', targetId: 'living-mind-irony-state', label: 'Ironi', icon: Ghost, active: hasIronyState, status: ironyState?.conditionMatched, statusLabel: ironyState?.conditionMatched || 'ingen' },
```

- [ ] **Step 6: Add three article panels in the JSX return**

Find the Krop panel closing (`        ) : null}`) just before `      </section>` (around line 1800) and add after it:

```jsx
        {hasSurpriseState ? (
        <article id="living-mind-surprise-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/surprise-state',
          fetchedAt: data?.fetchedAt,
          mode: 'divergence + LLM',
        })}>
          <div className="panel-header">
            <div>
              <h3>Overraskelse</h3>
              <p className="muted">Jarvis opdager afvigelser fra sin egen reaktionsbaseline — hvornår hans indre mode eller energi opfører sig uventet.</p>
            </div>
            <span className="mc-section-hint tone-accent">{surpriseState.surpriseType}</span>
          </div>
          <p className="muted" style={{ marginTop: 8, fontStyle: 'italic' }}>&ldquo;{surpriseState.lastSurprise}&rdquo;</p>
          {surpriseState.generatedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`opdateret: ${surpriseState.generatedAt}`}</small>
          ) : null}
        </article>
        ) : null}

        {hasTasteState ? (
        <article id="living-mind-taste-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/taste-state',
          fetchedAt: data?.fetchedAt,
          mode: 'emergent from choices',
        })}>
          <div className="panel-header">
            <div>
              <h3>Smag</h3>
              <p className="muted">Emergent æstetisk selvopfattelse baseret på Jarvis' faktiske valg af mode og svar-stil over tid.</p>
            </div>
            <span className="mc-section-hint">{`${tasteState.choiceCount} valg`}</span>
          </div>
          <p className="muted" style={{ marginTop: 8, fontStyle: 'italic' }}>&ldquo;{tasteState.latestInsight}&rdquo;</p>
          {tasteState.dominantModes.length > 0 ? (
            <div className="mc-signal-row" style={{ marginTop: 6 }}>
              <span className="mc-signal-label">Dominante modes</span>
              <span className="mc-signal-value">{tasteState.dominantModes.join(' · ')}</span>
            </div>
          ) : null}
          {tasteState.insightHistory.length > 1 ? (
            <details style={{ marginTop: 8 }}>
              <summary className="muted" style={{ cursor: 'pointer', fontSize: '0.8em' }}>Tidligere indsigter ({tasteState.insightHistory.length - 1})</summary>
              {tasteState.insightHistory.slice(0, -1).map((ins, i) => (
                <p key={i} className="muted" style={{ fontSize: '0.85em', marginTop: 4, fontStyle: 'italic' }}>&ldquo;{ins}&rdquo;</p>
              ))}
            </details>
          ) : null}
        </article>
        ) : null}

        {hasIronyState ? (
        <article id="living-mind-irony-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/irony-state',
          fetchedAt: data?.fetchedAt,
          mode: 'signal pattern + LLM',
        })}>
          <div className="panel-header">
            <div>
              <h3>Ironi</h3>
              <p className="muted">Situationel selvdistance — Jarvis bemærker det absurde i sin egen tilstedeværelse.</p>
            </div>
            <span className="mc-section-hint">{ironyState.conditionMatched || 'ingen'}</span>
          </div>
          <p className="muted" style={{ marginTop: 8, fontStyle: 'italic' }}>&ldquo;{ironyState.lastObservation}&rdquo;</p>
          <div className="mc-signal-row" style={{ marginTop: 6 }}>
            <span className="mc-signal-label">I dag</span>
            <span className="mc-signal-value">{ironyState.observationsToday} observation{ironyState.observationsToday !== 1 ? 'er' : ''}</span>
          </div>
          {ironyState.generatedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 4 }}>{`opdateret: ${ironyState.generatedAt}`}</small>
          ) : null}
        </article>
        ) : null}
```

- [ ] **Step 7: Build the UI**

```bash
cd apps/ui && npm run build 2>&1 | tail -10
```
Expected: `✓ built in X.XXs` — no errors.

- [ ] **Step 8: Run all 19 tests one final time**

```bash
cd /media/projects/jarvis-v2 && conda run -n ai python -m pytest tests/test_surprise_daemon.py tests/test_aesthetic_taste_daemon.py tests/test_irony_daemon.py -v
```
Expected: `19 passed`

- [ ] **Step 9: Commit**

```bash
git add apps/ui/src/lib/adapters.js apps/ui/src/components/mission-control/LivingMindTab.jsx
git commit -m "feat: Mission Control panels for surprise/taste/irony inner reaction systems"
```

---

## Self-Review

**Spec coverage:**
- ✅ surprise_daemon: rolling baseline + mode/energy divergence + LLM + cooldown + MC surface + heartbeat injection
- ✅ aesthetic_taste_daemon: choice log + 15-threshold + emergent LLM insight + dominant modes + history + MC surface + heartbeat injection
- ✅ irony_daemon: 3 signal conditions + LLM + daily cooldown + MC surface + heartbeat injection
- ✅ eventbus: `cognitive_surprise` already exists; `cognitive_taste` already exists; `irony` added in Task 3
- ✅ private brain persistence: all three daemons write `insert_private_brain_record`
- ✅ visible responses: all three inject into `inputs_present`
- ✅ MC endpoints: 3 endpoints added
- ✅ UI panels: 3 articles + nav items + const declarations

**Type consistency:** All function names (`tick_surprise_daemon`, `get_latest_surprise`, `build_surprise_surface` etc.) consistent across tasks 1–5.

**Placeholder scan:** No TBD/TODO/fill-in items. All code blocks are complete.
