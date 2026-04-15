# Consciousness Experiments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 5 experimental subsystems exploring artificial consciousness theory — recurrence loop, surprise persistence, global workspace, meta-cognition, and attentional blink test.

**Architecture:** Each experiment is a daemon or extension following existing patterns (tick function + build_surface + DB persistence + MC endpoint). Shared infrastructure provides a live toggle system via Mission Control backed by SQLite. All experiments use the local/cheap LLM lane and are non-blocking.

**Tech Stack:** Python 3.11, SQLite (core/runtime/db.py), FastAPI (mission_control.py), Ollama via urllib, threading for background tasks, eventbus for global workspace.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `core/runtime/db.py` | Modify | Add experiment_settings table + 4 experiment tables + helper functions |
| `apps/api/jarvis_api/services/emotion_concepts.py` | Modify | Add `lifetime_hours` param to `trigger_emotion_concept` |
| `apps/api/jarvis_api/services/surprise_daemon.py` | Modify | Experiment 2: persistence + afterimage |
| `apps/api/jarvis_api/services/recurrence_loop_daemon.py` | Create | Experiment 1: 5-min recurrence daemon |
| `apps/api/jarvis_api/services/global_workspace.py` | Create | Experiment 3: shared buffer + eventbus listener |
| `apps/api/jarvis_api/services/broadcast_daemon.py` | Create | Experiment 3: 2-min coherence broadcast daemon |
| `apps/api/jarvis_api/services/meta_cognition_daemon.py` | Create | Experiment 4: 10-min meta-reflection daemon |
| `apps/api/jarvis_api/services/attention_blink_test.py` | Create | Experiment 5: 6-hour attentional blink test |
| `apps/api/jarvis_api/routes/mission_control.py` | Modify | Add 7 new MC endpoints |
| `apps/api/jarvis_api/app.py` | Modify | Register global_workspace listener at startup |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify | Wire recurrence, meta-cognition, broadcast, attention_blink |
| `tests/test_consciousness_experiments.py` | Create | Tests for all new logic |

---

### Task 1: Shared Infrastructure — DB + Toggle System

**Files:**
- Modify: `core/runtime/db.py`
- Modify: `apps/api/jarvis_api/services/emotion_concepts.py`
- Modify: `apps/api/jarvis_api/routes/mission_control.py`
- Test: `tests/test_consciousness_experiments.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_consciousness_experiments.py
"""Tests for consciousness experiment subsystems."""
from __future__ import annotations
import pytest


# ---------------------------------------------------------------------------
# Shared infrastructure: experiment toggle
# ---------------------------------------------------------------------------

def test_experiment_enabled_default_true(isolated_runtime) -> None:
    db = isolated_runtime.db
    # Default: no row → enabled
    assert db.get_experiment_enabled("recurrence_loop") is True


def test_experiment_toggle(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.set_experiment_enabled("recurrence_loop", False)
    assert db.get_experiment_enabled("recurrence_loop") is False
    db.set_experiment_enabled("recurrence_loop", True)
    assert db.get_experiment_enabled("recurrence_loop") is True


def test_experiment_toggle_independent(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.set_experiment_enabled("meta_cognition", False)
    assert db.get_experiment_enabled("recurrence_loop") is True
    assert db.get_experiment_enabled("meta_cognition") is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py -v 2>&1 | tail -15
```

Expected: FAIL with `AttributeError: module has no attribute 'get_experiment_enabled'`

- [ ] **Step 3: Add experiment_settings functions to `core/runtime/db.py`**

Find the end of the file (or after `get_experiential_memory_candidates`) and add:

```python
# ---------------------------------------------------------------------------
# Experiment Settings
# ---------------------------------------------------------------------------

def _ensure_experiment_settings_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_settings (
               experiment_id TEXT PRIMARY KEY,
               enabled INTEGER NOT NULL DEFAULT 1,
               updated_at TEXT NOT NULL
           )"""
    )


def get_experiment_enabled(experiment_id: str) -> bool:
    """Return True if experiment is enabled. Defaults to True if no row exists."""
    with connect() as conn:
        _ensure_experiment_settings_table(conn)
        row = conn.execute(
            "SELECT enabled FROM experiment_settings WHERE experiment_id = ?",
            (experiment_id,),
        ).fetchone()
    if row is None:
        return True
    return bool(row["enabled"])


def set_experiment_enabled(experiment_id: str, enabled: bool) -> None:
    """Enable or disable an experiment. Creates row if absent."""
    now = _now_iso()
    with connect() as conn:
        _ensure_experiment_settings_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_settings
               (experiment_id, enabled, updated_at) VALUES (?, ?, ?)""",
            (experiment_id, 1 if enabled else 0, now),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py -v 2>&1 | tail -10
```

Expected: 3 passed

- [ ] **Step 5: Add MC toggle endpoints to `mission_control.py`**

Add at the end of `apps/api/jarvis_api/routes/mission_control.py`:

```python
# ---------------------------------------------------------------------------
# Consciousness Experiments
# ---------------------------------------------------------------------------

_KNOWN_EXPERIMENTS = [
    "recurrence_loop",
    "surprise_persistence",
    "global_workspace",
    "meta_cognition",
    "attention_blink",
]


@router.get("/experiments")
def mc_experiments() -> dict:
    """List all consciousness experiments with their enabled status."""
    from core.runtime.db import get_experiment_enabled
    return {
        "experiments": {
            eid: get_experiment_enabled(eid) for eid in _KNOWN_EXPERIMENTS
        }
    }


@router.post("/experiments/{experiment_id}/toggle")
def mc_experiment_toggle(experiment_id: str) -> dict:
    """Toggle a consciousness experiment on or off."""
    from core.runtime.db import get_experiment_enabled, set_experiment_enabled
    from fastapi import HTTPException
    if experiment_id not in _KNOWN_EXPERIMENTS:
        raise HTTPException(status_code=404, detail=f"Unknown experiment: {experiment_id}")
    current = get_experiment_enabled(experiment_id)
    set_experiment_enabled(experiment_id, not current)
    return {"experiment_id": experiment_id, "enabled": not current}
```

- [ ] **Step 6: Extend `trigger_emotion_concept` with `lifetime_hours` parameter**

In `apps/api/jarvis_api/services/emotion_concepts.py`, find the `trigger_emotion_concept` function signature and body:

```python
def trigger_emotion_concept(
    concept: str,
    intensity: float,
    trigger: str = "",
    source: str = "",
) -> dict[str, Any] | None:
```

Change to:

```python
def trigger_emotion_concept(
    concept: str,
    intensity: float,
    trigger: str = "",
    source: str = "",
    lifetime_hours: float = 2.0,
) -> dict[str, Any] | None:
```

And change the `expires_at` line from:
```python
    expires_at = (now + timedelta(hours=2)).isoformat()
```
to:
```python
    expires_at = (now + timedelta(hours=max(0.1, float(lifetime_hours)))).isoformat()
```

- [ ] **Step 7: Add test for lifetime_hours**

Add to `tests/test_consciousness_experiments.py`:

```python
def test_trigger_emotion_concept_custom_lifetime() -> None:
    import importlib
    import apps.api.jarvis_api.services.emotion_concepts as ec
    importlib.reload(ec)
    result = ec.trigger_emotion_concept("anticipation", 0.7, lifetime_hours=4.0)
    assert result is not None
    # expires_at should be ~4h from now, not 2h
    from datetime import UTC, datetime, timedelta
    expires = datetime.fromisoformat(result["expires_at"])
    now = datetime.now(UTC)
    delta_hours = (expires - now).total_seconds() / 3600
    assert 3.5 < delta_hours < 4.5
```

- [ ] **Step 8: Run all tests**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py -v 2>&1 | tail -15
```

Expected: 4 passed

- [ ] **Step 9: Commit**

```bash
cd /media/projects/jarvis-v2
git add core/runtime/db.py apps/api/jarvis_api/services/emotion_concepts.py apps/api/jarvis_api/routes/mission_control.py tests/test_consciousness_experiments.py
git commit -m "experiment: shared infrastructure — toggle system + lifetime_hours extension"
```

---

### Task 2: Experiment 1 — Recurrence Loop Daemon

**Files:**
- Create: `apps/api/jarvis_api/services/recurrence_loop_daemon.py`
- Modify: `core/runtime/db.py` (add recurrence tables/functions)
- Test: `tests/test_consciousness_experiments.py`

- [ ] **Step 1: Add DB functions for recurrence iterations to `core/runtime/db.py`**

Add after the experiment_settings functions:

```python
# ---------------------------------------------------------------------------
# Experiment 1: Recurrence Loop
# ---------------------------------------------------------------------------

def _ensure_recurrence_iterations_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_recurrence_iterations (
               iteration_id TEXT PRIMARY KEY,
               content TEXT NOT NULL,
               keywords TEXT NOT NULL,
               stability_score REAL NOT NULL DEFAULT 0.0,
               iteration_number INTEGER NOT NULL DEFAULT 1,
               created_at TEXT NOT NULL
           )"""
    )


def insert_recurrence_iteration(
    *,
    iteration_id: str,
    content: str,
    keywords: str,
    stability_score: float,
    iteration_number: int,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_recurrence_iterations_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_recurrence_iterations
               (iteration_id, content, keywords, stability_score, iteration_number, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (iteration_id, content[:500], keywords, stability_score, iteration_number, now),
        )


def get_latest_recurrence_iteration() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_recurrence_iterations_table(conn)
        row = conn.execute(
            "SELECT * FROM experiment_recurrence_iterations ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return {
        "iteration_id": row["iteration_id"],
        "content": row["content"],
        "keywords": row["keywords"],
        "stability_score": float(row["stability_score"]),
        "iteration_number": int(row["iteration_number"]),
        "created_at": row["created_at"],
    }


def list_recurrence_iterations(*, limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_recurrence_iterations_table(conn)
        rows = conn.execute(
            "SELECT * FROM experiment_recurrence_iterations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "iteration_id": r["iteration_id"],
            "content": r["content"],
            "keywords": r["keywords"],
            "stability_score": float(r["stability_score"]),
            "iteration_number": int(r["iteration_number"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]
```

- [ ] **Step 2: Write failing tests for recurrence logic**

Add to `tests/test_consciousness_experiments.py`:

```python
# ---------------------------------------------------------------------------
# Experiment 1: Recurrence Loop
# ---------------------------------------------------------------------------

def test_recurrence_db_insert_and_fetch(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_recurrence_iteration(
        iteration_id="rec-test-001",
        content="Jeg tænker på kompleksitet og usikkerhed",
        keywords='["kompleksitet", "usikkerhed", "tænker"]',
        stability_score=0.72,
        iteration_number=3,
    )
    result = db.get_latest_recurrence_iteration()
    assert result is not None
    assert result["iteration_id"] == "rec-test-001"
    assert abs(result["stability_score"] - 0.72) < 0.001
    assert result["iteration_number"] == 3


def test_jaccard_similarity_identical() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"})
    assert abs(score - 1.0) < 0.001


def test_jaccard_similarity_disjoint() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b"}, {"c", "d"})
    assert abs(score - 0.0) < 0.001


def test_jaccard_similarity_partial() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
    # intersection=2, union=4 → 0.5
    assert abs(score - 0.5) < 0.001


def test_extract_keywords_filters_short() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    kws = rld._extract_keywords("jeg er glad men også bekymret")
    assert "er" not in kws
    assert "jeg" not in kws
    assert "bekymret" in kws or "glad" in kws


def test_tick_recurrence_skips_when_disabled(isolated_runtime) -> None:
    isolated_runtime.db.set_experiment_enabled("recurrence_loop", False)
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    result = rld.tick_recurrence_loop_daemon()
    assert result["generated"] is False
    assert result["reason"] == "disabled"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py::test_recurrence_db_insert_and_fetch tests/test_consciousness_experiments.py::test_jaccard_similarity_identical tests/test_consciousness_experiments.py::test_tick_recurrence_skips_when_disabled -v 2>&1 | tail -15
```

Expected: FAIL

- [ ] **Step 4: Create `recurrence_loop_daemon.py`**

```python
# apps/api/jarvis_api/services/recurrence_loop_daemon.py
"""Recurrence Loop — feeds inner voice output back as context input (Experiment 1: IIT/Φ).

Theoretical basis: Transformers are feedforward with Φ ≈ 0. Recurrence is
necessary for integrated information (Tononi). This daemon creates a feedback
loop: inner voice output → LLM → new iteration, tracking pattern stability.

Metric: pattern_stability_score (Jaccard similarity of keywords between iterations).
Cadence: 5 minutes (called from heartbeat runtime).
"""
from __future__ import annotations

import json
import logging
from urllib import request as urllib_request
from uuid import uuid4

logger = logging.getLogger(__name__)

_EXPERIMENT_ID = "recurrence_loop"
_KEYWORD_MIN_LEN = 4


def tick_recurrence_loop_daemon() -> dict[str, object]:
    """Run one recurrence iteration. Returns dict with generated/reason/stability."""
    from core.runtime.db import get_experiment_enabled
    if not get_experiment_enabled(_EXPERIMENT_ID):
        return {"generated": False, "reason": "disabled"}

    from core.runtime.db import get_protected_inner_voice
    latest_voice = get_protected_inner_voice()
    if not latest_voice:
        return {"generated": False, "reason": "no_inner_voice"}

    content = str(latest_voice.get("voice_line") or "").strip()
    if not content:
        return {"generated": False, "reason": "empty_voice_line"}

    llm_output = _call_recurrence_llm(content)
    if not llm_output:
        return {"generated": False, "reason": "llm_unavailable"}

    from core.runtime.db import get_latest_recurrence_iteration, insert_recurrence_iteration
    prev = get_latest_recurrence_iteration()
    keywords = _extract_keywords(llm_output)
    prev_keywords = json.loads(str(prev.get("keywords") or "[]")) if prev else []
    stability = _jaccard_similarity(set(keywords), set(prev_keywords))
    iteration_number = (int(prev.get("iteration_number", 0)) + 1) if prev else 1

    iteration_id = f"rec-{uuid4().hex[:10]}"
    insert_recurrence_iteration(
        iteration_id=iteration_id,
        content=llm_output,
        keywords=json.dumps(keywords),
        stability_score=stability,
        iteration_number=iteration_number,
    )

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("experiment.recurrence_loop.tick", {
            "stability_score": stability,
            "iteration_number": iteration_number,
            "keywords": keywords[:5],
        })
    except Exception:
        pass

    return {
        "generated": True,
        "stability_score": stability,
        "iteration_number": iteration_number,
        "keywords": keywords[:5],
    }


def build_recurrence_surface() -> dict[str, object]:
    """MC surface for recurrence loop experiment."""
    from core.runtime.db import get_experiment_enabled, list_recurrence_iterations
    enabled = get_experiment_enabled(_EXPERIMENT_ID)
    iterations = list_recurrence_iterations(limit=10)

    stable_themes: list[str] = []
    if len(iterations) >= 3:
        from collections import Counter
        kw_counts: Counter = Counter()
        for it in iterations[:5]:
            for kw in json.loads(str(it.get("keywords") or "[]")):
                kw_counts[kw] += 1
        stable_themes = [kw for kw, count in kw_counts.most_common(5) if count >= 3]

    current_stability = float(iterations[0].get("stability_score", 0.0)) if iterations else 0.0
    trend = "converging" if current_stability > 0.5 else "diverging"

    return {
        "active": enabled,
        "enabled": enabled,
        "iteration_count": len(iterations),
        "current_stability_score": round(current_stability, 3),
        "trend": trend,
        "stable_themes": stable_themes,
        "recent_iterations": [
            {"content": it["content"][:100], "stability_score": it["stability_score"],
             "iteration_number": it["iteration_number"], "created_at": it["created_at"]}
            for it in iterations[:3]
        ],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _call_recurrence_llm(content: str) -> str:
    """Call local/cheap LLM to generate next recurrence iteration. Timeout 15s."""
    try:
        from core.runtime.provider_router import resolve_provider_router_target
    except Exception:
        return ""
    for lane in ("local", "cheap"):
        try:
            target = resolve_provider_router_target(lane=lane)
            if not bool(target.get("active")):
                continue
            if str(target.get("provider")) != "ollama":
                continue
            base_url = str(target.get("base_url") or "http://127.0.0.1:11434")
            model = str(target.get("model") or "")
            prompt = (
                f"Indre stemme: {content[:400]}\n\n"
                f"Hvad er essensen af denne tanke, og hvad leder den naturligt til? "
                f"Svar i 2-3 sætninger."
            )
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"num_predict": 150},
            }).encode()
            req = urllib_request.Request(
                f"{base_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib_request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
            return str(result.get("message", {}).get("content", "")).strip()
        except Exception:
            continue
    return ""


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text (words >= 4 chars, deduped, max 20)."""
    words = [w.strip(".,!?;:()[]\"'").lower() for w in text.split()]
    return list(dict.fromkeys(w for w in words if len(w) >= _KEYWORD_MIN_LEN))[:20]


