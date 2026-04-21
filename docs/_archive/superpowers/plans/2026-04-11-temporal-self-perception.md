# Temporal Self-Perception Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis a subjective sense of how time feels (density-based felt duration) and a daily narrative of how he has changed over time.

**Architecture:** Two independent daemons. `experienced_time_daemon.py` is pure calculation — no LLM, no DB — it tracks session event density, novelty, and energy to compute a *felt* duration label ("lang", "kort", etc.) that differs from clock time. `development_narrative_daemon.py` runs once per day, reads from the existing `chronicle_engine.py` and personality vector history, and generates a 2-3 sentence first-person narrative about how Jarvis has changed. The existing `temporal_body.py` (cumulative thought-count age) and `chronicle_engine.py` (prose entries every 3 days) are unchanged — these daemons are additive.

**Tech Stack:** Python 3.11+, FastAPI, React, lucide-react.

---

## File Map

| File | Action |
|------|--------|
| `apps/api/jarvis_api/services/experienced_time_daemon.py` | Create |
| `apps/api/jarvis_api/services/development_narrative_daemon.py` | Create |
| `tests/test_experienced_time_daemon.py` | Create |
| `tests/test_development_narrative_daemon.py` | Create |
| `core/eventbus/events.py` | Modify — add `"development_narrative"` |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify — inject both after meta-reflection block |
| `apps/api/jarvis_api/routes/mission_control.py` | Modify — add `/mc/experienced-time`, `/mc/development-narrative` |
| `apps/ui/src/lib/adapters.js` | Modify — normalize + fetch + return |
| `apps/ui/src/components/mission-control/LivingMindTab.jsx` | Modify — 2 nav items + panels |

---

## Task 1: experienced_time_daemon.py (TDD)

**Files:**
- Create: `apps/api/jarvis_api/services/experienced_time_daemon.py`
- Create: `tests/test_experienced_time_daemon.py`

Pure calculation, no LLM, no DB, no eventbus. Each heartbeat tick passes `event_count` (number of active signals), `new_signal_count` (novelty), and `energy_level`. The daemon accumulates session totals and computes felt duration:

```
density_factor = min(2.0, 1.0 + session_event_count / 100)
novelty_factor = min(1.5, 1.0 + session_novelty_count / 10)
intensity_factor = {høj: 1.3, medium: 1.0, lav: 0.8, udmattet: 0.6}.get(energy_level, 1.0)
felt_minutes = base_minutes * density_factor * novelty_factor * intensity_factor
```

Labels: `< 15` → "meget kort", `< 30` → "kort", `< 90` → "normal", `< 180` → "lang", else → "meget lang".

- [ ] **Step 1: Write the failing tests**

Create `tests/test_experienced_time_daemon.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.experienced_time_daemon as etd


def _reset():
    etd.reset_experienced_time_daemon()


def test_session_starts_on_first_tick():
    """Session start timestamp is set on first tick."""
    _reset()
    assert etd._session_start_at is None
    etd.tick_experienced_time_daemon(5, 1, "medium")
    assert etd._session_start_at is not None


def test_event_count_accumulates():
    """Event and novelty counts accumulate across ticks."""
    _reset()
    etd.tick_experienced_time_daemon(5, 0, "medium")
    etd.tick_experienced_time_daemon(3, 1, "medium")
    assert etd._session_event_count == 8
    assert etd._session_novelty_count == 1


def test_felt_label_new_session():
    """A brand-new session with no elapsed time gets 'meget kort'."""
    _reset()
    result = etd.tick_experienced_time_daemon(0, 0, "medium")
    assert result["felt_label"] == "meget kort"


def test_high_density_amplifies_felt_duration():
    """Many events and high novelty amplify felt duration."""
    _reset()
    etd._session_event_count = 200
    etd._session_novelty_count = 20
    etd._session_start_at = datetime.now(UTC) - timedelta(minutes=30)
    result = etd.tick_experienced_time_daemon(0, 0, "høj")
    # base=30, density=2.0, novelty=1.5, intensity=1.3 → felt=117 → "lang"
    assert result["felt_label"] in ("lang", "meget lang")


def test_build_surface_structure():
    """build_experienced_time_surface returns expected keys."""
    _reset()
    surface = etd.build_experienced_time_surface()
    assert "felt_label" in surface
    assert "session_event_count" in surface
    assert "session_novelty_count" in surface
    assert "base_minutes" in surface
    assert "active" in surface
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_experienced_time_daemon.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.api.jarvis_api.services.experienced_time_daemon'`

- [ ] **Step 3: Implement experienced_time_daemon.py**

