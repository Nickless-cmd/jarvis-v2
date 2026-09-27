"""Reconcile balancer cooldowns with successful calls from the shared cheap lane."""
from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def reconcile_successes(states: dict[str, Any], now_epoch: float) -> bool:
    """A later successful invocation proves a profile's old failure has healed."""
    pending = {
        slot_id: state for slot_id, state in states.items()
        if not state.manually_disabled and state.last_failure_at
        and (state.cooldown_until and state.cooldown_until > now_epoch
             or state.breaker_level > 0 or state.consecutive_failures >= 3)
    }
    if not pending:
        return False

    from core.runtime.db_core import connect

    since = datetime.fromtimestamp(
        min(float(state.last_failure_at) for state in pending.values()), UTC,
    ).isoformat().replace("+00:00", "Z")
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT provider, model, "
                "COALESCE(NULLIF(auth_profile, ''), 'default') AS profile, "
                "MAX(created_at) AS completed_at "
                "FROM cheap_provider_invocations "
                "WHERE lane = 'cheap' AND status = 'completed' AND created_at >= ? "
                "GROUP BY provider, model, profile",
                (since,),
            ).fetchall()
    except (sqlite3.DatabaseError, OSError) as exc:
        logger.warning("cheap-lane success reconciliation unavailable: %s", exc)
        return False

    changed = False
    for row in rows:
        slot_id = f"{row['provider']}::{row['model']}::{row['profile']}"
        state = pending.get(slot_id)
        if state is None:
            continue
        try:
            completed_at = datetime.fromisoformat(
                str(row["completed_at"]).replace("Z", "+00:00")
            ).timestamp()
        except ValueError:  # Malformed optional telemetry must not affect routing.
            continue
        if completed_at <= max(float(state.last_failure_at or 0),
                               float(state.last_success_at or 0)):
            continue
        state.last_success_at = completed_at
        state.consecutive_failures = 0
        state.cooldown_until = None
        state.cooldown_reason = ""
        state.breaker_level = max(0, state.breaker_level - 1)
        changed = True
    return changed
