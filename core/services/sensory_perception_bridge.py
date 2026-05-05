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


def _metadata_changed(
    new_md: dict, baseline_md: dict, modality: str
) -> bool:
    """Per-modality metadata change detection.

    audio: category-shift only (talk/silence/music/noise/mixed).
    visual: prompt-rotation ignored; other key changes count.
    atmosphere/mixed: any new key or value-shift counts.
    """
    if not new_md and not baseline_md:
        return False

    if modality == "audio":
        new_cat = str(new_md.get("category") or "")
        baseline_cats = baseline_md.get("category")
        if not new_cat:
            return False
        if isinstance(baseline_cats, set):
            return new_cat not in baseline_cats
        return new_cat != str(baseline_cats or "")

    if modality == "visual":
        for k, v in new_md.items():
            if k == "vision_prompt_index":
                continue
            baseline_vals = baseline_md.get(k)
            if baseline_vals is None:
                return True
            if isinstance(baseline_vals, set):
                if str(v) not in baseline_vals:
                    return True
            else:
                if str(v) != str(baseline_vals):
                    return True
        return False

    # atmosphere + mixed: any shift counts
    for k, v in new_md.items():
        baseline_vals = baseline_md.get(k)
        if baseline_vals is None:
            return True
        if isinstance(baseline_vals, set):
            if str(v) not in baseline_vals:
                return True
        else:
            if str(v) != str(baseline_vals):
                return True
    return False


def _detect_change(
    record: dict, baseline: dict | None, modality: str
) -> dict:
    """Combined heuristic: mood_tone shift OR Jaccard < 0.4 OR metadata shift.

    Returns:
        {
            "changed": bool,
            "kind": str,  # one of: no_baseline, no_change, mood_shift, content_drift,
                          #         lexical_drift, metadata_change, mood_and_content
            "jaccard": float,
            "summary": str,
            "baseline_mood": str | None,
        }
    """
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        change_threshold = float(
            getattr(settings, "sensory_perception_jaccard_change_threshold", 0.4)
        )
        medium_threshold = float(
            getattr(settings, "sensory_perception_jaccard_medium_threshold", 0.25)
        )
    except Exception:
        change_threshold, medium_threshold = (0.4, 0.25)

    if baseline is None or not baseline.get("records"):
        return {
            "changed": False,
            "kind": "no_baseline",
            "jaccard": 1.0,
            "summary": "",
            "baseline_mood": None,
        }

    new_mood = (str(record.get("mood_tone") or "")).strip().lower() or None
    new_content = str(record.get("content") or "")
    new_metadata = record.get("metadata") or {}

    baseline_mood = baseline.get("mood")
    baseline_tokens = baseline.get("content_tokens") or set()
    baseline_metadata = baseline.get("metadata") or {}

    new_tokens = _shingle(new_content)
    jaccard = _jaccard(new_tokens, baseline_tokens)

    mood_shifted = bool(new_mood and baseline_mood and new_mood != baseline_mood)
    lex_shifted = jaccard < change_threshold
    metadata_shifted = _metadata_changed(new_metadata, baseline_metadata, modality)

    if not (mood_shifted or lex_shifted or metadata_shifted):
        return {
            "changed": False,
            "kind": "no_change",
            "jaccard": jaccard,
            "summary": "",
            "baseline_mood": baseline_mood,
        }

    if mood_shifted and (jaccard < medium_threshold or metadata_shifted):
        kind = "mood_and_content"
    elif mood_shifted:
        kind = "mood_shift"
    elif jaccard < medium_threshold:
        kind = "content_drift"
    elif metadata_shifted and not lex_shifted:
        kind = "metadata_change"
    else:
        kind = "lexical_drift"

    summary = _summary_for_change(modality, new_mood, baseline_mood, kind, jaccard)
    return {
        "changed": True,
        "kind": kind,
        "jaccard": jaccard,
        "summary": summary,
        "baseline_mood": baseline_mood,
    }


