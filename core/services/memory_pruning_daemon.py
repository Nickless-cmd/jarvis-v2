"""Memory pruning daemon — arkiverer entries med meget lav salience.

Kører hver 6. time. Scanner to lag:
  1. Brain entries med effektiv salience < tærskel (0.05)
  2. Private brain records med salience < tærskel (0.05)

Begge arkiveres (status → 'archived') så de ikke længere fylder i
aktiv søgning, men stadig kan genses via read_brain_entry / cold tier.

Dette er "glemsel som feature" — at glemme er at prioritere.
Uden denne daemon akkumulerer jeg al støj for evigt.

Polish 2026-05-08 (Claude review):
  - logger.warning på alle except-grene (var silent)
  - private records: én transaction for alle UPDATEs (var N+1 conns)
  - brain candidate-pull: hent flere kandidater og sortér på effektiv
    salience computed in-memory, så vi ikke skipper highly-decayed
    high-base entries (var ORDER BY salience_base — blind plet)
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 6          # kør hver 6. time
_SALIENCE_THRESHOLD = 0.05  # entries under denne tærskel arkiveres
_MAX_PRUNE_PER_CYCLE = 50   # max entries at arkivere per kørsel
# Vi henter flere kandidater end vi pruner — så vi har en realistisk
# chance for at finde de FAKTISK lavt-effektive entries (ikke kun dem
# med lav base). Forholdet 4x = solid headroom uden at scanne hele DB.
_BRAIN_CANDIDATE_FACTOR = 4

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
        logger.warning("memory_pruning: brain layer failed: %s", exc, exc_info=True)

    # --- Layer 2: Private brain records ---
    try:
        pruned_private = _prune_private_brain_records()
    except Exception as exc:
        logger.warning("memory_pruning: private layer failed: %s", exc, exc_info=True)

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
        except Exception as exc:
            logger.debug("memory_pruning: event publish failed: %s", exc)

    return {"pruned": True, **_last_result}


def _prune_brain_entries(now: datetime) -> int:
    """Find brain entries med effektiv salience under tærskel og arkivér dem.

    Henter en bredere kandidat-pool (4x cap) og scorer EFFEKTIV salience
    i Python-laget, ikke base-salience i SQL. Det undgår blind plet hvor
    high-base + højt decay entries slipper under threshold uden at blive
    set af pruning.
    """
    from core.services.jarvis_brain import (
        archive_entry,
        compute_effective_salience,
        connect_index,
        read_entry,
    )

    candidate_limit = _MAX_PRUNE_PER_CYCLE * _BRAIN_CANDIDATE_FACTOR
    conn = connect_index()
    try:
        # Sortér efter (last_used_at ASC, salience_base ASC) — last_used
        # er stærkere proxy for "decayed" end base alene. Stadig en
        # heuristik, men favoriserer det vi faktisk vil pruning'e.
        rows = conn.execute(
            "SELECT id FROM brain_index WHERE status = 'active' "
            "ORDER BY last_used_at ASC NULLS FIRST, salience_base ASC "
            f"LIMIT {candidate_limit}"
        ).fetchall()
    finally:
        conn.close()

    pruned = 0
    for (entry_id,) in rows:
        if pruned >= _MAX_PRUNE_PER_CYCLE:
            break
        try:
            entry = read_entry(entry_id)
        except Exception as exc:
            logger.warning(
                "memory_pruning: read_entry failed for %s: %s", entry_id, exc
            )
            continue
        eff = compute_effective_salience(entry, now)
        if eff < _SALIENCE_THRESHOLD:
            try:
                archive_entry(
                    entry_id,
                    reason=f"automatic pruning (salience={eff:.3f})",
                    now=now,
                )
                pruned += 1
            except Exception as exc:
                logger.warning(
                    "memory_pruning: archive_entry failed for %s: %s",
                    entry_id, exc,
                )
                continue
    return pruned


def _prune_private_brain_records() -> int:
    """Find private_brain_records med salience under tærskel og arkivér dem.

    Bruger ÉN database-connection for hele cyklus (var N+1 conns før
    polish 2026-05-08).
    """
    from core.runtime.db import (
        _ensure_private_brain_records_table,
        connect as db_connect,
    )

    pruned = 0
    now_iso = datetime.now(UTC).isoformat()
    with db_connect() as conn:
        _ensure_private_brain_records_table(conn)
        rows = conn.execute(
            "SELECT record_id FROM private_brain_records "
            "WHERE status = 'active' AND salience < ? "
            "ORDER BY salience ASC "
            f"LIMIT {_MAX_PRUNE_PER_CYCLE}",
            (_SALIENCE_THRESHOLD,),
        ).fetchall()
        for (record_id,) in rows:
            try:
                conn.execute(
                    "UPDATE private_brain_records SET status = 'archived', "
                    "updated_at = ? WHERE record_id = ?",
                    (now_iso, record_id),
                )
                pruned += 1
            except Exception as exc:
                logger.warning(
                    "memory_pruning: private archive failed for %s: %s",
                    record_id, exc,
                )
                continue
        # Single commit covers all rows (atomic per cycle).
        conn.commit()
    return pruned


# ---------------------------------------------------------------------------
# Surface for runtime awareness
# ---------------------------------------------------------------------------


def build_memory_pruning_surface() -> dict[str, object]:
    return {
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
        "last_result": _last_result,
    }
