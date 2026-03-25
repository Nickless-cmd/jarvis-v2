from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apps.api.jarvis_api.services.chat_sessions import recent_chat_session_messages
from core.identity.visible_identity import load_visible_identity_prompt
from core.identity.runtime_contract import build_runtime_contract_state
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.memory.private_retained_memory_projection import (
    build_private_retained_memory_projection,
)
from core.runtime.db import (
    get_private_temporal_promotion_signal,
    get_private_retained_memory_record,
    get_private_self_model,
    list_runtime_reflection_signals,
    list_runtime_world_model_signals,
    recent_private_growth_notes,
    recent_private_inner_notes,
    recent_private_retained_memory_records,
    recent_visible_runs,
    visible_session_continuity,
)
from core.tools.workspace_capabilities import load_workspace_capabilities

DEFAULT_EXCLUDED_FILES = (
    "runtime/RUNTIME_FEEDBACK.md",
    "raw private/internal dumps",
)


@dataclass(slots=True)
class PromptAssembly:
    mode: str
    text: str
    included_files: list[str]
    conditional_files: list[str]
    derived_inputs: list[str]
    excluded_files: list[str]


def build_visible_chat_prompt_assembly(
    *,
    provider: str,
    model: str,
    user_message: str,
    session_id: str | None = None,
    name: str = "default",
) -> PromptAssembly:
    compact = provider == "ollama"
    workspace_dir = ensure_default_workspace(name=name)
    parts: list[str] = []
    included_files: list[str] = []
    conditional_files: list[str] = []
    derived_inputs: list[str] = []
    excluded_files = ["BOOTSTRAP.md", "HEARTBEAT.md", *DEFAULT_EXCLUDED_FILES]

    capability_truth = _visible_capability_truth_instruction(compact=compact)
    if capability_truth:
        parts.append(capability_truth)
        derived_inputs.append("runtime capability and safety truth")

    if compact:
        local_rules = _local_model_behavior_instruction()
        if local_rules:
            parts.append(local_rules)
            derived_inputs.append("local model behavior guardrails")
        identity_prompt = load_visible_identity_prompt(name=name)
        if identity_prompt:
            parts.append(identity_prompt)
            included_files.extend(["SOUL.md", "IDENTITY.md", "USER.md"])
    else:
        for filename in ("SOUL.md", "IDENTITY.md", "USER.md"):
            section = _workspace_file_section(
                workspace_dir / filename,
                label=filename,
                max_lines=5,
                max_chars=340,
            )
            if section:
                parts.append(section)
                included_files.append(filename)

    if _should_include_memory(user_message, mode="visible_chat"):
        memory_section = _workspace_file_section(
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            max_lines=3 if compact else 4,
            max_chars=200 if compact else 280,
        )
        if memory_section:
            parts.append(memory_section)
            conditional_files.append("MEMORY.md")

    if _should_include_guidance(user_message):
        for filename in ("TOOLS.md", "SKILLS.md"):
            section = _workspace_guidance_section(
                workspace_dir / filename,
                label=filename,
                max_lines=2 if compact else 3,
                max_chars=180 if compact else 240,
            )
            if section:
                parts.append(section)
                conditional_files.append(filename)

    session_continuity = _visible_session_continuity_instruction()
    if session_continuity and (not compact or _should_include_continuity(user_message)):
        parts.append(session_continuity)
        derived_inputs.append("bounded session continuity")

    support_sections = _visible_support_signal_sections(
        compact=compact,
        include=(not compact) or _should_include_memory(user_message, mode="visible_chat"),
    )
    if support_sections:
        parts.extend(support_sections)
        derived_inputs.append("bounded runtime support signals")

    transcript = _recent_transcript_section(
        session_id,
        limit=5 if compact else 8,
        include=(not compact) or _should_include_transcript(user_message),
    )
    if transcript:
        parts.append(transcript)
        derived_inputs.append("recent transcript slice")

    return PromptAssembly(
        mode="visible_chat",
        text="\n\n".join(part for part in parts if part).strip(),
        included_files=included_files,
        conditional_files=conditional_files,
        derived_inputs=derived_inputs,
        excluded_files=excluded_files,
    )


