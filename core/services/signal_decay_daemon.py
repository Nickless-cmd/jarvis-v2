"""Signal decay daemon — archive and delete stale signals across all signal tables.

Runs every 60 minutes (cadence-gated). Scans all 35+ signal tables for entries
with status='stale' and updated_at older than 24 hours. Archives to signal_archive
table before deletion to preserve debugging trail.

Archive entries are themselves cleaned up after 30 days.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 1          # every 60 minutes
_STALE_THRESHOLD_HOURS = 24  # delete signals stale for > 24h
_ARCHIVE_RETENTION_DAYS = 30

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_last_result: dict[str, object] = {}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_signal_decay_daemon() -> dict[str, object]:
    """Run signal decay if cadence elapsed. Returns stats dict."""
    global _last_tick_at, _last_result

    now = datetime.now(UTC)

    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
            return {"generated": False}

    try:
        from core.runtime.db import signal_decay_archive_and_delete, signal_archive_cleanup
        from core.services.development_focus_tracking import refresh_runtime_development_focus_statuses
        from core.services.goal_signal_tracking import refresh_runtime_goal_signal_statuses
        from core.services.reflection_signal_tracking import refresh_runtime_reflection_signal_statuses
        from core.services.dream_hypothesis_signal_tracking import (
            refresh_runtime_dream_hypothesis_signal_statuses,
        )
        from core.services.witness_signal_tracking import refresh_runtime_witness_signal_statuses

        refresh_counts = {
            "development_focus": refresh_runtime_development_focus_statuses(),
            "goal": refresh_runtime_goal_signal_statuses(),
            "reflection": refresh_runtime_reflection_signal_statuses(),
            "dream_hypothesis": refresh_runtime_dream_hypothesis_signal_statuses(),
            "witness": refresh_runtime_witness_signal_statuses(),
        }
        result = signal_decay_archive_and_delete(stale_hours=_STALE_THRESHOLD_HOURS)
        archive_cleaned = signal_archive_cleanup(max_age_days=_ARCHIVE_RETENTION_DAYS)
        result["archive_cleaned"] = archive_cleaned
        result["refreshed"] = refresh_counts
    except Exception as exc:
        _last_tick_at = now
        return {"generated": False, "error": str(exc)[:200]}

    _last_tick_at = now
    _last_result = result

    if result.get("archived", 0) > 0 or archive_cleaned > 0:
        try:
            event_bus.publish(
                "signal_decay.cleanup_completed",
                {
                    "archived": result.get("archived", 0),
                    "archive_cleaned": archive_cleaned,
                    "tables_scanned": result.get("tables_scanned", 0),
                    "per_table": result.get("per_table", {}),
                    "completed_at": now.isoformat(),
                },
            )
        except Exception:
            pass

    return {"generated": True, **result}


def get_signal_decay_stats() -> dict[str, object]:
    return {
        "last_result": _last_result,
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }


def build_signal_decay_surface() -> dict[str, object]:
    return {
        "last_archived": _last_result.get("archived", 0),
        "last_archive_cleaned": _last_result.get("archive_cleaned", 0),
        "tables_scanned": _last_result.get("tables_scanned", 0),
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }
