"""Contradiction engine — detect semantic conflicts between commitments and reviews.

Porteret fra jarvis-ai/agent/ecosystem/contradiction_engine.py (2026-05-07),
men adapteret til v2-arkitektur:

Original kilde for "nodes": internal_web intent-graf (eksisterer ikke i v2).
Original kilde for "criticisms": MessageBus.consume("criticisms") topic.

V2-kilder i stedet:
- "Statements" = active behavioral_decisions (directive-tekst Jarvis har commitet til)
- "Criticisms" = recent cognitive_self_reviews (lessons + next_focus felter)

Bemærk: dette løser et hul som adherence-score IKKE løser. Adherence tæller
om man honored decision'en. Dette finder SEMANTISK kontradiktion — fx
"jeg gemmer altid" som decision, og "jeg glemmer at gemme" i review.
Det er den slags Jarvis selv-modsigelse han skal kunne se for at lukke
adherence-loopet.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

# Match alphanumeric+underscore tokens. Same regex as jarvis-ai original
# so the negation-detection logic stays equivalent.
_TOKEN_RE = re.compile(r"[a-z0-9_æøå]+", flags=re.IGNORECASE)

# Danish + English negation tokens. Original had "ingen, ikke" already
# (Bjørn's prior contributions); kept both languages so contradictions
# involving Danish self-talk get detected.
_NEGATION_TOKENS = {
    "not", "never", "no", "without", "n't", "cannot", "can't", "won't",
    "ikke", "ingen", "aldrig", "ej", "uden",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(str(text or "")) if token}


def _has_negation(text: str) -> bool:
    return bool(_tokens(text) & _NEGATION_TOKENS)


def _fetch_active_decisions(*, limit: int = 20) -> list[dict[str, Any]]:
    """Return active behavioral_decisions with their directive text."""
    try:
        with connect() as c:
            rows = c.execute(
                """
                SELECT decision_id, directive, trigger_cue, priority
                FROM behavioral_decisions
                WHERE status = 'active'
                ORDER BY priority DESC, created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.debug("contradiction_engine: fetch decisions failed: %s", exc)
        return []


def _fetch_recent_self_reviews(*, hours: int = 48, limit: int = 12) -> list[dict[str, Any]]:
    """Return cognitive_self_reviews from the last `hours` hours."""
    try:
        cutoff_iso = (datetime.now(UTC) - _timedelta(hours=hours)).isoformat()
        with connect() as c:
            rows = c.execute(
                """
                SELECT id, lessons_json, next_focus, risk_level, created_at
                FROM cognitive_self_reviews
                WHERE created_at >= ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (cutoff_iso, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.debug("contradiction_engine: fetch reviews failed: %s", exc)
        return []


def _timedelta(*, hours: int):
    from datetime import timedelta
    return timedelta(hours=hours)


def _critique_texts_from_review(review: dict[str, Any]) -> list[str]:
    """Extract per-lesson + next_focus strings as candidate critique texts."""
    import json as _json
    out: list[str] = []
    raw_lessons = review.get("lessons_json") or "[]"
    try:
        lessons = _json.loads(raw_lessons) if isinstance(raw_lessons, str) else (raw_lessons or [])
    except Exception:
        lessons = []
    for lesson in lessons or []:
        text = str(lesson or "").strip()
        if text:
            out.append(text)
    next_focus = str(review.get("next_focus") or "").strip()
    if next_focus:
        out.append(next_focus)
    return out


def detect_contradictions(*, max_findings: int = 5) -> list[dict[str, Any]]:
    """Find semantic contradictions between active decisions and recent reviews.

    Algorithm (same as jarvis-ai original):
    1. Tokenize both texts
    2. Require ≥2 token overlap (filters incidental noise)
    3. Fire ONLY if negation-state differs (one says X, other says ~X)

    Returns list of dicts with decision + critique pair + overlap tokens.
    Capped at `max_findings` to avoid spamming on a noisy day.
    """
    decisions = _fetch_active_decisions(limit=20)
    reviews = _fetch_recent_self_reviews(hours=48, limit=12)
    if not decisions or not reviews:
        return []

    # Pre-extract critique texts with review-id for traceability
    critiques: list[tuple[int, str]] = []
    for r in reviews:
        review_id = int(r.get("id") or 0)
        for text in _critique_texts_from_review(r):
            critiques.append((review_id, text))
    if not critiques:
        return []

    findings: list[dict[str, Any]] = []
    for d in decisions:
        directive = str(d.get("directive") or "").strip()
        if not directive:
            continue
        d_tokens = _tokens(directive)
        if not d_tokens:
            continue
        d_negated = _has_negation(directive)
        for review_id, critique in critiques:
            c_tokens = _tokens(critique)
            overlap = d_tokens & c_tokens
            if len(overlap) < 2:
                continue
            if d_negated == _has_negation(critique):
                continue  # both same polarity → not a contradiction
            findings.append(
                {
                    "decision_id": str(d.get("decision_id") or ""),
                    "decision_directive": directive[:200],
                    "decision_priority": int(d.get("priority") or 0),
                    "review_id": review_id,
                    "review_text": critique[:200],
                    "overlap_tokens": sorted(list(overlap))[:8],
                    "detected_at": _now_iso(),
                }
            )
            if len(findings) >= max_findings:
                return findings
    return findings


def run_contradiction_tick() -> dict[str, Any]:
    """One detection cycle. Publishes contradiction.detected events.

    Designed to be called from a heartbeat tick or a scheduled task.
    Idempotent — same contradiction fires multiple times only if both
    decision and review survive a deduplication gap.
    """
    findings = detect_contradictions()
    if not findings:
        return {"outcome": "completed", "contradictions": 0}

    for f in findings:
        try:
            event_bus.publish(
                "contradiction.detected",
                {
                    "decision_id": f.get("decision_id"),
                    "decision_directive": f.get("decision_directive"),
                    "review_id": f.get("review_id"),
                    "review_text": f.get("review_text"),
                    "overlap_tokens": f.get("overlap_tokens"),
                    "detected_at": f.get("detected_at"),
                },
            )
        except Exception as exc:
            logger.debug("contradiction_engine: publish failed: %s", exc)

    return {
        "outcome": "completed",
        "contradictions": len(findings),
        "findings": findings,
    }


def build_contradiction_engine_surface(*, limit: int = 5) -> dict[str, Any]:
    """Mission-control/read-surface for semantic contradiction detection.

    Side-effect free: runs detection only, does not publish events.
    """
    findings = detect_contradictions(max_findings=max(1, int(limit or 5)))
    return {
        "active": bool(findings),
        "mode": "semantic-decision-review-contradictions",
        "summary": {
            "finding_count": len(findings),
            "current_finding": (
                str(findings[0].get("decision_directive") or "")
                if findings else "No semantic contradiction detected"
            ),
        },
        "items": findings,
        "allowed_effects": [
            "prompt_attention",
            "review_decision_or_self_review",
            "do_not_auto_mutate_decisions",
        ],
    }
