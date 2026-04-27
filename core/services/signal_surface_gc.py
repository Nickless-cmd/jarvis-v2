"""Garbage collector for runtime signal-surface trackers.

Three trackers (private_state_snapshot, metabolism_state_signal,
release_marker_signal) each have their own stale-detection that runs
on read-side surface builds. Problem: any update touches updated_at,
which keeps the stale clock perpetually fresh, so old signals
accumulate forever — Jarvis sees 8 active in each surface even when
none are recent in any meaningful sense.

This module adds two layers of cleanup, run as a periodic job:

1. **Refresh-based stale**: invoke each tracker's existing refresh
   function to get baseline cleanup.

2. **Force-archive by created_at**: anything older than 14 days from
   creation gets status='archived' regardless of touches. created_at
   is immutable so this can't be defeated by activity.

Hourly cadence is fine — the surfaces are read-mostly and a slightly
stale cleanup horizon is acceptable.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_FORCE_ARCHIVE_AFTER_DAYS = 14


def _force_archive(
    *,
    items: list[dict[str, Any]],
    id_field: str,
    update_fn: Any,
    label: str,
) -> int:
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=_FORCE_ARCHIVE_AFTER_DAYS)
    archived = 0
    for item in items:
        status = str(item.get("status") or "")
        if status in {"archived", "closed", "resolved"}:
            continue
        created_raw = str(item.get("created_at") or "")
        if not created_raw:
            continue
        try:
            created = datetime.fromisoformat(created_raw)
        except ValueError:
            continue
        if created > cutoff:
            continue
        item_id = str(item.get(id_field) or "")
        if not item_id:
            continue
        try:
            update_fn(
                item_id,
                status="archived",
                updated_at=now.isoformat(),
                status_reason=(
                    f"Force-archived after {_FORCE_ARCHIVE_AFTER_DAYS}d since creation "
                    "(signal-surface GC)."
                ),
            )
            archived += 1
        except Exception as exc:
            logger.debug("signal_gc: archive %s/%s failed: %s", label, item_id, exc)
    return archived


def collect() -> dict[str, Any]:
    """Run a full GC pass across the three signal-surface trackers.
    Returns counts per tracker."""
    out: dict[str, Any] = {}

    # Private state snapshots — id field is snapshot_id
    try:
        from core.services.private_state_snapshot_tracking import (
            refresh_runtime_private_state_snapshot_statuses,
        )
        from core.runtime.db import (
            list_runtime_private_state_snapshots,
            update_runtime_private_state_snapshot_status,
        )
        refreshed = refresh_runtime_private_state_snapshot_statuses() or {}
        items = list_runtime_private_state_snapshots(limit=200) or []
        archived = _force_archive(
            items=items, id_field="snapshot_id",
            update_fn=update_runtime_private_state_snapshot_status,
            label="private_state",
        )
        out["private_state"] = {"refreshed": refreshed, "archived": archived}
    except Exception as exc:
        out["private_state_error"] = str(exc)

    # Metabolism signals — id field is signal_id
    try:
        from core.services.metabolism_state_signal_tracking import (
            refresh_runtime_metabolism_state_signal_statuses,
        )
        from core.runtime.db import (
            list_runtime_metabolism_state_signals,
            update_runtime_metabolism_state_signal_status,
        )
        refreshed = refresh_runtime_metabolism_state_signal_statuses() or {}
        items = list_runtime_metabolism_state_signals(limit=200) or []
        archived = _force_archive(
            items=items, id_field="signal_id",
            update_fn=update_runtime_metabolism_state_signal_status,
            label="metabolism",
        )
        out["metabolism"] = {"refreshed": refreshed, "archived": archived}
    except Exception as exc:
        out["metabolism_error"] = str(exc)

    # Release markers — id field is signal_id
    try:
        from core.services.release_marker_signal_tracking import (
            refresh_runtime_release_marker_signal_statuses,
        )
        from core.runtime.db import (
            list_runtime_release_marker_signals,
            update_runtime_release_marker_signal_status,
        )
        refreshed = refresh_runtime_release_marker_signal_statuses() or {}
        items = list_runtime_release_marker_signals(limit=200) or []
        archived = _force_archive(
            items=items, id_field="signal_id",
            update_fn=update_runtime_release_marker_signal_status,
            label="release_marker",
        )
        out["release_marker"] = {"refreshed": refreshed, "archived": archived}
    except Exception as exc:
        out["release_marker_error"] = str(exc)

    # Loops — proactive_loop_lifecycle_tracking
    try:
        from core.services.proactive_loop_lifecycle_tracking import (
            refresh_runtime_proactive_loop_lifecycle_signal_statuses,
        )
        out["loops"] = {
            "refreshed": refresh_runtime_proactive_loop_lifecycle_signal_statuses() or {},
        }
    except Exception as exc:
        out["loops_error"] = str(exc)

    # Corrupt goal-signal cleanup: archive any active goal_signal whose
    # title is detectably noise. Catches existing rot from the era before
    # _explicit_learning_focus had a substantive-topic gate.
    try:
        from core.runtime.db import (
            list_runtime_goal_signals,
            update_runtime_goal_signal_status,
        )
        from core.services.signal_noise_guard import is_noisy_signal_text
        items = list_runtime_goal_signals(limit=200) or []
        cleaned = 0
        now = datetime.now(UTC)
        for item in items:
            status = str(item.get("status") or "")
            if status not in {"active", "blocked", "stale"}:
                continue
            title = str(item.get("title") or "")
            summary = str(item.get("summary") or "")
            blob = (title + " " + summary).strip()
            if not blob or not is_noisy_signal_text(blob):
                continue
            try:
                update_runtime_goal_signal_status(
                    str(item.get("goal_id") or ""),
                    status="archived",
                    updated_at=now.isoformat(),
                    status_reason=(
                        "Force-archived: title/summary fails signal-noise guard "
                        "(sweeping corrupt entries from raw-runtime-text era)."
                    ),
                )
                cleaned += 1
            except Exception:
                continue
        out["goal_signal_cleanup"] = {"corrupt_archived": cleaned}
    except Exception as exc:
        out["goal_signal_cleanup_error"] = str(exc)

    return out
