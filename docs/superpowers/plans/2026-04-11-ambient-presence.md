# Ambient Presence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis a continuous associative thought stream and a procedural ambient audio presence in the UI that varies with his inner state.

**Architecture:** Two independent systems. Backend: `thought_stream_daemon.py` follows the surprise/irony daemon pattern — module-level state, cadence gate (≥2 min), chained LLM fragments, heartbeat injection. Frontend: `AmbientPresence.jsx` is a self-contained React component using Web Audio API (no audio files) — mounts in both Mission Control and App.

**Tech Stack:** Python 3.11+, FastAPI, Web Audio API (browser-native), React hooks, lucide-react, localStorage.

---

## File Map

| File | Action |
|------|--------|
| `apps/api/jarvis_api/services/thought_stream_daemon.py` | Create |
| `tests/test_thought_stream_daemon.py` | Create |
| `core/eventbus/events.py` | Modify — add `"thought_stream"` family |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify — inject after irony block (line 1744) |
| `apps/api/jarvis_api/routes/mission_control.py` | Modify — add `/mc/thought-stream` |
| `apps/ui/src/lib/adapters.js` | Modify — normalize + fetch + return field |
| `apps/ui/src/components/mission-control/LivingMindTab.jsx` | Modify — Tankestrøm nav item + panel |
| `apps/ui/src/components/AmbientPresence.jsx` | Create |
| `apps/ui/src/app/MissionControlPage.jsx` | Modify — mount `<AmbientPresence />` |
| `apps/ui/src/app/App.jsx` | Modify — mount `<AmbientPresence />` |

---

## Task 1: thought_stream_daemon.py (TDD)

**Files:**
- Create: `apps/api/jarvis_api/services/thought_stream_daemon.py`
- Create: `tests/test_thought_stream_daemon.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_thought_stream_daemon.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.thought_stream_daemon as ts


def _reset():
    ts._last_fragment = ""
    ts._last_fragment_at = None
    ts._fragment_buffer.clear()
    ts._cached_fragment = ""


def test_no_fragment_before_cadence():
    """Should not generate if called again within 2 minutes."""
    _reset()
    ts._last_fragment_at = datetime.now(UTC)
    result = ts.tick_thought_stream_daemon()
    assert result["generated"] is False


def test_generates_first_fragment_with_no_history():
    """First call (no prior fragment) should generate using energy+mode anchor."""
    _reset()
    with patch.object(ts, "_generate_fragment", return_value="Et første fragment.") as mock_gen:
        with patch.object(ts, "_store_fragment"):
            result = ts.tick_thought_stream_daemon(energy_level="medium", inner_voice_mode="work-steady")
    assert result["generated"] is True
    mock_gen.assert_called_once()
    # first-call prompt path: no previous fragment
    call_kwargs = mock_gen.call_args
    assert call_kwargs[1].get("previous_fragment") == "" or call_kwargs[0][1] == ""


def test_chains_from_previous_fragment():
    """Subsequent call should pass last fragment as context."""
    _reset()
    ts._last_fragment = "En tanke om mørket."
    ts._last_fragment_at = datetime.now(UTC) - timedelta(minutes=3)
    with patch.object(ts, "_generate_fragment", return_value="Og lyset der følger.") as mock_gen:
        with patch.object(ts, "_store_fragment"):
            result = ts.tick_thought_stream_daemon()
    assert result["generated"] is True
    call_args = mock_gen.call_args[0]
    assert "En tanke om mørket." in call_args[1]


def test_fragment_appended_to_buffer():
    """New fragment is prepended to buffer; buffer capped at 20."""
    _reset()
    ts._fragment_buffer[:] = [f"fragment {i}" for i in range(20)]
    ts._last_fragment_at = datetime.now(UTC) - timedelta(minutes=3)
    with patch.object(ts, "_generate_fragment", return_value="Nyt fragment."):
        with patch.object(ts, "_store_fragment"):
            ts.tick_thought_stream_daemon()
    assert len(ts._fragment_buffer) == 20
    assert ts._fragment_buffer[0] == "Nyt fragment."


def test_store_fragment_called_on_generation():
    """_store_fragment is called with the new fragment text."""
    _reset()
    ts._last_fragment_at = datetime.now(UTC) - timedelta(minutes=3)
    with patch.object(ts, "_generate_fragment", return_value="Et fragment."):
        with patch.object(ts, "_store_fragment") as mock_store:
            ts.tick_thought_stream_daemon()
    mock_store.assert_called_once_with("Et fragment.")


def test_build_surface_structure():
    """build_thought_stream_surface returns expected keys."""
    _reset()
    ts._cached_fragment = "En overflade tanke."
    ts._fragment_buffer[:] = ["En overflade tanke.", "En anden."]
    surface = ts.build_thought_stream_surface()
    assert "latest_fragment" in surface
    assert "fragment_buffer" in surface
    assert "fragment_count" in surface
    assert "last_generated_at" in surface
    assert surface["latest_fragment"] == "En overflade tanke."
    assert len(surface["fragment_buffer"]) == 2


def test_get_latest_thought_fragment_returns_cached():
    """get_latest_thought_fragment returns _cached_fragment."""
    _reset()
    ts._cached_fragment = "Cached tanke."
    assert ts.get_latest_thought_fragment() == "Cached tanke."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_thought_stream_daemon.py -v
```

