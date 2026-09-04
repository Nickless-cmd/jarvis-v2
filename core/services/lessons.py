"""Lessons service — from mistake to next conversation (memory repair 2026-09-04, R4).

Writers (each a one-liner for the callers):
- ``record_correction`` — Bjørn's own words + what Jarvis had just said
- ``record_tool_error`` — a tool failed; signature = tool + error head
- ``record_review_lessons`` — self-review / regret / arc-rule text (proposed
  until seen twice)

Reader:
- ``build_lessons_section`` — the ``[HUKOMMELSE]`` block: the lessons most
  similar to the user's message first, then the strongest overall.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from core.runtime import db_lessons

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[0-9A-Za-zÆØÅæøå][0-9A-Za-zÆØÅæøå\-]{2,}")
_TOPIC_WORDS = 8
_MAX_LINE = 220


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _topic_from(text: str) -> str:
    words = [w for w in _WORD_RE.findall(str(text or "")) if len(w) >= 3]
    return " ".join(words[:_TOPIC_WORDS])


def _clip(text: str, n: int) -> str:
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def record_correction(*, session_id: str, user_words: str, jarvis_words: str = "", topic: str = "") -> dict[str, Any]:
    """Bjørn corrected the previous turn. Active immediately — his word is authoritative."""
    uw = _clip(user_words, 300)
    jw = _clip(jarvis_words, 300)
    if not uw:
        return {"outcome": "skipped", "reason": "no user words"}
    sig_topic = topic or _topic_from(jw) or _topic_from(uw)
    signature = f"correction: {sig_topic}"
    if jw:
        lesson = f"Bjørn rettede mig ({_today()}): «{uw}» — efter jeg sagde «{jw}»."
    else:
        lesson = f"Bjørn rettede mig ({_today()}): «{uw}»."
    try:
        return db_lessons.upsert_lesson(
            signature=signature, lesson=lesson, source=db_lessons.SOURCE_CORRECTION,
            user_words=uw, jarvis_words=jw, activate=True,
        )
    except Exception as exc:
        logger.debug("lessons.record_correction failed: %s", exc)
        return {"outcome": "error", "reason": str(exc)[:160]}


def record_tool_error(*, tool_name: str, error_text: str, context: str = "") -> dict[str, Any]:
    """A tool call failed. Proposed until it happens twice, then active."""
    name = str(tool_name or "").strip() or "ukendt"
    err = _clip(error_text, 200)
    if not err:
        return {"outcome": "skipped", "reason": "no error text"}
    head = _clip(err, 80)
    signature = f"tool_error: {name}: {head}"
    ctx = f" (kontekst: {_clip(context, 80)})" if context else ""
    lesson = f"Værktøjet {name} fejlede: {err}{ctx}. Tjek forudsætningerne før næste kald."
    try:
        return db_lessons.upsert_lesson(signature=signature, lesson=lesson, source=db_lessons.SOURCE_TOOL_ERROR)
    except Exception as exc:
        logger.debug("lessons.record_tool_error failed: %s", exc)
        return {"outcome": "error", "reason": str(exc)[:160]}


def record_review_lessons(lessons: list[str] | tuple[str, ...], source: str) -> list[dict[str, Any]]:
    """Self-review / regret / arc-rule lessons → proposed (active at evidence ≥ 2)."""
    out: list[dict[str, Any]] = []
    for raw in lessons or []:
        text = _clip(raw, 400)
        if len(text) < 12:
            continue
        try:
            out.append(db_lessons.upsert_lesson(signature=text[:120], lesson=text, source=source))
        except Exception as exc:
            logger.debug("lessons.record_review_lessons failed: %s", exc)
    return out


def _format(lesson: dict[str, Any]) -> str:
    src = str(lesson.get("source") or "")
    ev = int(lesson.get("evidence_count") or 1)
    rep = int(lesson.get("repeated_count") or 0)
    tag = f"{src}, x{ev}"
    if rep:
        tag += f", gentaget {rep}×"
    return f"- [{tag}] {_clip(str(lesson.get('lesson') or ''), _MAX_LINE)}"


def build_lessons_section(user_message: str, *, limit_similar: int = 3, limit_strong: int = 3) -> str:
    """Render the lessons block for the prompt, or "" when nothing is active."""
    try:
        similar = db_lessons.find_similar_lessons(user_message, limit=limit_similar) if user_message else []
        strong = db_lessons.list_lessons(status="active", limit=limit_strong + limit_similar)
    except Exception as exc:
        logger.debug("lessons.build_lessons_section failed: %s", exc)
        return ""
    chosen: list[dict[str, Any]] = []
    seen: set[int] = set()
    for l in similar:
        if l.get("id") not in seen:
            seen.add(int(l["id"]))
            chosen.append(l)
    for l in strong:
        if len(chosen) >= limit_similar + limit_strong:
            break
        if l.get("id") not in seen:
            seen.add(int(l["id"]))
            chosen.append(l)
    if not chosen:
        return ""
    lines = ["Lektier (det jeg har lært af fejl — brug dem, og sig det hvis en gentager sig):"]
    lines.extend(_format(l) for l in chosen)
    return "\n".join(lines)
