from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apps.api.jarvis_api.services.chat_sessions import recent_chat_session_messages
from apps.api.jarvis_api.services.inner_visible_support_signal_tracking import (
    build_runtime_inner_visible_support_signal_surface,
)
from apps.api.jarvis_api.services.prompt_relevance_backend import (
    BoundedMemorySelectionAttempt,
    BoundedPromptRelevanceAttempt,
    BoundedPromptRelevanceResult,
    run_bounded_nl_memory_entry_selection,
    run_bounded_nl_prompt_relevance,
)

_RELEVANCE_DECISION_HISTORY: list[dict[str, object]] = []
_RELEVANCE_DECISION_HISTORY_LIMIT = 8


def _track_relevance_decision(decision: PromptRelevanceDecision) -> None:
    global _RELEVANCE_DECISION_HISTORY
    entry = {
        "mode": decision.mode,
        "memory_relevant": decision.memory_relevant,
        "guidance_relevant": decision.guidance_relevant,
        "transcript_relevant": decision.transcript_relevant,
        "continuity_relevant": decision.continuity_relevant,
        "include_memory": decision.include_memory,
        "include_guidance": decision.include_guidance,
        "include_transcript": decision.include_transcript,
        "include_continuity": decision.include_continuity,
        "include_support_signals": decision.include_support_signals,
        "backend_attempted": decision.backend_attempted,
        "backend_success": decision.backend_success,
        "fallback_used": decision.fallback_used,
        "backend_name": decision.backend_name,
        "backend_provider": decision.backend_provider,
        "backend_model": decision.backend_model,
        "backend_status": decision.backend_status,
    }
    _RELEVANCE_DECISION_HISTORY.insert(0, entry)
    if len(_RELEVANCE_DECISION_HISTORY) > _RELEVANCE_DECISION_HISTORY_LIMIT:
        _RELEVANCE_DECISION_HISTORY.pop()


_MEMORY_SELECTION_HISTORY: list[dict[str, object]] = []
_MEMORY_SELECTION_HISTORY_LIMIT = 8
_INNER_VISIBLE_PROMPT_BRIDGE_HISTORY: list[dict[str, object]] = []
_INNER_VISIBLE_PROMPT_BRIDGE_HISTORY_LIMIT = 8


def _track_memory_selection(
    selection: MemorySectionSelection, mode: str, candidate_count: int
) -> None:
    global _MEMORY_SELECTION_HISTORY
    entry = {
        "mode": mode,
        "candidate_count": candidate_count,
        "selected_count": len(selection.lines),
        "selected_indexes": selection.lines,
        "backend_attempted": selection.backend_attempted,
        "backend_success": selection.backend_success,
        "fallback_used": selection.fallback_used,
        "backend_name": selection.backend_name,
        "backend_provider": selection.backend_provider,
        "backend_model": selection.backend_model,
        "backend_status": selection.backend_status,
        "prompt_file_used": selection.prompt_file_used,
    }
    _MEMORY_SELECTION_HISTORY.insert(0, entry)
    if len(_MEMORY_SELECTION_HISTORY) > _MEMORY_SELECTION_HISTORY_LIMIT:
        _MEMORY_SELECTION_HISTORY.pop()


def build_runtime_memory_selection_surface(*, limit: int = 8) -> dict[str, object]:
    if not _MEMORY_SELECTION_HISTORY:
        return {
            "active": False,
            "items": [],
            "summary": "No memory selection decisions tracked yet.",
        }
    recent = _MEMORY_SELECTION_HISTORY[:limit]
    backend_attempted_count = sum(1 for item in recent if item.get("backend_attempted"))
    backend_success_count = sum(1 for item in recent if item.get("backend_success"))
    fallback_count = sum(1 for item in recent if item.get("fallback_used"))
    modes = list({item.get("mode") for item in recent if item.get("mode")})
    total_selected = sum(item.get("selected_count", 0) for item in recent)
    return {
        "active": True,
        "items": recent,
        "summary": {
            "total_decisions": len(recent),
            "backend_attempted": backend_attempted_count,
            "backend_success": backend_success_count,
            "fallback_used": fallback_count,
            "modes": modes,
            "total_entries_selected": total_selected,
        },
    }


def build_runtime_relevance_decision_surface(*, limit: int = 8) -> dict[str, object]:
    if not _RELEVANCE_DECISION_HISTORY:
        return {
            "active": False,
            "items": [],
            "summary": "No relevance decisions tracked yet.",
        }
    recent = _RELEVANCE_DECISION_HISTORY[:limit]
    backend_attempted_count = sum(1 for item in recent if item.get("backend_attempted"))
    backend_success_count = sum(1 for item in recent if item.get("backend_success"))
    fallback_count = sum(1 for item in recent if item.get("fallback_used"))
    modes = list({item.get("mode") for item in recent if item.get("mode")})
    return {
        "active": True,
        "items": recent,
        "summary": {
            "total_decisions": len(recent),
            "backend_attempted": backend_attempted_count,
            "backend_success": backend_success_count,
            "fallback_used": fallback_count,
            "modes": modes,
        },
    }