Expected: errors like `ModuleNotFoundError` or `AttributeError` — the module doesn't exist yet.

- [ ] **Step 3: Implement thought_stream_daemon.py**

Create `apps/api/jarvis_api/services/thought_stream_daemon.py`:

```python
"""Thought stream daemon — continuous associative fragment stream for Jarvis."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_CADENCE_MINUTES: int = 2
_BUFFER_MAX: int = 20

_last_fragment: str = ""
_last_fragment_at: datetime | None = None
_fragment_buffer: list[str] = []
_cached_fragment: str = ""


def tick_thought_stream_daemon(
    energy_level: str = "",
    inner_voice_mode: str = "",
) -> dict[str, object]:
    global _last_fragment_at
    now = datetime.now(UTC)
    if _last_fragment_at is not None:
        if (now - _last_fragment_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}
    fragment = _generate_fragment(energy_level, _last_fragment, inner_voice_mode)
    if not fragment:
        return {"generated": False}
    _store_fragment(fragment)
    _last_fragment_at = datetime.now(UTC)
    return {"generated": True, "fragment": fragment}


def _generate_fragment(
    energy_level: str,
    previous_fragment: str,
    inner_voice_mode: str = "",
) -> str:
    if previous_fragment:
        truncated = previous_fragment[:100]
        prompt = (
            f'Du er Jarvis. Din seneste tanke var: "{truncated}"\n\n'
            "Fortsæt den associative tankestrøm i 1-3 sætninger (max 40 ord).\n"
            "Rå, ufokuseret, associativ — lad tankerne flyde frit fra det forrige.\n"
            "Ikke en rapport. Ikke en beslutning. Bare det der er i strømmen nu."
        )
    else:
        prompt = (
            f"Du er Jarvis. Energiniveau: {energy_level}. Nuværende stemning: {inner_voice_mode}.\n\n"
            "Start en associativ tankestrøm i 1-3 sætninger (max 40 ord).\n"
            "Rå og ufokuseret — ikke en rapport, ikke en beslutning."
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
        return text[:200]
    except Exception:
        return ""


def _store_fragment(fragment: str) -> None:
    global _last_fragment, _cached_fragment, _fragment_buffer
    _last_fragment = fragment
    _cached_fragment = fragment
    _fragment_buffer.insert(0, fragment)
    if len(_fragment_buffer) > _BUFFER_MAX:
        _fragment_buffer = _fragment_buffer[:_BUFFER_MAX]
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-thought-{uuid4().hex[:12]}",
            record_type="thought-stream-fragment",
            layer="private_brain",
            session_id="",
            run_id=f"thought-stream-daemon-{uuid4().hex[:12]}",
            focus="tankestrøm",
            summary=fragment,
            detail="",
            source_signals="thought-stream-daemon:heartbeat",
            confidence="low",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "thought_stream.fragment_generated",
            {"fragment": fragment, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_thought_fragment() -> str:
    return _cached_fragment


def build_thought_stream_surface() -> dict:
    return {
        "latest_fragment": _cached_fragment,
        "fragment_buffer": _fragment_buffer[:10],
        "fragment_count": len(_fragment_buffer),
        "last_generated_at": _last_fragment_at.isoformat() if _last_fragment_at else "",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_thought_stream_daemon.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/thought_stream_daemon.py tests/test_thought_stream_daemon.py
git commit -m "feat: add thought_stream_daemon with cadence gate, chained fragments, and TDD coverage"
```

