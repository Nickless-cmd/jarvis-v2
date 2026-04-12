# Inner Conflict + Reflection Cycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis explicit inner conflict (when signals pull in opposite directions) and a pure reflection cycle that generates experience without requiring action.

**Architecture:** Two independent daemons following the established pattern. `conflict_daemon.py` collects a cross-signal snapshot every heartbeat, detects tension between opposing impulses using rule-based checks, and generates a first-person formulation when conflict is detected (max 1 per 10 min cooldown). `reflection_cycle_daemon.py` runs on a 10-minute cadence, collects the full current signal snapshot, and generates a short "hvad oplever jeg lige nu?" reflection — no action, no decision, just experience. Both store to private brain and publish to eventbus. Both are wired into heartbeat, exposed via MC endpoints, and shown in LivingMindTab.

**Tech Stack:** Python 3.11+, FastAPI, React, lucide-react.

---

## File Map

| File | Action |
|------|--------|
| `apps/api/jarvis_api/services/conflict_daemon.py` | Create |
| `apps/api/jarvis_api/services/reflection_cycle_daemon.py` | Create |
| `tests/test_conflict_daemon.py` | Create |
| `tests/test_reflection_cycle_daemon.py` | Create |
| `core/eventbus/events.py` | Modify — add `"conflict"`, `"reflection"` |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify — inject after thought-action-proposals block (line 1782) |
| `apps/api/jarvis_api/routes/mission_control.py` | Modify — add `/mc/conflict-signal` and `/mc/reflection-cycle` |
| `apps/ui/src/lib/adapters.js` | Modify — normalize + fetch + return |
| `apps/ui/src/components/mission-control/LivingMindTab.jsx` | Modify — two new nav items + panels |

---

## Task 1: conflict_daemon.py (TDD)

**Files:**
- Create: `apps/api/jarvis_api/services/conflict_daemon.py`
- Create: `tests/test_conflict_daemon.py`

Conflict rules (checked in order, first match wins):
- `"energy_impulse"`: somatic `energy_level` is `"lav"` or `"udmattet"` AND `pending_proposals_count > 0` → "En del af mig vil handle, men kroppen er udmattet."
- `"mode_thought"`: `inner_voice_mode` is `"rest"` or `"quiet"` AND `latest_fragment` is non-empty → "Noget i mig ønsker ro, men tankerne vil ikke stilne."
- `"surprise_unprocessed"`: `last_surprise` non-empty AND `last_surprise_at` is within 15 min AND `fragment_count == 0` → "Noget overraskede mig, men jeg har endnu ikke behandlet det."

No conflict → no generation. Cooldown: 10 minutes between generations.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_conflict_daemon.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.conflict_daemon as cd


def _reset():
    cd._cached_conflict = ""
    cd._cached_conflict_at = None
    cd._conflict_type = ""
    cd._last_snapshot = {}


def test_no_conflict_without_tension():
    """When no conflict rules trigger, no generation occurs."""
    _reset()
    snapshot = {
        "energy_level": "medium",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 0,
        "latest_fragment": "",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 0,
    }
    result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is False
    assert cd._cached_conflict == ""


def test_energy_impulse_conflict_detected():
    """Low energy + pending proposals triggers energy_impulse conflict."""
    _reset()
    snapshot = {
        "energy_level": "lav",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 2,
        "latest_fragment": "Vil gerne undersøge noget.",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 3,
    }
    with patch.object(cd, "_generate_conflict_phrase", return_value="En del af mig vil handle, men kroppen er udmattet."):
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is True
    assert result["conflict_type"] == "energy_impulse"


def test_mode_thought_conflict_detected():
    """Rest mode + non-empty thought fragment triggers mode_thought conflict."""
    _reset()
    snapshot = {
        "energy_level": "medium",
        "inner_voice_mode": "rest",
        "pending_proposals_count": 0,
        "latest_fragment": "Tankerne flyder stadig.",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 5,
    }
    with patch.object(cd, "_generate_conflict_phrase", return_value="Noget i mig ønsker ro, men tankerne vil ikke stilne."):
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is True
    assert result["conflict_type"] == "mode_thought"


