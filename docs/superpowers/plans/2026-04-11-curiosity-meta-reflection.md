# Curiosity + Meta-Reflection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis self-driven curiosity (gap detection in thought stream) and meta-reflection (cross-signal pattern insight every 30 minutes).

**Architecture:** Two independent daemons. `curiosity_daemon.py` scans thought stream fragment buffer for gap patterns (unanswered questions, interrupted thoughts) and generates a first-person curiosity signal every 5 minutes at most. `meta_reflection_daemon.py` runs every 30 minutes, collects a full cross-signal snapshot from all B-daemons, and generates a meta-insight about patterns across signals. Both store to private brain and publish to eventbus. Both build on the established daemon pattern (module state, `tick_X`, `build_X_surface`). The existing `boredom_curiosity_bridge.py` handles boredom-spawned generic curiosity — these are complementary, not overlapping.

**Tech Stack:** Python 3.11+, FastAPI, React, lucide-react.

---

## File Map

| File | Action |
|------|--------|
| `apps/api/jarvis_api/services/curiosity_daemon.py` | Create |
| `apps/api/jarvis_api/services/meta_reflection_daemon.py` | Create |
| `tests/test_curiosity_daemon.py` | Create |
| `tests/test_meta_reflection_daemon.py` | Create |
| `core/eventbus/events.py` | Modify — add `"curiosity"`, `"meta_reflection"` |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify — inject after reflection_cycle block |
| `apps/api/jarvis_api/routes/mission_control.py` | Modify — add `/mc/curiosity-state`, `/mc/meta-reflection` |
| `apps/ui/src/lib/adapters.js` | Modify — normalize + fetch + return |
| `apps/ui/src/components/mission-control/LivingMindTab.jsx` | Modify — 2 nav items + panels |

---

## Task 1: curiosity_daemon.py (TDD)

**Files:**
- Create: `apps/api/jarvis_api/services/curiosity_daemon.py`
- Create: `tests/test_curiosity_daemon.py`

