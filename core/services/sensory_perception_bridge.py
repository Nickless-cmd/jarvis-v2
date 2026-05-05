"""Sensory perception bridge.

Bridges Sansernes Arkiv (sensory_archive) into perceptual_event_engine.
When a sensory record is created, this module compares it against a
modality-specific baseline (time-of-day window for visual+audio with
recent-baseline fallback, recent-baseline only for atmosphere+mixed).
Meaningful changes become perceptual events with salience proportional
to change magnitude.

See docs/superpowers/specs/2026-05-04-sensory-perception-bridge-design.md
for the full design.
"""
from __future__ import annotations

import logging
from collections import Counter

logger = logging.getLogger(__name__)


def _shingle(text: str, *, n: int = 3) -> set[str]:
    """Tokenize lowercased text into overlapping n-grams of words."""
    words = [w for w in (text or "").lower().split() if w]
    if len(words) < n:
        return set(words)
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets. Returns 0 if both empty."""
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b) or 1
    return inter / union


def _mode(values: list[str]) -> str | None:
    """Most common value. On tie, returns the value that appears first in the list."""
    if not values:
        return None
    counter = Counter(values)
    max_count = max(counter.values())
    for v in values:
        if counter[v] == max_count:
            return v
    return None


def _aggregate_baseline(records: list[dict]) -> dict:
    """Aggregate 1-N records into a single baseline.

    Returns:
        {
            "records": [...],
            "mood": str | None,        # mode (most common) of non-empty mood_tones
            "content_tokens": set[str],  # union of shingles across all contents
            "metadata": dict[str, set[str]],  # per-key union of stringified values
        }
    """
    moods = [str(r.get("mood_tone") or "").strip().lower() for r in records]
    moods = [m for m in moods if m]
    mood_mode = _mode(moods) if moods else None

    all_tokens: set[str] = set()
    for r in records:
        all_tokens.update(_shingle(str(r.get("content") or "")))

    metadata_union: dict[str, set[str]] = {}
    for r in records:
        md = r.get("metadata") or {}
        if isinstance(md, dict):
            for k, v in md.items():
                metadata_union.setdefault(k, set()).add(str(v))

    return {
        "records": list(records),
        "mood": mood_mode,
        "content_tokens": all_tokens,
        "metadata": metadata_union,
    }