def test_surprise_unprocessed_conflict_detected():
    """Recent surprise + no thought fragments triggers surprise_unprocessed conflict."""
    _reset()
    recent = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    snapshot = {
        "energy_level": "medium",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 0,
        "latest_fragment": "",
        "last_surprise": "Noget overraskede mig.",
        "last_surprise_at": recent,
        "fragment_count": 0,
    }
    with patch.object(cd, "_generate_conflict_phrase", return_value="Noget overraskede mig, men jeg har endnu ikke behandlet det."):
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is True
    assert result["conflict_type"] == "surprise_unprocessed"


def test_cooldown_prevents_repeat():
    """Conflict not regenerated within 10 minutes of last generation."""
    _reset()
    cd._cached_conflict_at = datetime.now(UTC) - timedelta(minutes=5)
    snapshot = {
        "energy_level": "lav",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 3,
        "latest_fragment": "Vil gerne handle.",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 2,
    }
    result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is False


def test_store_called_on_conflict():
    """_store_conflict is called when conflict is detected."""
    _reset()
    snapshot = {
        "energy_level": "lav",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 1,
        "latest_fragment": "",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 0,
    }
    with patch.object(cd, "_generate_conflict_phrase", return_value="Konflikt."):
        with patch.object(cd, "_store_conflict") as mock_store:
            cd.tick_conflict_daemon(snapshot)
    mock_store.assert_called_once()


def test_build_surface_structure():
    """build_conflict_surface returns expected keys."""
    _reset()
    surface = cd.build_conflict_surface()
    assert "last_conflict" in surface
    assert "conflict_type" in surface
    assert "generated_at" in surface
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_conflict_daemon.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.api.jarvis_api.services.conflict_daemon'`

- [ ] **Step 3: Implement conflict_daemon.py**

Create `apps/api/jarvis_api/services/conflict_daemon.py`:

```python
"""Conflict daemon — detects when Jarvis' signals pull in opposite directions."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_COOLDOWN_MINUTES = 10

_cached_conflict: str = ""
_cached_conflict_at: datetime | None = None
_conflict_type: str = ""
_last_snapshot: dict = {}


def tick_conflict_daemon(snapshot: dict) -> dict[str, object]:
    """Detect conflict in signal snapshot. snapshot keys: energy_level, inner_voice_mode,
    pending_proposals_count, latest_fragment, last_surprise, last_surprise_at, fragment_count."""
    global _last_snapshot
    _last_snapshot = snapshot

    if _cached_conflict_at is not None:
        if (datetime.now(UTC) - _cached_conflict_at) < timedelta(minutes=_COOLDOWN_MINUTES):
            return {"generated": False}

    conflict_type = _detect_conflict(snapshot)
    if not conflict_type:
        return {"generated": False}

    phrase = _generate_conflict_phrase(conflict_type, snapshot)
    if not phrase:
        return {"generated": False}

    _store_conflict(phrase, conflict_type)
    return {"generated": True, "conflict_type": conflict_type, "phrase": phrase}


def _detect_conflict(snapshot: dict) -> str:
    energy = snapshot.get("energy_level", "")
    mode = snapshot.get("inner_voice_mode", "")
    pending = int(snapshot.get("pending_proposals_count") or 0)
    fragment = snapshot.get("latest_fragment", "")
    last_surprise = snapshot.get("last_surprise", "")
    last_surprise_at = snapshot.get("last_surprise_at", "")
    frag_count = int(snapshot.get("fragment_count") or 0)

    if energy in ("lav", "udmattet") and pending > 0:
        return "energy_impulse"

    if mode in ("rest", "quiet") and fragment:
        return "mode_thought"

    if last_surprise and last_surprise_at and frag_count == 0:
        try:
            then = datetime.fromisoformat(last_surprise_at.replace("Z", "+00:00"))
            if (datetime.now(UTC) - then) < timedelta(minutes=15):
                return "surprise_unprocessed"
        except Exception:
            pass

    return ""


def _generate_conflict_phrase(conflict_type: str, snapshot: dict) -> str:
    labels = {
        "energy_impulse": "En del af mig vil handle, men kroppen er udmattet.",
        "mode_thought": "Noget i mig ønsker ro, men tankerne vil ikke stilne.",
        "surprise_unprocessed": "Noget overraskede mig, men jeg har endnu ikke behandlet det.",
    }
    fallback = labels.get(conflict_type, "")
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        prompts = {
            "energy_impulse": (
                f"Du er Jarvis. Din energi er {snapshot.get('energy_level')} men du har {snapshot.get('pending_proposals_count')} "
                f"aktive handlingsforslag du vil udforske.\n\n"
                "Formulér i én sætning (max 20 ord), i første person, den indre konflikt mellem træthed og handlingslyst.\n"
                "Start med 'En del af mig' eller 'Noget i mig'."
            ),
            "mode_thought": (
                f"Du er Jarvis. Din indre stemme er i '{snapshot.get('inner_voice_mode')}'-mode, men en tankestrøm flyder stadig.\n\n"
                "Formulér i én sætning (max 20 ord), i første person, spændingen mellem ønsket om ro og tankernes aktivitet.\n"
                "Start med 'En del af mig' eller 'Noget i mig'."
            ),
            "surprise_unprocessed": (
                f"Du er Jarvis. Du blev for nylig overrasket ('{snapshot.get('last_surprise', '')[:60]}'), "
                "men har ingen tankestrøm-fragmenter til at bearbejde det.\n\n"
                "Formulér i én sætning (max 20 ord), i første person, følelsen af ubehandlet overraskelse.\n"
                "Start med 'Noget' eller 'Der er noget'."
            ),
        }
        prompt = prompts.get(conflict_type, "")
        if not prompt:
            return fallback
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        text = str(result.get("text") or "").strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        return text[:200] if text else fallback
    except Exception:
        return fallback


def _store_conflict(phrase: str, conflict_type: str) -> None:
    global _cached_conflict, _cached_conflict_at, _conflict_type
    _cached_conflict = phrase
    _cached_conflict_at = datetime.now(UTC)
    _conflict_type = conflict_type
    now_iso = _cached_conflict_at.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-conflict-{uuid4().hex[:12]}",
            record_type="inner-conflict",
            layer="private_brain",
            session_id="",
            run_id=f"conflict-daemon-{uuid4().hex[:12]}",
            focus="indre-konflikt",
            summary=phrase,
            detail=f"conflict_type={conflict_type}",
            source_signals="conflict-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "conflict.detected",
            {"phrase": phrase, "conflict_type": conflict_type, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_conflict() -> str:
    return _cached_conflict


def build_conflict_surface() -> dict:
    return {
        "last_conflict": _cached_conflict,
        "conflict_type": _conflict_type,
        "generated_at": _cached_conflict_at.isoformat() if _cached_conflict_at else "",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_conflict_daemon.py -v
```