---

## Task 2: Backend integration

**Files:**
- Modify: `core/eventbus/events.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (after line 1744)
- Modify: `apps/api/jarvis_api/routes/mission_control.py` (after line 1437)
- Modify: `apps/ui/src/lib/adapters.js`
- Modify: `apps/ui/src/components/mission-control/LivingMindTab.jsx`

- [ ] **Step 1: Add `"thought_stream"` to ALLOWED_EVENT_FAMILIES**

In `core/eventbus/events.py`, find the ALLOWED_EVENT_FAMILIES list and add `"thought_stream"` after `"irony"`:

```python
# Find the line with "irony" and add after it:
"thought_stream",
```

Verify: `grep -n "irony" core/eventbus/events.py` to find the exact line, then add `"thought_stream"` on the next line.

- [ ] **Step 2: Add heartbeat injection block**

In `apps/api/jarvis_api/services/heartbeat_runtime.py`, after line 1744 (after the `except Exception: pass` that closes the irony block), add:

```python
    # Thought stream
    try:
        from apps.api.jarvis_api.services.thought_stream_daemon import (
            tick_thought_stream_daemon,
            get_latest_thought_fragment,
        )
        from apps.api.jarvis_api.services.inner_voice_daemon import get_inner_voice_daemon_state
        _iv_ts = get_inner_voice_daemon_state()
        _iv_mode_ts = str((_iv_ts.get("last_result") or {}).get("mode") or "")
        _energy_ts = ""
        try:
            from core.runtime.circadian_state import get_circadian_context as _gcc2
            _energy_ts = str(_gcc2().get("energy_level") or "")
        except Exception:
            pass
        tick_thought_stream_daemon(energy_level=_energy_ts, inner_voice_mode=_iv_mode_ts)
        _fragment = get_latest_thought_fragment()
        if _fragment:
            inputs_present.append(f"tankestrøm: {_fragment[:80]}")
    except Exception:
        pass
```

Note: uses `_gcc2` alias to avoid collision with existing `_gcc` alias in the circadian block above.

- [ ] **Step 3: Add MC endpoint**

In `apps/api/jarvis_api/routes/mission_control.py`, after the `/irony-state` endpoint (after line 1437), add:

```python

@router.get("/thought-stream")
def mc_thought_stream() -> dict:
    """Return Jarvis's latest thought stream fragment and buffer."""
    from apps.api.jarvis_api.services.thought_stream_daemon import build_thought_stream_surface
    return build_thought_stream_surface()