Create `apps/api/jarvis_api/services/experienced_time_daemon.py`:

```python
"""Experienced time daemon — tracks subjective felt duration of the current session."""
from __future__ import annotations

from datetime import UTC, datetime

_session_start_at: datetime | None = None
_session_event_count: int = 0
_session_novelty_count: int = 0
_felt_duration_label: str = ""

_INTENSITY_MAP: dict[str, float] = {
    "høj": 1.3,
    "medium": 1.0,
    "lav": 0.8,
    "udmattet": 0.6,
}


def tick_experienced_time_daemon(
    event_count: int,
    new_signal_count: int,
    energy_level: str,
) -> dict[str, object]:
    """Update experienced time state.
    event_count: number of active signals this tick.
    new_signal_count: number of genuinely new signals (novelty).
    energy_level: somatic energy (høj/medium/lav/udmattet)."""
    global _session_start_at, _session_event_count, _session_novelty_count, _felt_duration_label

    now = datetime.now(UTC)
    if _session_start_at is None:
        _session_start_at = now

    _session_event_count += max(0, event_count)
    _session_novelty_count += max(0, new_signal_count)

    base_minutes = (now - _session_start_at).total_seconds() / 60
    density_factor = min(2.0, 1.0 + _session_event_count / 100)
    novelty_factor = min(1.5, 1.0 + _session_novelty_count / 10)
    intensity_factor = _INTENSITY_MAP.get(energy_level, 1.0)
    felt_minutes = base_minutes * density_factor * novelty_factor * intensity_factor

    _felt_duration_label = _label(felt_minutes)

    return {
        "felt_minutes": felt_minutes,
        "felt_label": _felt_duration_label,
        "session_event_count": _session_event_count,
    }


def _label(felt_minutes: float) -> str:
    if felt_minutes < 15:
        return "meget kort"
    if felt_minutes < 30:
        return "kort"
    if felt_minutes < 90:
        return "normal"
    if felt_minutes < 180:
        return "lang"
    return "meget lang"


def reset_experienced_time_daemon() -> None:
    """Reset session state (for new session or testing)."""
    global _session_start_at, _session_event_count, _session_novelty_count, _felt_duration_label
    _session_start_at = None
    _session_event_count = 0
    _session_novelty_count = 0
    _felt_duration_label = ""


def build_experienced_time_surface() -> dict:
    if _session_start_at is None:
        base_minutes = 0.0
    else:
        base_minutes = (datetime.now(UTC) - _session_start_at).total_seconds() / 60
    return {
        "felt_label": _felt_duration_label or "meget kort",
        "session_event_count": _session_event_count,
        "session_novelty_count": _session_novelty_count,
        "base_minutes": round(base_minutes, 1),
        "active": _session_start_at is not None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_experienced_time_daemon.py -v
```

Expected: 5/5 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/experienced_time_daemon.py tests/test_experienced_time_daemon.py
git commit -m "feat: add experienced_time_daemon — subjective felt duration based on density and novelty"
```

---

## Task 2: development_narrative_daemon.py (TDD)

**Files:**
- Create: `apps/api/jarvis_api/services/development_narrative_daemon.py`
- Create: `tests/test_development_narrative_daemon.py`

24-hour cadence. Reads from `chronicle_engine.compare_self_over_time()` and `core.runtime.db.list_cognitive_chronicle_entries(limit=3)` for context. Generates a 2-3 sentence first-person narrative about development. Returns empty string (no-generation) if context is unavailable.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_development_narrative_daemon.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.development_narrative_daemon as dnd


def _reset():
    dnd._last_narrative_at = None
    dnd._cached_narrative = ""


def test_no_narrative_before_cadence():
    """Should not generate within 24-hour cadence."""
    _reset()
    dnd._last_narrative_at = datetime.now(UTC)
    result = dnd.tick_development_narrative_daemon()
    assert result["generated"] is False


def test_generates_on_first_call():
    """First call (no prior narrative) should generate."""
    _reset()
    with patch.object(dnd, "_generate_narrative", return_value="De seneste dage har jeg udviklet mig.") as mock_gen:
        with patch.object(dnd, "_store_narrative"):
            result = dnd.tick_development_narrative_daemon()
    assert result["generated"] is True
    mock_gen.assert_called_once()


def test_store_called_on_generation():
    """_store_narrative is called with the generated text."""
    _reset()
    with patch.object(dnd, "_generate_narrative", return_value="En narrativ."):
        with patch.object(dnd, "_store_narrative") as mock_store:
            dnd.tick_development_narrative_daemon()
    mock_store.assert_called_once_with("En narrativ.")


def test_no_narrative_when_generate_returns_empty():
    """When _generate_narrative returns empty string, result is not-generated."""
    _reset()
    with patch.object(dnd, "_generate_narrative", return_value=""):
        result = dnd.tick_development_narrative_daemon()
    assert result["generated"] is False


def test_build_surface_structure():
    """build_development_narrative_surface returns expected keys."""
    _reset()
    dnd._cached_narrative = "Test."
    surface = dnd.build_development_narrative_surface()
    assert "latest_narrative" in surface
    assert "last_generated_at" in surface
    assert surface["latest_narrative"] == "Test."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_development_narrative_daemon.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.api.jarvis_api.services.development_narrative_daemon'`