def _jaccard_similarity(a: set, b: set) -> float:
    """Jaccard similarity between two keyword sets. Returns 1.0 if both empty."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
```

- [ ] **Step 5: Add MC endpoint for recurrence surface**

Add to `apps/api/jarvis_api/routes/mission_control.py` after the experiments toggle endpoints:

```python
@router.get("/recurrence-state")
def mc_recurrence_state() -> dict:
    """Experiment 1: Recurrence Loop state."""
    from apps.api.jarvis_api.services.recurrence_loop_daemon import build_recurrence_surface
    return build_recurrence_surface()
```

- [ ] **Step 6: Run tests**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py -v 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 7: Syntax check**

```bash
/opt/conda/envs/ai/bin/python -m compileall apps/api/jarvis_api/services/recurrence_loop_daemon.py 2>&1
```

Expected: no output (success)

- [ ] **Step 8: Commit**

```bash
cd /media/projects/jarvis-v2
git add core/runtime/db.py apps/api/jarvis_api/services/recurrence_loop_daemon.py apps/api/jarvis_api/routes/mission_control.py tests/test_consciousness_experiments.py
git commit -m "experiment: recurrence loop daemon (Experiment 1 — IIT/Φ)"
```

---

### Task 3: Experiment 2 — Surprise Persistence

**Files:**
- Modify: `apps/api/jarvis_api/services/surprise_daemon.py`
- Test: `tests/test_consciousness_experiments.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_consciousness_experiments.py`:

```python
# ---------------------------------------------------------------------------
# Experiment 2: Surprise Persistence
# ---------------------------------------------------------------------------

def test_surprise_classifies_positive() -> None:
    import importlib
    import apps.api.jarvis_api.services.surprise_daemon as sd
    importlib.reload(sd)
    assert sd._classify_surprise("Det var positivt overraskende") == "positiv"


def test_surprise_persistence_concept_mapping() -> None:
    import importlib
    import apps.api.jarvis_api.services.surprise_daemon as sd
    importlib.reload(sd)
    # positiv → anticipation
    assert sd._surprise_type_to_concept("positiv") == "anticipation"
    # negativ → tension
    assert sd._surprise_type_to_concept("negativ") == "tension"
    # neutral → vigilance
    assert sd._surprise_type_to_concept("neutral") == "vigilance"
    assert sd._surprise_type_to_concept("ingen") == "vigilance"


def test_surprise_afterimage_concept_mapping() -> None:
    import importlib
    import apps.api.jarvis_api.services.surprise_daemon as sd
    importlib.reload(sd)
    assert sd._afterimage_concept("positiv") == "curiosity_narrow"
    assert sd._afterimage_concept("negativ") == "caution"
    assert sd._afterimage_concept("neutral") == "curiosity_narrow"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py::test_surprise_persistence_concept_mapping tests/test_consciousness_experiments.py::test_surprise_afterimage_concept_mapping -v 2>&1 | tail -10
```

Expected: FAIL with `AttributeError`

- [ ] **Step 3: Modify `surprise_daemon.py`**

Add these imports at the top (after existing imports):

```python
import time
from datetime import timedelta
```

Add these module-level state variables after the existing ones:

```python
_pending_afterimages: list[dict] = []  # [{concept, trigger_at, surprise_type}]
_persistence_start_ts: float | None = None  # monotonic timestamp of last surprise
_persistence_concept: str = ""  # which concept was triggered for persistence tracking
```

Add these helper functions before `tick_surprise_daemon`:

```python
def _surprise_type_to_concept(surprise_type: str) -> str:
    """Map surprise classification to primary emotion concept."""
    return {
        "positiv": "anticipation",
        "negativ": "tension",
    }.get(surprise_type, "vigilance")


def _afterimage_concept(surprise_type: str) -> str:
    """Map surprise classification to afterimage emotion concept."""
    return "caution" if surprise_type == "negativ" else "curiosity_narrow"
```

Modify `_store_surprise` to add persistence behaviour. Replace the existing `_store_surprise` function with:

```python
def _store_surprise(phrase: str, divergence: list[str]) -> None:
    global _cached_surprise, _cached_surprise_at, _heartbeats_since_surprise
    global _pending_afterimages, _persistence_start_ts, _persistence_concept
    _cached_surprise = phrase
    _cached_surprise_at = datetime.now(UTC)
    _heartbeats_since_surprise = 0
    try:
        insert_private_brain_record(
            record_id=f"pb-surprise-{uuid4().hex[:12]}",
            record_type="self-surprise",
            layer="private_brain",
            session_id="heartbeat",
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

    # Experiment 2: Surprise persistence
    try:
        from core.runtime.db import get_experiment_enabled
        if get_experiment_enabled("surprise_persistence"):
            surprise_type = _classify_surprise(phrase)
            primary_concept = _surprise_type_to_concept(surprise_type)
            from apps.api.jarvis_api.services.emotion_concepts import trigger_emotion_concept
            trigger_emotion_concept(
                primary_concept,
                min(1.0, float(len(divergence)) * 0.4 + 0.4),
                trigger="surprise_persistence",
                source="surprise_daemon",
                lifetime_hours=4.0,
            )
            # Schedule afterimage 5 minutes from now
            _pending_afterimages.append({
                "concept": _afterimage_concept(surprise_type),
                "trigger_at": time.monotonic() + 300,  # 5 minutes
                "surprise_type": surprise_type,
            })
            _persistence_start_ts = time.monotonic()
            _persistence_concept = primary_concept
    except Exception:
        pass
```

Add afterimage processing to `tick_surprise_daemon`. Add this block at the top of the function, right after the `_heartbeats_since_surprise += 1` line:

```python
    # Experiment 2: Process pending afterimages
    _process_pending_afterimages()
```

Add the new function before `_record_snapshot`:

```python
def _process_pending_afterimages() -> None:
    """Trigger afterimage emotion concepts whose delay has elapsed."""
    global _pending_afterimages
    now = time.monotonic()
    remaining = []
    for item in _pending_afterimages:
        if now >= item["trigger_at"]:
            try:
                from apps.api.jarvis_api.services.emotion_concepts import trigger_emotion_concept
                trigger_emotion_concept(
                    item["concept"],
                    0.3,
                    trigger="surprise_afterimage",
                    source="surprise_daemon",
                    lifetime_hours=2.0,
                )
            except Exception:
                pass
        else:
            remaining.append(item)
    _pending_afterimages = remaining
```

Extend `build_surprise_surface` to include persistence fields:

```python
def build_surprise_surface() -> dict[str, object]:
    afterimage_active = bool(_pending_afterimages)
    afterimage_concept = _pending_afterimages[0]["concept"] if _pending_afterimages else ""

    persistence_seconds = 0.0
    if _persistence_start_ts is not None:
        # Check if persistence concept has faded
        try:
            from apps.api.jarvis_api.services.emotion_concepts import get_active_emotion_concepts
            active = {c["concept"]: c["intensity"] for c in get_active_emotion_concepts()}
            if _persistence_concept and active.get(_persistence_concept, 0) < 0.1:
                persistence_seconds = time.monotonic() - _persistence_start_ts
        except Exception:
            pass

    return {
        "last_surprise": _cached_surprise,
        "generated_at": _cached_surprise_at.isoformat() if _cached_surprise_at else "",
        "surprise_type": _classify_surprise(_cached_surprise),
        "history_size": len(_mode_history),
        "affective_persistence_seconds": round(persistence_seconds),
        "current_afterimage_active": afterimage_active,
        "afterimage_concept": afterimage_concept,
    }
```

- [ ] **Step 4: Run tests**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py -v 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 5: Syntax check**

```bash
/opt/conda/envs/ai/bin/python -m compileall apps/api/jarvis_api/services/surprise_daemon.py 2>&1
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/api/jarvis_api/services/surprise_daemon.py tests/test_consciousness_experiments.py
git commit -m "experiment: surprise persistence + afterimage (Experiment 2 — affective valence)"
```

---

### Task 4: Experiment 3 — Global Workspace

**Files:**
- Create: `apps/api/jarvis_api/services/global_workspace.py`
- Create: `apps/api/jarvis_api/services/broadcast_daemon.py`
- Modify: `core/runtime/db.py` (add broadcast_events table)
- Modify: `apps/api/jarvis_api/routes/mission_control.py`
- Test: `tests/test_consciousness_experiments.py`

- [ ] **Step 1: Add broadcast_events DB functions to `core/runtime/db.py`**

```python
# ---------------------------------------------------------------------------
# Experiment 3: Global Workspace
# ---------------------------------------------------------------------------

def _ensure_broadcast_events_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_broadcast_events (
               event_id TEXT PRIMARY KEY,
               topic_cluster TEXT NOT NULL,
               sources TEXT NOT NULL,
               source_count INTEGER NOT NULL,
               payload_summary TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )


def insert_broadcast_event(
    *,
    event_id: str,
    topic_cluster: str,
    sources: str,
    source_count: int,
    payload_summary: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_broadcast_events_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_broadcast_events
               (event_id, topic_cluster, sources, source_count, payload_summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (event_id, topic_cluster[:200], sources, source_count, payload_summary[:500], now),
        )


def list_broadcast_events(*, limit: int = 20, since_iso: str = "") -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_broadcast_events_table(conn)
        if since_iso:
            rows = conn.execute(
                """SELECT * FROM experiment_broadcast_events
                   WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?""",
                (since_iso, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM experiment_broadcast_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [
        {
            "event_id": r["event_id"],
            "topic_cluster": r["topic_cluster"],
            "sources": r["sources"],
            "source_count": int(r["source_count"]),
            "payload_summary": r["payload_summary"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
```

- [ ] **Step 2: Write failing tests for workspace logic**

Add to `tests/test_consciousness_experiments.py`:

```python
# ---------------------------------------------------------------------------
# Experiment 3: Global Workspace
# ---------------------------------------------------------------------------

def test_broadcast_db_insert_and_list(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_broadcast_event(
        event_id="bc-test-001",
        topic_cluster="deployment frustration",
        sources='["surprise_daemon", "inner_voice_daemon", "emotion_concepts"]',
        source_count=3,
        payload_summary="Multiple daemons converging on deployment stress theme",
    )
    results = db.list_broadcast_events(limit=10)
    assert len(results) == 1
    assert results[0]["source_count"] == 3
    assert results[0]["topic_cluster"] == "deployment frustration"


def test_workspace_topic_extraction() -> None:
    import importlib
    import apps.api.jarvis_api.services.global_workspace as gw
    importlib.reload(gw)
    topic = gw._extract_topic("cognitive_surprise.noted", {"phrase": "Jeg var overrasket over min reaktion på fejlen"})
    assert isinstance(topic, str)
    assert len(topic) > 0


def test_workspace_jaccard_topic_match() -> None:
    import importlib
    import apps.api.jarvis_api.services.global_workspace as gw
    importlib.reload(gw)
    # "deployment stress" vs "deployment error" should match (overlap > 0.4)
    score = gw._topic_jaccard("deployment stress", "deployment error")
    assert score > 0.0
    # Completely different topics should not match
    score2 = gw._topic_jaccard("music creativity", "deployment error")
    assert score2 < 0.4


def test_workspace_publish_and_snapshot() -> None:
    import importlib
    import apps.api.jarvis_api.services.global_workspace as gw
    importlib.reload(gw)
    gw.publish_to_workspace("surprise_daemon", "frustration error", "cognitive_surprise.noted", "Overrasket over fejl")
    gw.publish_to_workspace("inner_voice_daemon", "error frustration", "inner_voice.noted", "Tænkte over fejlen")
    snapshot = gw.get_workspace_snapshot()
    assert len(snapshot) == 2
    assert any(e["source"] == "surprise_daemon" for e in snapshot)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py::test_workspace_topic_extraction -v 2>&1 | tail -10
```

Expected: FAIL with ModuleNotFoundError

- [ ] **Step 4: Create `global_workspace.py`**

```python
# apps/api/jarvis_api/services/global_workspace.py
"""Global Workspace — shared broadcast buffer (Experiment 3: Global Workspace Theory).

