"""Meta-læring aggregator — Phase 1 (AGI track #3).

Read-only queries på de 5 AGI-spor til ugentlig retrospektiv.
Hver funktion returnerer aggregat-stats + 1-2 ekstreme samples.

See spec: docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _in_window(ts_iso: str, since: datetime, until: datetime) -> bool:
    """Defensive: parse ts and check if it's within [since, until]."""
    if not ts_iso:
        return False
    try:
        ts = datetime.fromisoformat(ts_iso)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return False
    return since <= ts <= until


def _bucket_confidence(c: float) -> str:
    if c >= 0.7:
        return "high"
    if c >= 0.4:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# World model
# ---------------------------------------------------------------------------

def aggregate_world_model(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate world-model prediction activity in [since, until]."""
    from core.services.world_model_signal_tracking import _load_predictions

    try:
        all_predictions = _load_predictions()
    except Exception as exc:
        logger.warning("aggregate_world_model: load failed: %s", exc)
        all_predictions = []

    in_window = [
        p for p in all_predictions
        if _in_window(str(p.get("created_at") or ""), since, until)
    ]

    resolved = [p for p in in_window if p.get("outcome")]
    outcome_dist = {"supported": 0, "contradicted": 0, "uncertain": 0}
    for p in resolved:
        outcome = str(p.get("outcome") or "").strip()
        if outcome in outcome_dist:
            outcome_dist[outcome] += 1

    confidence_buckets = {"high": 0, "medium": 0, "low": 0}
    for p in in_window:
        try:
            c = float(p.get("confidence") or 0.0)
            confidence_buckets[_bucket_confidence(c)] += 1
        except (TypeError, ValueError):
            pass

    extreme_samples: list[dict[str, Any]] = []

    contradicted = [p for p in resolved if p.get("outcome") == "contradicted"]
    if contradicted:
        top = max(contradicted, key=lambda p: float(p.get("confidence") or 0))
        extreme_samples.append({
            "role": "highest_confidence_contradicted",
            "id": str(top.get("id") or ""),
            "data": {
                "subject": str(top.get("subject") or ""),
                "expectation": str(top.get("expectation") or ""),
                "confidence": float(top.get("confidence") or 0),
                "created_at": str(top.get("created_at") or ""),
                "resolved_at": str(top.get("resolved_at") or ""),
            },
        })

    supported = [p for p in resolved if p.get("outcome") == "supported"]
    if supported:
        low = min(supported, key=lambda p: float(p.get("confidence") or 1))
        extreme_samples.append({
            "role": "lowest_confidence_supported",
            "id": str(low.get("id") or ""),
            "data": {
                "subject": str(low.get("subject") or ""),
                "expectation": str(low.get("expectation") or ""),
                "confidence": float(low.get("confidence") or 0),
                "created_at": str(low.get("created_at") or ""),
                "resolved_at": str(low.get("resolved_at") or ""),
            },
        })

    return {
        "predictions_made": len(in_window),
        "predictions_resolved": len(resolved),
        "outcome_distribution": outcome_dist,
        "confidence_buckets": confidence_buckets,
        "extreme_samples": extreme_samples,
    }


# ---------------------------------------------------------------------------
# Plan revision
# ---------------------------------------------------------------------------

def _completion_seconds(rec: dict[str, Any]) -> float | None:
    """Seconds between created_at and updated_at; None if either missing."""
    try:
        c = datetime.fromisoformat(str(rec.get("created_at") or ""))
        u = datetime.fromisoformat(str(rec.get("updated_at") or ""))
        if c.tzinfo is None:
            c = c.replace(tzinfo=UTC)
        if u.tzinfo is None:
            u = u.replace(tzinfo=UTC)
        return (u - c).total_seconds()
    except (ValueError, TypeError):
        return None


def aggregate_plan_revision(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate plan-proposal activity in [since, until]."""
    from core.services.plan_proposals import _load_all

    try:
        all_plans = _load_all()
    except Exception as exc:
        logger.warning("aggregate_plan_revision: load failed: %s", exc)
        all_plans = {}

    in_window = [
        rec for rec in all_plans.values()
        if _in_window(str(rec.get("created_at") or ""), since, until)
    ]

    status_dist = {
        "awaiting_approval": 0, "approved": 0, "completed": 0,
        "dismissed": 0, "superseded": 0,
    }
    for rec in in_window:
        s = str(rec.get("status") or "")
        if s in status_dist:
            status_dist[s] += 1

    extreme_samples: list[dict[str, Any]] = []

    superseded = [r for r in in_window if r.get("status") == "superseded"]
    superseded_with_delta = [
        (r, _completion_seconds(r)) for r in superseded
    ]
    superseded_with_delta = [(r, d) for (r, d) in superseded_with_delta if d is not None]
    if superseded_with_delta:
        fastest, delta = min(superseded_with_delta, key=lambda pair: pair[1])
        extreme_samples.append({
            "role": "fastest_superseded",
            "id": str(fastest.get("plan_id") or ""),
            "data": {
                "title": str(fastest.get("title") or ""),
                "seconds_alive": delta,
                "superseded_by": str(fastest.get("superseded_by") or ""),
                "created_at": str(fastest.get("created_at") or ""),
            },
        })

    completed = [r for r in in_window if r.get("status") == "completed"]
    completed_with_delta = [
        (r, _completion_seconds(r)) for r in completed
    ]
    completed_with_delta = [(r, d) for (r, d) in completed_with_delta if d is not None]
    if completed_with_delta:
        longest, delta = max(completed_with_delta, key=lambda pair: pair[1])
        extreme_samples.append({
            "role": "longest_completion",
            "id": str(longest.get("plan_id") or ""),
            "data": {
                "title": str(longest.get("title") or ""),
                "seconds_to_complete": delta,
                "created_at": str(longest.get("created_at") or ""),
            },
        })

    return {
        "plans_created": len(in_window),
        "status_distribution": status_dist,
        "extreme_samples": extreme_samples,
    }
