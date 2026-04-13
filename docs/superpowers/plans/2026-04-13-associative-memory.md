# Associative Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dormant associative memory to Jarvis — experiential memories triggered by semantic content, emotional state, and repetition patterns rather than always loaded into context.

**Architecture:** A new `associative_recall.py` coordinator queries the existing `cognitive_experiential_memories` DB table, scores candidates via a local LLM, and maintains in-memory active memories per session. Strong matches (≥0.7) are injected as text into the system prompt via `cognitive_state_assembly.py`; weak matches (0.3–0.69) trigger emotion concepts.

**Tech Stack:** Python 3.11, SQLite (existing `core/runtime/db.py`), Ollama via `resolve_provider_router_target` (same pattern as `personality_vector.py`), `emotion_concepts.trigger_emotion_concept`.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `core/runtime/db.py` | Modify | Add `get_experiential_memory_candidates(limit)` |
| `apps/api/jarvis_api/services/experiential_memory.py` | Modify | Add `score_memories_by_relevance()` |
| `apps/api/jarvis_api/services/associative_recall.py` | Create | Session/message recall coordinator |
| `apps/api/jarvis_api/services/cognitive_state_assembly.py` | Modify | Replace existing experiential block with recall section |
| `tests/test_associative_recall.py` | Create | Tests for all new behavior |

---

### Task 1: DB candidate query

**Files:**
- Modify: `core/runtime/db.py` (after `list_cognitive_experiential_memories` at line ~30222)
- Test: `tests/test_associative_recall.py`

The existing `get_relevant_experiential_memories` does keyword-scored retrieval. We need a separate function that returns a raw candidate pool ordered by importance for LLM scoring.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_associative_recall.py
"""Tests for associative memory recall system."""
from __future__ import annotations
import pytest


def test_get_experiential_memory_candidates_empty(isolated_runtime) -> None:
    db = isolated_runtime.db
    result = db.get_experiential_memory_candidates(limit=20)
    assert result == []