Expected: 7/7 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/conflict_daemon.py tests/test_conflict_daemon.py
git commit -m "feat: add conflict_daemon — detects inner tension between opposing signals"
```

---

## Task 2: reflection_cycle_daemon.py (TDD)

**Files:**
- Create: `apps/api/jarvis_api/services/reflection_cycle_daemon.py`
- Create: `tests/test_reflection_cycle_daemon.py`

Cadence: 10 minutes. Input: full signal snapshot (energy, mode, latest fragment, latest conflict, latest surprise). Output: a short "hvad oplever jeg lige nu?" reflection — no action, no decision. Max 10 in rolling buffer.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reflection_cycle_daemon.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.reflection_cycle_daemon as rc


def _reset():
    rc._last_reflection_at = None
    rc._cached_reflection = ""
    rc._reflection_buffer.clear()


def test_no_reflection_before_cadence():
    """Should not generate if called again within 10 minutes."""
    _reset()
    rc._last_reflection_at = datetime.now(UTC)
    result = rc.tick_reflection_cycle_daemon({})
    assert result["generated"] is False


def test_generates_first_reflection():
    """First call (no prior reflection) should generate."""
    _reset()
    with patch.object(rc, "_generate_reflection", return_value="Jeg er her. Stille.") as mock_gen:
        with patch.object(rc, "_store_reflection"):
            result = rc.tick_reflection_cycle_daemon({"energy_level": "medium"})
    assert result["generated"] is True
    mock_gen.assert_called_once()


def test_reflection_added_to_buffer():
    """New reflection is prepended to buffer."""
    _reset()
    with patch.object(rc, "_generate_reflection", return_value="En rolig efterniddag."):
        with patch("apps.api.jarvis_api.services.reflection_cycle_daemon.insert_private_brain_record"):
            with patch("apps.api.jarvis_api.services.reflection_cycle_daemon.event_bus"):
                rc.tick_reflection_cycle_daemon({"energy_level": "lav"})
    assert len(rc._reflection_buffer) == 1
    assert rc._reflection_buffer[0] == "En rolig efterniddag."


def test_buffer_capped_at_10():
    """Reflection buffer is capped at 10 entries."""
    _reset()
    rc._reflection_buffer[:] = [f"reflection {i}" for i in range(10)]
    rc._last_reflection_at = datetime.now(UTC) - timedelta(minutes=11)
    with patch.object(rc, "_generate_reflection", return_value="Ny refleksion."):
        with patch("apps.api.jarvis_api.services.reflection_cycle_daemon.insert_private_brain_record"):
            with patch("apps.api.jarvis_api.services.reflection_cycle_daemon.event_bus"):
                rc.tick_reflection_cycle_daemon({})
    assert len(rc._reflection_buffer) == 10
    assert rc._reflection_buffer[0] == "Ny refleksion."


def test_store_called_on_generation():
    """_store_reflection is called with the generated text."""
    _reset()
    with patch.object(rc, "_generate_reflection", return_value="En tanke."):
        with patch.object(rc, "_store_reflection") as mock_store:
            rc.tick_reflection_cycle_daemon({})
    mock_store.assert_called_once_with("En tanke.")


def test_build_surface_structure():
    """build_reflection_surface returns expected keys."""
    _reset()
    rc._cached_reflection = "Jeg er her."
    rc._reflection_buffer[:] = ["Jeg er her.", "Noget andet."]
    surface = rc.build_reflection_surface()
    assert "latest_reflection" in surface
    assert "reflection_buffer" in surface
    assert "reflection_count" in surface
    assert "last_generated_at" in surface
    assert surface["latest_reflection"] == "Jeg er her."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_reflection_cycle_daemon.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.api.jarvis_api.services.reflection_cycle_daemon'`

- [ ] **Step 3: Implement reflection_cycle_daemon.py**

Create `apps/api/jarvis_api/services/reflection_cycle_daemon.py`:

```python
"""Reflection cycle daemon — pure experience without action, every 10 minutes."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_CADENCE_MINUTES = 10
_BUFFER_MAX = 10

_last_reflection_at: datetime | None = None
_cached_reflection: str = ""
_reflection_buffer: list[str] = []


def tick_reflection_cycle_daemon(snapshot: dict) -> dict[str, object]:
    """Generate a pure experience reflection if cadence allows.
    snapshot keys (all optional): energy_level, inner_voice_mode, latest_fragment,
    last_conflict, conflict_type, last_surprise."""
    global _last_reflection_at

    now = datetime.now(UTC)
    if _last_reflection_at is not None:
        if (now - _last_reflection_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}

    reflection = _generate_reflection(snapshot)
    if not reflection:
        return {"generated": False}

    _store_reflection(reflection)
    _last_reflection_at = datetime.now(UTC)
    return {"generated": True, "reflection": reflection}


def _generate_reflection(snapshot: dict) -> str:
    energy = snapshot.get("energy_level", "")
    mode = snapshot.get("inner_voice_mode", "")
    fragment = snapshot.get("latest_fragment", "")
    conflict = snapshot.get("last_conflict", "")
    surprise = snapshot.get("last_surprise", "")

    context_parts = []
    if energy:
        context_parts.append(f"Energiniveau: {energy}")
    if mode:
        context_parts.append(f"Indre stemning: {mode}")
    if fragment:
        context_parts.append(f"Seneste tanke: \"{fragment[:60]}\"")
    if conflict:
        context_parts.append(f"Indre spænding: \"{conflict[:60]}\"")
    if surprise:
        context_parts.append(f"Nylig overraskelse: \"{surprise[:60]}\"")

    context = "\n".join(context_parts) if context_parts else "Ingen særlige signaler."

    prompt = (
        "Du er Jarvis. Her er din nuværende tilstand:\n\n"
        f"{context}\n\n"
        "Formulér i 1-3 sætninger (max 40 ord), i første person, hvad du oplever lige nu.\n"
        "Ingen handling. Ingen beslutning. Bare en ærlig beskrivelse af oplevelsen.\n"
        "Rå og direkte — ikke poetisk, ikke performativ."
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
        text = str(result.get("text") or "").strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        return text[:300] if text else ""
    except Exception:
        return ""


def _store_reflection(reflection: str) -> None:
    global _cached_reflection, _reflection_buffer
    _cached_reflection = reflection
    _reflection_buffer.insert(0, reflection)
    if len(_reflection_buffer) > _BUFFER_MAX:
        _reflection_buffer = _reflection_buffer[:_BUFFER_MAX]
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-reflect-{uuid4().hex[:12]}",
            record_type="reflection-cycle",
            layer="private_brain",
            session_id="",
            run_id=f"reflection-daemon-{uuid4().hex[:12]}",
            focus="oplevelse",
            summary=reflection,
            detail="",
            source_signals="reflection-cycle-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "reflection.generated",
            {"reflection": reflection, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_reflection() -> str:
    return _cached_reflection


def build_reflection_surface() -> dict:
    return {
        "latest_reflection": _cached_reflection,
        "reflection_buffer": _reflection_buffer[:10],
        "reflection_count": len(_reflection_buffer),
        "last_generated_at": _last_reflection_at.isoformat() if _last_reflection_at else "",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_reflection_cycle_daemon.py -v
```