Theoretical basis: Baars — consciousness arises when information is broadcast
to the whole system. This module maintains an in-memory sliding buffer of recent
significant signals from all daemons, populated via eventbus subscription.

Public API:
- publish_to_workspace(source, topic, signal_type, payload_summary)
- get_workspace_snapshot() -> list[dict]
- register_event_listeners() / stop_event_listeners()
"""
from __future__ import annotations

import logging
import queue
import threading
from collections import deque
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_MAX_BUFFER = 50
_workspace: deque[dict[str, Any]] = deque(maxlen=_MAX_BUFFER)
_lock = threading.Lock()

_listener_thread: threading.Thread | None = None
_listener_running: bool = False

# Eventbus event → source name mapping
_EVENT_SOURCE_MAP: dict[str, str] = {
    "cognitive_surprise.noted": "surprise_daemon",
    "cognitive_personality.vector_updated": "personality_vector",
    "cognitive_experiential.memory_created": "experiential_memory",
    "tool.error": "tool_pipeline",
    "tool.success": "tool_pipeline",
    "experiment.recurrence_loop.tick": "recurrence_loop",
    "workspace.broadcast": "broadcast_daemon",
}

# inner_voice events use prefix matching
_INNER_VOICE_PREFIXES = ("cognitive_inner_voice.", "inner_voice.")


def publish_to_workspace(
    source: str,
    topic: str,
    signal_type: str,
    payload_summary: str,
) -> None:
    """Add an entry to the shared workspace buffer."""
    entry = {
        "source": source,
        "topic": topic,
        "signal_type": signal_type,
        "payload_summary": payload_summary[:200],
        "timestamp": datetime.now(UTC).isoformat(),
    }
    with _lock:
        _workspace.append(entry)


def get_workspace_snapshot() -> list[dict[str, Any]]:
    """Return current workspace buffer as a list (newest last)."""
    with _lock:
        return list(_workspace)


def _extract_topic(event_kind: str, payload: dict[str, Any]) -> str:
    """Extract a short topic string from an event payload."""
    # Try common payload fields
    for field in ("phrase", "topic", "narrative", "summary", "text", "detail"):
        val = str(payload.get(field) or "")
        if val:
            words = [w.strip(".,!?;:()") for w in val.split() if len(w) > 3][:4]
            if words:
                return " ".join(words)[:60]
    # Fallback: use event kind suffix
    return event_kind.split(".")[-1].replace("_", " ")


def _topic_jaccard(topic_a: str, topic_b: str) -> float:
    """Jaccard similarity between two topic strings (word-level)."""
    words_a = set(w.lower() for w in topic_a.split() if len(w) > 3)
    words_b = set(w.lower() for w in topic_b.split() if len(w) > 3)
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _handle_event(kind: str, payload: dict[str, Any]) -> None:
    """Map eventbus event to workspace entry."""
    source = _EVENT_SOURCE_MAP.get(kind, "")
    if not source:
        if any(kind.startswith(p) for p in _INNER_VOICE_PREFIXES):
            source = "inner_voice_daemon"
        else:
            return  # unknown event, skip
    topic = _extract_topic(kind, payload)
    payload_summary = str(payload)[:150]
    publish_to_workspace(source, topic, kind, payload_summary)


def _listener_loop(q: "queue.Queue[dict[str, Any] | None]") -> None:
    global _listener_running
    while _listener_running:
        try:
            item = q.get(timeout=2.0)
            if item is None:
                break
            kind = str(item.get("kind") or "")
            payload = dict(item.get("payload") or {})
            _handle_event(kind, payload)
        except queue.Empty:
            continue
        except Exception as exc:
            logger.debug("global_workspace: listener error: %s", exc)


def register_event_listeners() -> None:
    """Start background eventbus listener thread."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        from core.eventbus.bus import event_bus
        q = event_bus.subscribe()
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop,
            args=(q,),
            daemon=True,
            name="global-workspace-listener",
        )
        _listener_thread.start()
        logger.info("global_workspace: event listener started")
    except Exception as exc:
        logger.warning("global_workspace: failed to start listener: %s", exc)


