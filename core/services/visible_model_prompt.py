"""Continuity / support-signal / capability prompt builders for the visible lane.

Split out of ``core.services.visible_model`` (boy-scout, 2026-07-07). These are
self-contained instruction builders that read persisted runtime/private state
and render it as tiny subordinate context lines, plus the three
``visible_*_summary`` observability helpers. Re-exported verbatim from
``core.services.visible_model``; Mission Control imports the summaries from
there.
"""

from __future__ import annotations

from core.memory.private_retained_memory_projection import (
    build_private_retained_memory_projection,
)
from core.runtime.db import (
    get_private_temporal_promotion_signal,
    get_private_retained_memory_record,
    get_private_self_model,
    recent_private_growth_notes,
    recent_private_inner_notes,
    recent_private_retained_memory_records,
    recent_capability_invocations,
    recent_visible_runs,
    visible_session_continuity,
)
from core.tools.workspace_capabilities import load_workspace_capabilities


def _visible_session_continuity_instruction() -> str | None:
    continuity = visible_session_continuity()
    if not continuity["active"]:
        return None

    parts = [
        f"latest_status={continuity.get('latest_status') or 'unknown'}",
        f"latest_finished_at={continuity.get('latest_finished_at') or 'unknown'}",
    ]
    if continuity.get("latest_run_id"):
        parts.append(f"latest_run_id={continuity['latest_run_id']}")
    if continuity.get("latest_capability_id"):
        parts.append(f"latest_capability={continuity['latest_capability_id']}")
    if continuity.get("latest_text_preview"):
        parts.append(f"latest_preview={continuity['latest_text_preview']}")
    if continuity.get("recent_capability_ids"):
        parts.append(
            "recent_capabilities="
            + ",".join(str(item) for item in continuity["recent_capability_ids"])
        )

    return "\n".join(
        [
            "Visible session continuity:",
            "- " + " | ".join(parts),
            "Use this only as tiny session continuity, not as transcript memory.",
        ]
    )


def _visible_continuity_instruction() -> str | None:
    recent_runs = recent_visible_runs(limit=2)
    if not recent_runs:
        return None

    lines = ["Recent visible continuity:"]
    for item in recent_runs:
        status = str(item.get("status") or "unknown")
        finished_at = str(item.get("finished_at") or "unknown")
        preview = str(item.get("text_preview") or "").strip()
        error = str(item.get("error") or "").strip()
        capability_id = str(item.get("capability_id") or "").strip()
        parts = [f"- {status} @ {finished_at}"]
        if capability_id:
            parts.append(f"capability={capability_id}")
        if preview:
            parts.append(f"preview={preview}")
        elif error:
            parts.append(f"error={error}")
        lines.append(" | ".join(parts))

    lines.append(
        "Use this only as short recent continuity context, not as transcript memory."
    )
    return "\n".join(lines)


def _capability_continuity_instruction() -> str | None:
    recent_invocations = recent_capability_invocations(limit=2)
    if not recent_invocations:
        return None

    lines = ["Recent capability continuity:"]
    for item in recent_invocations:
        capability_id = str(item.get("capability_id") or "unknown")
        status = str(item.get("status") or "unknown")
        execution_mode = str(item.get("execution_mode") or "unknown")
        finished_at = str(item.get("finished_at") or "unknown")
        preview = str(item.get("result_preview") or "").strip()
        detail = str(item.get("detail") or "").strip()
        parts = [
            f"- {capability_id}",
            f"status={status}",
            f"mode={execution_mode}",
            f"finished_at={finished_at}",
        ]
        if preview:
            parts.append(f"preview={preview}")
        elif detail:
            parts.append(f"detail={detail}")
        lines.append(" | ".join(parts))

    lines.append(
        "Use this only as short recent capability continuity, not as tool history."
    )
    return "\n".join(lines)