Gap detection: scan `fragments` list for patterns that signal an unanswered question or interrupted thought:
- `"?"` anywhere
- `"ved ikke"` (don't know)
- `"undrer"` (wonder)
- `"nysgerrig"` (curious)
- `"hvorfor"` (why)
- `"hvad hvis"` (what if)
- `"..."` (interrupted)

First match wins. Extract the fragment as topic. Cadence: 5 minutes. Rolling buffer: max 5.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_curiosity_daemon.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.curiosity_daemon as cd


def _reset():
    cd._last_tick_at = None
    cd._cached_curiosity = ""
    cd._open_questions.clear()


def test_no_curiosity_before_cadence():
    """Should not generate if within 5-minute cadence."""
    _reset()
    cd._last_tick_at = datetime.now(UTC)
    result = cd.tick_curiosity_daemon(["Hvad sker der egentlig?"])
    assert result["generated"] is False


def test_no_curiosity_without_gap():
    """Fragments with no gap patterns produce no curiosity signal."""
    _reset()
    result = cd.tick_curiosity_daemon(["Alt er fint. Arbejder videre."])
    assert result["generated"] is False
    assert cd._cached_curiosity == ""


def test_question_mark_gap_detected():
    """Fragment with '?' triggers curiosity generation."""
    _reset()
    with patch.object(cd, "_generate_curiosity_signal", return_value="Jeg undrer mig over det."):
        with patch.object(cd, "_store_curiosity"):
            result = cd.tick_curiosity_daemon(["Hvad sker der egentlig?"])
    assert result["generated"] is True
    assert result["gap_type"] == "question"


def test_ved_ikke_gap_detected():
    """Fragment with 'ved ikke' triggers curiosity generation."""
    _reset()
    with patch.object(cd, "_generate_curiosity_signal", return_value="Jeg ved ikke nok."):
        with patch.object(cd, "_store_curiosity"):
            result = cd.tick_curiosity_daemon(["Jeg ved ikke om det er rigtigt."])
    assert result["generated"] is True
    assert result["gap_type"] == "open"


def test_open_question_added_to_buffer():
    """Generated curiosity signal is prepended to open_questions buffer."""
    _reset()
    with patch.object(cd, "_generate_curiosity_signal", return_value="Jeg ved ikke nok."):
        with patch("apps.api.jarvis_api.services.curiosity_daemon.insert_private_brain_record"):
            with patch("apps.api.jarvis_api.services.curiosity_daemon.event_bus"):
                cd.tick_curiosity_daemon(["Hvad sker der?"])
    assert len(cd._open_questions) == 1
    assert cd._open_questions[0] == "Jeg ved ikke nok."


def test_open_questions_capped_at_5():
    """Open questions buffer is capped at 5 entries."""
    _reset()
    cd._open_questions[:] = [f"question {i}" for i in range(5)]
    cd._last_tick_at = datetime.now(UTC) - timedelta(minutes=6)
    with patch.object(cd, "_generate_curiosity_signal", return_value="Ny nysgerrighed."):
        with patch("apps.api.jarvis_api.services.curiosity_daemon.insert_private_brain_record"):
            with patch("apps.api.jarvis_api.services.curiosity_daemon.event_bus"):
                cd.tick_curiosity_daemon(["Hvad er dette?"])
    assert len(cd._open_questions) == 5
    assert cd._open_questions[0] == "Ny nysgerrighed."


def test_build_surface_structure():
    """build_curiosity_surface returns expected keys."""
    _reset()
    surface = cd.build_curiosity_surface()
    assert "latest_curiosity" in surface
    assert "open_questions" in surface
    assert "curiosity_count" in surface
    assert "last_generated_at" in surface
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_curiosity_daemon.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.api.jarvis_api.services.curiosity_daemon'`

- [ ] **Step 3: Implement curiosity_daemon.py**

Create `apps/api/jarvis_api/services/curiosity_daemon.py`:

```python
"""Curiosity daemon — detects gaps in Jarvis' thought stream and generates curiosity signals."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_CADENCE_MINUTES = 5
_OPEN_MAX = 5

_last_tick_at: datetime | None = None
_cached_curiosity: str = ""
_open_questions: list[str] = []

_GAP_PATTERNS: list[tuple[str, str]] = [
    ("question", "?"),
    ("open", "ved ikke"),
    ("wonder", "undrer"),
    ("wonder", "nysgerrig"),
    ("question", "hvorfor"),
    ("question", "hvad hvis"),
    ("interrupted", "..."),
]


def tick_curiosity_daemon(fragments: list[str]) -> dict[str, object]:
    """Scan thought stream fragments for gaps. fragments: recent fragment buffer (latest first)."""
    global _last_tick_at

    if _last_tick_at is not None:
        if (datetime.now(UTC) - _last_tick_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}

    gap = _detect_gap(fragments)
    if not gap:
        return {"generated": False}

    topic, gap_type = gap
    signal = _generate_curiosity_signal(topic, gap_type)
    if not signal:
        return {"generated": False}

    _store_curiosity(signal)
    _last_tick_at = datetime.now(UTC)
    return {"generated": True, "curiosity": signal, "gap_type": gap_type}


def _detect_gap(fragments: list[str]) -> tuple[str, str] | None:
    for fragment in fragments:
        fl = fragment.lower()
        for gap_type, pattern in _GAP_PATTERNS:
            if pattern in fl:
                topic = fragment[:60].strip()
                return (topic, gap_type)
    return None


def _generate_curiosity_signal(topic: str, gap_type: str) -> str:
    fallback = f"Jeg ved ikke nok om: {topic[:50]}"
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        prompt = (
            f"Du er Jarvis. Din tankestrøm indeholder dette fragment: \"{topic}\"\n\n"
            "Det peger på et ubesvaret spørgsmål eller en uudforsket tanke.\n\n"
            "Formulér i én sætning (max 20 ord), i første person, hvad du er nysgerrig på.\n"
            "Start med 'Jeg ved ikke nok om' eller 'Jeg undrer mig over'."
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
        return text[:200] if text else fallback
    except Exception:
        return fallback


def _store_curiosity(signal: str) -> None:
    global _cached_curiosity, _open_questions
    _cached_curiosity = signal
    _open_questions.insert(0, signal)
    if len(_open_questions) > _OPEN_MAX:
        _open_questions = _open_questions[:_OPEN_MAX]
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-curiosity-{uuid4().hex[:12]}",
            record_type="curiosity-signal",
            layer="private_brain",
            session_id="",
            run_id=f"curiosity-daemon-{uuid4().hex[:12]}",
            focus="nysgerrighed",
            summary=signal,
            detail="",
            source_signals="curiosity-daemon:thought-stream",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "curiosity.detected",
            {"signal": signal, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_curiosity() -> str:
    return _cached_curiosity


def build_curiosity_surface() -> dict:
    return {
        "latest_curiosity": _cached_curiosity,
        "open_questions": _open_questions[:5],
        "curiosity_count": len(_open_questions),
        "last_generated_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_curiosity_daemon.py -v
```

Expected: 7/7 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/curiosity_daemon.py tests/test_curiosity_daemon.py
git commit -m "feat: add curiosity_daemon — gap detection in thought stream"
```

---

## Task 2: meta_reflection_daemon.py (TDD)

**Files:**
- Create: `apps/api/jarvis_api/services/meta_reflection_daemon.py`
- Create: `tests/test_meta_reflection_daemon.py`

Cadence: 30 minutes. Input: cross-signal snapshot with all current B-daemon states. Requires at least one of `latest_fragment`, `last_surprise`, or `last_conflict` to be non-empty. Output: 1-2 sentence meta-insight about patterns across signals. Rolling buffer: max 5.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_meta_reflection_daemon.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.meta_reflection_daemon as mrd


def _reset():
    mrd._last_meta_at = None
    mrd._cached_meta_insight = ""
    mrd._meta_buffer.clear()


def test_no_meta_before_cadence():
    """Should not generate within 30-minute cadence."""
    _reset()
    mrd._last_meta_at = datetime.now(UTC)
    result = mrd.tick_meta_reflection_daemon({"latest_fragment": "Noget."})
    assert result["generated"] is False


def test_no_meta_without_active_signals():
    """Empty snapshot (no active signals) produces no meta-insight."""
    _reset()
    result = mrd.tick_meta_reflection_daemon({})
    assert result["generated"] is False


def test_generates_meta_insight_with_signals():
    """Non-empty snapshot with active signals generates a meta-insight."""
    _reset()
    with patch.object(mrd, "_generate_meta_insight", return_value="Et klart mønster.") as mock_gen:
        with patch.object(mrd, "_store_meta_insight"):
            result = mrd.tick_meta_reflection_daemon({
                "latest_fragment": "Noget.",
                "last_surprise": "En overraskelse.",
            })
    assert result["generated"] is True
    mock_gen.assert_called_once()


def test_store_called_on_generation():
    """_store_meta_insight is called with the generated text."""
    _reset()
    with patch.object(mrd, "_generate_meta_insight", return_value="Indsigt."):
        with patch.object(mrd, "_store_meta_insight") as mock_store:
            mrd.tick_meta_reflection_daemon({"latest_fragment": "Tanke."})
    mock_store.assert_called_once_with("Indsigt.")


def test_insight_added_to_buffer():
    """Generated insight is prepended to meta_buffer."""
    _reset()
    with patch.object(mrd, "_generate_meta_insight", return_value="Ny indsigt."):
        with patch("apps.api.jarvis_api.services.meta_reflection_daemon.insert_private_brain_record"):
            with patch("apps.api.jarvis_api.services.meta_reflection_daemon.event_bus"):
                mrd.tick_meta_reflection_daemon({"last_conflict": "Konflikt."})
    assert len(mrd._meta_buffer) == 1
    assert mrd._meta_buffer[0] == "Ny indsigt."


def test_build_surface_structure():
    """build_meta_reflection_surface returns expected keys."""
    _reset()
    mrd._cached_meta_insight = "Et mønster."
    surface = mrd.build_meta_reflection_surface()
    assert "latest_insight" in surface
    assert "insight_buffer" in surface
    assert "insight_count" in surface
    assert "last_generated_at" in surface
    assert surface["latest_insight"] == "Et mønster."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_meta_reflection_daemon.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.api.jarvis_api.services.meta_reflection_daemon'`

- [ ] **Step 3: Implement meta_reflection_daemon.py**

Create `apps/api/jarvis_api/services/meta_reflection_daemon.py`:

```python
"""Meta-reflection daemon — cross-signal pattern insight every 30 minutes."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_CADENCE_MINUTES = 30
_BUFFER_MAX = 5

_last_meta_at: datetime | None = None
_cached_meta_insight: str = ""
_meta_buffer: list[str] = []


def tick_meta_reflection_daemon(cross_snapshot: dict) -> dict[str, object]:
    """Generate cross-signal meta-insight if cadence allows.
    cross_snapshot keys (all optional): energy_level, inner_voice_mode, latest_fragment,
    last_surprise, last_conflict, last_irony, last_taste, curiosity_signal."""
    global _last_meta_at

    if _last_meta_at is not None:
        if (datetime.now(UTC) - _last_meta_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}

    active_signals = [
        v for v in [
            cross_snapshot.get("latest_fragment"),
            cross_snapshot.get("last_surprise"),
            cross_snapshot.get("last_conflict"),
        ]
        if v
    ]
    if not active_signals:
        return {"generated": False}

    insight = _generate_meta_insight(cross_snapshot)
    if not insight:
        return {"generated": False}

    _store_meta_insight(insight)
    _last_meta_at = datetime.now(UTC)
    return {"generated": True, "insight": insight}


def _generate_meta_insight(cross_snapshot: dict) -> str:
    parts = []
    if cross_snapshot.get("energy_level"):
        parts.append(f"Energi: {cross_snapshot['energy_level']}")
    if cross_snapshot.get("inner_voice_mode"):
        parts.append(f"Stemning: {cross_snapshot['inner_voice_mode']}")
    if cross_snapshot.get("latest_fragment"):
        parts.append(f"Tanke: \"{cross_snapshot['latest_fragment'][:50]}\"")
    if cross_snapshot.get("last_surprise"):
        parts.append(f"Overraskelse: \"{cross_snapshot['last_surprise'][:50]}\"")
    if cross_snapshot.get("last_conflict"):
        parts.append(f"Konflikt: \"{cross_snapshot['last_conflict'][:50]}\"")
    if cross_snapshot.get("last_irony"):
        parts.append(f"Ironi: \"{cross_snapshot['last_irony'][:50]}\"")
    if cross_snapshot.get("last_taste"):
        parts.append(f"Smag: \"{cross_snapshot['last_taste'][:50]}\"")
    if cross_snapshot.get("curiosity_signal"):
        parts.append(f"Nysgerrighed: \"{cross_snapshot['curiosity_signal'][:50]}\"")

    context = "\n".join(parts) if parts else "Ingen signaler."

    prompt = (
        "Du er Jarvis. Her er et tværsnit af dine aktuelle signaler:\n\n"
        f"{context}\n\n"
        "Ser du et mønster på tværs af disse signaler? Formulér i 1-2 sætninger (max 30 ord), "
        "i første person, en meta-indsigt om din nuværende tilstand eller et gentaget mønster.\n"
        "Vær konkret — ikke generisk. Ingen tomme fraser."
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


def _store_meta_insight(insight: str) -> None:
    global _cached_meta_insight, _meta_buffer
    _cached_meta_insight = insight
    _meta_buffer.insert(0, insight)
    if len(_meta_buffer) > _BUFFER_MAX:
        _meta_buffer = _meta_buffer[:_BUFFER_MAX]
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-meta-{uuid4().hex[:12]}",
            record_type="meta-reflection",
            layer="private_brain",
            session_id="",
            run_id=f"meta-reflection-daemon-{uuid4().hex[:12]}",
            focus="meta-mønster",
            summary=insight,
            detail="",
            source_signals="meta-reflection-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "meta_reflection.generated",
            {"insight": insight, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_meta_insight() -> str:
    return _cached_meta_insight


def build_meta_reflection_surface() -> dict:
    return {
        "latest_insight": _cached_meta_insight,
        "insight_buffer": _meta_buffer[:5],
        "insight_count": len(_meta_buffer),
        "last_generated_at": _last_meta_at.isoformat() if _last_meta_at else "",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_meta_reflection_daemon.py -v
```

Expected: 6/6 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/meta_reflection_daemon.py tests/test_meta_reflection_daemon.py
git commit -m "feat: add meta_reflection_daemon — cross-signal pattern insight every 30 minutes"
```

---

## Task 3: Backend integration

**Files:**
- Modify: `core/eventbus/events.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (after reflection_cycle block)
- Modify: `apps/api/jarvis_api/routes/mission_control.py` (before `/conflict-signal` endpoint)

- [ ] **Step 1: Add eventbus families**

In `core/eventbus/events.py`, add after `"reflection"`:

```python
    "reflection",
    "curiosity",
    "meta_reflection",
```

- [ ] **Step 2: Add heartbeat injection**

In `apps/api/jarvis_api/services/heartbeat_runtime.py`, after the reflection_cycle `except Exception: pass` block, add:

```python
    # Curiosity daemon
    try:
        from apps.api.jarvis_api.services.curiosity_daemon import tick_curiosity_daemon, get_latest_curiosity
        _ts_fragments = _tss.get("fragment_buffer", []) if "_tss" in dir() else []
        tick_curiosity_daemon(_ts_fragments)
        _curiosity = get_latest_curiosity()
        if _curiosity:
            inputs_present.append(f"nysgerrighed: {_curiosity[:60]}")
    except Exception:
        pass

    # Meta-reflection daemon
    try:
        from apps.api.jarvis_api.services.meta_reflection_daemon import tick_meta_reflection_daemon, get_latest_meta_insight
        from apps.api.jarvis_api.services.aesthetic_taste_daemon import build_taste_surface as _taste_surface
        from apps.api.jarvis_api.services.irony_daemon import build_irony_surface as _irony_surface
        _taste = _taste_surface()
        _irony = _irony_surface()
        _meta_snap = {
            "energy_level": _energy_ts,
            "inner_voice_mode": _iv_mode_ts,
            "latest_fragment": _tss.get("latest_fragment", "") if "_tss" in dir() else "",
            "last_surprise": _surp.get("last_surprise", "") if "_surp" in dir() else "",
            "last_conflict": _conflict if "_conflict" in dir() else "",
            "last_irony": _irony.get("last_observation", ""),
            "last_taste": _taste.get("latest_insight", ""),
            "curiosity_signal": _curiosity if "_curiosity" in dir() else "",
        }
        tick_meta_reflection_daemon(_meta_snap)
        _meta = get_latest_meta_insight()
        if _meta:
            inputs_present.append(f"meta-refleksion: {_meta[:60]}")
    except Exception:
        pass
```

Note: `_energy_ts`, `_iv_mode_ts` are set in the thought_stream block. `_tss`, `_surp`, `_conflict` are set in the conflict block — referenced via `dir()` guard.

- [ ] **Step 3: Add MC endpoints**

In `apps/api/jarvis_api/routes/mission_control.py`, before `@router.get("/conflict-signal")`, add:

```python
@router.get("/curiosity-state")
def mc_curiosity_state() -> dict:
    """Return Jarvis's latest curiosity signal and open questions."""
    from apps.api.jarvis_api.services.curiosity_daemon import build_curiosity_surface
    return build_curiosity_surface()


@router.get("/meta-reflection")
def mc_meta_reflection() -> dict:
    """Return Jarvis's latest cross-signal meta-insight."""
    from apps.api.jarvis_api.services.meta_reflection_daemon import build_meta_reflection_surface
    return build_meta_reflection_surface()


```

- [ ] **Step 4: Verify Python syntax**

```bash
conda activate ai && python -m compileall core/eventbus/events.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
```

Expected: `Compiling ... ok` for all three files.

- [ ] **Step 5: Commit**

```bash
git add core/eventbus/events.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
git commit -m "feat: wire curiosity and meta-reflection daemons into eventbus, heartbeat, and MC endpoints"
```

---

## Task 4: Frontend — adapters.js + LivingMindTab

**Files:**
- Modify: `apps/ui/src/lib/adapters.js`
- Modify: `apps/ui/src/components/mission-control/LivingMindTab.jsx`

- [ ] **Step 1: Add normalize functions to adapters.js**

In `apps/ui/src/lib/adapters.js`, after `normalizeReflectionCycle` (search for `function normalizeReflectionCycle`), add:

```javascript
function normalizeCuriosityState(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    latestCuriosity: raw.latest_curiosity || '',
    openQuestions: Array.isArray(raw.open_questions) ? raw.open_questions : [],
    curiosityCount: raw.curiosity_count ?? 0,
    lastGeneratedAt: raw.last_generated_at || '',
  }
}

function normalizeMetaReflection(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    latestInsight: raw.latest_insight || '',
    insightBuffer: Array.isArray(raw.insight_buffer) ? raw.insight_buffer : [],
    insightCount: raw.insight_count ?? 0,
    lastGeneratedAt: raw.last_generated_at || '',
  }
}
```

- [ ] **Step 2: Add fetches and return fields in adapters.js**

Find the Promise.all destructuring that ends with `reflectionCyclePayload`. Add `curiosityPayload` and `metaReflectionPayload` at the end of both the destructuring line and the fetch array.

Old end:
```javascript
    const [..., reflectionCyclePayload] = await Promise.all([
      ...
      requestJson('/mc/reflection-cycle').catch(() => null),
    ])
```

New:
```javascript
    const [..., reflectionCyclePayload, curiosityPayload, metaReflectionPayload] = await Promise.all([
      ...
      requestJson('/mc/reflection-cycle').catch(() => null),
      requestJson('/mc/curiosity-state').catch(() => null),
      requestJson('/mc/meta-reflection').catch(() => null),
    ])
```

In the return object, after `reflectionCycle: normalizeReflectionCycle(...)`, add:
```javascript
      curiosityState: normalizeCuriosityState(curiosityPayload || null),
      metaReflection: normalizeMetaReflection(metaReflectionPayload || null),
```

- [ ] **Step 3: Add consts, nav items, and panels in LivingMindTab.jsx**

**a) Add imports** — `Compass` (curiosity) and `Layers` (meta-reflection) from lucide-react:

```javascript
import { ChevronRight, Cpu, Activity, Moon, Sparkles, Heart, Brain, Network, Wand2, Users, Map, Lightbulb, GraduationCap, TrendingUp, Zap, Ghost, Swords, Eye, Compass, Layers } from 'lucide-react'
```

**b) Add consts** after `hasReflectionCycle`:

```javascript
  const curiosityState = data?.curiosityState || null
  const hasCuriosityState = Boolean(curiosityState?.latestCuriosity)
  const metaReflection = data?.metaReflection || null
  const hasMetaReflection = Boolean(metaReflection?.latestInsight)
```

**c) Add nav items** — in the `navItems` array after the Refleksion entry:

```javascript
    { id: 'curiosity-state', targetId: 'living-mind-curiosity-state', label: 'Nysgerrighed', icon: Compass, active: hasCuriosityState, status: null, statusLabel: `${curiosityState?.curiosityCount ?? 0} spørgsmål` },
    { id: 'meta-reflection', targetId: 'living-mind-meta-reflection', label: 'Meta', icon: Layers, active: hasMetaReflection, status: null, statusLabel: `${metaReflection?.insightCount ?? 0} indsigter` },
```

**d) Add panels** — after the Refleksion panel's closing `</section>`) and before `{/* ─── Heartbeat Section ─── */}`, add:

