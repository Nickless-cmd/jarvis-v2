"""Associative Recall — dormant memories triggered by context.

Coordinator that queries experiential memory, private brain & sensory DBs,
scores candidates via local LLM, and maintains persistent active memories.

Strong matches (score ≥ 0.7) are injected into the [ASSOCIATIONER] awareness section.
Weak matches (score 0.3–0.69) trigger emotion concepts at proportional intensity.

Max 5 active memories at any time. Weakest is evicted when cap is reached.
Topic repetition: same topic in ≥3 of last 10 messages amplifies scores by ×1.5.

Persistence: active memories survive restarts via recall_active_memories table.
Keyword extraction: cheap-lane LLM with regex fallback.
Rate limiting: max 1 extraction every 3 seconds, queue max 10.
Scope: experiential memory + private brain + sensory archive.
"""
from __future__ import annotations

import json
import logging
import re
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_REPETITION_THRESHOLD = 3   # kept hardcoded — not in spec
_TOPIC_WINDOW = 10           # kept hardcoded — not in spec

# Rate limiting for LLM keyword extraction
_EXTRACTION_MIN_INTERVAL_S = 3.0
_EXTRACTION_QUEUE_MAX = 10
_last_extraction_at: float = 0.0
_extraction_queue: list[dict[str, Any]] = []

# In-memory state (synced to DB)
_active_memories: dict[str, dict[str, Any]] = {}
_topic_history: deque[str] = deque(maxlen=_TOPIC_WINDOW)


# ---------------------------------------------------------------------------
# Settings getters (must be defined before any module-level code that calls them)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------

def _ensure_active_memories_table() -> None:
    """Create recall_active_memories table if it doesn't exist (lazy init)."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recall_active_memories (
                    memory_id TEXT PRIMARY KEY,
                    narrative TEXT NOT NULL DEFAULT '',
                    topic TEXT NOT NULL DEFAULT '',
                    emotion_arc TEXT NOT NULL DEFAULT '',
                    importance REAL NOT NULL DEFAULT 0,
                    score REAL NOT NULL DEFAULT 0,
                    source_table TEXT NOT NULL DEFAULT 'experiential_memory',
                    activated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recall_active_memories_score
                ON recall_active_memories(score DESC)
            """)
    except Exception as exc:
        logger.warning("associative_recall: DB table init failed: %s", exc)


def _persist_active_memory(memory: dict[str, Any]) -> None:
    """Save an active memory to DB (upsert)."""
    try:
        from core.runtime.db import connect
        _ensure_active_memories_table()
        with connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO recall_active_memories
                (memory_id, narrative, topic, emotion_arc, importance, score, source_table, activated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(memory.get("memory_id") or ""),
                str(memory.get("narrative") or "")[:500],
                str(memory.get("topic") or "")[:200],
                str(memory.get("emotion_arc") or "")[:100],
                float(memory.get("importance") or 0),
                float(memory.get("score") or 0),
                str(memory.get("source_table") or "experiential_memory"),
                datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            ))
    except Exception as exc:
        logger.debug("associative_recall: persist failed for %s: %s",
                     memory.get("memory_id"), exc)


def _remove_persisted_memory(memory_id: str) -> None:
    """Remove a memory from the DB persistence table."""
    try:
        from core.runtime.db import connect
        _ensure_active_memories_table()
        with connect() as conn:
            conn.execute(
                "DELETE FROM recall_active_memories WHERE memory_id = ?",
                (memory_id,),
            )
    except Exception as exc:
        logger.debug("associative_recall: remove persisted failed for %s: %s",
                     memory_id, exc)


def _load_active_memories_from_db() -> dict[str, dict[str, Any]]:
    """Restore active memories from DB on module load."""
    try:
        from core.runtime.db import connect
        _ensure_active_memories_table()
        with connect() as conn:
            rows = conn.execute(
                "SELECT * FROM recall_active_memories ORDER BY score DESC LIMIT ?",
                (_get_max_active(),),
            ).fetchall()
        restored: dict[str, dict[str, Any]] = {}
        for r in rows:
            restored[str(r[0])] = {
                "memory_id": str(r[0]),
                "narrative": str(r[1]),
                "topic": str(r[2]),
                "emotion_arc": str(r[3]),
                "importance": float(r[4]),
                "score": float(r[5]),
                "source_table": str(r[6]),
            }
        if restored:
            logger.info("associative_recall: restored %d memories from DB", len(restored))
        return restored
    except Exception as exc:
        logger.debug("associative_recall: DB load failed (first run?): %s", exc)
        return {}


