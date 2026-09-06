"""`lessons` — the one store for what Jarvis learns from mistakes.

Memory repair 2026-09-04 (R4). Before: corrections became a boolean flag,
self-review/regret lessons went to a "morning thread" whose only reader was an
uncalled function, arc rules were blacklisted, and generalized_policies held
27.000 rows for 8 rules with zero matches. Nothing asked "has this happened
before?".

One small table. Every mistake source upserts into it by a normalized
*signature*; the same signature again raises ``evidence_count`` and, when the
lesson was already active, ``repeated_count`` — the closure signal.

Status: ``proposed`` → ``active`` (evidence ≥ 2, or immediately for user
corrections) → ``retired`` (stale, low evidence).
"""
from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect

SOURCE_CORRECTION = "correction"
SOURCE_TOOL_ERROR = "tool_error"
SOURCE_SELF_REVIEW = "self_review"
SOURCE_REGRET = "regret"
SOURCE_ARC_RULE = "arc_rule"

_ACTIVATE_IMMEDIATELY = frozenset({SOURCE_CORRECTION})
_ACTIVATE_AT_EVIDENCE = 2
_KEY_TOKENS = 12
_SIMILAR_JACCARD = 0.75

_TOKEN_RE = re.compile(r"[0-9a-zæøå]+")
_KEY_STOPWORDS = frozenset({
    "og", "i", "at", "det", "en", "et", "er", "til", "med", "for", "på", "af", "der", "som",
    "ikke", "du", "jeg", "den", "de", "har", "var", "kan", "skal", "vil", "om", "men", "så",
    "the", "a", "an", "to", "of", "and", "is", "in", "on", "for", "it", "that", "this",
})


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def signature_key(signature: str) -> str:
    """Lowercase, punctuation-free, stopword-free, first 12 tokens."""
    toks = [t for t in _TOKEN_RE.findall(str(signature or "").lower()) if len(t) >= 2 and t not in _KEY_STOPWORDS]
    return " ".join(toks[:_KEY_TOKENS])


def ensure_lessons_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signature TEXT NOT NULL,
            signature_key TEXT NOT NULL UNIQUE,
            lesson TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed',
            evidence_count INTEGER NOT NULL DEFAULT 1,
            repeated_count INTEGER NOT NULL DEFAULT 0,
            user_words TEXT NOT NULL DEFAULT '',
            jarvis_words TEXT NOT NULL DEFAULT '',
            first_at TEXT NOT NULL,
            last_at TEXT NOT NULL,
            last_repeated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_status ON lessons(status, evidence_count DESC)")