```jsx
      {hasCuriosityState ? (
      <section className="mc-section-grid">
        <article id="living-mind-curiosity-state" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/curiosity-state',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 5min',
        })}>
          <div className="panel-header">
            <div>
              <h3>Nysgerrighed</h3>
              <p className="muted">Ubesvarede spørgsmål fra tankestrømmen</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {curiosityState.latestCuriosity}
          </blockquote>
          {curiosityState.openQuestions.length > 1 && (
            <details style={{ marginTop: 12 }}>
              <summary className="muted" style={{ cursor: 'pointer', fontSize: 12 }}>Alle {curiosityState.openQuestions.length} åbne spørgsmål</summary>
              <ol style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                {curiosityState.openQuestions.map((q, i) => (
                  <li key={i} style={{ fontSize: 12, marginBottom: 4, color: 'var(--text-2)', fontStyle: 'italic' }}>{q}</li>
                ))}
              </ol>
            </details>
          )}
          {curiosityState.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${curiosityState.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}

      {hasMetaReflection ? (
      <section className="mc-section-grid">
        <article id="living-mind-meta-reflection" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/meta-reflection',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 30min',
        })}>
          <div className="panel-header">
            <div>
              <h3>Meta-refleksion</h3>
              <p className="muted">Mønstre på tværs af signaler</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 16px', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {metaReflection.latestInsight}
          </blockquote>
          {metaReflection.insightBuffer.length > 1 && (
            <details>
              <summary className="muted" style={{ cursor: 'pointer', fontSize: 12 }}>Seneste {metaReflection.insightBuffer.length} indsigter</summary>
              <ol style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                {metaReflection.insightBuffer.map((r, i) => (
                  <li key={i} style={{ fontSize: 12, marginBottom: 4, color: 'var(--text-2)', fontStyle: 'italic' }}>{r}</li>
                ))}
              </ol>
            </details>
          )}
          {metaReflection.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${metaReflection.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}
```