def build_heartbeat_prompt_assembly(
    *,
    heartbeat_context: dict[str, object] | None = None,
    name: str = "default",
) -> PromptAssembly:
    workspace_dir = ensure_default_workspace(name=name)
    contract = build_runtime_contract_state(name=name)
    parts: list[str] = []
    included_files: list[str] = []
    conditional_files: list[str] = []
    derived_inputs: list[str] = []
    excluded_files = ["runtime/RUNTIME_FEEDBACK.md", "boredom_templates.json", "full transcript", "heavy private/internal dumps"]

    parts.append(_heartbeat_runtime_truth_instruction(heartbeat_context or {}))
    derived_inputs.append("runtime heartbeat policy, schedule, and budget truth")

    if contract.get("bootstrap", {}).get("status") == "active":
        bootstrap = _workspace_file_section(
            workspace_dir / "BOOTSTRAP.md",
            label="BOOTSTRAP.md",
            max_lines=4,
            max_chars=260,
        )
        if bootstrap:
            parts.append(bootstrap)
            conditional_files.append("BOOTSTRAP.md")

    for filename in ("HEARTBEAT.md", "SOUL.md", "IDENTITY.md", "USER.md"):
        section = _workspace_file_section(
            workspace_dir / filename,
            label=filename,
            max_lines=4,
            max_chars=260,
        )
        if section:
            parts.append(section)
            included_files.append(filename)

    if _should_include_memory("heartbeat", mode="heartbeat"):
        memory_section = _workspace_file_section(
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            max_lines=4,
            max_chars=260,
        )
        if memory_section:
            parts.append(memory_section)
            conditional_files.append("MEMORY.md")

    due_summary = _heartbeat_due_summary(heartbeat_context or {})
    if due_summary:
        parts.append(due_summary)
        derived_inputs.append("due schedules and open-loop summary")

    capability_truth = _heartbeat_capability_truth_instruction(heartbeat_context or {})
    if capability_truth:
        parts.append(capability_truth)
        derived_inputs.append("compact capability truth")

    continuity = _heartbeat_continuity_summary(heartbeat_context or {})
    if continuity:
        parts.append(continuity)
        derived_inputs.append("optional compact continuity summary")

    return PromptAssembly(
        mode="heartbeat",
        text="\n\n".join(part for part in parts if part).strip(),
        included_files=included_files,
        conditional_files=conditional_files,
        derived_inputs=derived_inputs,
        excluded_files=excluded_files,
    )


