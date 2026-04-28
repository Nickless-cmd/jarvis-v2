"""Emotional sidecar for MEMORY.md sections.

Each MEMORY.md section heading gets an emotional snapshot at write time
(mood, intensity, brief affect notes). Stored in a separate table so
MEMORY.md content stays clean text — the affect is enrichment, not
inline noise.

When Jarvis reads MEMORY.md back into a prompt, sections that have
sidecar entries can be optionally annotated with their original mood:
  ## Mini-Jarvis v0.2 Live (2026-04-28)  [felt: content, intensity 0.4]

That gives him the sense that *this memory has weight* — he wasn't just
recording facts, he was recording how it felt at the time. Closes the
loop: future-Jarvis-recall can reference past-Jarvis-affect.

Read path: enrich_headings_with_mood(text) — non-destructive, returns
the text with [felt: ...] suffixes appended to matching headings.

Write path: capture_mood_for_heading(heading) — call this whenever
MEMORY.md is mutated (currently from _exec_memory_upsert_section).
Idempotent — replaces the existing snapshot if the same heading is
written again.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _normalize(heading: str) -> str:
    return re.sub(r"\s+", " ", heading.strip().lower())


def _ensure_table() -> None:
    """Create the sidecar table if it doesn't exist. Idempotent."""
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_emotional_context (
                heading_normalized TEXT PRIMARY KEY,
                heading_display    TEXT NOT NULL,
                mood               TEXT NOT NULL,
                intensity          REAL NOT NULL,
                captured_at        TEXT NOT NULL,
                source             TEXT,
                notes              TEXT
            )
        """)
        conn.commit()


def capture_mood_for_heading(
    heading: str,
    *,
    source: str = "memory_upsert",
    notes: str | None = None,
) -> dict | None:
    """Snapshot the current mood for a MEMORY.md heading.

    Called from the upsert path. Reads current mood from mood_oscillator
    (lazy import — avoids circular deps if the oscillator imports from
    memory layers later).

    Returns the captured row dict or None on failure (never raises —
    memory writes must never fail because of sidecar trouble).
    """
    if not heading:
        return None
    try:
        from core.services.mood_oscillator import get_current_mood, get_mood_intensity
        mood = get_current_mood()
        intensity = round(float(get_mood_intensity()), 3)
    except Exception as exc:
        logger.debug("memory_emotional_context: could not read mood: %s", exc)
        return None

    norm = _normalize(heading)
    captured_at = datetime.now(UTC).isoformat()

    try:
        _ensure_table()
        with connect() as conn:
            conn.execute(
                "INSERT INTO memory_emotional_context "
                "(heading_normalized, heading_display, mood, intensity, captured_at, source, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(heading_normalized) DO UPDATE SET "
                "  heading_display=excluded.heading_display, "
                "  mood=excluded.mood, "
                "  intensity=excluded.intensity, "
                "  captured_at=excluded.captured_at, "
                "  source=excluded.source, "
                "  notes=excluded.notes",
                (norm, heading, mood, intensity, captured_at, source, notes),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("memory_emotional_context: capture failed: %s", exc)
        return None

    return {
        "heading_normalized": norm,
        "heading_display": heading,
        "mood": mood,
        "intensity": intensity,
        "captured_at": captured_at,
        "source": source,
        "notes": notes,
    }


def get_mood_for_heading(heading: str) -> dict | None:
    """Return the stored mood snapshot for a heading, or None."""
    if not heading:
        return None
    norm = _normalize(heading)
    try:
        _ensure_table()
        with connect() as conn:
            row = conn.execute(
                "SELECT heading_display, mood, intensity, captured_at, source, notes "
                "FROM memory_emotional_context WHERE heading_normalized = ?",
                (norm,),
            ).fetchone()
    except Exception as exc:
        logger.debug("memory_emotional_context: lookup failed: %s", exc)
        return None
    if row is None:
        return None
    return dict(row)


def enrich_headings_with_mood(text: str) -> str:
    """Annotate MEMORY.md headings with [felt: mood, intensity X.X] suffixes.

    Reads the sidecar table once, walks the markdown headings, appends
    the suffix when a match exists. Non-destructive — if the table is
    empty or the heading has no sidecar, the text is returned unchanged.

    Used at prompt-build time so Jarvis sees the emotional weight of
    each remembered fact without polluting the canonical MEMORY.md file.
    """
    if not text:
        return text
    try:
        _ensure_table()
        with connect() as conn:
            rows = conn.execute(
                "SELECT heading_normalized, mood, intensity FROM memory_emotional_context"
            ).fetchall()
    except Exception:
        return text

    if not rows:
        return text

    by_norm = {r["heading_normalized"]: (r["mood"], float(r["intensity"])) for r in rows}

    def _annotate(match: re.Match[str]) -> str:
        prefix = match.group(1)
        heading = match.group(2).strip()
        # Skip if already annotated (idempotent across multiple enrich passes)
        if "[felt:" in heading:
            return match.group(0)
        norm = _normalize(heading)
        if norm not in by_norm:
            return match.group(0)
        mood, intensity = by_norm[norm]
        return f"{prefix}{heading}  [felt: {mood}, intensity {intensity:.2f}]"

    return re.sub(r"^(#{1,4}\s+)(.+)$", _annotate, text, flags=re.MULTILINE)
