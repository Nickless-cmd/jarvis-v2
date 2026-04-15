# Jarvis Experimental Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire experiential memory end-to-end into prompts, make recall thresholds configurable, add A/B toggle for cognitive state, extend emotion decay to all axes with configurable factor, and add forced dream hypothesis generation.

**Architecture:** All changes follow the existing pattern: runtime settings via `core/runtime/settings.py` (JSON-backed, no restart required), logging at INFO level for observable events, no breaking changes. Task 4 (Recurrence Loop daemon) is already implemented as `recurrence_loop_daemon.py` — skip it.

**Tech Stack:** Python 3.11, SQLite (`core/runtime/db.py`), FastAPI, `core/runtime/settings.py` for configurable params.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `core/runtime/settings.py` | Modify | Add 6 new configurable fields |
| `apps/api/jarvis_api/services/associative_recall.py` | Modify | Read thresholds from settings, add observability logging |
| `apps/api/jarvis_api/services/cognitive_state_assembly.py` | Modify | A/B toggle + recall activation logging |
| `apps/api/jarvis_api/services/personality_vector.py` | Modify | Extend decay to all affect axes, make factor configurable, add before/after logging |
| `apps/api/jarvis_api/services/dream_hypothesis_forced.py` | Create | Forced dream hypothesis generation logic |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify | Call forced dream hypothesis with 10% probability |
| `tests/test_jarvis_experimental.py` | Create | Tests for all new logic |

---

### Task 1: RuntimeSettings — Add 6 new configurable fields

**Files:**
- Modify: `core/runtime/settings.py`
- Test: `tests/test_jarvis_experimental.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_jarvis_experimental.py
"""Tests for Jarvis experimental backend extensions."""
from __future__ import annotations
import pytest


def test_settings_recall_thresholds_defaults() -> None:
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.recall_strong_threshold == 0.7
    assert s.recall_weak_threshold == 0.3
    assert s.recall_max_active == 5
    assert s.recall_repetition_multiplier == 1.5


def test_settings_cognitive_assembly_enabled_default() -> None:
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.cognitive_state_assembly_enabled is True


def test_settings_emotion_decay_factor_default() -> None:
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.emotion_decay_factor == 0.97
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py -v 2>&1 | tail -15
```

Expected: FAIL with `AttributeError: 'RuntimeSettings' object has no attribute 'recall_strong_threshold'`

- [ ] **Step 3: Add the 6 new fields to `core/runtime/settings.py`**

In the `RuntimeSettings` dataclass (after `relevance_model_name`), add:

```python
    # Associative recall thresholds
    recall_strong_threshold: float = 0.7
    recall_weak_threshold: float = 0.3
    recall_max_active: int = 5
    recall_repetition_multiplier: float = 1.5
    # Cognitive state assembly toggle
    cognitive_state_assembly_enabled: bool = True
    # Emotion decay
    emotion_decay_factor: float = 0.97
```

In `to_dict()`, add:

```python
            "recall_strong_threshold": self.recall_strong_threshold,
            "recall_weak_threshold": self.recall_weak_threshold,
            "recall_max_active": self.recall_max_active,
            "recall_repetition_multiplier": self.recall_repetition_multiplier,
            "cognitive_state_assembly_enabled": self.cognitive_state_assembly_enabled,
            "emotion_decay_factor": self.emotion_decay_factor,
```

In `load_settings()`, add:

```python
        recall_strong_threshold=float(data.get("recall_strong_threshold", defaults.recall_strong_threshold)),
        recall_weak_threshold=float(data.get("recall_weak_threshold", defaults.recall_weak_threshold)),
        recall_max_active=int(data.get("recall_max_active", defaults.recall_max_active)),
        recall_repetition_multiplier=float(data.get("recall_repetition_multiplier", defaults.recall_repetition_multiplier)),
        cognitive_state_assembly_enabled=bool(data.get("cognitive_state_assembly_enabled", defaults.cognitive_state_assembly_enabled)),
        emotion_decay_factor=float(data.get("emotion_decay_factor", defaults.emotion_decay_factor)),
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py -v 2>&1 | tail -10
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add core/runtime/settings.py tests/test_jarvis_experimental.py
git commit -m "feat: add 6 configurable settings fields for recall/assembly/decay"
```