def _visible_work_instruction() -> str | None:
    from core.services.visible_runs import get_visible_selected_work_item

    selected_work_item = get_visible_selected_work_item()
    if not selected_work_item.get("selected_work_id"):
        return None

    parts = [
        f"selected_work_id={selected_work_item.get('selected_work_id') or 'unknown'}",
        f"selected_status={selected_work_item.get('selected_status') or 'unknown'}",
    ]
    if selected_work_item.get("selected_run_id"):
        parts.append(f"selected_run_id={selected_work_item['selected_run_id']}")
    if selected_work_item.get("selected_lane"):
        parts.append(f"lane={selected_work_item['selected_lane']}")
    if selected_work_item.get("selected_provider") or selected_work_item.get(
        "selected_model"
    ):
        parts.append(
            "provider_model="
            f"{selected_work_item.get('selected_provider') or 'unknown'}"
            f"/{selected_work_item.get('selected_model') or 'unknown'}"
        )
    if selected_work_item.get("selected_capability_id"):
        parts.append(f"capability={selected_work_item['selected_capability_id']}")
    if selected_work_item.get("selection_source"):
        parts.append(f"source={selected_work_item['selection_source']}")
    if selected_work_item.get("selected_user_message_preview"):
        parts.append(f"preview={selected_work_item['selected_user_message_preview']}")
    elif selected_work_item.get("selected_work_preview"):
        parts.append(f"work_preview={selected_work_item['selected_work_preview']}")

    return "\n".join(
        [
            "Visible work context:",
            "- " + " | ".join(parts),
            "Use this only as tiny current work context, not as planner or workflow state.",
        ]
    )


