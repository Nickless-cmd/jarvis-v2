"""Selective Consolidation Daemon — D1.

Kører hver 24 timer. Scorer dagens records (sensory memories, brain entries,
private brain records) med simple kvalitetsheuristikker og arkiverer
bund-(100-K)% så kun top-K% når long-term storage.

Dette er "kvalitet før kvantitet" — i stedet for at gemme alt og prunen
senere (som memory_pruning_daemon gør med salience-threshold), sorterer
vi FØR langtidslagring.

Konfiguration:
  - TOP_K_PERCENT (default 50): hvor mange % af dagens records der beholdes
  - MIN_CONTENT_LENGTH (default 20): minimum content-længde for at få score > 0

Scoring (0.0-1.0):
  - Sensory: content_length/500 (capped) + 0.2 hvis mood_tone findes
  - Brain entries: salience_base (0-1) + content_length/500 (capped)
  - Private records: salience (0-1) + content_length/500 (capped)
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────

_CADENCE_HOURS = 24
_TOP_K_PERCENT = 50          # behold top 50%
_MIN_CONTENT_LENGTH = 20     # kortere content får score = 0
_MAX_CONTENT_FACTOR = 500    # maks content-længde der giver bonus

# ── Module-level state ──────────────────────────────────────────────

_last_tick_at: datetime | None = None


def tick_selective_consolidation_daemon() -> dict[str, Any]:
    """Run selective consolidation if cadence elapsed.

    Scores today's records across all memory stores and archives
    the bottom (100-K)%.
    """
    global _last_tick_at

    now = datetime.now(UTC)
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
            return {"consolidated": False, "reason": "cadence_not_reached"}

    today_start = now.strftime("%Y-%m-%dT00:00:00")
    results: dict[str, Any] = {"consolidated": True, "layers": []}

    # ── Layer 1: Sensory memories ────────────────────────────────
    try:
        sensory = _consolidate_sensory(today_start)
        results["layers"].append(sensory)
    except Exception as exc:
        logger.warning("selective_consolidation: sensory layer failed: %s", exc)
        results["layers"].append({"layer": "sensory", "error": str(exc)})

    # ── Layer 2: Brain entries ────────────────────────────────────
    try:
        brain = _consolidate_brain(today_start)
        results["layers"].append(brain)
    except Exception as exc:
        logger.warning("selective_consolidation: brain layer failed: %s", exc)
        results["layers"].append({"layer": "brain", "error": str(exc)})

    # ── Layer 3: Private brain records ────────────────────────────
    try:
        private = _consolidate_private(today_start)
        results["layers"].append(private)
    except Exception as exc:
        logger.warning("selective_consolidation: private layer failed: %s", exc)
        results["layers"].append({"layer": "private", "error": str(exc)})

    total_archived = sum(
        l.get("archived", 0) for l in results["layers"] if "archived" in l
    )
    total_scored = sum(
        l.get("scored", 0) for l in results["layers"] if "scored" in l
    )
    results["total_scored"] = total_scored
    results["total_archived"] = total_archived

    _last_tick_at = now

    if total_archived > 0:
        try:
            event_bus.publish("selective_consolidation.completed", {
                "total_scored": total_scored,
                "total_archived": total_archived,
                "completed_at": now.isoformat(),
            })
        except Exception:
            pass

    return results


# ── Layer 1: Sensory memories ────────────────────────────────────────


def _score_sensory(row: dict[str, Any]) -> float:
    """Score a sensory memory 0.0-1.0."""
    content = row.get("content") or ""
    content_len = len(content.strip())
    if content_len < _MIN_CONTENT_LENGTH:
        return 0.0
    score = min(content_len / _MAX_CONTENT_FACTOR, 0.8)
    if row.get("mood_tone"):
        score += 0.2
    return min(score, 1.0)


def _consolidate_sensory(today_start: str) -> dict[str, Any]:
    """Score and archive bottom (100-K)% of today's sensory memories."""
    from core.runtime.db_sensory import _ensure_sensory_memories_table
    from core.runtime.db import connect

    with connect() as conn:
        _ensure_sensory_memories_table(conn)
        rows = conn.execute(
            "SELECT id, timestamp, modality, content, mood_tone FROM sensory_memories "
            "WHERE timestamp >= ? ORDER BY timestamp ASC",
            (today_start,),
        ).fetchall()

    if not rows:
        return {"layer": "sensory", "scored": 0, "archived": 0}

    scored = []
    for r in rows:
        d = dict(r)
        d["_score"] = _score_sensory(d)
        scored.append(d)

    scored.sort(key=lambda x: x["_score"])
    keep_count = max(1, round(len(scored) * _TOP_K_PERCENT / 100))
    archive_targets = scored[:-keep_count] if keep_count < len(scored) else []

    if not archive_targets:
        return {"layer": "sensory", "scored": len(scored), "archived": 0}

    # Mark for deletion: we can't "archive" sensory memories (no status column),
    # so we delete them outright. Low-quality sensory noise has no recall value.
    ids_to_delete = [s["id"] for s in archive_targets]
    with connect() as conn:
        _ensure_sensory_memories_table(conn)
        for mid in ids_to_delete:
            conn.execute("DELETE FROM sensory_memories WHERE id = ?", (mid,))
        conn.commit()

    return {
        "layer": "sensory",
        "scored": len(scored),
        "archived": len(archive_targets),
        "threshold": scored[-keep_count]["_score"] if keep_count <= len(scored) else 0,
    }


