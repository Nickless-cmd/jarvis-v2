"""Theory of Mind — Step A.v1 of meta-evne stack.

Bygges 2026-05-23 efter Step E.v1 (metacognition_signal_tracker) er live.

Jarvis' egen formulering af manglen:
"Det ville transformere min kommunikation — og løse et problem jeg ofte
går og føler: gentager jeg mig selv, eller siger jeg noget nyt?"

v1 scope: en KOMMUNIKATIONS-LEDGER. Tracker konkrete fakta som er
udvekslet mellem Jarvis og partner — ikke partner's hele mentale tilstand.
Det er det vi kan vide med høj sikkerhed; inference om partner-belief
(v2+) kræver mere NLP og er bevidst udskudt.

Hvad ledger'en svarer på:
  - Har jeg fortalt partner X i sidste 24 timer?
  - Hvor mange gange har jeg gentaget X for samme partner?
  - Har partner selv sagt Y? Hvornår?
  - Hvilke fakta er etableret mellem os som "fælles viden"?

Storage: partner_knowledge_facts (partner_id, origin, fact_summary,
fact_key, first_at, last_at, reference_count). Dedup via fact_key
(normaliseret tekst).

Listener: DB-polling på channel.chat_message_appended — samme
cross-process pattern som metacognition_signal_tracker (jarvis-api
publish'er events, jarvis-runtime kører trackeren).

Default partner_id: 'primary_user' (generisk navn, ikke fornavn).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"

DEFAULT_PARTNER_ID = "primary_user"
_POLL_INTERVAL_SECONDS = 5.0

# Origin labels — captures HOW we learned the fact.
ORIGIN_TOLD_BY_JARVIS = "told-by-jarvis"
ORIGIN_STATED_BY_PARTNER = "stated-by-partner"

# Heuristic: only sentences that look factual (contain a claim marker)
# enter the ledger. Filters out greetings, fillers, questions.
_CLAIM_MARKER_RE = re.compile(
    r"\b("
    r"\d+(?:[.,]\d+)*"
    r"|kører|virker|fejler|bruger|skal|kan|må|vil|skal|skulle|kan|bør"
    r"|runs|works|fails|uses|will|should|must|can|needs"
    r")\b",
    re.IGNORECASE,
)
# Runtime-injiceret scaffolding (resume-noter ved afbrudte runs, interruption-markører)
# der APPENDES til Jarvis' beskeder af systemet — ikke hans egen kommunikation. De må ALDRIG
# ind i kommunikations-ledger'en, ellers oppustes de til "×29 gentaget"-støj (2026-06-22:
# "Next message can continue from here" stod ×29 i Jarvis' prompt). Matchet → droppet.
_SCAFFOLDING_RE = re.compile(
    r"next message can continue from here"
    r"|instead of starting over"
    r"|jeg blev afbrudt i agentic loopet",
    re.IGNORECASE,
)
_SENT_SPLIT_RE = re.compile(r"(?<=[\.\!\?])\s+|\n+")
_NORMALIZE_RE = re.compile(r"[^a-zæøå0-9 ]", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")

# Stopwords for fact_key normalization. Common Danish + English words
# that don't carry the meaning of a claim.
_KEY_STOPWORDS = frozenset({
    "og", "men", "for", "men", "som", "der", "det", "den", "de", "et", "en",
    "at", "i", "på", "med", "til", "fra", "om", "af", "er", "var", "har",
    "have", "havde", "blev", "bliver", "være", "været", "nu", "så", "også",
    "the", "and", "but", "or", "is", "was", "are", "were", "has", "have",
    "had", "be", "been", "to", "of", "in", "on", "at", "for", "with",
    "from", "by", "as", "this", "that", "these", "those", "it", "its",
})

_HEALTHY_REPEAT_LIMIT = 3  # 3+ mentions of same fact in 1 hour = flag


# ── DB ───────────────────────────────────────────────────────────────────


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS partner_knowledge_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id TEXT NOT NULL,
            origin TEXT NOT NULL,
            fact_summary TEXT NOT NULL,
            fact_key TEXT NOT NULL,
            first_at TEXT NOT NULL,
            last_at TEXT NOT NULL,
            reference_count INTEGER NOT NULL DEFAULT 1,
            session_id TEXT,
            message_id TEXT,
            evidence_json TEXT
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tom_partner_key "
        "ON partner_knowledge_facts(partner_id, fact_key)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tom_last_at "
        "ON partner_knowledge_facts(last_at)"
    )


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)
    return conn


# ── Normalization ────────────────────────────────────────────────────────


def _normalize_to_key(text: str) -> str:
    """Build a stable dedupe key from a sentence.

    Steps: lowercase, strip punctuation, drop stopwords, sort remaining
    content words, hash. Order-insensitive so "X kører på 8011" and
    "På 8011 kører X" collapse to same key.
    """
    cleaned = _NORMALIZE_RE.sub(" ", str(text).lower())
    tokens = [t for t in _WHITESPACE_RE.split(cleaned) if t]
    content = sorted({t for t in tokens if t not in _KEY_STOPWORDS and len(t) >= 3})
    if not content:
        return ""
    blob = " ".join(content)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def _split_factual_sentences(text: str) -> list[str]:
    """Return sentences from text that look like factual claims."""
    sentences = [s.strip() for s in _SENT_SPLIT_RE.split(text or "") if s.strip()]
    result = []
    for s in sentences:
        if len(s) < 12 or len(s) > 400:
            continue
        if s.endswith("?"):
            continue  # questions aren't claims
        if _SCAFFOLDING_RE.search(s):
            continue  # runtime-injiceret scaffolding, ikke Jarvis' kommunikation
        if _CLAIM_MARKER_RE.search(s):
            result.append(s)
    return result


# ── Recording ────────────────────────────────────────────────────────────


def record_fact(
    *,
    partner_id: str,
    origin: str,
    fact_summary: str,
    session_id: str | None = None,
    message_id: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Upsert a fact into the ledger.

    Returns the resulting row dict (with reference_count after update),
    or None if the fact was empty/unusable.
    """
    key = _normalize_to_key(fact_summary)
    if not key:
        return None
    now_iso = datetime.now(UTC).isoformat()
    evidence_json = json.dumps(evidence or {}, ensure_ascii=False, default=str)
    try:
        with _connect() as conn:
            existing = conn.execute(
                """SELECT id, reference_count FROM partner_knowledge_facts
                   WHERE partner_id = ? AND fact_key = ?""",
                (partner_id, key),
            ).fetchone()
            if existing:
                new_count = int(existing["reference_count"]) + 1
                conn.execute(
                    """UPDATE partner_knowledge_facts
                       SET last_at = ?, reference_count = ?
                       WHERE id = ?""",
                    (now_iso, new_count, existing["id"]),
                )
                conn.commit()
                return {
                    "id": existing["id"], "fact_key": key,
                    "reference_count": new_count, "status": "incremented",
                }
            conn.execute(
                """INSERT INTO partner_knowledge_facts
                   (partner_id, origin, fact_summary, fact_key,
                    first_at, last_at, reference_count,
                    session_id, message_id, evidence_json)
                   VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
                (partner_id, origin, fact_summary[:400], key,
                 now_iso, now_iso, session_id, message_id, evidence_json),
            )
            conn.commit()
            return {"fact_key": key, "reference_count": 1, "status": "inserted"}
    except Exception:
        logger.exception("theory_of_mind: record_fact failed")
        return None


def record_message(
    *,
    role: str,
    content: str,
    partner_id: str = DEFAULT_PARTNER_ID,
    session_id: str | None = None,
    message_id: str | None = None,
) -> list[dict[str, Any]]:
    """Extract factual sentences from a message and record each one.

    role='assistant' → origin=told-by-jarvis
    role='user'      → origin=stated-by-partner
    """
    if role == "assistant":
        origin = ORIGIN_TOLD_BY_JARVIS
    elif role == "user":
        origin = ORIGIN_STATED_BY_PARTNER
    else:
        return []
    sentences = _split_factual_sentences(content)
    results = []
    for sent in sentences:
        outcome = record_fact(
            partner_id=partner_id,
            origin=origin,
            fact_summary=sent,
            session_id=session_id,
            message_id=message_id,
        )
        if outcome:
            results.append(outcome)
    return results


# ── Queries ──────────────────────────────────────────────────────────────


def recent_facts(
    *,
    partner_id: str = DEFAULT_PARTNER_ID,
    origin: str | None = None,
    hours: int = 24,
    limit: int = 20,
) -> list[dict[str, Any]]:
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    try:
        with _connect() as conn:
            query = (
                "SELECT * FROM partner_knowledge_facts "
                "WHERE partner_id = ? AND last_at >= ?"
            )
            params: list[Any] = [partner_id, cutoff]
            if origin:
                query += " AND origin = ?"
                params.append(origin)
            query += " ORDER BY last_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def has_been_told(
    fact_text: str,
    *,
    partner_id: str = DEFAULT_PARTNER_ID,
    hours: int = 24,
) -> bool:
    """Has Jarvis told partner this fact within the time window?"""
    key = _normalize_to_key(fact_text)
    if not key:
        return False
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    try:
        with _connect() as conn:
            row = conn.execute(
                """SELECT 1 FROM partner_knowledge_facts
                   WHERE partner_id = ? AND fact_key = ?
                     AND origin = ? AND last_at >= ?
                   LIMIT 1""",
                (partner_id, key, ORIGIN_TOLD_BY_JARVIS, cutoff),
            ).fetchone()
    except Exception:
        return False
    return row is not None


def repetition_warnings(
    *,
    partner_id: str = DEFAULT_PARTNER_ID,
    hours: int = 1,
    threshold: int = _HEALTHY_REPEAT_LIMIT,
) -> list[dict[str, Any]]:
    """Facts Jarvis has repeated to partner at or above threshold within window."""
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    try:
        with _connect() as conn:
            rows = conn.execute(
                """SELECT fact_summary, reference_count, last_at
                   FROM partner_knowledge_facts
                   WHERE partner_id = ? AND origin = ?
                     AND last_at >= ? AND reference_count >= ?
                   ORDER BY reference_count DESC LIMIT 5""",
                (partner_id, ORIGIN_TOLD_BY_JARVIS, cutoff, threshold),
            ).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


# ── Awareness surface ────────────────────────────────────────────────────


def communication_ledger_section(
    *,
    partner_id: str = DEFAULT_PARTNER_ID,
) -> str | None:
    """Quiet by default. Surfaces only when Jarvis is repeating himself."""
    warnings = repetition_warnings(partner_id=partner_id)
    if not warnings:
        return None
    lines = ["Kommunikations-ledger (har gentaget i sidste time):"]
    for w in warnings:
        lines.append(
            f"  - ×{w['reference_count']}: "
            f"\"{str(w['fact_summary'])[:120]}\""
        )
    lines.append(
        "  → overvej at variere, opsummere kort, eller bevæge dig videre"
    )
    return "\n".join(lines)


# ── DB-polling listener ──────────────────────────────────────────────────


_listener_thread: threading.Thread | None = None
_listener_running = False


def _listener_loop() -> None:
    """Poll events table for channel.chat_message_appended events.

    Same cross-process pattern as metacognition_signal_tracker.
    """
    import time as _time
    global _listener_running
    try:
        with _connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()
            last_id = int(row[0] or 0) if row else 0
    except Exception:
        last_id = 0

    while _listener_running:
        _time.sleep(_POLL_INTERVAL_SECONDS)
        try:
            with _connect() as conn:
                rows = conn.execute(
                    """SELECT id, payload_json
                       FROM events
                       WHERE id > ?
                         AND kind = 'channel.chat_message_appended'
                       ORDER BY id ASC
                       LIMIT 100""",
                    (last_id,),
                ).fetchall()
            for r in rows:
                last_id = max(last_id, int(r["id"]))
                try:
                    payload = json.loads(r["payload_json"] or "{}")
                except (ValueError, TypeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                message = payload.get("message") or {}
                role = message.get("role")
                if role not in ("user", "assistant"):
                    continue
                content = str(message.get("content") or "")
                if len(content) < 12:
                    continue
                session_id = payload.get("session_id") or message.get("session_id")
                msg_id = message.get("id") or message.get("message_id")
                record_message(
                    role=role,
                    content=content,
                    session_id=session_id,
                    message_id=msg_id,
                )
        except Exception:
            logger.exception("theory_of_mind: poll cycle failed")


def start_theory_of_mind_tracker() -> None:
    """Start the DB-polling listener. Idempotent."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop, daemon=True,
            name="theory-of-mind-tracker",
        )
        _listener_thread.start()
        logger.warning("theory_of_mind: DB-polling listener started")
    except Exception:
        logger.exception("theory_of_mind: failed to start")


def stop_theory_of_mind_tracker() -> None:
    global _listener_running
    _listener_running = False