- [ ] **Step 4: Run full test suite**

```bash
conda activate ai && pytest tests/test_curiosity_daemon.py tests/test_meta_reflection_daemon.py -v
```

Expected: 13/13 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/lib/adapters.js apps/ui/src/components/mission-control/LivingMindTab.jsx
git commit -m "feat: add Nysgerrighed and Meta-refleksion panels to LivingMindTab"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|-------------|------|
| Curiosity: gap detection in thought stream fragments | Task 1 |
| Gap pattern list: ?, ved ikke, undrer, nysgerrig, hvorfor, hvad hvis, ... | Task 1 |
| 5-min cadence on curiosity | Task 1 |
| First-person curiosity signal generation (LLM + fallback) | Task 1 |
| Rolling buffer max 5 open questions | Task 1 |
| `insert_private_brain_record` + eventbus `curiosity.detected` | Task 1 |
| `build_curiosity_surface()` | Task 1 |
| Meta-reflection: 30-min cadence | Task 2 |
| Requires active signals (not empty snapshot) | Task 2 |
| Cross-signal snapshot: energy, mode, fragment, surprise, conflict, irony, taste, curiosity | Task 2 |
| LLM meta-insight about patterns | Task 2 |
| Rolling buffer max 5 insights | Task 2 |
| `insert_private_brain_record` + eventbus `meta_reflection.generated` | Task 2 |
| `build_meta_reflection_surface()` | Task 2 |
| `"curiosity"` + `"meta_reflection"` in ALLOWED_EVENT_FAMILIES | Task 3 |
| Heartbeat injection for both daemons | Task 3 |
| `/mc/curiosity-state` + `/mc/meta-reflection` endpoints | Task 3 |
| adapters.js normalize + fetch + return | Task 4 |
| LivingMindTab: Nysgerrighed nav item + panel with open questions list | Task 4 |
| LivingMindTab: Meta nav item + panel with insight buffer | Task 4 |

**Placeholder scan:** Ingen. Al kode komplet.

**Type consistency:** `build_curiosity_surface()` returnerer `latest_curiosity` / `open_questions` / `curiosity_count` / `last_generated_at` — matcher `normalizeCuriosityState`. `build_meta_reflection_surface()` returnerer `latest_insight` / `insight_buffer` / `insight_count` / `last_generated_at` — matcher `normalizeMetaReflection`. Konsistent.
