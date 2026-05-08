"""Memory pruning daemon — arkiverer entries med meget lav salience.

Kører hver 6. time. Scanner to lag:
  1. Brain entries med effektiv salience < tærskel (0.05)
  2. Private brain records med salience < tærskel (0.05)

Begge arkiveres (status → 'archived') så de ikke længere fylder i
aktiv søgning, men stadig kan genses via read_brain_entry / cold tier.

Dette er "glemsel som feature" — at glemme er at prioritere.
Uden denne daemon akkumulerer jeg al støj for evigt.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 6          # kør hver 6. time
_SALIENCE_THRESHOLD = 0.05  # entries under denne tærskel arkiveres
_MAX_PRUNE_PER_CYCLE = 50   # max entries at arkivere per kørsel

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_last_result: dict[str, object] = {}

# ---------------------------------------------------------------------------
# Daemon tick
# ---------------------------------------------------------------------------


def tick_memory_pruning_daemon() -> dict[str, object]:
    """Run pruning cycle if cadence elapsed. Returns stats dict."""
    global _last_tick_at, _last_result

    now = datetime.now(UTC)

    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
            return {"pruned": False}

    pruned_brain = 0
    pruned_private = 0

    # --- Layer 1: Brain entries ---
    try:
        pruned_brain = _prune_brain_entries(now)
    except Exception as exc:
        pass

    # --- Layer 2: Private brain records ---
    try:
        pruned_private = _prune_private_brain_records()
    except Exception as exc:
        pass

    total_pruned = pruned_brain + pruned_private
    _last_tick_at = now
    _last_result = {
        "pruned_brain_entries": pruned_brain,
        "pruned_private_records": pruned_private,
        "total_pruned": total_pruned,
    }

    if total_pruned > 0:
        try:
            event_bus.publish(
                "memory_pruning.cycle_completed",
                {
                    "pruned_brain_entries": pruned_brain,
                    "pruned_private_records": pruned_private,
                    "total_pruned": total_pruned,
                    "completed_at": now.isoformat(),
                },
            )
        except Exception:
            pass

    return {"pruned": True, **_last_result}


def _prune_brain_entries(now: datetime) -> int:
    """Find brain entries med effektiv salience under tærskel og arkivér dem."""
    from core.services.jarvis_brain import archive_entry, compute_effective_salience, \
        connect_index, read_entry, brain_dir, render_entry_markdown, _workspace_root

    conn = connect_index()
    try:
        rows = conn.execute(
            "SELECT id FROM brain_index WHERE status = 'active' "
            "ORDER BY salience_base ASC, last_used_at ASC "
            f"LIMIT {_MAX_PRUNE_PER_CYCLE}"
        ).fetchall()
    finally:
        conn.close()

    pruned = 0
    for (entry_id,) in rows:
        try:
            entry = read_entry(entry_id)
        except Exception:
            continue
        eff = compute_effective_salience(entry, now)
        if eff < _SALIENCE_THRESHOLD:
            try:
                archive_entry(entry_id, reason=f"automatic pruning (salience={eff:.3f})", now=now)
                pruned += 1
            except Exception:
                continue
    return pruned


def _prune_private_brain_records() -> int:
    """Find private_brain_records med salience under tærskel og arkivér dem."""
    from core.runtime.db import connect as db_connect, _ensure_private_brain_records_table

    conn = db_connect()
    try:
        _ensure_private_brain_records_table(conn)
        rows = conn.execute(
            "SELECT record_id FROM private_brain_records "
            "WHERE status = 'active' AND salience < ? "
            "ORDER BY salience ASC "
            f"LIMIT {_MAX_PRUNE_PER_CYCLE}",
            (_SALIENCE_THRESHOLD,),
        ).fetchall()
    finally:
        conn.close()

    pruned = 0
    for (record_id,) in rows:
        try:
            conn2 = db_connect()
            try:
                _ensure_private_brain_records_table(conn2)
                conn2.execute(
                    "UPDATE private_brain_records SET status = 'archived', updated_at = ? "
                    "WHERE record_id = ?",
                    (datetime.now(UTC).isoformat(), record_id),
                )
                conn2.commit()
            finally:
                conn2.close()
            pruned += 1
        except Exception:
            continue
    return pruned


# ---------------------------------------------------------------------------
# Surface for runtime awareness
# ---------------------------------------------------------------------------


def build_memory_pruning_surface() -> dict[str, object]:
    return {
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
        "last_result": _last_result,
    }