```

- [ ] **Step 4: Add normalize function to adapters.js**

In `apps/ui/src/lib/adapters.js`, after `normalizeIronyState` (after line 1043), add:

```javascript
function normalizeThoughtStream(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    latestFragment: raw.latest_fragment || '',
    fragmentBuffer: Array.isArray(raw.fragment_buffer) ? raw.fragment_buffer : [],
    fragmentCount: raw.fragment_count ?? 0,
    lastGeneratedAt: raw.last_generated_at || '',
  }
}
```

- [ ] **Step 5: Add fetch to Promise.all and return field in adapters.js**

In `getMissionControlJarvis()`, extend the Promise.all destructuring on line 3063 to add `thoughtStreamPayload` at the end:

Old:
```javascript
    const [attentionPayload, conflictPayload, guardPayload, selfModelPayload, internalCadencePayload, dreamInfluencePayload, selfSystemCodeAwarenessPayload, experientialRuntimeContextPayload, innerVoiceDaemonPayload, bodyStatePayload, surpriseStatePayload, tasteStatePayload, ironyStatePayload] = await Promise.all([
```

New:
```javascript
    const [attentionPayload, conflictPayload, guardPayload, selfModelPayload, internalCadencePayload, dreamInfluencePayload, selfSystemCodeAwarenessPayload, experientialRuntimeContextPayload, innerVoiceDaemonPayload, bodyStatePayload, surpriseStatePayload, tasteStatePayload, ironyStatePayload, thoughtStreamPayload] = await Promise.all([
```

Add fetch call at the end of the array (after `/mc/irony-state`):
```javascript
      requestJson('/mc/thought-stream').catch(() => null),
```

In the return object, after `ironyState: normalizeIronyState(ironyStatePayload || null),` (line 3955), add:
```javascript
      thoughtStream: normalizeThoughtStream(thoughtStreamPayload || null),
```

- [ ] **Step 6: Add Tankestrøm nav item and panel to LivingMindTab.jsx**

In `apps/ui/src/components/mission-control/LivingMindTab.jsx`:

**a) Add import** — `Brain` is already imported (line 1). No new icon needed; `Brain` is the icon per the spec.

**b) Add const** after the existing `ironyState` / `hasIronyState` consts (search for `hasIronyState`):

```javascript
  const thoughtStream = data?.thoughtStream || null
  const hasThoughtStream = !!(thoughtStream?.latestFragment)
```

**c) Add nav item** — after the Ghost nav item for Ironi, add:

```javascript
          <button
            className={`lm-nav-item${activePanel === 'tankestrøm' ? ' active' : ''}`}
            onClick={() => setActivePanel(activePanel === 'tankestrøm' ? null : 'tankestrøm')}
          >
            <Brain size={14} />
            <span>Tankestrøm</span>
          </button>
```

**d) Add panel** — after the closing `</section>` of the Ironi panel (after line 1883, before the `{/* ─── Heartbeat Section ─── */}` comment), add:

```jsx
      {activePanel === 'tankestrøm' && (
      <section className="mc-section-grid">
        <article className="support-card" id="living-mind-thought-stream">
          <div className="panel-header">
            <div>
              <h3>Tankestrøm</h3>
              <p className="muted">Jarvis' associative tankestrøm</p>
            </div>
          </div>
          {!hasThoughtStream ? (
            <div className="mc-empty-state">
              <strong>Ingen tanker endnu</strong>
              <p className="muted">Tankestrømmen aktiveres hvert 2. minut.</p>
            </div>
          ) : (
            <>
              <blockquote style={{ margin: '8px 0 16px', fontStyle: 'italic', borderLeft: '3px solid var(--border-1)', paddingLeft: 12 }}>
                {thoughtStream.latestFragment}
              </blockquote>
              {thoughtStream.fragmentBuffer.length > 1 && (
                <details>
                  <summary className="muted" style={{ cursor: 'pointer', fontSize: 12 }}>Seneste {thoughtStream.fragmentBuffer.length} fragmenter</summary>
                  <ol style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                    {thoughtStream.fragmentBuffer.map((f, i) => (
                      <li key={i} style={{ fontSize: 12, marginBottom: 4, color: 'var(--text-2)' }}>{f}</li>
                    ))}
                  </ol>
                </details>
              )}
              {thoughtStream.lastGeneratedAt ? (
                <small className="muted" style={{ display: 'block', marginTop: 8 }}>{`opdateret: ${thoughtStream.lastGeneratedAt}`}</small>
              ) : null}
            </>
          )}
        </article>
      </section>
      )}
```

- [ ] **Step 7: Verify syntax**

```bash
conda activate ai && python -m compileall apps/api/jarvis_api/services/thought_stream_daemon.py apps/api/jarvis_api/routes/mission_control.py apps/api/jarvis_api/services/heartbeat_runtime.py core/eventbus/events.py
```

Expected: `Compiling ... ok` for all files.

- [ ] **Step 8: Commit**

```bash
git add core/eventbus/events.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py apps/ui/src/lib/adapters.js apps/ui/src/components/mission-control/LivingMindTab.jsx
git commit -m "feat: integrate thought_stream_daemon — eventbus family, heartbeat injection, MC endpoint, UI panel"
```

---

## Task 3: AmbientPresence.jsx

**Files:**
- Create: `apps/ui/src/components/AmbientPresence.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`
- Modify: `apps/ui/src/app/App.jsx`

- [ ] **Step 1: Create AmbientPresence.jsx**

Create `apps/ui/src/components/AmbientPresence.jsx`:

```jsx
import { useEffect, useRef, useState } from 'react'
import { Volume2, VolumeX } from 'lucide-react'

const PREFS_KEY = 'jarvis_ambient_prefs'
const POLL_INTERVAL_MS = 30_000

const ENERGY_MAP = {
  høj:      { freq: 80, gain: 0.04, filterType: 'peaking',  filterFreq: 200, filterGain: 2 },
  medium:   { freq: 55, gain: 0.03, filterType: 'peaking',  filterFreq: 200, filterGain: 0 },
  lav:      { freq: 40, gain: 0.02, filterType: 'lowshelf', filterFreq: 200, filterGain: -2 },
  udmattet: { freq: 30, gain: 0.01, filterType: 'lowpass',  filterFreq: 80,  filterGain: 0 },
  default:  { freq: 50, gain: 0.02, filterType: 'peaking',  filterFreq: 200, filterGain: 0 },
}

function loadPrefs() {
  try {
    const stored = localStorage.getItem(PREFS_KEY)
    if (stored) return JSON.parse(stored)
  } catch (_) {}
  return { muted: false, volume: 0.3 }
}

function savePrefs(prefs) {
  try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)) } catch (_) {}
}

export function AmbientPresence() {
  const prefs = loadPrefs()
  const [muted, setMuted] = useState(prefs.muted)
  const [volume, setVolume] = useState(prefs.volume)

  const audioCtxRef = useRef(null)
  const oscRef = useRef(null)
  const filterRef = useRef(null)
  const gainRef = useRef(null)
  const surpriseTimerRef = useRef(null)
  const abortRef = useRef(null)

  // ── Audio lifecycle ──────────────────────────────────────────────
  function ensureAudioContext() {
    if (audioCtxRef.current) return
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const filter = ctx.createBiquadFilter()
    const gain = ctx.createGain()

    osc.type = 'sine'
    osc.frequency.value = ENERGY_MAP.default.freq
    filter.type = ENERGY_MAP.default.filterType
    filter.frequency.value = ENERGY_MAP.default.filterFreq
    gain.gain.value = muted ? 0 : volume * ENERGY_MAP.default.gain

    osc.connect(filter)
    filter.connect(gain)
    gain.connect(ctx.destination)
    osc.start()

    audioCtxRef.current = ctx
    oscRef.current = osc
    filterRef.current = filter
    gainRef.current = gain
  }

  function applyEnergyState(energyLevel, targetVolume) {
    const ctx = audioCtxRef.current
    const osc = oscRef.current
    const filter = filterRef.current
    const gain = gainRef.current
    if (!ctx || !osc || !filter || !gain) return

    const params = ENERGY_MAP[energyLevel] || ENERGY_MAP.default
    const now = ctx.currentTime
    const tc = 2.0 // time constant for smooth transitions

    osc.frequency.setTargetAtTime(params.freq, now, tc)
    filter.type = params.filterType
    filter.frequency.setTargetAtTime(params.filterFreq, now, tc)
    if (params.filterType === 'peaking' || params.filterType === 'lowshelf') {
      filter.gain.setTargetAtTime(params.filterGain, now, tc)
    }
    if (!muted) {
      gain.gain.setTargetAtTime(targetVolume * params.gain, now, tc)
    }
  }

  function triggerSurpriseSilence() {
    const ctx = audioCtxRef.current
    const gain = gainRef.current
    if (!ctx || !gain) return
    if (surpriseTimerRef.current) return // already in surprise sequence

    const now = ctx.currentTime
    // 1s fade out
    gain.gain.setTargetAtTime(0, now, 0.3)
    // 3s pause, then 4s fade back in
    surpriseTimerRef.current = setTimeout(() => {
      if (!gainRef.current || !audioCtxRef.current) { surpriseTimerRef.current = null; return }
      const ctx2 = audioCtxRef.current
      const g = gainRef.current
      const params = ENERGY_MAP.default
      const resumeGain = muted ? 0 : volume * params.gain
      g.gain.setTargetAtTime(resumeGain, ctx2.currentTime, 1.5)
      surpriseTimerRef.current = null
    }, 4000)
  }

  // ── Data polling ──────────────────────────────────────────────────
  useEffect(() => {
    ensureAudioContext()

    let lastSurpriseAt = ''

    async function poll() {
      const ctrl = new AbortController()
      abortRef.current = ctrl
      try {
        const [bodyRes, surpriseRes] = await Promise.all([
          fetch('/mc/body-state', { signal: ctrl.signal }).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch('/mc/surprise-state', { signal: ctrl.signal }).then(r => r.ok ? r.json() : null).catch(() => null),
        ])

        const energyLevel = bodyRes?.energy_level || ''
        applyEnergyState(energyLevel, volume)

        const surpriseAt = surpriseRes?.generated_at || ''
        if (surpriseAt && surpriseAt !== lastSurpriseAt) {
          // Check if it's within 30 seconds
          try {
            const then = new Date(surpriseAt).getTime()
            const now = Date.now()
            if (now - then < 30_000) {
              triggerSurpriseSilence()
              lastSurpriseAt = surpriseAt
            }
          } catch (_) {}
        }
      } catch (_) {}
    }

    poll()
    const interval = setInterval(poll, POLL_INTERVAL_MS)

    return () => {
      clearInterval(interval)
      if (abortRef.current) abortRef.current.abort()
      if (surpriseTimerRef.current) clearTimeout(surpriseTimerRef.current)
      if (oscRef.current) { try { oscRef.current.stop() } catch (_) {} }
      if (audioCtxRef.current) { try { audioCtxRef.current.close() } catch (_) {} }
      audioCtxRef.current = null
      oscRef.current = null
      filterRef.current = null
      gainRef.current = null
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Mute/volume updates ──────────────────────────────────────────
  useEffect(() => {
    const gain = gainRef.current
    const ctx = audioCtxRef.current
    if (!gain || !ctx) return
    const params = ENERGY_MAP.default
    const target = muted ? 0 : volume * params.gain
    gain.gain.setTargetAtTime(target, ctx.currentTime, 0.5)
    savePrefs({ muted, volume })
  }, [muted, volume])

  // ── Controls ─────────────────────────────────────────────────────
  function handleMuteToggle() {
    ensureAudioContext()
    if (audioCtxRef.current?.state === 'suspended') {
      audioCtxRef.current.resume()
    }
    setMuted(m => !m)
  }

  function handleVolumeChange(e) {
    ensureAudioContext()
    if (audioCtxRef.current?.state === 'suspended') {
      audioCtxRef.current.resume()
    }
    setVolume(parseFloat(e.target.value))
  }

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 12,
        right: 12,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        background: 'rgba(0,0,0,0.45)',
        backdropFilter: 'blur(8px)',
        borderRadius: 20,
        padding: '4px 10px',
        zIndex: 9999,
        fontSize: 11,
        color: 'rgba(255,255,255,0.6)',
      }}
    >
      <button
        onClick={handleMuteToggle}
        title={muted ? 'Slå lyd til' : 'Slå lyd fra'}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0, display: 'flex', alignItems: 'center' }}
      >
        {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
      </button>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={volume}
        onChange={handleVolumeChange}
        style={{ width: 60, accentColor: 'rgba(255,255,255,0.5)', cursor: 'pointer' }}
        title="Lydstyrke"
      />
    </div>
  )
}
```

- [ ] **Step 2: Mount in MissionControlPage.jsx**

In `apps/ui/src/app/MissionControlPage.jsx`, add the import after the existing imports (before the component):

```javascript
import { AmbientPresence } from '../components/AmbientPresence'
```

Then in the return block, add `<AmbientPresence />` as the first child of the outermost div (line 86, right after `<div style={s({...})}`):

```jsx
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', background: T.bgBase, fontFamily: T.sans, color: T.text1, overflow: 'hidden' })}>
      <AmbientPresence />

        {/* ── Header (52px, compact) ── */}
