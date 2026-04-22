"""Shared Language Extended — shorthand-udvikling og -resolution.

Over tid udvikler Jarvis og brugeren fælles vocabulary. "Det sædvanlige"
begynder at betyde noget specifikt. Dette modul:

1. **propose_shorthand_terms()**: scanner recent chat_messages for
   gentagne n-grammer (2-3 ord) → foreslår dem som shorthand
2. **maybe_weekly_shorthand_suggestion()**: max 1 ny term pr. uge
3. **resolve_shorthand_text()**: ekspand shorthand i real-time
   ("den sædvanlige refaktor" → "den sædvanlige refaktor (kodebase-
   konsolidering af bs.*)")

Porteret fra jarvis-ai/agent/cognition/shared_language.py (2026-04-22).

v2 har shared_language.py (88L stub). Vi tilføjer dette som extension
for at undgå konflikt. Ny tabel cognitive_shared_terms.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-zæøåA-ZÆØÅ0-9][a-zæøåA-ZÆØÅ0-9_\-/]{1,}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_shared_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phrase TEXT NOT NULL UNIQUE,
                meaning TEXT NOT NULL DEFAULT '',
                anchors_json TEXT NOT NULL DEFAULT '[]',
                confidence REAL NOT NULL DEFAULT 0.6,
                last_used_ts TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_shared_terms_last "
            "ON cognitive_shared_terms(last_used_ts DESC)"
        )
        conn.commit()


def _ngrams(text: str) -> list[str]:
    words = [m.group(0).lower() for m in _TOKEN_PATTERN.finditer(str(text or ""))]
    grams: list[str] = []
    for size in (2, 3):
        for i in range(0, max(0, len(words) - size + 1)):
            g = " ".join(words[i:i + size]).strip()
            if len(g) >= 6:
                grams.append(g)
    return grams


def _load_recent_user_messages(days: int = 30, limit: int = 500) -> list[dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(days=max(1, int(days)))
    since_iso = since.isoformat().replace("+00:00", "Z")
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT session_id, content, created_at FROM chat_messages "
                "WHERE role = 'user' AND created_at >= ? "
                "ORDER BY id DESC LIMIT ?",
                (since_iso, int(limit)),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def propose_shorthand_terms(*, min_occurrences: int = 3, max_proposals: int = 6) -> list[dict[str, Any]]:
    """Scan chat messages for repeated n-grams; propose as shorthand."""
    _ensure_table()
    msgs = _load_recent_user_messages(days=30, limit=500)
    if not msgs:
        return []

    counts: dict[str, int] = {}
    anchors_by_phrase: dict[str, list[str]] = {}
    for m in msgs:
        text = str(m.get("content") or "")
        if not text:
            continue
        anchor = f"msg:{m.get('session_id') or ''}:{m.get('created_at') or ''}"
        for gram in _ngrams(text):
            counts[gram] = counts.get(gram, 0) + 1
            anchors_by_phrase.setdefault(gram, [])
            if anchor not in anchors_by_phrase[gram]:
                anchors_by_phrase[gram].append(anchor)

    # Exclude existing phrases
    existing: set[str] = set()
    with connect() as conn:
        rows = conn.execute("SELECT phrase FROM cognitive_shared_terms").fetchall()
        existing = {str(r["phrase"] or "").lower() for r in rows}

    proposals: list[dict[str, Any]] = []
    for phrase, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        if count < min_occurrences:
            continue
        if phrase.lower() in existing:
            continue
        anchors = anchors_by_phrase.get(phrase) or []
        if len(anchors) < 2:
            continue
        # Filter obviously-bad n-grams (common Danish/English stop-word combos)
        lower = phrase.lower()
        _STOP_STARTS = (
            "the ", "a ", "an ", "is ", "was ", "it ", "i ", "you ", "we ",
            "en ", "et ", "den ", "det ", "at ", "og ", "eller ", "men ",
            "til ", "fra ", "med ", "ikke ", "som ", "er ", "var ", "har ",
            "skal ", "kan ", "vil ", "du ", "jeg ", "vi ", "så ", "for ",
        )
        # Block if phrase starts with stop-word AND total words <= 2
        words = lower.split()
        if len(words) <= 2 and any(lower.startswith(sw) for sw in _STOP_STARTS):
            continue
        # Block if all words are stop-words
        _STOP_SET = {s.strip() for s in _STOP_STARTS}
        if all(w in _STOP_SET for w in words):
            continue
        conf = min(0.9, 0.55 + count * 0.05)
        proposals.append({
            "phrase": phrase,
            "meaning": f"Repeated reference to '{phrase}' in chat context.",
            "anchors": anchors[:10],
            "confidence": conf,
            "occurrence_count": count,
        })
        if len(proposals) >= int(max_proposals):
            break
    return proposals


def _latest_suggestion_ts() -> datetime | None:
    _ensure_table()
    with connect() as conn:
        row = conn.execute(
            "SELECT created_at FROM cognitive_shared_terms ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row and row["created_at"]:
        try:
            ts = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
            return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
        except Exception:
            pass
    return None


def maybe_weekly_shorthand_suggestion() -> dict[str, Any]:
    """Max 1 shorthand per 7 days. Returns the new term if added."""
    _ensure_table()
    last = _latest_suggestion_ts()
    now = datetime.now(UTC)
    if last and (now - last) < timedelta(days=7):
        return {"outcome": "skipped", "reason": "weekly_budget"}

    proposals = propose_shorthand_terms()
    if not proposals:
        return {"outcome": "skipped", "reason": "no_candidate"}

    selected = proposals[0]
    now_iso = now.isoformat().replace("+00:00", "Z")
    with connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO cognitive_shared_terms
                    (phrase, meaning, anchors_json, confidence, last_used_ts, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(selected["phrase"]),
                    str(selected.get("meaning") or ""),
                    json.dumps(selected.get("anchors") or [], ensure_ascii=False),
                    float(selected.get("confidence") or 0.6),
                    now_iso, now_iso,
                ),
            )
            conn.commit()
        except Exception as exc:
            return {"outcome": "error", "reason": str(exc)[:80]}

    question = f"Vi nævner ofte '{selected['phrase']}' — vil du gøre det til et shorthand?"
    try:
        event_bus.publish("cognitive_shared_language.term_proposed", {
            "phrase": selected["phrase"], "confidence": selected.get("confidence"),
        })
    except Exception:
        pass
    return {"outcome": "completed", "question": question, "term": selected}


def list_shorthand_terms(*, limit: int = 50) -> list[dict[str, Any]]:
    _ensure_table()
    lim = max(1, min(int(limit or 50), 200))
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_shared_terms ORDER BY last_used_ts DESC LIMIT ?",
            (lim,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        try:
            d["anchors"] = json.loads(d.pop("anchors_json", "[]") or "[]")
        except Exception:
            d["anchors"] = []
        out.append(d)
    return out


def resolve_shorthand_text(text: str) -> dict[str, Any]:
    """Expand shorthand in text. Returns {resolved_text, matched_terms}."""
    _ensure_table()
    safe = str(text or "")
    if not safe.strip():
        return {"resolved_text": safe, "matched_terms": []}

    terms = list_shorthand_terms(limit=100)
    resolved = safe
    matched: list[dict[str, Any]] = []
    now_iso = _now_iso()

    for term in terms:
        phrase = str(term.get("phrase") or "").strip()
        meaning = str(term.get("meaning") or "").strip()
        if not phrase or not meaning:
            continue
        pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
        if not pattern.search(resolved):
            continue
        resolved = pattern.sub(f"{phrase} ({meaning})", resolved, count=1)
        matched.append(term)
        # Touch last_used_ts
        try:
            with connect() as conn:
                conn.execute(
                    "UPDATE cognitive_shared_terms SET last_used_ts = ? WHERE phrase = ?",
                    (now_iso, phrase),
                )
                conn.commit()
        except Exception:
            pass

    return {"resolved_text": resolved, "matched_terms": matched}


def build_shared_language_extended_surface() -> dict[str, Any]:
    _ensure_table()
    terms = list_shorthand_terms(limit=20)
    active = bool(terms)
    return {
        "active": active,
        "summary": (
            f"{len(terms)} shared-language terms registered"
            if terms else "No shared-language terms yet"
        ),
        "terms": terms,
    }
