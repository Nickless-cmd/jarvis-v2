"""Silence Patterns — hvad brugeren IKKE siger.

Detekterer mønstre i tavshed og fravær:
- topic_drop: emner der fyldte meget, så blev tavse
- short_questions: samtalen bliver pludselig kort + spørgende (stress-signal)
- avoidance: åbne loops der ikke længere nævnes
- no_testing: eksekverings-events uden test-mentions

Porteret fra jarvis-ai/agent/cognition/silence.py (2026-04-22).

LLM-path: ingen — ren pattern-matching på chat_messages + events.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SilenceSignal:
    type: str
    topic: str | None
    evidence: list[str]
    confidence: float
    ts: str


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None


def _topic_key(text: str) -> str:
    words = [w.strip().lower() for w in str(text or "").split() if w.strip()]
    if not words:
        return ""
    return " ".join(words[:3])


def _load_recent_user_messages(lookback_days: int) -> list[dict[str, Any]]:
    """Load recent user messages from chat_messages table."""
    since = datetime.now(UTC) - timedelta(days=max(1, int(lookback_days)))
    since_iso = since.isoformat().replace("+00:00", "Z")
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, role, content, created_at
                  FROM chat_messages
                 WHERE role = 'user' AND created_at >= ?
                 ORDER BY id DESC
                 LIMIT 400
                """,
                (since_iso,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.debug("silence_patterns: chat_messages fetch failed: %s", exc)
        return []


def _load_recent_events(lookback_days: int) -> list[dict[str, Any]]:
    """Pull recent events from event_bus — filtered for execution + tool signals."""
    try:
        events = event_bus.recent(limit=500)
    except Exception:
        return []
    since = datetime.now(UTC) - timedelta(days=max(1, int(lookback_days)))
    out: list[dict[str, Any]] = []
    for ev in events:
        ts = _parse_iso(ev.get("created_at"))
        if ts is not None and ts < since:
            continue
        out.append(ev)
    return out


def _load_open_loop_topics(limit: int = 8) -> list[str]:
    """Pull open loop titles/summaries for avoidance detection."""
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT summary, title FROM visible_work_units
                 WHERE status IN ('open', 'active', 'pending', 'in_progress')
                 ORDER BY id DESC LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        out: list[str] = []
        for r in rows:
            text = str(r["summary"] or r["title"] or "").strip()
            if text:
                out.append(text)
        return out
    except Exception:
        return []


def detect_silence_patterns(*, lookback_days: int = 30) -> list[dict[str, Any]]:
    """Detect silence signals from chat history + event stream.

    Returns a list of dicts (SilenceSignal as dict) with type, topic,
    evidence, confidence, ts.
    """
    user_msgs = _load_recent_user_messages(lookback_days)
    if not user_msgs:
        return []

    events = _load_recent_events(lookback_days)

    # Midpoint split — compare older half vs recent half
    midpoint = max(1, len(user_msgs) // 2)
    # Newest first from DB — reverse to chronological
    user_msgs_chrono = list(reversed(user_msgs))
    older = user_msgs_chrono[:midpoint]
    recent = user_msgs_chrono[midpoint:]

    older_topics: dict[str, int] = {}
    recent_topics: dict[str, int] = {}
    recent_texts: list[str] = []

    for msg in older:
        tk = _topic_key(str(msg.get("content") or ""))
        if tk:
            older_topics[tk] = older_topics.get(tk, 0) + 1

    for msg in recent:
        tk = _topic_key(str(msg.get("content") or ""))
        if tk:
            recent_topics[tk] = recent_topics.get(tk, 0) + 1
        content = str(msg.get("content") or "").strip()
        if content:
            recent_texts.append(content)

    signals: list[SilenceSignal] = []

    # 1. Topic drop — topic that was frequent in older but absent in recent
    dropped_topic = ""
    dropped_count = 0
    for topic, count in older_topics.items():
        if count < 3:
            continue
        if int(recent_topics.get(topic, 0)) == 0 and count > dropped_count:
            dropped_topic = topic
            dropped_count = count
    if dropped_topic:
        conf = max(0.55, min(0.95, 0.55 + (dropped_count / max(1.0, len(older))) * 0.6))
        signals.append(SilenceSignal(
            type="topic_drop",
            topic=dropped_topic,
            evidence=[
                f"topic:{dropped_topic}",
                f"older_count:{dropped_count}",
                f"recent_count:{int(recent_topics.get(dropped_topic, 0))}",
            ],
            confidence=float(conf),
            ts=_now_iso(),
        ))

    # 2. Short questions — avg length small + high question ratio
    if recent_texts:
        lengths = [len(t.strip()) for t in recent_texts if t.strip()]
        avg_len = sum(lengths) / max(1, len(lengths)) if lengths else 0.0
        q_ratio = sum(1 for t in recent_texts if "?" in t) / max(1, len(recent_texts))
        if avg_len <= 40 and q_ratio >= 0.6:
            conf = max(0.6, min(0.9, 0.5 + (q_ratio * 0.4)))
            signals.append(SilenceSignal(
                type="short_questions",
                topic=None,
                evidence=[f"avg_len:{avg_len:.1f}", f"question_ratio:{q_ratio:.2f}"],
                confidence=float(conf),
                ts=_now_iso(),
            ))

    # 3. Avoidance — open loop topic whose first word is absent in recent chat
    open_loops = _load_open_loop_topics(limit=8)
    if open_loops and recent_texts:
        lowered_recent = "\n".join(recent_texts).lower()
        candidate = ""
        for loop in open_loops:
            first = str(loop or "").strip().split()
            if not first:
                continue
            probe = first[0].lower()
            if probe and probe not in lowered_recent:
                candidate = str(loop)
                break
        if candidate:
            signals.append(SilenceSignal(
                type="avoidance",
                topic=candidate,
                evidence=[f"open_loop:{candidate[:80]}", "recent_mentions_missing"],
                confidence=0.78,
                ts=_now_iso(),
            ))

    # 4. No testing — execution events present but no test mentions
    has_execution = any(
        str(ev.get("kind") or "").startswith(("visible_run", "tool.invoked", "tool.completed"))
        for ev in events
    )
    has_test_mention = any(
        any(tok in str(msg.get("content") or "").lower() for tok in (" test", "pytest", "test_"))
        for msg in user_msgs[:50]
    )
    if has_execution and not has_test_mention:
        signals.append(SilenceSignal(
            type="no_testing",
            topic="testing",
            evidence=["execution_events_present", "testing_mentions_missing"],
            confidence=0.82,
            ts=_now_iso(),
        ))

    # Filter noise + sort by confidence
    kept = [s for s in signals if s.confidence > 0.5]
    kept.sort(key=lambda s: s.confidence, reverse=True)

    # Publish to event bus
    for s in kept:
        try:
            event_bus.publish("cognitive_silence.pattern_detected", {
                "type": s.type,
                "topic": s.topic,
                "confidence": s.confidence,
            })
        except Exception:
            pass

    return [asdict(s) for s in kept]


def render_soft_question(signal: dict[str, Any]) -> str:
    """Generate a natural Danish follow-up question for a silence signal."""
    stype = str(signal.get("type") or "")
    topic = str(signal.get("topic") or "").strip()

    if stype == "topic_drop":
        t = topic or "det område"
        return f"Jeg lagde mærke til at vi holdt op med at nævne {t} — er det løst, eller smed vi den?"
    if stype == "short_questions":
        return (
            "Jeg lagde mærke til at dine beskeder blev korte — "
            "er vi i hurtig-mode, eller skal jeg udvide næste skridt?"
        )
    if stype == "avoidance":
        t = topic or "det åbne loop"
        return f"Jeg lagde mærke til at vi stopped med at nævne {t} — blev den løst, eller droppede vi den?"
    if stype == "no_testing":
        return (
            "Jeg lagde mærke til at vi ikke har nævnt tests i et stykke tid — "
            "flyttede de sig, eller skal vi genbesøge dækningen?"
        )
    return ""


def build_silence_patterns_surface() -> dict[str, Any]:
    """MC surface for silence patterns."""
    try:
        signals = detect_silence_patterns(lookback_days=30)
    except Exception as exc:
        logger.debug("silence_patterns surface build failed: %s", exc)
        signals = []
    active = bool(signals)
    soft_qs = [render_soft_question(s) for s in signals[:3]]
    soft_qs = [q for q in soft_qs if q]
    return {
        "active": active,
        "summary": (
            f"{len(signals)} tavsheds-mønster(re) detekteret"
            if active else "Ingen tavsheds-mønstre lige nu"
        ),
        "signals": signals,
        "soft_questions": soft_qs,
    }