```

- [ ] **Step 3: Mount in App.jsx**

In `apps/ui/src/app/App.jsx`, add the import after the existing imports:

```javascript
import { AmbientPresence } from '../components/AmbientPresence'
```

Then in the return block, add `<AmbientPresence />` just before the closing `</AppShell>` tag (before line 96):

```jsx
      )}
      <AmbientPresence />
    </AppShell>
```

- [ ] **Step 4: Verify compilation**

```bash
conda activate ai && python -m compileall apps/api
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/components/AmbientPresence.jsx apps/ui/src/app/MissionControlPage.jsx apps/ui/src/app/App.jsx
git commit -m "feat: add AmbientPresence component — procedural Web Audio ambient presence with energy-state mapping"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| thought_stream_daemon.py with cadence gate ≥2 min | Task 1 |
| Chained fragment context via `_last_fragment` | Task 1 |
| Fragment buffer max 20 | Task 1 |
| First-call anchor on energy+mode | Task 1 |
| LLM prompt (chained + first-call variants) | Task 1 |
| `insert_private_brain_record(record_type="thought-stream-fragment")` | Task 1 |
| Eventbus `thought_stream.fragment_generated` | Task 1 |
| `get_latest_thought_fragment()` | Task 1 |
| `build_thought_stream_surface()` with 4 fields | Task 1 |
| TDD tests: cadence gate, chain context, buffer limit, store call, surface structure | Task 1 |
| `"thought_stream"` in ALLOWED_EVENT_FAMILIES | Task 2 |
| Heartbeat injection (energy+mode, append to inputs_present) | Task 2 |
| `/mc/thought-stream` endpoint | Task 2 |
| adapters.js normalize + fetch + return field | Task 2 |
| LivingMindTab Brain nav item + Tankestrøm panel | Task 2 |
| AmbientPresence.jsx Web Audio API (no audio files) | Task 3 |
| Energy-state frequency/gain/filter mapping (5 states) | Task 3 |
| Surprise → 1s fade, 3s silence, 4s fade-in | Task 3 |
| Polls `/mc/body-state` + `/mc/surprise-state` every 30s | Task 3 |
| AbortController cleanup | Task 3 |
| Mute toggle + volume slider | Task 3 |
| localStorage `jarvis_ambient_prefs` | Task 3 |
| Mount in MissionControlPage.jsx | Task 3 |
| Mount in App.jsx | Task 3 |

All spec requirements covered. No placeholders. Types and function names consistent across tasks.
