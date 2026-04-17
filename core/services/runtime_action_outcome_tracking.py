from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.services.completion_satisfaction import detect_completion_satisfaction
from core.services.runtime_learning_signals import (
    extract_runtime_learning_signals,
)
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
    learning_signals = _persist_learning_signals(stored)
    event_bus.publish(
        "runtime.executive_action_outcome_recorded",
        {
            "action_id": normalized["action_id"],
            "decision_mode": normalized["decision_mode"],
            "result_status": normalized["result_status"],
            "result_summary": normalized["result_summary"],
            "recorded_at": recorded_at,
            "learning_signal_count": len(learning_signals),
        },
    )
    return stored


def build_runtime_action_outcome_surface(*, limit: int = 20) -> dict[str, Any]:
    items = recent_runtime_action_outcomes(limit=limit)
    latest = items[0] if items else {}
    completion_satisfaction = detect_completion_satisfaction(
        task_outcomes=[
            _completion_outcome_label(item.get("result_status"))
            for item in items[:10]
        ],
        repetition_on_same_topic=_consecutive_repetition_count(items),
    )
    return {
        "active": bool(items),
        "items": items,
        "summary": {
            "count": len(items),
            "latest_action": str(latest.get("action_id") or "none"),
            "latest_status": str(latest.get("result_status") or "none"),
            "latest_mode": str(latest.get("decision_mode") or "none"),
            "latest_summary": str(latest.get("result_summary") or "No recorded executive outcomes yet."),
            "completion_satisfaction": completion_satisfaction,
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


def _persist_learning_signals(outcome: dict[str, Any]) -> list[dict[str, Any]]:
    from core.runtime import db as runtime_db

    writer = getattr(runtime_db, "record_runtime_learning_signal", None)
    if not callable(writer):
        return []
    stored: list[dict[str, Any]] = []
    for signal in extract_runtime_learning_signals(outcome):
        stored.append(
            writer(
                outcome_id=str(signal.get("outcome_id") or ""),
                source_action_id=str(signal.get("source_action_id") or ""),
                target_action_id=str(signal.get("target_action_id") or ""),
                target_family=str(signal.get("target_family") or ""),
                target_domain=str(signal.get("target_domain") or ""),
                signal_key=str(signal.get("signal_key") or ""),
                signal_weight=float(signal.get("signal_weight") or 0.0),
                signal_count=int(signal.get("signal_count") or 1),
                metadata_json=signal.get("metadata") or {},
                recorded_at=str(signal.get("recorded_at") or ""),
            )
        )
    return stored


def _completion_outcome_label(status: object) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"executed", "success", "completed"}:
        return "success"
    if normalized in {"blocked", "failed"}:
        return "failed"
    if normalized in {"proposed", "skipped"}:
        return "partial"
    return normalized or "partial"


def _consecutive_repetition_count(items: list[dict[str, Any]]) -> int:
    if not items:
        return 0
    latest_action = str(items[0].get("action_id") or "").strip()
    if not latest_action:
        return 0
    count = 0
    for item in items:
        if str(item.get("action_id") or "").strip() != latest_action:
            break
        count += 1
    return max(count - 1, 0)
