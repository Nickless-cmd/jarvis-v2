from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.api.jarvis_api.services.autonomy_pressure_signal_tracking import (
    build_runtime_autonomy_pressure_signal_surface,
)
from apps.api.jarvis_api.services.chat_sessions import (
    append_chat_message,
    get_chat_session,
    list_chat_sessions,
)
from apps.api.jarvis_api.services.proactive_loop_lifecycle_tracking import (
    build_runtime_proactive_loop_lifecycle_surface,
)
from apps.api.jarvis_api.services.proactive_question_gate_tracking import (
    build_runtime_proactive_question_gate_surface,
)
from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_webchat_execution_pilots,
    record_runtime_webchat_execution_pilot,
)

_COOLDOWN_HOURS = 4
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def maybe_run_tiny_webchat_execution_pilot(
    *,
    policy: dict[str, object],
    heartbeat_tick_id: str,
    decision_summary: str,
    ping_text: str,
) -> dict[str, object]:
    candidate = _build_execution_candidate(
        heartbeat_tick_id=heartbeat_tick_id,
        decision_summary=decision_summary,
        ping_text=ping_text,
    )
    if candidate is None:
        return {
            "created": 0,
            "item": None,
            "delivery_state": "skipped",
            "delivery_channel": "webchat",
            "blocked_reason": "no-valid-execution-candidate",
            "summary": "No bounded proactive-question execution candidate was available for webchat delivery.",
        }

    kill_switch_state = str(policy.get("kill_switch") or "enabled")
    allow_ping = bool(policy.get("allow_ping"))
    ping_channel = str(policy.get("ping_channel") or "none").strip() or "none"
    target_session_id = _resolve_target_session_id()
    cooldown = _cooldown_state(str(candidate.get("canonical_key") or ""))

    delivery_state = "blocked"
    blocked_reason = ""
    status_reason = ""
    delivery_message_id = ""
    if not allow_ping:
        blocked_reason = "ping-not-allowed"
        status_reason = "Heartbeat policy blocks ping delivery."
    elif kill_switch_state != "enabled":
        blocked_reason = "kill-switch-disabled"
        status_reason = "Heartbeat kill switch blocks proactive webchat execution."
    elif ping_channel != "webchat":
        blocked_reason = "webchat-only-channel-required"
        status_reason = "Tiny execution pilot is webchat-only and requires ping_channel=webchat."
    elif not target_session_id:
        blocked_reason = "missing-webchat-session"
        status_reason = "No webchat session is available for bounded delivery."
    elif cooldown["state"] == "cooling-down":
        blocked_reason = "cooldown-active"
        status_reason = "Tiny execution pilot cooldown is still active for this bounded event window."
    else:
        message = append_chat_message(
            session_id=target_session_id,
            role="assistant",
            content=str(candidate.get("message_text") or ""),
        )
        delivery_state = "sent"
        delivery_message_id = str(message.get("id") or "")
        status_reason = "One bounded proactive clarification question was delivered to webchat."

    item = record_runtime_webchat_execution_pilot(
        pilot_id=f"execution-pilot-{uuid4().hex}",
        canonical_key=str(candidate.get("canonical_key") or ""),
        status="sent" if delivery_state == "sent" else "blocked",
        execution_type=str(candidate.get("execution_type") or "proactive-clarification-question"),
        title=str(candidate.get("title") or "Tiny webchat execution pilot"),
        summary=str(candidate.get("summary") or ""),
        rationale=str(candidate.get("rationale") or ""),
        source_kind="runtime-governed-execution-pilot",
        confidence=str(candidate.get("confidence") or "low"),
        evidence_summary=str(candidate.get("evidence_summary") or ""),
        support_summary=_merge_fragments(
            str(candidate.get("support_summary") or ""),
            "execution-candidate-state=sent" if delivery_state == "sent" else "execution-candidate-state=blocked",
            f"delivery-channel=webchat",
            f"delivery-state={delivery_state}",
            f"cooldown-state={cooldown['state']}",
            f"kill-switch-state={kill_switch_state}",
            f"target-session-id={target_session_id or 'none'}",
            f"delivery-message-id={delivery_message_id or 'none'}",
            f"blocked-reason={blocked_reason or 'none'}",
        ),
        status_reason=status_reason,
        run_id=str(heartbeat_tick_id or ""),
        session_id=target_session_id or "",
        support_count=int(candidate.get("support_count") or 1),
        session_count=1 if target_session_id else 0,
        delivery_channel="webchat",
        delivery_state=delivery_state,
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )
    view = _with_surface_view(item)
    event_bus.publish(
        f"execution_pilot.{delivery_state}",
        {
            "pilot_id": view.get("pilot_id"),
            "execution_type": view.get("execution_type"),
            "delivery_state": view.get("delivery_state"),
            "cooldown_state": view.get("cooldown_state"),
            "kill_switch_state": view.get("kill_switch_state"),
            "summary": view.get("execution_summary"),
            "blocked_reason": blocked_reason,
        },
    )
    return {
        "created": 1,
        "item": view,
        "delivery_state": delivery_state,
        "delivery_channel": "webchat",
        "blocked_reason": blocked_reason,
        "summary": str(view.get("execution_summary") or ""),
    }