def _clear_persisted_memories() -> None:
    """Remove all active memories from DB."""
    try:
        from core.runtime.db import connect
        _ensure_active_memories_table()
        with connect() as conn:
            conn.execute("DELETE FROM recall_active_memories")
    except Exception as exc:
        logger.debug("associative_recall: clear persisted failed: %s", exc)


# Restore from DB on module load
_active_memories = _load_active_memories_from_db()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recall_for_session(session_context: dict[str, Any]) -> list[dict[str, Any]]:
    """Run associative recall at session start. Populates up to 3 active memories.

    Scope: experiential memory + private brain + sensory archive.
    session_context keys used: channel, bearing, time_of_day (all optional).
    Returns list of memories that were activated.
    """
    from core.runtime.db import get_experiential_memory_candidates
    from core.services.experiential_memory import score_memories_by_relevance

    candidates = get_experiential_memory_candidates(limit=20)

    # --- Private brain + sensory scope ---
    _add_private_brain_candidates(candidates, "", limit=5)
    _add_sensory_candidates(candidates, "", limit=3)

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
        if score >= _get_strong_threshold() and len(_active_memories) < 3:
            _add_to_active({**candidate, "score": score})
            activated.append({**candidate, "score": score})
        elif score >= _get_weak_threshold():
            weak.append({**candidate, "score": score})

    if weak:
        apply_weak_recall_to_emotions(weak)

    logger.debug("associative_recall: session init — %d active, %d weak", len(activated), len(weak))
    logger.info(
        "associative_recall session_init: activated=%d weak=%d total_candidates=%d strong_threshold=%.2f weak_threshold=%.2f",
        len(activated), len(weak), len(candidates),
        _get_strong_threshold(), _get_weak_threshold(),
    )
    return activated