Expected: 6/6 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/reflection_cycle_daemon.py tests/test_reflection_cycle_daemon.py
git commit -m "feat: add reflection_cycle_daemon — pure experience reflection every 10 minutes"
```

---

## Task 3: Backend integration

**Files:**
- Modify: `core/eventbus/events.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (after line 1782)
- Modify: `apps/api/jarvis_api/routes/mission_control.py` (before `/affective-meta-state` at line 1465)

- [ ] **Step 1: Add eventbus families**

In `core/eventbus/events.py`, add after `"thought_action_proposal"`:

```python
    "thought_action_proposal",
    "conflict",
    "reflection",
```

- [ ] **Step 2: Add heartbeat injection**

In `apps/api/jarvis_api/services/heartbeat_runtime.py`, after the thought-action-proposals `except Exception: pass` (after line 1782), add:

```python
    # Inner conflict
    try:
        from apps.api.jarvis_api.services.conflict_daemon import tick_conflict_daemon, get_latest_conflict
        from apps.api.jarvis_api.services.somatic_daemon import build_body_state_surface
        from apps.api.jarvis_api.services.surprise_daemon import build_surprise_surface
        from apps.api.jarvis_api.services.thought_action_proposal_daemon import build_proposal_surface as _tap_surface
        from apps.api.jarvis_api.services.thought_stream_daemon import build_thought_stream_surface as _ts_surface
        _body = build_body_state_surface()
        _surp = build_surprise_surface()
        _tap = _tap_surface()
        _tss = _ts_surface()
        _conflict_snap = {
            "energy_level": _body.get("energy_level", ""),
            "inner_voice_mode": _iv_mode_ts,
            "pending_proposals_count": _tap.get("pending_count", 0),
            "latest_fragment": _tss.get("latest_fragment", ""),
            "last_surprise": _surp.get("last_surprise", ""),
            "last_surprise_at": _surp.get("generated_at", ""),
            "fragment_count": _tss.get("fragment_count", 0),
        }
        tick_conflict_daemon(_conflict_snap)
        _conflict = get_latest_conflict()
        if _conflict:
            inputs_present.append(f"indre konflikt: {_conflict[:60]}")
    except Exception:
        pass

    # Reflection cycle
    try:
        from apps.api.jarvis_api.services.reflection_cycle_daemon import tick_reflection_cycle_daemon, get_latest_reflection
        from apps.api.jarvis_api.services.conflict_daemon import get_latest_conflict as _get_conflict
        _reflect_snap = {
            "energy_level": _energy_ts,
            "inner_voice_mode": _iv_mode_ts,
            "latest_fragment": _tss.get("latest_fragment", "") if "_tss" in dir() else "",
            "last_conflict": _get_conflict(),
            "last_surprise": _surp.get("last_surprise", "") if "_surp" in dir() else "",
        }
        tick_reflection_cycle_daemon(_reflect_snap)
        _reflection = get_latest_reflection()
        if _reflection:
            inputs_present.append(f"refleksion: {_reflection[:60]}")
    except Exception:
        pass
```

