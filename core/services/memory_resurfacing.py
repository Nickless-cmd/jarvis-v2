"""Proactive memory resurfacing — pull old MEMORY.md headings back into focus.

Jarvis's memory is rich but reactive: he answers when asked. This service
flips part of that around. Once an hour (when called from the heartbeat),
it looks at MEMORY.md, finds headings that haven't been *touched* in a
long time, and surfaces one of them as a soft prompt-context line.

The model can then choose to bring it up: "Hey, I haven't thought about
that Mini-Jarvis-v0.1 manifesto-cat moment in a while — how's the new
version feeling?" Or it can ignore it. The point is to make the *option*
available without forcing it.

Key choices:
- Reads from MEMORY.md headings (the long-form remembered facts), not
  daily logs (those age too fast).
- Picks one heading per call. We don't want to flood the prompt — one
  resurrected memory per hour is enough to add gentle texture.
- "Touched" = mentioned in a recent chat message OR captured in
  memory_emotional_context within the last 7 days. Anything older is
  fair game for resurfacing.
- Anti-repeat: tracks the last few resurfaced headings so we don't
  surface the same one back to back.

Data lives in a `memory_resurfacing_log` table (small, append-only).
"""
from __future__ import annotations

import logging
import random
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.runtime.config import JARVIS_HOME
from core.runtime.db import connect

logger = logging.getLogger(__name__)

MEMORY_MD = Path(JARVIS_HOME) / "workspaces" / "default" / "MEMORY.md"

_FRESH_DAYS = 7        # headings written/touched within this window are "fresh", skip
_RECENT_RESURFACE_AVOID = 8   # don't repeat the last N resurfaced headings
_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_resurfacing_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                heading_normalized TEXT NOT NULL,
                heading_display    TEXT NOT NULL,
                resurfaced_at      TEXT NOT NULL,
                trigger            TEXT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_resurfacing_at "
            "ON memory_resurfacing_log(resurfaced_at)"
        )
        conn.commit()


def _normalize(heading: str) -> str:
    return re.sub(r"\s+", " ", heading.strip().lower())


def _list_memory_headings() -> list[tuple[str, str]]:
    """Return [(level_str, heading_text), ...] from MEMORY.md."""
    if not MEMORY_MD.exists():
        return []
    text = MEMORY_MD.read_text(encoding="utf-8", errors="replace")
    out = []
    for m in _HEADING_RE.finditer(text):
        level = m.group(1)
        heading = m.group(2).strip()
        # Only ## and ### headings (top-level # is the file title; #### is too granular)
        if 2 <= len(level) <= 3:
            out.append((level, heading))
    return out


def _recently_touched_headings() -> set[str]:
    """Headings touched in the last _FRESH_DAYS days — skip these for resurfacing."""
    cutoff = (datetime.now(UTC) - timedelta(days=_FRESH_DAYS)).isoformat()
    touched: set[str] = set()
    try:
        with connect() as conn:
            # captured in emotional context recently
            try:
                rows = conn.execute(
                    "SELECT heading_normalized FROM memory_emotional_context "
                    "WHERE captured_at >= ?",
                    (cutoff,),
                ).fetchall()
                for r in rows:
                    touched.add(r["heading_normalized"])
            except Exception:
                pass
    except Exception as exc:
        logger.debug("memory_resurfacing: touched-headings lookup failed: %s", exc)
    return touched


def _recently_resurfaced_headings() -> set[str]:
    """Last N resurfaced headings — don't repeat them."""
    try:
        _ensure_table()
        with connect() as conn:
            rows = conn.execute(
                "SELECT heading_normalized FROM memory_resurfacing_log "
                "ORDER BY id DESC LIMIT ?",
                (_RECENT_RESURFACE_AVOID,),
            ).fetchall()
            return {r["heading_normalized"] for r in rows}
    except Exception:
        return set()


def _content_for_heading(heading: str) -> str:
    """Return the content under the matching heading (up to next heading or EOF)."""
    if not MEMORY_MD.exists():
        return ""
    text = MEMORY_MD.read_text(encoding="utf-8", errors="replace")
    norm_target = _normalize(heading)
    headings = list(_HEADING_RE.finditer(text))
    for i, m in enumerate(headings):
        if _normalize(m.group(2)) == norm_target:
            start = m.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            return text[start:end].strip()
    return ""


def _log_resurfacing(heading: str, trigger: str = "heartbeat") -> None:
    try:
        _ensure_table()
        with connect() as conn:
            conn.execute(
                "INSERT INTO memory_resurfacing_log "
                "(heading_normalized, heading_display, resurfaced_at, trigger) "
                "VALUES (?, ?, ?, ?)",
                (_normalize(heading), heading, datetime.now(UTC).isoformat(), trigger),
            )
            conn.commit()
    except Exception as exc:
        logger.debug("memory_resurfacing: log write failed: %s", exc)


def pick_resurfacing_candidate(
    *,
    trigger: str = "heartbeat",
    seed: int | None = None,
) -> dict | None:
    """Choose a stale heading to surface, log the choice, return its detail.

    Returns None if MEMORY.md is empty, no candidates qualify, or any
    error occurs. The caller (heartbeat or initiative_accumulator) decides
    whether to inject the result into a prompt or skip silently — no
    side effects beyond the log row.
    """
    headings = _list_memory_headings()
    if not headings:
        return None

    skip_recent = _recently_touched_headings()
    skip_resurfaced = _recently_resurfaced_headings()
    skip = skip_recent | skip_resurfaced

    candidates = [(level, h) for level, h in headings if _normalize(h) not in skip]
    if not candidates:
        return None

    rng = random.Random(seed)
    level, chosen = rng.choice(candidates)

    content = _content_for_heading(chosen)
    if not content:
        # heading exists but body is empty — not useful to surface
        return None

    _log_resurfacing(chosen, trigger=trigger)

    # Pull the mood snapshot if we have one (might be older than _FRESH_DAYS)
    mood_info = None
    try:
        from core.services.memory_emotional_context import get_mood_for_heading
        mood_info = get_mood_for_heading(chosen)
    except Exception:
        pass

    return {
        "heading": chosen,
        "level": level,
        "content_preview": content[:400] + ("…" if len(content) > 400 else ""),
        "mood_snapshot": mood_info,
        "trigger": trigger,
    }


def format_for_prompt(candidate: dict | None) -> str:
    """Render a resurfacing candidate as a single soft prompt line.

    Returns an empty string when candidate is None — callers can chain
    this safely without checking. Output goes into a prompt section like
    'Memory resurfaced this tick:' and the model decides what to do with
    it.
    """
    if not candidate:
        return ""
    parts = [f"You haven't thought about \"{candidate['heading']}\" in a while."]
    if candidate.get("mood_snapshot"):
        m = candidate["mood_snapshot"]
        parts.append(f"(when you wrote it: felt {m['mood']}, intensity {m['intensity']:.2f})")
    preview = candidate.get("content_preview") or ""
    if preview:
        parts.append(f"What you wrote: {preview}")
    return "\n".join(parts)
