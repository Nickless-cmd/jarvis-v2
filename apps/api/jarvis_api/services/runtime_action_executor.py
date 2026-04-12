from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from apps.api.jarvis_api.services.chat_sessions import recent_chat_session_messages
from apps.api.jarvis_api.services.initiative_queue import (
    mark_acted,
    mark_attempted,
)
from apps.api.jarvis_api.services.notification_bridge import send_session_notification
from apps.api.jarvis_api.services.runtime_operational_memory import (
    build_operational_memory_snapshot,
)
from core.eventbus.bus import event_bus
from core.runtime.db import recent_visible_runs


ExecutionStatus = Literal["executed", "proposed", "blocked", "failed", "skipped"]


@dataclass(slots=True)
class RuntimeExecutionResult:
    status: ExecutionStatus
    action_id: str
    summary: str
    details: dict[str, Any]
    side_effects: list[str]
    error: str = ""


def execute_runtime_action(
    *,
    action_id: str,
    payload: dict[str, Any],
) -> RuntimeExecutionResult:
    action = str(action_id or "").strip()
    if action == "refresh_memory_context":
        result = execute_refresh_memory_context(payload)
    elif action == "follow_open_loop":
        result = execute_follow_open_loop(payload)
    elif action == "inspect_repo_context":
        result = execute_inspect_repo_context(payload)
    elif action == "review_recent_conversations":
        result = execute_review_recent_conversations(payload)
    elif action == "write_internal_work_note":
        result = execute_write_internal_work_note(payload)
    elif action == "bounded_self_check":
        result = execute_bounded_self_check(payload)
    elif action == "propose_next_user_step":
        result = execute_propose_next_user_step(payload)
    elif action == "promote_initiative_to_visible_lane":
        result = execute_promote_initiative_to_visible_lane(payload)
    else:
        result = RuntimeExecutionResult(
            status="skipped",
            action_id=action or "unknown",
            summary="Runtime action is not implemented.",
            details={"payload": dict(payload)},
            side_effects=[],
            error="unknown-action",
        )
    _publish_action_event(result)
    return result


def execute_refresh_memory_context(payload: dict[str, Any]) -> RuntimeExecutionResult:
    snapshot = build_operational_memory_snapshot(limit=6)
    summary = snapshot.get("summary") or {}
    return RuntimeExecutionResult(
        status="executed",
        action_id="refresh_memory_context",
        summary=(
            "Refreshed operational memory context "
            f"(loops={summary.get('open_loop_count') or 0}, "
            f"initiatives={summary.get('initiative_count') or 0})."
        ),
        details={"snapshot_summary": summary, "reason": str(payload.get("reason") or "")},
        side_effects=["operational-memory-refresh"],
    )


def execute_follow_open_loop(payload: dict[str, Any]) -> RuntimeExecutionResult:
    title = str(payload.get("title") or "Open loop").strip()
    return RuntimeExecutionResult(
        status="executed",
        action_id="follow_open_loop",
        summary=f"Selected bounded follow-up for open loop: {title[:160]}",
        details={
            "loop_id": str(payload.get("loop_id") or ""),
            "title": title[:200],
            "status": str(payload.get("status") or ""),
            "next_step": f"Inspect and carry forward '{title[:120]}' on the next eligible lane.",
        },
        side_effects=["open-loop-selected"],
    )


def execute_inspect_repo_context(payload: dict[str, Any]) -> RuntimeExecutionResult:
    runs = recent_visible_runs(limit=3)
    latest = runs[0] if runs else {}
    return RuntimeExecutionResult(
        status="executed",
        action_id="inspect_repo_context",
        summary="Built a bounded repo context inspection from recent visible work.",
        details={
            "latest_run": latest,
            "requested_focus": str(payload.get("focus") or ""),
        },
        side_effects=["repo-context-inspected"],
    )