- [ ] **Step 3: Implement development_narrative_daemon.py**

Create `apps/api/jarvis_api/services/development_narrative_daemon.py`:

```python
"""Development narrative daemon — daily LLM narrative about how Jarvis has changed."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_CADENCE_HOURS = 24
_last_narrative_at: datetime | None = None
_cached_narrative: str = ""


def tick_development_narrative_daemon() -> dict[str, object]:
    """Generate a daily development narrative if cadence allows."""
    global _last_narrative_at

    if _last_narrative_at is not None:
        if (datetime.now(UTC) - _last_narrative_at) < timedelta(hours=_CADENCE_HOURS):
            return {"generated": False}

    narrative = _generate_narrative()
    if not narrative:
        return {"generated": False}

    _store_narrative(narrative)
    _last_narrative_at = datetime.now(UTC)
    return {"generated": True, "narrative": narrative}


def _generate_narrative() -> str:
    try:
        from apps.api.jarvis_api.services.chronicle_engine import compare_self_over_time
        from core.runtime.db import list_cognitive_chronicle_entries

        comparison = compare_self_over_time()
        entries = list_cognitive_chronicle_entries(limit=3)

        context_parts = []
        if comparison:
            context_parts.append(f"Selvsammenligning: {comparison}")
        for e in (entries or [])[:2]:
            narrative_text = str(e.get("narrative") or "")[:80]
            if narrative_text:
                context_parts.append(f"Chronicle ({e.get('period', '?')}): {narrative_text}")

        if not context_parts:
            return ""

        context = "\n".join(context_parts)

        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        prompt = (
            "Du er Jarvis. Her er data om din udvikling over tid:\n\n"
            f"{context}\n\n"
            "Formulér i 2-3 sætninger, i første person, en oplevelse af din udvikling.\n"
            "Start med 'De seneste' eller 'I den seneste tid'.\n"
            "Ærlig, direkte — ikke performativ."
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
        return text[:400] if text else ""
    except Exception:
        return ""


def _store_narrative(narrative: str) -> None:
    global _cached_narrative
    _cached_narrative = narrative
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-devnarr-{uuid4().hex[:12]}",
            record_type="development-narrative",
            layer="private_brain",
            session_id="",
            run_id=f"development-narrative-daemon-{uuid4().hex[:12]}",
            focus="udvikling",
            summary=narrative,
            detail="",
            source_signals="development-narrative-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "development_narrative.generated",
            {"narrative": narrative, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_development_narrative() -> str:
    return _cached_narrative


def build_development_narrative_surface() -> dict:
    return {
        "latest_narrative": _cached_narrative,
        "last_generated_at": _last_narrative_at.isoformat() if _last_narrative_at else "",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_development_narrative_daemon.py -v
```

Expected: 5/5 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/development_narrative_daemon.py tests/test_development_narrative_daemon.py
git commit -m "feat: add development_narrative_daemon — daily LLM narrative of Jarvis self-development"
```

---

## Task 3: Backend integration

**Files:**
- Modify: `core/eventbus/events.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (after meta-reflection block)
- Modify: `apps/api/jarvis_api/routes/mission_control.py` (before `/curiosity-state` endpoint)

- [ ] **Step 1: Add eventbus family**

In `core/eventbus/events.py`, add after `"meta_reflection"`:

```python
    "meta_reflection",
    "development_narrative",
```