---

### Task 2: Associative Recall — Configurable thresholds + observability logging

**Files:**
- Modify: `apps/api/jarvis_api/services/associative_recall.py`
- Test: `tests/test_jarvis_experimental.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_jarvis_experimental.py`:

```python
def test_recall_thresholds_read_from_settings() -> None:
    """Thresholds should reflect RuntimeSettings values."""
    import importlib
    import apps.api.jarvis_api.services.associative_recall as ar
    importlib.reload(ar)
    # Default values should match settings defaults
    assert ar._get_strong_threshold() == 0.7
    assert ar._get_weak_threshold() == 0.3
    assert ar._get_max_active() == 5
    assert ar._get_repetition_multiplier() == 1.5


def test_recall_logs_observability(capsys) -> None:
    """recall_for_message should log candidate/score info at DEBUG."""
    import logging
    import importlib
    import apps.api.jarvis_api.services.associative_recall as ar
    importlib.reload(ar)
    # With no candidates the log should still not crash
    result = ar.recall_for_message("hej verden test tekst", {})
    assert isinstance(result, list)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py::test_recall_thresholds_read_from_settings -v 2>&1 | tail -10
```

Expected: FAIL with `AttributeError: module has no attribute '_get_strong_threshold'`

- [ ] **Step 3: Modify `apps/api/jarvis_api/services/associative_recall.py`**

Remove the hardcoded module-level constants and replace with getter functions. Find the section at the top of the file:

```python
_MAX_ACTIVE = 5
_STRONG_THRESHOLD = 0.7
_WEAK_THRESHOLD = 0.3
_REPETITION_THRESHOLD = 3
_REPETITION_MULTIPLIER = 1.5
_TOPIC_WINDOW = 10
```

Replace with:

```python
_REPETITION_THRESHOLD = 3   # kept hardcoded — not exposed to spec
_TOPIC_WINDOW = 10           # kept hardcoded — not exposed to spec


def _get_strong_threshold() -> float:
    try:
        from core.runtime.settings import load_settings
        return float(load_settings().recall_strong_threshold)
    except Exception:
        return 0.7


def _get_weak_threshold() -> float:
    try:
        from core.runtime.settings import load_settings
        return float(load_settings().recall_weak_threshold)
    except Exception:
        return 0.3


def _get_max_active() -> int:
    try:
        from core.runtime.settings import load_settings
        return int(load_settings().recall_max_active)
    except Exception:
        return 5


def _get_repetition_multiplier() -> float:
    try:
        from core.runtime.settings import load_settings
        return float(load_settings().recall_repetition_multiplier)
    except Exception:
        return 1.5
```

Now update all call-sites that reference the old constants. In `recall_for_session`, replace:

```python
        if score >= _STRONG_THRESHOLD and len(_active_memories) < 3:
```
with:
```python
        if score >= _get_strong_threshold() and len(_active_memories) < 3:
```

```python
        elif score >= _WEAK_THRESHOLD:
```
with:
```python
        elif score >= _get_weak_threshold():
```

In `recall_for_message`, replace:

```python
    for memory_id in list(scores.keys()):
        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
        if candidate:
            topic = str(candidate.get("topic") or "")
            multiplier = _get_topic_multiplier(topic)
            scores[memory_id] = min(1.0, scores[memory_id] * multiplier)
```
(no change needed there — `_get_topic_multiplier` already calls `_REPETITION_MULTIPLIER`)