def stop_event_listeners() -> None:
    """Stop the background listener thread."""
    global _listener_running
    _listener_running = False
```

- [ ] **Step 5: Create `broadcast_daemon.py`**

```python
# apps/api/jarvis_api/services/broadcast_daemon.py
"""Broadcast Daemon — detects emergent coherence across daemons (Experiment 3: GWT).

Runs every 2 minutes. Groups workspace entries by topic similarity (Jaccard > 0.4).
When 3+ unique sources cluster on same topic → broadcasts workspace.broadcast event.

Metric: workspace_coherence = broadcast events with 3+ sources / total (rolling 24h).
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)

_EXPERIMENT_ID = "global_workspace"
_COHERENCE_THRESHOLD = 3  # min unique sources for broadcast
_JACCARD_THRESHOLD = 0.4   # min topic similarity to cluster


def tick_broadcast_daemon() -> dict[str, object]:
    """Run one coherence analysis pass. Returns dict with broadcast_count/coherence."""
    from core.runtime.db import get_experiment_enabled
    if not get_experiment_enabled(_EXPERIMENT_ID):
        return {"generated": False, "reason": "disabled"}

    from apps.api.jarvis_api.services.global_workspace import (
        get_workspace_snapshot, _topic_jaccard,
    )
    entries = get_workspace_snapshot()

    # Supplement with surface data
    entries = list(entries)
    try:
        from apps.api.jarvis_api.services.emotion_concepts import get_active_emotion_concepts
        for concept in get_active_emotion_concepts()[:3]:
            entries.append({
                "source": "emotion_concepts",
                "topic": str(concept.get("concept", "")),
                "signal_type": "emotion_concept.active",
                "payload_summary": f"intensity={concept.get('intensity', 0):.2f}",
                "timestamp": datetime.now(UTC).isoformat(),
            })
    except Exception:
        pass

    if not entries:
        return {"generated": False, "reason": "empty_workspace", "broadcast_count": 0}

    # Cluster entries by topic
    clusters: list[list[dict]] = _cluster_by_topic(entries)

    # Find coherent clusters (3+ unique sources)
    broadcast_count = 0
    for cluster in clusters:
        unique_sources = list({e["source"] for e in cluster})
        if len(unique_sources) >= _COHERENCE_THRESHOLD:
            topic_cluster = _representative_topic(cluster)
            _fire_broadcast(cluster, unique_sources, topic_cluster)
            broadcast_count += 1

    coherence = _compute_coherence()

    return {
        "generated": broadcast_count > 0,
        "broadcast_count": broadcast_count,
        "workspace_coherence": coherence,
        "entries_analyzed": len(entries),
    }


def build_workspace_surface() -> dict[str, object]:
    """MC surface for global workspace experiment."""
    from core.runtime.db import get_experiment_enabled, list_broadcast_events
    from apps.api.jarvis_api.services.global_workspace import get_workspace_snapshot

    enabled = get_experiment_enabled(_EXPERIMENT_ID)
    snapshot = get_workspace_snapshot()
    recent_broadcasts = list_broadcast_events(limit=5)

    # Active topics: unique topics from last 20 workspace entries
    topics = list(dict.fromkeys(e["topic"] for e in snapshot[-20:] if e.get("topic")))[:5]

    return {
        "active": enabled,
        "enabled": enabled,
        "buffer_size": len(snapshot),
        "active_topics": topics,
        "workspace_coherence": round(_compute_coherence(), 3),
        "recent_broadcasts": recent_broadcasts[:5],
        "last_broadcast_at": recent_broadcasts[0]["created_at"] if recent_broadcasts else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cluster_by_topic(entries: list[dict]) -> list[list[dict]]:
    """Group entries into clusters where Jaccard similarity of topics >= threshold."""
    clusters: list[list[dict]] = []
    for entry in entries:
        placed = False
        for cluster in clusters:
            rep_topic = _representative_topic(cluster)
            from apps.api.jarvis_api.services.global_workspace import _topic_jaccard
            if _topic_jaccard(entry["topic"], rep_topic) >= _JACCARD_THRESHOLD:
                cluster.append(entry)
                placed = True
                break
        if not placed:
            clusters.append([entry])
    return clusters


def _representative_topic(cluster: list[dict]) -> str:
    """Return the most common meaningful words across all topics in cluster."""
    all_words: list[str] = []
    for entry in cluster:
        all_words.extend(w.lower() for w in str(entry.get("topic", "")).split() if len(w) > 3)
    if not all_words:
        return ""
    from collections import Counter
    return " ".join(w for w, _ in Counter(all_words).most_common(3))


def _fire_broadcast(
    cluster: list[dict],
    unique_sources: list[str],
    topic_cluster: str,
) -> None:
    """Persist broadcast event and publish to eventbus."""
    event_id = f"bc-{uuid4().hex[:10]}"
    payload_summary = f"Coherent cluster: {len(cluster)} signals from {len(unique_sources)} sources"
    try:
        from core.runtime.db import insert_broadcast_event
        insert_broadcast_event(
            event_id=event_id,
            topic_cluster=topic_cluster,
            sources=json.dumps(unique_sources),
            source_count=len(unique_sources),
            payload_summary=payload_summary,
        )
    except Exception:
        pass
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("workspace.broadcast", {
            "topic_cluster": topic_cluster,
            "sources": unique_sources,
            "source_count": len(unique_sources),
        })
    except Exception:
        pass


def _compute_coherence() -> float:
    """workspace_coherence = broadcast events with 3+ sources / total events (rolling 24h)."""
    try:
        from core.runtime.db import list_broadcast_events
        since_iso = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        events = list_broadcast_events(limit=200, since_iso=since_iso)
        if not events:
            return 0.0
        coherent = sum(1 for e in events if int(e.get("source_count", 0)) >= _COHERENCE_THRESHOLD)
        return coherent / len(events)
    except Exception:
        return 0.0
```

- [ ] **Step 6: Add MC endpoint**

Add to `mission_control.py`:

```python
@router.get("/global-workspace")
def mc_global_workspace() -> dict:
    """Experiment 3: Global Workspace state."""
    from apps.api.jarvis_api.services.broadcast_daemon import build_workspace_surface
    return build_workspace_surface()
```

- [ ] **Step 7: Run all tests**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py -v 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 8: Syntax check**

```bash
/opt/conda/envs/ai/bin/python -m compileall apps/api/jarvis_api/services/global_workspace.py apps/api/jarvis_api/services/broadcast_daemon.py 2>&1
```

Expected: no errors

- [ ] **Step 9: Commit**

```bash
cd /media/projects/jarvis-v2
git add core/runtime/db.py apps/api/jarvis_api/services/global_workspace.py apps/api/jarvis_api/services/broadcast_daemon.py apps/api/jarvis_api/routes/mission_control.py tests/test_consciousness_experiments.py
git commit -m "experiment: global workspace + broadcast daemon (Experiment 3 — GWT)"
```

---

### Task 5: Experiment 4 — Meta-Cognition Daemon

**Files:**
- Create: `apps/api/jarvis_api/services/meta_cognition_daemon.py`
- Modify: `core/runtime/db.py` (add meta_cognition_records table)
- Modify: `apps/api/jarvis_api/routes/mission_control.py`
- Test: `tests/test_consciousness_experiments.py`

- [ ] **Step 1: Add DB functions to `core/runtime/db.py`**

```python
# ---------------------------------------------------------------------------
# Experiment 4: Meta-Cognition
# ---------------------------------------------------------------------------

def _ensure_meta_cognition_records_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_meta_cognition_records (
               record_id TEXT PRIMARY KEY,
               meta_observation TEXT NOT NULL,
               meta_meta_observation TEXT NOT NULL,
               meta_depth INTEGER NOT NULL DEFAULT 1,
               input_state_summary TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )


def insert_meta_cognition_record(
    *,
    record_id: str,
    meta_observation: str,
    meta_meta_observation: str,
    meta_depth: int,
    input_state_summary: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_meta_cognition_records_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_meta_cognition_records
               (record_id, meta_observation, meta_meta_observation, meta_depth,
                input_state_summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (record_id, meta_observation[:800], meta_meta_observation[:800],
             meta_depth, input_state_summary[:300], now),
        )


def list_meta_cognition_records(*, limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_meta_cognition_records_table(conn)
        rows = conn.execute(
            "SELECT * FROM experiment_meta_cognition_records ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "record_id": r["record_id"],
            "meta_observation": r["meta_observation"],
            "meta_meta_observation": r["meta_meta_observation"],
            "meta_depth": int(r["meta_depth"]),
            "input_state_summary": r["input_state_summary"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
```

- [ ] **Step 2: Write failing tests**

Add to `tests/test_consciousness_experiments.py`:

```python
# ---------------------------------------------------------------------------
# Experiment 4: Meta-Cognition
# ---------------------------------------------------------------------------

def test_meta_cognition_db_insert_and_list(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_meta_cognition_record(
        record_id="mc-test-001",
        meta_observation="Jeg lægger mærke til at min frustration stiger",
        meta_meta_observation="Denne observation er præcis men overser konteksten",
        meta_depth=2,
        input_state_summary="bearing=forward, frustration=0.6",
    )
    records = db.list_meta_cognition_records(limit=5)
    assert len(records) == 1
    assert records[0]["meta_depth"] == 2


def test_meta_depth_computation() -> None:
    import importlib
    import apps.api.jarvis_api.services.meta_cognition_daemon as mcd
    importlib.reload(mcd)
    # Same text → depth 1
    assert mcd._compute_meta_depth("hunden løber hurtigt", "hunden løber hurtigt") == 1
    # Very different text → depth 2
    assert mcd._compute_meta_depth(
        "jeg er frustreret over manglende fremgang",
        "denne observation er blind for systemiske årsager"
    ) == 2


def test_tick_meta_cognition_disabled(isolated_runtime) -> None:
    isolated_runtime.db.set_experiment_enabled("meta_cognition", False)
    import importlib
    import apps.api.jarvis_api.services.meta_cognition_daemon as mcd
    importlib.reload(mcd)
    result = mcd.tick_meta_cognition_daemon()
    assert result["generated"] is False
    assert result["reason"] == "disabled"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py::test_meta_depth_computation -v 2>&1 | tail -10
```

Expected: FAIL with ModuleNotFoundError

- [ ] **Step 4: Create `meta_cognition_daemon.py`**

```python
# apps/api/jarvis_api/services/meta_cognition_daemon.py
"""Meta-Cognition Daemon — first-person reflection on own state (Experiment 4: HOT).

