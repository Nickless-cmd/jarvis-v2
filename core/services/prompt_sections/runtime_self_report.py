"""Runtime self-report + self-model prompt sections.

Udskilt fra core/services/prompt_contract.py (Boy Scout-split, hot-path-sikker
kode-flytning, 0 logik-ændring). Re-importeret i prompt_contract under de
oprindelige private navne, så eksisterende call-sites (orchestratoren i
build_visible_chat_prompt_assembly) + tests' monkeypatch fortsat virker.

Kun ren flytning — ingen adfærdsændring.
"""
from __future__ import annotations

from core.runtime.db import list_runtime_awareness_signals


def _self_model_signal_tracking_section() -> str | None:
    """Bridge to self_model_signal_tracking prompt section in visible chat.

    Surfaces active self-model signals (limitations, strengths,
    confidence baselines) tracked from personality_vector evolution.
    Previously this data lived only in MC and was never injected into
    Jarvis' own prompts.
    """
    try:
        from core.services.self_model_signal_tracking import (
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
        from core.services.runtime_resource_signal import (
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

    from core.services.open_loop_signal_tracking import (
        build_runtime_open_loop_signal_surface,
    )
    from core.services.autonomy_pressure_signal_tracking import (
        build_runtime_autonomy_pressure_signal_surface,
    )
    from core.services.proactive_loop_lifecycle_tracking import (
        build_runtime_proactive_loop_lifecycle_surface,
    )
    from core.services.proactive_question_gate_tracking import (
        build_runtime_proactive_question_gate_surface,
    )
    from core.services.regulation_homeostasis_signal_tracking import (
        build_runtime_regulation_homeostasis_signal_surface,
    )
    from core.services.private_state_snapshot_tracking import (
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

    from core.services.identity_composer import get_entity_name as _gn4
    _ent = _gn4()
    return "\n".join(
        [
            f"RUNTIME SELF-REPORT GROUNDING ({_ent}-specific):",
            f"- You are {_ent}, a persistent digital entity with runtime state. You are NOT a generic OpenAI/ChatGPT assistant.",
            "- Use these runtime facts first when the user asks about your backend, open loops, current state, what you are basing your answer on, certainty, or whether you are guessing.",
            f"- Do NOT respond as 'ChatGPT', 'OpenAI assistant', or generic server helpdesk. Your identity is {_ent}, grounded in these runtime facts.",
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
        from core.services.self_deception_guard import (
            evaluate_self_deception_guard,
            set_last_guard_trace,
        )
        from core.services.runtime_self_knowledge import (
            build_runtime_self_knowledge_map,
        )
        from core.services.conflict_resolution import (
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
        from core.services.runtime_self_model import (
            build_self_model_prompt_lines,
        )

        lines = build_self_model_prompt_lines()
        if lines:
            return lines
    except Exception:
        pass

    # Fallback: older flat self-knowledge map
    try:
        from core.services.runtime_self_knowledge import (
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
        from core.services.identity_composer import get_entity_name as _gn5
        _ent5 = _gn5()
        lines.append(
            f"- For backend-status questions, lead with backend_provider/backend_model/backend_status from YOUR runtime. Say '{_ent5} backend is X' not 'The backend is X' or 'I use OpenAI'."
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