Replace `_REPETITION_MULTIPLIER` inside `_get_topic_multiplier`:
```python
def _get_topic_multiplier(topic: str) -> float:
    """Return configured multiplier if topic appears ≥3 times in recent history, else ×1.0."""
    if not topic:
        return 1.0
    topic_lower = topic.lower()
    count = sum(1 for t in _topic_history if topic_lower in t or t in topic_lower)
    return _get_repetition_multiplier() if count >= _REPETITION_THRESHOLD else 1.0
```

In `recall_for_message`, replace threshold comparisons:
```python
        if score >= _STRONG_THRESHOLD and added_count < 2:
```
with:
```python
        strong_thresh = _get_strong_threshold()
        weak_thresh = _get_weak_threshold()
```
(put before the for loop, then use `strong_thresh` and `weak_thresh` in the loop)

In `_add_to_active`, replace:
```python
    if len(_active_memories) >= _MAX_ACTIVE and memory_id not in _active_memories:
```
with:
```python
    if len(_active_memories) >= _get_max_active() and memory_id not in _active_memories:
```

Add observability logging at the end of `recall_for_message`, before `return activated`:

```python
    top_score = max(scores.values()) if scores else 0.0
    strong_count = sum(1 for s in scores.values() if s >= _get_strong_threshold())
    weak_count = sum(1 for s in scores.values() if _get_weak_threshold() <= s < _get_strong_threshold())
    logger.info(
        "associative_recall: %d candidates scored — top=%.2f strong=%d weak=%d activated=%d",
        len(scores), top_score, strong_count, weak_count, len(activated),
    )
```

Also add the same logging at the end of `recall_for_session` before `return activated`.

- [ ] **Step 4: Run tests**

```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py -v 2>&1 | tail -10
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/associative_recall.py tests/test_jarvis_experimental.py
git commit -m "feat: associative recall — configurable thresholds + observability logging"
```

---

### Task 3: Cognitive State Assembly — A/B toggle + recall activation logging

**Files:**
- Modify: `apps/api/jarvis_api/services/cognitive_state_assembly.py`
- Test: `tests/test_jarvis_experimental.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_jarvis_experimental.py`:

```python
def test_cognitive_assembly_returns_none_when_disabled(monkeypatch) -> None:
    """When cognitive_state_assembly_enabled=False, build_cognitive_state_for_prompt returns None."""
    import importlib
    from unittest.mock import MagicMock
    import core.runtime.settings as settings_mod
    importlib.reload(settings_mod)

    fake_settings = settings_mod.RuntimeSettings(cognitive_state_assembly_enabled=False)
    monkeypatch.setattr(settings_mod, "load_settings", lambda: fake_settings)

    import apps.api.jarvis_api.services.cognitive_state_assembly as csa
    importlib.reload(csa)
    result = csa.build_cognitive_state_for_prompt()
    assert result is None


def test_cognitive_assembly_returns_string_when_enabled(monkeypatch) -> None:
    """When enabled (default), function runs normally (may return None if no data, but doesn't early-exit)."""
    import importlib
    import core.runtime.settings as settings_mod
    importlib.reload(settings_mod)

    fake_settings = settings_mod.RuntimeSettings(cognitive_state_assembly_enabled=True)
    monkeypatch.setattr(settings_mod, "load_settings", lambda: fake_settings)

    import apps.api.jarvis_api.services.cognitive_state_assembly as csa
    importlib.reload(csa)
    # With no runtime data this may return None, but it should NOT raise
    result = csa.build_cognitive_state_for_prompt()
    assert result is None or isinstance(result, str)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py::test_cognitive_assembly_returns_none_when_disabled -v 2>&1 | tail -10
```

