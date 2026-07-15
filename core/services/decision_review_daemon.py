"""Decision review daemon — closes the adherence loop automatically.

Runs every 6 hours (360 min) via heartbeat. On each tick, it calls
`review_pending_decisions()` from `decision_review_prompter.py` which:

  1. Fetches all active behavioral_decisions
  2. Skips any reviewed within the last 24 hours
  3. Runs an LLM-based self-review (quality lane, deepseek-v4-flash)
  4. Persists the verdict (kept/partial/broken) + evidence to the DB
  5. Updates adherence_score on the decision

The daemon is pure read-then-write — it never creates or deletes decisions.
Max 5 decisions reviewed per tick to avoid burst load on the LLM provider.

Edge cases:
  - No active decisions: returns reviewed=0, skipped=0, failed=0
  - LLM failure: increments failed count, moves to next decision
  - Parsing failure: increments failed count, moves to next decision
  - DB write failure: increments failed count, moves to next decision
  - All decisions recently reviewed: returns reviewed=0, skipped=N
  - >5 overdue decisions: only reviews first 5, rest wait for next tick
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Max decisions to review per tick — prevents burst load on LLM provider.
_MAX_REVIEW_PER_TICK = 5


def tick_decision_review_daemon() -> dict[str, Any]:
    """Daemon tick: review overdue behavioral decisions.

    Called by heartbeat_runtime every 360 min (configurable via daemon_manager).
    Delegates to decision_review_prompter.review_pending_decisions() with a
    per-tick cap of _MAX_REVIEW_PER_TICK.

    Returns a dict with counts for observability:
      {"status": "ok", "considered": N, "reviewed": N, "skipped_recent": N, "failed": N}
    """
    try:
        from core.services.decision_review_prompter import review_pending_decisions
    except ImportError as exc:
        logger.error("decision_review: import failed: %s", exc)
        return {"status": "error", "error": f"import failed: {exc}"}

    try:
        result = review_pending_decisions(max_reviews=_MAX_REVIEW_PER_TICK)
        if not isinstance(result, dict):
            return {"status": "error", "error": f"unexpected return type: {type(result)}"}
        return result
    except Exception as exc:
        logger.error("decision_review: tick failed: %s", exc)
        return {"status": "error", "error": str(exc)}


# Alias for consistent daemon import pattern:
#   from core.services.decision_review_daemon import tick
tick = tick_decision_review_daemon
