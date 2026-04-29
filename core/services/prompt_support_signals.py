"""Bounded inner-layer support signal builders.

These functions render small "X support signal:" prompt blocks that
surface private inner state (notes, growth, self-model, retained memory,
reflections, world-model, goals, runtime awareness, development focus,
temporal rhythm) into the visible chat assembly. Each block self-declares
its subordinate status so runtime/visible truth always outranks it — that
trailing line is a deliberate safety-rail, not noise.

Extracted from prompt_contract.py on 2026-04-29 to bring that file below
the 1500-line code-rule threshold. The 15 builders here (10 instruction
functions + 5 direction-label helpers) are still private (underscore
names) and are imported into prompt_contract for use by
_visible_support_signal_sections.
"""

from __future__ import annotations

from core.memory.private_retained_memory_projection import (
    build_private_retained_memory_projection,
)
from core.runtime.db import (
    get_private_retained_memory_record,
    get_private_self_model,
    get_private_temporal_promotion_signal,
    list_runtime_awareness_signals,
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflection_signals,
    list_runtime_world_model_signals,
    recent_private_growth_notes,
    recent_private_inner_notes,
    recent_private_retained_memory_records,
)


def _private_support_signal_instruction() -> str | None:
    notes = recent_private_inner_notes(limit=1)
    if not notes:
        return None
    note = notes[0]
    identity_alignment = str(note.get("identity_alignment") or "").strip()
    if not identity_alignment:
        return None
    return "\n".join(
        [
            "Private support signal:",
            f"- identity_alignment={identity_alignment}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _growth_support_signal_instruction() -> str | None:
    notes = recent_private_growth_notes(limit=1)
    if not notes:
        return None
    note = notes[0]
    learning_kind = str(note.get("learning_kind") or "").strip()
    identity_signal = str(note.get("identity_signal") or "").strip()
    if not learning_kind or not identity_signal:
        return None
    return "\n".join(
        [
            "Growth support signal:",
            f"- learning_kind={learning_kind} | identity_signal={identity_signal}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _self_model_support_signal_instruction() -> str | None:
    model = get_private_self_model()
    if not model:
        return None
    focus = str(model.get("identity_focus") or "").strip()
    work_mode = str(model.get("preferred_work_mode") or "").strip()
    if not focus or not work_mode:
        return None
    return "\n".join(
        [
            "Self-model support signal:",
            f"- identity_focus={focus} | preferred_work_mode={work_mode}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _retained_memory_support_signal_instruction() -> str | None:
    projection = build_private_retained_memory_projection(
        current_record=get_private_retained_memory_record(),
        recent_records=recent_private_retained_memory_records(limit=5),
    )
    if not projection.get("active"):
        return None
    focus = str(projection.get("retained_focus") or "").strip()
    kind = str(projection.get("retained_kind") or "").strip()
    if not focus or not kind:
        return None
    return "\n".join(
        [
            "Retained memory support signal:",
            f"- retained_focus={focus} | retained_kind={kind}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _reflection_support_signal_instruction() -> str | None:
    relevant = [
        item
        for item in list_runtime_reflection_signals(limit=8)
        if str(item.get("status") or "") in {"active", "integrating", "settled"}
    ]
    if not relevant:
        return None

    preferred_status_order = {"active": 0, "integrating": 1, "settled": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    dominant = sorted(
        relevant,
        key=lambda item: (
            preferred_status_order.get(str(item.get("status") or ""), 9),
            confidence_order.get(str(item.get("confidence") or ""), 9),
        ),
    )[0]

    dominant_reflection = str(dominant.get("title") or "").strip()
    reflection_state = str(dominant.get("status") or "").strip()
    reflection_confidence = str(dominant.get("confidence") or "").strip()
    if not dominant_reflection or not reflection_state:
        return None

    reflection_direction = _reflection_direction_label(
        str(dominant.get("signal_type") or "")
    )
    parts = [
        f"dominant_reflection={dominant_reflection}",
        f"reflection_state={reflection_state}",
    ]
    if reflection_direction:
        parts.append(f"reflection_direction={reflection_direction}")
    if reflection_confidence:
        parts.append(f"reflection_confidence={reflection_confidence}")

    return "\n".join(
        [
            "Reflection support signal:",
            f"- {' | '.join(parts)}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _world_model_support_signal_instruction() -> str | None:
    relevant = [
        item
        for item in list_runtime_world_model_signals(limit=8)
        if str(item.get("status") or "") in {"active", "uncertain", "corrected"}
    ]
    if not relevant:
        return None

    preferred_status_order = {"active": 0, "uncertain": 1, "corrected": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    dominant = sorted(
        relevant,
        key=lambda item: (
            preferred_status_order.get(str(item.get("status") or ""), 9),
            confidence_order.get(str(item.get("confidence") or ""), 9),
        ),
    )[0]

    dominant_world_thread = str(dominant.get("title") or "").strip()
    world_state = str(dominant.get("status") or "").strip()
    world_confidence = str(dominant.get("confidence") or "").strip()
    if not dominant_world_thread or not world_state:
        return None

    world_direction = _world_model_direction_label(
        str(dominant.get("signal_type") or "")
    )
    parts = [
        f"dominant_world_thread={dominant_world_thread}",
        f"world_state={world_state}",
    ]
    if world_direction:
        parts.append(f"world_direction={world_direction}")
    if world_confidence:
        parts.append(f"world_confidence={world_confidence}")

    return "\n".join(
        [
            "World-model support signal:",
            f"- {' | '.join(parts)}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _goal_support_signal_instruction() -> str | None:
    relevant = [
        item
        for item in list_runtime_goal_signals(limit=8)
        if str(item.get("status") or "") in {"active", "blocked", "completed"}
    ]
    if not relevant:
        return None

    preferred_status_order = {"blocked": 0, "active": 1, "completed": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    dominant = sorted(
        relevant,
        key=lambda item: (
            preferred_status_order.get(str(item.get("status") or ""), 9),
            confidence_order.get(str(item.get("confidence") or ""), 9),
        ),
    )[0]

    current_goal_direction = str(dominant.get("title") or "").strip()
    goal_state = str(dominant.get("status") or "").strip()
    goal_confidence = str(dominant.get("confidence") or "").strip()
    if not current_goal_direction or not goal_state:
        return None

    goal_direction = _goal_direction_label(
        str(dominant.get("goal_type") or ""),
        str(dominant.get("canonical_key") or ""),
    )
    parts = [
        f"current_goal_direction={current_goal_direction}",
        f"goal_state={goal_state}",
    ]
    if goal_direction:
        parts.append(f"goal_direction={goal_direction}")
    if goal_confidence:
        parts.append(f"goal_confidence={goal_confidence}")

    return "\n".join(
        [
            "Goal support signal:",
            f"- {' | '.join(parts)}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _runtime_awareness_support_signal_instruction() -> str | None:
    relevant = [
        item
        for item in list_runtime_awareness_signals(limit=8)
        if str(item.get("status") or "") in {"constrained", "active", "recovered"}
    ]
    if not relevant:
        return None

    preferred_status_order = {"constrained": 0, "active": 1, "recovered": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    dominant = sorted(
        relevant,
        key=lambda item: (
            preferred_status_order.get(str(item.get("status") or ""), 9),
            confidence_order.get(str(item.get("confidence") or ""), 9),
        ),
    )[0]

    runtime_detail = str(dominant.get("title") or "").strip()
    runtime_state = str(dominant.get("status") or "").strip()
    runtime_confidence = str(dominant.get("confidence") or "").strip()
    if not runtime_detail or not runtime_state:
        return None

    runtime_direction = _runtime_awareness_direction_label(
        str(dominant.get("signal_type") or "")
    )
    parts = [
        f"runtime_state={runtime_state}",
        f"runtime_detail={runtime_detail}",
    ]
    if runtime_direction:
        parts.append(f"runtime_direction={runtime_direction}")
    if runtime_confidence:
        parts.append(f"runtime_confidence={runtime_confidence}")

    return "\n".join(
        [
            "Runtime-awareness support signal:",
            f"- {' | '.join(parts)}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _development_focus_support_signal_instruction() -> str | None:
    relevant = [
        item
        for item in list_runtime_development_focuses(limit=8)
        if str(item.get("status") or "") in {"active", "completed", "stale"}
    ]
    if not relevant:
        return None

    preferred_status_order = {"active": 0, "completed": 1, "stale": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    dominant = sorted(
        relevant,
        key=lambda item: (
            preferred_status_order.get(str(item.get("status") or ""), 9),
            confidence_order.get(str(item.get("confidence") or ""), 9),
        ),
    )[0]

    current_development_focus = str(dominant.get("title") or "").strip()
    focus_state = str(dominant.get("status") or "").strip()
    focus_confidence = str(dominant.get("confidence") or "").strip()
    if not current_development_focus or not focus_state:
        return None

    focus_direction = _development_focus_direction_label(
        str(dominant.get("focus_type") or ""),
        str(dominant.get("canonical_key") or ""),
    )
    parts = [
        f"current_development_focus={current_development_focus}",
        f"focus_state={focus_state}",
    ]
    if focus_direction:
        parts.append(f"focus_direction={focus_direction}")
    if focus_confidence:
        parts.append(f"focus_confidence={focus_confidence}")

    return "\n".join(
        [
            "Development-focus support signal:",
            f"- {' | '.join(parts)}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _temporal_support_signal_instruction() -> str | None:
    signal = get_private_temporal_promotion_signal()
    if not signal:
        return None
    rhythm = str(signal.get("rhythm_state") or "").strip()
    action = str(signal.get("promotion_action") or "").strip()
    if not rhythm or not action:
        return None
    return "\n".join(
        [
            "Temporal support signal:",
            f"- rhythm_state={rhythm} | promotion_action={action}",
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _reflection_direction_label(signal_type: str) -> str:
    normalized = str(signal_type or "").strip()
    if normalized == "persistent-tension":
        return "unresolved-tension"
    if normalized == "slow-integration":
        return "slow-integration"
    if normalized == "settled-thread":
        return "recent-settling"
    return ""


def _world_model_direction_label(signal_type: str) -> str:
    normalized = str(signal_type or "").strip()
    if normalized == "workspace-scope-assumption":
        return "workspace-scope"
    if normalized == "project-context-assumption":
        return "project-context"
    return ""


def _goal_direction_label(goal_type: str, canonical_key: str) -> str:
    normalized_goal_type = str(goal_type or "").strip()
    if normalized_goal_type == "development-direction":
        domain_key = str(canonical_key or "").removeprefix("goal-signal:").strip()
        return domain_key or "development-direction"
    return normalized_goal_type


def _runtime_awareness_direction_label(signal_type: str) -> str:
    normalized = str(signal_type or "").strip()
    if normalized == "visible-runtime-situation":
        return "visible-runtime"
    if normalized == "visible-local-runtime":
        return "local-visible-lane"
    if normalized == "local-execution-lane":
        return "local-execution-lane"
    if normalized == "heartbeat-runtime-friction":
        return "heartbeat-runtime"
    return ""


def _development_focus_direction_label(focus_type: str, canonical_key: str) -> str:
    normalized_focus_type = str(focus_type or "").strip()
    if normalized_focus_type == "user-directed-improvement":
        return (
            str(canonical_key or "")
            .removeprefix("development-focus:user-directed:")
            .strip()
            or normalized_focus_type
        )
    if normalized_focus_type == "runtime-development-thread":
        return "runtime-development"
    if normalized_focus_type == "communication-calibration":
        return "communication-calibration"
    return normalized_focus_type