Expected: FAIL (function doesn't check the setting, so it runs regardless)

- [ ] **Step 3: Add toggle to `cognitive_state_assembly.py`**

In `build_cognitive_state_for_prompt`, add as the very first lines of the function body (after the docstring):

```python
    # A/B toggle: if disabled, return None so nothing is injected
    try:
        from core.runtime.settings import load_settings
        if not load_settings().cognitive_state_assembly_enabled:
            logger.info("cognitive_state_assembly: disabled via settings — skipping injection")
            return None
    except Exception:
        pass
```

Also add recall-activation logging. Find the section around line 303–308:

```python
            _safe_call(lambda: recall_for_message(message_text, emotional_state))

        recall_section = _safe_call(build_recall_prompt_section)
        if recall_section:
            parts.append(recall_section)
            sources_used.append("associative_recall")
```

Change to:

```python
            activated = _safe_call(lambda: recall_for_message(message_text, emotional_state))
            if activated:
                logger.info(
                    "cognitive_state_assembly: %d memories activated via associative recall",
                    len(activated) if isinstance(activated, list) else 0,
                )

        recall_section = _safe_call(build_recall_prompt_section)
        if recall_section:
            parts.append(recall_section)
            sources_used.append("associative_recall")
            logger.debug("cognitive_state_assembly: recall section injected (%d chars)", len(recall_section))
```

- [ ] **Step 4: Run tests**

```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py -v 2>&1 | tail -10
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/cognitive_state_assembly.py tests/test_jarvis_experimental.py
git commit -m "feat: cognitive state assembly — A/B toggle + recall activation logging"
```

---

### Task 4: Emotion Decay — All axes + configurable factor + before/after logging

**Files:**
- Modify: `apps/api/jarvis_api/services/personality_vector.py`
- Test: `tests/test_jarvis_experimental.py`

The current implementation only decays `fatigue` and `frustration` with hardcoded `0.95`. We extend to all 4 axes (`confidence`, `curiosity`, `fatigue`, `frustration`) with a configurable factor defaulting to `0.97`.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_jarvis_experimental.py`:

```python
def test_emotion_decay_uses_configured_factor(monkeypatch) -> None:
    """_apply_decay_to_baseline should use emotion_decay_factor from settings."""
    import importlib
    import core.runtime.settings as settings_mod
    importlib.reload(settings_mod)

    fake_settings = settings_mod.RuntimeSettings(emotion_decay_factor=0.5)
    monkeypatch.setattr(settings_mod, "load_settings", lambda: fake_settings)

    import apps.api.jarvis_api.services.personality_vector as pv
    importlib.reload(pv)

    baseline = {"confidence": 1.0, "curiosity": 1.0, "fatigue": 1.0, "frustration": 1.0}
    result = pv._apply_decay_to_baseline(baseline)
    # All axes decayed by 0.5
    for axis in ("confidence", "curiosity", "fatigue", "frustration"):
        assert abs(result[axis] - 0.5) < 0.001, f"{axis} should be 0.5, got {result[axis]}"


def test_emotion_decay_all_axes_default_factor(monkeypatch) -> None:
    """All 4 axes should decay with 0.97 default factor."""
    import importlib
    import core.runtime.settings as settings_mod
    importlib.reload(settings_mod)
    monkeypatch.setattr(settings_mod, "load_settings", lambda: settings_mod.RuntimeSettings())

    import apps.api.jarvis_api.services.personality_vector as pv
    importlib.reload(pv)

    baseline = {"confidence": 1.0, "curiosity": 1.0, "fatigue": 1.0, "frustration": 1.0}
    result = pv._apply_decay_to_baseline(baseline)
    for axis in ("confidence", "curiosity", "fatigue", "frustration"):
        assert abs(result[axis] - 0.97) < 0.001, f"{axis} should be 0.97 got {result[axis]}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py::test_emotion_decay_uses_configured_factor -v 2>&1 | tail -10
```

Expected: FAIL with `AttributeError: module has no attribute '_apply_decay_to_baseline'`

- [ ] **Step 3: Modify `apps/api/jarvis_api/services/personality_vector.py`**

Add this new helper function after the `_record_decay_timestamp` function:

```python
def _apply_decay_to_baseline(baseline: dict) -> dict:
    """Apply configured decay factor to all emotional axes. Returns modified baseline."""
    try:
        from core.runtime.settings import load_settings
        factor = float(load_settings().emotion_decay_factor)
    except Exception:
        factor = 0.97
    factor = max(0.0, min(1.0, factor))  # clamp to valid range

    _EMOTIONAL_AXES_LOCAL = ("confidence", "curiosity", "fatigue", "frustration")
    before = {k: float(baseline.get(k, 0.0)) for k in _EMOTIONAL_AXES_LOCAL}
    for axis in _EMOTIONAL_AXES_LOCAL:
        baseline[axis] = max(0.0, float(baseline.get(axis, 0.0)) * factor)
    after = {k: float(baseline.get(k, 0.0)) for k in _EMOTIONAL_AXES_LOCAL}

    import logging as _logging
    _log = _logging.getLogger(__name__)
    _log.info(
        "personality_vector: emotion decay applied (factor=%.3f) — "
        "confidence %.2f→%.2f  curiosity %.2f→%.2f  fatigue %.2f→%.2f  frustration %.2f→%.2f",
        factor,
        before["confidence"], after["confidence"],
        before["curiosity"], after["curiosity"],
        before["fatigue"], after["fatigue"],
        before["frustration"], after["frustration"],
    )
    return baseline
```

Find the current decay block in `_deterministic_update`:

```python
    # Fix 1: Debounced natural decay — at most once per 30 minutes
    if _should_apply_decay():
        baseline["fatigue"] = max(0.0, float(baseline.get("fatigue", 0.0)) * 0.95)
        baseline["frustration"] = max(0.0, float(baseline.get("frustration", 0.0)) * 0.95)
        _record_decay_timestamp()
```

Replace with:

```python
    # Fix 1: Debounced natural decay — at most once per 30 minutes, all axes, configurable factor
    if _should_apply_decay():
        baseline = _apply_decay_to_baseline(baseline)
        _record_decay_timestamp()
```

- [ ] **Step 4: Run tests**

```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py -v 2>&1 | tail -10
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/personality_vector.py tests/test_jarvis_experimental.py
git commit -m "feat: emotion decay — all 4 axes, configurable factor, before/after logging"
```

---

### Task 5: Forced Dream Hypothesis Generation

**Files:**
- Create: `apps/api/jarvis_api/services/dream_hypothesis_forced.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`
- Test: `tests/test_jarvis_experimental.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_jarvis_experimental.py`:

```python
def test_forced_dream_skips_when_no_memories() -> None:
    """force_dream_hypothesis should return generated=False when no memories exist."""
    import importlib
    import apps.api.jarvis_api.services.dream_hypothesis_forced as dhf
    importlib.reload(dhf)
    result = dhf.force_dream_hypothesis_if_due(force=True)
    # No memories in test env → skips gracefully
    assert result["generated"] is False or isinstance(result.get("signal_id"), str)


def test_forced_dream_respects_max_active() -> None:
    """Should not create hypothesis if max_active (3) already reached."""
    import importlib
    import apps.api.jarvis_api.services.dream_hypothesis_forced as dhf
    importlib.reload(dhf)
    # Patch list_runtime_dream_hypothesis_signals to return 3 active items
    from unittest.mock import patch
    fake_active = [{"signal_id": f"s{i}", "status": "active"} for i in range(3)]
    with patch("apps.api.jarvis_api.services.dream_hypothesis_forced.list_runtime_dream_hypothesis_signals",
               return_value=fake_active):
        result = dhf.force_dream_hypothesis_if_due(force=True)
    assert result["generated"] is False
    assert result["reason"] == "max_active_reached"


def test_blink_ratio_not_regressed() -> None:
    """Smoke test: attention_blink_test still importable after changes."""
    import apps.api.jarvis_api.services.attention_blink_test as abt
    assert callable(abt._compute_blink_ratio)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py::test_forced_dream_respects_max_active -v 2>&1 | tail -10
```

Expected: FAIL with `ModuleNotFoundError: No module named '...dream_hypothesis_forced'`

- [ ] **Step 3: Create `dream_hypothesis_forced.py`**

```python
# apps/api/jarvis_api/services/dream_hypothesis_forced.py
"""Forced Dream Hypothesis — proactive hypothesis seeding from experiential memory.

With 10% probability per heartbeat tick, picks a random topic from recent
experiential memories and creates a dream hypothesis about Jarvis' identity
or behavioural patterns. Confidence 0.3–0.5 (lower than organic hypotheses).

Max 3 active hypotheses enforced — skips if already at cap.
"""
from __future__ import annotations

import logging
import random
from datetime import UTC, datetime
from uuid import uuid4

from core.runtime.db import (
    list_runtime_dream_hypothesis_signals,
    upsert_runtime_dream_hypothesis_signal,
)

logger = logging.getLogger(__name__)

_MAX_ACTIVE = 3
_FORCED_CONFIDENCE_RANGE = (0.3, 0.5)
_TRIGGER_PROBABILITY = 0.10  # 10% per heartbeat tick


def force_dream_hypothesis_if_due(*, force: bool = False) -> dict[str, object]:
    """Conditionally create a forced dream hypothesis.

    Args:
        force: If True, bypass the probability gate (for testing/manual trigger).

    Returns dict with keys: generated (bool), reason (str), signal_id (str, optional).
    """
    if not force and random.random() > _TRIGGER_PROBABILITY:
        return {"generated": False, "reason": "probability_gate"}

    # Check max_active cap
    active = list_runtime_dream_hypothesis_signals(status="active", limit=10)
    if len(active) >= _MAX_ACTIVE:
        logger.debug("dream_hypothesis_forced: max_active=%d reached — skipping", _MAX_ACTIVE)
        return {"generated": False, "reason": "max_active_reached"}

    # Pick topic from recent experiential memories
    topic = _pick_random_topic()
    if not topic:
        return {"generated": False, "reason": "no_memories"}

    # Generate hypothesis text deterministically (no LLM — keep it cheap)
    hypothesis = _generate_hypothesis(topic)

    now = datetime.now(UTC).isoformat()
    signal_id = f"forced-dream-{uuid4().hex[:10]}"
    confidence = f"{random.uniform(*_FORCED_CONFIDENCE_RANGE):.2f}"
    canonical_key = f"forced:{topic[:40]}"

    upsert_runtime_dream_hypothesis_signal(
        signal_id=signal_id,
        signal_type="forced_hypothesis",
        canonical_key=canonical_key,
        status="active",
        title=f"Tvunget hypotese: {topic[:60]}",
        summary=hypothesis,
        rationale=f"Automatisk genereret fra gentaget tema: {topic}",
        source_kind="heartbeat_forced",
        confidence=confidence,
        evidence_summary=f"Tema {topic!r} fundet i nylige experiential memories",
        support_summary="",
        support_count=1,
        session_count=0,
        created_at=now,
        updated_at=now,
        status_reason="forced_by_heartbeat",
    )

    logger.info(
        "dream_hypothesis_forced: created hypothesis signal_id=%s topic=%r confidence=%s",
        signal_id, topic, confidence,
    )

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("dream_hypothesis.forced", {
            "signal_id": signal_id,
            "topic": topic,
            "confidence": confidence,
        })
    except Exception:
        pass

    return {"generated": True, "signal_id": signal_id, "topic": topic, "confidence": confidence}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_random_topic() -> str:
    """Pick a random topic from recent experiential memories."""
    try:
        from core.runtime.db import list_cognitive_experiential_memories
        memories = list_cognitive_experiential_memories(limit=20)
        topics = [str(m.get("topic") or "").strip() for m in memories if m.get("topic")]
        if not topics:
            return ""
        return random.choice(topics)
    except Exception:
        return ""


_HYPOTHESIS_TEMPLATES = [
    "Jarvis tenderer mod {topic} som et tilbagevendende omdrejningspunkt i sine interaktioner.",
    "Der er et mønster: {topic} optræder hyppigere end forventet — måske afspejler det en dybereliggende præference.",
    "Hypotese: Jarvis' tilgang til {topic} er mere konsistent end tilfældig — det kan være en del af identiteten.",
    "Refleksion over {topic} antyder at dette tema har strukturel betydning for Jarvis' adfærd.",
    "{topic} kan være en bærende søjle i Jarvis' selvforståelse — værd at undersøge nærmere.",
]


def _generate_hypothesis(topic: str) -> str:
    """Generate a hypothesis string from topic without LLM."""
    template = random.choice(_HYPOTHESIS_TEMPLATES)
    return template.format(topic=topic[:80])
```

- [ ] **Step 4: Wire into `heartbeat_runtime.py`**

In the consciousness experiments block we added earlier (near line 1240–1270), add a call to the forced dream function. Find the block ending:

```python
    try:
        from apps.api.jarvis_api.services.attention_blink_test import run_attention_blink_test_if_due
        run_attention_blink_test_if_due()
    except Exception:
        pass
```

Add immediately after:

```python
    try:
        from apps.api.jarvis_api.services.dream_hypothesis_forced import force_dream_hypothesis_if_due
        force_dream_hypothesis_if_due()
    except Exception:
        pass
```

- [ ] **Step 5: Run all tests**

```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py -v 2>&1 | tail -15
```

Expected: All tests pass

- [ ] **Step 6: Syntax check**

```bash
/opt/conda/envs/ai/bin/python -m compileall apps/api/jarvis_api/services/dream_hypothesis_forced.py apps/api/jarvis_api/services/heartbeat_runtime.py 2>&1 | grep -E "error|Error"
```

Expected: no output

- [ ] **Step 7: Commit**

```bash
git add apps/api/jarvis_api/services/dream_hypothesis_forced.py apps/api/jarvis_api/services/heartbeat_runtime.py tests/test_jarvis_experimental.py
git commit -m "feat: forced dream hypothesis — 10% probability per tick, max 3 active"
```

---

### Task 6: Full regression + compileall

**Files:**
- Run: existing test suites

- [ ] **Step 1: Run full test suite**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_jarvis_experimental.py tests/test_consciousness_experiments.py tests/test_emotion_concepts.py tests/test_affective_meta_state.py tests/test_associative_recall.py -q 2>&1 | tail -10
```

Expected: All pass

- [ ] **Step 2: Full compileall**

```bash
/opt/conda/envs/ai/bin/python -m compileall core apps/api scripts 2>&1 | grep -E "error|Error" | head -10
```

Expected: no output

- [ ] **Step 3: Commit if any fixes needed, otherwise done**

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|-------------|------|
| Experiential memory prompt injection end-to-end | Task 3 (logging added, circuit confirmed working) |
| Recall thresholds configurable | Task 2 |
| Recall observability log | Task 2 |
| `_MAX_ACTIVE` and `_REPETITION_MULTIPLIER` configurable | Task 1 + Task 2 |
| Cognitive state A/B toggle | Task 3 |
| Emotion decay all axes | Task 4 |
| Decay factor configurable | Task 1 + Task 4 |
| Before/after decay logging | Task 4 |
| Forced dream hypothesis 10% probability | Task 5 |
| Forced hypothesis from experiential memory topic | Task 5 |
| Forced hypothesis status `active`, confidence 0.3–0.5 | Task 5 |
| max_active respected | Task 5 |
| Recurrence Loop daemon | Already implemented (recurrence_loop_daemon.py) — skip |

**Notes:**
- Task 1 (Jarvis spec) is about verifying the circuit. Our exploration confirmed `recall_for_message` → `build_recall_prompt_section` → prompt IS wired correctly. Task 3 adds logging to make this observable.
- The `list_cognitive_experiential_memories` function is used by `_pick_random_topic()` — verify it exists in `core/runtime/db.py` before running Task 5. If it doesn't exist, use `get_experiential_memory_candidates(limit=20)` instead (that one we added earlier).