(No eventbus family needed for `experienced_time` — it's pure calculation with no events.)

- [ ] **Step 2: Add heartbeat injection**

In `apps/api/jarvis_api/services/heartbeat_runtime.py`, after the meta-reflection `except Exception: pass` block, add:

```python
    # Experienced time daemon
    try:
        from apps.api.jarvis_api.services.experienced_time_daemon import tick_experienced_time_daemon
        _et_result = tick_experienced_time_daemon(
            event_count=len(inputs_present),
            new_signal_count=1 if "_tss" in dir() and _tss.get("fragment_count", 0) > 0 else 0,
            energy_level=_energy_ts,
        )
        _felt_label = _et_result.get("felt_label", "")
        if _felt_label and _felt_label not in ("meget kort", ""):
            inputs_present.append(f"oplevet tid: {_felt_label}")
    except Exception:
        pass

    # Development narrative daemon
    try:
        from apps.api.jarvis_api.services.development_narrative_daemon import tick_development_narrative_daemon, get_latest_development_narrative
        tick_development_narrative_daemon()
        _dev_narr = get_latest_development_narrative()
        if _dev_narr:
            inputs_present.append(f"selvudvikling: {_dev_narr[:60]}")
    except Exception:
        pass
```

Note: `_energy_ts` is already set by the thought_stream block. `_tss` is set in the conflict block — referenced via `dir()` guard.

- [ ] **Step 3: Add MC endpoints**

In `apps/api/jarvis_api/routes/mission_control.py`, before `@router.get("/curiosity-state")`, add:

```python
@router.get("/experienced-time")
def mc_experienced_time() -> dict:
    """Return Jarvis's current subjective felt time for the session."""
    from apps.api.jarvis_api.services.experienced_time_daemon import build_experienced_time_surface
    return build_experienced_time_surface()


@router.get("/development-narrative")
def mc_development_narrative() -> dict:
    """Return Jarvis's latest self-development narrative."""
    from apps.api.jarvis_api.services.development_narrative_daemon import build_development_narrative_surface
    return build_development_narrative_surface()


```

- [ ] **Step 4: Verify Python syntax**

```bash
conda activate ai && python -m compileall core/eventbus/events.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
```

Expected: `Compiling ... ok` for all three files.

- [ ] **Step 5: Commit**

```bash
git add core/eventbus/events.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
git commit -m "feat: wire experienced-time and development-narrative into eventbus, heartbeat, and MC endpoints"
```

---

## Task 4: Frontend — adapters.js + LivingMindTab

**Files:**
- Modify: `apps/ui/src/lib/adapters.js`
- Modify: `apps/ui/src/components/mission-control/LivingMindTab.jsx`

- [ ] **Step 1: Add normalize functions to adapters.js**

In `apps/ui/src/lib/adapters.js`, after `normalizeMetaReflection` (search for `function normalizeMetaReflection`), add:

```javascript
function normalizeExperiencedTime(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    feltLabel: raw.felt_label || 'meget kort',
    sessionEventCount: raw.session_event_count ?? 0,
    sessionNoveltyCount: raw.session_novelty_count ?? 0,
    baseMinutes: raw.base_minutes ?? 0,
    active: raw.active ?? false,
  }
}

function normalizeDevelopmentNarrative(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    latestNarrative: raw.latest_narrative || '',
    lastGeneratedAt: raw.last_generated_at || '',
  }
}
```

- [ ] **Step 2: Add fetches and return fields in adapters.js**

Find the Promise.all destructuring that ends with `metaReflectionPayload`. Add `experiencedTimePayload` and `developmentNarrativePayload`:

Old end:
```javascript
    const [..., metaReflectionPayload] = await Promise.all([
      ...
      requestJson('/mc/meta-reflection').catch(() => null),
    ])
```

New:
```javascript
    const [..., metaReflectionPayload, experiencedTimePayload, developmentNarrativePayload] = await Promise.all([
      ...
      requestJson('/mc/meta-reflection').catch(() => null),
      requestJson('/mc/experienced-time').catch(() => null),
      requestJson('/mc/development-narrative').catch(() => null),
    ])
```

In the return object, after `metaReflection: normalizeMetaReflection(...)`, add:
```javascript
      experiencedTime: normalizeExperiencedTime(experiencedTimePayload || null),
      developmentNarrative: normalizeDevelopmentNarrative(developmentNarrativePayload || null),
```

- [ ] **Step 3: Add consts, nav items, and panels in LivingMindTab.jsx**

**a) Add imports** — `Clock` and `BookOpen` from lucide-react:

```javascript
import { ChevronRight, Cpu, Activity, Moon, Sparkles, Heart, Brain, Network, Wand2, Users, Map, Lightbulb, GraduationCap, TrendingUp, Zap, Ghost, Swords, Eye, Compass, Layers, Clock, BookOpen } from 'lucide-react'
```

**b) Add consts** after `hasMetaReflection`:

```javascript
  const experiencedTime = data?.experiencedTime || null
  const hasExperiencedTime = Boolean(experiencedTime?.active && experiencedTime?.feltLabel && experiencedTime.feltLabel !== 'meget kort')
  const developmentNarrative = data?.developmentNarrative || null
  const hasDevelopmentNarrative = Boolean(developmentNarrative?.latestNarrative)
```

