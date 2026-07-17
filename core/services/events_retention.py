"""Events-table retention — bound the unbounded ``events`` telemetry table.

The eventbus persists every event to ``events`` with no retention. Left alone it
grows without limit (measured 2.56M rows / ~4 months / 2.7GB DB, ~211k rows/day
under the cheap-lane churn). A large table means slower INSERTs (deeper index) →
longer WAL write-lock holds → more contention with API chat/cost writes (the
amplifier behind API latency spikes, alongside per-event commits which the writer
now batches).

``prune_old_events`` deletes rows older than a cutoff in SMALL batches (one commit
per batch → never a long lock), capped per invocation so the initial drain of a
huge table happens gradually across ticks rather than in one table-locking sweep.
Self-safe: never raises.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

_DEFAULT_MAX_AGE_DAYS = 14
_DEFAULT_MAX_DELETE = 50_000   # per invocation — gradual drain of a huge backlog
_DEFAULT_BATCH_SIZE = 5_000    # rows per transaction — short lock holds


def _retention_days() -> int:
    try:
        from core.runtime.settings import load_settings
        v = int(load_settings().extra.get("events_retention_days", _DEFAULT_MAX_AGE_DAYS))
        return max(1, v)
    except Exception:
        return _DEFAULT_MAX_AGE_DAYS


def prune_old_events(
    *,
    max_age_days: int | None = None,
    max_delete: int = _DEFAULT_MAX_DELETE,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    """Delete events older than ``max_age_days`` in batches. Returns {"deleted": N}.

    Batched (one commit per ``batch_size`` rows) so no single long lock; capped at
    ``max_delete`` per call so a huge backlog drains gradually. Self-safe."""
    days = int(max_age_days) if max_age_days is not None else _retention_days()
    cutoff = (datetime.now(UTC) - timedelta(days=max(1, days))).isoformat()
    total = 0
    try:
        from core.runtime.db import connect
        while total < max_delete:
            take = min(batch_size, max_delete - total)
            with connect() as conn:
                cur = conn.execute(
                    "DELETE FROM events WHERE id IN "
                    "(SELECT id FROM events WHERE created_at < ? ORDER BY id ASC LIMIT ?)",
                    (cutoff, take),
                )
                n = cur.rowcount or 0
                conn.commit()
            if n <= 0:
                break
            total += n
    except Exception as exc:
        return {"deleted": total, "error": str(exc)[:200], "cutoff": cutoff}
    return {"deleted": total, "cutoff": cutoff, "retention_days": days}
