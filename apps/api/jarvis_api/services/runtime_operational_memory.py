from __future__ import annotations

from typing import Any

from apps.api.jarvis_api.services.executive_contradiction_signal_tracking import (
    build_runtime_executive_contradiction_signal_surface,
)
from apps.api.jarvis_api.services.initiative_queue import get_pending_initiatives
from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface
from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
    build_runtime_private_initiative_tension_signal_surface,
)
from core.runtime.db import (
    recent_runtime_action_outcomes,
    recent_visible_runs,
    recent_visible_work_notes,
    recent_visible_work_units,
    visible_session_continuity,
)


def build_operational_memory_snapshot(*, limit: int = 12) -> dict[str, Any]:
    loops = recent_open_loops(limit=min(limit, 6))
    outcomes = recent_visible_outcomes(limit=min(limit, 6))
    tensions = active_internal_pressures(limit=min(limit, 4))
    contradictions = active_executive_contradictions(limit=min(limit, 4))
    initiatives = queued_initiatives(limit=min(limit, 4))
    executive_feedback = recent_executive_feedback(limit=min(limit, 6))
    executive_feedback_summary = summarize_executive_feedback(executive_feedback)
    continuity = visible_session_continuity()
    user_facts = remembered_user_facts(limit=min(limit, 3))
    work_context = active_work_context(limit=min(limit, 5))

    return {
        "open_loops": loops,
        "recent_outcomes": outcomes,
        "user_facts": user_facts,
        "internal_pressures": tensions,
        "executive_contradictions": contradictions,
        "queued_initiatives": initiatives,
        "executive_feedback": executive_feedback,
        "executive_feedback_summary": executive_feedback_summary,
        "work_context": work_context,
        "visible_continuity": continuity,
        "summary": {
            "open_loop_count": len(loops),
            "recent_outcome_count": len(outcomes),
            "executive_outcome_count": len(executive_feedback),
            "initiative_count": len(initiatives),
            "pressure_count": len(tensions),
            "contradiction_count": len(contradictions),
            "memory_context_stale": (
                len(outcomes) == 0
                and len(executive_feedback) == 0
                and len(work_context) <= 1
            ),
            "continuity_summary": str(continuity.get("summary") or ""),
            "latest_executive_action": executive_feedback_summary["latest_action"],
            "latest_executive_status": executive_feedback_summary["latest_status"],
            "repeat_action_detected": executive_feedback_summary["repeat_action_detected"],
            "blocked_action_detected": executive_feedback_summary["blocked_action_detected"],
        },
    }


def recent_open_loops(*, limit: int = 5) -> list[dict[str, Any]]:
    runtime = build_loop_runtime_surface()
    items = list(runtime.get("items") or [])
    live_items = [
        item
        for item in items
        if str(item.get("runtime_status") or "") in {"active", "resumed", "standby"}
    ]
    return live_items[: max(limit, 1)]


def recent_visible_outcomes(*, limit: int = 5) -> list[dict[str, Any]]:
    notes = recent_visible_work_notes(limit=max(limit, 1))
    if notes:
        return notes[: max(limit, 1)]
    units = recent_visible_work_units(limit=max(limit, 1))
    if units:
        return units[: max(limit, 1)]
    return recent_visible_runs(limit=max(limit, 1))


def active_internal_pressures(*, limit: int = 5) -> list[dict[str, Any]]:
    surface = build_runtime_private_initiative_tension_signal_surface(limit=max(limit, 1))
    items = list(surface.get("items") or [])
    return [
        item
        for item in items
        if str(item.get("status") or "") == "active"
    ][: max(limit, 1)]


def active_executive_contradictions(*, limit: int = 5) -> list[dict[str, Any]]:
    surface = build_runtime_executive_contradiction_signal_surface(limit=max(limit, 1))
    items = list(surface.get("items") or [])
    return [
        item
        for item in items
        if str(item.get("status") or "") in {"active", "softening"}
    ][: max(limit, 1)]


def remembered_user_facts(*, limit: int = 5) -> list[dict[str, Any]]:
    continuity = visible_session_continuity()
    notes = list(continuity.get("recent_notes") or [])
    facts: list[dict[str, Any]] = []
    for item in notes[: max(limit, 1)]:
        preview = str(item.get("user_message_preview") or "").strip()
        if not preview:
            continue
        facts.append(
            {
                "source": "visible-note",
                "summary": preview[:200],
                "created_at": str(item.get("created_at") or ""),
            }
        )
    return facts


def active_work_context(*, limit: int = 5) -> list[dict[str, Any]]:
    items = recent_visible_work_units(limit=max(limit, 1))
    context: list[dict[str, Any]] = []
    for item in items:
        context.append(
            {
                "source": "visible-work-unit",
                "work_id": str(item.get("work_id") or ""),
                "summary": str(item.get("work_preview") or item.get("user_message_preview") or "")[:200],
                "status": str(item.get("status") or ""),
                "updated_at": str(item.get("finished_at") or item.get("started_at") or ""),
            }
        )
    return context[: max(limit, 1)]


def queued_initiatives(*, limit: int = 5) -> list[dict[str, Any]]:
    return get_pending_initiatives()[: max(limit, 1)]


def recent_executive_feedback(*, limit: int = 6) -> list[dict[str, Any]]:
    return recent_runtime_action_outcomes(limit=max(limit, 1))[: max(limit, 1)]


def summarize_executive_feedback(
    items: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    normalized = list(items or [])
    latest = normalized[0] if normalized else {}
    action_stats: dict[str, dict[str, Any]] = {}
    for item in normalized:
        action_id = str(item.get("action_id") or "").strip()
        if not action_id:
            continue
        status = str(item.get("result_status") or "unknown").strip() or "unknown"
        bucket = action_stats.setdefault(
            action_id,
            {
                "count": 0,
                "latest_status": status,
                "success_count": 0,
                "blocked_count": 0,
                "failed_count": 0,
                "executed_count": 0,
                "proposed_count": 0,
            },
        )
        bucket["count"] += 1
        bucket["latest_status"] = bucket.get("latest_status") or status
        if status in {"executed", "recorded", "sent"}:
            bucket["success_count"] += 1
        if status == "blocked":
            bucket["blocked_count"] += 1
        if status == "failed":
            bucket["failed_count"] += 1
        if status == "executed":
            bucket["executed_count"] += 1
        if status == "proposed":
            bucket["proposed_count"] += 1
    repeat_action_detected = False
    blocked_action_detected = False
    if len(normalized) >= 2:
        first = str(normalized[0].get("action_id") or "")
        second = str(normalized[1].get("action_id") or "")
        repeat_action_detected = bool(first and first == second)
    if normalized:
        blocked_action_detected = any(
            str(item.get("result_status") or "") in {"blocked", "failed"}
            for item in normalized[:2]
        )
    return {
        "latest_action": str(latest.get("action_id") or "none"),
        "latest_status": str(latest.get("result_status") or "none"),
        "repeat_action_detected": repeat_action_detected,
        "blocked_action_detected": blocked_action_detected,
        "action_stats": action_stats,
    }
