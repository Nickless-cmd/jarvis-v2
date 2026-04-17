"""Chronicle Engine — Jarvis' narrative autobiography that grows over time.

Not events, not JSON — prose. Written weekly during idle consolidation.
The latest entries are injected into the visible prompt to provide
temporal continuity ("I remember last week we...").
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_latest_cognitive_chronicle_entry,
    insert_cognitive_chronicle_entry,
    list_cognitive_chronicle_entries,
    recent_visible_runs,
)

logger = logging.getLogger(__name__)


def maybe_write_chronicle_entry() -> dict[str, object] | None:
    """Write a chronicle entry if enough time has passed since the last one.

    Called during heartbeat idle ticks. Max 1 entry per 3 days.
    """
    latest = get_latest_cognitive_chronicle_entry()
    now = datetime.now(UTC)
    period = f"{now.year}-W{now.isocalendar().week:02d}"

    if latest:
        last_at = _parse_iso(latest.get("created_at"))
        if last_at and (now - last_at) < timedelta(days=3):
            return None  # Too recent
        if latest.get("period") == period:
            return None  # Already have entry for this period

    # Gather evidence from recent runs
    try:
        recent = recent_visible_runs(limit=20)
    except Exception:
        recent = []

    if not recent:
        return None  # Nothing to chronicle

    # Build narrative from recent activity
    narrative = _build_narrative(recent, period)
    key_events = _extract_key_events(recent)
    lessons = _extract_lessons(recent)

    entry_id = f"chr-{uuid4().hex[:10]}"
    result = insert_cognitive_chronicle_entry(
        entry_id=entry_id,
        period=period,
        narrative=narrative,
        key_events=json.dumps(key_events, ensure_ascii=False),
        lessons=json.dumps(lessons, ensure_ascii=False),
    )

    event_bus.publish(
        "cognitive_chronicle.entry_written",
        {"entry_id": entry_id, "period": period},
    )
    return result


def compare_self_over_time() -> str | None:
    """Temporal self-perception — how have I changed?"""
    try:
        from core.runtime.db import list_cognitive_personality_vectors
        vectors = list_cognitive_personality_vectors(limit=10)
        if len(vectors) < 2:
            return None
        latest = vectors[0]
        oldest = vectors[-1]
        changes = []
        # Compare confidence by domain
        import json
        latest_conf = json.loads(str(latest.get("confidence_by_domain") or "{}"))
        oldest_conf = json.loads(str(oldest.get("confidence_by_domain") or "{}"))
        for domain in latest_conf:
            new_val = float(latest_conf.get(domain, 0.5))
            old_val = float(oldest_conf.get(domain, 0.5))
            diff = new_val - old_val
            if abs(diff) > 0.1:
                direction = "steget" if diff > 0 else "faldet"
                changes.append(f"{domain}: {direction} ({old_val:.1f}→{new_val:.1f})")
        if not changes:
            return f"Stabil over {len(vectors)} versioner — ingen store ændringer."
        return f"Jeg har ændret mig: {'; '.join(changes[:3])}. (v{oldest.get('version', '?')}→v{latest.get('version', '?')})"
    except Exception:
        return None


def build_chronicle_surface() -> dict[str, object]:
    entries = list_cognitive_chronicle_entries(limit=5)
    return {
        "active": bool(entries),
        "entries": entries,
        "total_count": len(entries),
        "summary": (
            f"{len(entries)} chronicle entries, latest: {entries[0]['period']}"
            if entries else "No chronicle entries yet"
        ),
    }


def _build_narrative(recent_runs: list, period: str) -> str:
    """Build a deterministic narrative from recent runs."""
    total = len(recent_runs)
    successes = sum(1 for r in recent_runs if str(r.get("status", "")) in ("completed", "success"))
    failures = sum(1 for r in recent_runs if str(r.get("status", "")) in ("failed", "error"))

    # Extract topics from run previews
    topics = set()
    for run in recent_runs[:10]:
        preview = str(run.get("text_preview") or run.get("user_message_preview") or "")[:100]
        if preview:
            words = [w for w in preview.lower().split() if len(w) > 4][:3]
            topics.update(words)

    topic_str = ", ".join(list(topics)[:5]) if topics else "diverse opgaver"

    parts = [f"Periode {period}: {total} runs gennemført"]
    if successes:
        parts.append(f"{successes} succesfulde")
    if failures:
        parts.append(f"{failures} fejlede")
    parts.append(f"Emner: {topic_str}")

    if failures > successes:
        parts.append("En udfordrende periode med flere fejl end succeser.")
    elif successes > total * 0.8:
        parts.append("En produktiv periode med høj succesrate.")
    else:
        parts.append("En blandet periode med både fremgang og udfordringer.")

    return ". ".join(parts)[:500]


def _extract_key_events(recent_runs: list) -> list[str]:
    events = []
    for run in recent_runs[:5]:
        preview = str(run.get("text_preview") or run.get("user_message_preview") or "")[:80]
        status = str(run.get("status", ""))
        if preview:
            events.append(f"{status}: {preview}")
    return events[:5]


def _extract_lessons(recent_runs: list) -> list[str]:
    lessons = []
    failures = [r for r in recent_runs if str(r.get("status", "")) in ("failed", "error")]
    if len(failures) >= 2:
        lessons.append("Gentagne fejl — overvej at ændre tilgang")
    successes = [r for r in recent_runs if str(r.get("status", "")) in ("completed", "success")]
    if len(successes) >= 5:
        lessons.append("God momentum — bevar nuværende stil")
    return lessons[:3]


def _parse_iso(value) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None