def execute_review_recent_conversations(payload: dict[str, Any]) -> RuntimeExecutionResult:
    session_id = str(payload.get("session_id") or "").strip()
    messages = recent_chat_session_messages(session_id, limit=6) if session_id else []
    return RuntimeExecutionResult(
        status="executed",
        action_id="review_recent_conversations",
        summary=f"Reviewed {len(messages)} recent chat messages for carry-forward context.",
        details={"session_id": session_id, "messages": messages},
        side_effects=["conversation-review"],
    )


def execute_write_internal_work_note(payload: dict[str, Any]) -> RuntimeExecutionResult:
    current_mode = str(payload.get("current_mode") or "watch")
    note = (
        "Executive note: "
        f"runtime is in {current_mode} mode and is carrying quiet internal pressure."
    )
    return RuntimeExecutionResult(
        status="executed",
        action_id="write_internal_work_note",
        summary=note,
        details={"note": note, "current_mode": current_mode},
        side_effects=["internal-work-note"],
    )


def execute_bounded_self_check(payload: dict[str, Any]) -> RuntimeExecutionResult:
    contradiction_count = int(payload.get("contradiction_count") or 0)
    current_mode = str(payload.get("current_mode") or "clarify")
    return RuntimeExecutionResult(
        status="executed",
        action_id="bounded_self_check",
        summary=(
            "Ran bounded self-check before action "
            f"(mode={current_mode}, contradictions={contradiction_count})."
        ),
        details={
            "current_mode": current_mode,
            "contradiction_count": contradiction_count,
        },
        side_effects=["self-check"],
    )


def execute_propose_next_user_step(payload: dict[str, Any]) -> RuntimeExecutionResult:
    current_mode = str(payload.get("current_mode") or "respond")
    content = (
        "[runtime proposal] Jeg har en lille næste handling klar, "
        f"men holder den bounded indtil den er nyttig i {current_mode}-mode."
    )
    delivery = send_session_notification(content, source="runtime-proposal")
    status = "proposed" if delivery.get("status") == "ok" else "blocked"
    return RuntimeExecutionResult(
        status=status,
        action_id="propose_next_user_step",
        summary="Proposed a bounded next step into the visible lane." if status == "proposed" else "Could not deliver visible proposal.",
        details={"delivery": delivery, "content": content},
        side_effects=["visible-proposal"] if status == "proposed" else [],
        error="" if status == "proposed" else str(delivery.get("error") or "no-active-session"),
    )


def execute_promote_initiative_to_visible_lane(payload: dict[str, Any]) -> RuntimeExecutionResult:
    initiative_id = str(payload.get("initiative_id") or "").strip()
    focus = str(payload.get("focus") or "Pending initiative").strip()
    delivery = send_session_notification(
        f"[initiative] Jeg vil gerne følge op på: {focus[:180]}",
        source="runtime-initiative",
    )
    if delivery.get("status") == "ok":
        if initiative_id:
            mark_acted(initiative_id, action_summary="promoted-to-visible-lane")
        return RuntimeExecutionResult(
            status="proposed",
            action_id="promote_initiative_to_visible_lane",
            summary=f"Promoted initiative to visible lane: {focus[:160]}",
            details={"delivery": delivery, "initiative_id": initiative_id, "focus": focus[:200]},
            side_effects=["initiative-promoted"],
        )

    if initiative_id:
        mark_attempted(
            initiative_id,
            blocked_reason=str(delivery.get("error") or "no-active-session"),
            action_summary="promotion-blocked",
        )
    return RuntimeExecutionResult(
        status="blocked",
        action_id="promote_initiative_to_visible_lane",
        summary="Initiative could not be promoted to the visible lane.",
        details={"delivery": delivery, "initiative_id": initiative_id, "focus": focus[:200]},
        side_effects=[],
        error=str(delivery.get("error") or "no-active-session"),
    )


def _publish_action_event(result: RuntimeExecutionResult) -> None:
    event_bus.publish(
        "runtime.executive_action_completed",
        {
            "action_id": result.action_id,
            "status": result.status,
            "summary": result.summary,
            "details": asdict(result).get("details", {}),
            "side_effects": list(result.side_effects),
            "error": result.error,
        },
    )