# ── Layer 2: Brain entries ──────────────────────────────────────────


def _score_brain(entry: dict[str, Any]) -> float:
    """Score a brain entry 0.0-1.0."""
    content = entry.get("content") or entry.get("summary") or ""
    content_len = len(content.strip())
    if content_len < _MIN_CONTENT_LENGTH:
        return 0.0
    salience = float(entry.get("salience_base") or 0.0)
    content_score = min(content_len / _MAX_CONTENT_FACTOR, 0.5)
    return min(salience + content_score, 1.0)


def _consolidate_brain(today_start: str) -> dict[str, Any]:
    """Score and archive bottom (100-K)% of today's brain entries."""
    try:
        from core.services.jarvis_brain import (
            connect_index, archive_entry, read_entry,
        )
    except Exception:
        return {"layer": "brain", "scored": 0, "archived": 0, "error": "jarvis_brain not available"}

    conn = connect_index()
    try:
        rows = conn.execute(
            "SELECT id FROM brain_index WHERE status = 'active' AND created_at >= ?",
            (today_start,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"layer": "brain", "scored": 0, "archived": 0}

    scored: list[dict[str, Any]] = []
    for (entry_id,) in rows:
        try:
            entry = read_entry(entry_id)
            if entry:
                entry["_score"] = _score_brain(entry)
                scored.append(entry)
        except Exception:
            continue

    if not scored:
        return {"layer": "brain", "scored": 0, "archived": 0}

    scored.sort(key=lambda x: x["_score"])
    keep_count = max(1, round(len(scored) * _TOP_K_PERCENT / 100))
    archive_targets = scored[:-keep_count] if keep_count < len(scored) else []

    archived = 0
    for entry in archive_targets:
        try:
            archive_entry(
                entry.get("id", entry.get("entry_id", "")),
                reason=f"selective consolidation: score={entry['_score']:.2f}",
            )
            archived += 1
        except Exception:
            continue

    return {
        "layer": "brain",
        "scored": len(scored),
        "archived": archived,
        "threshold": scored[-keep_count]["_score"] if keep_count <= len(scored) else 0,
    }


# ── Layer 3: Private brain records ──────────────────────────────────


def _score_private(record: dict[str, Any]) -> float:
    """Score a private brain record 0.0-1.0."""
    content = record.get("detail") or record.get("summary") or ""
    content_len = len(content.strip())
    if content_len < _MIN_CONTENT_LENGTH:
        return 0.0
    salience = float(record.get("salience") or 0.0)
    content_score = min(content_len / _MAX_CONTENT_FACTOR, 0.5)
    return min(salience + content_score, 1.0)


def _consolidate_private(today_start: str) -> dict[str, Any]:
    """Score and archive bottom (100-K)% of today's private brain records."""
    from core.runtime.db import (
        connect,
        _ensure_private_brain_records_table,
    )

    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        rows = conn.execute(
            "SELECT record_id, detail, summary, salience, record_type "
            "FROM private_brain_records "
            "WHERE status = 'active' AND created_at >= ? ORDER BY created_at ASC",
            (today_start,),
        ).fetchall()

    if not rows:
        return {"layer": "private", "scored": 0, "archived": 0}

    scored = []
    for r in rows:
        d = dict(r)
        d["_score"] = _score_private(d)
        scored.append(d)

    scored.sort(key=lambda x: x["_score"])
    keep_count = max(1, round(len(scored) * _TOP_K_PERCENT / 100))
    archive_targets = scored[:-keep_count] if keep_count < len(scored) else []

    if not archive_targets:
        return {"layer": "private", "scored": len(scored), "archived": 0}

    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_private_brain_records_table(conn)
        for rec in archive_targets:
            conn.execute(
                "UPDATE private_brain_records SET status = 'archived', "
                "updated_at = ? WHERE record_id = ?",
                (now_iso, rec["record_id"]),
            )
        conn.commit()

    return {
        "layer": "private",
        "scored": len(scored),
        "archived": len(archive_targets),
        "threshold": scored[-keep_count]["_score"] if keep_count <= len(scored) else 0,
    }


# ── Surface ─────────────────────────────────────────────────────────


def build_selective_consolidation_surface() -> dict[str, Any]:
    """Build surface data for mission control."""
    return {
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else None,
        "cadence_hours": _CADENCE_HOURS,
        "top_k_percent": _TOP_K_PERCENT,
    }


# Alias for heartbeat_runtime import convention
tick = tick_selective_consolidation_daemon
