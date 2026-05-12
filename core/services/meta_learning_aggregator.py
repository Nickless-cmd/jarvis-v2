"""Meta-læring aggregator — Phase 1 (AGI track #3).

Read-only queries på de 5 AGI-spor til ugentlig retrospektiv.
Hver funktion returnerer aggregat-stats + 1-2 ekstreme samples.

See spec: docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
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


def _confidence_score(value: Any, *, default: float = 0.0) -> float:
    """Normalize numeric and world-model textual confidence to 0..1."""
    if isinstance(value, str):
        mapped = {"low": 0.25, "medium": 0.55, "high": 0.85}
        lowered = value.strip().lower()
        if lowered in mapped:
            return mapped[lowered]
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _prediction_id(prediction: dict[str, Any]) -> str:
    return str(prediction.get("prediction_id") or prediction.get("id") or "")


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
        c = _confidence_score(p.get("confidence"))
        confidence_buckets[_bucket_confidence(c)] += 1

    extreme_samples: list[dict[str, Any]] = []

    contradicted = [p for p in resolved if p.get("outcome") == "contradicted"]
    if contradicted:
        top = max(contradicted, key=lambda p: _confidence_score(p.get("confidence")))
        extreme_samples.append({
            "role": "highest_confidence_contradicted",
            "id": _prediction_id(top),
            "data": {
                "subject": str(top.get("subject") or ""),
                "expectation": str(top.get("expectation") or ""),
                "confidence": top.get("confidence"),
                "confidence_score": _confidence_score(top.get("confidence")),
                "created_at": str(top.get("created_at") or ""),
                "resolved_at": str(top.get("resolved_at") or ""),
            },
        })

    supported = [p for p in resolved if p.get("outcome") == "supported"]
    if supported:
        low = min(supported, key=lambda p: _confidence_score(
            p.get("confidence"), default=1.0
        ))
        extreme_samples.append({
            "role": "lowest_confidence_supported",
            "id": _prediction_id(low),
            "data": {
                "subject": str(low.get("subject") or ""),
                "expectation": str(low.get("expectation") or ""),
                "confidence": low.get("confidence"),
                "confidence_score": _confidence_score(low.get("confidence")),
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


# ---------------------------------------------------------------------------
# Curiosity
# ---------------------------------------------------------------------------

def aggregate_curiosity(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate curiosity-tool activity in [since, until]."""
    from core.runtime.db import connect

    since_iso = since.isoformat()
    until_iso = until.isoformat()

    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, action, observation_text FROM curiosity_observations "
                "WHERE ts >= ? AND ts <= ? ORDER BY ts",
                (since_iso, until_iso),
            ).fetchall()
            rows = [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("aggregate_curiosity: query failed: %s", exc)
        rows = []

    action_dist: dict[str, int] = {}
    for r in rows:
        a = str(r.get("action") or "")
        action_dist[a] = action_dist.get(a, 0) + 1

    extreme_samples: list[dict[str, Any]] = []
    non_empty = [r for r in rows if str(r.get("observation_text") or "").strip()]
    if non_empty:
        longest = max(non_empty, key=lambda r: len(str(r.get("observation_text") or "")))
        shortest = min(non_empty, key=lambda r: len(str(r.get("observation_text") or "")))
        extreme_samples.append({
            "role": "longest_observation_text",
            "id": str(longest.get("id") or ""),
            "data": {
                "action": str(longest.get("action") or ""),
                "ts": str(longest.get("ts") or ""),
                "observation_text": str(longest.get("observation_text") or ""),
            },
        })
        if shortest.get("id") != longest.get("id"):
            extreme_samples.append({
                "role": "shortest_non_empty_observation",
                "id": str(shortest.get("id") or ""),
                "data": {
                    "action": str(shortest.get("action") or ""),
                    "ts": str(shortest.get("ts") or ""),
                    "observation_text": str(shortest.get("observation_text") or ""),
                },
            })

    return {
        "actions_used": len(rows),
        "action_distribution": action_dist,
        "extreme_samples": extreme_samples,
    }


# ---------------------------------------------------------------------------
# Skill chain Phase 2
# ---------------------------------------------------------------------------

def aggregate_skill_chain_phase2(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate skill_chain Phase 2 events in [since, until]."""
    from core.runtime.db import connect

    since_iso = since.isoformat()
    until_iso = until.isoformat()

    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT event_id, kind, created_at, payload_json FROM events "
                "WHERE family = 'cognitive_skill_chain' "
                "AND kind IN ('proposed', 'revised') "
                "AND created_at >= ? AND created_at <= ?",
                (since_iso, until_iso),
            ).fetchall()
            rows = [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("aggregate_skill_chain_phase2: query failed: %s", exc)
        rows = []

    proposals: list[dict[str, Any]] = []
    revisions: list[dict[str, Any]] = []
    for r in rows:
        try:
            payload = json.loads(str(r.get("payload_json") or "{}"))
        except (json.JSONDecodeError, ValueError):
            payload = {}
        r["_payload"] = payload
        if r.get("kind") == "proposed":
            proposals.append(r)
        elif r.get("kind") == "revised":
            revisions.append(r)

    ctx_dist = {"pre_execution": 0, "mid_chain": 0}
    for r in revisions:
        ctx = str(r["_payload"].get("revision_context") or "")
        if ctx in ctx_dist:
            ctx_dist[ctx] += 1

    extreme_samples: list[dict[str, Any]] = []

    if proposals:
        top = max(proposals, key=lambda r: float(r["_payload"].get("confidence") or 0))
        extreme_samples.append({
            "role": "highest_confidence_proposal",
            "id": str(top.get("event_id") or ""),
            "data": {
                "plan": top["_payload"].get("plan", []),
                "confidence": float(top["_payload"].get("confidence") or 0),
                "created_at": str(top.get("created_at") or ""),
            },
        })

    if revisions:
        longest = max(revisions, key=lambda r: len(str(r["_payload"].get("reason") or "")))
        extreme_samples.append({
            "role": "longest_reason_revision",
            "id": str(longest.get("event_id") or ""),
            "data": {
                "new_plan": longest["_payload"].get("new_plan", []),
                "revision_context": str(longest["_payload"].get("revision_context") or ""),
                "reason": str(longest["_payload"].get("reason") or ""),
                "created_at": str(longest.get("created_at") or ""),
            },
        })

    return {
        "proposals_made": len(proposals),
        "revisions_made": len(revisions),
        "revision_context_distribution": ctx_dist,
        "extreme_samples": extreme_samples,
    }


# ---------------------------------------------------------------------------
# Tool invention (proxy via plan_proposals with skill_data)
# ---------------------------------------------------------------------------

def aggregate_tool_invention(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate tool-invention activity in [since, until]."""
    from core.services.plan_proposals import _load_all

    try:
        all_plans = _load_all()
    except Exception as exc:
        logger.warning("aggregate_tool_invention: load failed: %s", exc)
        all_plans = {}

    skill_plans = [
        rec for rec in all_plans.values()
        if rec.get("skill_data") and _in_window(
            str(rec.get("created_at") or ""), since, until
        )
    ]
    proposed = len(skill_plans)
    adopted = sum(1 for r in skill_plans if r.get("status") == "approved")

    extreme_samples: list[dict[str, Any]] = []
    approved_skills = [r for r in skill_plans if r.get("status") == "approved"]
    if approved_skills:
        latest = max(approved_skills, key=lambda r: str(r.get("created_at") or ""))
        sd = latest.get("skill_data") or {}
        extreme_samples.append({
            "role": "most_recent_adopted_skill",
            "id": str(latest.get("plan_id") or ""),
            "data": {
                "skill_name": str(sd.get("name") or ""),
                "description": str(sd.get("description") or "")[:200],
                "created_at": str(latest.get("created_at") or ""),
            },
        })

    dismissed_skills = [r for r in skill_plans if r.get("status") == "dismissed"]
    if dismissed_skills:
        latest = max(dismissed_skills, key=lambda r: str(r.get("created_at") or ""))
        sd = latest.get("skill_data") or {}
        extreme_samples.append({
            "role": "most_recent_dismissed_skill",
            "id": str(latest.get("plan_id") or ""),
            "data": {
                "skill_name": str(sd.get("name") or ""),
                "description": str(sd.get("description") or "")[:200],
                "created_at": str(latest.get("created_at") or ""),
            },
        })

    return {
        "proposed": proposed,
        "adopted": adopted,
        "extreme_samples": extreme_samples,
    }