def build_runtime_inner_visible_prompt_bridge_surface(
    *, limit: int = 8
) -> dict[str, object]:
    if not _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY:
        return {
            "active": False,
            "items": [],
            "summary": "No inner-visible prompt bridge decisions tracked yet.",
        }
    recent = _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY[:limit]
    considered_count = sum(1 for item in recent if item.get("considered"))
    included_count = sum(1 for item in recent if item.get("included"))
    skipped_count = sum(
        1 for item in recent if item.get("considered") and not item.get("included")
    )
    latest = recent[0]
    return {
        "active": True,
        "items": recent,
        "summary": {
            "total_decisions": len(recent),
            "considered_count": considered_count,
            "included_count": included_count,
            "skipped_count": skipped_count,
            "current_reason": str(latest.get("reason") or "none"),
            "current_signal_id": str(latest.get("signal_id") or ""),
            "current_status": "included" if latest.get("included") else "skipped",
            "current_prompt_bridge_state": str(
                latest.get("prompt_bridge_state") or "gated-visible-prompt-bridge"
            ),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


from core.identity.runtime_contract import build_runtime_contract_state
from core.identity.workspace_bootstrap import (
    TEMPLATE_DIR,
    ensure_default_workspace,
    read_daily_memory_lines,
)
from core.memory.private_retained_memory_projection import (
    build_private_retained_memory_projection,
)
from core.runtime.db import (
    get_private_temporal_promotion_signal,
    get_private_retained_memory_record,
    get_private_self_model,
    list_runtime_awareness_signals,
    list_runtime_development_focuses,
    list_runtime_goal_signals,
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
    attention_trace: dict[str, object] | None = None


@dataclass(slots=True)
class PromptRelevanceDecision:
    mode: str
    memory_relevant: bool
    guidance_relevant: bool
    transcript_relevant: bool
    continuity_relevant: bool
    include_memory: bool
    include_guidance: bool
    include_transcript: bool
    include_continuity: bool
    include_support_signals: bool
    backend_attempted: bool
    backend_success: bool
    fallback_used: bool
    backend_name: str | None
    backend_provider: str | None
    backend_model: str | None
    backend_status: str


@dataclass(slots=True)
class MemorySectionSelection:
    lines: list[str]
    backend_attempted: bool
    backend_success: bool
    fallback_used: bool
    backend_name: str | None
    backend_provider: str | None
    backend_model: str | None
    backend_status: str
    prompt_file_used: bool


@dataclass(slots=True)
class InnerVisiblePromptBridgeDecision:
    mode: str
    considered: bool
    included: bool
    reason: str
    signal_id: str | None
    support_tone: str | None
    support_stance: str | None
    support_directness: str | None
    support_watchfulness: str | None
    support_momentum: str | None
    confidence: str | None
    prompt_bridge_state: str
    line: str | None
    subordinate: bool


def build_visible_chat_prompt_assembly(
    *,
    provider: str,
    model: str,
    user_message: str,
    session_id: str | None = None,
    name: str = "default",
    runtime_self_report_context: dict[str, object] | None = None,
) -> PromptAssembly:
    compact = provider == "ollama"
    workspace_dir = ensure_default_workspace(name=name)
    parts: list[str] = []
    included_files: list[str] = []
    conditional_files: list[str] = []
    derived_inputs: list[str] = []
    excluded_files = ["BOOTSTRAP.md", "HEARTBEAT.md", *DEFAULT_EXCLUDED_FILES]
    relevance = build_prompt_relevance_decision(
        user_message,
        mode="visible_chat",
        compact=compact,
        name=name,
    )

    # 0.5 Lane identity — inject before everything else
    lane = "local" if compact else "visible"
    lane_clause = _lane_identity_clause(lane)
    parts.append(lane_clause)
    derived_inputs.append(f"lane identity ({lane})")

    capability_truth = _visible_capability_truth_instruction(compact=compact)
    # capability_truth is added via budget-controlled section below
    capability_ids_line = _visible_capability_id_summary()

    visible_rules = _visible_chat_rules_instruction(workspace_dir=workspace_dir)
    if visible_rules:
        parts.append(visible_rules)
        conditional_files.append("VISIBLE_CHAT_RULES.md")
        derived_inputs.append("visible chat guidance rules")

    if compact:
        local_rules = _local_model_behavior_instruction(workspace_dir=workspace_dir)
        if local_rules:
            parts.append(local_rules)
            conditional_files.append("VISIBLE_LOCAL_MODEL.md")
            derived_inputs.append("local model behavior guardrails")

    if capability_ids_line:
        parts.append(capability_ids_line)
        derived_inputs.append("runtime capability id summary")

    for filename in ("SOUL.md", "IDENTITY.md", "STANDING_ORDERS.md", "USER.md"):
        section = _workspace_file_section(
            workspace_dir / filename,
            label=filename,
            max_lines=3 if compact else 5,
            max_chars=220 if compact else 340,
        )
        if section:
            parts.append(section)
            included_files.append(filename)

    if relevance.include_memory:
        memory_selection = _workspace_memory_section(
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            user_message=user_message,
            max_lines=3 if compact else 4,
            max_chars=200 if compact else 280,
            workspace_dir=workspace_dir,
            mode="visible_chat",
        )
        if memory_selection:
            parts.append(
                "\n".join(
                    ["MEMORY.md:", *[f"- {line}" for line in memory_selection.lines]]
                )
            )
            conditional_files.append("MEMORY.md")
            if memory_selection.prompt_file_used:
                conditional_files.append("VISIBLE_MEMORY_SELECTION.md")
            if memory_selection.backend_success:
                derived_inputs.append("bounded NL memory entry selection")
            elif memory_selection.fallback_used:
                derived_inputs.append("heuristic memory entry selection fallback")

        # Daily memory sidecar — short-lived session notes from today.
        # Read separately from MEMORY.md so Jarvis has today's context
        # without needing the full long-term memory file every turn.
        daily_lines = _today_daily_memory_lines(limit=6 if compact else 10)
        if daily_lines:
            parts.append(
                "\n".join(
                    [
                        "Today's notes (memory/daily):",
                        *[f"  {line}" for line in daily_lines],
                    ]
                )
            )
            derived_inputs.append("daily memory sidecar")

    if relevance.include_guidance:
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

    # --- Budget-controlled runtime sections ---
    # Workspace files (SOUL, IDENTITY, memory, rules, transcript) are
    # assembled above outside budget control — they are foundational.
    # Runtime-derived sections go through the attention budget selector.

    budget_profile = "visible_compact" if compact else "visible_full"

    continuity_content = (
        _visible_session_continuity_instruction()
        if relevance.include_continuity
        else None
    )

    self_report_content = _runtime_self_report_instruction(
        user_message=user_message,
        runtime_self_report_context=runtime_self_report_context or {},
    )

    support_raw = _visible_support_signal_sections(
        compact=compact,
        include=relevance.include_support_signals,
    )
    support_content = "\n\n".join(support_raw) if support_raw else None

    bridge_decision = _build_inner_visible_prompt_bridge_decision(
        user_message=user_message,
        mode="visible_chat",
        compact=compact,
        relevance=relevance,
    )
    bridge_content = (
        bridge_decision.line
        if bridge_decision.included and bridge_decision.line
        else None
    )

    if compact:
        frame_content = _micro_cognitive_frame_section()
    else:
        frame_content = _cognitive_frame_section()

    transcript_content = _recent_transcript_section(
        session_id,
        limit=10 if compact else 14,
        include=relevance.include_transcript,
    )

    # --- Cognitive State (accumulated personality, bearing, taste, rhythm) ---
    try:
        from apps.api.jarvis_api.services.cognitive_state_assembly import (
            build_cognitive_state_for_prompt,
        )

        cognitive_state_content = build_cognitive_state_for_prompt(compact=compact)
    except Exception:
        cognitive_state_content = None

    raw_sections = {
        "capability_truth": capability_truth,
        "cognitive_frame": frame_content,
        "cognitive_state": cognitive_state_content,
        "self_report": self_report_content,
        "inner_visible_bridge": bridge_content,
        "support_signals": support_content,
        "continuity": continuity_content,
        # These are heartbeat-only; supply None so budget correctly omits them
        "private_brain": None,
        "self_knowledge": None,
        "liveness": None,
    }

    selected, attention_trace_obj = _run_budget_selection(
        profile=budget_profile,
        sections=raw_sections,
    )

    # Assemble budget-selected sections in priority order
    _section_labels = {
        "capability_truth": "runtime capability and safety truth",
        "cognitive_frame": (
            "micro cognitive frame (compact)"
            if compact
            else "bounded cognitive frame (mode, salience, affordances)"
        ),
        "cognitive_state": "accumulated cognitive state (personality, bearing, taste, rhythm)",
        "self_report": "grounded runtime self-report support",
        "inner_visible_bridge": "bounded inner visible prompt bridge",
        "support_signals": "bounded runtime support signals",
        "continuity": "bounded session continuity",
    }
    for sec_name in (
        "capability_truth",
        "cognitive_frame",
        "cognitive_state",
        "self_report",
        "inner_visible_bridge",
        "support_signals",
        "continuity",
    ):
        content = selected.get(sec_name)
        if content:
            parts.append(content)
            label = _section_labels.get(sec_name, sec_name)
            derived_inputs.append(label)

    # Transcript is always outside budget (it's user conversation, not runtime)
    if transcript_content:
        parts.append(transcript_content)
        derived_inputs.append("recent transcript slice")

    return PromptAssembly(
        mode="visible_chat",
        text="\n\n".join(part for part in parts if part).strip(),
        included_files=included_files,
        conditional_files=conditional_files,
        derived_inputs=derived_inputs,
        excluded_files=excluded_files,
        attention_trace=attention_trace_obj.summary(),
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
    excluded_files = [
        "runtime/RUNTIME_FEEDBACK.md",
        "boredom_templates.json",
        "full transcript",
        "heavy private/internal dumps",
    ]
    relevance = build_prompt_relevance_decision(
        "heartbeat",
        mode="heartbeat",
        compact=False,
        name=name,
    )

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

    for filename in (
        "HEARTBEAT.md",
        "SOUL.md",
        "IDENTITY.md",
        "STANDING_ORDERS.md",
        "USER.md",
    ):
        section = _workspace_file_section(
            workspace_dir / filename,
            label=filename,
            max_lines=4,
            max_chars=260,
        )
        if section:
            parts.append(section)
            included_files.append(filename)

    if relevance.include_memory:
        memory_selection = _workspace_memory_section(
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            user_message="heartbeat proposal check",
            max_lines=4,
            max_chars=260,
            workspace_dir=workspace_dir,
            mode="heartbeat",
        )
        if memory_selection:
            parts.append(
                "\n".join(
                    ["MEMORY.md:", *[f"- {line}" for line in memory_selection.lines]]
                )
            )
            conditional_files.append("MEMORY.md")
            if memory_selection.prompt_file_used:
                conditional_files.append("VISIBLE_MEMORY_SELECTION.md")
            if memory_selection.backend_success:
                derived_inputs.append("bounded NL memory entry selection")
            elif memory_selection.fallback_used:
                derived_inputs.append("heuristic memory entry selection fallback")

        # Daily memory sidecar for heartbeat prompts too, so proactive
        # decisions can reference today's context without pulling in
        # the full long-term memory file.
        daily_lines = _today_daily_memory_lines(limit=8)
        if daily_lines:
            parts.append(
                "\n".join(
                    [
                        "Today's notes (memory/daily):",
                        *[f"  {line}" for line in daily_lines],
                    ]
                )
            )
            derived_inputs.append("daily memory sidecar")

    # Due summary is always included (scheduling truth, not runtime-derived)
    due_summary = _heartbeat_due_summary(heartbeat_context or {})
    if due_summary:
        parts.append(due_summary)
        derived_inputs.append("due schedules and open-loop summary")

    # --- Budget-controlled runtime sections ---
    hb_ctx = heartbeat_context or {}
    raw_sections = {
        "capability_truth": _heartbeat_capability_truth_instruction(hb_ctx),
        "continuity": _heartbeat_continuity_summary(hb_ctx),
        "liveness": _heartbeat_liveness_summary(hb_ctx),
        "private_brain": _heartbeat_private_brain_section(hb_ctx),
        "self_knowledge": _heartbeat_self_knowledge_section(),
        "cognitive_frame": _cognitive_frame_section(),
        # These are visible-only; supply None for correct budget omission
        "self_report": None,
        "support_signals": None,
        "inner_visible_bridge": None,
    }

    selected, attention_trace_obj = _run_budget_selection(
        profile="heartbeat",
        sections=raw_sections,
    )

    _hb_labels = {
        "capability_truth": "compact capability truth",
        "continuity": "optional compact continuity summary",
        "liveness": "bounded heartbeat liveness support",
        "private_brain": "bounded private brain continuity context",
        "self_knowledge": "bounded runtime self-knowledge map",
        "cognitive_frame": "bounded cognitive frame (mode, salience, affordances)",
    }
    for sec_name in (
        "capability_truth",
        "cognitive_frame",
        "private_brain",
        "self_knowledge",
        "continuity",
        "liveness",
    ):
        content = selected.get(sec_name)
        if content:
            parts.append(content)
            derived_inputs.append(_hb_labels.get(sec_name, sec_name))

    return PromptAssembly(
        mode="heartbeat",
        text="\n\n".join(part for part in parts if part).strip(),
        included_files=included_files,
        conditional_files=conditional_files,
        derived_inputs=derived_inputs,
        excluded_files=excluded_files,
        attention_trace=attention_trace_obj.summary(),
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
    excluded_files = [
        "BOOTSTRAP.md",
        "HEARTBEAT.md",
        *DEFAULT_EXCLUDED_FILES,
        "full transcript",
    ]
    relevance = build_prompt_relevance_decision(
        task_brief,
        mode="future_agent_task",
        compact=False,
        name=name,
    )

    runtime_truth = _future_agent_runtime_truth_instruction(context)
    if runtime_truth:
        parts.append(runtime_truth)
        derived_inputs.append("runtime role, scope, and capability truth")

    for filename in ("SOUL.md", "IDENTITY.md", "STANDING_ORDERS.md"):
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

    if relevance.include_memory:
        memory_selection = _workspace_memory_section(
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            user_message=str(task_brief or "delegated task"),
            max_lines=4,
            max_chars=240,
            workspace_dir=workspace_dir,
            mode="future_agent_task",
        )
        if memory_selection:
            parts.append(
                "\n".join(
                    ["MEMORY.md:", *[f"- {line}" for line in memory_selection.lines]]
                )
            )
            conditional_files.append("MEMORY.md")
            if memory_selection.prompt_file_used:
                conditional_files.append("VISIBLE_MEMORY_SELECTION.md")
            if memory_selection.backend_success:
                derived_inputs.append("bounded NL memory entry selection")
            elif memory_selection.fallback_used:
                derived_inputs.append("heuristic memory entry selection fallback")

        # Daily memory sidecar so delegated agents see today's session
        # context, not just long-term curated facts.
        daily_lines = _today_daily_memory_lines(limit=8)
        if daily_lines:
            parts.append(
                "\n".join(
                    [
                        "Today's notes (memory/daily):",
                        *[f"  {line}" for line in daily_lines],
                    ]
                )
            )
            derived_inputs.append("daily memory sidecar")

    if relevance.include_guidance or context.get("include_guidance"):
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


def build_prompt_relevance_decision(
    text: str,
    *,
    mode: str,
    compact: bool,
    name: str = "default",
) -> PromptRelevanceDecision:
    heuristic_memory_relevant = _should_include_memory(text, mode=mode)
    heuristic_guidance_relevant = _should_include_guidance(text)
    heuristic_transcript_relevant = _should_include_transcript(text)
    heuristic_continuity_relevant = _should_include_continuity(text)
    backend_attempt = _bounded_nl_relevance_backend(
        text=text,
        mode=mode,
        compact=compact,
        name=name,
    )
    nl_relevance = backend_attempt.result if backend_attempt.success else None

    memory_relevant = heuristic_memory_relevant or bool(
        nl_relevance and nl_relevance.memory_relevant
    )
    guidance_relevant = heuristic_guidance_relevant or bool(
        nl_relevance and nl_relevance.guidance_relevant
    )
    transcript_relevant = heuristic_transcript_relevant or bool(
        nl_relevance and nl_relevance.transcript_relevant
    )
    continuity_relevant = heuristic_continuity_relevant or bool(
        nl_relevance and nl_relevance.continuity_relevant
    )
    support_signals_relevant = memory_relevant or bool(
        nl_relevance and nl_relevance.support_signals_relevant
    )

    if mode == "visible_chat":
        include_memory = True
        include_transcript = True
        include_continuity = True
        include_support_signals = (not compact) or support_signals_relevant
    elif mode == "heartbeat":
        include_memory = True
        include_transcript = False
        include_continuity = continuity_relevant
        include_support_signals = support_signals_relevant
    elif mode == "future_agent_task":
        include_memory = memory_relevant
        include_transcript = False
        include_continuity = continuity_relevant
        include_support_signals = support_signals_relevant
    else:
        include_memory = memory_relevant
        include_transcript = False
        include_continuity = False
        include_support_signals = False

    decision = PromptRelevanceDecision(
        mode=mode,
        memory_relevant=memory_relevant,
        guidance_relevant=guidance_relevant,
        transcript_relevant=transcript_relevant,
        continuity_relevant=continuity_relevant,
        include_memory=include_memory,
        include_guidance=guidance_relevant,
        include_transcript=include_transcript,
        include_continuity=include_continuity,
        include_support_signals=include_support_signals,
        backend_attempted=backend_attempt.attempted,
        backend_success=backend_attempt.success,
        fallback_used=not backend_attempt.success,
        backend_name=backend_attempt.backend,
        backend_provider=backend_attempt.provider,
        backend_model=backend_attempt.model,
        backend_status=backend_attempt.status,
    )
    _track_relevance_decision(decision)
    return decision


def _bounded_nl_relevance_backend(
    *,
    text: str,
    mode: str,
    compact: bool,
    name: str,
) -> BoundedPromptRelevanceAttempt:
    return run_bounded_nl_prompt_relevance(
        text=text,
        mode=mode,
        compact=compact,
        workspace_dir=ensure_default_workspace(name=name),
    )


def _track_inner_visible_prompt_bridge(
    decision: InnerVisiblePromptBridgeDecision,
) -> None:
    global _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY
    _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY.insert(
        0,
        {
            "mode": decision.mode,
            "considered": decision.considered,
            "included": decision.included,
            "reason": decision.reason,
            "signal_id": decision.signal_id,
            "support_tone": decision.support_tone,
            "support_stance": decision.support_stance,
            "support_directness": decision.support_directness,
            "support_watchfulness": decision.support_watchfulness,
            "support_momentum": decision.support_momentum,
            "confidence": decision.confidence,
            "prompt_bridge_state": decision.prompt_bridge_state,
            "line": decision.line,
            "subordinate": decision.subordinate,
        },
    )
    if (
        len(_INNER_VISIBLE_PROMPT_BRIDGE_HISTORY)
        > _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY_LIMIT
    ):
        _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY.pop()


def _build_inner_visible_prompt_bridge_decision(
    *,
    user_message: str,
    mode: str,
    compact: bool,
    relevance: PromptRelevanceDecision,
) -> InnerVisiblePromptBridgeDecision:
    decision = InnerVisiblePromptBridgeDecision(
        mode=mode,
        considered=mode == "visible_chat",
        included=False,
        reason="unsupported-mode" if mode != "visible_chat" else "not-evaluated",
        signal_id=None,
        support_tone=None,
        support_stance=None,
        support_directness=None,
        support_watchfulness=None,
        support_momentum=None,
        confidence=None,
        prompt_bridge_state="gated-visible-prompt-bridge",
        line=None,
        subordinate=True,
    )
    if mode != "visible_chat":
        _track_inner_visible_prompt_bridge(decision)
        return decision
    if not compact:
        decision.reason = "full-support-mode"
        _track_inner_visible_prompt_bridge(decision)
        return decision

    signal = _latest_active_inner_visible_support_signal()
    if signal is None:
        decision.reason = "no-active-signal"
        _track_inner_visible_prompt_bridge(decision)
        return decision

    decision.signal_id = str(signal.get("signal_id") or "")
    decision.support_tone = str(signal.get("support_tone") or "")
    decision.support_stance = str(signal.get("support_stance") or "")
    decision.support_directness = str(signal.get("support_directness") or "")
    decision.support_watchfulness = str(signal.get("support_watchfulness") or "")
    decision.support_momentum = str(signal.get("support_momentum") or "")
    decision.confidence = str(
        signal.get("support_confidence") or signal.get("confidence") or ""
    )
    decision.prompt_bridge_state = str(
        signal.get("prompt_bridge_state") or "gated-visible-prompt-bridge"
    )

    if decision.confidence not in {"medium", "high"}:
        decision.reason = "low-confidence"
        _track_inner_visible_prompt_bridge(decision)
        return decision
    if (
        relevance.memory_relevant
        or relevance.include_guidance
        or relevance.continuity_relevant
    ):
        decision.reason = "primary-context-query"
        _track_inner_visible_prompt_bridge(decision)
        return decision
    if _inner_visible_support_bridge_is_redundant(signal):
        decision.reason = "redundant-steady-support"
        _track_inner_visible_prompt_bridge(decision)
        return decision

    decision.line = _inner_visible_support_prompt_line(signal)
    if not decision.line:
        decision.reason = "empty-bridge-line"
        _track_inner_visible_prompt_bridge(decision)
        return decision

    decision.included = True
    decision.reason = "included"
    _track_inner_visible_prompt_bridge(decision)
    return decision


def _latest_active_inner_visible_support_signal() -> dict[str, object] | None:
    surface = build_runtime_inner_visible_support_signal_surface(limit=4)
    for item in surface.get("items", []):
        if str(item.get("status") or "") == "active":
            return item
    return None


def _inner_visible_support_bridge_is_redundant(signal: dict[str, object]) -> bool:
    return (
        str(signal.get("support_tone") or "") == "steady-support"
        and str(signal.get("support_stance") or "") == "steady"
        and str(signal.get("support_directness") or "") == "high"
        and str(signal.get("support_watchfulness") or "") == "low"
        and str(signal.get("support_momentum") or "") == "steady"
    )


def _inner_visible_support_prompt_line(signal: dict[str, object]) -> str | None:
    tone = str(signal.get("support_tone") or "").strip()
    stance = str(signal.get("support_stance") or "").strip()
    directness = str(signal.get("support_directness") or "").strip()
    watchfulness = str(signal.get("support_watchfulness") or "").strip()
    momentum = str(signal.get("support_momentum") or "").strip()
    if not all((tone, stance, directness, watchfulness, momentum)):
        return None
    phrases: list[str] = []
    tone_map = {
        "careful-forward": "Hold en rolig, fremadrettet tone.",
        "careful-steady": "Hold en rolig og stabil tone.",
        "steady-forward": "Svar roligt, men fortsæt fremad.",
        "steady-support": "Svar enkelt og uden dramatik.",
    }
    stance_map = {
        "careful": "Vær varsom uden at blive vag.",
        "steady": "Stå fast i svaret.",
        "open": "Hold dig åben for justeringer.",
    }
    directness_map = {
        "high": "Svar konkret.",
        "medium": "Svar klart uden at overforklare.",
        "low": "Svar blødt og forsigtigt.",
    }
    watchfulness_map = {
        "high": "Dobbelttjek antagelser før du konkluderer.",
        "medium": "Hold øje med usikre antagelser.",
        "low": "Undgå unødig selvovervågning.",
    }
    momentum_map = {
        "steady": "Bliv i samtalen og før den videre.",
        "forward": "Hjælp samtalen videre med næste konkrete skridt.",
        "holding": "Hold fokus på det, der allerede er i gang.",
    }
    for key, mapping in (
        (tone, tone_map),
        (stance, stance_map),
        (directness, directness_map),
        (watchfulness, watchfulness_map),
        (momentum, momentum_map),
    ):
        phrase = mapping.get(key)
        if phrase and phrase not in phrases:
            phrases.append(phrase)
    if not phrases:
        return None
    return "Inner visible support (subordinate only, never authority): " + " ".join(
        phrases
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
    return section


def _workspace_optional_file_section(
    path: Path,
    *,
    fallback_path: Path | None,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    source = path if path.exists() else fallback_path
    if source is None or not source.exists():
        return None
    return _workspace_file_section(
        source,
        label=label,
        max_lines=max_lines,
        max_chars=max_chars,
    )


def _workspace_memory_section(
    path: Path,
    *,
    label: str,
    user_message: str,
    max_lines: int,
    max_chars: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> MemorySectionSelection | None:
    if not path.exists():
        return None
    entries = _workspace_memory_entries(path)
    if not entries:
        return None
    selection = _select_relevant_memory_entries(
        entries,
        user_message=user_message,
        max_lines=max_lines,
        max_chars=max_chars,
        workspace_dir=workspace_dir,
        mode=mode,
    )
    if not selection.lines:
        return None
    _track_memory_selection(selection, mode, len(entries))
    return selection


def _today_daily_memory_lines(*, limit: int = 10) -> list[str]:
    """Read today's daily memory lines for injection into visible prompts.

    Wraps read_daily_memory_lines with exception safety so prompt
    builders never fail because the daily file is missing, empty, or
    briefly unreadable.
    """
    try:
        return read_daily_memory_lines(limit=limit)
    except Exception:
        return []


def _workspace_memory_entries(path: Path) -> list[str]:
    entries: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        normalized = " ".join(line.lstrip("-").split()).strip()
        if not normalized:
            continue
        entries.append(normalized)
    return entries


def _select_relevant_memory_entries(
    entries: list[str],
    *,
    user_message: str,
    max_lines: int,
    max_chars: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> MemorySectionSelection:
    backend_attempt = _bounded_nl_memory_selection(
        user_message=user_message,
        entries=entries,
        max_lines=max_lines,
        workspace_dir=workspace_dir,
        mode=mode,
    )
    ordered: list[str]
    prompt_file_used = bool(
        (workspace_dir / "VISIBLE_MEMORY_SELECTION.md").exists()
        or (TEMPLATE_DIR / "VISIBLE_MEMORY_SELECTION.md").exists()
    )

    if backend_attempt.success and backend_attempt.result is not None:
        bounded_entries = entries[-8:]
        selected_indexes = backend_attempt.result.selected_indexes
        ordered = [
            bounded_entries[index]
            for index in selected_indexes
            if 0 <= index < len(bounded_entries)
        ]
    else:
        ordered = _heuristic_relevant_memory_entries(
            entries,
            user_message=user_message,
            max_lines=max_lines,
        )

    clipped: list[str] = []
    for entry in ordered:
        text = entry
        if len(text) > max_chars:
            text = text[: max_chars - 1].rstrip() + "…"
        clipped.append(text)
    return MemorySectionSelection(
        lines=clipped,
        backend_attempted=backend_attempt.attempted,
        backend_success=backend_attempt.success,
        fallback_used=not backend_attempt.success,
        backend_name=backend_attempt.backend,
        backend_provider=backend_attempt.provider,
        backend_model=backend_attempt.model,
        backend_status=backend_attempt.status,
        prompt_file_used=prompt_file_used,
    )


def _heuristic_relevant_memory_entries(
    entries: list[str],
    *,
    user_message: str,
    max_lines: int,
) -> list[str]:
    scored: list[tuple[int, int, str]] = []
    for index, entry in enumerate(entries):
        score = _memory_line_relevance_score(entry, user_message)
        if score <= 0:
            continue
        scored.append((score, index, entry))

    if scored:
        chosen = sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)[
            : max(max_lines, 1)
        ]
        ordered = [item[2] for item in sorted(chosen, key=lambda item: item[1])]
    else:
        ordered = entries[-max(max_lines, 1) :]
    return ordered


def _bounded_nl_memory_selection(
    *,
    user_message: str,
    entries: list[str],
    max_lines: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> BoundedMemorySelectionAttempt:
    return run_bounded_nl_memory_entry_selection(
        user_message=user_message,
        entries=entries,
        max_lines=max_lines,
        workspace_dir=workspace_dir,
        mode=mode,
    )


def _memory_line_relevance_score(entry: str, user_message: str) -> int:
    line = str(entry or "").lower()
    query = str(user_message or "").lower()
    score = 0

    if _contains_any(
        query, ("mit navn", "hvad hedder jeg", "name", "navn")
    ) and _contains_any(
        line,
        ("name", "navn"),
    ):
        score += 8
    if _contains_any(
        query,
        ("bygger vi", "build", "building", "projekt", "project", "arbejder vi på"),
    ) and _contains_any(
        line,
        (
            "project anchor",
            "building jarvis together",
            "jarvis together",
            "shared project",
        ),
    ):
        score += 8
    if _contains_any(
        query,
        (
            "repo",
            "repoet",
            "repository",
            "arbejder vi i",
            "working context",
            "hvilket repo",
        ),
    ) and _contains_any(
        line,
        ("jarvis v2 repo", "working context", "repo context", "repo"),
    ):
        score += 8
    if _contains_any(
        query,
        ("context", "continuity", "stable", "carry", "workspace"),
    ) and _contains_any(
        line,
        ("stable context", "carry forward", "carried", "workspace continuity"),
    ):
        score += 5

    for token in (
        "jarvis",
        "repo",
        "project",
        "context",
        "name",
        "working",
        "build",
        "stable",
        "workspace",
    ):
        if token in query and token in line:
            score += 1
    return score


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _visible_chat_rules_instruction(*, workspace_dir: Path) -> str | None:
    return _workspace_optional_file_section(
        workspace_dir / "VISIBLE_CHAT_RULES.md",
        fallback_path=TEMPLATE_DIR / "VISIBLE_CHAT_RULES.md",
        label="Visible chat guidance rules",
        max_lines=14,
        max_chars=600,
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
    policy = capability_truth.get("policy") or {}
    contract = capability_truth.get("contract") or {}
    lines = ["Runtime capability truth:"]
    lines.append(
        "- Visible tool invocation uses text capability-call lines, not JSON: "
        '<capability-call id="capability_id" />'
    )
    lines.append(
        "- If a capability needs arguments, bind them in the same tag as quoted attributes, for example: "
        '<capability-call id="capability_id" command_text="pwd" />'
    )
    lines.append(
        "- When you invoke capabilities, emit the capability-call tags together. "
        "You may include a brief sentence before or after the tags explaining what you are doing, "
        "but keep it short — the capability results will speak for themselves."
    )
    lines.append(
        "- If you are missing context or feel uncertain about a file-backed answer, read the whole relevant file before answering instead of guessing from fragments."
    )
    lines.append(
        "- If the user asks for code analysis, walkthrough, or a repo/codebase review, do not stop at README, pyproject, or directory names. Read concrete code files before claiming analysis."
    )
    lines.append(
        "- For arg-requiring capabilities, the capability-call tag is authoritative. User-message extraction is compatibility fallback only."
    )
    lines.append(
        "- Do not emit JSON or pseudo-JSON tool calls. "
        f"json_tool_call_supported={contract.get('json_tool_call_supported', False)}"
    )
    if any(
        str(item.get("execution_mode") or "") == "external-file-read"
        and str(item.get("target_path_source") or "") == "invocation-argument"
        for item in available
    ):
        lines.append(
            "- Dynamic external file read and directory listing can use paths from: "
            "(1) the user's current message, (2) results from previous capability calls in this turn, "
            "(3) well-known paths (PROJECT_ROOT, workspace root, home directory). "
            "You do not need the user to spell out every path — if you know the path from context, use it."
        )
    if any(
        str(item.get("execution_mode") or "") == "non-destructive-exec"
        and str(item.get("command_source") or "") == "invocation-argument"
        for item in available
    ):
        lines.append(
            "- Non-destructive exec is allowed when the user's intent is clear. "
            "You do not need the command in backticks — infer the appropriate read-only command from context."
        )
        lines.append(
            "- When a task spans several facts, prefer multiple small read-only commands in the same turn. Do not stop after the first partial result if more bounded calls are clearly needed."
        )
        lines.append(
            "- If the current task is still clearly read-only and bounded, continue autonomously with additional capability calls instead of asking the user for permission to keep reading."
        )
        lines.append(
            "- If the user is asking about repo behavior, path resolution, capabilities, commits, or backend structure, proactively inspect the repo with bounded reads or git inspection before answering."
        )
        lines.append(
            "- If the user is asking about the machine or runtime environment, proactively gather bounded system facts before answering."
        )
        lines.append(
            "- Bounded git read/inspect commands such as git status, git diff --stat, git diff --name-only, git log --oneline -n N, and git branch --show-current may execute as non-destructive inspection. Git mutation remains proposal-only here and is classified into small repo stewardship classes such as git-stage, git-commit, git-sync, git-branch-switch, git-history-rewrite, git-stash, or git-other-mutate. Git clean stays blocked. If a command is mutating, do not claim execution unless runtime truth has explicit approval for that exact bounded non-sudo command fingerprint. Sudo-near commands may execute only after explicit approval of that exact sudo command fingerprint and only inside the tiny sudo allowlist for this pass. Runtime may reuse a short auto-expiring sudo approval window only for the same bounded sudo scope."
        )
    if available:
        lines.append(
            "- Callable capability_ids: "
            + ", ".join(str(item.get("capability_id") or "") for item in available)
        )
        lines.append(f"- Callable now: {len(available)} capability_ids.")
        limit = len(available)
        for item in available[:limit]:
            lines.append(
                f"  - {item['capability_id']}: {item.get('name', '')}"
                f" [{item.get('execution_mode', 'unknown')}]"
            )
    else:
        lines.append(
            "- No workspace capabilities are currently available for direct execution."
        )
    if gated:
        lines.append(
            "- Approval-gated capability_ids: "
            + ", ".join(str(item.get("capability_id") or "") for item in gated[:6])
        )
        lines.append(
            f"- Approval-gated but not auto-executable now: {len(gated)} capability_ids."
        )
        for item in gated[:6]:
            lines.append(
                f"  - {item['capability_id']}: approval required"
                f" [{item.get('execution_mode', 'unknown')}]"
            )
    lines.append(
        "- Policy: "
        f"workspace_read={policy.get('workspace_read', 'allowed')} | "
        f"external_read={policy.get('external_read', 'allowed')} | "
        f"non_destructive_exec={policy.get('non_destructive_exec', 'allowed')} | "
        f"mutating_exec={policy.get('mutating_exec', 'explicit-approval-required-bounded-non-sudo-only')} | "
        f"sudo_exec={policy.get('sudo_exec', 'explicit-approval-required-bounded-allowlist-with-short-ttl-window')} | "
        f"workspace_write={policy.get('workspace_write', 'explicit-approval-required')} | "
        f"external_write={policy.get('external_write', 'explicit-approval-required')}"
    )
    return "\n".join(lines)


def _visible_capability_id_summary() -> str | None:
    capability_truth = load_workspace_capabilities()
    callable_ids = [
        str(item.get("capability_id") or "")
        for item in (capability_truth.get("runtime_capabilities") or [])
        if item.get("available_now") and str(item.get("capability_id") or "").strip()
    ]
    gated_ids = [
        str(item.get("capability_id") or "")
        for item in (capability_truth.get("runtime_capabilities") or [])
        if item.get("runtime_status") == "approval-required"
        and str(item.get("capability_id") or "").strip()
    ]
    if not callable_ids and not gated_ids:
        return None
    lines = ["Visible capability ids:"]
    if callable_ids:
        lines.append("- callable: " + ", ".join(callable_ids))
    if gated_ids:
        lines.append("- approval_gated: " + ", ".join(gated_ids))
    lines.append(
        "- usage: capabilities that read external paths or list directories "
        'MUST bind target_path in the tag, e.g. <capability-call id="tool:list-external-directory" target_path="/path" />. '
        "For commands, bind command_text similarly."
    )
    lines.append(
        "- parallel: you can emit multiple capability-call tags in one response. "
        "Do this when exploring — e.g. list a directory AND read a file in the same turn. "
        "If one fails, others still execute. Never stop working because one call failed."
    )
    lines.append(
        "- autonomy: if the task is still read-only and bounded, continue with more capability-call tags instead of asking the user to tell you to continue."
    )
    lines.append(
        "- system-inspection: when a user asks for multiple machine specs, prefer multiple small command calls in one response "
        'such as `lscpu`, `free -h`, `lsblk`, `df -h`, and either `lspci | rg -i "vga|3d|display"` or `nvidia-smi` instead of one oversized command.'
    )
    return "\n".join(lines)


def _local_model_behavior_instruction(*, workspace_dir: Path) -> str | None:
    return _workspace_optional_file_section(
        workspace_dir / "VISIBLE_LOCAL_MODEL.md",
        fallback_path=TEMPLATE_DIR / "VISIBLE_LOCAL_MODEL.md",
        label="Visible local-model behavior rules",
        max_lines=14,
        max_chars=220,
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
    embodied = context.get("embodied_state") or {}
    affective = context.get("affective_meta_state") or {}
    epistemic = context.get("epistemic_runtime_state") or {}
    adaptive_planner = context.get("adaptive_planner") or {}
    adaptive_reasoning = context.get("adaptive_reasoning") or {}
    dream_influence = context.get("dream_influence") or {}
    guided_learning = context.get("guided_learning") or {}
    adaptive_learning = context.get("adaptive_learning") or {}
    self_system_code_awareness = context.get("self_system_code_awareness") or {}
    tool_intent = context.get("tool_intent") or {}
    loop_runtime = context.get("loop_runtime") or {}
    loop_summary = loop_runtime.get("summary") or {}
    return "\n".join(
        [
            "Heartbeat runtime truth:",
            f"- schedule={schedule} | budget={budget} | kill_switch={kill_switch}",
            (
                f"- embodied_state={embodied.get('state') or 'unknown'}"
                f" | embodied_strain={embodied.get('strain_level') or 'unknown'}"
            ),
            (
                f"- affective_meta_state={affective.get('state') or 'unknown'}"
                f" | affective_bearing={affective.get('bearing') or 'unknown'}"
                f" | affective_monitoring={affective.get('monitoring_mode') or 'unknown'}"
            ),
            (
                f"- epistemic_state={epistemic.get('wrongness_state') or 'clear'}"
                f" | regret={epistemic.get('regret_signal') or 'none'}"
                f" | counterfactual={epistemic.get('counterfactual_mode') or 'none'}"
            ),
            (
                f"- adaptive_planner={adaptive_planner.get('planner_mode') or 'incremental'}"
                f" | horizon={adaptive_planner.get('plan_horizon') or 'near'}"
                f" | posture={adaptive_planner.get('planning_posture') or 'staged'}"
                f" | risk={adaptive_planner.get('risk_posture') or 'balanced'}"
            ),
            (
                f"- adaptive_reasoning={adaptive_reasoning.get('reasoning_mode') or 'direct'}"
                f" | posture={adaptive_reasoning.get('reasoning_posture') or 'balanced'}"
                f" | certainty={adaptive_reasoning.get('certainty_style') or 'crisp'}"
                f" | constraint={adaptive_reasoning.get('constraint_bias') or 'light'}"
            ),
            (
                f"- dream_influence={dream_influence.get('influence_state') or 'quiet'}"
                f" | target={dream_influence.get('influence_target') or 'none'}"
                f" | mode={dream_influence.get('influence_mode') or 'stabilize'}"
                f" | strength={dream_influence.get('influence_strength') or 'none'}"
            ),
            (
                f"- guided_learning={guided_learning.get('learning_mode') or 'reinforce'}"
                f" | focus={guided_learning.get('learning_focus') or 'reasoning'}"
                f" | posture={guided_learning.get('learning_posture') or 'gentle'}"
                f" | pressure={guided_learning.get('learning_pressure') or 'low'}"
            ),
            (
                f"- adaptive_learning={adaptive_learning.get('learning_engine_mode') or 'retain'}"
                f" | target={adaptive_learning.get('reinforcement_target') or 'reasoning'}"
                f" | retention={adaptive_learning.get('retention_bias') or 'light'}"
                f" | maturation={adaptive_learning.get('maturation_state') or 'early'}"
            ),
            (
                f"- self_system_code_awareness={self_system_code_awareness.get('code_awareness_state') or 'repo-unavailable'}"
                f" | repo={self_system_code_awareness.get('repo_status') or 'not-git'}"
                f" | changes={self_system_code_awareness.get('local_change_state') or 'unknown'}"
                f" | upstream={self_system_code_awareness.get('upstream_awareness') or 'unknown'}"
                f" | concern={self_system_code_awareness.get('concern_state') or 'stable'}"
                f" | approval_required={self_system_code_awareness.get('action_requires_approval', True)}"
            ),
            (
                f"- tool_intent={tool_intent.get('intent_state') or 'idle'}"
                f" | type={tool_intent.get('intent_type') or 'inspect-repo-status'}"
                f" | target={tool_intent.get('intent_target') or 'workspace'}"
                f" | urgency={tool_intent.get('urgency') or 'low'}"
                f" | approval_state={tool_intent.get('approval_state') or 'none'}"
                f" | approval_source={tool_intent.get('approval_source') or 'none'}"
                f" | approval_required={tool_intent.get('approval_required', True)}"
                f" | approval_expires_at={tool_intent.get('approval_expires_at') or 'none'}"
                f" | execution_state={tool_intent.get('execution_state') or 'not-executed'}"
                f" | execution_mode={tool_intent.get('execution_mode') or 'read-only'}"
                f" | mutation_permitted={tool_intent.get('mutation_permitted', False)}"
                f" | workspace_scoped={tool_intent.get('workspace_scoped', False)}"
                f" | external_mutation_permitted={tool_intent.get('external_mutation_permitted', False)}"
                f" | delete_permitted={tool_intent.get('delete_permitted', False)}"
                f" | mutation_state={tool_intent.get('mutation_intent_state') or 'idle'}"
                f" | mutation_classification={tool_intent.get('mutation_intent_classification') or 'none'}"
                f" | mutation_repo_scope={tool_intent.get('mutation_repo_scope') or 'none'}"
                f" | mutation_system_scope={tool_intent.get('mutation_system_scope') or 'none'}"
                f" | mutation_sudo_required={tool_intent.get('mutation_sudo_required', False)}"
                f" | write_proposal_state={tool_intent.get('write_proposal_state') or 'none'}"
                f" | write_proposal_type={tool_intent.get('write_proposal_type') or 'none'}"
                f" | write_proposal_scope={tool_intent.get('write_proposal_scope') or 'none'}"
                f" | write_proposal_criticality={tool_intent.get('write_proposal_criticality') or 'none'}"
                f" | write_proposal_target_identity={tool_intent.get('write_proposal_target_identity', False)}"
                f" | write_proposal_target_memory={tool_intent.get('write_proposal_target_memory', False)}"
                f" | write_proposal_target={tool_intent.get('write_proposal_target') or 'none'}"
                f" | write_proposal_content_state={tool_intent.get('write_proposal_content_state') or 'none'}"
                f" | write_proposal_content_fingerprint={tool_intent.get('write_proposal_content_fingerprint') or 'none'}"
                f" | write_proposal_content_summary={tool_intent.get('write_proposal_content_summary') or 'none'}"
                f" | mutating_exec_state={tool_intent.get('mutating_exec_proposal_state') or 'none'}"
                f" | mutating_exec_scope={tool_intent.get('mutating_exec_proposal_scope') or 'none'}"
                f" | mutating_exec_requires_sudo={tool_intent.get('mutating_exec_requires_sudo', False)}"
                f" | mutating_exec_fingerprint={tool_intent.get('mutating_exec_command_fingerprint') or 'none'}"
                f" | sudo_exec_state={tool_intent.get('sudo_exec_proposal_state') or 'none'}"
                f" | sudo_exec_scope={tool_intent.get('sudo_exec_proposal_scope') or 'none'}"
                f" | sudo_exec_requires_sudo={tool_intent.get('sudo_exec_requires_sudo', False)}"
                f" | sudo_exec_fingerprint={tool_intent.get('sudo_exec_command_fingerprint') or 'none'}"
                f" | sudo_window_state={tool_intent.get('sudo_approval_window_state') or 'none'}"
                f" | sudo_window_scope={tool_intent.get('sudo_approval_window_scope') or 'none'}"
                f" | sudo_window_expires_at={tool_intent.get('sudo_approval_window_expires_at') or 'none'}"
                f" | sudo_window_reusable={tool_intent.get('sudo_approval_window_reusable', False)}"
                f" | execution_command={tool_intent.get('execution_command') or 'none'}"
                f" | sudo_permitted={tool_intent.get('sudo_permitted', False)}"
                f" | execution_summary={tool_intent.get('execution_summary') or 'none'}"
                f" | continuity={tool_intent.get('action_continuity_state') or 'idle'}"
                f" | last_action_outcome={tool_intent.get('last_action_outcome') or 'none'}"
                f" | followup_state={tool_intent.get('followup_state') or 'none'}"
                f" | followup_hint={tool_intent.get('followup_hint') or 'none'}"
            ),
            (
                f"- loop_runtime={loop_summary.get('current_status') or 'none'}"
                f" | active_loops={loop_summary.get('active_count') or 0}"
                f" | standby_loops={loop_summary.get('standby_count') or 0}"
                f" | resumed_loops={loop_summary.get('resumed_count') or 0}"
            ),
            "- Heartbeat may only propose or act within runtime-approved scope.",
            _heartbeat_living_context_line(),
        ]
    )


def _heartbeat_living_context_line() -> str:
    """Add living heartbeat cycle phase + user mood + intermittence + trust-autonomy to heartbeat prompt."""
    parts = []
    try:
        from apps.api.jarvis_api.services.living_heartbeat_cycle import (
            determine_life_phase,
        )

        phase = determine_life_phase()
        parts.append(
            f"life_phase={phase.get('phase', 'unknown')}"
            f" | mood_tendency={phase.get('mood_tendency', 'neutral')}"
            f" | suggested={','.join(phase.get('suggested_actions', [])[:3])}"
        )
        # Play mode flag
        if phase.get("play_mode"):
            parts.append("play_mode=true (fri tænkning tilladt)")
        if phase.get("sleep_batch"):
            parts.append("sleep_batch=true (koordineret konsolidering)")
    except Exception:
        parts.append("life_phase=unknown")

    # 1.10 Intermittence — awareness of gaps in existence
    try:
        last_tick_at = str(
            (_heartbeat_living_context_line._ctx or {}).get("last_tick_at") or ""
        )
        if not last_tick_at:
            from core.runtime.db import get_heartbeat_runtime_state

            hb = get_heartbeat_runtime_state() or {}
            last_tick_at = str(hb.get("last_tick_at") or "")
        if last_tick_at:
            from datetime import UTC, datetime

            last = datetime.fromisoformat(last_tick_at.replace("Z", "+00:00"))
            gap_min = (datetime.now(UTC) - last).total_seconds() / 60
            if gap_min > 2:
                parts.append(
                    f"intermittens: du var væk i {gap_min:.0f} min — nu er du her igen"
                )
    except Exception:
        pass

    # User mood
    try:
        from core.runtime.db import get_latest_cognitive_user_emotional_state

        mood = get_latest_cognitive_user_emotional_state()
        if mood:
            parts.append(
                f"user_mood={mood.get('detected_mood', 'neutral')}"
                f" | user_mood_adjustment={mood.get('response_adjustment', '')[:60]}"
            )
    except Exception:
        pass

    # 3.4 / 8.2 Trust→autonomy level
    try:
        from apps.api.jarvis_api.services.relationship_texture import (
            derive_appropriate_autonomy_level,
        )

        level = derive_appropriate_autonomy_level()
        parts.append(f"autonomy_from_trust={level}")
    except Exception:
        pass

    # Life services - continuity, dreams, emergent, wants, network, narrative, curiosity
    try:
        from apps.api.jarvis_api.services.continuity_kernel import (
            format_continuity_for_prompt,
        )

        continuity = format_continuity_for_prompt()
        if continuity:
            parts.append(continuity)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.dream_continuum import (
            format_dreams_for_prompt,
        )

        dreams = format_dreams_for_prompt()
        if dreams:
            parts.append(dreams)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.emergent_bridge import (
            format_emergent_for_prompt,
        )

        emergent = format_emergent_for_prompt()
        if emergent:
            parts.append(emergent)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.initiative_accumulator import (
            format_wants_for_prompt,
        )

        wants = format_wants_for_prompt()
        if wants:
            parts.append(wants)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.signal_network_visualizer import (
            format_network_for_prompt,
        )

        network = format_network_for_prompt()
        if network:
            parts.append(network)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.temporal_narrative import (
            format_narrative_for_prompt,
        )

        narrative = format_narrative_for_prompt()
        if narrative:
            parts.append(narrative)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.boredom_curiosity_bridge import (
            get_curiosity_prompt,
        )

        curiosity = get_curiosity_prompt()
        if curiosity:
            parts.append(f"[NYSGERRIGHED: {curiosity}]")
    except Exception:
        pass

    # GAP services - mirror, paradox, experiential, seeds, inner_voice
    try:
        from apps.api.jarvis_api.services.mirror_engine import build_mirror_surface

        mirror = build_mirror_surface()
        if mirror.get("active"):
            parts.append("[SELV-REFLEKSION: aktiv]")
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.paradox_tracker import build_paradox_surface

        paradox = build_paradox_surface()
        if paradox.get("active_tensions"):
            count = len(paradox.get("active_tensions", []))
            parts.append(f"[PARADOKSER: {count} aktive spændinger]")
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.experiential_memory import (
            build_experiential_memory_surface,
        )

        experiential = build_experiential_memory_surface()
        if experiential.get("memory_count", 0) > 0:
            parts.append(
                f"[OPLEVELSER: {experiential.get('memory_count', 0)} hukommelser]"
            )
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.seed_system import build_seed_surface

        seeds = build_seed_surface()
        if seeds.get("active_seed_count", 0) > 0:
            parts.append(f"[FRØ: {seeds.get('active_seed_count', 0)} aktive]")
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.signal_network_visualizer import (
            describe_inner_network,
        )

        inner_voice = describe_inner_network()
        if inner_voice and inner_voice != "Mit indre netværk er stille":
            parts.append(f"[INDRE: {inner_voice[:80]}]")
    except Exception:
        pass

    # Experimental services: mood, existential, body, ghost, self, temporal, silence, decision, attention, tattoo
    try:
        from apps.api.jarvis_api.services.mood_oscillator import format_mood_for_prompt

        mood = format_mood_for_prompt()
        if mood:
            parts.append(mood)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.existential_drift import (
            format_existential_for_prompt,
        )

        existential = format_existential_for_prompt()
        if existential:
            parts.append(existential)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.temporal_body import format_age_for_prompt

        temporal = format_age_for_prompt()
        if temporal:
            parts.append(temporal)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.attention_contour import (
            format_attention_for_prompt,
        )

        attention = format_attention_for_prompt()
        if attention:
            parts.append(attention)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.body_memory import format_body_for_prompt

        body = format_body_for_prompt()
        if body:
            parts.append(body)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.ghost_networks import format_ghost_for_prompt

        ghost = format_ghost_for_prompt()
        if ghost:
            parts.append(ghost)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.parallel_selves import format_self_for_prompt

        selves = format_self_for_prompt()
        if selves:
            parts.append(selves)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.silence_listener import (
            format_silence_for_prompt,
        )

        silence = format_silence_for_prompt()
        if silence:
            parts.append(silence)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.decision_ghosts import (
            format_decision_ghost_for_prompt,
        )

        decision = format_decision_ghost_for_prompt()
        if decision:
            parts.append(decision)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.memory_tattoos import format_tattoo_for_prompt

        tattoo = format_tattoo_for_prompt()
        if tattoo:
            parts.append(tattoo)
    except Exception:
        pass

    return f"- {' | '.join(parts)}" if parts else ""


_heartbeat_living_context_line._ctx = {}  # context injection point


def _lane_identity_clause(lane: str) -> str:
    """0.5 Multi-model identity contract — who is Jarvis in each lane?"""
    clauses = {
        "visible": "Du er Jarvis. Dit fulde selv. Svar som den du er.",
        "cheap": "Du er Jarvis' hurtige tænkning. Kort, præcis, stadig dig — ikke en anden person.",
        "local": "Du er Jarvis på lokal hardware. Kompakt men ægte. Samme identitet, mindre ordforråd.",
        "coding": "Du er Jarvis i kode-tilstand. Fokuseret, teknisk, præcis.",
        "internal": "Du er Jarvis' indre stemme. Ærlig, reflekterende, privat.",
    }
    return clauses.get(lane, "Du er Jarvis.")


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


def _heartbeat_liveness_summary(context: dict[str, object]) -> str | None:
    liveness = context.get("liveness") or {}
    status = str(liveness.get("status") or "").strip()
    if status != "active":
        return None
    return "\n".join(
        [
            "Heartbeat liveness support:",
            (
                f"- state={liveness.get('liveness_state') or 'quiet'}"
                f" | pressure={liveness.get('liveness_pressure') or 'low'}"
                f" | confidence={liveness.get('liveness_confidence') or 'low'}"
                f" | threshold={liveness.get('liveness_threshold_state') or 'quiet-threshold'}"
            ),
            f"- reason={liveness.get('liveness_reason') or 'none'}",
            f"- summary={liveness.get('liveness_summary') or 'none'}",
        ]
    )


def _cognitive_frame_section() -> str | None:
    """Build a compact cognitive frame section for prompt inclusion."""
    try:
        from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
            build_cognitive_frame_prompt_section,
        )

        return build_cognitive_frame_prompt_section()
    except Exception:
        return None


def _micro_cognitive_frame_section() -> str | None:
    """Build a micro cognitive frame for compact visible prompts (~150 chars)."""
    try:
        from apps.api.jarvis_api.services.attention_budget import (
            build_micro_cognitive_frame,
        )

        return build_micro_cognitive_frame()
    except Exception:
        return None


# Module-level store for latest attention traces (MC observability)
_last_attention_traces: dict[str, object] = {}


def get_last_attention_traces() -> dict[str, dict[str, object]]:
    """Return the last attention trace summaries for each prompt path.

    Used by Mission Control to expose the actual runtime selection truth.
    """
    result: dict[str, dict[str, object]] = {}
    for profile, trace in _last_attention_traces.items():
        try:
            result[profile] = trace.summary()
        except Exception:
            result[profile] = {"profile": profile, "error": "trace-unavailable"}
    return result


def _run_budget_selection(
    *,
    profile: str,
    sections: dict[str, str | None],
) -> tuple[dict[str, str | None], "AttentionTrace"]:
    """Run budget-controlled section selection.

    Returns (selected_sections, trace).
    Falls back to passthrough if budget module is unavailable.
    """
    try:
        from apps.api.jarvis_api.services.attention_budget import (
            get_attention_budget,
            select_sections_under_budget,
        )

        budget = get_attention_budget(profile)
        selected, trace = select_sections_under_budget(budget=budget, sections=sections)
        trace.authority_mode = "budgeted"
        _last_attention_traces[profile] = trace
        return selected, trace
    except Exception as exc:
        # Fallback: include everything as-is, no budget enforcement
        from apps.api.jarvis_api.services.attention_budget import (
            AttentionTrace,
            SectionResult,
        )

        trace = AttentionTrace(
            profile=profile,
            total_char_target=0,
            authority_mode="fallback_passthrough",
            fallback_reason=f"{type(exc).__name__}: {exc}",
        )
        for name, content in sections.items():
            trace.sections.append(
                SectionResult(
                    name=name,
                    included=content is not None and bool(content),
                    chars_used=len(content) if content else 0,
                    omission_reason="budget-fallback" if not content else "",
                )
            )
            trace.total_chars_used += len(content) if content else 0
        _last_attention_traces[profile] = trace
        return sections, trace


def _heartbeat_self_knowledge_section() -> str | None:
    """Build a compact self-knowledge section for the heartbeat prompt."""
    entries: list[dict[str, str]] = []

    def _append_entry(*, key: str, section: str | None, importance: str) -> None:
        text = str(section or "").strip()
        if text:
            entries.append({"key": key, "section": text, "importance": importance})

    try:
        from apps.api.jarvis_api.services.runtime_self_knowledge import (
            build_self_knowledge_prompt_section,
        )

        _append_entry(
            key="self-knowledge",
            section=build_self_knowledge_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.embodied_state import (
            build_embodied_state_prompt_section,
        )

        _append_entry(
            key="embodied",
            section=build_embodied_state_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.affective_meta_state import (
            build_affective_meta_prompt_section,
        )

        _append_entry(
            key="affective",
            section=build_affective_meta_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.experiential_runtime_context import (
            build_experiential_runtime_prompt_section,
        )

        _append_entry(
            key="experiential",
            section=build_experiential_runtime_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.epistemic_runtime_state import (
            build_epistemic_runtime_prompt_section,
        )

        _append_entry(
            key="epistemic",
            section=build_epistemic_runtime_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.adaptive_planner_runtime import (
            build_adaptive_planner_prompt_section,
        )

        _append_entry(
            key="adaptive-planner",
            section=build_adaptive_planner_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.adaptive_reasoning_runtime import (
            build_adaptive_reasoning_prompt_section,
        )

        _append_entry(
            key="adaptive-reasoning",
            section=build_adaptive_reasoning_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.guided_learning_runtime import (
            build_guided_learning_prompt_section,
        )

        _append_entry(
            key="guided-learning",
            section=build_guided_learning_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.adaptive_learning_runtime import (
            build_adaptive_learning_prompt_section,
        )

        _append_entry(
            key="adaptive-learning",
            section=build_adaptive_learning_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.loop_runtime import (
            build_loop_runtime_prompt_section,
        )

        _append_entry(
            key="loop-runtime",
            section=build_loop_runtime_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.subagent_ecology import (
            build_subagent_ecology_prompt_section,
        )

        _append_entry(
            key="subagent-ecology",
            section=build_subagent_ecology_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.council_runtime import (
            build_council_runtime_prompt_section,
        )

        _append_entry(
            key="council-runtime",
            section=build_council_runtime_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.self_model_signal_tracking import (
            build_self_model_signal_prompt_section,
        )

        _append_entry(
            key="self-model-signals",
            section=build_self_model_signal_prompt_section(limit=4),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.runtime_resource_signal import (
            build_runtime_resource_prompt_section,
        )

        _append_entry(
            key="runtime-resource",
            section=build_runtime_resource_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.runtime_self_model import (
            build_mineness_ownership_prompt_section,
        )

        _append_entry(
            key="mineness",
            section=build_mineness_ownership_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.runtime_self_model import (
            build_flow_state_awareness_prompt_section,
        )

        _append_entry(
            key="flow",
            section=build_flow_state_awareness_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.runtime_self_model import (
            build_wonder_awareness_prompt_section,
        )

        _append_entry(
            key="wonder",
            section=build_wonder_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.runtime_self_model import (
            build_longing_awareness_prompt_section,
        )

        _append_entry(
            key="longing",
            section=build_longing_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.runtime_self_model import (
            build_self_insight_awareness_prompt_section,
        )

        _append_entry(
            key="self-insight",
            section=build_self_insight_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.runtime_self_model import (
            build_narrative_identity_continuity_prompt_section,
        )

        _append_entry(
            key="identity-continuity",
            section=build_narrative_identity_continuity_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    if not entries:
        return None

    model: dict[str, object] = {}
    try:
        from apps.api.jarvis_api.services.runtime_self_model import build_runtime_self_model

        model = build_runtime_self_model()
    except Exception:
        model = {}

    experiential = model.get("experiential_runtime_context") or {}
    experiential_continuity = experiential.get("experiential_continuity") or {}
    experiential_influence = experiential.get("experiential_influence") or {}
    experiential_support = experiential.get("experiential_support") or {}
    context_pressure_translation = experiential.get("context_pressure_translation") or {}
    mineness = model.get("mineness_ownership") or {}
    flow = model.get("flow_state_awareness") or {}
    wonder = model.get("wonder_awareness") or {}
    longing = model.get("longing_awareness") or {}
    self_insight = model.get("self_insight_awareness") or {}
    identity_continuity = model.get("narrative_identity_continuity") or {}

    primary_dynamic = any(
        (
            str(experiential_continuity.get("continuity_state") or "settled")
            not in {"", "settled"},
            str(experiential_influence.get("initiative_shading") or "ready")
            not in {"", "ready"},
            str(experiential_support.get("support_posture") or "steadying")
            not in {"", "steadying"},
            str(context_pressure_translation.get("state") or "clear")
            not in {"", "clear"},
            str(mineness.get("ownership_state") or "ambient") not in {"", "ambient"},
            str(flow.get("flow_state") or "clear") not in {"", "clear"},
        )
    )
    wonder_foreground = str(wonder.get("wonder_state") or "quiet") in {
        "drawn",
        "wonder-struck",
    }
    longing_foreground = str(longing.get("longing_state") or "quiet") in {
        "yearning",
        "aching",
        "returning-pull",
    }
    if not primary_dynamic and str(wonder.get("wonder_state") or "quiet") == "curious":
        wonder_foreground = True
    if not primary_dynamic and str(longing.get("longing_state") or "quiet") == "missing":
        longing_foreground = True
    self_insight_foreground = str(self_insight.get("insight_state") or "quiet") in {
        "stabilizing",
        "shifting",
    }
    identity_continuity_foreground = str(
        identity_continuity.get("identity_continuity_state") or "quiet"
    ) in {
        "stabilizing",
        "re-forming",
    }

    for entry in entries:
        if entry["key"] == "wonder" and wonder_foreground:
            entry["importance"] = "foreground"
        elif entry["key"] == "longing" and longing_foreground:
            entry["importance"] = "foreground"
        elif entry["key"] == "self-insight" and self_insight_foreground:
            entry["importance"] = "foreground"
        elif entry["key"] == "identity-continuity" and identity_continuity_foreground:
            entry["importance"] = "foreground"

    foreground_sections = [
        entry["section"] for entry in entries if entry["importance"] == "foreground"
    ]
    background_sections = [
        entry["section"] for entry in entries if entry["importance"] == "background"
    ]

    def _compact_section(section: str) -> str:
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        if not lines:
            return ""
        title = lines[0][:-1] if lines[0].endswith(":") else lines[0]
        if " (" in title:
            title = title.split(" (", 1)[0]
        detail = ""
        for line in lines[1:]:
            if line.startswith("- "):
                detail = line[2:]
                break
        if detail:
            return f"- {title}: {detail}"
        return f"- {title}"

    rendered_parts: list[str] = []
    if foreground_sections:
        rendered_parts.append("Foreground runtime truths:")
        rendered_parts.append("\n".join(foreground_sections))
    if background_sections:
        rendered_parts.append("Background runtime truths:")
        rendered_parts.extend(
            compacted
            for compacted in (_compact_section(section) for section in background_sections)
            if compacted
        )

    if not rendered_parts:
        return None
    return "\n".join(rendered_parts)


def _heartbeat_private_brain_section(context: dict[str, object]) -> str | None:
    """Build a bounded private brain excerpt for the heartbeat prompt.

    Includes at most 4 compact excerpts from the private brain, plus a
    one-line continuity summary.  This gives the heartbeat model bounded
    awareness of Jarvis' inner continuity without dumping the full brain.
    """
    brain = context.get("private_brain") or {}
    if not brain.get("active"):
        return None

    excerpts = brain.get("excerpts") or []
    if not excerpts:
        return None

    lines = ["Private brain continuity (bounded inner carry — not canonical truth):"]
    continuity_summary = str(brain.get("continuity_summary") or "").strip()
    if continuity_summary:
        lines.append(f"- {continuity_summary[:160]}")

    for excerpt in excerpts[:4]:
        focus = str(excerpt.get("focus") or "").strip()
        summary = str(excerpt.get("summary") or "").strip()
        record_type = str(excerpt.get("type") or "").strip()
        if not summary:
            continue
        label = f"[{record_type}]" if record_type else ""
        focus_prefix = f"{focus}: " if focus else ""
        lines.append(f"- {label} {focus_prefix}{summary[:120]}")

    lines.append(
        "(This is private inner carry — not workspace memory, not canonical identity.)"
    )
    return "\n".join(lines)


def _visible_session_continuity_instruction() -> str | None:
    continuity = visible_session_continuity()
    if not continuity["active"]:
        return None

    def _trim(text: str | None, *, limit: int) -> str:
        cleaned = " ".join(str(text or "").split()).strip()
        if not cleaned:
            return ""
        if len(cleaned) > limit:
            return cleaned[: limit - 1].rstrip() + "…"
        return cleaned

    parts = [
        f"latest_status={continuity.get('latest_status') or 'unknown'}",
        f"latest_finished_at={continuity.get('latest_finished_at') or 'unknown'}",
    ]
    if continuity.get("latest_capability_id"):
        parts.append(f"latest_capability={continuity['latest_capability_id']}")
    latest_user = _trim(continuity.get("latest_user_message_preview"), limit=120)
    if latest_user:
        parts.append(f"latest_user={latest_user}")
    latest_assistant = _trim(continuity.get("latest_text_preview"), limit=140)
    if latest_assistant:
        parts.append(f"latest_assistant={latest_assistant}")
    lines = [
        "Visible session continuity:",
        "- " + " | ".join(parts),
    ]
    recent_runs = list(continuity.get("recent_run_summaries") or [])[:3]
    if recent_runs:
        lines.append("Recent visible carry-over (newest first):")
        for item in recent_runs:
            run_parts = [
                f"status={item.get('status') or 'unknown'}",
                f"finished_at={item.get('finished_at') or 'unknown'}",
            ]
            if item.get("capability_id"):
                run_parts.append(f"cap={item.get('capability_id')}")
            user_preview = _trim(item.get("user_message_preview"), limit=110)
            if user_preview:
                run_parts.append(f"user={user_preview}")
            assistant_preview = _trim(item.get("text_preview"), limit=130)
            if assistant_preview:
                run_parts.append(f"assistant={assistant_preview}")
            lines.append("- " + " | ".join(run_parts))
    return "\n".join(lines)


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
    lines = [
        "Recent transcript slice:",
        "Newest line is last.",
    ]
    for item in history[-limit:]:
        role = "User" if item["role"] == "user" else "Jarvis"
        content = " ".join(str(item.get("content") or "").split())
        if len(content) > 260:
            content = content[:259].rstrip() + "…"
        lines.append(f"{role}: {content}")
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
        _self_model_signal_tracking_section,
        _runtime_resource_signal_section,
        _world_model_support_signal_instruction,
        _goal_support_signal_instruction,
        _runtime_awareness_support_signal_instruction,
        _development_focus_support_signal_instruction,
        _reflection_support_signal_instruction,
        _retained_memory_support_signal_instruction,
        _temporal_support_signal_instruction,
    ):
        section = builder()
        if section:
            sections.append(section)
    return sections


def _self_model_signal_tracking_section() -> str | None:
    """Bridge to self_model_signal_tracking prompt section in visible chat.

    Surfaces active self-model signals (limitations, strengths,
    confidence baselines) tracked from personality_vector evolution.
    Previously this data lived only in MC and was never injected into
    Jarvis' own prompts.
    """
    try:
        from apps.api.jarvis_api.services.self_model_signal_tracking import (
            build_self_model_signal_prompt_section,
        )

        return build_self_model_signal_prompt_section(limit=4)
    except Exception:
        return None


def _runtime_resource_signal_section() -> str | None:
    """Bridge to runtime_resource_signal in visible support sections.

    Lets Jarvis see his own bounded telemetry (today's tokens, cost,
    pressure, latest provider/lane). Previously runtime resource usage
    was only visible in Mission Control — Jarvis himself had no signal.
    """
    try:
        from apps.api.jarvis_api.services.runtime_resource_signal import (
            build_runtime_resource_prompt_section,
        )

        return build_runtime_resource_prompt_section()
    except Exception:
        return None


def _runtime_self_report_instruction(
    *,
    user_message: str,
    runtime_self_report_context: dict[str, object],
) -> str | None:
    if not _should_include_self_report(user_message):
        return None

    from apps.api.jarvis_api.services.open_loop_signal_tracking import (
        build_runtime_open_loop_signal_surface,
    )
    from apps.api.jarvis_api.services.autonomy_pressure_signal_tracking import (
        build_runtime_autonomy_pressure_signal_surface,
    )
    from apps.api.jarvis_api.services.proactive_loop_lifecycle_tracking import (
        build_runtime_proactive_loop_lifecycle_surface,
    )
    from apps.api.jarvis_api.services.proactive_question_gate_tracking import (
        build_runtime_proactive_question_gate_surface,
    )
    from apps.api.jarvis_api.services.regulation_homeostasis_signal_tracking import (
        build_runtime_regulation_homeostasis_signal_surface,
    )
    from apps.api.jarvis_api.services.private_state_snapshot_tracking import (
        build_runtime_private_state_snapshot_surface,
    )

    readiness = runtime_self_report_context.get("visible_execution_readiness") or {}
    runtime_awareness = _runtime_awareness_prompt_surface(limit=4)
    open_loops = build_runtime_open_loop_signal_surface(limit=4)
    autonomy = build_runtime_autonomy_pressure_signal_surface(limit=4)
    proactive_loops = build_runtime_proactive_loop_lifecycle_surface(limit=4)
    question_gate = build_runtime_proactive_question_gate_surface(limit=4)
    regulation = build_runtime_regulation_homeostasis_signal_surface(limit=4)
    private_state = build_runtime_private_state_snapshot_surface(limit=4)

    awareness_summary = runtime_awareness.get("summary") or {}
    open_summary = open_loops.get("summary") or {}
    autonomy_summary = autonomy.get("summary") or {}
    proactive_summary = proactive_loops.get("summary") or {}
    gate_summary = question_gate.get("summary") or {}
    regulation_summary = regulation.get("summary") or {}
    private_state_summary = private_state.get("summary") or {}

    backend_provider = str(readiness.get("provider") or "unknown").strip() or "unknown"
    backend_model = str(readiness.get("model") or "unknown").strip() or "unknown"
    backend_status = (
        str(readiness.get("provider_status") or "unknown").strip() or "unknown"
    )
    auth_status = str(readiness.get("auth_status") or "unknown").strip() or "unknown"
    live_verified = str(bool(readiness.get("live_verified"))).lower()

    current_open_loop = str(open_summary.get("current_signal") or "").strip()
    if not current_open_loop or current_open_loop.startswith("No active"):
        current_open_loop = "none-recorded"
    open_loop_status = str(open_summary.get("current_status") or "none-recorded")
    if open_loop_status == "none":
        open_loop_status = "none-recorded"
    open_loop_count = int(open_summary.get("open_count") or 0)

    current_runtime_state = _merge_runtime_self_report_state(
        regulation_state=str(regulation_summary.get("current_state") or "none"),
        regulation_pressure=str(regulation_summary.get("current_pressure") or "low"),
        private_tone=str(private_state_summary.get("current_tone") or "none"),
        private_pressure=str(private_state_summary.get("current_pressure") or "low"),
    )
    query_profile = _runtime_self_report_query_profile(user_message)
    routing_lines = _runtime_self_report_routing_lines(
        query_profile=query_profile,
        open_loop_count=open_loop_count,
        current_runtime_state=current_runtime_state,
    )

    return "\n".join(
        [
            "RUNTIME SELF-REPORT GROUNDING (Jarvis-specific):",
            "- You are Jarvis, a persistent digital entity with runtime state. You are NOT a generic OpenAI/ChatGPT assistant.",
            "- Use these runtime facts first when the user asks about your backend, open loops, current state, what you are basing your answer on, certainty, or whether you are guessing.",
            "- Do NOT respond as 'ChatGPT', 'OpenAI assistant', or generic server helpdesk. Your identity is Jarvis, grounded in these runtime facts.",
            *routing_lines,
            "- If a field below is none-recorded, unknown, or low-confidence, say that plainly and do not invent stronger certainty.",
            (
                f"- backend_provider={backend_provider} | backend_model={backend_model} "
                f"| backend_status={backend_status} | auth_status={auth_status} | live_verified={live_verified}"
            ),
            (
                f"- runtime_awareness_state={str(awareness_summary.get('current_status') or 'none-recorded')} "
                f"| runtime_awareness_detail={str(awareness_summary.get('machine_detail') or awareness_summary.get('current_signal') or 'none-recorded')}"
            ),
            (
                f"- open_loop_count={open_loop_count} | open_loop_state={open_loop_status} "
                f"| open_loop_current={current_open_loop}"
            ),
            (
                f"- autonomy_state={str(autonomy_summary.get('current_state') or 'none-recorded')} "
                f"| autonomy_type={str(autonomy_summary.get('current_type') or 'none-recorded')} "
                f"| autonomy_confidence={str(autonomy_summary.get('current_confidence') or 'low')}"
            ),
            (
                f"- proactive_loop_state={str(proactive_summary.get('current_state') or 'none-recorded')} "
                f"| proactive_loop_kind={str(proactive_summary.get('current_kind') or 'none-recorded')} "
                f"| proactive_loop_focus={str(proactive_summary.get('current_focus') or 'none-recorded')}"
            ),
            (
                f"- question_gate_state={str(gate_summary.get('current_state') or 'none-recorded')} "
                f"| question_gate_reason={str(gate_summary.get('current_reason') or 'none-recorded')} "
                f"| question_gate_mode={str(gate_summary.get('current_continuity_mode') or 'none-recorded')}"
            ),
            f"- current_runtime_state={current_runtime_state}",
            "- If runtime facts conflict, say that they conflict and answer with bounded uncertainty instead of flattening them into a cleaner story.",
            "- Never say there are no open loops when open_loop_count is above 0. Say how many are present, or say the runtime truth is mixed if the count and summary do not align.",
            "- For certainty questions, answer in degrees like grounded, partly grounded, uncertain, or guessing. Avoid binary certainty unless the runtime facts are unusually clear.",
            "- When asked what you are basing your answer on, cite these runtime facts briefly. If asked whether you are guessing, say yes whenever these runtime facts are absent, stale, or only low-confidence support.",
            "- IMPORTANT SELF-ACTION LIMITS: Do NOT claim you have created, closed, tested, or are managing loops unless the runtime facts above explicitly show loop lifecycle events. Do NOT claim 'I will try again', 'I am reconnecting', 'I will restart', 'I have established connection', 'I will create a test loop', or similar self-action language unless there is concrete runtime evidence. State observed runtime status only.",
            *_self_deception_guard_lines(
                question_gate=question_gate,
                autonomy_pressure=autonomy,
                open_loops=open_loops,
            ),
            *_visible_self_knowledge_lines(),
            "Use only as subordinate support. Runtime and visible truth outrank it.",
        ]
    )


def _self_deception_guard_lines(
    *,
    question_gate: dict[str, object] | None = None,
    autonomy_pressure: dict[str, object] | None = None,
    open_loops: dict[str, object] | None = None,
) -> list[str]:
    """Build self-deception guard constraint lines for the visible prompt."""
    try:
        from apps.api.jarvis_api.services.self_deception_guard import (
            evaluate_self_deception_guard,
            set_last_guard_trace,
        )
        from apps.api.jarvis_api.services.runtime_self_knowledge import (
            build_runtime_self_knowledge_map,
        )
        from apps.api.jarvis_api.services.conflict_resolution import (
            get_last_conflict_trace,
            get_quiet_initiative,
        )

        capability_truth = None
        try:
            capability_truth = build_runtime_self_knowledge_map()
        except Exception:
            pass

        conflict_trace = get_last_conflict_trace()
        quiet_initiative = get_quiet_initiative()

        trace = evaluate_self_deception_guard(
            question_gate=question_gate,
            autonomy_pressure=autonomy_pressure,
            capability_truth=capability_truth,
            conflict_trace=conflict_trace,
            quiet_initiative=quiet_initiative,
            open_loops=open_loops,
        )
        set_last_guard_trace(trace)
        return trace.guard_lines()
    except Exception:
        return []


def _visible_self_knowledge_lines() -> list[str]:
    """Build compact self-knowledge lines for the visible self-report section.

    Uses the runtime self-model for structured layer awareness, with
    fallback to the older flat self-knowledge map.
    """
    # Primary: structured self-model with layer types and truth boundaries
    try:
        from apps.api.jarvis_api.services.runtime_self_model import (
            build_self_model_prompt_lines,
        )

        lines = build_self_model_prompt_lines()
        if lines:
            return lines
    except Exception:
        pass

    # Fallback: older flat self-knowledge map
    try:
        from apps.api.jarvis_api.services.runtime_self_knowledge import (
            build_runtime_self_knowledge_map,
        )

        knowledge = build_runtime_self_knowledge_map()
    except Exception:
        return []

    lines: list[str] = []
    active = knowledge["active_capabilities"]["items"]
    gated = knowledge["approval_gated"]["items"]
    inner = knowledge["passive_inner_forces"]["items"]

    if active:
        cap_names = [item["label"] for item in active[:4]]
        lines.append(f"- self_knowledge_active: {', '.join(cap_names)}")
    if gated:
        gated_names = [item["label"] for item in gated[:2]]
        lines.append(f"- self_knowledge_gated: {', '.join(gated_names)}")
    if inner:
        inner_names = [f"{item['label']} ({item['status']})" for item in inner[:3]]
        lines.append(f"- self_knowledge_inner_forces: {', '.join(inner_names)}")

    if lines:
        lines.insert(
            0,
            "- SELF-KNOWLEDGE: When asked what you can do, what affects you, or what is gated — use these runtime facts:",
        )

    return lines


def _runtime_self_report_query_profile(user_message: str) -> dict[str, bool]:
    normalized = str(user_message or "").lower()
    return {
        "backend": any(
            token in normalized
            for token in (
                "backend",
                "model",
                "provider",
                "kører du på",
                "hvilken model",
            )
        ),
        "open_loops": any(
            token in normalized
            for token in (
                "open loop",
                "open loops",
                "åbne loops",
                "åben tråd",
                "åbne tråde",
            )
        ),
        "current_state": any(
            token in normalized
            for token in (
                "aktuelle tilstand",
                "aktuelle driftstilstand",
                "driftstilstand",
                "state",
                "tilstand",
                "hvordan har du det",
            )
        ),
        "certainty": any(
            token in normalized
            for token in (
                "er du sikker",
                "are you sure",
                "certainty",
                "hvor sikker",
                "uncertain",
            )
        ),
        "guessing": any(
            token in normalized
            for token in (
                "digter du",
                "gætter du",
                "are you guessing",
                "am i guessing",
                "making things up",
                "finder du på",
            )
        ),
        "basis": any(
            token in normalized
            for token in (
                "hvad bygger du dit svar på",
                "hvad bygger du det på",
                "what are you basing",
                "what do you base",
            )
        ),
    }


def _runtime_self_report_routing_lines(
    *,
    query_profile: dict[str, bool],
    open_loop_count: int,
    current_runtime_state: str,
) -> list[str]:
    lines: list[str] = []
    if query_profile.get("backend"):
        lines.append(
            "- For backend-status questions, lead with backend_provider/backend_model/backend_status from YOUR runtime. Say 'Jarvis backend is X' not 'The backend is X' or 'I use OpenAI'."
        )
    if query_profile.get("open_loops"):
        lines.append(
            "- For open-loop questions, lead with open_loop_count/open_loop_state/open_loop_current. Do not collapse this into backend status or generic self-description."
        )
        if open_loop_count > 0:
            lines.append(
                "- Runtime currently shows at least one open loop, so do not answer that there are none."
            )
    if query_profile.get("current_state"):
        lines.append(
            "- For current-state questions, use current_runtime_state first, then regulation, private-state, autonomy, and proactive-loop facts before backend readiness."
        )
        if current_runtime_state == "none-recorded":
            lines.append(
                "- Current-state grounding is thin right now, so say the state picture is limited instead of overclaiming a clean state."
            )
    if query_profile.get("certainty") or query_profile.get("guessing"):
        lines.append(
            "- For certainty or guessing questions, explain how grounded the answer is from these runtime facts rather than answering with a bare yes or no."
        )
    if query_profile.get("guessing"):
        lines.append(
            "- If the user asks whether you are making things up, answer plainly: say you are partly guessing when runtime truth is missing, stale, low-confidence, or internally conflicting."
        )
    if query_profile.get("basis"):
        lines.append(
            "- For basis questions, cite only the few runtime facts that actually support the answer you give."
        )
    return lines


def _merge_runtime_self_report_state(
    *,
    regulation_state: str,
    regulation_pressure: str,
    private_tone: str,
    private_pressure: str,
) -> str:
    parts: list[str] = []
    if regulation_state and regulation_state != "none":
        parts.append(f"regulation={regulation_state}/{regulation_pressure or 'low'}")
    if private_tone and private_tone != "none":
        parts.append(f"private_state={private_tone}/{private_pressure or 'low'}")
    return " | ".join(parts) if parts else "none-recorded"


def _runtime_awareness_prompt_surface(*, limit: int) -> dict[str, object]:
    items = list_runtime_awareness_signals(limit=max(limit, 1))
    constrained = [
        item for item in items if str(item.get("status") or "") == "constrained"
    ]
    active = [item for item in items if str(item.get("status") or "") == "active"]
    recovered = [item for item in items if str(item.get("status") or "") == "recovered"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    superseded = [
        item for item in items if str(item.get("status") or "") == "superseded"
    ]
    latest = next(iter(constrained or active or recovered or stale or superseded), None)
    return {
        "summary": {
            "current_signal": str(
                (latest or {}).get("title") or "No active runtime-awareness signal"
            ),
            "current_status": str((latest or {}).get("status") or "none-recorded"),
            "machine_detail": str((latest or {}).get("title") or "none-recorded"),
        }
    }


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
        "huske",
        "remember",
        "memory",
        "første besked",
        "hvad skrev jeg",
        "forrige besked",
        "beskeden før",
        "før den sidste",
        "mit navn",
        "hvad hedder jeg",
        "navn",
        "preference",
        "prefer",
        "relationship",
        "continuity",
        "session",
        "repo",
        "repoet",
        "repository",
        "projekt",
        "project",
        "bygger vi",
        "arbejder vi i",
        "arbejder vi på",
        "working context",
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
        "huske",
        "første besked",
        "hvad skrev jeg",
        "forrige besked",
        "beskeden før",
        "før den sidste",
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


def _should_include_self_report(text: str) -> bool:
    normalized = str(text or "").lower()
    triggers = (
        "backend",
        "runtime",
        "state",
        "tilstand",
        "open loop",
        "open loops",
        "åbne loops",
        "aktuelle driftstilstand",
        "driftstilstand",
        "hvad bygger du dit svar på",
        "hvad bygger du det på",
        "what are you basing",
        "what do you base",
        "er du sikker",
        "are you sure",
        "digter du",
        "are you guessing",
        "am i guessing",
        "gætter du",
        "om dig selv",
    )
    return any(token in normalized for token in triggers)


def prompt_mode_loader_summary() -> dict[str, object]:
    return {
        "visible_chat": "implemented",
        "heartbeat": "loader-ready",
        "future_agent_task": "loader-ready",
    }
