"""Causal alerts — surface failure-event chains in the prompt.

Scanner sidste LOOKBACK_MINUTES for kritiske failure-events og injecter
top-1 kausal-kæde for hver. Cap'er max 2 chains pr. tur så det ikke
fylder prompten.

Kører som awareness-item (priority 30) i prompt_contract.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from core.runtime.db import connect

logger = logging.getLogger(__name__)

# Tunable. Senere kan vi skifte til events_since_last_tick i stedet
# for et fast tidsvindue (per spec note §7.2).
LOOKBACK_MINUTES = 30

_FAILURE_KINDS = (
    "tool.error",
    "behavioral_decision_review.broken",
    "runtime.cheap_lane_provider_failed",
    "identity.drift_detected",
    "executive_contradiction.detected",
)

_MAX_CHAINS_PER_TURN = 2
_CHAIN_DEPTH = 3
_MIN_CONFIDENCE = 0.7


def _fetch_recent_failures(limit: int) -> list[dict]:
    cutoff = (datetime.now(UTC) - timedelta(minutes=LOOKBACK_MINUTES)).isoformat()
    placeholders = ",".join("?" * len(_FAILURE_KINDS))
    with connect() as c:
        rows = c.execute(
            f"SELECT id, kind, payload_json, created_at FROM events "
            f"WHERE kind IN ({placeholders}) AND created_at >= ? "
            f"ORDER BY id DESC LIMIT ?",
            (*list(_FAILURE_KINDS), cutoff, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _format_chain_for_failure(failure_event: dict) -> str:
    from core.services.causal_graph import query_causal_chain
    chain = query_causal_chain(
        event_id=int(failure_event["id"]),
        direction="backward",
        max_depth=_CHAIN_DEPTH,
        min_confidence=_MIN_CONFIDENCE,
    )
    root_kind = str(failure_event["kind"])
    root_ts = str(failure_event.get("created_at", ""))[:19]
    if not chain["chain"]:
        return (
            f"🔗 Kausalkæde — recent failure:\n"
            f"  ROOT: {root_kind} ({root_ts}) <ingen edges fundet>"
        )
    lines = ["🔗 Kausalkæde — recent failure:"]
    lines.append(f"  ROOT: {root_kind} ({root_ts})")
    for step in chain["chain"]:
        ev = step["event"]
        ts = str(ev.get("created_at", ""))[:19]
        lines.append(f"    ↳ {ev['kind']} ({ts})")
    return "\n".join(lines)


def causal_alerts_section() -> str:
    """Build the causal-alerts awareness section. Returns "" if no alerts."""
    try:
        failures = _fetch_recent_failures(limit=_MAX_CHAINS_PER_TURN)
    except Exception as exc:
        logger.debug("causal_alerts: fetch failed: %s", exc)
        return ""
    if not failures:
        return ""
    chunks: list[str] = []
    for fail in failures:
        try:
            chunks.append(_format_chain_for_failure(fail))
        except Exception as exc:
            logger.debug("causal_alerts: format failed: %s", exc)
            continue
    return "\n\n".join(chunks)