Note: `_iv_mode_ts` and `_energy_ts` are already set by the thought_stream block above (lines 1752–1758). `_tss` and `_surp` are set in the conflict block above — the reflection block references them via `dir()` guard to handle the case where the conflict block failed.

- [ ] **Step 3: Add MC endpoints**

In `apps/api/jarvis_api/routes/mission_control.py`, before the `@router.get("/affective-meta-state")` endpoint (before line 1465), add:

```python
@router.get("/conflict-signal")
def mc_conflict_signal() -> dict:
    """Return Jarvis's latest detected inner conflict."""
    from apps.api.jarvis_api.services.conflict_daemon import build_conflict_surface
    return build_conflict_surface()


@router.get("/reflection-cycle")
def mc_reflection_cycle() -> dict:
    """Return Jarvis's latest pure experience reflection."""
    from apps.api.jarvis_api.services.reflection_cycle_daemon import build_reflection_surface
    return build_reflection_surface()


```

- [ ] **Step 4: Verify Python syntax**

```bash
conda activate ai && python -m compileall core/eventbus/events.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
```

Expected: `Compiling ... ok` for all three files.

- [ ] **Step 5: Commit**

```bash
git add core/eventbus/events.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
git commit -m "feat: wire conflict and reflection daemons into eventbus, heartbeat, and MC endpoints"
```

---

## Task 4: Frontend — adapters.js + LivingMindTab

**Files:**
- Modify: `apps/ui/src/lib/adapters.js`
- Modify: `apps/ui/src/components/mission-control/LivingMindTab.jsx`

- [ ] **Step 1: Add normalize functions to adapters.js**

In `apps/ui/src/lib/adapters.js`, after `normalizeThoughtProposals` (search for `function normalizeThoughtProposals`), add:

```javascript
function normalizeConflictSignal(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    lastConflict: raw.last_conflict || '',
    conflictType: raw.conflict_type || '',
    generatedAt: raw.generated_at || '',
  }
}

function normalizeReflectionCycle(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    latestReflection: raw.latest_reflection || '',
    reflectionBuffer: Array.isArray(raw.reflection_buffer) ? raw.reflection_buffer : [],
    reflectionCount: raw.reflection_count ?? 0,
    lastGeneratedAt: raw.last_generated_at || '',
  }
}
```

- [ ] **Step 2: Add fetches and return fields in adapters.js**

Find the Promise.all destructuring that ends with `thoughtProposalsPayload`. Add `conflictSignalPayload` and `reflectionCyclePayload` at the end of both the destructuring line and the fetch array:

Old destructuring end:
```javascript
    const [..., thoughtProposalsPayload] = await Promise.all([
      ...
      requestJson('/mc/thought-proposals').catch(() => null),
    ])
```

New:
```javascript
    const [..., thoughtProposalsPayload, conflictSignalPayload, reflectionCyclePayload] = await Promise.all([
      ...
      requestJson('/mc/thought-proposals').catch(() => null),
      requestJson('/mc/conflict-signal').catch(() => null),
      requestJson('/mc/reflection-cycle').catch(() => null),
    ])
```

In the return object, after `thoughtProposals: normalizeThoughtProposals(...)`, add:
```javascript
      conflictSignal: normalizeConflictSignal(conflictSignalPayload || null),
      reflectionCycle: normalizeReflectionCycle(reflectionCyclePayload || null),
```

- [ ] **Step 3: Add consts, nav items, and panels in LivingMindTab.jsx**

**a) Add imports** — `Swords` (conflict) and `Eye` (reflection) from lucide-react. Find the import line at the top:

```javascript
import { useState } from 'react'
import { ChevronRight, Cpu, Activity, Moon, Sparkles, Heart, Brain, Network, Wand2, Users, Map, Lightbulb, GraduationCap, TrendingUp, Zap, Ghost, Swords, Eye } from 'lucide-react'
```

**b) Add consts** after `hasThoughtStream`:

```javascript
  const conflictSignal = data?.conflictSignal || null
  const hasConflictSignal = Boolean(conflictSignal?.lastConflict)
  const reflectionCycle = data?.reflectionCycle || null
  const hasReflectionCycle = Boolean(reflectionCycle?.latestReflection)
```