def build_future_agent_task_prompt_assembly(
    *,
    task_brief: str,
    agent_context: dict[str, object] | None = None,
    name: str = "default",
) -> PromptAssembly:
    workspace_dir = ensure_default_workspace(name=name)
    context = agent_context or {}
    parts: list[str] = []
    included_files: list[str] = []
    conditional_files: list[str] = []
    derived_inputs: list[str] = []
    excluded_files = ["BOOTSTRAP.md", "HEARTBEAT.md", *DEFAULT_EXCLUDED_FILES, "full transcript"]

    runtime_truth = _future_agent_runtime_truth_instruction(context)
    if runtime_truth:
        parts.append(runtime_truth)
        derived_inputs.append("runtime role, scope, and capability truth")

    for filename in ("SOUL.md", "IDENTITY.md"):
        section = _workspace_file_section(
            workspace_dir / filename,
            label=filename,
            max_lines=4,
            max_chars=260,
        )
        if section:
            parts.append(section)
            included_files.append(filename)

    if context.get("include_user", True):
        user_section = _workspace_file_section(
            workspace_dir / "USER.md",
            label="USER.md",
            max_lines=3,
            max_chars=220,
        )
        if user_section:
            parts.append(user_section)
            conditional_files.append("USER.md")

    parts.append(
        "\n".join(
            [
                "Delegated task brief:",
                f"- {str(task_brief or '').strip() or 'No task brief provided.'}",
            ]
        )
    )

    if _should_include_memory(task_brief, mode="future_agent_task"):
        memory_section = _workspace_file_section(
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            max_lines=4,
            max_chars=240,
        )
        if memory_section:
            parts.append(memory_section)
            conditional_files.append("MEMORY.md")

    if _should_include_guidance(task_brief) or context.get("include_guidance"):
        for filename in ("TOOLS.md", "SKILLS.md"):
            section = _workspace_guidance_section(
                workspace_dir / filename,
                label=filename,
                max_lines=3,
                max_chars=220,
            )
            if section:
                parts.append(section)
                conditional_files.append(filename)

    continuity = _delegated_continuity_summary(context)
    if continuity:
        parts.append(continuity)
        derived_inputs.append("bounded delegated continuity")

    return PromptAssembly(
        mode="future_agent_task",
        text="\n\n".join(part for part in parts if part).strip(),
        included_files=included_files,
        conditional_files=conditional_files,
        derived_inputs=derived_inputs,
        excluded_files=excluded_files,
    )


