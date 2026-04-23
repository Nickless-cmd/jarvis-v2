"""Behavioral decisions — closing the reflection→behavior loop.

A reflection says "I should stop X". A decision is the durable
commitment: "from now on, when Y happens, do Z." This service:

- Lets Jarvis record, review, and revoke commitments via tools.
- Publishes events (decision.created/.updated/.reviewed/.revoked)
  so MC can project adherence.
- Surfaces active decisions in the heartbeat prompt every cycle,
  so Jarvis actually feels his own commitments instead of forgetting
  them the moment the conversation ends.
"""
from __future__ import annotations

import logging
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db_decisions import (
    append_review,
    count_decisions,
    create_decision as _db_create,
    delete_decision as _db_delete,
    get_decision as _db_get,
    list_decisions as _db_list,
    list_reviews,
    set_status as _db_set_status,
)

logger = logging.getLogger(__name__)


def create_decision(
    *,
    directive: str,
    rationale: str | None = None,
    trigger_cue: str | None = None,
    priority: int = 50,
    source_record_id: str | None = None,
    source_type: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    decision = _db_create(
        directive=directive,
        rationale=rationale,
        trigger_cue=trigger_cue,
        priority=priority,
        source_record_id=source_record_id,
        source_type=source_type,
        created_by=created_by,
    )
    try:
        event_bus.publish(
            "decision.created",
            {
                "decision_id": decision.get("decision_id"),
                "directive": decision.get("directive"),
                "priority": decision.get("priority"),
                "source_type": decision.get("source_type"),
            },
        )
    except Exception as exc:
        logger.debug("behavioral_decisions: publish created failed: %s", exc)
    return decision


def review_decision(
    *,
    decision_id: str,
    verdict: str,
    note: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any] | None:
    result = append_review(
        decision_id=decision_id,
        verdict=verdict,
        note=note,
        evidence=evidence,
    )
    if not result:
        return None
    try:
        event_bus.publish(
            "decision.reviewed",
            {
                "decision_id": result.get("decision_id"),
                "directive": result.get("directive"),
                "verdict": verdict,
                "adherence_score": result.get("adherence_score"),
            },
        )
    except Exception as exc:
        logger.debug("behavioral_decisions: publish reviewed failed: %s", exc)
    return result


def change_status(decision_id: str, new_status: str) -> dict[str, Any] | None:
    updated = _db_set_status(decision_id, new_status)
    if not updated:
        return None
    try:
        event_bus.publish(
            "decision.updated",
            {
                "decision_id": updated.get("decision_id"),
                "directive": updated.get("directive"),
                "status": updated.get("status"),
            },
        )
    except Exception:
        pass
    return updated


def revoke_decision(decision_id: str, *, reason: str | None = None) -> dict[str, Any] | None:
    updated = _db_set_status(decision_id, "revoked")
    if not updated:
        return None
    try:
        event_bus.publish(
            "decision.revoked",
            {
                "decision_id": updated.get("decision_id"),
                "directive": updated.get("directive"),
                "reason": reason,
            },
        )
    except Exception:
        pass
    return updated


def delete_decision(decision_id: str) -> bool:
    ok = _db_delete(decision_id)
    if ok:
        try:
            event_bus.publish("decision.deleted", {"decision_id": decision_id})
        except Exception:
            pass
    return ok


def get_decision(decision_id: str) -> dict[str, Any] | None:
    return _db_get(decision_id)


def get_decision_with_reviews(
    decision_id: str, *, review_limit: int = 10
) -> dict[str, Any] | None:
    d = _db_get(decision_id)
    if not d:
        return None
    d = dict(d)
    d["recent_reviews"] = list_reviews(decision_id, limit=review_limit)
    return d


def list_active_decisions(*, limit: int = 20) -> list[dict[str, Any]]:
    return _db_list(status="active", limit=limit)


def list_all_decisions(*, limit: int = 100) -> list[dict[str, Any]]:
    return _db_list(status="all", limit=limit)


def format_active_decisions_for_heartbeat(*, max_items: int = 3) -> str:
    """Compact line of top active commitments for heartbeat injection."""
    decisions = _db_list(status="active", limit=max_items)
    if not decisions:
        return ""
    parts: list[str] = []
    for d in decisions:
        directive = str(d.get("directive") or "").strip()
        cue = str(d.get("trigger_cue") or "").strip()
        adherence = d.get("adherence_score")
        chunk = directive
        if cue:
            chunk = f"{directive} (when: {cue})"
        if adherence is not None:
            chunk += f" [adherence={adherence:.2f}]"
        parts.append(chunk)
    return " | ".join(parts)


def get_stats() -> dict[str, Any]:
    return {
        "active": count_decisions(status="active"),
        "paused": count_decisions(status="paused"),
        "revoked": count_decisions(status="revoked"),
        "fulfilled": count_decisions(status="fulfilled"),
        "total": count_decisions(),
    }