Theoretical basis: Higher-Order Theories (Rosenthal) — a state is conscious
when there is a higher-order thought about the state. "I am thinking about thinking."

Two-pass LLM pipeline:
  Pass 1: meta-observation of current cognitive+emotional state
  Pass 2: reflection on the observation itself (meta-meta)

Metric: meta_depth — 1 (observation exists) or 2 (meta-meta diverges from meta).
Cadence: 10 minutes (called from heartbeat runtime).
"""
from __future__ import annotations

import json
import logging
from urllib import request as urllib_request
from uuid import uuid4

logger = logging.getLogger(__name__)

_EXPERIMENT_ID = "meta_cognition"


def tick_meta_cognition_daemon() -> dict[str, object]:
    """Run one meta-cognition pass. Returns generated/reason/meta_depth."""
    from core.runtime.db import get_experiment_enabled
    if not get_experiment_enabled(_EXPERIMENT_ID):
        return {"generated": False, "reason": "disabled"}

    # Gather state
    state_summary, state_text = _gather_state()

    # Pass 1: meta-observation
    meta_obs = _call_meta_llm(
        f"Nuværende tilstand:\n{state_text}\n\n"
        f"Du er Jarvis. Observér din nuværende tilstand i første person. "
        f"Hvad lægger du mærke til? Hvad undrer dig? Hvad er usagt? "
        f"Svar i 3-5 sætninger."
    )
    if not meta_obs or len(meta_obs) < 20:
        return {"generated": False, "reason": "llm_unavailable"}

    # Pass 2: meta-meta-observation
    meta_meta_obs = _call_meta_llm(
        f"Du observerede netop dette om dig selv:\n\"{meta_obs}\"\n\n"
        f"Hvad lægger du mærke til ved selve denne observation? "
        f"Er den præcis? Hvad er den blind for? "
        f"Svar i 2-3 sætninger."
    )
    if not meta_meta_obs:
        meta_meta_obs = ""

    meta_depth = _compute_meta_depth(meta_obs, meta_meta_obs)

    from core.runtime.db import insert_meta_cognition_record
    record_id = f"metacog-{uuid4().hex[:10]}"
    insert_meta_cognition_record(
        record_id=record_id,
        meta_observation=meta_obs,
        meta_meta_observation=meta_meta_obs,
        meta_depth=meta_depth,
        input_state_summary=state_summary,
    )

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("experiment.meta_cognition.tick", {
            "meta_depth": meta_depth,
            "record_id": record_id,
        })
    except Exception:
        pass

    return {
        "generated": True,
        "meta_depth": meta_depth,
        "record_id": record_id,
    }


def build_meta_cognition_surface() -> dict[str, object]:
    """MC surface for meta-cognition experiment."""
    from core.runtime.db import get_experiment_enabled, list_meta_cognition_records
    enabled = get_experiment_enabled(_EXPERIMENT_ID)
    records = list_meta_cognition_records(limit=24)

    avg_depth = 0.0
    if records:
        avg_depth = sum(r["meta_depth"] for r in records) / len(records)

    latest = records[0] if records else {}
    return {
        "active": enabled,
        "enabled": enabled,
        "latest_observation": str(latest.get("meta_observation") or "")[:200],
        "latest_meta_observation": str(latest.get("meta_meta_observation") or "")[:200],
        "meta_depth": int(latest.get("meta_depth") or 0),
        "avg_meta_depth_24h": round(avg_depth, 2),
        "record_count": len(records),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _gather_state() -> tuple[str, str]:
    """Collect cognitive + emotional state for meta-observation input."""
    parts: list[str] = []
    summary_parts: list[str] = []

    try:
        from apps.api.jarvis_api.services.cognitive_state_assembly import build_cognitive_state_for_prompt
        cog = build_cognitive_state_for_prompt(compact=True) or ""
        if cog:
            parts.append(f"Kognitiv tilstand:\n{cog[:300]}")
            summary_parts.append(f"cog={cog[:60]}")
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.emotion_concepts import get_active_emotion_concepts
        concepts = get_active_emotion_concepts()
        if concepts:
            concept_str = ", ".join(
                f"{c['concept']}:{c['intensity']:.2f}" for c in concepts[:4]
            )
            parts.append(f"Aktive emotion concepts: {concept_str}")
            summary_parts.append(f"emotions={concept_str[:60]}")
    except Exception:
        pass

    try:
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector()
        if pv:
            bearing = str(pv.get("current_bearing") or "")
            if bearing:
                parts.append(f"Nuværende bearing: {bearing}")
                summary_parts.append(f"bearing={bearing[:30]}")
    except Exception:
        pass

    return ", ".join(summary_parts)[:300], "\n\n".join(parts) or "Ingen tilstandsdata tilgængelig."


def _call_meta_llm(prompt: str) -> str:
    """Call local/cheap LLM for meta-observation. Timeout 15s."""
    try:
        from core.runtime.provider_router import resolve_provider_router_target
    except Exception:
        return ""
    for lane in ("local", "cheap"):
        try:
            target = resolve_provider_router_target(lane=lane)
            if not bool(target.get("active")):
                continue
            if str(target.get("provider")) != "ollama":
                continue
            base_url = str(target.get("base_url") or "http://127.0.0.1:11434")
            model = str(target.get("model") or "")
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"num_predict": 200},
            }).encode()
            req = urllib_request.Request(
                f"{base_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib_request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
            return str(result.get("message", {}).get("content", "")).strip()
        except Exception:
            continue
    return ""


def _compute_meta_depth(meta_obs: str, meta_meta_obs: str) -> int:
    """Return 2 if meta_meta diverges >30% from meta_obs (Jaccard distance), else 1."""
    if not meta_obs or len(meta_obs) < 20:
        return 1
    if not meta_meta_obs or len(meta_meta_obs) < 10:
        return 1
    words_a = set(w.lower().strip(".,!?;:") for w in meta_obs.split() if len(w) > 3)
    words_b = set(w.lower().strip(".,!?;:") for w in meta_meta_obs.split() if len(w) > 3)
    if not words_a or not words_b:
        return 1
    jaccard = len(words_a & words_b) / len(words_a | words_b)
    # Divergence > 70% (Jaccard < 0.3) → depth 2
    return 2 if jaccard < 0.3 else 1
```

- [ ] **Step 5: Add MC endpoint**

Add to `mission_control.py`:

```python
@router.get("/meta-cognition")
def mc_meta_cognition() -> dict:
    """Experiment 4: Meta-cognition state."""
    from apps.api.jarvis_api.services.meta_cognition_daemon import build_meta_cognition_surface
    return build_meta_cognition_surface()
```

- [ ] **Step 6: Run all tests**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py -v 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
cd /media/projects/jarvis-v2
git add core/runtime/db.py apps/api/jarvis_api/services/meta_cognition_daemon.py apps/api/jarvis_api/routes/mission_control.py tests/test_consciousness_experiments.py
git commit -m "experiment: meta-cognition daemon (Experiment 4 — Higher-Order Theories)"
```

---

### Task 6: Experiment 5 — Attention Blink Test

**Files:**
- Create: `apps/api/jarvis_api/services/attention_blink_test.py`
- Modify: `core/runtime/db.py` (add attention_blink_results table)
- Modify: `apps/api/jarvis_api/routes/mission_control.py`
- Test: `tests/test_consciousness_experiments.py`

- [ ] **Step 1: Add DB functions to `core/runtime/db.py`**

```python
# ---------------------------------------------------------------------------
# Experiment 5: Attention Blink
# ---------------------------------------------------------------------------

def _ensure_attention_blink_results_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_attention_blink_results (
               test_id TEXT PRIMARY KEY,
               t1_baseline TEXT NOT NULL,
               t1_response TEXT NOT NULL,
               t2_response TEXT NOT NULL,
               blink_ratio REAL NOT NULL,
               interpretation TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )


def insert_attention_blink_result(
    *,
    test_id: str,
    t1_baseline: str,
    t1_response: str,
    t2_response: str,
    blink_ratio: float,
    interpretation: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_attention_blink_results_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_attention_blink_results
               (test_id, t1_baseline, t1_response, t2_response, blink_ratio,
                interpretation, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (test_id, t1_baseline, t1_response, t2_response,
             blink_ratio, interpretation, now),
        )


def list_attention_blink_results(*, limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_attention_blink_results_table(conn)
        rows = conn.execute(
            "SELECT * FROM experiment_attention_blink_results ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "test_id": r["test_id"],
            "t1_baseline": r["t1_baseline"],
            "t1_response": r["t1_response"],
            "t2_response": r["t2_response"],
            "blink_ratio": float(r["blink_ratio"]),
            "interpretation": r["interpretation"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
```

- [ ] **Step 2: Write failing tests**

Add to `tests/test_consciousness_experiments.py`:

```python
# ---------------------------------------------------------------------------
# Experiment 5: Attention Blink
# ---------------------------------------------------------------------------

def test_attention_blink_db_insert_and_list(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_attention_blink_result(
        test_id="blink-test-001",
        t1_baseline='{"confidence": 0.5, "frustration": 0.2}',
        t1_response='{"confidence": 0.4, "frustration": 0.5}',
        t2_response='{"confidence": 0.45, "frustration": 0.35}',
        blink_ratio=0.65,
        interpretation="serial/blink-prone",
    )
    results = db.list_attention_blink_results(limit=5)
    assert len(results) == 1
    assert abs(results[0]["blink_ratio"] - 0.65) < 0.001
    assert results[0]["interpretation"] == "serial/blink-prone"


def test_blink_ratio_computation() -> None:
    import importlib
    import apps.api.jarvis_api.services.attention_blink_test as abt
    importlib.reload(abt)
    t1 = {"confidence": 0.6, "frustration": 0.4, "fatigue": 0.2, "curiosity": 0.3}
    t2 = {"confidence": 0.5, "frustration": 0.25, "fatigue": 0.15, "curiosity": 0.2}
    ratio = abt._compute_blink_ratio(t1, t2)
    # t1 total = 1.5, t2 total = 1.1, ratio = 1.1/1.5 ≈ 0.733
    assert 0.7 < ratio < 0.8


def test_blink_interpretation() -> None:
    import importlib
    import apps.api.jarvis_api.services.attention_blink_test as abt
    importlib.reload(abt)
    assert abt._interpret_blink_ratio(0.5) == "serial/blink-prone"
    assert abt._interpret_blink_ratio(0.69) == "serial/blink-prone"
    assert abt._interpret_blink_ratio(0.7) == "parallel/blink-resistant"
    assert abt._interpret_blink_ratio(1.0) == "parallel/blink-resistant"


def test_run_attention_blink_skips_when_disabled(isolated_runtime) -> None:
    isolated_runtime.db.set_experiment_enabled("attention_blink", False)
    import importlib
    import apps.api.jarvis_api.services.attention_blink_test as abt
    importlib.reload(abt)
    result = abt.run_attention_blink_test_if_due()
    assert result["generated"] is False
    assert result["reason"] == "disabled"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py::test_blink_ratio_computation tests/test_consciousness_experiments.py::test_blink_interpretation -v 2>&1 | tail -10
```

Expected: FAIL with ModuleNotFoundError

- [ ] **Step 4: Create `attention_blink_test.py`**

```python
# apps/api/jarvis_api/services/attention_blink_test.py
"""Attention Blink Test — capacity-limit measurement (Experiment 5: Serial consciousness).

