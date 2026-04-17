"""Negotiation Engine — internal trade offers between subsystems.

When different cognitive signals disagree, the negotiation engine
proposes trades: "Give up speed for quality" or "Accept risk for progress".
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_TRADE_LOCK = threading.Lock()
_TRADE_HISTORY: list[dict[str, object]] = []


def propose_trade(
    *,
    proposer: str,
    counterparty: str,
    requested_decision: str,
    confidence: float,
    rationale: str,
    evidence: dict[str, int] | None = None,
) -> dict[str, object]:
    """Propose an internal trade between subsystems."""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    trade = {
        "trade_id": f"trade-{uuid4().hex[:8]}",
        "proposer": proposer,
        "counterparty": counterparty,
        "requested_decision": requested_decision,
        "confidence": round(min(1.0, max(0.0, confidence)), 2),
        "rationale": rationale[:200],
        "evidence": evidence or {},
        "status": "proposed",
        "created_at": now,
    }

    with _TRADE_LOCK:
        _TRADE_HISTORY.append(trade)
        if len(_TRADE_HISTORY) > 50:
            _TRADE_HISTORY.pop(0)

    event_bus.publish(
        "cognitive_negotiation.trade_proposed",
        {"trade_id": trade["trade_id"], "proposer": proposer},
    )
    return trade


def build_negotiation_surface() -> dict[str, object]:
    with _TRADE_LOCK:
        recent = list(_TRADE_HISTORY[-10:])
    return {
        "active": bool(recent),
        "recent_trades": recent,
        "total_count": len(_TRADE_HISTORY),
        "summary": (
            f"{len(recent)} recent trades"
            if recent else "No negotiations yet"
        ),
    }
