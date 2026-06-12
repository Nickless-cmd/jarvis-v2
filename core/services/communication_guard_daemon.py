"""Communication guard daemon — vedligeholder TTL-rydning.

Kører hvert heartbeat (60s). To opgaver:
  1. Rens udløbne TTL-triggers (cleanup_expired)
  2. Log antal aktive triggers til eventbus (observability)

Hvis der er aktive triggers, tilføjes en kort reminder til prompt_contract
via communication_guard_prompt_section().
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def tick_communication_guard_daemon() -> dict[str, Any]:
    """Daemon tick: cleanup expired TTL triggers + log active count."""
    try:
        from core.services.communication_guard import cleanup_expired, active_count
    except ImportError as exc:
        logger.error("comm_guard: import failed: %s", exc)
        return {"status": "error", "error": f"import failed: {exc}"}

    try:
        removed = cleanup_expired()
        count = active_count()
        if removed:
            logger.info("comm_guard: removed %d expired TTL trigger(s)", removed)
        return {
            "status": "ok",
            "active_triggers": count,
            "expired_removed": removed,
        }
    except Exception as exc:
        logger.error("comm_guard: tick failed: %s", exc)
        return {"status": "error", "error": str(exc)}


tick = tick_communication_guard_daemon