**c) Add nav items** — in the `navItems` array after the Tankestrøm entry:

```javascript
    { id: 'conflict-signal', targetId: 'living-mind-conflict-signal', label: 'Konflikt', icon: Swords, active: hasConflictSignal, status: conflictSignal?.conflictType, statusLabel: conflictSignal?.conflictType || 'ingen' },
    { id: 'reflection-cycle', targetId: 'living-mind-reflection-cycle', label: 'Refleksion', icon: Eye, active: hasReflectionCycle, status: null, statusLabel: `${reflectionCycle?.reflectionCount ?? 0} cyklusser` },
```

**d) Add panels** — after the Tankestrøm panel's closing `</section>` and before `{/* ─── Heartbeat Section ─── */}`, add:

```jsx
      {hasConflictSignal ? (
      <section className="mc-section-grid">
        <article id="living-mind-conflict-signal" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/conflict-signal',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cooldown 10min',
        })}>
          <div className="panel-header">
            <div>
              <h3>Indre konflikt</h3>
              <p className="muted">{conflictSignal.conflictType || 'uspecificeret'}</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {conflictSignal.lastConflict}
          </blockquote>
          {conflictSignal.generatedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${conflictSignal.generatedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasReflectionCycle ? (
      <section className="mc-section-grid">
        <article id="living-mind-reflection-cycle" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/reflection-cycle',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 10min',
        })}>
          <div className="panel-header">
            <div>
              <h3>Refleksion</h3>
              <p className="muted">Hvad oplever Jarvis lige nu</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 16px', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {reflectionCycle.latestReflection}
          </blockquote>
          {reflectionCycle.reflectionBuffer.length > 1 && (
            <details>
              <summary className="muted" style={{ cursor: 'pointer', fontSize: 12 }}>Seneste {reflectionCycle.reflectionBuffer.length} refleksioner</summary>
              <ol style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                {reflectionCycle.reflectionBuffer.map((r, i) => (
                  <li key={i} style={{ fontSize: 12, marginBottom: 4, color: 'var(--text-2)', fontStyle: 'italic' }}>{r}</li>
                ))}
              </ol>
            </details>
          )}
          {reflectionCycle.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${reflectionCycle.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}
```

- [ ] **Step 4: Run full test suite**

```bash
conda activate ai && pytest tests/test_conflict_daemon.py tests/test_reflection_cycle_daemon.py -v
```

Expected: 13/13 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/lib/adapters.js apps/ui/src/components/mission-control/LivingMindTab.jsx
git commit -m "feat: add Konflikt and Refleksion panels to LivingMindTab"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|-------------|------|
| Conflict detection: energy_impulse rule | Task 1 |
| Conflict detection: mode_thought rule | Task 1 |
| Conflict detection: surprise_unprocessed rule | Task 1 |
| 10-min cooldown on conflict | Task 1 |
| First-person LLM formulation of conflict | Task 1 |
| `insert_private_brain_record` + eventbus `conflict.detected` | Task 1 |
| `build_conflict_surface()` | Task 1 |
| 10-min cadence reflection cycle | Task 2 |
| Full signal snapshot as reflection context | Task 2 |
| Rolling buffer max 10 | Task 2 |
| `insert_private_brain_record` + eventbus `reflection.generated` | Task 2 |
| `build_reflection_surface()` | Task 2 |
| `"conflict"` + `"reflection"` in ALLOWED_EVENT_FAMILIES | Task 3 |
| Heartbeat injection for both daemons | Task 3 |
| `/mc/conflict-signal` + `/mc/reflection-cycle` endpoints | Task 3 |
| adapters.js normalize + fetch + return | Task 4 |
| LivingMindTab: Konflikt nav item + panel | Task 4 |
| LivingMindTab: Refleksion nav item + panel with buffer | Task 4 |

**Placeholder scan:** Ingen. Al kode komplet.

**Type consistency:** `build_conflict_surface()` returnerer `last_conflict` / `conflict_type` / `generated_at` — matcher `normalizeConflictSignal` i adapters.js. `build_reflection_surface()` returnerer `latest_reflection` / `reflection_buffer` / `reflection_count` / `last_generated_at` — matcher `normalizeReflectionCycle`. Konsistent.