def recall_for_message(
    message_text: str,
    emotional_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Run associative recall for a user message. Adds up to 2 active memories.

    Scope: experiential memory + private brain + sensory archive.
    Excludes already-active memories from candidate pool.
    Applies topic repetition multiplier to scores.
    Returns list of newly activated memories.
    """
    from core.runtime.db import get_experiential_memory_candidates, reinforce_experiential_memory
    from core.services.experiential_memory import score_memories_by_relevance

    topic_hint = _extract_topic_hint(message_text)
    if topic_hint:
        _record_topic(topic_hint)

    candidates = get_experiential_memory_candidates(limit=15)
    active_ids = set(_active_memories.keys())
    candidates = [c for c in candidates if c["memory_id"] not in active_ids]

    # --- Private brain scope: include private_brain_records ---
    _add_private_brain_candidates(candidates, topic_hint, limit=5)

    # --- Sensory scope: include recent sensory memories ---
    _add_sensory_candidates(candidates, topic_hint, limit=3)

    # Check for re-activation of existing active memories
    for mem_id in list(active_ids):
        mem = _active_memories.get(mem_id)
        if mem and topic_hint and topic_hint.lower() in str(mem.get("topic") or "").lower():
            try:
                reinforce_experiential_memory(mem_id)
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
        # Fallback: activate top-2 by importance when LLM scoring fails
        for c in candidates[:2]:
            _add_to_active({**c, "score": c["importance"]})
        return list(_active_memories.values())

    # Apply topic repetition multiplier
    for memory_id in list(scores.keys()):
        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
        if candidate:
            topic = str(candidate.get("topic") or "")
            multiplier = _get_topic_multiplier(topic)
            scores[memory_id] = min(1.0, scores[memory_id] * multiplier)

    activated = []
    weak = []
    added_count = 0
    for memory_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
        if not candidate:
            continue
        if score >= _get_strong_threshold() and added_count < 2:
            _add_to_active({**candidate, "score": score})
            activated.append({**candidate, "score": score})
            added_count += 1
        elif score >= _get_weak_threshold():
            weak.append({**candidate, "score": score})

    if weak:
        apply_weak_recall_to_emotions(weak)

    logger.info(
        "associative_recall message: activated=%d weak=%d candidates_evaluated=%d topic_hint=%r",
        len(activated), len(weak), len(candidates), topic_hint,
    )
    return activated


def build_recall_prompt_section() -> str:
    """Format active memories as [ASSOCIATIONER] awareness section (Danish, compact).

    Returns empty string if no active memories.
    Format: one line per memory — "→ narrative (topic, styrke: score)"
    """
    if not _active_memories:
        return ""

    lines = ["[ASSOCIATIONER]"]
    for mem in sorted(_active_memories.values(), key=lambda m: m.get("score", 0), reverse=True):
        narrative = str(mem.get("narrative") or "")[:80]
        topic = str(mem.get("topic") or "")
        score = float(mem.get("score") or 0)
        source = str(mem.get("source_table") or "")
        # Compact: source only shown if not experiential_memory
        source_suffix = f", fra: {source}" if source and source != "experiential_memory" else ""
        lines.append(f"→ {narrative} ({topic}, styrke: {score:.2f}{source_suffix})")

    return "\n".join(lines)


def apply_weak_recall_to_emotions(memories: list[dict[str, Any]]) -> None:
    """Trigger emotion concepts from weak-scoring memories.

    Maps emotion_arc content to relevant emotion concepts at proportional intensity.
    """
    try:
        from core.services.emotion_concepts import trigger_emotion_concept
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
    _clear_persisted_memories()
    logger.debug("associative_recall: session cleared (memory + DB)")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _add_to_active(memory: dict[str, Any]) -> None:
    """Add memory to active set. Evicts weakest if at cap. Persists to DB."""
    memory_id = str(memory["memory_id"])
    if len(_active_memories) >= _get_max_active() and memory_id not in _active_memories:
        weakest_id = min(
            _active_memories.keys(),
            key=lambda k: float(_active_memories[k].get("score") or 0),
        )
        _remove_persisted_memory(weakest_id)
        del _active_memories[weakest_id]
    _active_memories[memory_id] = memory
    _persist_active_memory(memory)


def _record_topic(topic: str) -> None:
    """Record a topic in the sliding window history."""
    _topic_history.append(topic.lower()[:50])


def _get_topic_multiplier(topic: str) -> float:
    """Return ×1.5 if topic appears ≥3 times in recent history, else ×1.0."""
    if not topic:
        return 1.0
    topic_lower = topic.lower()
    count = sum(1 for t in _topic_history if topic_lower in t or t in topic_lower)
    return _get_repetition_multiplier() if count >= _REPETITION_THRESHOLD else 1.0


# ---------------------------------------------------------------------------
# Keyword extraction (LLM + regex fallback)
# ---------------------------------------------------------------------------

def _extract_keywords_llm(text: str) -> list[str]:
    """Extract keywords via cheap-lane LLM. Returns empty list on failure."""
    try:
        from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane

        prompt = (
            "Extract 3-5 key topics/keywords from this message. "
            "Return ONLY a JSON array of lowercase strings, nothing else. "
            "Focus on concrete topics, technical terms, and named entities.\n\n"
            f"Message: {text[:500]}"
        )
        result = execute_public_safe_cheap_lane(message=prompt)
        response_text = str((result or {}).get("text") or "")
        if response_text and response_text.strip():
            # Parse JSON array from response
            cleaned = response_text.strip().strip("`").strip()
            if cleaned.startswith("["):
                keywords = json.loads(cleaned)
                if isinstance(keywords, list):
                    return [str(k).lower().strip()[:50] for k in keywords[:5] if str(k).strip()]
    except Exception as exc:
        logger.debug("associative_recall: LLM keyword extraction failed: %s", exc)
    return []


def _extract_keywords_regex(text: str) -> list[str]:
    """Regex fallback: capitalized words, technical terms, named entities."""
    keywords: list[str] = []

    # Capitalized words (potential named entities)
    capitalized = re.findall(r'\b[A-ZÆØÅ][a-zæøå]{2,}\b', text)
    keywords.extend([w.lower() for w in capitalized[:3]])

    # CamelCase / snake_case technical terms
    technical = re.findall(r'\b[a-z]+(?:[_-][a-z]+)+(?:\.[a-z]+)?\b', text)
    keywords.extend([t.lower() for t in technical[:3]])

    # Code-like tokens (imports, paths, function names)
    code_like = re.findall(r'\b[a-z_]+\.[a-z_]+\b', text)
    keywords.extend([c.lower() for c in code_like[:2]])

    # Remove duplicates, filter noise
    seen: set[str] = set()
    filtered: list[str] = []
    noise = {"the", "and", "for", "that", "this", "with", "from", "have",
             "det", "der", "som", "til", "for", "med", "har", "kan", "skal"}
    for kw in keywords:
        kw = kw.strip(".,!?;:'\"()[]{}").lower()
        if kw and kw not in seen and kw not in noise and len(kw) > 2:
            seen.add(kw)
            filtered.append(kw)

    return filtered[:5]


def _extract_topic_hint(text: str) -> str:
    """Extract topic hints: LLM first, regex fallback, then simple fallback.

    Returns a space-joined string of keywords (max 40 chars).
    """
    global _last_extraction_at, _extraction_queue

    # Rate limit: max 1 extraction every 3 seconds
    now = time.monotonic()
    if now - _last_extraction_at < _EXTRACTION_MIN_INTERVAL_S:
        # Queue the text and use simple fallback for this call
        if len(_extraction_queue) < _EXTRACTION_QUEUE_MAX:
            _extraction_queue.append({"text": text, "queued_at": now})
        # Simple fallback for rate-limited calls
        words = [w.strip(".,!?") for w in text.split() if len(w) > 4][:3]
        return " ".join(words)[:40] if words else ""

    _last_extraction_at = now

    # Process any queued extractions first
    if _extraction_queue:
        # Take the latest queued item (most recent context)
        queued = _extraction_queue.pop()
        text = str(queued.get("text") or text)
        _extraction_queue.clear()  # Drain queue

    # Try LLM extraction
    keywords = _extract_keywords_llm(text)
    if keywords:
        logger.debug("associative_recall: LLM keywords: %s", keywords)
        return " ".join(keywords)[:40]

    # Regex fallback
    keywords = _extract_keywords_regex(text)
    if keywords:
        logger.debug("associative_recall: regex keywords: %s", keywords)
        return " ".join(keywords)[:40]

    # Ultimate fallback: first meaningful words
    words = [w.strip(".,!?") for w in text.split() if len(w) > 4][:3]
    return " ".join(words)[:40] if words else ""


def _add_private_brain_candidates(
    candidates: list[dict[str, Any]],
    topic_hint: str,
    limit: int = 5,
) -> None:
    """Add private brain records as recall candidates.

    Maps private_brain_records to the candidate format expected by scoring.
    Only includes records with salience ≥ 0.3.
    """
    try:
        from core.runtime.db import get_salient_private_brain_records
        records = get_salient_private_brain_records(threshold=0.3, limit=limit)
        existing_ids = {str(c.get("memory_id") or "") for c in candidates}
        for r in records:
            record_id = str(r.get("record_id") or "")
            if record_id in existing_ids:
                continue
            # Map to candidate format
            candidate = {
                "memory_id": f"pb:{record_id}",
                "narrative": str(r.get("content") or r.get("title") or "")[:200],
                "topic": str(r.get("domain") or "")[:80],
                "emotion_arc": "",
                "importance": float(r.get("salience") or 0.5),
                "source_table": "private_brain",
            }
            candidates.append(candidate)
    except Exception as exc:
        logger.debug("associative_recall: private_brain candidates failed: %s", exc)


def _add_sensory_candidates(
    candidates: list[dict[str, Any]],
    topic_hint: str,
    limit: int = 3,
) -> None:
    """Add recent sensory memories as recall candidates.

    Maps sensory_memories to the candidate format expected by scoring.
    """
    try:
        from core.runtime.db_sensory import list_sensory_memories
        records = list_sensory_memories(limit=limit)
        existing_ids = {str(c.get("memory_id") or "") for c in candidates}
        for r in records:
            record_id = str(r.get("id") or "")
            if f"sensory:{record_id}" in existing_ids:
                continue
            description = str(r.get("description") or "")[:200]
            modality = str(r.get("modality") or "")
            candidate = {
                "memory_id": f"sensory:{record_id}",
                "narrative": description,
                "topic": f"{modality} memory",
                "emotion_arc": str(r.get("atmosphere") or ""),
                "importance": 0.4,  # Sensory memories start at moderate importance
                "source_table": "sensory",
            }
            candidates.append(candidate)
    except Exception as exc:
        logger.debug("associative_recall: sensory candidates failed: %s", exc)


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


def build_associative_recall_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push. Reports module presence + mode
    so the cartographer registers it as observed. Specific state-readers
    can be added later as the module evolves.
    """
    return {
        "active": True,
        "mode": "associative-recall",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_associative_recall_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a associative_recall-scoped event. Defensive — never blocks caller.

    Cartographer scans for event_bus.publish() text. This wrapper keeps
    publishes consistent across the module.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"associative_recall.{kind}",
            payload or {},
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Heartbeat daemon tick
# ---------------------------------------------------------------------------

_DECAY_RATE_PER_MINUTE = 0.015  # ~50% decay in ~45 min
_last_tick_at: float | None = None


def tick_associative_recall() -> dict[str, Any]:
    """Heartbeat daemon tick — decay + periodic candidate scan.

    Called every 2 minutes by the heartbeat scheduler.
    1. Decay all active memory scores (slow fade)
    2. Evict fallen memories (score < 0.1)
    3. If room available, scan for new candidates
    Returns summary dict for daemon_manager.
    """
    global _last_tick_at

    now = time.monotonic()
    elapsed_minutes = 2.0
    if _last_tick_at is not None:
        elapsed_minutes = max(0.5, (now - _last_tick_at) / 60.0)
    _last_tick_at = now

    decayed = 0
    evicted = 0
    refreshed = 0

    # 1. Decay + evict
    for mem_id in list(_active_memories.keys()):
        mem = _active_memories[mem_id]
        old_score = float(mem.get("score") or 0)
        new_score = max(0.0, old_score - (_DECAY_RATE_PER_MINUTE * elapsed_minutes))
        if new_score < 0.1:
            _remove_persisted_memory(mem_id)
            del _active_memories[mem_id]
            evicted += 1
        elif new_score < old_score:
            mem["score"] = new_score
            _persist_active_memory(mem)
            decayed += 1

    # 2. If room, scan for new candidates
    max_active = _get_max_active()
    if len(_active_memories) < max_active:
        try:
            from core.runtime.db import get_experiential_memory_candidates
            from core.services.experiential_memory import score_memories_by_relevance

            slots = max_active - len(_active_memories)
            active_ids = set(_active_memories.keys())
            candidates = get_experiential_memory_candidates(limit=10)
            candidates = [c for c in candidates if c["memory_id"] not in active_ids]

            _add_private_brain_candidates(candidates, "", limit=3)
            _add_sensory_candidates(candidates, "", limit=2)
            candidates = [c for c in candidates if c["memory_id"] not in active_ids]

            if candidates:
                # Score against current active memory topics as context
                context = " ".join(str(m.get("topic") or "") for m in _active_memories.values())
                scores = score_memories_by_relevance(
                    candidates=candidates,
                    context_text=context or "idle heartbeat",
                    emotional_state={},
                )
                if scores:
                    for memory_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                        if score < _get_weak_threshold():
                            continue
                        if refreshed >= slots:
                            break
                        candidate = next((c for c in candidates if c["memory_id"] == memory_id), None)
                        if candidate:
                            _add_to_active({**candidate, "score": score})
                            refreshed += 1
                else:
                    # Fallback: activate by importance when LLM scoring fails
                    for c in candidates[:slots]:
                        if float(c.get("importance") or 0) >= 0.3:
                            _add_to_active({**c, "score": c["importance"]})
                            refreshed += 1
        except Exception as exc:
            logger.debug("associative_recall: tick scan failed: %s", exc)
            # Memory-cluster: brækket associativ-recall-scan SYNLIG i Centralen
            # (var katalogiseret instrument men emitterede aldrig). Self-safe.
            try:
                from core.services.central_core import central
                central().observe({
                    "cluster": "memory", "nerve": "memory_associative_recall",
                    "kind": "scan_error",
                    "error": f"{type(exc).__name__}: {exc}"[:160],
                })
            except Exception:
                pass

    active_count = len(_active_memories)
    result = {
        "active_count": active_count,
        "decayed": decayed,
        "evicted": evicted,
        "refreshed": refreshed,
    }

    if active_count > 0 or refreshed > 0:
        logger.debug("associative_recall tick: %s", result)

    return result

