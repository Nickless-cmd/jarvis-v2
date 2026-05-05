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


from datetime import UTC, datetime, timedelta


def _parse_iso(ts: str) -> datetime | None:
    """Parse ISO timestamp; return None if malformed. Treats naive as UTC."""
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(str(ts))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _now() -> datetime:
    """Indirected for monkey-patching in tests."""
    return datetime.now(UTC)


def _recent_baseline(modality: str, current_record: dict) -> dict:
    """Latest N records of same modality excluding current."""
    from core.services import sensory_archive
    from core.runtime.settings import load_settings

    try:
        size = int(getattr(load_settings(), "sensory_perception_recent_baseline_size", 3))
    except Exception:
        size = 3

    candidates = sensory_archive.list_recent(modality=modality, limit=size + 5)
    matching = [r for r in candidates if r.get("id") != current_record.get("id")][:size]
    if not matching:
        return {"records": [], "mood": None, "content_tokens": set(), "metadata": {}}
    return _aggregate_baseline(matching)


def _time_of_day_baseline(modality: str, current_record: dict) -> dict | None:
    """Records inside ±N hours of current's time-of-day, over last M days.

    Returns None if fewer than `min_baseline_records` matches found.
    """
    from core.services import sensory_archive
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        window_hours = int(getattr(settings, "sensory_perception_time_window_hours", 2))
        window_days = int(getattr(settings, "sensory_perception_time_window_days", 7))
        min_records = int(getattr(settings, "sensory_perception_min_baseline_records", 3))
    except Exception:
        window_hours, window_days, min_records = (2, 7, 3)

    current_time = _parse_iso(str(current_record.get("timestamp") or ""))
    if current_time is None:
        return None

    since = (current_time - timedelta(days=window_days)).isoformat()
    candidates = sensory_archive.list_recent(
        modality=modality, since=since, limit=200,
    )
    target_hour = current_time.hour
    matching: list[dict] = []
    current_id = current_record.get("id")
    for r in candidates:
        if r.get("id") == current_id:
            continue
        ts = _parse_iso(str(r.get("timestamp") or ""))
        if ts is None:
            continue
        # Circular time-of-day distance: 23:00 vs 01:00 = 2 hours, not 22
        diff = abs(ts.hour - target_hour)
        hour_dist = min(diff, 24 - diff)
        if hour_dist <= window_hours:
            matching.append(r)
    if len(matching) < min_records:
        return None
    return _aggregate_baseline(matching)


def _build_baseline(modality: str, current_record: dict) -> dict | None:
    """Modality-aware baseline selection.

    visual + audio: time-of-day window primary, recent-baseline fallback.
    atmosphere + mixed: recent baseline only.
    """
    if modality in {"visual", "audio"}:
        baseline = _time_of_day_baseline(modality, current_record)
        if baseline and len(baseline["records"]) >= 1:
            return baseline
        return _recent_baseline(modality, current_record)
    elif modality in {"atmosphere", "mixed"}:
        return _recent_baseline(modality, current_record)
    return None