def test_get_experiential_memory_candidates_ordering(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_cognitive_experiential_memory(
        memory_id="mem-low",
        narrative="Low importance memory",
        topic="testing",
        importance=0.3,
    )
    db.insert_cognitive_experiential_memory(
        memory_id="mem-high",
        narrative="High importance memory",
        topic="testing",
        importance=0.9,
    )
    db.insert_cognitive_experiential_memory(
        memory_id="mem-mid",
        narrative="Medium importance memory",
        topic="testing",
        importance=0.6,
    )
    result = db.get_experiential_memory_candidates(limit=20)
    assert len(result) == 3
    # Ordered by importance DESC
    assert result[0]["memory_id"] == "mem-high"
    assert result[1]["memory_id"] == "mem-mid"
    assert result[2]["memory_id"] == "mem-low"
    # Required fields present
    assert "memory_id" in result[0]
    assert "narrative" in result[0]
    assert "topic" in result[0]
    assert "emotion_arc" in result[0]
    assert "key_lesson" in result[0]
    assert "importance" in result[0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_associative_recall.py -v 2>&1 | head -30
```

Expected: FAIL with `AttributeError: module 'core.runtime.db' has no attribute 'get_experiential_memory_candidates'`

- [ ] **Step 3: Add `get_experiential_memory_candidates` to `core/runtime/db.py`**

Add this function after the `list_cognitive_experiential_memories` function (around line 30245):

```python
def get_experiential_memory_candidates(
    *, limit: int = 20
) -> list[dict[str, object]]:
    """Return candidate memories for LLM-based associative scoring.

    Ordered by importance DESC so the most significant memories surface first.
    Returns raw candidates without keyword scoring — the LLM does the scoring.
    """
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        rows = conn.execute(
            """SELECT memory_id, narrative, topic, emotion_arc, key_lesson,
                      importance, decay_score, reinforcement_count
               FROM cognitive_experiential_memories
               WHERE decay_score < 0.95
               ORDER BY importance DESC, reinforcement_count DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "memory_id": r["memory_id"],
            "narrative": str(r["narrative"] or ""),
            "topic": str(r["topic"] or ""),
            "emotion_arc": str(r["emotion_arc"] or ""),
            "key_lesson": str(r["key_lesson"] or ""),
            "importance": float(r["importance"]),
            "decay_score": float(r["decay_score"]),
            "reinforcement_count": int(r["reinforcement_count"]),
        }
        for r in rows
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_associative_recall.py -v 2>&1 | head -30
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2
git add core/runtime/db.py tests/test_associative_recall.py
git commit -m "feat: add get_experiential_memory_candidates DB function"
```

---

### Task 2: LLM scoring in `experiential_memory.py`

**Files:**
- Modify: `apps/api/jarvis_api/services/experiential_memory.py`
- Test: `tests/test_associative_recall.py`

Add LLM-based scoring using the same pattern as `personality_vector._call_llm` and `_resolve_local_llm_target`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_associative_recall.py`:

```python
def test_score_memories_returns_empty_on_no_candidates() -> None:
    import importlib
    import apps.api.jarvis_api.services.experiential_memory as em
    importlib.reload(em)
    result = em.score_memories_by_relevance(
        candidates=[],
        context_text="testing deployment",
        emotional_state={},
    )
    assert result == {}


def test_score_memories_fallback_on_llm_failure(monkeypatch) -> None:
    import importlib
    import apps.api.jarvis_api.services.experiential_memory as em
    importlib.reload(em)

    # Mock LLM to raise
    monkeypatch.setattr(em, "_call_scoring_llm", lambda target, prompt: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(em, "_resolve_scoring_llm_target", lambda: {"active": True, "provider": "ollama", "model": "test", "base_url": "http://localhost:11434"})

    candidates = [
        {"memory_id": "mem-1", "narrative": "We fixed a bug", "topic": "debugging", "emotion_arc": "neutral → relief", "key_lesson": "test more"},
    ]
    result = em.score_memories_by_relevance(
        candidates=candidates,
        context_text="there is a bug",
        emotional_state={"frustration": 0.6},
    )
    assert result == {}


def test_score_memories_parses_llm_response(monkeypatch) -> None:
    import importlib
    import apps.api.jarvis_api.services.experiential_memory as em
    importlib.reload(em)

    llm_response = '{"mem-1": 0.85, "mem-2": 0.3}'
    monkeypatch.setattr(em, "_call_scoring_llm", lambda target, prompt: llm_response)
    monkeypatch.setattr(em, "_resolve_scoring_llm_target", lambda: {"active": True})

    candidates = [
        {"memory_id": "mem-1", "narrative": "bug fix", "topic": "debugging", "emotion_arc": "", "key_lesson": ""},
        {"memory_id": "mem-2", "narrative": "refactor", "topic": "code", "emotion_arc": "", "key_lesson": ""},
    ]
    result = em.score_memories_by_relevance(
        candidates=candidates,
        context_text="we have a bug",
        emotional_state={"frustration": 0.4},
    )
    assert abs(result["mem-1"] - 0.85) < 0.001
    assert abs(result["mem-2"] - 0.3) < 0.001
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_associative_recall.py::test_score_memories_returns_empty_on_no_candidates tests/test_associative_recall.py::test_score_memories_fallback_on_llm_failure tests/test_associative_recall.py::test_score_memories_parses_llm_response -v 2>&1 | head -30
```

Expected: FAIL with `AttributeError: module has no attribute 'score_memories_by_relevance'`

- [ ] **Step 3: Add scoring functions to `experiential_memory.py`**

Add these imports at the top of the file (after existing imports):

```python
import json
from urllib import request as urllib_request
```

Add these functions before the `_safe` helper at the bottom of the file:

```python
def score_memories_by_relevance(
    *,
    candidates: list[dict[str, object]],
    context_text: str,
    emotional_state: dict[str, object],
) -> dict[str, float]:
    """Score candidate memories for relevance using local LLM.

    Returns {memory_id: score} dict with scores 0.0–1.0.
    Returns empty dict if no candidates, LLM unavailable, or LLM call fails.
    """
    if not candidates:
        return {}
    target = _resolve_scoring_llm_target()
    if not target:
        return {}
    prompt = _build_scoring_prompt(candidates, context_text, emotional_state)
    try:
        response = _call_scoring_llm(target, prompt)
        return _parse_scoring_response(response, candidates)
    except Exception:
        logger.debug("experiential_memory: LLM scoring failed", exc_info=True)
        return {}


def _resolve_scoring_llm_target() -> dict[str, object] | None:
    """Resolve local/cheap LLM lane for scoring."""
    try:
        from core.runtime.provider_router import resolve_provider_router_target
        for lane in ("local", "cheap"):
            try:
                target = resolve_provider_router_target(lane=lane)
                if bool(target.get("active")):
                    return target
            except Exception:
                continue
    except Exception:
        pass
    return None


def _build_scoring_prompt(
    candidates: list[dict[str, object]],
    context_text: str,
    emotional_state: dict[str, object],
) -> str:
    """Build LLM prompt for memory relevance scoring."""
    emotion_parts = [
        f"{k}={v:.2f}" for k, v in emotional_state.items()
        if isinstance(v, (int, float)) and v > 0.1
    ]
    emotion_str = ", ".join(emotion_parts) if emotion_parts else "neutral"

    candidate_lines = []
    for c in candidates:
        narrative = str(c.get("narrative") or "")[:80]
        topic = str(c.get("topic") or "")
        emotion_arc = str(c.get("emotion_arc") or "")
        candidate_lines.append(
            f'  "{c["memory_id"]}": topic={topic!r}, narrative={narrative!r}, arc={emotion_arc!r}'
        )
    candidates_str = "\n".join(candidate_lines)

    return (
        f"Current context: {context_text[:200]}\n"
        f"Emotional state: {emotion_str}\n\n"
        f"Score each memory for relevance to the current context (0.0 = irrelevant, 1.0 = highly relevant).\n"
        f"Consider: semantic similarity, emotional resonance, topic overlap.\n\n"
        f"Memories:\n{candidates_str}\n\n"
        f"Return ONLY a JSON object: {{\"memory_id\": score, ...}}\n"
        f"Example: {{\"exp-abc123\": 0.82, \"exp-def456\": 0.15}}"
    )


def _call_scoring_llm(target: dict[str, object], prompt: str) -> str:
    """Call local LLM with scoring prompt. Timeout 15s."""
    provider = str(target.get("provider") or "")
    model = str(target.get("model") or "")
    base_url = str(target.get("base_url") or "")

    if provider == "ollama":
        url = f"{base_url or 'http://127.0.0.1:11434'}/api/chat"
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 300},
        }).encode()
        req = urllib_request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib_request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        return str(result.get("message", {}).get("content", ""))
    return ""


def _parse_scoring_response(
    text: str,
    candidates: list[dict[str, object]],
) -> dict[str, float]:
    """Parse LLM JSON scoring response. Validates memory_ids against candidates."""
    valid_ids = {str(c["memory_id"]) for c in candidates}
    text = text.strip()
    # Strip markdown fences
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.startswith("```")]
        text = "\n".join(lines).strip()
    # Try direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return {
                k: max(0.0, min(1.0, float(v)))
                for k, v in parsed.items()
                if k in valid_ids and isinstance(v, (int, float))
            }
    except Exception:
        pass
    # Try extracting JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                return {
                    k: max(0.0, min(1.0, float(v)))
                    for k, v in parsed.items()
                    if k in valid_ids and isinstance(v, (int, float))
                }
        except Exception:
            pass
    return {}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_associative_recall.py -v 2>&1 | head -40
```

Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/api/jarvis_api/services/experiential_memory.py tests/test_associative_recall.py
git commit -m "feat: add LLM-based memory scoring to experiential_memory"
```

---

### Task 3: `associative_recall.py` coordinator

**Files:**
- Create: `apps/api/jarvis_api/services/associative_recall.py`
- Test: `tests/test_associative_recall.py`

The coordinator manages in-memory active memories, detects topic repetition, and exposes the public API used by `cognitive_state_assembly.py`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_associative_recall.py`:

```python
def _fresh_ar():
    """Return freshly reloaded associative_recall module with empty state."""
    import importlib
    import apps.api.jarvis_api.services.associative_recall as ar
    importlib.reload(ar)
    return ar


def test_build_recall_prompt_section_empty() -> None:
    ar = _fresh_ar()
    result = ar.build_recall_prompt_section()
    assert result == ""


def test_clear_session_recall_resets_state() -> None:
    ar = _fresh_ar()
    # Manually inject a memory
    ar._active_memories["mem-1"] = {
        "memory_id": "mem-1",
        "narrative": "We fixed a bug",
        "topic": "debugging",
        "score": 0.85,
    }
    ar.clear_session_recall()
    assert ar._active_memories == {}
    assert ar.build_recall_prompt_section() == ""


def test_build_recall_prompt_section_formats_correctly() -> None:
    ar = _fresh_ar()
    ar._active_memories["mem-1"] = {
        "memory_id": "mem-1",
        "narrative": "We fixed a critical deployment bug together",
        "topic": "deployment",
        "score": 0.85,
    }
    result = ar.build_recall_prompt_section()
    assert "deployment" in result
    assert "0.85" in result
    assert "mem-1" not in result  # memory_id not exposed to prompt


def test_apply_weak_recall_to_emotions_triggers_concept() -> None:
    import importlib
    import apps.api.jarvis_api.services.emotion_concepts as ec_mod
    importlib.reload(ec_mod)
    ar = _fresh_ar()

    triggered = []
    original = ec_mod.trigger_emotion_concept
    ec_mod.trigger_emotion_concept = lambda concept, intensity, **kw: triggered.append((concept, intensity))

    try:
        memories = [
            {"memory_id": "mem-1", "narrative": "...", "topic": "error", "score": 0.5, "emotion_arc": "frustration → relief"},
        ]
        ar.apply_weak_recall_to_emotions(memories)
    finally:
        ec_mod.trigger_emotion_concept = original

    assert len(triggered) >= 1


def test_cap_enforcement_at_five_memories() -> None:
    ar = _fresh_ar()
    for i in range(5):
        ar._active_memories[f"mem-{i}"] = {
            "memory_id": f"mem-{i}",
            "narrative": f"Memory {i}",
            "topic": "test",
            "score": 0.5 + i * 0.05,
        }
    assert len(ar._active_memories) == 5

    # Adding a 6th via _add_to_active should evict the weakest
    ar._add_to_active({
        "memory_id": "mem-strong",
        "narrative": "Very relevant memory",
        "topic": "test",
        "score": 0.95,
    })
    assert len(ar._active_memories) == 5
    assert "mem-0" not in ar._active_memories  # weakest (0.5) evicted
    assert "mem-strong" in ar._active_memories


def test_topic_repetition_multiplier() -> None:
    ar = _fresh_ar()
    # Simulate 3 messages with same topic
    ar._record_topic("deployment")
    ar._record_topic("deployment")
    ar._record_topic("deployment")
    multiplier = ar._get_topic_multiplier("deployment")
    assert abs(multiplier - 1.5) < 0.001


def test_topic_multiplier_resets_after_ten_messages() -> None:
    ar = _fresh_ar()
    for _ in range(10):
        ar._record_topic("other")
    ar._record_topic("deployment")
    # Counter reset at 10, so deployment count should be 1
    multiplier = ar._get_topic_multiplier("deployment")
    assert multiplier == 1.0  # Not enough repetitions
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_associative_recall.py::test_build_recall_prompt_section_empty tests/test_associative_recall.py::test_clear_session_recall_resets_state tests/test_associative_recall.py::test_cap_enforcement_at_five_memories -v 2>&1 | head -20
```

Expected: FAIL with `ModuleNotFoundError: No module named 'apps.api.jarvis_api.services.associative_recall'`

- [ ] **Step 3: Create `associative_recall.py`**

```python
# apps/api/jarvis_api/services/associative_recall.py
"""Associative Recall — dormant memories triggered by context.

Coordinator that queries the experiential memory DB, scores candidates via
local LLM, and maintains in-memory active memories for the current session.

Strong matches (score ≥ 0.7) are injected as text into the system prompt.
Weak matches (score 0.3–0.69) trigger emotion concepts at proportional intensity.

Max 5 active memories at any time. Weakest is evicted when cap is reached.
Topic repetition: same topic in ≥3 of last 10 messages amplifies scores by ×1.5.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

_MAX_ACTIVE = 5
_STRONG_THRESHOLD = 0.7
_WEAK_THRESHOLD = 0.3
_REPETITION_THRESHOLD = 3
_REPETITION_MULTIPLIER = 1.5
_TOPIC_WINDOW = 10

# In-memory state
_active_memories: dict[str, dict[str, Any]] = {}
_topic_history: deque[str] = deque(maxlen=_TOPIC_WINDOW)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recall_for_session(session_context: dict[str, Any]) -> list[dict[str, Any]]:
    """Run associative recall at session start. Populates up to 3 active memories.

    session_context keys used: channel, bearing, time_of_day (all optional).
    Returns list of memories that were activated.
    """
    from core.runtime.db import get_experiential_memory_candidates
    from apps.api.jarvis_api.services.experiential_memory import score_memories_by_relevance

    candidates = get_experiential_memory_candidates(limit=20)
    if not candidates:
        return []

    context_text = _build_session_context_text(session_context)
    scores = score_memories_by_relevance(
        candidates=candidates,
        context_text=context_text,
        emotional_state={},
    )

    if not scores:
        # Fallback: activate top-3 by importance
        for c in candidates[:3]:
            _add_to_active({**c, "score": c["importance"]})
        return list(_active_memories.values())

    activated = []
    weak = []
    for memory_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
        if not candidate:
            continue
        if score >= _STRONG_THRESHOLD and len(_active_memories) < 3:
            _add_to_active({**candidate, "score": score})
            activated.append({**candidate, "score": score})
        elif score >= _WEAK_THRESHOLD:
            weak.append({**candidate, "score": score})

    if weak:
        apply_weak_recall_to_emotions(weak)

    logger.debug("associative_recall: session init — %d active, %d weak", len(activated), len(weak))
    return activated


def recall_for_message(
    message_text: str,
    emotional_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Run associative recall for a user message. Adds up to 2 active memories.

    Excludes already-active memories from candidate pool.
    Applies topic repetition multiplier to scores.
    Returns list of newly activated memories.
    """
    from core.runtime.db import get_experiential_memory_candidates
    from apps.api.jarvis_api.services.experiential_memory import score_memories_by_relevance
    from core.runtime.db import reinforce_experiential_memory as db_reinforce

    # Extract topic hint from message for repetition tracking
    topic_hint = _extract_topic_hint(message_text)
    if topic_hint:
        _record_topic(topic_hint)

    candidates = get_experiential_memory_candidates(limit=15)
    # Exclude already-active memories
    active_ids = set(_active_memories.keys())
    candidates = [c for c in candidates if c["memory_id"] not in active_ids]

    if not candidates and not active_ids:
        return []

    # Check for re-activation of existing active memories
    for mem_id in list(active_ids):
        mem = _active_memories.get(mem_id)
        if mem and topic_hint and topic_hint.lower() in str(mem.get("topic") or "").lower():
            try:
                db_reinforce(mem_id)
                logger.debug("associative_recall: reinforced existing memory %s", mem_id)
            except Exception:
                pass

    if not candidates:
        return []

    scores = score_memories_by_relevance(
        candidates=candidates,
        context_text=message_text,
        emotional_state=emotional_state,
    )

    if not scores:
        return []

    # Apply topic repetition multiplier
    for memory_id, score in list(scores.items()):
        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
        if candidate:
            topic = str(candidate.get("topic") or "")
            multiplier = _get_topic_multiplier(topic)
            scores[memory_id] = min(1.0, score * multiplier)

    activated = []
    weak = []
    added_count = 0
    for memory_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
        if not candidate:
            continue
        if score >= _STRONG_THRESHOLD and added_count < 2:
            _add_to_active({**candidate, "score": score})
            activated.append({**candidate, "score": score})
            added_count += 1
        elif score >= _WEAK_THRESHOLD:
            weak.append({**candidate, "score": score})

    if weak:
        apply_weak_recall_to_emotions(weak)

    return activated


def build_recall_prompt_section() -> str:
    """Format active memories for system prompt injection.

    Returns empty string if no active memories.
    Format: 'Associative memories (triggered by current context):\\n- ...'
    """
    if not _active_memories:
        return ""

    lines = ["Associative memories (triggered by current context):"]
    for mem in sorted(_active_memories.values(), key=lambda m: m.get("score", 0), reverse=True):
        narrative = str(mem.get("narrative") or "")[:80]
        topic = str(mem.get("topic") or "")
        score = float(mem.get("score") or 0)
        lines.append(f"- {narrative} (topic: {topic}, strength: {score:.2f})")

    return "\n".join(lines)


def apply_weak_recall_to_emotions(memories: list[dict[str, Any]]) -> None:
    """Trigger emotion concepts from weak-scoring memories.

    Maps emotion_arc content to relevant emotion concepts at proportional intensity.
    """
    try:
        from apps.api.jarvis_api.services.emotion_concepts import trigger_emotion_concept
    except Exception:
        return

    for mem in memories:
        score = float(mem.get("score") or 0)
        emotion_arc = str(mem.get("emotion_arc") or "").lower()
        intensity = score * 0.5  # Scale: 0.3 → 0.15, 0.69 → 0.345

        if "frustration" in emotion_arc:
            trigger_emotion_concept("frustration_blocked", intensity, trigger="weak_recall", source="associative_recall")
        elif "relief" in emotion_arc:
            trigger_emotion_concept("relief", intensity, trigger="weak_recall", source="associative_recall")
        elif "indsigt" in emotion_arc or "insight" in emotion_arc:
            trigger_emotion_concept("insight", intensity, trigger="weak_recall", source="associative_recall")
        elif "begejstring" in emotion_arc or "enthusias" in emotion_arc:
            trigger_emotion_concept("anticipation", intensity, trigger="weak_recall", source="associative_recall")
        elif "tilfredshed" in emotion_arc or "satisf" in emotion_arc:
            trigger_emotion_concept("accomplishment", intensity, trigger="weak_recall", source="associative_recall")
        elif "skuffelse" in emotion_arc or "disappoint" in emotion_arc:
            trigger_emotion_concept("doubt", intensity, trigger="weak_recall", source="associative_recall")
        else:
            trigger_emotion_concept("curiosity_narrow", intensity, trigger="weak_recall", source="associative_recall")


def clear_session_recall() -> None:
    """Reset all active memories and topic history. Call at session end."""
    global _topic_history
    _active_memories.clear()
    _topic_history = deque(maxlen=_TOPIC_WINDOW)
    logger.debug("associative_recall: session cleared")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _add_to_active(memory: dict[str, Any]) -> None:
    """Add memory to active set. Evicts weakest if at cap."""
    memory_id = str(memory["memory_id"])
    if len(_active_memories) >= _MAX_ACTIVE and memory_id not in _active_memories:
        # Evict the weakest
        weakest_id = min(
            _active_memories.keys(),
            key=lambda k: float(_active_memories[k].get("score") or 0),
        )
        del _active_memories[weakest_id]
    _active_memories[memory_id] = memory


def _record_topic(topic: str) -> None:
    """Record a topic in the sliding window history."""
    _topic_history.append(topic.lower()[:50])


def _get_topic_multiplier(topic: str) -> float:
    """Return ×1.5 if topic appears ≥3 times in recent history, else ×1.0."""
    if not topic:
        return 1.0
    topic_lower = topic.lower()
    count = sum(1 for t in _topic_history if topic_lower in t or t in topic_lower)
    return _REPETITION_MULTIPLIER if count >= _REPETITION_THRESHOLD else 1.0


def _extract_topic_hint(text: str) -> str:
    """Extract a short topic hint from message text (first meaningful words)."""
    words = [w.strip(".,!?") for w in text.split() if len(w) > 4][:3]
    return " ".join(words)[:40] if words else ""


def _build_session_context_text(session_context: dict[str, Any]) -> str:
    """Build a context description string for session-level scoring."""
    parts = []
    if channel := session_context.get("channel"):
        parts.append(f"channel={channel}")
    if bearing := session_context.get("bearing"):
        parts.append(f"bearing={bearing}")
    if time_of_day := session_context.get("time_of_day"):
        parts.append(f"time={time_of_day}")
    return "Session start. " + ", ".join(parts) if parts else "Session start."
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_associative_recall.py -v 2>&1 | head -50
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/api/jarvis_api/services/associative_recall.py tests/test_associative_recall.py
git commit -m "feat: add associative_recall coordinator service"
```

---

### Task 4: Wire into `cognitive_state_assembly.py`

**Files:**
- Modify: `apps/api/jarvis_api/services/cognitive_state_assembly.py` (lines 289–301)
- Test: `tests/test_associative_recall.py`

Replace the existing basic `experience: lesson` block with the full recall section.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_associative_recall.py`:

```python
def test_cognitive_state_includes_recall_section(isolated_runtime) -> None:
    """When active memories exist, cognitive state includes them."""
    import importlib
    import apps.api.jarvis_api.services.associative_recall as ar_mod
    importlib.reload(ar_mod)

    # Inject an active memory directly
    ar_mod._active_memories["mem-test"] = {
        "memory_id": "mem-test",
        "narrative": "We debugged a tricky race condition together",
        "topic": "concurrency",
        "score": 0.88,
    }

    import apps.api.jarvis_api.services.cognitive_state_assembly as csa
    importlib.reload(csa)

    result = csa.build_cognitive_state_for_prompt(compact=False)
    assert result is not None
    assert "concurrency" in result or "race condition" in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_associative_recall.py::test_cognitive_state_includes_recall_section -v 2>&1 | head -20
```

Expected: FAIL (result doesn't contain memory content)

- [ ] **Step 3: Modify `cognitive_state_assembly.py`**

Add import at the top (after existing imports):

```python
from apps.api.jarvis_api.services.associative_recall import (
    build_recall_prompt_section,
    recall_for_message,
)
```

Find and replace the existing experiential memory block (lines 289–301):

```python
    # --- Relevant Experiential Memory ---
    if not compact and user_mood:
        memories = _safe_call(
            lambda: get_relevant_experiential_memories(
                context=str(user_mood.get("user_message_preview") or ""),
                limit=1,
            )
        )
        if memories:
            lesson = str(memories[0].get("key_lesson") or "")[:80]
            if lesson:
                parts.append(f"experience: {lesson}")
                sources_used.append("experiential")
```

Replace with:

```python
    # --- Associative Memory Recall ---
    if not compact:
        # Trigger per-message recall (updates _active_memories in background-safe way)
        if user_mood:
            message_text = str(user_mood.get("user_message_preview") or "")
            emotional_state = {}
            try:
                from apps.api.jarvis_api.services.affective_meta_state import build_affective_meta_state
                aff = build_affective_meta_state()
                baseline = aff.get("emotional_baseline") or {}
                if isinstance(baseline, dict):
                    emotional_state = {k: float(v) for k, v in baseline.items() if isinstance(v, (int, float))}
            except Exception:
                pass
            _safe_call(lambda: recall_for_message(message_text, emotional_state))

        recall_section = _safe_call(build_recall_prompt_section)
        if recall_section:
            parts.append(recall_section)
            sources_used.append("associative_recall")
```

- [ ] **Step 4: Also remove the now-unused `get_relevant_experiential_memories` import**

In `cognitive_state_assembly.py`, find the imports from `core.runtime.db`:

```python
from core.runtime.db import (
    get_latest_cognitive_personality_vector,
    get_latest_cognitive_taste_profile,
    get_latest_cognitive_chronicle_entry,
    get_latest_cognitive_relationship_texture,
    get_latest_cognitive_compass_state,
    get_latest_cognitive_rhythm_state,
    get_latest_cognitive_user_emotional_state,
    get_relevant_experiential_memories,
    list_cognitive_seeds,
)
```

Remove `get_relevant_experiential_memories,` from that list.

- [ ] **Step 5: Run all tests**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/test_associative_recall.py -v 2>&1 | head -50
```

Expected: All tests PASS

- [ ] **Step 6: Run broader regression test**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/ -v --ignore=tests/test_associative_recall.py -x -q 2>&1 | tail -20
```

Expected: No new failures

- [ ] **Step 7: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/api/jarvis_api/services/cognitive_state_assembly.py tests/test_associative_recall.py
git commit -m "feat: wire associative recall into cognitive state assembly"
```

---

### Task 5: Syntax check and final verification

**Files:**
- No new files

- [ ] **Step 1: Python syntax check across all modified files**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m compileall core apps/api scripts 2>&1 | grep -E "error|Error|SyntaxError" | head -20
```

Expected: No errors

- [ ] **Step 2: Run full test suite**

```bash
cd /media/projects/jarvis-v2
/opt/conda/envs/ai/bin/python -m pytest tests/ -q 2>&1 | tail -20
```

Expected: All tests pass, no regressions

- [ ] **Step 3: Commit final state if any cleanup needed**

```bash
cd /media/projects/jarvis-v2
git status
# Only commit if there are actual changes from cleanup
```