def _summary_for_change(
    modality: str,
    new_mood: str | None,
    baseline_mood: str | None,
    kind: str,
    jaccard: float,
) -> str:
    """Generate a short Danish summary line for the perceptual event."""
    modality_label = {
        "visual": "Visuel",
        "audio": "Audio",
        "atmosphere": "Atmosfære",
        "mixed": "Sammensat",
    }.get(modality, modality)

    if kind == "mood_and_content":
        if new_mood and baseline_mood:
            return (
                f"{modality_label}-ændring: stemning skiftet fra {baseline_mood} "
                f"til {new_mood} med markant nyt indhold"
            )
        return f"{modality_label}-ændring: kombineret stemnings- og indholdsskift"
    if kind == "mood_shift":
        if new_mood and baseline_mood:
            return f"{modality_label}-stemning ændret fra {baseline_mood} til {new_mood}"
        return f"{modality_label}-stemningsskift detekteret"
    if kind == "content_drift":
        return f"{modality_label}-indhold markant ændret (similarity {jaccard:.2f})"
    if kind == "metadata_change":
        return f"{modality_label}-metadata ændret (fx kategori-skift)"
    if kind == "lexical_drift":
        return f"{modality_label}-indhold mildt ændret (similarity {jaccard:.2f})"
    return f"{modality_label}-ændring"


def _salience_for_change(change: dict) -> str:
    """Map change description to salience level (high/medium/normal)."""
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        high_threshold = float(
            getattr(settings, "sensory_perception_jaccard_high_threshold", 0.15)
        )
    except Exception:
        high_threshold = 0.15

    kind = str(change.get("kind") or "")
    jaccard = float(change.get("jaccard") or 1.0)

    if kind == "mood_and_content":
        return "high"
    if kind == "mood_shift" and jaccard < high_threshold:
        return "high"
    if kind == "mood_shift":
        return "medium"
    if kind == "content_drift" and jaccard < high_threshold:
        return "high"
    if kind == "content_drift":
        return "medium"
    if kind == "metadata_change":
        return "medium"
    return "normal"


_VALID_MODALITIES = {"visual", "audio", "atmosphere", "mixed"}


def _bridge_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "sensory_perception_bridge_enabled", True))
    except Exception:
        return True


def _percept(
    *,
    source_event_id: int,
    source_kind: str,
    change_type: str,
    salience: str,
    summary: str,
    observed_at: str,
    evidence: dict[str, object],
) -> dict[str, object]:
    """Build a percept dict in the shape expected by perceptual_event_engine._record_perceptual_event."""
    return {
        "source_event_id": int(source_event_id or 0),
        "source_kind": str(source_kind or ""),
        "change_type": str(change_type or ""),
        "salience": str(salience or "normal"),
        "summary": " ".join(str(summary or "").split())[:240],
        "observed_at": str(observed_at or ""),
        "evidence": dict(evidence or {}),
    }


def classify_sensory_change(event: dict[str, object]) -> dict[str, object] | None:
    """Top-level entry. Returns a percept dict if the event represents a meaningful
    sensory change, else None. Never raises."""
    try:
        if not _bridge_enabled():
            return None
        return _classify_sensory_change_inner(event)
    except Exception as exc:
        logger.warning("sensory_perception_bridge: classify failed: %s", exc)
        return None


def _classify_sensory_change_inner(event: dict[str, object]) -> dict[str, object] | None:
    if str(event.get("kind") or "") != "memory.sensory.recorded":
        return None

    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payload = payload or {}
    memory_id = payload.get("id")
    modality = str(payload.get("modality") or "")
    if not memory_id or modality not in _VALID_MODALITIES:
        return None

    try:
        from core.services import sensory_archive
        record = sensory_archive.get(str(memory_id))
    except Exception as exc:
        logger.debug("sensory_perception_bridge: get record failed: %s", exc)
        return None
    if not record:
        return None

    try:
        baseline = _build_baseline(modality, record)
    except Exception as exc:
        logger.debug("sensory_perception_bridge: build_baseline failed: %s", exc)
        return None

    change = _detect_change(record, baseline, modality)
    if not change.get("changed"):
        return None

    salience = _salience_for_change(change)
    return _percept(
        source_event_id=int(event.get("id") or 0),
        source_kind="memory.sensory.recorded",
        change_type=f"sensory-change-{modality}",
        salience=salience,
        summary=change.get("summary") or f"Sensory change in {modality}",
        observed_at=str(event.get("created_at") or record.get("timestamp") or ""),
        evidence={
            "memory_id": memory_id,
            "modality": modality,
            "mood_tone_now": record.get("mood_tone"),
            "mood_tone_baseline": change.get("baseline_mood"),
            "jaccard": round(float(change.get("jaccard") or 0.0), 4),
            "change_kind": change.get("kind"),
        },
    )
