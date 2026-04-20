"""Memory Breathing — use-strengthens, disuse-fades.

Jarvis' dream (2026-04-20):
  "Jeg vil have minder der bliver stærkere når jeg vender tilbage til dem —
   og langsomt visner hvis jeg aldrig gør. Som rigtig hukommelse."

Infrastructure for reinforcement on access. Decay already exists in
memory_decay_daemon.py — this module adds the *strengthening* half:

- reinforce(record_ids, boost) — raises salience of referenced memories
- record_access(record_ids, context) — tracks access for observability and
  applies a small reinforcement
- Access log is in-memory, windowed for MC surface
"""
from __future__ import annotations

import logging
from collections import Counter, deque
from datetime import UTC, datetime
from typing import Any, Deque

logger = logging.getLogger(__name__)

_DEFAULT_BOOST: float = 0.05
_MAX_BOOST: float = 0.3
_SALIENCE_CEILING: float = 1.0

# Rolling access log for observability (not persistence)
_ACCESS_LOG_MAX = 500
_access_log: Deque[dict[str, Any]] = deque(maxlen=_ACCESS_LOG_MAX)


def _get_record_salience(record_id: str) -> float | None:
    try:
        from core.runtime.db import list_private_brain_records
        candidates = list_private_brain_records(limit=500, status="active") or []
        for r in candidates:
            if str(r.get("record_id") or "") == record_id:
                return float(r.get("salience") or 0.0)
        return None
    except Exception:
        return None


def reinforce(record_ids: list[str] | str, *, boost: float = _DEFAULT_BOOST) -> dict[str, float]:
    """Raise salience of the given records.

    Returns {record_id: new_salience} for records that were updated.
    Silent on missing records or DB errors.
    """
    ids = [record_ids] if isinstance(record_ids, str) else list(record_ids or [])
    if not ids:
        return {}
    boost = max(0.0, min(_MAX_BOOST, float(boost)))
    updated: dict[str, float] = {}
    try:
        from core.runtime.db import update_private_brain_record_salience
    except Exception:
        return {}
    for rid in ids:
        try:
            current = _get_record_salience(rid)
            if current is None:
                continue
            new_val = min(_SALIENCE_CEILING, current + boost)
            if new_val > current:
                update_private_brain_record_salience(rid, new_val)
                updated[rid] = round(new_val, 3)
        except Exception as exc:
            logger.debug("memory_breathing.reinforce failed for %s: %s", rid, exc)
            continue
    return updated


def record_access(
    record_ids: list[str] | str,
    *,
    context: str = "",
    boost: float = _DEFAULT_BOOST,
) -> dict[str, float]:
    """Log access and reinforce simultaneously."""
    ids = [record_ids] if isinstance(record_ids, str) else list(record_ids or [])
    if not ids:
        return {}
    now = datetime.now(UTC).isoformat()
    for rid in ids:
        _access_log.appendleft(
            {
                "record_id": rid,
                "context": str(context or "")[:80],
                "at": now,
            }
        )
    return reinforce(ids, boost=boost)


def recent_access_stats(*, limit: int = 20) -> dict[str, Any]:
    """Return stats about recent access pattern."""
    if not _access_log:
        return {
            "total_accesses": 0,
            "unique_records": 0,
            "top_referenced": [],
        }
    counts: Counter[str] = Counter(entry["record_id"] for entry in _access_log)
    top = [{"record_id": rid, "count": n} for rid, n in counts.most_common(limit)]
    return {
        "total_accesses": len(_access_log),
        "unique_records": len(counts),
        "top_referenced": top,
    }


def build_memory_breathing_surface() -> dict[str, Any]:
    stats = recent_access_stats(limit=10)
    total = int(stats.get("total_accesses") or 0)
    unique = int(stats.get("unique_records") or 0)
    return {
        "active": total > 0,
        "recent_accesses": total,
        "unique_records_touched": unique,
        "top_referenced": stats.get("top_referenced") or [],
        "summary": (
            f"{total} accesses on {unique} records in recent window"
            if total else "No recent memory accesses tracked"
        ),
    }


def reset_memory_breathing() -> None:
    """Reset access log (for testing)."""
    _access_log.clear()