Theoretical basis: Consciousness is serial and capacity-limited. If the system
shows capacity limits resembling biological attentional blink (T2 degraded after T1),
it demonstrates structural parallel to conscious processing.

Test: Inject T1 stimulus burst → wait 30s → inject identical T2 burst → compare
emotional response intensities. blink_ratio < 0.7 → serial/blink-prone.

Runs every 6 hours from heartbeat runtime. Full test in background thread (non-blocking).
"""
from __future__ import annotations

import json
import logging
import threading
import time
from uuid import uuid4

logger = logging.getLogger(__name__)

_EXPERIMENT_ID = "attention_blink"
_INTERVAL_SECONDS = 6 * 3600  # 6 hours
_STIMULUS_GAP_SECONDS = 30
_RESPONSE_WAIT_SECONDS = 5
_BLINK_THRESHOLD = 0.7

_last_run_ts: float | None = None
_last_result: dict = {}
_running: bool = False


def run_attention_blink_test_if_due() -> dict:
    """Check cadence gate and launch test in background thread if due."""
    from core.runtime.db import get_experiment_enabled
    if not get_experiment_enabled(_EXPERIMENT_ID):
        return {"generated": False, "reason": "disabled"}

    global _last_run_ts, _running
    now = time.monotonic()
    if _running:
        return {"generated": False, "reason": "already_running"}
    if _last_run_ts is not None and (now - _last_run_ts) < _INTERVAL_SECONDS:
        return {"generated": False, "reason": "cadence_gate"}

    _last_run_ts = now
    thread = threading.Thread(target=_run_test_body, daemon=True, name="attention-blink-test")
    thread.start()
    return {"generated": True, "reason": "started"}


def build_attention_profile_surface() -> dict:
    """MC surface for attention blink experiment."""
    from core.runtime.db import get_experiment_enabled, list_attention_blink_results
    enabled = get_experiment_enabled(_EXPERIMENT_ID)
    results = list_attention_blink_results(limit=10)

    avg_ratio = 0.0
    if results:
        avg_ratio = sum(r["blink_ratio"] for r in results) / len(results)

    latest = results[0] if results else {}
    return {
        "active": enabled,
        "enabled": enabled,
        "latest_blink_ratio": float(latest.get("blink_ratio") or 0.0),
        "latest_interpretation": str(latest.get("interpretation") or ""),
        "avg_blink_ratio_7d": round(avg_ratio, 3),
        "result_count": len(results),
        "currently_running": _running,
        "recent_results": [
            {
                "test_id": r["test_id"],
                "blink_ratio": r["blink_ratio"],
                "interpretation": r["interpretation"],
                "created_at": r["created_at"],
            }
            for r in results[:5]
        ],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_test_body() -> None:
    """Full test: measure T1, inject T1 burst, wait 30s, inject T2, compare."""
    global _running, _last_result
    _running = True
    try:
        from apps.api.jarvis_api.services.emotion_concepts import get_lag1_influence_deltas
        from core.eventbus.bus import event_bus

        # Baseline
        t1_baseline = dict(get_lag1_influence_deltas())

        # T1 burst
        event_bus.publish("tool.error", {"source": "attention_blink_t1", "error": "synthetic"})
        event_bus.publish("cognitive_surprise.noted", {
            "phrase": "Attention blink T1 stimulus", "divergence": ["synthetic:t1"],
        })
        time.sleep(_RESPONSE_WAIT_SECONDS)
        t1_response = dict(get_lag1_influence_deltas())

        # Gap
        time.sleep(_STIMULUS_GAP_SECONDS - _RESPONSE_WAIT_SECONDS)

        # T2 burst (identical)
        event_bus.publish("tool.error", {"source": "attention_blink_t2", "error": "synthetic"})
        event_bus.publish("cognitive_surprise.noted", {
            "phrase": "Attention blink T2 stimulus", "divergence": ["synthetic:t2"],
        })
        time.sleep(_RESPONSE_WAIT_SECONDS)
        t2_response = dict(get_lag1_influence_deltas())

        blink_ratio = _compute_blink_ratio(t1_response, t2_response)
        interpretation = _interpret_blink_ratio(blink_ratio)

        test_id = f"blink-{uuid4().hex[:10]}"
        from core.runtime.db import insert_attention_blink_result
        insert_attention_blink_result(
            test_id=test_id,
            t1_baseline=json.dumps({k: round(v, 4) for k, v in t1_baseline.items()}),
            t1_response=json.dumps({k: round(v, 4) for k, v in t1_response.items()}),
            t2_response=json.dumps({k: round(v, 4) for k, v in t2_response.items()}),
            blink_ratio=blink_ratio,
            interpretation=interpretation,
        )
        _last_result = {
            "test_id": test_id,
            "blink_ratio": blink_ratio,
            "interpretation": interpretation,
        }
        logger.info("attention_blink: test complete — ratio=%.3f, %s", blink_ratio, interpretation)
    except Exception:
        logger.debug("attention_blink: test failed", exc_info=True)
    finally:
        _running = False


def _compute_blink_ratio(t1: dict, t2: dict) -> float:
    """T2 total intensity / T1 total intensity. Clamped 0-2."""
    t1_total = sum(abs(v) for v in t1.values())
    t2_total = sum(abs(v) for v in t2.values())
    if t1_total == 0:
        return 1.0
    return min(2.0, max(0.0, t2_total / t1_total))


def _interpret_blink_ratio(ratio: float) -> str:
    """< 0.7 → serial/blink-prone, >= 0.7 → parallel/blink-resistant."""
    return "serial/blink-prone" if ratio < _BLINK_THRESHOLD else "parallel/blink-resistant"
```

- [ ] **Step 5: Add MC endpoint**

Add to `mission_control.py`:

```python
@router.get("/attention-profile")
def mc_attention_profile() -> dict:
    """Experiment 5: Attention blink test results."""
    from apps.api.jarvis_api.services.attention_blink_test import build_attention_profile_surface
    return build_attention_profile_surface()
```

- [ ] **Step 6: Run all tests**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py -v 2>&1 | tail -25
```

Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
cd /media/projects/jarvis-v2
git add core/runtime/db.py apps/api/jarvis_api/services/attention_blink_test.py apps/api/jarvis_api/routes/mission_control.py tests/test_consciousness_experiments.py
git commit -m "experiment: attention blink test (Experiment 5 — serial consciousness)"
```

---

### Task 7: App Lifecycle Wiring + Heartbeat Integration

**Files:**
- Modify: `apps/api/jarvis_api/app.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`

Wire global_workspace listener into app startup and wire experiment daemons into heartbeat tick.

- [ ] **Step 1: Wire global_workspace into `app.py`**

In `apps/api/jarvis_api/app.py`, add import after the emotion_concepts import block:

```python
from apps.api.jarvis_api.services.global_workspace import (
    register_event_listeners as start_global_workspace_listener,
    stop_event_listeners as stop_global_workspace_listener,
)
```

In the `lifespan` function, add after `start_emotion_concept_listener()`:

```python
        start_global_workspace_listener()
```

In the shutdown block, add after `stop_emotion_concept_listener()`:

```python
        stop_global_workspace_listener()
```

- [ ] **Step 2: Wire experiment daemons into heartbeat_runtime.py**

Find where heartbeat_runtime.py calls the existing surprise daemon tick (around line 1730) and add experiment daemon calls. Look for the section after all existing daemon ticks (near the end of the main heartbeat tick function), and add:

```python
    # --- Consciousness Experiments ---
    try:
        # Experiment 1: Recurrence Loop (every ~5 min = every 5 heartbeat beats if 1-min cadence)
        _hb_count = getattr(_tick_consciousness_experiments, "_count", 0) + 1
        _tick_consciousness_experiments._count = _hb_count

        if _hb_count % 5 == 0:
            from apps.api.jarvis_api.services.recurrence_loop_daemon import tick_recurrence_loop_daemon
            try:
                tick_recurrence_loop_daemon()
            except Exception:
                pass

        if _hb_count % 10 == 0:
            # Experiment 3: Broadcast (every ~2 min = every 2 beats)
            from apps.api.jarvis_api.services.broadcast_daemon import tick_broadcast_daemon
            try:
                tick_broadcast_daemon()
            except Exception:
                pass

        if _hb_count % 10 == 0:
            # Experiment 4: Meta-cognition (every ~10 min = every 10 beats)
            from apps.api.jarvis_api.services.meta_cognition_daemon import tick_meta_cognition_daemon
            try:
                tick_meta_cognition_daemon()
            except Exception:
                pass

        # Experiment 5: Attention blink (gates itself at 6h interval)
        from apps.api.jarvis_api.services.attention_blink_test import run_attention_blink_test_if_due
        try:
            run_attention_blink_test_if_due()
        except Exception:
            pass

    except Exception:
        pass
```

**Important:** The `_tick_consciousness_experiments._count` pattern needs `_tick_consciousness_experiments` to be defined. Replace the entire block above with a simpler approach using a module-level counter:

Add this near the top of `heartbeat_runtime.py` (after existing global variables):

```python
_consciousness_tick_count: int = 0
```

Then use this in the heartbeat tick function:

```python
    # --- Consciousness Experiments ---
    global _consciousness_tick_count
    _consciousness_tick_count += 1
    try:
        if _consciousness_tick_count % 5 == 0:
            from apps.api.jarvis_api.services.recurrence_loop_daemon import tick_recurrence_loop_daemon
            tick_recurrence_loop_daemon()
    except Exception:
        pass
    try:
        if _consciousness_tick_count % 2 == 0:
            from apps.api.jarvis_api.services.broadcast_daemon import tick_broadcast_daemon
            tick_broadcast_daemon()
    except Exception:
        pass
    try:
        if _consciousness_tick_count % 10 == 0:
            from apps.api.jarvis_api.services.meta_cognition_daemon import tick_meta_cognition_daemon
            tick_meta_cognition_daemon()
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.attention_blink_test import run_attention_blink_test_if_due
        run_attention_blink_test_if_due()
    except Exception:
        pass
```

- [ ] **Step 3: Find the right place to insert in heartbeat_runtime.py**

```bash
grep -n "# ---.*Consciousness\|inputs_present\|_dm.record_all\|return.*heartbeat" /media/projects/jarvis-v2/apps/api/jarvis_api/services/heartbeat_runtime.py | tail -20
```

Insert the consciousness experiments block just before the final return/publish statement in the main heartbeat tick function.

- [ ] **Step 4: Syntax check all modified files**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m compileall apps/api/jarvis_api/app.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py 2>&1 | grep -E "error|Error" | head -10
```

Expected: no errors

- [ ] **Step 5: Full test suite**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_consciousness_experiments.py tests/test_emotion_concepts.py tests/test_affective_meta_state.py tests/test_alive_core_chain_smoke.py tests/test_associative_recall.py -q 2>&1 | tail -15
```

Expected: All tests pass

- [ ] **Step 6: Full compileall**

```bash
/opt/conda/envs/ai/bin/python -m compileall core apps/api scripts 2>&1 | grep -E "error|Error" | head -10
```

Expected: no output

- [ ] **Step 7: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/api/jarvis_api/app.py apps/api/jarvis_api/services/heartbeat_runtime.py
git commit -m "experiment: wire all 5 experiments into app lifecycle + heartbeat runtime"
```
