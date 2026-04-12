from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus


def record_runtime_action_outcome(
    *,
    action_id: str,
    mode: str,
    reason: str,
    score: float,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    recorded_at = datetime.now(UTC).isoformat()
    status = str(result.get("status") or "unknown")
    summary = str(result.get("summary") or "").strip()
    normalized = {
        "action_id": str(action_id or "").strip(),
        "decision_mode": str(mode or "").strip() or "noop",
        "decision_reason": str(reason or "").strip(),
        "decision_score": float(score or 0.0),
        "payload": dict(payload or {}),
        "result_status": status,
        "result_summary": summary,
        "result": dict(result or {}),
        "recorded_at": recorded_at,
    }

    stored = _persist_runtime_action_outcome(normalized)
    event_bus.publish(
        "runtime.executive_action_outcome_recorded",
        {
            "action_id": normalized["action_id"],
            "decision_mode": normalized["decision_mode"],
            "result_status": normalized["result_status"],
            "result_summary": normalized["result_summary"],
            "recorded_at": recorded_at,
        },
    )
    return stored


def build_runtime_action_outcome_surface(*, limit: int = 20) -> dict[str, Any]:
    items = recent_runtime_action_outcomes(limit=limit)
    latest = items[0] if items else {}
    return {
        "active": bool(items),
        "items": items,
        "summary": {
            "count": len(items),
            "latest_action": str(latest.get("action_id") or "none"),
            "latest_status": str(latest.get("result_status") or "none"),
            "latest_mode": str(latest.get("decision_mode") or "none"),
            "latest_summary": str(latest.get("result_summary") or "No recorded executive outcomes yet."),
        },
    }


def recent_runtime_action_outcomes(*, limit: int = 10) -> list[dict[str, Any]]:
    from core.runtime import db as runtime_db

    getter = getattr(runtime_db, "recent_runtime_action_outcomes", None)
    if not callable(getter):
        return []
    return list(getter(limit=max(limit, 1)))


def _persist_runtime_action_outcome(outcome: dict[str, Any]) -> dict[str, Any]:
    from core.runtime import db as runtime_db

    writer = getattr(runtime_db, "record_runtime_action_outcome", None)
    if not callable(writer):
        return outcome
    return writer(
        action_id=str(outcome.get("action_id") or ""),
        decision_mode=str(outcome.get("decision_mode") or ""),
        decision_reason=str(outcome.get("decision_reason") or ""),
        decision_score=float(outcome.get("decision_score") or 0.0),
        payload_json=outcome.get("payload") or {},
        result_status=str(outcome.get("result_status") or ""),
        result_summary=str(outcome.get("result_summary") or ""),
        result_json=outcome.get("result") or {},
        recorded_at=str(outcome.get("recorded_at") or ""),
    )