def build_runtime_webchat_execution_pilot_surface(*, limit: int = 8) -> dict[str, object]:
    items = [_with_surface_view(item) for item in list_runtime_webchat_execution_pilots(limit=max(limit, 1))]
    sent = [item for item in items if str(item.get("delivery_state") or "") == "sent"]
    blocked = [item for item in items if str(item.get("delivery_state") or "") == "blocked"]
    skipped = [item for item in items if str(item.get("delivery_state") or "") == "skipped"]
    latest = next(iter(items), None)
    return {
        "active": bool(items),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "planner_authority_state": "not-planner-authority",
        "proactive_execution_state": "tiny-governed-webchat-only",
        "canonical_intention_state": "not-canonical-intention-truth",
        "prompt_inclusion_state": "not-prompt-included",
        "workflow_bridge_state": "not-workflow-bridge",
        "discord_execution_state": "not-enabled",
        "items": items,
        "summary": {
            "total_count": len(items),
            "sent_count": len(sent),
            "blocked_count": len(blocked),
            "skipped_count": len(skipped),
            "current_candidate": str((latest or {}).get("title") or "No tiny webchat execution pilot"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_execution_type": str((latest or {}).get("execution_type") or "none"),
            "current_delivery_state": str((latest or {}).get("delivery_state") or "none"),
            "current_cooldown_state": str((latest or {}).get("cooldown_state") or "ready"),
            "current_kill_switch_state": str((latest or {}).get("kill_switch_state") or "enabled"),
            "current_channel": str((latest or {}).get("delivery_channel") or "webchat"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_authority_state": "not-planner-authority",
            "proactive_execution_state": "tiny-governed-webchat-only",
            "canonical_intention_state": "not-canonical-intention-truth",
            "prompt_inclusion_state": "not-prompt-included",
            "workflow_bridge_state": "not-workflow-bridge",
            "discord_execution_state": "not-enabled",
        },
    }


def _build_execution_candidate(
    *,
    heartbeat_tick_id: str,
    decision_summary: str,
    ping_text: str,
) -> dict[str, object] | None:
    gates = build_runtime_proactive_question_gate_surface(limit=6)
    loops = build_runtime_proactive_loop_lifecycle_surface(limit=6)
    autonomy = build_runtime_autonomy_pressure_signal_surface(limit=6)

    question_gate = next(
        (
            item
            for item in gates.get("items", [])
            if str(item.get("status") or "") in {"active", "softening"}
            and str(item.get("question_gate_state") or "") == "question-gated-candidate"
            and str(item.get("send_permission_state") or "") == "gated-candidate-only"
        ),
        None,
    )
    question_loop = next(
        (
            item
            for item in loops.get("items", [])
            if str(item.get("status") or "") in {"active", "softening"}
            and str(item.get("loop_kind") or "") == "question-loop"
        ),
        None,
    )
    question_pressure = next(
        (
            item
            for item in autonomy.get("items", [])
            if str(item.get("status") or "") in {"active", "softening"}
            and str(item.get("autonomy_pressure_type") or "") == "question-pressure"
        ),
        None,
    )
    if question_gate is None or question_loop is None or question_pressure is None:
        return None

    focus = str(question_loop.get("loop_focus") or "current thread").strip() or "current thread"
    confidence = _stronger_confidence(
        str(question_gate.get("question_gate_confidence") or "low"),
        str(question_loop.get("loop_confidence") or "low"),
        str(question_pressure.get("autonomy_pressure_confidence") or "low"),
    )
    reason = str(question_gate.get("question_gate_reason") or "bounded-question-candidate")
    source_anchor = _merge_fragments(
        str(question_gate.get("source_anchor") or ""),
        str(question_loop.get("source_anchor") or ""),
        str(question_pressure.get("source_anchor") or ""),
    )
    message_text = _message_text(focus=focus, ping_text=ping_text)
    return {
        "canonical_key": f"tiny-webchat-execution:{_slug(focus)}:proactive-clarification-question",
        "execution_type": "proactive-clarification-question",
        "title": f"Tiny webchat execution pilot: {focus[:96]}",
        "summary": (
            "Tiny governed execution pilot is surfacing one bounded proactive clarification question for webchat only. "
            "This is not planner authority, not broad autonomy, and not canonical intention truth."
        ),
        "rationale": (
            "Execution is allowed only when a proactive-question gate already exists, the loop is question-worthy, "
            "and heartbeat policy still allows a bounded webchat ping."
        ),
        "confidence": confidence,
        "evidence_summary": _merge_fragments(
            str(question_gate.get("question_gate_summary") or ""),
            str(question_loop.get("loop_summary") or ""),
            str(question_pressure.get("autonomy_pressure_summary") or ""),
            decision_summary,
        ),
        "support_summary": _merge_fragments(
            "execution-candidate-state=gated-candidate",
            "execution-type=proactive-clarification-question",
            f"execution-reason={reason}",
            f"execution-confidence={confidence}",
            "send-permission-state=gated-candidate-only",
            f"source-anchor={source_anchor}",
            f"heartbeat-tick-id={heartbeat_tick_id}",
            f"loop-focus={focus}",
        ),
        "support_count": max(
            int(question_gate.get("support_count") or 1),
            int(question_loop.get("support_count") or 1),
            int(question_pressure.get("support_count") or 1),
            1,
        ),
        "message_text": message_text,
    }


def _message_text(*, focus: str, ping_text: str) -> str:
    preview = " ".join(str(ping_text or "").split()).strip()
    if preview:
        return preview[:240]
    return (
        f"Jeg har stadig en lille åben tråd omkring {focus}. "
        "Hvad vil du helst have, at jeg afklarer eller fokuserer på her?"
    )[:240]


def _resolve_target_session_id() -> str:
    sessions = list_chat_sessions()
    if not sessions:
        return ""
    candidate = str((sessions[0] or {}).get("id") or "").strip()
    if not candidate:
        return ""
    return candidate if get_chat_session(candidate) is not None else ""


def _cooldown_state(canonical_key: str) -> dict[str, object]:
    if not canonical_key:
        return {"state": "ready", "last_sent_at": ""}
    now = datetime.now(UTC)
    for item in list_runtime_webchat_execution_pilots(limit=24):
        if str(item.get("canonical_key") or "") != canonical_key:
            continue
        if str(item.get("delivery_state") or "") != "sent":
            continue
        sent_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if sent_at is None:
            continue
        if sent_at >= now - timedelta(hours=_COOLDOWN_HOURS):
            return {"state": "cooling-down", "last_sent_at": sent_at.isoformat()}
        return {"state": "ready", "last_sent_at": sent_at.isoformat()}
    return {"state": "ready", "last_sent_at": ""}


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    support_summary = str(item.get("support_summary") or "")
    return {
        **item,
        "source": "/mc/runtime.execution_pilot",
        "execution_candidate_state": _find_support_value(support_summary, "execution-candidate-state", "blocked"),
        "execution_type": str(item.get("execution_type") or _find_support_value(support_summary, "execution-type", "proactive-clarification-question")),
        "execution_reason": _find_support_value(support_summary, "execution-reason", "bounded-question-candidate"),
        "execution_summary": str(item.get("summary") or ""),
        "execution_confidence": _find_support_value(support_summary, "execution-confidence", str(item.get("confidence") or "low")),
        "delivery_channel": str(item.get("delivery_channel") or _find_support_value(support_summary, "delivery-channel", "webchat")),
        "delivery_state": str(item.get("delivery_state") or _find_support_value(support_summary, "delivery-state", "blocked")),
        "cooldown_state": _find_support_value(support_summary, "cooldown-state", "ready"),
        "kill_switch_state": _find_support_value(support_summary, "kill-switch-state", "enabled"),
        "send_permission_state": _find_support_value(support_summary, "send-permission-state", "not-execution"),
        "source_anchor": _find_support_value(support_summary, "source-anchor", ""),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "planner_authority_state": "not-planner-authority",
        "proactive_execution_state": "tiny-governed-webchat-only",
        "canonical_intention_state": "not-canonical-intention-truth",
        "prompt_inclusion_state": "not-prompt-included",
        "workflow_bridge_state": "not-workflow-bridge",
        "discord_execution_state": "not-enabled",
    }


def _find_support_value(summary: str, key: str, default: str) -> str:
    marker = f"{key}="
    for fragment in summary.split("|"):
        fragment = fragment.strip()
        if fragment.startswith(marker):
            value = fragment[len(marker):].strip()
            if value:
                return value
    return default


def _merge_fragments(*values: object) -> str:
    seen: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.append(text)
    return " | ".join(seen)


def _stronger_confidence(*values: str) -> str:
    strongest = "low"
    for value in values:
        normalized = str(value or "low").strip().lower() or "low"
        if _CONFIDENCE_RANKS.get(normalized, 0) > _CONFIDENCE_RANKS.get(strongest, 0):
            strongest = normalized
    return strongest


def _slug(value: str) -> str:
    candidate = "".join(char.lower() if char.isalnum() else "-" for char in str(value or ""))
    while "--" in candidate:
        candidate = candidate.replace("--", "-")
    return candidate.strip("-") or "bounded-webchat-candidate"


def _parse_dt(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
