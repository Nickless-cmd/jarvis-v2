"""User-scoped persistence for experiential memories."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from core.runtime.db_core import connect


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _scope(user_id: str | None) -> str:
    if user_id:
        return str(user_id).strip()
    from core.services.scoped_recall_policy import require_private_scope

    return require_private_scope()


def _ensure_cognitive_experiential_memories_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cognitive_experiential_memories (
            memory_id TEXT NOT NULL PRIMARY KEY,
            session_id TEXT NOT NULL DEFAULT '', run_id TEXT NOT NULL DEFAULT '',
            narrative TEXT NOT NULL DEFAULT '', user_mood TEXT NOT NULL DEFAULT 'neutral',
            jarvis_mood TEXT NOT NULL DEFAULT 'neutral', key_lesson TEXT NOT NULL DEFAULT '',
            emotion_arc TEXT NOT NULL DEFAULT '', topic TEXT NOT NULL DEFAULT '',
            importance REAL NOT NULL DEFAULT 0.5, decay_score REAL NOT NULL DEFAULT 0.0,
            reinforcement_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, user_id TEXT
        )
    """)
    columns = {str(row[1]) for row in conn.execute(
        "PRAGMA table_info(cognitive_experiential_memories)"
    ).fetchall()}
    if "user_id" not in columns:
        conn.execute("ALTER TABLE cognitive_experiential_memories ADD COLUMN user_id TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_experiential_user_created "
        "ON cognitive_experiential_memories(user_id, created_at DESC)"
    )


def insert_cognitive_experiential_memory(
    *, memory_id: str, session_id: str = "", run_id: str = "", narrative: str = "",
    user_mood: str = "neutral", jarvis_mood: str = "neutral", key_lesson: str = "",
    emotion_arc: str = "", topic: str = "", importance: float = 0.5,
    user_id: str | None = None,
) -> dict[str, object]:
    owner = _scope(user_id)
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        conn.execute("""INSERT OR REPLACE INTO cognitive_experiential_memories
            (memory_id, session_id, run_id, narrative, user_mood, jarvis_mood,
             key_lesson, emotion_arc, topic, importance, decay_score,
             reinforcement_count, created_at, updated_at, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0, ?, ?, ?)""",
            (memory_id, session_id, run_id, narrative[:500], user_mood, jarvis_mood,
             key_lesson[:200], emotion_arc, topic[:100], importance, now, now, owner))
    return {"memory_id": memory_id, "topic": topic, "created_at": now}


def reinforce_experiential_memory(memory_id: str, *, user_id: str | None = None) -> None:
    owner = _scope(user_id)
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        conn.execute("""UPDATE cognitive_experiential_memories
            SET reinforcement_count=reinforcement_count+1, decay_score=0.0, updated_at=?
            WHERE memory_id=? AND user_id=?""", (_now_iso(), memory_id, owner))


def list_cognitive_experiential_memories(
    *, limit: int = 20, user_id: str | None = None,
) -> list[dict[str, object]]:
    owner = _scope(user_id)
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_experiential_memories WHERE user_id=? "
            "ORDER BY created_at DESC LIMIT ?", (owner, limit)).fetchall()
    return [{
        "memory_id": r["memory_id"], "narrative": r["narrative"],
        "user_mood": r["user_mood"], "jarvis_mood": r["jarvis_mood"],
        "key_lesson": r["key_lesson"], "emotion_arc": r["emotion_arc"],
        "topic": r["topic"], "importance": float(r["importance"]),
        "decay_score": float(r["decay_score"]),
        "reinforcement_count": int(r["reinforcement_count"]),
        "created_at": r["created_at"], "user_id": str(r["user_id"] or ""),
    } for r in rows]


def get_experiential_memory_candidates(
    *, limit: int = 20, user_id: str | None = None,
) -> list[dict[str, object]]:
    owner = _scope(user_id)
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        rows = conn.execute("""SELECT memory_id, narrative, topic, emotion_arc,
            key_lesson, importance, decay_score, reinforcement_count, user_id
            FROM cognitive_experiential_memories WHERE decay_score < 0.95 AND user_id=?
            ORDER BY importance DESC, reinforcement_count DESC LIMIT ?""",
            (owner, limit)).fetchall()
    return [{
        "memory_id": r["memory_id"], "narrative": str(r["narrative"] or ""),
        "topic": str(r["topic"] or ""), "emotion_arc": str(r["emotion_arc"] or ""),
        "key_lesson": str(r["key_lesson"] or ""), "importance": float(r["importance"]),
        "decay_score": float(r["decay_score"]),
        "reinforcement_count": int(r["reinforcement_count"]),
        "user_id": str(r["user_id"] or ""),
    } for r in rows]


__all__ = [
    "_ensure_cognitive_experiential_memories_table",
    "get_experiential_memory_candidates", "insert_cognitive_experiential_memory",
    "list_cognitive_experiential_memories", "reinforce_experiential_memory",
]