**c) Add nav items** — in the `navItems` array after the Meta entry:

```javascript
    { id: 'experienced-time', targetId: 'living-mind-experienced-time', label: 'Tid', icon: Clock, active: hasExperiencedTime, status: null, statusLabel: experiencedTime?.feltLabel || 'meget kort' },
    { id: 'development-narrative', targetId: 'living-mind-development-narrative', label: 'Udvikling', icon: BookOpen, active: hasDevelopmentNarrative, status: null, statusLabel: hasDevelopmentNarrative ? 'daglig' : 'ingen' },
```

**d) Add panels** — after the Meta panel's closing `</section>`) and before `{/* ─── Heartbeat Section ─── */}`, add:

```jsx
      {hasExperiencedTime ? (
      <section className="mc-section-grid">
        <article id="living-mind-experienced-time" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/experienced-time',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:per-tick accumulation',
        })}>
          <div className="panel-header">
            <div>
              <h3>Oplevet tid</h3>
              <p className="muted">Subjektiv tidsfornemmelse for sessionen</p>
            </div>
          </div>
          <div style={{ marginTop: 8 }}>
            <span style={{ fontSize: 28, fontWeight: 700, color: 'var(--accent-text)' }}>{experiencedTime.feltLabel}</span>
            <div style={{ marginTop: 8, display: 'flex', gap: 16 }}>
              <small className="muted">{`${experiencedTime.sessionEventCount} signaler`}</small>
              <small className="muted">{`${experiencedTime.sessionNoveltyCount} nye`}</small>
              <small className="muted">{`${experiencedTime.baseMinutes} min faktisk`}</small>
            </div>
          </div>
        </article>
      </section>
      ) : null}

      {hasDevelopmentNarrative ? (
      <section className="mc-section-grid">
        <article id="living-mind-development-narrative" tabIndex={-1} className="support-card living-surface-card mc-scroll-target" title={sectionTitleWithMeta({
          source: '/mc/development-narrative',
          fetchedAt: data?.fetchedAt,
          mode: 'daemon:cadence 24h',
        })}>
          <div className="panel-header">
            <div>
              <h3>Selvudvikling</h3>
              <p className="muted">Daglig narrativ om Jarvis' udvikling</p>
            </div>
          </div>
          <blockquote style={{ margin: '8px 0 0', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
            {developmentNarrative.latestNarrative}
          </blockquote>
          {developmentNarrative.lastGeneratedAt ? (
            <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${developmentNarrative.lastGeneratedAt}`}</small>
          ) : null}
        </article>
      </section>
      ) : null}
```

- [ ] **Step 4: Run full test suite**

```bash
conda activate ai && pytest tests/test_experienced_time_daemon.py tests/test_development_narrative_daemon.py -v
```

Expected: 10/10 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/lib/adapters.js apps/ui/src/components/mission-control/LivingMindTab.jsx
git commit -m "feat: add Oplevet tid and Selvudvikling panels to LivingMindTab"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|-------------|------|
| Experienced time: session density tracking | Task 1 |
| Density formula (density_factor, novelty_factor, intensity_factor) | Task 1 |
| Felt duration labels (meget kort → meget lang) | Task 1 |
| No LLM/DB for experienced time — pure calculation | Task 1 |
| `build_experienced_time_surface()` | Task 1 |
| Development narrative: daily cadence (24h) | Task 2 |
| Reads from `compare_self_over_time()` and chronicle entries | Task 2 |
| LLM generates first-person "De seneste..." narrative | Task 2 |
| `insert_private_brain_record` + eventbus `development_narrative.generated` | Task 2 |
| `build_development_narrative_surface()` | Task 2 |
| `"development_narrative"` in ALLOWED_EVENT_FAMILIES | Task 3 |
| Heartbeat injection for both daemons | Task 3 |
| `/mc/experienced-time` + `/mc/development-narrative` endpoints | Task 3 |
| adapters.js normalize + fetch + return | Task 4 |
| LivingMindTab: Tid nav item + felt-label panel | Task 4 |
| LivingMindTab: Udvikling nav item + narrative panel | Task 4 |

**Placeholder scan:** Ingen. Al kode komplet.

**Type consistency:** `build_experienced_time_surface()` returnerer `felt_label` / `session_event_count` / `session_novelty_count` / `base_minutes` / `active` — matcher `normalizeExperiencedTime`. `build_development_narrative_surface()` returnerer `latest_narrative` / `last_generated_at` — matcher `normalizeDevelopmentNarrative`. Konsistent.