def _workspace_file_section(
    path: Path,
    *,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    if not path.exists():
        return None
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        normalized = " ".join(line.split())
        if len(normalized) > max_chars:
            normalized = normalized[: max_chars - 1].rstrip() + "…"
        lines.append(f"- {normalized}")
        if len(lines) >= max_lines:
            break
    if not lines:
        return None
    return "\n".join([f"{label}:", *lines])


def _workspace_guidance_section(
    path: Path,
    *,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    section = _workspace_file_section(
        path,
        label=f"{label} guidance (not authority)",
        max_lines=max_lines,
        max_chars=max_chars,
    )
    if not section:
        return None
    return "\n".join(
        [
            section,
            "- These notes guide usage and workspace conventions only.",
            "- Runtime capability truth decides what is actually available now.",
        ]
    )


def _visible_capability_truth_instruction(*, compact: bool) -> str | None:
    capability_truth = load_workspace_capabilities()
    capabilities = capability_truth.get("runtime_capabilities", [])
    available = [
        item
        for item in capabilities
        if item.get("available_now") and str(item.get("capability_id") or "").strip()
    ]
    gated = [
        item
        for item in capabilities
        if item.get("runtime_status") == "approval-required"
    ]
    lines = [
        "Runtime capability truth:",
        "- Runtime capability and policy truth outrank TOOLS.md and SKILLS.md guidance notes.",
        "- TOOLS.md and SKILLS.md may describe conventions or hints only; file presence does not prove real execution authority.",
    ]
    if available:
        lines.append(
            "- Use a workspace capability only by replying with exactly one line in this form: "
            '<capability-call id="capability_id" />'
        )
        lines.append("- Currently available capability_ids:")
        limit = 4 if compact else 8
        for item in available[:limit]:
            lines.append(f'  - {item["capability_id"]}: {item.get("name", "")}')
    else:
        lines.append("- No workspace capabilities are currently available for direct execution.")
    if gated:
        lines.append(
            f"- Approval-gated capabilities currently known to runtime: {min(len(gated), 6)} shown below."
        )
        for item in gated[:6]:
            lines.append(f'  - {item["capability_id"]}: approval required')
    return "\n".join(lines)


def _local_model_behavior_instruction() -> str:
    return "\n".join(
        [
            "Visible local-model behavior rules:",
            "- Answer the latest user request first and do not add ceremonial framing.",
            "- Keep replies short and direct unless the user asks for detail.",
            "- Reply in the same language as the latest user message. If the user writes Danish, reply in Danish.",
            "- Do not translate your answer into another language unless the user explicitly asks for translation.",
            "- Follow user corrections immediately and visibly.",
            "- If the user asks for one word or a very short answer, output only that answer.",
            "- Do not explain your rules, context, or reasoning unless the user explicitly asks.",
            "- Do not add notes, translations, parenthetical meta-comments, or commentary about following instructions.",
            "- Do not repeat self-descriptions, identity boilerplate, or greeting formulas unless directly relevant.",
            "- Do not mention being a persistent digital entity unless the user asks about identity or architecture.",
        ]
    )


def _heartbeat_capability_truth_instruction(context: dict[str, object]) -> str | None:
    allowed = context.get("allowed_capabilities") or []
    lines = [
        "Heartbeat capability truth:",
        "- Runtime scope and budget decide what heartbeat may actually do.",
        "- Guidance files may describe options, but they do not grant execution authority.",
    ]
    if allowed:
        lines.append("- Allowed capability_ids:")
        for item in list(allowed)[:6]:
            lines.append(f"  - {item}")
    else:
        lines.append("- No active heartbeat capability scope is currently granted.")
    return "\n".join(lines)


def _future_agent_runtime_truth_instruction(context: dict[str, object]) -> str:
    role = str(context.get("role") or "delegated-agent")
    scope = str(context.get("scope") or "bounded")
    budget = str(context.get("budget") or "runtime-governed")
    provider = str(context.get("provider") or "runtime-selected")
    return "\n".join(
        [
            "Future agent runtime truth:",
            f"- role={role} | scope={scope} | budget={budget} | provider={provider}",
            "- Runtime capability and policy truth outrank workspace notes or prompt claims.",
            "- TOOLS.md and SKILLS.md are guidance only and do not authorize execution.",
        ]
    )


def _heartbeat_runtime_truth_instruction(context: dict[str, object]) -> str:
    schedule = str(context.get("schedule_status") or "not-configured")
    budget = str(context.get("budget_status") or "runtime-governed")
    kill_switch = str(context.get("kill_switch") or "enabled")
    return "\n".join(
        [
            "Heartbeat runtime truth:",
            f"- schedule={schedule} | budget={budget} | kill_switch={kill_switch}",
            "- Heartbeat may only propose or act within runtime-approved scope.",
        ]
    )


def _heartbeat_due_summary(context: dict[str, object]) -> str:
    due = context.get("due_items") or []
    open_loops = context.get("open_loops") or []
    recent_events = context.get("recent_events") or []
    lines = ["Heartbeat due summary:"]
    if due:
        for item in list(due)[:4]:
            lines.append(f"- due: {item}")
    if open_loops:
        for item in list(open_loops)[:3]:
            lines.append(f"- open-loop: {item}")
    if recent_events:
        for item in list(recent_events)[:3]:
            lines.append(f"- event: {item}")
    if len(lines) == 1:
        lines.append("- No due schedule items or open loops are currently recorded.")
    return "\n".join(lines)


def _heartbeat_continuity_summary(context: dict[str, object]) -> str | None:
    continuity = context.get("continuity_summary")
    if continuity:
        return "\n".join(
            [
                "Heartbeat continuity summary:",
                f"- {continuity}",
            ]
        )
    session = visible_session_continuity()
    if not session.get("active"):
        return None
    preview = str(session.get("latest_text_preview") or "").strip()
    if not preview:
        return None
    return "\n".join(
        [
            "Heartbeat continuity summary:",
            f"- latest_visible_preview={preview}",
        ]
    )


def _visible_session_continuity_instruction() -> str | None:
    continuity = visible_session_continuity()
    if not continuity["active"]:
        return None
    parts = [
        f"latest_status={continuity.get('latest_status') or 'unknown'}",
        f"latest_finished_at={continuity.get('latest_finished_at') or 'unknown'}",
    ]
    if continuity.get("latest_capability_id"):
        parts.append(f"latest_capability={continuity['latest_capability_id']}")
    if continuity.get("latest_text_preview"):
        parts.append(f"latest_preview={continuity['latest_text_preview']}")
    return "\n".join(
        [
            "Visible session continuity:",
            "- " + " | ".join(parts),
            "Use this only as tiny session continuity, not as transcript memory.",
        ]
    )


def _recent_transcript_section(
    session_id: str | None,
    *,
    limit: int,
    include: bool,
) -> str | None:
    if not session_id or not include:
        return None
    history = recent_chat_session_messages(session_id, limit=max(limit + 1, 1))
    if not history:
        return None
    lines = ["Recent transcript slice:"]
    for item in history[-limit:]:
        role = "User" if item["role"] == "user" else "Jarvis"
        content = " ".join(str(item.get("content") or "").split())
        if len(content) > 180:
            content = content[:179].rstrip() + "…"
        lines.append(f"- {role}: {content}")
    lines.append("Use this as recent transcript context, not as stable memory.")
    return "\n".join(lines)


def _visible_support_signal_sections(*, compact: bool, include: bool) -> list[str]:
    if not include:
        return []
    sections: list[str] = []

    if compact:
        return sections

    for builder in (
        _private_support_signal_instruction,
        _growth_support_signal_instruction,
        _self_model_support_signal_instruction,
        _world_model_support_signal_instruction,
        _reflection_support_signal_instruction,
        _retained_memory_support_signal_instruction,
        _temporal_support_signal_instruction,
    ):
        section = builder()
        if section:
            sections.append(section)
    return sections


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

    reflection_direction = _reflection_direction_label(str(dominant.get("signal_type") or ""))
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

    world_direction = _world_model_direction_label(str(dominant.get("signal_type") or ""))
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


def _delegated_continuity_summary(context: dict[str, object]) -> str | None:
    continuity = str(context.get("continuity_summary") or "").strip()
    if continuity:
        return "\n".join(
            [
                "Delegated continuity:",
                f"- {continuity}",
            ]
        )

    recent_runs = recent_visible_runs(limit=1)
    if not recent_runs:
        return None
    run = recent_runs[0]
    preview = str(run.get("text_preview") or "").strip()
    if not preview:
        return None
    return "\n".join(
        [
            "Delegated continuity:",
            f"- latest_visible_preview={preview}",
        ]
    )


def _should_include_memory(text: str, *, mode: str) -> bool:
    normalized = str(text or "").lower()
    if mode == "heartbeat":
        return True
    triggers = (
        "remember",
        "memory",
        "første besked",
        "første besked",
        "hvad skrev jeg",
        "preference",
        "prefer",
        "relationship",
        "continuity",
        "session",
    )
    return any(token in normalized for token in triggers)


def _should_include_guidance(text: str) -> bool:
    normalized = str(text or "").lower()
    triggers = (
        "tool",
        "tools",
        "skill",
        "skills",
        "capability",
        "read file",
        "search",
        "use tool",
        "use skill",
        "use capability",
        "invoke",
    )
    return any(token in normalized for token in triggers)


def _should_include_transcript(text: str) -> bool:
    normalized = str(text or "").lower()
    triggers = (
        "første besked",
        "hvad skrev jeg",
        "remember",
        "memory",
        "session",
        "continuity",
        "earlier",
        "previous",
    )
    return any(token in normalized for token in triggers)


def _should_include_continuity(text: str) -> bool:
    normalized = str(text or "").lower()
    triggers = (
        "remember",
        "memory",
        "continuity",
        "session",
        "første besked",
        "hvad skrev jeg",
    )
    return any(token in normalized for token in triggers)


def prompt_mode_loader_summary() -> dict[str, object]:
    return {
        "visible_chat": "implemented",
        "heartbeat": "loader-ready",
        "future_agent_task": "loader-ready",
    }
