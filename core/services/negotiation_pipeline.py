"""Negotiation Pipeline — interne trade-offs mellem sub-persporaer.

Når Jarvis står mellem forskellige interne "stemmer" (memory siger X,
critic siger Y, watcher alerter om Z), kan han "forhandle" mellem dem:

1. propose_trade(): generer et TradeOffer baseret på signal-mix
2. resolve_trade_offer(): afgør om tilbuddet accepteres baseret på
   intent_confidence + offer.requested_decision
3. record_trade_outcome(): registrér resultatet for læring over tid

Forskellen fra regret (bagud-kigget på fejl) og counterfactual (hvad
hvis): negotiation er FORKANT af beslutning — "hvilken indre stemme
skal jeg lytte til?"

Porteret fra jarvis-ai/agent/cognition/negotiation.py (2026-04-22).

v2-tilpasning: SQLite-persisteret i stedet for in-memory dict,
så outcomes overlever reboots og kan analyseres over tid.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class TradeOffer:
    offer_id: str
    run_id: str
    trace_id: str
    proposer: str
    counterparty: str
    requested_decision: str
    confidence: float
    rationale: str
    evidence: dict[str, int]
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence"] = dict(self.evidence)
        return d


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_trade_outcomes (
                outcome_id TEXT PRIMARY KEY,
                offer_id TEXT NOT NULL,
                proposer TEXT NOT NULL DEFAULT '',
                requested_decision TEXT NOT NULL DEFAULT '',
                accepted INTEGER NOT NULL DEFAULT 0,
                decision_applied TEXT NOT NULL DEFAULT '',
                run_status TEXT NOT NULL DEFAULT '',
                decision_reason TEXT NOT NULL DEFAULT '',
                offer_json TEXT NOT NULL DEFAULT '{}',
                resolution_json TEXT NOT NULL DEFAULT '{}',
                recorded_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_trade_outcomes_time "
            "ON cognitive_trade_outcomes(recorded_at DESC)"
        )
        conn.commit()


def _count_topics(signals: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"alerts": 0, "criticisms": 0, "memory_hints": 0}
    for item in signals or []:
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic") or "").strip()
        if topic in counts:
            counts[topic] += 1
    return counts


def propose_trade(
    *,
    run_id: str = "",
    trace_id: str = "",
    action: str = "",
    intent_confidence: float = 0.5,
    signals: list[dict[str, Any]] | None = None,
) -> TradeOffer | None:
    """Generate a TradeOffer from signal-mix. Returns None if no signals."""
    counts = _count_topics(signals or [])
    if sum(counts.values()) <= 0:
        return None

    proposer = "jarvis-memory"
    requested = "review_required"
    rationale = "ecosystem_consensus_requests_review"
    conf = 0.62

    if counts["alerts"] > 0:
        proposer = "jarvis-watcher"
        requested = "review_required"
        rationale = "anomaly_signal_detected"
        conf = min(0.98, 0.72 + (0.08 * counts["alerts"]))
    elif counts["criticisms"] > 0:
        proposer = "jarvis-critic"
        requested = "replan_required" if float(intent_confidence) < 0.75 else "review_required"
        rationale = "critic_risk_signal_detected"
        conf = min(0.95, 0.66 + (0.06 * counts["criticisms"]))
    elif counts["memory_hints"] > 0:
        proposer = "jarvis-memory"
        requested = "replan_required" if float(intent_confidence) < 0.45 else "review_required"
        rationale = "memory_pattern_signal_detected"
        conf = min(0.9, 0.58 + (0.04 * counts["memory_hints"]))

    return TradeOffer(
        offer_id=f"trade_{uuid4().hex[:12]}",
        run_id=str(run_id or "").strip(),
        trace_id=str(trace_id or "").strip(),
        proposer=proposer,
        counterparty="jarvis-core",
        requested_decision=requested,
        confidence=float(conf),
        rationale=f"{rationale}:{str(action or '').strip() or 'unknown_action'}",
        evidence=counts,
        created_at=_now_iso(),
    )


def resolve_trade_offer(*, offer: TradeOffer, intent_confidence: float) -> dict[str, Any]:
    """Decide whether to accept the offer based on intent_confidence."""
    requested = str(offer.requested_decision or "review_required").strip()
    conf = float(intent_confidence)
    accepted = False
    if requested == "replan_required":
        accepted = conf < 0.8
    elif requested == "review_required":
        accepted = conf < 0.9

    return {
        "offer_id": offer.offer_id,
        "accepted": bool(accepted),
        "decision_applied": requested if accepted else "valid",
        "resolver": "jarvis-core",
        "resolved_at": _now_iso(),
        "resolution_reason": (
            "accepted_due_to_signal_pressure" if accepted
            else "rejected_due_to_high_intent_confidence"
        ),
    }


def record_trade_outcome(
    *,
    offer: dict[str, Any],
    resolution: dict[str, Any],
    run_status: str = "",
    decision_reason: str = "",
) -> dict[str, Any]:
    _ensure_table()
    outcome_id = f"trade_outcome_{uuid4().hex[:10]}"
    event = {
        "outcome_id": outcome_id,
        "offer_id": str(offer.get("offer_id") or ""),
        "proposer": str(offer.get("proposer") or ""),
        "requested_decision": str(offer.get("requested_decision") or ""),
        "accepted": bool(resolution.get("accepted", False)),
        "decision_applied": str(resolution.get("decision_applied") or "valid"),
        "run_status": str(run_status or "").strip() or "unknown",
        "decision_reason": str(decision_reason or "").strip(),
        "recorded_at": _now_iso(),
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cognitive_trade_outcomes
                (outcome_id, offer_id, proposer, requested_decision, accepted,
                 decision_applied, run_status, decision_reason,
                 offer_json, resolution_json, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["outcome_id"], event["offer_id"], event["proposer"],
                event["requested_decision"],
                1 if event["accepted"] else 0,
                event["decision_applied"], event["run_status"],
                event["decision_reason"],
                json.dumps(offer, ensure_ascii=False),
                json.dumps(resolution, ensure_ascii=False),
                event["recorded_at"],
            ),
        )
        conn.commit()
    try:
        event_bus.publish("cognitive_trade.outcome_recorded", {
            "outcome_id": outcome_id, "accepted": event["accepted"],
        })
    except Exception:
        pass
    return event


def list_recent_trade_outcomes(*, limit: int = 20) -> list[dict[str, Any]]:
    _ensure_table()
    lim = max(1, min(int(limit or 20), 200))
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_trade_outcomes ORDER BY recorded_at DESC LIMIT ?",
            (lim,),
        ).fetchall()
    return [dict(r) for r in rows]


def build_negotiation_surface() -> dict[str, Any]:
    outcomes = list_recent_trade_outcomes(limit=20)
    active = bool(outcomes)
    if not outcomes:
        return {"active": False, "summary": "No trade outcomes yet", "recent": []}
    accepted = sum(1 for o in outcomes if o.get("accepted"))
    rejected = len(outcomes) - accepted
    summary = f"{len(outcomes)} trade outcomes ({accepted} accepted, {rejected} rejected)"
    return {
        "active": active,
        "summary": summary,
        "accepted_count": accepted,
        "rejected_count": rejected,
        "recent": outcomes,
    }