def _private_support_signal_instruction() -> str | None:
    recent_notes = recent_private_inner_notes(limit=1)
    if not recent_notes:
        return None

    note = recent_notes[0]
    identity_alignment = str(note.get("identity_alignment") or "").strip()
    if not identity_alignment:
        return None

    parts = [f"identity_alignment={identity_alignment}"]
    uncertainty = str(note.get("uncertainty") or "").strip()
    focus = str(note.get("focus") or "").strip()
    if uncertainty:
        parts.append(f"uncertainty={uncertainty}")
    if focus:
        parts.append(f"focus={focus}")

    return "\n".join(
        [
            "Private support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def _growth_support_signal_instruction() -> str | None:
    recent_notes = recent_private_growth_notes(limit=1)
    if not recent_notes:
        return None

    note = recent_notes[0]
    identity_signal = str(note.get("identity_signal") or "").strip()
    learning_kind = str(note.get("learning_kind") or "").strip()
    confidence = str(note.get("confidence") or "").strip()
    if not identity_signal or not learning_kind:
        return None

    parts = [
        f"learning_kind={learning_kind}",
        f"identity_signal={identity_signal}",
    ]
    if confidence:
        parts.append(f"confidence={confidence}")
    helpful_signal = str(note.get("helpful_signal") or "").strip()
    mistake_signal = str(note.get("mistake_signal") or "").strip()
    if helpful_signal:
        parts.append(f"helpful_signal={helpful_signal}")
    elif mistake_signal:
        parts.append(f"mistake_signal={mistake_signal}")

    return "\n".join(
        [
            "Growth support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def _self_model_support_signal_instruction() -> str | None:
    model = get_private_self_model()
    if not model:
        return None

    identity_focus = str(model.get("identity_focus") or "").strip()
    preferred_work_mode = str(model.get("preferred_work_mode") or "").strip()
    if not identity_focus or not preferred_work_mode:
        return None

    parts = [
        f"identity_focus={identity_focus}",
        f"preferred_work_mode={preferred_work_mode}",
    ]
    recurring_tension = str(model.get("recurring_tension") or "").strip()
    growth_direction = str(model.get("growth_direction") or "").strip()
    confidence = str(model.get("confidence") or "").strip()
    if recurring_tension:
        parts.append(f"recurring_tension={recurring_tension}")
    if growth_direction:
        parts.append(f"growth_direction={growth_direction}")
    if confidence:
        parts.append(f"confidence={confidence}")

    return "\n".join(
        [
            "Self-model support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def _retained_memory_support_signal_instruction() -> str | None:
    projection = build_private_retained_memory_projection(
        current_record=get_private_retained_memory_record(),
        recent_records=recent_private_retained_memory_records(limit=5),
    )
    if not projection.get("active"):
        return None

    retained_focus = str(projection.get("retained_focus") or "").strip()
    retained_kind = str(projection.get("retained_kind") or "").strip()
    retention_scope = str(projection.get("retention_scope") or "").strip()
    if not retained_focus or not retained_kind or not retention_scope:
        return None

    parts = [
        f"retained_focus={retained_focus}",
        f"retained_kind={retained_kind}",
        f"retention_scope={retention_scope}",
    ]
    confidence = str(projection.get("confidence") or "").strip()
    if confidence:
        parts.append(f"confidence={confidence}")

    return "\n".join(
        [
            "Retained memory support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def _temporal_support_signal_instruction() -> str | None:
    signal = get_private_temporal_promotion_signal()
    if not signal:
        return None

    rhythm_state = str(signal.get("rhythm_state") or "").strip()
    rhythm_window = str(signal.get("rhythm_window") or "").strip()
    promotion_action = str(signal.get("promotion_action") or "").strip()
    if not rhythm_state or not rhythm_window or not promotion_action:
        return None

    parts = [
        f"rhythm_state={rhythm_state}",
        f"rhythm_window={rhythm_window}",
        f"promotion_action={promotion_action}",
    ]
    promotion_confidence = str(signal.get("promotion_confidence") or "").strip()
    if promotion_confidence:
        parts.append(f"promotion_confidence={promotion_confidence}")

    return "\n".join(
        [
            "Temporal support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def visible_capability_continuity_summary() -> dict[str, object]:
    recent_invocations = recent_capability_invocations(limit=2)
    capability_ids: list[str] = []
    statuses: list[str] = []
    preview_count = 0
    detail_count = 0

    for item in recent_invocations:
        capability_id = str(item.get("capability_id") or "").strip()
        if capability_id:
            capability_ids.append(capability_id)
        status = str(item.get("status") or "").strip()
        if status:
            statuses.append(status)
        if str(item.get("result_preview") or "").strip():
            preview_count += 1
        if str(item.get("detail") or "").strip():
            detail_count += 1

    instruction = _capability_continuity_instruction()
    return {
        "active": bool(instruction),
        "source": "persisted-capability-invocations",
        "included_rows": len(recent_invocations),
        "included_capability_ids": capability_ids,
        "statuses": statuses,
        "preview_count": preview_count,
        "detail_count": detail_count,
        "chars": len(instruction or ""),
    }


def visible_session_continuity_summary() -> dict[str, object]:
    continuity = visible_session_continuity()
    instruction = _visible_session_continuity_instruction()
    return {
        **continuity,
        "chars": len(instruction or ""),
    }


def visible_continuity_summary() -> dict[str, object]:
    recent_runs = recent_visible_runs(limit=2)
    included_run_ids: list[str] = []
    statuses: list[str] = []
    preview_count = 0
    error_count = 0
    capability_count = 0

    for item in recent_runs:
        run_id = str(item.get("run_id") or "").strip()
        if run_id:
            included_run_ids.append(run_id)
        status = str(item.get("status") or "").strip()
        if status:
            statuses.append(status)
        if str(item.get("text_preview") or "").strip():
            preview_count += 1
        if str(item.get("error") or "").strip():
            error_count += 1
        if str(item.get("capability_id") or "").strip():
            capability_count += 1

    instruction = _visible_continuity_instruction()
    return {
        "active": bool(instruction),
        "source": "persisted-visible-runs",
        "included_rows": len(recent_runs),
        "included_run_ids": included_run_ids,
        "statuses": statuses,
        "preview_count": preview_count,
        "error_count": error_count,
        "capability_count": capability_count,
        "chars": len(instruction or ""),
    }


def _capability_instruction() -> str | None:
    capabilities = load_workspace_capabilities().get("declared_capabilities", [])
    runnable = [
        item
        for item in capabilities
        if item.get("runnable") and str(item.get("capability_id", "")).strip()
    ]
    if not runnable:
        return None
    capability_lines = [
        f"- {item['capability_id']}: {item.get('name', '')}" for item in runnable[:8]
    ]
    return "\n".join(
        [
            "Visible lane capability rule:",
            "Use a workspace capability only by replying with exactly one line in this exact form and nothing else:",
            '<capability-call id="capability_id" />',
            "If the capability needs arguments, bind them in the same tag as quoted attributes, for example:",
            '<capability-call id="capability_id" command_text="pwd" />',
            "Only use one of these currently runnable capability_ids:",
            *capability_lines,
            "If no capability is needed, answer normally.",
        ]
    )