def _row(r: sqlite3.Row | tuple | None) -> dict[str, Any] | None:
    if r is None:
        return None
    if isinstance(r, sqlite3.Row):
        return dict(r)
    cols = ["id", "signature", "signature_key", "lesson", "source", "status", "evidence_count",
            "repeated_count", "user_words", "jarvis_words", "first_at", "last_at", "last_repeated_at"]
    return dict(zip(cols, r))


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _find_match(conn: sqlite3.Connection, key: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM lessons WHERE signature_key = ?", (key,)).fetchone()
    if row is not None:
        return _row(row)
    # fuzzy: token-set overlap against the newest 200 lessons
    best: tuple[float, dict[str, Any] | None] = (0.0, None)
    for r in conn.execute("SELECT * FROM lessons ORDER BY id DESC LIMIT 200").fetchall():
        d = _row(r) or {}
        j = _jaccard(key, str(d.get("signature_key") or ""))
        if j > best[0]:
            best = (j, d)
    if best[0] >= _SIMILAR_JACCARD:
        return best[1]
    return None


def upsert_lesson(
    *,
    signature: str,
    lesson: str,
    source: str,
    user_words: str = "",
    jarvis_words: str = "",
    activate: bool | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Insert or reinforce a lesson. Returns the stored row plus ``outcome``:
    ``created`` | ``reinforced`` | ``repeated`` (reinforced while already active)."""
    key = signature_key(signature)
    lesson_text = " ".join(str(lesson or "").split()).strip()[:600]
    if not key or not lesson_text:
        return {"outcome": "skipped", "reason": "empty signature or lesson"}
    ts = now or _now_iso()
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_lessons_table(conn)
        existing = _find_match(conn, key)
        if existing is None:
            status = "active" if (activate or source in _ACTIVATE_IMMEDIATELY) else "proposed"
            cur = conn.execute(
                "INSERT INTO lessons (signature, signature_key, lesson, source, status, evidence_count, "
                "repeated_count, user_words, jarvis_words, first_at, last_at) "
                "VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?)",
                (str(signature)[:300], key, lesson_text, source, status,
                 str(user_words or "")[:600], str(jarvis_words or "")[:600], ts, ts),
            )
            conn.commit()
            row = _row(conn.execute("SELECT * FROM lessons WHERE id = ?", (cur.lastrowid,)).fetchone()) or {}
            row["outcome"] = "created"
            return row
        was_active = str(existing.get("status")) == "active"
        evidence = int(existing.get("evidence_count") or 0) + 1
        repeated = int(existing.get("repeated_count") or 0) + (1 if was_active else 0)
        status = "active" if (was_active or activate or source in _ACTIVATE_IMMEDIATELY
                              or evidence >= _ACTIVATE_AT_EVIDENCE) else str(existing.get("status"))
        if status == "retired":
            status = "active"
        conn.execute(
            "UPDATE lessons SET evidence_count = ?, repeated_count = ?, status = ?, last_at = ?, "
            "last_repeated_at = CASE WHEN ? THEN ? ELSE last_repeated_at END, "
            "user_words = CASE WHEN ? != '' THEN ? ELSE user_words END, "
            "jarvis_words = CASE WHEN ? != '' THEN ? ELSE jarvis_words END "
            "WHERE id = ?",
            (evidence, repeated, status, ts, 1 if was_active else 0, ts,
             str(user_words or ""), str(user_words or "")[:600],
             str(jarvis_words or ""), str(jarvis_words or "")[:600], existing["id"]),
        )
        conn.commit()
        row = _row(conn.execute("SELECT * FROM lessons WHERE id = ?", (existing["id"],)).fetchone()) or {}
        row["outcome"] = "repeated" if was_active else "reinforced"
        return row


def get_lesson(lesson_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_lessons_table(conn)
        return _row(conn.execute("SELECT * FROM lessons WHERE id = ?", (int(lesson_id),)).fetchone())


def list_lessons(*, status: str | None = "active", limit: int = 30, source: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM lessons"
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if source:
        clauses.append("source = ?")
        params.append(source)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY repeated_count DESC, evidence_count DESC, last_at DESC LIMIT ?"
    params.append(int(limit))
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_lessons_table(conn)
        return [_row(r) or {} for r in conn.execute(sql, params).fetchall()]


def count_lessons(*, status: str | None = None) -> int:
    with connect() as conn:
        ensure_lessons_table(conn)
        if status:
            row = conn.execute("SELECT count(*) FROM lessons WHERE status = ?", (status,)).fetchone()
        else:
            row = conn.execute("SELECT count(*) FROM lessons").fetchone()
        return int(row[0] if row else 0)


def find_similar_lessons(text: str, *, limit: int = 3, status: str = "active") -> list[dict[str, Any]]:
    """Active lessons most similar to ``text`` (BM25 over signature + lesson)."""
    q = " ".join(str(text or "").split()).strip()
    if not q:
        return []
    rows = list_lessons(status=status, limit=200)
    if not rows:
        return []
    try:
        from core.services.multi_signal_retrieval import BM25Index

        idx = BM25Index(k1=1.2, b=0.5)
        idx.build([f"{r.get('signature', '')} {r.get('lesson', '')}" for r in rows])
        hits = [(i, s) for i, s in idx.search(q, top_k=max(limit * 2, 5)) if s > 0]
    except Exception:
        key = signature_key(q)
        hits = [(i, _jaccard(key, str(r.get("signature_key") or ""))) for i, r in enumerate(rows)]
        hits = [(i, s) for i, s in hits if s > 0]
        hits.sort(key=lambda t: t[1], reverse=True)
    out = []
    for i, s in hits[:limit]:
        d = dict(rows[i])
        d["similarity"] = round(float(s), 4)
        out.append(d)
    return out


def record_repeat(lesson_id: int, *, now: str | None = None) -> dict[str, Any] | None:
    ts = now or _now_iso()
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_lessons_table(conn)
        conn.execute(
            "UPDATE lessons SET repeated_count = repeated_count + 1, last_repeated_at = ?, last_at = ? WHERE id = ?",
            (ts, ts, int(lesson_id)),
        )
        conn.commit()
        return _row(conn.execute("SELECT * FROM lessons WHERE id = ?", (int(lesson_id),)).fetchone())


def retire_stale(*, days: int = 30, min_evidence: int = 2, now: datetime | None = None) -> int:
    """Retire proposed/active lessons with evidence < min_evidence, no repeat,
    and no activity for ``days``. Corrections are never retired automatically."""
    cutoff = ((now or datetime.now(UTC)).timestamp() - days * 86400)
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=UTC).isoformat()
    with connect() as conn:
        ensure_lessons_table(conn)
        cur = conn.execute(
            "UPDATE lessons SET status = 'retired' WHERE status IN ('proposed', 'active') "
            "AND source != ? AND evidence_count < ? AND repeated_count = 0 AND last_at < ?",
            (SOURCE_CORRECTION, int(min_evidence), cutoff_iso),
        )
        conn.commit()
        return int(cur.rowcount or 0)


def set_lesson_status(lesson_id: int, status: str) -> dict[str, Any] | None:
    """Saet en lektions status. Returnerer raekken bagefter, eller None.

    Loekken var halv: forslag blev skrevet (`proposed`), og `build_lessons_section`
    laeser `active` ind i prompten — men intet kunne flytte en lektion fra det ene
    til det andet. 4 forslag stod fra 4.-5. september uden at nogen kunne se dem.

    Tilladte vaerdier holdes snaevre med vilje: en fri streng her ville kunne
    parkere en lektion i en status ingen laeser.
    """
    tilladt = {"proposed", "active", "rejected", "retired"}
    s = str(status or "").strip().lower()
    if s not in tilladt:
        raise ValueError(f"ukendt status: {status!r} (tilladt: {sorted(tilladt)})")
    with connect() as conn:
        ensure_lessons_table(conn)
        conn.execute(
            "UPDATE lessons SET status = ?, last_at = ? WHERE id = ?",
            (s, _now_iso(), int(lesson_id)),
        )
        conn.commit()
    return get_lesson(int(lesson_id))
