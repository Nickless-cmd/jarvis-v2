from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services import runtime_flows, runtime_tasks
from core.eventbus.bus import event_bus
from core.runtime import db as runtime_db

_SUPPORTED_EVENT_KINDS = {
    "heartbeat.initiative_pushed",
    "heartbeat.tick_completed",
    "heartbeat.tick_blocked",
}


def dispatch_unhandled_hook_events(
    *,
    limit: int = 20,
    event_kinds: set[str] | None = None,
) -> list[dict[str, object]]:
    recent_events = list(reversed(event_bus.recent(limit=max(limit * 4, 20))))
    processed: list[dict[str, object]] = []
    allowed_event_kinds = (
        {kind for kind in event_kinds if kind in _SUPPORTED_EVENT_KINDS}
        if event_kinds
        else _SUPPORTED_EVENT_KINDS
    )
    for event in recent_events:
        if len(processed) >= max(limit, 1):
            break
        event_id = int(event.get("id") or 0)
        event_kind = str(event.get("kind") or "")
        if event_id <= 0 or event_kind not in allowed_event_kinds:
            continue
        if runtime_db.get_runtime_hook_dispatch(event_id) is not None:
            continue
        processed.append(dispatch_hook_event(event))
    return processed


def dispatch_hook_event(event: dict[str, object]) -> dict[str, object]:
    event_id = int(event.get("id") or 0)
    event_kind = str(event.get("kind") or "")
    payload = dict(event.get("payload") or {})
    created_at = str(event.get("created_at") or datetime.now(UTC).isoformat())
    existing = runtime_db.get_runtime_hook_dispatch(event_id)
    if existing is not None:
        return existing

    if event_kind == "heartbeat.initiative_pushed":
        focus = str(payload.get("focus") or "").strip() or "Follow queued initiative"
        priority = str(payload.get("priority") or "medium").strip().lower()
        existing = _find_active_task(
            kind="initiative-followup",
            goal=focus,
            scope=focus,
        )
        if existing is not None:
            return runtime_db.record_runtime_hook_dispatch(
                event_id=event_id,
                event_kind=event_kind,
                status="coalesced",
                task_id=str(existing.get("task_id") or ""),
                flow_id=str(existing.get("flow_id") or ""),
                summary=f"Coalesced into existing initiative follow-up: {focus[:120]}",
                created_at=created_at,
            )
        task = runtime_tasks.create_task(
            kind="initiative-followup",
            goal=focus,
            origin=f"hook:{event_kind}",
            scope=focus,
            priority=priority,
            owner="runtime-hook",
        )
        flow = runtime_flows.create_flow(
            task_id=task["task_id"],
            current_step="review-initiative",
            step_state="queued",
            plan=[
                {"step": "review-initiative", "status": "queued"},
                {"step": "take-bounded-next-step", "status": "pending"},
            ],
            next_action="Inspect the initiative focus and choose the next bounded action.",
        )
        return runtime_db.record_runtime_hook_dispatch(
            event_id=event_id,
            event_kind=event_kind,
            status="dispatched",
            task_id=task["task_id"],
            flow_id=flow["flow_id"],
            summary=f"Created initiative follow-up task for: {focus[:120]}",
            created_at=created_at,
        )

    if event_kind in {"heartbeat.tick_completed", "heartbeat.tick_blocked"}:
        action_status = str(payload.get("action_status") or "").strip().lower()
        summary = str(payload.get("summary") or "").strip()
        blocked_reason = str(payload.get("blocked_reason") or "").strip()
        goal = summary or blocked_reason or "Investigate blocked heartbeat action"
        scope = str(payload.get("action_type") or "").strip()
        if action_status not in {"blocked", "failed"} and not blocked_reason:
            return runtime_db.record_runtime_hook_dispatch(
                event_id=event_id,
                event_kind=event_kind,
                status="ignored",
                summary="Heartbeat tick had no blocked or failed follow-up condition.",
                created_at=created_at,
            )
        existing = _find_active_task(
            kind="heartbeat-followup",
            goal=goal,
            scope=scope,
        )
        if existing is not None:
            return runtime_db.record_runtime_hook_dispatch(
                event_id=event_id,
                event_kind=event_kind,
                status="coalesced",
                task_id=str(existing.get("task_id") or ""),
                flow_id=str(existing.get("flow_id") or ""),
                summary=f"Coalesced into existing heartbeat follow-up: {goal[:120]}",
                created_at=created_at,
            )
        task = runtime_tasks.create_task(
            kind="heartbeat-followup",
            goal=goal,
            origin=f"hook:{event_kind}",
            scope=scope,
            priority="medium",
            run_id=str(payload.get("tick_id") or "").strip(),
            owner="runtime-hook",
        )
        flow = runtime_flows.create_flow(
            task_id=task["task_id"],
            current_step="inspect-heartbeat-block",
            step_state="queued",
            plan=[
                {"step": "inspect-heartbeat-block", "status": "queued"},
                {"step": "resume-bounded-work", "status": "pending"},
            ],
            next_action="Inspect the blocked heartbeat path and prepare the next bounded continuation.",
        )
        return runtime_db.record_runtime_hook_dispatch(
            event_id=event_id,
            event_kind=event_kind,
            status="dispatched",
            task_id=task["task_id"],
            flow_id=flow["flow_id"],
            summary=(summary or blocked_reason)[:200]
            or "Created heartbeat follow-up task from blocked tick.",
            created_at=created_at,
        )

    return runtime_db.record_runtime_hook_dispatch(
        event_id=event_id,
        event_kind=event_kind,
        status="ignored",
        summary="Event kind is not supported by runtime hook dispatch.",
        created_at=created_at,
    )


def _find_active_task(
    *,
    kind: str,
    goal: str,
    scope: str,
) -> dict[str, object] | None:
    normalized_goal = " ".join(str(goal or "").split()).strip().lower()
    normalized_scope = " ".join(str(scope or "").split()).strip().lower()
    for status in ("queued", "running", "blocked"):
        for task in runtime_tasks.list_tasks(status=status, kind=kind, limit=40):
            task_goal = " ".join(str(task.get("goal") or "").split()).strip().lower()
            task_scope = " ".join(str(task.get("scope") or "").split()).strip().lower()
            if task_goal == normalized_goal and task_scope == normalized_scope:
                return task
    return None
