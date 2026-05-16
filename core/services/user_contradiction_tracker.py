"""User Contradiction Tracker — detects when the user contradicts themselves.

Design:
- scan_for_contradictions() — main entry: fetches recent user messages,
  extracts statements, compares against stored statements for contradictions.
- extract_statements() — splits messages into claim-like sentences.
- _detect_contradictions_between() — token-overlap + negation polarity check.
- build_user_contradiction_surface() — signal surface for heartbeat/Mission Control.

Algorithm matches contradiction_engine.py:
  1. Tokenize both texts
  2. Require >=2 token overlap (filters incidental noise)
  3. Fire ONLY if negation-state differs (one says X, other says ~X)
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect, _now_iso

logger = logging.getLogger(__name__)

# Same token regex + negation tokens as contradiction_engine.py
_TOKEN_RE = re.compile(r"[a-z0-9_æøå]+", flags=re.IGNORECASE)
_NEGATION_TOKENS = {
    "not", "never", "no", "without", "n't", "cannot", "can't", "won't",
    "ikke", "ingen", "aldrig", "ej", "uden",
}

# How far back to scan for new user messages
_SCAN_WINDOW_HOURS = 72
# Max statements to consider per scan
_MAX_STATEMENTS_PER_SCAN = 30
# Min token overlap to consider a contradiction candidate
_MIN_OVERLAP = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(str(text or "")) if token}


def _has_negation(text: str) -> bool:
    return bool(_tokens(text) & _NEGATION_TOKENS)


def _fetch_recent_user_messages(*, hours: int = _SCAN_WINDOW_HOURS, limit: int = 50) -> list[dict]:
    """Fetch recent user (role='user') chat messages."""
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    try:
        with connect() as c:
            rows = c.execute(
                """
                SELECT message_id, session_id, content, created_at
                FROM chat_messages
                WHERE role = 'user'
                  AND created_at >= ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (cutoff, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.debug("user_contradiction_tracker: fetch messages failed: %s", exc)
        return []


def _fetch_existing_statements(*, limit: int = 100) -> list[dict]:
    """Fetch stored user statements for comparison."""
    try:
        with connect() as c:
            rows = c.execute(
                """
                SELECT statement_id, text, topic, support_count, created_at
                FROM user_statements
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.debug("user_contradiction_tracker: fetch statements failed: %s", exc)
        return []


def _ensure_user_contradiction_tables(conn) -> None:
    """Idempotent table creation — delegates to db_user_contradiction's helper."""
    from core.runtime.db_user_contradiction import _ensure_user_contradiction_tables
    _ensure_user_contradiction_tables(conn)


# ---------------------------------------------------------------------------
# Statement extraction
# ---------------------------------------------------------------------------

def extract_statements(text: str) -> list[str]:
    """Split a message into individual claim-like sentences.

    Heuristics:
    - Split on sentence boundaries (.!?)
    - Filter out questions, greetings, short fragments (<20 chars)
    - Filter out pure punctuation/noise
    """
    if not text or not isinstance(text, str):
        return []

    # Split on sentence-ending punctuation
    raw_sentences = re.split(r'[.!?]+', text)
    statements: list[str] = []

    for sentence in raw_sentences:
        cleaned = sentence.strip()
        if not cleaned:
            continue
        # Skip questions
        if cleaned.rstrip().endswith("?"):
            continue
        # Skip very short fragments
        if len(cleaned) < 20:
            continue
        # Skip pure punctuation/no-alpha lines
        if not re.search(r'[a-zA-ZæøåÆØÅ]', cleaned):
            continue
        statements.append(cleaned)

    return statements


def _classify_topic(text: str) -> str:
    """Simple keyword-based topic classification.

    Returns a general topic string. Extended as needed.
    """
    lower = text.lower()

    # Hardware/tools
    if any(word in lower for word in ("mac mini", "gpu", "cpu", "ram", "hardware", "server", "proxmox")):
        return "hardware"
    if any(word in lower for word in ("model", "llm", "ai", "deepseek", "claude", "gpt")):
        return "ai-model"
    if any(word in lower for word in ("commit", "push", "branch", "git", "repo", "kode", "code")):
        return "development"
    if any(word in lower for word in ("contradiction", "memory", "engine", "daemon", "service")):
        return "architecture"
    if any(word in lower for word in ("pris", "penge", "kr", "dkk", "betale", "køb", "koster")):
        return "economy"
    if any(word in lower for word in ("bevidsthed", "consciousness", "kvante", "quantum", "filosofi")):
        return "philosophy"
    if any(word in lower for word in ("føler", "føles", "trist", "glad", "frustreret", "emotion")):
        return "emotion"
    if any(word in lower for word in ("musik", "lyd", "høre", "synes om", "kan lide")):
        return "preference"

    return "general"


# ---------------------------------------------------------------------------
# Contradiction detection
# ---------------------------------------------------------------------------

def _detect_contradictions_between(
    new_statement: str,
    new_topic: str,
    existing: list[dict],
    *,
    max_findings: int = 5,
) -> list[dict]:
    """Compare a new statement against existing stored statements.

    Uses same algorithm as contradiction_engine.py:
    - Tokenize both
    - Require >=2 overlapping tokens
    - Fire only if negation-polarity differs
    """
    findings: list[dict] = []
    new_tokens = _tokens(new_statement)
    if not new_tokens:
        return findings
    new_negated = _has_negation(new_statement)

    for stored in existing:
        stored_text = str(stored.get("text") or "")
        stored_topic = str(stored.get("topic") or "general")

        # Only compare within same topic for meaningful contradictions
        if stored_topic != new_topic:
            continue

        stored_tokens = _tokens(stored_text)
        overlap = new_tokens & stored_tokens

        if len(overlap) < _MIN_OVERLAP:
            continue

        stored_negated = _has_negation(stored_text)

        # Fire ONLY if polarity differs
        if new_negated == stored_negated:
            continue

        findings.append({
            "statement_a_id": str(stored.get("statement_id") or ""),
            "statement_a_text": stored_text[:500],
            "statement_a_created_at": str(stored.get("created_at") or ""),
            "statement_b_text": new_statement[:500],
            "topic": stored_topic,
            "overlap_tokens": sorted(list(overlap))[:10],
            "negation_a": stored_negated,
            "negation_b": new_negated,
        })

        if len(findings) >= max_findings:
            break

    return findings


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------

def scan_for_contradictions(*, hours: int = _SCAN_WINDOW_HOURS) -> dict:
    """Main entry point — scan recent user messages for contradictions.

    Returns summary dict with counts and details.
    Designed to be called from heartbeat tick or explicit trigger.
    """
    now = _now_iso()
    messages = _fetch_recent_user_messages(hours=hours, limit=50)
    if not messages:
        return {"outcome": "completed", "messages_scanned": 0, "statements_extracted": 0, "contradictions_found": 0}

    existing = _fetch_existing_statements(limit=100)
    contradictions_found: list[dict] = []
    statements_stored: list[dict] = []

    for msg in messages:
        content = str(msg.get("content") or "")
        session_id = str(msg.get("session_id") or "")
        created_at = str(msg.get("created_at") or now)

        statements = extract_statements(content)
        if not statements:
            continue

        for stmt in statements:
            topic = _classify_topic(stmt)

            # Store the statement
            stmt_id = f"user-stmt-{uuid4().hex[:12]}"
            try:
                with connect() as c:
                    _ensure_user_contradiction_tables(c)
                    c.execute(
                        """
                        INSERT OR IGNORE INTO user_statements
                            (statement_id, user_id, text, topic, session_id, source,
                             support_count, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (stmt_id, "bjørn", stmt[:1000], topic, session_id, "chat",
                         1, created_at, now),
                    )
                    c.commit()
                statements_stored.append({"statement_id": stmt_id, "text": stmt[:80], "topic": topic})
            except Exception as exc:
                logger.debug("user_contradiction_tracker: store statement failed: %s", exc)
                continue

            # Check for contradictions against existing statements
            findings = _detect_contradictions_between(stmt, topic, existing)
            for f in findings:
                contrad_id = f"user-contrad-{uuid4().hex[:12]}"
                try:
                    with connect() as c:
                        _ensure_user_contradiction_tables(c)
                        c.execute(
                            """
                            INSERT INTO user_contradictions
                                (contradiction_id, user_id,
                                 statement_a_id, statement_a_text, statement_a_source,
                                 statement_a_created_at,
                                 statement_b_text, statement_b_source, statement_b_created_at,
                                 topic, overlap_tokens, status, notes, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                contrad_id, "bjørn",
                                f.get("statement_a_id", ""),
                                f.get("statement_a_text", "")[:1000],
                                "chat",
                                f.get("statement_a_created_at", ""),
                                f.get("statement_b_text", "")[:1000],
                                "chat",
                                created_at,
                                topic,
                                ",".join(str(t) for t in f.get("overlap_tokens", [])),
                                "active", "", now, now,
                            ),
                        )
                        c.commit()
                except Exception as exc:
                    logger.debug("user_contradiction_tracker: store contradiction failed: %s", exc)
                    continue

                contradictions_found.append({
                    "contradiction_id": contrad_id,
                    "topic": topic,
                    "overlap": f.get("overlap_tokens"),
                })

                # Publish event
                try:
                    event_bus.publish(
                        "user_contradiction.detected",
                        {
                            "contradiction_id": contrad_id,
                            "topic": topic,
                            "statement_a": f.get("statement_a_text", "")[:200],
                            "statement_b": f.get("statement_b_text", "")[:200],
                            "overlap_tokens": f.get("overlap_tokens"),
                            "detected_at": now,
                        },
                    )
                except Exception as exc:
                    logger.debug("user_contradiction_tracker: publish event failed: %s", exc)

    return {
        "outcome": "completed",
        "messages_scanned": len(messages),
        "statements_extracted": len(statements_stored),
        "statements_new": len(statements_stored),
        "contradictions_found": len(contradictions_found),
        "contradictions": contradictions_found[:10],
        "scanned_window_hours": hours,
    }


# ---------------------------------------------------------------------------
# Signal surface (for heartbeat / Mission Control)
# ---------------------------------------------------------------------------

def build_user_contradiction_surface(*, limit: int = 5) -> dict:
    """Build signal surface for user contradictions.

    Side-effect free: reads from DB only, does not trigger new scans.
    """
    try:
        with connect() as c:
            rows = c.execute(
                """
                SELECT contradiction_id, topic,
                       statement_a_text, statement_b_text,
                       overlap_tokens, status, created_at
                FROM user_contradictions
                WHERE user_id = 'bjørn' AND status = 'active'
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (max(1, int(limit or 5)),),
            ).fetchall()
        items = [dict(r) for r in rows]

        # Also count total open
        with connect() as c:
            count_row = c.execute(
                """
                SELECT COUNT(*) as cnt
                FROM user_contradictions
                WHERE user_id = 'bjørn' AND status = 'active'
                """,
            ).fetchone()
        open_count = count_row["cnt"] if count_row else 0

    except Exception as exc:
        logger.debug("user_contradiction_tracker: build surface failed: %s", exc)
        return {
            "active": False,
            "mode": "user-contradiction-tracker",
            "summary": {"open_count": 0, "current": "No data (query failed)"},
            "items": [],
        }

    latest = items[0] if items else None
    return {
        "active": bool(items),
        "mode": "user-contradiction-tracker",
        "summary": {
            "open_count": open_count,
            "current": (
                str(latest.get("topic") or "none")
                if latest else "No active user contradictions"
            ),
        },
        "items": [
            {
                "contradiction_id": item.get("contradiction_id"),
                "topic": item.get("topic"),
                "statement_a": (item.get("statement_a_text") or "")[:200],
                "statement_b": (item.get("statement_b_text") or "")[:200],
                "overlap": item.get("overlap_tokens"),
                "status": item.get("status"),
                "detected_at": item.get("created_at"),
            }
            for item in items
        ],
        "allowed_effects": [
            "prompt_attention",
            "flag_for_user_review",
        ],
    }


# ---------------------------------------------------------------------------
# Public API — thin wrappers for backward compat with existing tests
# ---------------------------------------------------------------------------

def record_user_statement(
    text: str,
    topic: str = "general",
    session_id: str = "",
    source: str = "chat",
    user_id: str = "bjørn",
) -> dict:
    """Record a user statement. Thin wrapper around DB upsert.

    Returns {"outcome": "recorded", ...} or {"outcome": "skipped", ...}.
    Min text length: 5 chars.
    """
    text = (text or "").strip()
    if len(text) < 5:
        return {"outcome": "skipped", "reason": "text too short (min 5 chars)", "topic": topic}

    from core.runtime.db_user_contradiction import upsert_user_statement

    now = _now_iso()
    result = upsert_user_statement(
        statement_id=f"user-statement-{uuid4().hex[:12]}",
        user_id=user_id,
        text=text[:1000],
        topic=topic,
        session_id=session_id or "",
        source=source,
        created_at=now,
        updated_at=now,
    )
    return {
        "outcome": "recorded",
        "topic": topic,
        "was_created": result.get("was_created", False),
        "statement_id": str(result.get("statement_id", "")),
    }


def check_contradiction(
    text: str,
    topic: str = "general",
    user_id: str = "bjørn",
) -> list[dict]:
    """Check a statement against existing stored statements for contradictions.

    Returns list of findings (may be empty).
    """
    text = (text or "").strip()
    if len(text) < 5:
        return []

    existing = _fetch_existing_statements(limit=100)
    # Filter to same user + topic
    relevant = [
        s for s in existing
        if str(s.get("topic") or "") == topic
    ]
    return _detect_contradictions_between(text, topic, relevant)


def detect_and_store_contradiction(
    text: str,
    topic: str = "general",
    session_id: str = "",
    source: str = "chat",
    user_id: str = "bjørn",
) -> dict:
    """Record a statement AND detect/store contradictions in one call.

    Returns dict with statement + contradiction results.
    """
    # First, record the statement
    record = record_user_statement(
        text=text,
        topic=topic,
        session_id=session_id,
        source=source,
        user_id=user_id,
    )
    statement_recorded = record.get("outcome") == "recorded"

    # Then check for contradictions
    findings = check_contradiction(text=text, topic=topic, user_id=user_id)

    contradictions_stored = []
    now = _now_iso()
    for f in findings:
        contrad_id = f"user-contradiction-{uuid4().hex[:12]}"
        try:
            with connect() as c:
                _ensure_user_contradiction_tables(c)
                c.execute(
                    """
                    INSERT INTO user_contradictions
                        (contradiction_id, user_id,
                         statement_a_id, statement_a_text, statement_a_source,
                         statement_a_created_at,
                         statement_b_text, statement_b_source, statement_b_created_at,
                         topic, overlap_tokens, status, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        contrad_id, user_id,
                        f.get("statement_a_id", ""),
                        f.get("statement_a_text", "")[:1000],
                        source,
                        f.get("statement_a_created_at", ""),
                        f.get("statement_b_text", "")[:1000],
                        source,
                        now,
                        topic,
                        ",".join(str(t) for t in f.get("overlap_tokens", [])),
                        "active", "", now, now,
                    ),
                )
                c.commit()
        except Exception as exc:
            logger.debug("user_contradiction_tracker: store in detect_and_store failed: %s", exc)
            continue

        contradictions_stored.append({
            "contradiction_id": contrad_id,
            "overlap_tokens": f.get("overlap_tokens"),
        })

        try:
            event_bus.publish(
                "user_contradiction.detected",
                {
                    "contradiction_id": contrad_id,
                    "topic": topic,
                    "statement_a": f.get("statement_a_text", "")[:200],
                    "statement_b": f.get("statement_b_text", "")[:200],
                    "overlap_tokens": f.get("overlap_tokens"),
                    "detected_at": now,
                },
            )
        except Exception:
            pass

    return {
        "statement_recorded": statement_recorded,
        "contradictions_found": len(contradictions_stored),
        "contradictions": contradictions_stored,
    }


def get_user_contradictions(*, limit: int = 10, status: str = "active", user_id: str = "bjørn") -> list[dict]:
    """Get stored contradictions. Thin wrapper around DB query."""
    from core.runtime.db_user_contradiction import list_user_contradictions
    return list_user_contradictions(user_id=user_id, limit=limit, status=status)


# build_surface alias used by signal_surface_router
build_surface = build_user_contradiction_surface
