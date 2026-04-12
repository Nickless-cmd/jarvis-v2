from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import asdict, dataclass
from typing import Any, Literal
from uuid import uuid4

from apps.api.jarvis_api.services.chat_sessions import recent_chat_session_messages
from apps.api.jarvis_api.services.bounded_repo_tools_runtime import (
    build_bounded_repo_tool_execution_surface,
)
from apps.api.jarvis_api.services.initiative_queue import (
    mark_acted,
    mark_attempted,
)
from apps.api.jarvis_api.services.notification_bridge import send_session_notification
from apps.api.jarvis_api.services.open_loop_closure_proposal_tracking import (
    build_runtime_open_loop_closure_proposal_surface,
)
from apps.api.jarvis_api.services.runtime_operational_memory import (
    build_operational_memory_snapshot,
)
from apps.api.jarvis_api.services.runtime_tasks import create_task
from apps.api.jarvis_api.services.self_system_code_awareness import (
    build_self_system_code_awareness_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.config import PROJECT_ROOT
from core.runtime.db import record_visible_work_note
from core.tools.workspace_capabilities import (
    invoke_workspace_capability,
    load_workspace_capabilities,
)


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
    loop_id = str(payload.get("loop_id") or "")
    status = str(payload.get("status") or "")
    canonical_key = str(payload.get("canonical_key") or "")
    closure = _matching_loop_closure(loop_id=loop_id, canonical_key=canonical_key)
    closure_summary = str((closure or {}).get("summary") or "").strip()
    closure_confidence = str((closure or {}).get("closure_confidence") or "").strip()
    goal = (
        closure_summary
        or f"Follow open loop with a bounded next step: {title[:160]}"
    )
    task = create_task(
        kind="open-loop-follow-up",
        goal=goal,
        origin="runtime-executive",
        scope=canonical_key or loop_id or title[:120],
        priority="high" if status in {"active", "resumed"} else "medium",
        owner="runtime-executive",
    )
    return RuntimeExecutionResult(
        status="executed",
        action_id="follow_open_loop",
        summary=f"Persisted bounded follow-up for open loop: {title[:160]}",
        details={
            "loop_id": loop_id,
            "title": title[:200],
            "status": status,
            "canonical_key": canonical_key,
            "task": task,
            "closure_proposal": closure,
            "next_step": (
                closure_summary
                or f"Inspect and carry forward '{title[:120]}' on the next eligible lane."
            ),
        },
        side_effects=[
            "open-loop-selected",
            "runtime-task-created",
            *(
                [f"closure-proposal:{closure_confidence or 'present'}"]
                if closure
                else []
            ),
        ],
    )


def execute_inspect_repo_context(payload: dict[str, Any]) -> RuntimeExecutionResult:
    focus = str(payload.get("focus") or payload.get("title") or "").strip()
    operation = _repo_operation_from_focus(focus)
    capability_result = invoke_workspace_capability(
        "tool:run-non-destructive-command",
        run_id=str(payload.get("run_id") or f"runtime-exec-{uuid4().hex[:12]}"),
        name="default",
        command_text=_repo_command_for_operation(operation),
    )
    awareness = build_self_system_code_awareness_surface()
    bounded_surface = build_bounded_repo_tool_execution_surface(
        {
            "intent_state": "active",
            "intent_type": operation,
            "intent_target": focus or "workspace",
            "approval_scope": (
                "repo-update-check"
                if operation == "inspect-upstream-divergence"
                else "repo-read"
            ),
            "approval_state": "approved",
            "confidence": "high",
        },
        awareness_surface=awareness,
    )
    capabilities = load_workspace_capabilities(name="default")
    callable_ids = list(capabilities.get("callable_capability_ids") or [])
    cap_result = capability_result.get("result") or {}
    command_preview = ""
    if isinstance(cap_result, dict):
        command_preview = str(cap_result.get("text") or "").strip()
    return RuntimeExecutionResult(
        status="executed"
        if str(capability_result.get("status") or "") == "executed"
        else "blocked",
        action_id="inspect_repo_context",
        summary=(
            str(bounded_surface.get("execution_summary") or "").strip()
            or "Ran a bounded repo context inspection."
        ),
        details={
            "requested_focus": focus,
            "repo_operation": operation,
            "workspace_capability_id": "tool:run-non-destructive-command",
            "workspace_capability_status": str(capability_result.get("status") or ""),
            "workspace_capability_detail": str(capability_result.get("detail") or ""),
            "workspace_callable_capability_ids": callable_ids,
            "bounded_repo_surface": bounded_surface,
            "repo_command_preview": command_preview[:4000],
        },
        side_effects=(
            ["repo-context-inspected", "workspace-capability-invoked"]
            if str(capability_result.get("status") or "") == "executed"
            else ["workspace-capability-blocked"]
        ),
        error=""
        if str(capability_result.get("status") or "") == "executed"
        else str(capability_result.get("detail") or "repo-capability-blocked"),
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
    focus_hint = str(payload.get("title") or payload.get("focus_hint") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    emphasis = focus_hint or reason
    if reason and focus_hint and focus_hint.lower() not in reason.lower():
        emphasis = f"{focus_hint}; {reason}"
    note = _build_internal_work_note(current_mode=current_mode, emphasis=emphasis)
    now = datetime.now(UTC).isoformat()
    persisted = record_visible_work_note(
        note_id=f"rwn-{uuid4().hex[:12]}",
        work_id=f"runtime-work-{uuid4().hex[:12]}",
        run_id=f"runtime-note-{uuid4().hex[:12]}",
        status="completed",
        lane="heartbeat",
        provider="runtime-executive",
        model="internal-note",
        user_message_preview="Runtime executive internal note",
        capability_id="runtime:write_internal_work_note",
        work_preview=note[:400],
        projection_source="runtime-executive-note",
        created_at=now,
        finished_at=now,
    )
    return RuntimeExecutionResult(
        status="executed",
        action_id="write_internal_work_note",
        summary="Persisted executive work note.",
        details={
            "note": note,
            "current_mode": current_mode,
            "persisted_note": persisted,
        },
        side_effects=["internal-work-note", "visible-work-note-persisted"],
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


def _matching_loop_closure(
    *,
    loop_id: str,
    canonical_key: str,
) -> dict[str, Any] | None:
    domain_key = _loop_domain_key(loop_id=loop_id, canonical_key=canonical_key)
    if not domain_key:
        return None
    for item in build_runtime_open_loop_closure_proposal_surface(limit=8).get("items", []):
        canonical = str(item.get("canonical_key") or "")
        if canonical.endswith(f":{domain_key}"):
            return dict(item)
    return None


def _loop_domain_key(*, loop_id: str, canonical_key: str) -> str:
    if canonical_key.strip():
        parts = canonical_key.split(":")
        return parts[-1].strip()
    if loop_id.startswith("open-loop:"):
        raw = loop_id.removeprefix("open-loop:")
        parts = raw.split(":")
        return parts[-1].strip()
    return loop_id.strip()


def _repo_operation_from_focus(focus: str) -> str:
    lowered = focus.lower()
    if any(token in lowered for token in ("upstream", "ahead", "behind", "diverg")):
        return "inspect-upstream-divergence"
    if any(token in lowered for token in ("working tree", "diff", "stat", "patch")):
        return "inspect-working-tree"
    if any(token in lowered for token in ("change", "dirty", "modified", "untracked")):
        return "inspect-local-changes"
    if any(token in lowered for token in ("concern", "problem", "issue", "anomaly")):
        return "inspect-concern"
    return "inspect-repo-status"


def _repo_command_for_operation(operation: str) -> str:
    repo = str(PROJECT_ROOT)
    if operation == "inspect-upstream-divergence":
        return (
            f"git -C {repo} status --short; "
            f"git -C {repo} branch --show-current; "
            f"git -C {repo} rev-list --left-right --count HEAD...@{{upstream}}"
        )
    if operation == "inspect-working-tree":
        return (
            f"git -C {repo} status --short; "
            f"git -C {repo} diff --stat --compact-summary"
        )
    if operation == "inspect-local-changes":
        return f"git -C {repo} status --short"
    return (
        f"git -C {repo} status --short; "
        f"git -C {repo} branch --show-current; "
        f"git -C {repo} log --oneline -n 5"
    )


def _build_internal_work_note(*, current_mode: str, emphasis: str) -> str:
    if emphasis:
        return (
            "Executive note: "
            f"runtime is in {current_mode} mode and is carrying {emphasis[:220]}."
        )
    return (
        "Executive note: "
        f"runtime is in {current_mode} mode and is carrying quiet internal pressure."
    )
