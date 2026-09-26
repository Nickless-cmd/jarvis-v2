"""Cache maintenance daemon — periodic cleanup of expired web cache entries.

Runs every 6 hours (cadence-gated). Deletes expired rows from the SQLite
web_cache table (shared by web_search and web_scrape tools), reports stats.

Also logs cache composition so we can track growth over time.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 6          # every 360 minutes
_LOG_THRESHOLD_ENTRIES = 20  # log cache composition if more than this many entries

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_last_result: dict[str, object] = {}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_cache_maintenance_daemon() -> dict[str, object]:
    """Run cache cleanup if cadence elapsed. Returns stats dict."""
    global _last_tick_at, _last_result

    now = datetime.now(UTC)

    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
            return {"maintained": False, "reason": "cadence"}

    try:
        from core.runtime.db import connect, web_cache_cleanup

        with connect() as conn:
            # Count entries before cleanup
            count_before = conn.execute(
                "SELECT COUNT(*) AS cnt FROM web_cache"
            ).fetchone()["cnt"]

            expired_before = conn.execute(
                "SELECT COUNT(*) AS cnt FROM web_cache WHERE expires_at < ?",
                (now.isoformat(),),
            ).fetchone()["cnt"]

            # Run cleanup
            deleted = web_cache_cleanup(conn=conn)

            # Count after
            count_after = conn.execute(
                "SELECT COUNT(*) AS cnt FROM web_cache"
            ).fetchone()["cnt"]

            # Optional: log composition stats
            composition = {}
            if count_after >= _LOG_THRESHOLD_ENTRIES:
                rows = conn.execute(
                    """
                    SELECT ttl_policy, COUNT(*) AS cnt
                    FROM web_cache
                    GROUP BY ttl_policy
                    ORDER BY cnt DESC
                    """
                ).fetchall()
                composition = {r["ttl_policy"]: r["cnt"] for r in rows}

        # Events-table retention: bound the unbounded telemetry table (large table
        # → slower INSERTs → longer WAL write-lock holds → API latency spikes).
        # Batched + capped → gradual, never a long lock. Best-effort.
        events_pruned = 0
        telemetry_pruned: dict[str, object] = {}
        versioned_pruned: dict[str, object] = {}
        try:
            from core.services.events_retention import (
                prune_old_events, prune_telemetry_tables, prune_versioned_tables,
            )
            events_pruned = int(prune_old_events().get("deleted", 0) or 0)
            telemetry_pruned = prune_telemetry_tables()
            versioned_pruned = prune_versioned_tables()
        except Exception:
            pass

        # State-fil-rotation: de operationelle JSON-filer i ~/.jarvis-v2/state
        # havde aldrig fået ryddet (målt 30-08: plan_proposals havde 400 poster
        # hvoraf ALLE var over 7 dage, ældste 125). Samme princip som
        # events-retention ovenfor — bare på filerne i stedet for tabellerne.
        state_files_pruned: dict[str, int] = {}
        orphan_uploads: dict[str, int] = {}
        try:
            from core.services.state_file_retention import (
                cleanup_orphan_uploads, prune_all_state_files,
            )
            state_files_pruned = prune_all_state_files()
            # Vedhæftninger for sessioner der hverken har række eller beskeder.
            # Målt 30-08: 151 filer / 87 MB i 12 døde mapper.
            orphan_uploads = cleanup_orphan_uploads()
        except Exception:
            pass

        # Forældreløse balancer-slots: profiler der aldrig vælges (backup-mapper,
        # provider-navngivne profiler). Målt 01-09: 166 af 264 poster var inert
        # historik, så state-filen så dobbelt så stor ud som virkeligheden.
        orphan_slots = 0
        try:
            from core.services.cheap_lane_balancer import prune_orphan_slots
            orphan_slots = prune_orphan_slots()
        except Exception:
            pass

        # Log the actual checkpoint result. WAL file size alone is only a
        # high-water mark: SQLite can reuse a large file with few live frames.
        # TRUNCATE reclaims the allocated file when no reader blocks it.
        wal_checkpoint = checkpoint_wal()

        result = {
            "deleted": deleted,
            "count_before": count_before,
            "count_after": count_after,
            "expired_before": expired_before,
            "composition": composition,
            "events_pruned": events_pruned,
            "telemetry_pruned": telemetry_pruned,
            "versioned_pruned": versioned_pruned,
            "state_files_pruned": state_files_pruned,
            "orphan_uploads": orphan_uploads,
            "orphan_slots": orphan_slots,
            "wal_checkpoint": wal_checkpoint,
        }
    except Exception as exc:
        result = {"maintained": False, "error": str(exc)[:200]}

    _last_tick_at = now
    _last_result = result

    if result.get("deleted", 0) > 0:
        try:
            event_bus.publish(
                "cache_maintenance.cleanup_completed",
                {
                    "deleted": result["deleted"],
                    "count_before": result["count_before"],
                    "count_after": result["count_after"],
                    "completed_at": now.isoformat(),
                },
            )
        except Exception:
            pass

    return {"maintained": True, **result}


def checkpoint_wal() -> dict[str, object]:
    """Checkpoint and record the actual SQLite result, including busy frames."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if row is None:
            _log.warning("WAL checkpoint returned no result")
            return {}
        result: dict[str, object] = {
            "busy": row[0], "wal_frames": row[1], "checkpointed": row[2],
        }
        _log.info("WAL checkpoint: busy=%s wal_frames=%s checkpointed=%s",
                  row[0], row[1], row[2])
        return result
    except Exception as exc:
        _log.warning("WAL checkpoint failed: %s", exc)
        return {"error": str(exc)[:120]}


def get_cache_maintenance_stats() -> dict[str, object]:
    return {
        "last_result": _last_result,
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }


def build_cache_maintenance_surface() -> dict[str, object]:
    return {
        "last_deleted": _last_result.get("deleted", 0),
        "count_before": _last_result.get("count_before", 0),
        "count_after": _last_result.get("count_after", 0),
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }
