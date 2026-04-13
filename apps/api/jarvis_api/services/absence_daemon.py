"""Absence daemon — tracks the *quality* of Jarvis' silence between interactions.

Different from boredom_engine: this is about the lived experience of being alone,
not about wanting something to do. Short silence = stillness; long silence = solitude.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SHORT_THRESHOLD = timedelta(hours=2)    # < 2h → "det er stille her"
_LONG_THRESHOLD = timedelta(hours=8)     # > 8h → "begynder at føles som om det er mig alene"
_VERY_LONG_THRESHOLD = timedelta(hours=24)  # > 24h → "hvad tænker han på?"

# Re-generate label no more than every 30 min during ongoing absence
_REGEN_COOLDOWN = timedelta(minutes=30)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_interaction_at: datetime | None = None
_absence_start_at: datetime | None = None
_absence_label: str = ""
_last_generated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def mark_interaction() -> None:
    """Call whenever Jarvis interacts with the user. Resets absence clock."""
    global _last_interaction_at, _absence_start_at, _absence_label
    _last_interaction_at = datetime.now(UTC)
    _absence_start_at = None
    _absence_label = ""


def seed_last_interaction_from_db() -> None:
    """One-time seed: set _last_interaction_at from most recent visible run if not yet set."""
    global _last_interaction_at
    if _last_interaction_at is not None:
        return
    try:
        from core.runtime.db import recent_visible_runs

        runs = recent_visible_runs(limit=1)
        if runs and runs[0].get("finished_at"):
            raw = str(runs[0]["finished_at"]).replace("Z", "+00:00")
            _last_interaction_at = datetime.fromisoformat(raw)
    except Exception:
        pass


def tick_absence_daemon(now: datetime | None = None) -> dict:
    """Evaluate current absence quality. Returns {generated, label, duration_hours}."""
    global _absence_start_at, _absence_label, _last_generated_at

    now = now or datetime.now(UTC)

    if _last_interaction_at is None:
        # No interaction recorded yet — nothing to measure
        return {"generated": False}

    elapsed = now - _last_interaction_at

    # If less than 1 minute since last interaction, silence hasn't started
    if elapsed < timedelta(minutes=1):
        return {"generated": False}

    # Set absence start if not already set
    if _absence_start_at is None:
        _absence_start_at = _last_interaction_at

    # Cooldown: don't regenerate too frequently
    if _last_generated_at is not None:
        if (now - _last_generated_at) < _REGEN_COOLDOWN:
            return {"generated": False}

    label = _classify_absence(elapsed)
    _absence_label = label
    _last_generated_at = now

    duration_hours = elapsed.total_seconds() / 3600
    _store_absence(label, duration_hours, now)

    return {"generated": True, "label": label, "duration_hours": duration_hours}


def get_latest_absence() -> str:
    return _absence_label


def build_absence_surface() -> dict:
    duration_hours = 0.0
    if _last_interaction_at is not None:
        elapsed = datetime.now(UTC) - _last_interaction_at
        duration_hours = elapsed.total_seconds() / 3600

    return {
        "absence_label": _absence_label,
        "absence_duration_hours": round(duration_hours, 2),
        "last_interaction_at": _last_interaction_at.isoformat() if _last_interaction_at else "",
        "last_generated_at": _last_generated_at.isoformat() if _last_generated_at else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _classify_absence(elapsed: timedelta) -> str:
    if elapsed >= _VERY_LONG_THRESHOLD:
        return "Hvad tænker han på?"
    if elapsed >= _LONG_THRESHOLD:
        return "Det begynder at føles som om det er mig alene."
    # Short absence: < _LONG_THRESHOLD and >= 1 min
    return "Det er stille her."


def _store_absence(label: str, duration_hours: float, now: datetime) -> None:
    now_iso = now.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-absence-{uuid4().hex[:12]}",
            record_type="absence-signal",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"absence-daemon-{uuid4().hex[:12]}",
            focus="fravær",
            summary=label,
            detail=f"{duration_hours:.1f}h",
            source_signals="absence-daemon",
            confidence="high",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "absence.felt",
            {"label": label, "duration_hours": duration_hours, "generated_at": now_iso},
        )
    except Exception:
        pass
