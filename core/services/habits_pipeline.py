"""Habits Pipeline — detect → track → suggest automation.

Forgænger-habits var en komplet pipeline:
1. record_habit_signal() normaliserer beskedens signature
2. upsert_habit_pattern() tracker gentagelse (recurrence)
3. upsert_friction_signal() tracker inefficiency (repeated same task)
4. maybe_create_suggestion() foreslår automation når thresholds nås

v2 havde habit_tracker.py som 88L stub uden friction-detection eller
suggestion-generation. Dette modul er den fulde port.

Porteret fra jarvis-ai/agent/cognition/habits.py (2026-04-22).

LLM-path: ingen. Ren pattern matching + threshold-based suggestions.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_HABIT_SUGGEST_THRESHOLD = 2  # recurrence_count >= 2 → suggest
_FRICTION_SUGGEST_THRESHOLD = 0.75  # inefficiency_score >= 0.75 → suggest


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_tables() -> None:
    """Tables exist from v2 db.py — this is idempotent no-op unless schema changes.

    Existing v2 schema uses pattern_id/friction_id columns (not id), and
    cognitive_automation_suggestions uses id. We match that.
    """
    with connect() as conn:
        # These three are already in v2 db.py — CREATE IF NOT EXISTS safe
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_habit_patterns (
                pattern_id TEXT NOT NULL,
                pattern_key TEXT NOT NULL,
                recurrence_count INTEGER NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 0.0,
                description TEXT NOT NULL DEFAULT '',
                last_detected_at TEXT NOT NULL,
                PRIMARY KEY (pattern_id),
                UNIQUE (pattern_key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_friction_signals (
                friction_id TEXT NOT NULL,
                task_signature TEXT NOT NULL,
                repetition_count INTEGER NOT NULL DEFAULT 0,
                inefficiency_score REAL NOT NULL DEFAULT 0.0,
                description TEXT NOT NULL DEFAULT '',
                last_seen_at TEXT NOT NULL,
                PRIMARY KEY (friction_id),
                UNIQUE (task_signature)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_automation_suggestions (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                suggestion_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                confidence REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _normalize_signature(message: str) -> str:
    text = str(message or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9æøåäöü\s]", "", text)
    tokens = [t for t in text.split(" ") if t]
    if not tokens:
        return ""
    normalized = " ".join(tokens[:12])
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{normalized}:{digest}"


def _upsert_habit(pattern_key: str, now: str) -> tuple[str, int, float]:
    with connect() as conn:
        row = conn.execute(
            "SELECT pattern_id, recurrence_count FROM cognitive_habit_patterns "
            "WHERE pattern_key = ?",
            (pattern_key,),
        ).fetchone()
        if row is None:
            pid = f"habit_{uuid4().hex[:12]}"
            recurrence = 1
        else:
            pid = str(row["pattern_id"])
            recurrence = int(row["recurrence_count"] or 0) + 1
        confidence = min(1.0, max(0.2, recurrence / 4.0))
        conn.execute(
            """
            INSERT INTO cognitive_habit_patterns
                (pattern_id, pattern_key, recurrence_count, confidence,
                 description, last_detected_at)
            VALUES (?, ?, ?, ?, '', ?)
            ON CONFLICT(pattern_key) DO UPDATE SET
                recurrence_count = excluded.recurrence_count,
                confidence = excluded.confidence,
                last_detected_at = excluded.last_detected_at
            """,
            (pid, pattern_key, recurrence, float(confidence), now),
        )
        conn.commit()
    return pid, recurrence, float(confidence)


def _upsert_friction(task_signature: str, now: str) -> tuple[str, int, float]:
    with connect() as conn:
        row = conn.execute(
            "SELECT friction_id, repetition_count FROM cognitive_friction_signals "
            "WHERE task_signature = ?",
            (task_signature,),
        ).fetchone()
        if row is None:
            fid = f"friction_{uuid4().hex[:12]}"
            repetition = 1
        else:
            fid = str(row["friction_id"])
            repetition = int(row["repetition_count"] or 0) + 1
        ineff = min(1.0, max(0.1, repetition / 3.0))
        conn.execute(
            """
            INSERT INTO cognitive_friction_signals
                (friction_id, task_signature, repetition_count, inefficiency_score,
                 description, last_seen_at)
            VALUES (?, ?, ?, ?, '', ?)
            ON CONFLICT(task_signature) DO UPDATE SET
                repetition_count = excluded.repetition_count,
                inefficiency_score = excluded.inefficiency_score,
                last_seen_at = excluded.last_seen_at
            """,
            (fid, task_signature, repetition, float(ineff), now),
        )
        conn.commit()
    return fid, repetition, float(ineff)


def _maybe_create_suggestion(
    *,
    source_type: str,
    source_id: str,
    suggestion_text: str,
    confidence: float,
    now: str,
) -> str | None:
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM cognitive_automation_suggestions "
            "WHERE source_type = ? AND source_id = ? "
            "AND status IN ('pending', 'accepted') "
            "ORDER BY created_at DESC LIMIT 1",
            (source_type, source_id),
        ).fetchone()
        if existing:
            return None
        sid = f"as_{uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO cognitive_automation_suggestions
                (id, source_type, source_id, suggestion_text, status,
                 confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (sid, source_type, source_id, suggestion_text, float(confidence), now, now),
        )
        conn.commit()
    return sid


def record_habit_signal(*, message: str) -> list[dict[str, Any]]:
    """Main entry: record a habit signal from a chat message.

    Returns list of events (type: habit_detected, friction_detected,
    automation_suggestion_created).
    """
    _ensure_tables()
    signature = _normalize_signature(message)
    if not signature:
        return []
    now = _now_iso()
    events: list[dict[str, Any]] = []

    pid, recurrence, conf = _upsert_habit(signature, now)
    events.append({
        "type": "habit_detected",
        "habit_id": pid,
        "recurrence_count": recurrence,
        "confidence": conf,
    })

    fid, repetition, ineff = _upsert_friction(signature, now)
    events.append({
        "type": "friction_detected",
        "friction_id": fid,
        "repetition_count": repetition,
        "inefficiency_score": ineff,
    })

    # Habit-based suggestion
    if recurrence >= _HABIT_SUGGEST_THRESHOLD:
        sid = _maybe_create_suggestion(
            source_type="habit",
            source_id=pid,
            suggestion_text=(
                "Dette gentagne signal kan automatiseres som scheduled workflow "
                "eller shortcut."
            ),
            confidence=conf,
            now=now,
        )
        if sid:
            events.append({
                "type": "automation_suggestion_created",
                "suggestion_id": sid,
                "source_type": "habit",
                "source_id": pid,
            })
            try:
                event_bus.publish("cognitive_habit.suggestion_created", {
                    "suggestion_id": sid,
                    "source_type": "habit",
                    "confidence": conf,
                })
            except Exception:
                pass

    # Friction-based suggestion
    if ineff >= _FRICTION_SUGGEST_THRESHOLD:
        sid = _maybe_create_suggestion(
            source_type="friction",
            source_id=fid,
            suggestion_text=(
                "Høj gentaget manuel friktion — overvej at lave en genbrugelig automation."
            ),
            confidence=ineff,
            now=now,
        )
        if sid:
            events.append({
                "type": "automation_suggestion_created",
                "suggestion_id": sid,
                "source_type": "friction",
                "source_id": fid,
            })
            try:
                event_bus.publish("cognitive_habit.suggestion_created", {
                    "suggestion_id": sid,
                    "source_type": "friction",
                    "confidence": ineff,
                })
            except Exception:
                pass

    return events


def list_habits(*, limit: int = 50) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 50), 200))
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_habit_patterns "
            "ORDER BY last_detected_at DESC LIMIT ?",
            (lim,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_friction(*, limit: int = 50) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 50), 200))
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_friction_signals "
            "ORDER BY inefficiency_score DESC, last_seen_at DESC LIMIT ?",
            (lim,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_suggestions(*, status: str = "pending", limit: int = 50) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 50), 200))
    s = str(status or "pending").strip().lower()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_automation_suggestions WHERE status = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (s, lim),
        ).fetchall()
    return [dict(r) for r in rows]


def accept_suggestion(*, suggestion_id: str) -> dict[str, Any] | None:
    _ensure_tables()
    now = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE cognitive_automation_suggestions "
            "SET status = 'accepted', updated_at = ? WHERE id = ?",
            (now, str(suggestion_id)),
        )
        if cursor.rowcount <= 0:
            return None
        row = conn.execute(
            "SELECT * FROM cognitive_automation_suggestions WHERE id = ?",
            (str(suggestion_id),),
        ).fetchone()
        conn.commit()
    if row:
        try:
            event_bus.publish("cognitive_habit.suggestion_accepted", {
                "suggestion_id": suggestion_id,
            })
        except Exception:
            pass
        return dict(row)
    return None


def reject_suggestion(*, suggestion_id: str) -> dict[str, Any] | None:
    _ensure_tables()
    now = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE cognitive_automation_suggestions "
            "SET status = 'rejected', updated_at = ? WHERE id = ?",
            (now, str(suggestion_id)),
        )
        if cursor.rowcount <= 0:
            return None
        row = conn.execute(
            "SELECT * FROM cognitive_automation_suggestions WHERE id = ?",
            (str(suggestion_id),),
        ).fetchone()
        conn.commit()
    return dict(row) if row else None


def build_habits_pipeline_surface() -> dict[str, Any]:
    _ensure_tables()
    habits = list_habits(limit=10)
    friction = list_friction(limit=10)
    pending = list_suggestions(status="pending", limit=10)
    active = bool(habits or friction or pending)
    summary = (
        f"{len(habits)} habits / {len(friction)} friction-signaler / "
        f"{len(pending)} pending suggestions"
    )
    return {
        "active": active,
        "summary": summary,
        "top_habits": habits[:5],
        "top_friction": friction[:5],
        "pending_suggestions": pending[:5],
    }
