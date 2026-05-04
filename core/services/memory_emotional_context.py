"""Backwards-compatible shim — emotional memory now lives in emotional_memory_engine.

This module re-exposes the original three public functions so existing
call-sites do not break. New code should import from
`core.services.emotional_memory_engine` directly.

The legacy `memory_emotional_context` table is no longer written to or
read from by this shim. A separate one-shot migration script (see
`scripts/migrate_emotional_memory.py`) copies any pre-existing legacy
rows into `emotional_memory_anchors`.
"""
from __future__ import annotations

import json
import logging
import re

from core.runtime.db import (
    get_emotional_memory_anchor,
    list_emotional_memory_anchors,
)
from core.services.emotional_memory_engine import capture_emotional_anchor

logger = logging.getLogger(__name__)


def _normalize(heading: str) -> str:
    return re.sub(r"\s+", " ", (heading or "").strip().lower())


def capture_mood_for_heading(
    heading: str,
    *,
    source: str = "memory_upsert",
    notes: str | None = None,
) -> dict | None:
    """Snapshot mood for a MEMORY.md heading. Returns legacy dict shape."""
    if not heading:
        return None
    norm = _normalize(heading)
    captured = capture_emotional_anchor(
        anchor_type="memory_heading",
        anchor_id=norm,
        context_features={"heading_display": heading},
        source=source,
        notes=notes,
    )
    if captured is None:
        return None
    return {
        "heading_normalized": norm,
        "heading_display": heading,
        "mood": captured.get("mood"),
        "intensity": captured.get("intensity"),
        "captured_at": captured.get("captured_at"),
        "source": source,
        "notes": notes,
    }


def get_mood_for_heading(heading: str) -> dict | None:
    if not heading:
        return None
    norm = _normalize(heading)
    row = get_emotional_memory_anchor(
        anchor_type="memory_heading", anchor_id=norm
    )
    if row is None:
        return None
    try:
        ctx = json.loads(str(row.get("context_features_json") or "{}"))
    except Exception:
        ctx = {}
    return {
        "heading_normalized": norm,
        "heading_display": str(ctx.get("heading_display") or norm),
        "mood": row.get("mood"),
        "intensity": row.get("intensity"),
        "captured_at": row.get("captured_at"),
        "source": row.get("source"),
        "notes": row.get("notes"),
    }


def enrich_headings_with_mood(text: str) -> str:
    """Annotate MEMORY.md headings with [felt: mood, intensity X.X] suffixes."""
    if not text:
        return text
    try:
        rows = list_emotional_memory_anchors(
            anchor_type="memory_heading", limit=2000
        )
    except Exception:
        return text
    if not rows:
        return text

    by_norm: dict[str, tuple[str, float]] = {}
    for r in rows:
        try:
            mood = str(r.get("mood") or "")
            intensity = float(r.get("intensity") or 0.0)
            anchor_id = str(r.get("anchor_id") or "")
            if anchor_id and mood:
                by_norm[anchor_id] = (mood, intensity)
        except Exception:
            continue

    def _annotate(match: re.Match[str]) -> str:
        prefix = match.group(1)
        heading = match.group(2).strip()
        if "[felt:" in heading:
            return match.group(0)
        norm = _normalize(heading)
        if norm not in by_norm:
            return match.group(0)
        mood, intensity = by_norm[norm]
        return f"{prefix}{heading}  [felt: {mood}, intensity {intensity:.2f}]"

    return re.sub(r"^(#{1,4}\s+)(.+)$", _annotate, text, flags=re.MULTILINE)
