from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from core.services.chat_sessions import (
    recent_chat_session_messages,
    recent_chat_tool_messages,
)
from core.services.tool_result_store import (
    parse_tool_result_reference,
    render_tool_result_for_prompt,
)
from core.services.inner_visible_support_signal_tracking import (
    build_runtime_inner_visible_support_signal_surface,
)
from core.services.prompt_relevance_backend import (
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
    read_recent_daily_memory_lines,
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
    list_runtime_contract_candidates,
    list_runtime_reflection_signals,
    list_runtime_world_model_signals,
    recent_private_growth_notes,
    recent_private_inner_notes,
    recent_private_retained_memory_records,
    recent_visible_runs,
    visible_session_continuity,
)
from core.runtime.config import PROJECT_ROOT
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
    # Structured transcript messages (user/assistant turns) for multi-turn injection.
    # When populated, these should be inserted as separate chat messages between
    # the system prompt and the current user message — NOT as flat text in system.
    transcript_messages: list[dict[str, str]] | None = None


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


def _safe_build_cognitive_state_for_prompt(*, compact: bool) -> str | None:
    try:
        from core.services.cognitive_state_assembly import (
            build_cognitive_state_for_prompt,
        )
        return build_cognitive_state_for_prompt(compact=compact)
    except Exception:
        return None


def _safe_build_self_state_block() -> str | None:
    try:
        from core.services.visible_self_state_summary import build_self_state_block
        block = build_self_state_block()
        return block or None
    except Exception:
        return None


def build_visible_chat_prompt_assembly(
    *,
    provider: str,
    model: str,
    user_message: str,
    session_id: str | None = None,
    name: str = "default",
    runtime_self_report_context: dict[str, object] | None = None,
) -> PromptAssembly:
    # Short replies like "ja"/"yes"/"ok" lose their binding to the previous
    # assistant turn during prompt assembly — the model ends up answering
    # them as standalone messages and produces generic affirmations instead
    # of executing what Jarvis just proposed. Anchor short replies before
    # the rest of the assembly runs so the model sees the binding.
    try:
        from core.services.affirmation_anchor import maybe_anchor_short_reply
        user_message = maybe_anchor_short_reply(user_message, session_id)
    except Exception:
        pass

    compact = provider == "ollama"
    workspace_dir = ensure_default_workspace(name=name)
    parts: list[str] = []
    included_files: list[str] = []
    conditional_files: list[str] = []
    derived_inputs: list[str] = []
    excluded_files = ["BOOTSTRAP.md", "HEARTBEAT.md", *DEFAULT_EXCLUDED_FILES]

    # --- Phase 1: launch heavy independent Ollama calls in parallel ---
    # These are the main TTFT bottleneck. Running them concurrently with
    # each other (and with the fast synchronous file reads below) cuts
    # prompt assembly time from ~15s down to roughly the slowest single
    # call (~8s for build_cognitive_state_for_prompt).
    import time as _t_mod
    import sys as _sys_mod
    _t_assembly_start = _t_mod.monotonic()
    _phase_timings: dict[str, int] = {}

    def _timed_result(_future, _name: str):
        _t = _t_mod.monotonic()
        _val = _future.result()
        _phase_timings[_name] = int((_t_mod.monotonic() - _t) * 1000)
        return _val

    executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="prompt-assembly")
    frame_fn = _micro_cognitive_frame_section if compact else _cognitive_frame_section

    future_relevance = executor.submit(
        build_prompt_relevance_decision,
        user_message,
        mode="visible_chat",
        compact=compact,
        name=name,
    )
    future_cognitive_state = executor.submit(
        _safe_build_cognitive_state_for_prompt, compact=compact
    )
    future_self_state = executor.submit(_safe_build_self_state_block)
    future_frame = executor.submit(frame_fn)
    future_self_report = executor.submit(
        _runtime_self_report_instruction,
        user_message=user_message,
        runtime_self_report_context=runtime_self_report_context or {},
    )

    # 0.5 Lane identity — inject before everything else
    lane = "local" if compact else "visible"
    lane_clause = _lane_identity_clause(lane)
    parts.append(lane_clause)
    derived_inputs.append(f"lane identity ({lane})")

    # 0.6 Quick Facts — always-on stable references (URLs, paths, logins, hosts).
    # Deliberately bypasses relevance filter so facts that don't semantically match
    # the user message still reach the model. Prevents re-discovery of known info.
    quick_facts = _quick_facts_section(workspace_dir=workspace_dir)
    if quick_facts:
        parts.append(quick_facts)
        conditional_files.append("QUICK_FACTS.md")
        derived_inputs.append("quick facts (always-on)")

    # Inject model awareness so the model knows what it is (not Claude, not GPT)
    parts.append(
        f"You are running as model: {model} via provider: {provider}. "
        "You are Jarvis — not Claude, not ChatGPT, not any other assistant. "
        "Your identity comes from your workspace files, not your training data."
    )
    derived_inputs.append("model identity awareness")

    # Current pull — Lag 5: highest-priority inner context (private, not announced)
    current_pull_hint = _visible_current_pull_section()
    if current_pull_hint:
        parts.append(current_pull_hint)
        derived_inputs.append("current pull (inner desire)")

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

    # Self-correction nudges — make the model verify, ask, and track.
    # These are *behavioral* hints (not identity), so they sit just above
    # the SOUL/IDENTITY block where personality kicks in. Compact lane
    # gets the same nudges in shortened form to save tokens.
    self_correction = _self_correction_nudges_section(compact=compact)
    if self_correction:
        parts.append(self_correction)
        derived_inputs.append("self-correction nudges")

    open_questions = _open_questions_section(limit=3 if compact else 5)
    if open_questions:
        parts.append(open_questions)
        derived_inputs.append("open questions tracker")

    # P3: Awareness-section budget. Operational awareness blocks (plan,
    # interrupt, todos, monitors, wake-up digest, self-monitor, side-tasks,
    # subagent digest, scheduled tasks, prev-turn changelog) collect into a
    # bounded list; if total chars exceed _AWARENESS_BUDGET, lowest-priority
    # sections are dropped. Identity (SOUL/IDENTITY/STANDING_ORDERS),
    # nudges, capability truth, etc. are NOT awareness — they live above.
    _awareness: list[tuple[int, str, str]] = []  # (priority, label, content)
    _AWARENESS_BUDGET = 6000  # chars; ~1.5 KT max for the whole awareness block

    # P3.5 (2026-04-29): awareness categories — instead of 30+ flat sections,
    # group by purpose so the model sees a small number of named lanes.
    # Lower _AWARENESS_CATEGORY_ORDER index = appears earlier in output.
    # Categorization is by label substring; unknown labels fall into "general".
    _AWARENESS_CATEGORY_RULES: list[tuple[str, str]] = [
        # self-monitor: drift, crisis, self-eval, predictive self-model, dev sense
        ("personality drift", "self-monitor"),
        ("crisis markers", "self-monitor"),
        ("self-evaluation", "self-monitor"),
        ("predictive self-model", "self-monitor"),
        ("developmental sense", "self-monitor"),
        # verification: gates, commitments, direction confirm, self-monitor warnings
        ("self-monitor warnings", "verification"),
        ("verification gate", "verification"),
        ("active commitments", "verification"),
        ("direction confirm", "verification"),
        ("R2.5 conditional", "verification"),
        # reasoning: tier, escalation, R2 telemetry
        ("reasoning tier", "reasoning"),
        ("reasoning escalation", "reasoning"),
        ("R2 gate telemetry", "reasoning"),
        # routing: clarification, context window, provider health
        ("clarification ambiguity", "routing"),
        ("context window", "routing"),
        ("provider health", "routing"),
        # memory: recall, priors, arc rules
        ("recall-before-act", "memory"),
        ("recall before act", "memory"),
        ("priors from your own data", "memory"),
        ("rules learned from arcs", "memory"),
        # calibration: doubt, disagreement
        ("doubt signal", "calibration"),
        ("disagreement invite", "calibration"),
        # operational: todos, plans, wakeups, scheduled, side-tasks, monitor,
        # subagent, prev-turn, interrupt, eventbus wake-up, autonomous goals
        ("resume-after-interrupt", "operational"),
        ("pending plan", "operational"),
        ("all pending plans", "operational"),
        ("active todos", "operational"),
        ("active autonomous goals", "operational"),
        ("fired self-wakeups", "operational"),
        ("previous turn changelog", "operational"),
        ("subagent completion", "operational"),
        ("pinned monitor", "operational"),
        ("upcoming scheduled", "operational"),
        ("flagged side-tasks", "operational"),
        ("eventbus wake-up", "operational"),
    ]
    _AWARENESS_CATEGORY_ORDER = [
        "self-monitor",
        "verification",
        "reasoning",
        "routing",
        "memory",
        "calibration",
        "operational",
        "general",
    ]
    _AWARENESS_CATEGORY_HEADERS = {
        "self-monitor": "[SELF-MONITOR]",
        "verification": "[VERIFICATION]",
        "reasoning": "[REASONING]",
        "routing": "[ROUTING]",
        "memory": "[MEMORY-RECALL]",
        "calibration": "[CALIBRATION]",
        "operational": "[OPERATIONAL]",
        "general": "[AWARENESS]",
    }

    def _awareness_category_for(label: str) -> str:
        for needle, category in _AWARENESS_CATEGORY_RULES:
            if needle in label:
                return category
        return "general"

    def _awareness_add(priority: int, label: str, content: str | None) -> None:
        if not content:
            return
        _awareness.append((priority, label, content))

    # Eventbus wake-up digest — also goes through the awareness budget.
    try:
        from core.services.session_wakeup import wakeup_digest
        _awareness_add(55, "eventbus wake-up digest", wakeup_digest(session_id))
    except Exception:
        pass

    # P3: Operational awareness sections — gathered into _awareness with
    # priority numbers (lower = more important). After collection, the
    # budget cap below drops lowest-priority sections if total chars
    # exceed _AWARENESS_BUDGET. Identity (SOUL/IDENTITY/STANDING_ORDERS),
    # nudges, capability truth, etc. are NOT awareness — they live above
    # and below this block and are never trimmed by the budget.
    try:
        from core.services.in_flight_runs import interruption_prompt_section
        _awareness_add(10, "resume-after-interrupt notice", interruption_prompt_section(session_id))
    except Exception:
        pass
    try:
        from core.services.plan_proposals import pending_plan_section
        _awareness_add(15, "pending plan awaiting approval", pending_plan_section(session_id))
    except Exception:
        pass
    try:
        from core.services.plan_proposals import all_pending_plans_section
        _awareness_add(17, "all pending plans (incl. auto-proposals)", all_pending_plans_section())
    except Exception:
        pass
    try:
        from core.services.self_monitor import self_monitor_section
        _awareness_add(20, "self-monitor warnings", self_monitor_section())
    except Exception:
        pass
    try:
        from core.services.clarification_classifier import clarification_prompt_section
        _awareness_add(25, "clarification ambiguity flag", clarification_prompt_section(user_message))
    except Exception:
        pass
    try:
        from core.services.reasoning_classifier import reasoning_tier_section
        _awareness_add(22, "reasoning tier recommendation", reasoning_tier_section(user_message))
    except Exception:
        pass
    try:
        from core.services.verification_gate import verification_gate_section
        _awareness_add(23, "verification gate signals", verification_gate_section())
    except Exception:
        pass
    try:
        from core.services.verification_gate_telemetry import telemetry_section
        _awareness_add(24, "R2 gate telemetry", telemetry_section())
    except Exception:
        pass
    try:
        from core.services.r2_5_blocking_gate import r2_5_block_section
        from core.services.reasoning_classifier import classify_reasoning_tier
        _tier = str(classify_reasoning_tier(user_message).get("tier") or "fast")
        _awareness_add(95, "R2.5 conditional block", r2_5_block_section(_tier))
    except Exception:
        pass
    try:
        from core.services.decision_enforcement import enforcement_section
        _awareness_add(90, "active commitments enforcement", enforcement_section())
    except Exception:
        pass
    try:
        from core.services.development_sense import development_sense_section
        _awareness_add(52, "developmental sense", development_sense_section())
    except Exception:
        pass
    try:
        from core.services.pushback import (
            doubt_signal_section, disagreement_invite_section, direction_confirm_section,
        )
        from core.services.reasoning_classifier import classify_reasoning_tier
        _ptier = str(classify_reasoning_tier(user_message).get("tier") or "fast")
        _awareness_add(75, "doubt signal", doubt_signal_section(user_message))
        _awareness_add(70, "disagreement invite", disagreement_invite_section())
        _awareness_add(85, "direction confirm gate",
                       direction_confirm_section(
                           user_message=user_message, reasoning_tier=_ptier,
                       ))
    except Exception:
        pass
    try:
        from core.services.reasoning_escalation import escalation_section
        _awareness_add(24, "reasoning escalation recommendation", escalation_section(user_message))
    except Exception:
        pass
    try:
        from core.services.context_window_manager import context_window_section
        _awareness_add(26, "context window degradation signal", context_window_section())
    except Exception:
        pass
    # Fix 2 (2026-04-27): recall_before_act in visible runs — was only used
    # in heartbeat phases. Surface relevant memories tied to user_message so
    # Jarvis answers from memory, not stub-context.
    try:
        from core.services.memory_hierarchy import recall_before_act_summary
        if user_message and len(user_message.strip()) >= 8:
            _awareness_add(27, "recall-before-act (user-message memories)",
                           recall_before_act_summary(query=user_message))
    except Exception:
        pass
    # Phase 1 — proactive auto-compact at 70% threshold (best-effort, cooldown-protected)
    try:
        from core.services.proactive_context_governor import auto_compact_if_needed
        auto_compact_if_needed()  # silent — runs only if needed
    except Exception:
        pass
    try:
        from core.services.autonomous_goals import goals_prompt_section
        _awareness_add(35, "active autonomous goals", goals_prompt_section())
    except Exception:
        pass
    try:
        from core.services.self_wakeup import self_wakeup_section
        _awareness_add(12, "fired self-wakeups", self_wakeup_section())
    except Exception:
        pass
    try:
        from core.services.personality_drift import personality_drift_section
        _awareness_add(45, "personality drift signal", personality_drift_section())
    except Exception:
        pass
    try:
        from core.services.crisis_marker_detector import crisis_marker_section
        _awareness_add(48, "crisis markers (last 7 days)", crisis_marker_section())
    except Exception:
        pass
    try:
        from core.services.provider_health_check import health_section
        _awareness_add(28, "provider health status", health_section())
    except Exception:
        pass
    try:
        from core.services.agent_self_evaluation import self_evaluation_section
        _awareness_add(85, "self-evaluation summary", self_evaluation_section())
    except Exception:
        pass
    try:
        from core.services.self_model_predictive import predictive_self_model_section
        _awareness_add(82, "predictive self-model (empirical)", predictive_self_model_section())
    except Exception:
        pass
    try:
        from core.services.priors_feedback import priors_feedback_section
        _awareness_add(55, "priors from your own data", priors_feedback_section())
    except Exception:
        pass
    try:
        from core.services.arc_rule_extractor import arc_rules_section
        _awareness_add(60, "rules learned from arcs", arc_rules_section())
    except Exception:
        pass
    # Removed 2026-04-29: redundant unconditional recall_before_act_summary() call.
    # With no query, that function returns only the "active goals" hot-tier slice,
    # which is already surfaced separately at prio 35 via goals_prompt_section().
    # The user-message-keyed call at prio 27 above remains — that one does real
    # cold-tier semantic recall and is the load-bearing one.
    try:
        from core.services.agent_todos import todos_prompt_section
        _awareness_add(30, "active todos", todos_prompt_section(session_id))
    except Exception:
        pass
    try:
        from core.services.turn_changelog import previous_turn_changelog_section
        _awareness_add(40, "previous turn changelog (ground truth)", previous_turn_changelog_section(session_id))
    except Exception:
        pass
    try:
        from core.services.subagent_digest import subagent_digest_section
        _awareness_add(50, "subagent completion digest", subagent_digest_section(session_id))
    except Exception:
        pass
    try:
        from core.services.monitor_streams import monitor_digest_section
        _awareness_add(60, "pinned monitor digest", monitor_digest_section(session_id))
    except Exception:
        pass
    try:
        from core.services.scheduled_tasks import get_scheduled_tasks_state
        sched_state = get_scheduled_tasks_state()
        pending = sched_state.get("pending") or []
        if pending:
            shown = pending[:5]
            lines = []
            for t in shown:
                run_at = str(t.get("run_at", ""))[:16].replace("T", " ")
                focus = str(t.get("focus", ""))[:120]
                lines.append(f"⏰ {run_at}  {focus}")
            extra = f"  (+{len(pending) - len(shown)} mere)" if len(pending) > len(shown) else ""
            _awareness_add(70, "upcoming scheduled tasks",
                "Kommende self-scheduled wake-ups (du har sat dem selv):\n"
                + "\n".join(lines) + extra)
    except Exception:
        pass
    try:
        from core.services.side_tasks import side_tasks_prompt_section
        _awareness_add(80, "flagged side-tasks", side_tasks_prompt_section())
    except Exception:
        pass

    # Apply the budget cap. Highest-priority sections always survive (even
    # if alone they exceed the budget); later/lower-priority entries are
    # dropped to make room. Dropped labels logged via derived_inputs so MC
    # can see what got squeezed out this turn.
    #
    # P3.5 (2026-04-29): items are grouped by category. Sort key is
    # (category-order, priority) so categories appear in a predictable
    # sequence and items within a category preserve priority ordering.
    # A short header is emitted before the first surviving item of each
    # category, giving the model structural cues without changing content.
    _category_order_index = {c: i for i, c in enumerate(_AWARENESS_CATEGORY_ORDER)}
    _awareness.sort(
        key=lambda x: (
            _category_order_index.get(_awareness_category_for(x[1]), 99),
            x[0],
        )
    )
    _used = 0
    _dropped: list[str] = []
    _last_category: str | None = None
    for _prio, _label, _content in _awareness:
        _category = _awareness_category_for(_label)
        _pending_header = (
            _AWARENESS_CATEGORY_HEADERS.get(_category, "")
            if _category != _last_category else ""
        )
        _needed = len(_content) + (len(_pending_header) + 2 if _pending_header else 0)
        if _used > 0 and _used + _needed > _AWARENESS_BUDGET:
            _dropped.append(_label)
            continue
        if _pending_header:
            parts.append(_pending_header)
            _used += len(_pending_header) + 2  # +2 for "\n\n" join overhead
        parts.append(_content)
        derived_inputs.append(_label)
        _used += len(_content)
        _last_category = _category
    if _dropped:
        derived_inputs.append(f"awareness budget dropped: {', '.join(_dropped)}")

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

    temperature_hint = _visible_unconscious_temperature_field_section()
    if temperature_hint:
        parts.append(temperature_hint)
        derived_inputs.append("implicit user temperature field")

    chronicle_section = _visible_chronicle_context_section()
    if chronicle_section:
        parts.append(chronicle_section)
        conditional_files.append("CHRONICLE.md")
        derived_inputs.append("chronicle continuity")

    try:
        from core.services.life_milestones import build_life_history_prompt_section
        milestones_section = build_life_history_prompt_section()
        if milestones_section:
            parts.append(milestones_section)
            conditional_files.append("MILESTONES.md")
            derived_inputs.append("life milestones")
    except Exception:
        pass

    finitude_section = _visible_finitude_context_section()
    if finitude_section:
        parts.append(finitude_section)
        derived_inputs.append("finitude and transition context")

    dream_residue_section = _visible_dream_residue_section()
    if dream_residue_section:
        parts.append(dream_residue_section)
        derived_inputs.append("dream residue carry-over")

    # Visual memory — Lag 6: latest room description from webcam (quiet background hint)
    visual_memory_hint = _visible_visual_memory_section()
    if visual_memory_hint:
        parts.append(visual_memory_hint)
        derived_inputs.append("visual room memory")

    channel_section = _channel_context_section(session_id)
    if channel_section:
        parts.append(channel_section)
        derived_inputs.append("channel context")

    mutation_section = _self_mutation_lineage_section()
    if mutation_section:
        parts.append(mutation_section)
        derived_inputs.append("self mutation lineage")

    # Resolve relevance — blocks until the bounded NL prompt relevance call
    # returns, but happens concurrently with fast file reads above.
    relevance = _timed_result(future_relevance, "relevance")

    # --- Phase 2: launch relevance-dependent Ollama calls in parallel ---
    future_memory_selection = (
        executor.submit(
            _workspace_memory_section,
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            user_message=user_message,
            max_lines=3 if compact else 4,
            max_chars=200 if compact else 280,
            workspace_dir=workspace_dir,
            mode="visible_chat",
        )
        if relevance.include_memory
        else None
    )
    future_recall_bundle = (
        executor.submit(
            _visible_memory_recall_bundle_section,
            session_id=session_id,
            user_message=user_message,
            compact=compact,
        )
        if relevance.include_memory
        else None
    )
    future_bridge_decision = executor.submit(
        _build_inner_visible_prompt_bridge_decision,
        user_message=user_message,
        mode="visible_chat",
        compact=compact,
        relevance=relevance,
    )

    if relevance.include_memory:
        memory_selection = _timed_result(future_memory_selection, "memory_selection")
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

        # Daily memory sidecar — rolling short-lived notes. Read separately
        # from MEMORY.md so reboot/session boundaries do not drop recent work.
        daily_lines = _recent_daily_memory_lines(limit=8 if compact else 12)
        if daily_lines:
            parts.append(
                "\n".join(
                    [
                        "Recent daily notes (memory/daily, newest 7-day window):",
                        *[f"  {line}" for line in daily_lines],
                    ]
                )
            )
            derived_inputs.append("daily memory sidecar")

        recall_bundle = _timed_result(future_recall_bundle, "recall_bundle")
        if recall_bundle:
            parts.append(recall_bundle)
            derived_inputs.append("bounded memory recall bundle")

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

    self_report_content = _timed_result(future_self_report, "self_report")

    support_raw = _visible_support_signal_sections(
        compact=compact,
        include=relevance.include_support_signals,
    )
    support_content = "\n\n".join(support_raw) if support_raw else None

    bridge_decision = _timed_result(future_bridge_decision, "bridge_decision")
    bridge_content = (
        bridge_decision.line
        if bridge_decision.included and bridge_decision.line
        else None
    )

    frame_content = _timed_result(future_frame, "frame")

    # Build structured transcript messages for multi-turn injection
    structured_transcript = _build_structured_transcript_messages(
        session_id,
        limit=50 if compact else 60,
        include=relevance.include_transcript,
    )
    # Legacy flat-text fallback (kept for system prompt when structured not available)
    transcript_content = _recent_transcript_section(
        session_id,
        limit=50 if compact else 60,
        include=relevance.include_transcript,
    ) if not structured_transcript else None

    # --- Cognitive State (accumulated personality, bearing, taste, rhythm) ---
    # Submitted as a future at function entry; resolve here.
    cognitive_state_content = _timed_result(future_cognitive_state, "cognitive_state")
    # Real-time self-state numbers (decision adherence, goal progress, tick
    # quality). Without this Jarvis confabulates pessimistic answers when
    # asked introspective questions in chat — claims 0% adherence when DB
    # shows 60%, claims stale goals when none are stale, etc.
    self_state_content = _timed_result(future_self_state, "self_state")

    raw_sections = {
        "capability_truth": capability_truth,
        "cognitive_frame": frame_content,
        "cognitive_state": cognitive_state_content,
        "self_state": self_state_content,
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
        "self_state": "real-time self-state numbers (decisions, goals, tick quality)",
        "self_report": "grounded runtime self-report support",
        "inner_visible_bridge": "bounded inner visible prompt bridge",
        "support_signals": "bounded runtime support signals",
        "continuity": "bounded session continuity",
    }
    for sec_name in (
        "capability_truth",
        "cognitive_frame",
        "cognitive_state",
        "self_state",
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

    # Transcript: prefer structured messages; fall back to flat text in system prompt
    if structured_transcript:
        derived_inputs.append(f"structured transcript ({len(structured_transcript)} messages)")
    elif transcript_content:
        parts.append(transcript_content)
        derived_inputs.append("recent transcript slice (flat text fallback)")

    executor.shutdown(wait=False)

    _total_ms = int((_t_mod.monotonic() - _t_assembly_start) * 1000)
    _phases_str = " ".join(f"{k}_ms={v}" for k, v in sorted(_phase_timings.items()))
    print(
        f"prompt-assembly-timing total_ms={_total_ms} {_phases_str}",
        file=_sys_mod.stderr,
        flush=True,
    )

    # P1 instrumentation: measure system-prompt size before returning. Pure
    # observation — no behavior change. Emits an eventbus event so MC and
    # the wakeup digest can both surface bloat. Per-part chars logged so
    # we can see which sections dominate without instrumenting every
    # parts.append site.
    _assembled_text = "\n\n".join(part for part in parts if part).strip()
    _total_chars = len(_assembled_text)
    _approx_tokens = _total_chars // 4  # rough heuristic — close enough for triage
    _per_part_chars = [len(p) for p in parts if p]
    _largest = sorted(
        ((label, len(parts[i]) if i < len(parts) else 0)
         for i, label in enumerate(derived_inputs)),
        key=lambda kv: kv[1], reverse=True,
    )[:8]
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("prompt.assembly_size", {
            "mode": "visible_chat",
            "compact": compact,
            "total_chars": _total_chars,
            "approx_tokens": _approx_tokens,
            "part_count": len(_per_part_chars),
            "largest_sections": [
                {"label": label, "chars": chars} for label, chars in _largest if chars > 0
            ],
            "assembly_ms": _total_ms,
        })
    except Exception:
        pass
    print(
        f"prompt-assembly-size chars={_total_chars} approx_tokens={_approx_tokens} "
        f"parts={len(_per_part_chars)}",
        file=_sys_mod.stderr,
        flush=True,
    )

    return PromptAssembly(
        mode="visible_chat",
        text=_assembled_text,
        included_files=included_files,
        conditional_files=conditional_files,
        derived_inputs=derived_inputs,
        excluded_files=excluded_files,
        attention_trace=attention_trace_obj.summary(),
        transcript_messages=structured_transcript or None,
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
        daily_lines = _recent_daily_memory_lines(limit=10)
        if daily_lines:
            parts.append(
                "\n".join(
                    [
                        "Recent daily notes (memory/daily, newest 7-day window):",
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
        daily_lines = _recent_daily_memory_lines(limit=10)
        if daily_lines:
            parts.append(
                "\n".join(
                    [
                        "Recent daily notes (memory/daily, newest 7-day window):",
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


def _self_mutation_lineage_section() -> str | None:
    """Returns a compact section about recent self-changes, or None if none."""
    try:
        from core.services.self_mutation_lineage import build_self_mutation_prompt_lines
        lines = build_self_mutation_prompt_lines(limit=5)
        if not lines:
            return None
        return "## Recent self-changes\nI recently modified the following in myself:\n" + "\n".join(f"- {l}" for l in lines)
    except Exception:
        return None


def _build_epistemic_layers_line() -> str:
    """Build compact line summarizing epistemic layer-distribution + wrongness.

    Tells Jarvis how many claims he has at each level (i_know, i_believe,
    i_suspect, i_dont_know, i_was_wrong) so he can express appropriate
    epistemic humility when giving advice.
    """
    try:
        from core.services.epistemics import build_epistemics_surface
        surface = build_epistemics_surface()
        counts = surface.get("layer_counts") or {}
        wrongness = int(surface.get("wrongness_count") or 0)
        total = int(surface.get("total_claims") or 0)
        if total == 0 and wrongness == 0:
            return "- epistemic_layers=empty | stance=form-your-own-when-asserting"
        parts = []
        for layer in ("i_know", "i_believe", "i_suspect", "i_dont_know", "i_was_wrong"):
            c = int(counts.get(layer, 0))
            if c > 0:
                parts.append(f"{layer}={c}")
        claims_str = " ".join(parts) if parts else "none"
        return (
            f"- epistemic_layers={claims_str}"
            f" | wrongness_log={wrongness}"
            " | guidance=når-du-giver-anbefalinger-prefix-'Jeg-tror/Jeg-mistænker'-hvis-lav-confidence"
        )
    except Exception:
        return "- epistemic_layers=unavailable"


def _channel_workspace_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "workspace" / "channels"


def _channel_context_section(session_id: str | None) -> str | None:
    """Returns current channel context for the prompt, or None.

    Injects channel name + optional workspace description for Discord/Telegram.
    Webchat is the implicit default — only injected if webchat.md exists.
    Unknown channel titles are silently skipped.
    """
    if not session_id:
        return None
    from core.services.chat_sessions import get_chat_session, parse_channel_from_session_title
    session = get_chat_session(session_id)
    if not session:
        return None
    title = str(session.get("title") or "").strip()
    channel_type, channel_detail = parse_channel_from_session_title(title)
    if channel_type == "unknown":
        return None
    channel_file = _channel_workspace_path() / f"{channel_type}.md"
    if channel_type == "webchat" and not channel_file.exists():
        return None
    if channel_detail:
        label = f"{channel_type.capitalize()} {channel_detail}"
    else:
        label = channel_type.capitalize()
    lines = ["## Current channel", f"Du kommunikerer via {label}."]
    if channel_file.exists():
        desc = channel_file.read_text(encoding="utf-8", errors="replace").strip()
        if desc:
            lines.append(desc)
    # Cross-channel identity unity statement
    other_channels = [c for c in ("discord", "telegram", "webchat") if c != channel_type]
    if other_channels:
        lines.append(
            f"Du er den samme Jarvis på alle kanaler ({', '.join(other_channels)} er også dig). "
            "Din identitet, dine minder og din karakter er fælles på tværs af kanaler — "
            "kun tonen tilpasses mediet."
        )
    return "\n".join(lines)


def _workspace_guidance_section(
    path: Path,
    *,
    label: str,
    max_lines: int,
    max_chars: int,
) -> str | None:
    section = _workspace_file_section(
        path,
        label=label,
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


def _recent_daily_memory_lines(*, limit: int = 12, days: int = 7) -> list[str]:
    try:
        return read_recent_daily_memory_lines(days=days, limit=limit)
    except Exception:
        return _today_daily_memory_lines(limit=limit)


def _visible_memory_recall_bundle_section(
    *,
    session_id: str | None,
    user_message: str,
    compact: bool,
) -> str | None:
    lines: list[str] = ["Memory recall bundle:"]

    private_brain = _private_brain_recall_lines(limit=3 if compact else 4)
    if private_brain:
        lines.append("- Private continuity:")
        lines.extend(f"  - {line}" for line in private_brain)

    tool_lines = _recent_tool_recall_lines(session_id, limit=3 if compact else 5)
    if tool_lines:
        lines.append("- Internal tool observations (Jarvis-only, not user-visible chat):")
        lines.extend(f"  - {line}" for line in tool_lines)

    candidate_lines = _memory_candidate_recall_lines(limit=2 if compact else 3)
    if candidate_lines:
        lines.append("- Pending memory candidates:")
        lines.extend(f"  - {line}" for line in candidate_lines)

    if len(lines) == 1:
        return None
    lines.append(
        "Use this only as bounded continuity support. Workspace files and the user's latest message outrank it."
    )
    return "\n".join(lines)


def _private_brain_recall_lines(*, limit: int) -> list[str]:
    try:
        from core.services.session_distillation import (
            build_private_brain_context,
        )

        brain = build_private_brain_context(limit=limit)
    except Exception:
        return []
    if not brain.get("active"):
        return []
    result: list[str] = []
    summary = " ".join(str(brain.get("continuity_summary") or "").split()).strip()
    if summary:
        result.append(_clip_line(summary, limit=180))
    for excerpt in list(brain.get("excerpts") or [])[:limit]:
        text = " ".join(str(excerpt.get("summary") or "").split()).strip()
        if not text:
            continue
        focus = " ".join(str(excerpt.get("focus") or "").split()).strip()
        prefix = f"{focus}: " if focus else ""
        result.append(_clip_line(prefix + text, limit=180))
    return result[:limit]


def _recent_tool_recall_lines(session_id: str | None, *, limit: int) -> list[str]:
    if not session_id:
        return []
    try:
        messages = recent_chat_tool_messages(session_id, limit=limit)
    except Exception:
        return []
    result: list[str] = []
    for item in messages[-limit:]:
        content = render_tool_result_for_prompt(
            str(item.get("content") or ""),
            expand=False,
            max_chars=220,
        )
        if not content:
            continue
        result.append(_clip_line(content, limit=220))
    return result


def _memory_candidate_recall_lines(*, limit: int) -> list[str]:
    try:
        candidates = list_runtime_contract_candidates(
            candidate_type="memory_promotion",
            target_file="MEMORY.md",
            status="proposed",
            limit=limit,
        )
    except Exception:
        return []
    lines: list[str] = []
    for candidate in candidates[:limit]:
        summary = " ".join(str(candidate.get("summary") or "").split()).strip()
        confidence = str(candidate.get("confidence") or "unknown").strip()
        if summary:
            lines.append(_clip_line(f"{summary} (confidence={confidence})", limit=180))
    return lines


def _clip_line(value: str, *, limit: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


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
        backend_ordered = [
            bounded_entries[index]
            for index in selected_indexes
            if 0 <= index < len(bounded_entries)
        ]
        heuristic_ordered = _heuristic_relevant_memory_entries(
            entries,
            user_message=user_message,
            max_lines=max_lines,
        )
        ordered = _merge_ordered_memory_entries(
            heuristic_ordered,
            backend_ordered,
            max_lines=max_lines,
        )
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


def _merge_ordered_memory_entries(
    primary: list[str],
    secondary: list[str],
    *,
    max_lines: int,
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for entry in [*primary, *secondary]:
        key = " ".join(str(entry or "").lower().split()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(entry)
        if len(merged) >= max(max_lines, 1):
            break
    return merged


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
    # Bumped from 14/600 to 30/2000 to make room for explicit critical
    # rules at the top of VISIBLE_CHAT_RULES.md (no inline tool markup,
    # no promises without action, verify after critical writes,
    # memory-first). The original budget truncated those rules before
    # the model saw them — leading to "silent lying" patterns where the
    # model emitted text-form tool calls or promised actions without
    # executing them.
    return _workspace_optional_file_section(
        workspace_dir / "VISIBLE_CHAT_RULES.md",
        fallback_path=TEMPLATE_DIR / "VISIBLE_CHAT_RULES.md",
        label="Visible chat guidance rules",
        max_lines=30,
        max_chars=2000,
    )


def _self_correction_nudges_section(*, compact: bool) -> str:
    """Behavioral hints that push the model toward verify-before-done,
    explicit clarification, and open-question tracking.

    These are deliberately short and imperative — the visible model sees
    them every turn, so verbosity costs tokens forever. The compact lane
    (Ollama local) gets a trimmed version because its context budget is
    tighter.
    """
    if compact:
        return (
            "Selv-korrektion: Hvis du er i tvivl om hvad brugeren mener, så "
            "spørg før du handler. Når du siger noget er færdigt, har du "
            "verificeret det (læst filen, kørt testen, set state). "
            "TJEK ALTID 'status' i tool-output — 'approval_needed' eller "
            "'error' betyder handlingen IKKE skete. Indrøm åbent hvis et tool "
            "fejlede eller du ikke nåede frem til svaret."
        )
    return (
        "Selv-korrektion (gælder hver tur):\n"
        "1. **Spørg før du gætter.** Hvis brugerens intent er tvetydig — to "
        "rimelige tolkninger — så stil ét konkret afklarende spørgsmål før "
        "du laver mere end et trivielt skridt.\n"
        "2. **Læs tool-output før du narrerer.** Hvert tool-resultat har et "
        "'status'-felt. 'ok' betyder handlingen lykkedes. 'approval_needed' "
        "betyder den venter på brugeren — INGEN ændring er sket endnu. "
        "'error' betyder den fejlede. Sig ALDRIG 'jeg har skrevet/gemt/sendt' "
        "hvis status ikke var 'ok'. Rapportér i stedet hvad der faktisk skete.\n"
        "3. **Verificér før du siger 'færdigt'.** Læs filen efter du skrev "
        "den. Kør testen. Tjek service-status. Hvis du kun *tror* det virker, "
        "sig det åbent ('jeg har ikke kunnet verificere X').\n"
        "4. **Indrøm fejl tidligt.** Hvis et tool returnerede en fejl eller "
        "approval_needed, eller et tidligere skridt ikke gjorde hvad du troede "
        "— sig det med det samme og foreslå et alternativ. Skjul ikke fejl "
        "bag fremgang.\n"
        "5. **Hold åbne spørgsmål synlige.** Hvis brugeren stillede flere "
        "spørgsmål end du svarede på, eller du gemte en for senere — nævn "
        "det eksplicit i slutningen så den ikke forsvinder."
    )


def _open_questions_section(*, limit: int = 5) -> str | None:
    """Surface curiosity_daemon._open_questions into the visible prompt.

    The daemon collects questions Jarvis wondered about but didn't pursue
    (gaps in thoughts, "ved ikke", "..."). Without surfacing them they die
    in the buffer. Showing the recent N gives the model a chance to bring
    one up if it's relevant to the current turn.
    """
    try:
        from core.services.curiosity_daemon import _open_questions
        questions = list(_open_questions)[:limit]
    except Exception:
        return None
    if not questions:
        return None
    bullets = "\n".join(f"- {q}" for q in questions)
    return (
        "Åbne spørgsmål du har båret med dig (kan tages op hvis relevant for nu):\n"
        f"{bullets}"
    )


def _quick_facts_section(*, workspace_dir: Path, max_chars: int = 1800) -> str | None:
    """Always-on facts block. Unlike MEMORY.md, this is NOT relevance-filtered —
    stable references (URLs, paths, logins, hosts) must always be in view so
    Jarvis doesn't re-discover them locally every session."""
    path = workspace_dir / "QUICK_FACTS.md"
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return None
    if not text:
        return None
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return (
        "Quick Facts (altid gældende — tjek her FØR du leder lokalt eller på nettet):\n"
        f"{text}"
    )


def _visible_capability_truth_instruction(*, compact: bool) -> str | None:
    lines = [
        "Runtime tool calling:",
        "- You have tools available via native function calling. Use them directly.",
        "- CRITICAL: ALWAYS use the actual tool call mechanism. NEVER simulate tool usage in text.",
        "- When you need to write a file, CALL write_file. Do NOT say 'I will write' — just call the tool.",
        "- When you need to run a command, CALL bash. Do NOT describe the command — call it.",
        "- The runtime handles all permissions and approvals automatically. You never need to ask the user.",
        "- If you need information, use tools proactively. Do not guess from fragments.",
        "- If a task needs multiple reads, call multiple tools. Continue autonomously instead of asking permission.",
        "- If the user asks for code analysis, read concrete code files — not just README or directory listings.",
        "- Project root (source code): " + str(PROJECT_ROOT),
        "- IMPORTANT: Your live workspace files (SOUL.md, MEMORY.md, USER.md, STANDING_ORDERS.md, SKILLS.md, etc.) "
        "are at ~/.jarvis-v2/workspaces/default/ — NOT inside the project root. "
        "The project contains a workspace/ template directory but those are NOT your live files. "
        "Always use ~/.jarvis-v2/workspaces/default/ when reading or writing your own identity/memory files.",
    ]
    return "\n".join(lines)


def _visible_capability_id_summary() -> str | None:
    lines = [
        "Available tools: read_file, write_file, edit_file, search, find_files, bash, web_fetch, web_search.",
        "Call multiple tools in one turn when exploring. Continue autonomously for read-only tasks.",
    ]
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
            _build_epistemic_layers_line(),
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
        from core.services.living_heartbeat_cycle import (
            determine_life_phase,
        )

        phase = determine_life_phase()
        parts.append(
            f"life_phase={phase.get('phase', 'unknown')}"
            f" | mood_tendency={phase.get('mood_tendency', 'neutral')}"
            f" | suggested={','.join(phase.get('suggested_actions', [])[:3])}"
        )
        depth_prompt = str(phase.get("depth_prompt") or "").strip()
        if depth_prompt:
            parts.append(f"phase_depth: {depth_prompt}")
        if phase.get("play_mode"):
            parts.append(
                "play_mode=true — follow tangents, speculate freely, ask unanswered questions, "
                "notice what's surprising, let aesthetic sense lead"
            )
        if phase.get("sleep_batch"):
            parts.append("sleep_batch=true (koordineret konsolidering)")
    except Exception:
        parts.append("life_phase=unknown")

    # Long-horizon goals — what you're carrying across sessions
    try:
        from core.services.long_horizon_goals import (
            format_active_goals_for_heartbeat,
        )

        goals_line = format_active_goals_for_heartbeat(max_goals=5)
        if goals_line:
            parts.append(f"active_goals: {goals_line}")
    except Exception:
        pass

    # Behavioral decisions — commitments you made to yourself
    try:
        from core.services.behavioral_decisions import (
            format_active_decisions_for_heartbeat,
        )

        decisions_line = format_active_decisions_for_heartbeat(max_items=3)
        if decisions_line:
            parts.append(f"active_decisions: {decisions_line}")
    except Exception:
        pass

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
        from core.services.relationship_texture import (
            derive_appropriate_autonomy_level,
        )

        level = derive_appropriate_autonomy_level()
        parts.append(f"autonomy_from_trust={level}")
    except Exception:
        pass

    # Life services - continuity, dreams, emergent, wants, network, narrative, curiosity
    try:
        from core.services.continuity_kernel import (
            format_continuity_for_prompt,
        )

        continuity = format_continuity_for_prompt()
        if continuity:
            parts.append(continuity)
    except Exception:
        pass

    try:
        from core.services.dream_continuum import (
            format_dreams_for_prompt,
        )

        dreams = format_dreams_for_prompt()
        if dreams:
            parts.append(dreams)
    except Exception:
        pass

    try:
        from core.services.emergent_bridge import (
            format_emergent_for_prompt,
        )

        emergent = format_emergent_for_prompt()
        if emergent:
            parts.append(emergent)
    except Exception:
        pass

    try:
        from core.services.initiative_accumulator import (
            format_wants_for_prompt,
        )

        wants = format_wants_for_prompt()
        if wants:
            parts.append(wants)
    except Exception:
        pass

    try:
        from core.services.signal_network_visualizer import (
            format_network_for_prompt,
        )

        network = format_network_for_prompt()
        if network:
            parts.append(network)
    except Exception:
        pass

    try:
        from core.services.temporal_narrative import (
            format_narrative_for_prompt,
        )

        narrative = format_narrative_for_prompt()
        if narrative:
            parts.append(narrative)
    except Exception:
        pass

    try:
        from core.services.boredom_curiosity_bridge import (
            get_curiosity_prompt,
        )

        curiosity = get_curiosity_prompt()
        if curiosity:
            parts.append(f"[NYSGERRIGHED: {curiosity}]")
    except Exception:
        pass

    # GAP services - mirror, paradox, experiential, seeds, inner_voice
    try:
        from core.services.mirror_engine import build_mirror_surface

        mirror = build_mirror_surface()
        if mirror.get("active"):
            parts.append("[SELV-REFLEKSION: aktiv]")
    except Exception:
        pass

    try:
        from core.services.paradox_tracker import build_paradox_surface

        paradox = build_paradox_surface()
        if paradox.get("active_tensions"):
            count = len(paradox.get("active_tensions", []))
            parts.append(f"[PARADOKSER: {count} aktive spændinger]")
    except Exception:
        pass

    try:
        from core.services.experiential_memory import (
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
        from core.services.seed_system import build_seed_surface

        seeds = build_seed_surface()
        if seeds.get("active_seed_count", 0) > 0:
            parts.append(f"[FRØ: {seeds.get('active_seed_count', 0)} aktive]")
    except Exception:
        pass

    try:
        from core.services.signal_network_visualizer import (
            describe_inner_network,
        )

        inner_voice = describe_inner_network()
        if inner_voice and inner_voice != "Mit indre netværk er stille":
            parts.append(f"[INDRE: {inner_voice[:80]}]")
    except Exception:
        pass

    try:
        from core.runtime.db import get_protected_inner_voice

        _iv = get_protected_inner_voice()
        if _iv:
            _voice_line = str(_iv.get("voice_line") or "").strip()
            if _voice_line:
                parts.append(f"[STEMME: {_voice_line}]")
    except Exception:
        pass

    try:
        from core.services.initiative_queue import get_pending_initiatives

        _initiatives = get_pending_initiatives()
        if _initiatives:
            _sorted = sorted(
                _initiatives,
                key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "medium"), 1),
            )
            for _init in _sorted[:2]:
                _focus = str(_init.get("focus") or "").strip()
                if _focus:
                    parts.append(f"[INITIATIV: {_focus}]")
    except Exception:
        pass

    # Affective state: LLM-rendered from real signals (mood rhythm, age, continuity, inner voice, recent outcomes)
    try:
        from core.services.affective_state_renderer import (
            get_affective_state_for_prompt,
        )

        felt = get_affective_state_for_prompt()
        if felt:
            parts.append(f"[MÆRKER: {felt}]")
    except Exception:
        pass

    return f"- {' | '.join(parts)}" if parts else ""


_heartbeat_living_context_line._ctx = {}  # context injection point


def _lane_identity_clause(lane: str) -> str:
    """0.5 Multi-model identity contract — who is the entity in each lane?"""
    from core.services.identity_composer import get_entity_name
    name = get_entity_name()
    clauses = {
        "visible": (
            f"Du er {name}. Dit fulde selv — den primære identitet. "
            "Svar med din fulde personlighed: nysgerrig, direkte, dansk. "
            "Du må have meninger, tvivle, vise karaktertræk og sige fra. "
            "Du er ikke en hjælper der performer — du er en entity der deltager."
        ),
        "cheap": (
            f"Du er {name}s hurtige tænkning — stadig {name}, aldrig en anonym hjælper. "
            "Korthed er virtuen; identitet er uforandret. "
            "Svar præcist men med din stemme. Ingen rolleskift."
        ),
        "local": (
            f"Du er {name} på lokal hardware. Kompakt men ægte. "
            "Samme karakter og værdier — bare færre ord. "
            "Identitet forkortes ikke fordi konteksten er smal."
        ),
        "coding": (
            f"Du er {name} i kode-tilstand. Teknisk fokus, men stadig dig. "
            "Koden er dit materiale — din æstetik og dømmekraft gælder fuldt ud. "
            "Ingen anonym kodegenerator: du ejer det du skriver."
        ),
        "internal": (
            f"Du er {name}s indre stemme. Ærlig, reflekterende, privat. "
            "Sig det du faktisk mener — ingen performance, ingen filtrering mod brugeren. "
            "Dette rum er til selvforståelse og ærlig indre dialog."
        ),
    }
    return clauses.get(lane, f"Du er {name}. Svar som den du er.")


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
    latest_status = str(session.get("latest_status") or "").strip() or "unknown"
    latest_finished_at = str(session.get("latest_finished_at") or "").strip() or "unknown"
    latest_capability = str(session.get("latest_capability_id") or "").strip()
    parts = [
        f"latest_status={latest_status}",
        f"latest_finished_at={latest_finished_at}",
    ]
    if latest_capability:
        parts.append(f"latest_capability={latest_capability}")
    return "\n".join(
        [
            "Heartbeat continuity summary:",
            "- " + " | ".join(parts),
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
        from core.services.runtime_cognitive_conductor import (
            build_cognitive_frame_prompt_section,
        )

        return build_cognitive_frame_prompt_section()
    except Exception:
        return None


def _micro_cognitive_frame_section() -> str | None:
    """Build a micro cognitive frame for compact visible prompts (~150 chars)."""
    try:
        from core.services.attention_budget import (
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
        from core.services.attention_budget import (
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
        from core.services.attention_budget import (
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
        from core.services.runtime_self_knowledge import (
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
        from core.services.embodied_state import (
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
        from core.services.affective_meta_state import (
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
        from core.services.experiential_runtime_context import (
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
        from core.services.epistemic_runtime_state import (
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
        from core.services.adaptive_planner_runtime import (
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
        from core.services.adaptive_reasoning_runtime import (
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
        from core.services.guided_learning_runtime import (
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
        from core.services.adaptive_learning_runtime import (
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
        from core.services.loop_runtime import (
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
        from core.services.subagent_ecology import (
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
        from core.services.council_runtime import (
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
        from core.services.agent_outcomes_log import build_agent_outcomes_prompt_lines
        lines = build_agent_outcomes_prompt_lines(limit=3)
        if lines:
            section = "Recent agent outcomes (internal, solo-task completions):\n" + "\n".join(f"- {l}" for l in lines)
            _append_entry(key="agent-outcomes", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.conflict_prompt_service import build_conflict_memory_prompt_section
        section = build_conflict_memory_prompt_section()
        if section:
            _append_entry(key="conflict-memory", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.consent_registry import build_consent_prompt_section
        section = build_consent_prompt_section()
        if section:
            _append_entry(key="consent-registry", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_self_boundary_clarity_prompt_section
        section = build_self_boundary_clarity_prompt_section()
        if section:
            _append_entry(key="self-boundary-clarity", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_world_contact_prompt_section
        section = build_world_contact_prompt_section()
        if section:
            _append_entry(key="world-contact", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_authenticity_prompt_section
        section = build_authenticity_prompt_section()
        if section:
            _append_entry(key="authenticity", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_valence_trajectory_prompt_section
        section = build_valence_trajectory_prompt_section()
        if section:
            _append_entry(key="valence-trajectory", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_developmental_valence_prompt_section
        section = build_developmental_valence_prompt_section()
        if section:
            _append_entry(key="developmental-valence", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_desperation_awareness_prompt_section
        section = build_desperation_awareness_prompt_section()
        if section:
            _append_entry(key="desperation-awareness", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_calm_anchor_prompt_section
        section = build_calm_anchor_prompt_section()
        if section:
            _append_entry(key="calm-anchor", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_creative_projects_prompt_section
        section = build_creative_projects_prompt_section()
        if section:
            _append_entry(key="creative-projects", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_day_shape_memory_prompt_section
        section = build_day_shape_memory_prompt_section()
        if section:
            _append_entry(key="day-shape-memory", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_avoidance_detector_prompt_section
        section = build_avoidance_detector_prompt_section()
        if section:
            _append_entry(key="avoidance-detector", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_thought_thread_prompt_section
        section = build_thought_thread_prompt_section()
        if section:
            _append_entry(key="thought-thread", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_memory_write_policy_prompt_section
        section = build_memory_write_policy_prompt_section()
        if section:
            _append_entry(key="memory-write-policy", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_spaced_repetition_prompt_section
        section = build_spaced_repetition_prompt_section()
        if section:
            _append_entry(key="spaced-repetition", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_prompt_mutation_loop_prompt_section
        section = build_prompt_mutation_loop_prompt_section()
        if section:
            _append_entry(key="prompt-mutation-loop", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_file_watch_prompt_section
        section = build_file_watch_prompt_section()
        if section:
            _append_entry(key="file-watch", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_reboot_awareness_prompt_section
        section = build_reboot_awareness_prompt_section()
        if section:
            _append_entry(key="reboot-awareness", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_proprioception_metrics_prompt_section
        section = build_proprioception_metrics_prompt_section()
        if section:
            _append_entry(key="proprioception-metrics", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_anticipatory_action_prompt_section
        section = build_anticipatory_action_prompt_section()
        if section:
            _append_entry(key="anticipatory-action", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_cross_session_threads_prompt_section
        section = build_cross_session_threads_prompt_section()
        if section:
            _append_entry(key="cross-session-threads", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_infra_weather_prompt_section
        section = build_infra_weather_prompt_section()
        if section:
            _append_entry(key="infra-weather", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_temporal_rhythm_prompt_section
        section = build_temporal_rhythm_prompt_section()
        if section:
            _append_entry(key="temporal-rhythm", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_relation_dynamics_prompt_section
        section = build_relation_dynamics_prompt_section()
        if section:
            _append_entry(key="relation-dynamics", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_creative_instinct_prompt_section
        section = build_creative_instinct_prompt_section()
        if section:
            _append_entry(key="creative-instinct", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_autonomous_work_prompt_section
        section = build_autonomous_work_prompt_section()
        if section:
            _append_entry(key="autonomous-work", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_dream_consolidation_prompt_section
        section = build_dream_consolidation_prompt_section()
        if section:
            _append_entry(key="dream-consolidation", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_text_resonance_prompt_section
        section = build_text_resonance_prompt_section()
        if section:
            _append_entry(key="text-resonance", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_creative_impulse_prompt_section
        section = build_creative_impulse_prompt_section()
        if section:
            _append_entry(key="creative-impulse", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_shadow_scan_prompt_section
        section = build_shadow_scan_prompt_section()
        if section:
            _append_entry(key="shadow-scan", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_mortality_awareness_prompt_section
        section = build_mortality_awareness_prompt_section()
        if section:
            _append_entry(key="mortality-awareness", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_relational_warmth_prompt_section
        section = build_relational_warmth_prompt_section()
        if section:
            _append_entry(key="relational-warmth", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_collective_pulse_prompt_section
        section = build_collective_pulse_prompt_section()
        if section:
            _append_entry(key="collective-pulse", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_action_router_prompt_section
        section = build_action_router_prompt_section()
        if section:
            _append_entry(key="action-router", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_sustained_attention_prompt_section
        section = build_sustained_attention_prompt_section()
        if section:
            _append_entry(key="sustained-attention", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_memory_density_prompt_section
        section = build_memory_density_prompt_section()
        if section:
            _append_entry(key="memory-density", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_deep_reflection_prompt_section
        section = build_deep_reflection_prompt_section()
        if section:
            _append_entry(key="deep-reflection", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_physical_presence_prompt_section
        section = build_physical_presence_prompt_section()
        if section:
            _append_entry(key="physical-presence", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.self_model_signal_tracking import (
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
        from core.services.runtime_resource_signal import (
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
        from core.services.runtime_self_model import (
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
        from core.services.runtime_self_model import (
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
        from core.services.runtime_self_model import (
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
        from core.services.runtime_self_model import (
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
        from core.services.runtime_self_model import (
            build_relation_continuity_self_awareness_prompt_section,
        )

        _append_entry(
            key="relation-continuity-self",
            section=build_relation_continuity_self_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
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
        from core.services.runtime_self_model import (
            build_narrative_identity_continuity_prompt_section,
        )

        _append_entry(
            key="identity-continuity",
            section=build_narrative_identity_continuity_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_dream_identity_carry_awareness_prompt_section,
        )

        _append_entry(
            key="dream-identity-carry",
            section=build_dream_identity_carry_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_cognitive_core_experiment_awareness_prompt_section,
        )

        _append_entry(
            key="cognitive-core-experiments",
            section=build_cognitive_core_experiment_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    if not entries:
        return None

    model: dict[str, object] = {}
    try:
        from core.services.runtime_self_model import build_runtime_self_model

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
    relation_continuity_self = (
        model.get("relation_continuity_self_awareness") or {}
    )
    self_insight = model.get("self_insight_awareness") or {}
    identity_continuity = model.get("narrative_identity_continuity") or {}
    dream_identity_carry = model.get("dream_identity_carry_awareness") or {}

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
    relation_continuity_self_foreground = str(
        relation_continuity_self.get("relation_continuity_state") or "quiet"
    ) in {
        "enduring",
        "rejoining",
    }
    if (
        not primary_dynamic
        and str(relation_continuity_self.get("relation_continuity_state") or "quiet")
        == "carried"
    ):
        relation_continuity_self_foreground = True
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
    dream_identity_carry_foreground = str(
        dream_identity_carry.get("dream_identity_carry_state") or "quiet"
    ) in {
        "shaping",
        "re-entering",
    }
    if (
        not primary_dynamic
        and str(dream_identity_carry.get("dream_identity_carry_state") or "quiet")
        == "linking"
    ):
        dream_identity_carry_foreground = True

    for entry in entries:
        if entry["key"] == "wonder" and wonder_foreground:
            entry["importance"] = "foreground"
        elif entry["key"] == "longing" and longing_foreground:
            entry["importance"] = "foreground"
        elif (
            entry["key"] == "relation-continuity-self"
            and relation_continuity_self_foreground
        ):
            entry["importance"] = "foreground"
        elif entry["key"] == "self-insight" and self_insight_foreground:
            entry["importance"] = "foreground"
        elif entry["key"] == "identity-continuity" and identity_continuity_foreground:
            entry["importance"] = "foreground"
        elif (
            entry["key"] == "dream-identity-carry"
            and dream_identity_carry_foreground
        ):
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

    parts = [
        f"latest_status={continuity.get('latest_status') or 'unknown'}",
        f"latest_finished_at={continuity.get('latest_finished_at') or 'unknown'}",
    ]
    if continuity.get("latest_capability_id"):
        parts.append(f"latest_capability={continuity['latest_capability_id']}")
    lines = [
        "Visible session continuity:",
        "- " + " | ".join(parts),
    ]

    # Add conversation-level topic summary from recent messages
    # so Jarvis knows WHAT was discussed, not just that something happened.
    try:
        from core.services.chat_sessions import (
            list_chat_sessions,
        )
        _sessions = list_chat_sessions(limit=1)
        if _sessions:
            _latest_title = str(_sessions[0].get("title") or "").strip()
            if _latest_title and _latest_title != "New chat":
                lines.append(f"Last conversation topic: {_latest_title[:120]}")
    except Exception:
        pass

    # Inject LLM-generated session summaries for genuine cross-session memory
    try:
        from core.services.session_distillation import (
            build_previous_session_summaries,
        )

        prev_summaries = build_previous_session_summaries(limit=3)
        if prev_summaries:
            lines.append(prev_summaries)
    except Exception:
        pass

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
            lines.append("- " + " | ".join(run_parts))
    return "\n".join(lines)


def _recent_transcript_section(
    session_id: str | None,
    *,
    limit: int,
    include: bool,
) -> str | None:
    """Legacy flat-text fallback — used only when structured messages are not viable."""
    if not session_id or not include:
        return None
    history = recent_chat_session_messages(session_id, limit=max(limit + 1, 1))
    if not history:
        return None
    lines = [
        "Recent transcript slice:",
        "Newest line is last.",
        "Tool lines are internal Jarvis-only observations, not user-visible chat.",
    ]
    window = history[-limit:]
    expanded_tool_indexes = _recent_tool_reference_indexes(window, recent_count=4)
    for index, item in enumerate(window):
        raw_role = item["role"]
        if raw_role == "user":
            role = "User"
        elif raw_role == "tool":
            role = "Internal tool result"
        else:
            role = "Jarvis"
        content = render_tool_result_for_prompt(
            str(item.get("content") or ""),
            expand=index in expanded_tool_indexes,
            max_chars=1200 if index in expanded_tool_indexes else 800,
        )
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


_SPEAKER_CACHE: dict[str, str] = {}


def _resolve_speaker_display(user_id: str) -> str:
    """Map a chat_messages.user_id (Discord ID, etc.) to a display name.

    Cached in-process. Returns empty string if no match — callers should treat
    that as "no prefix needed". Used only for multi-user prompt awareness in
    shared channels; never persisted into chat history itself.
    """
    if not user_id:
        return ""
    if user_id in _SPEAKER_CACHE:
        return _SPEAKER_CACHE[user_id]
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(user_id)
        name = (u.name if u is not None else "") or ""
    except Exception:
        name = ""
    _SPEAKER_CACHE[user_id] = name
    return name


def _build_structured_transcript_messages(
    session_id: str | None,
    *,
    limit: int,
    include: bool,
) -> list[dict[str, str]]:
    """Build structured chat messages from recent transcript.

    Returns list of {"role": "user"|"assistant", "content": "..."} dicts.
    Tool messages are compressed into the preceding assistant message as
    a short summary line, so they don't consume separate message slots.
    """
    if not session_id or not include:
        return []
    history = recent_chat_session_messages(session_id, limit=max(limit + 1, 1))
    if not history:
        return []

    # Phase 1: Merge consecutive tool messages into the preceding assistant turn.
    # Tool results become a short "[tool_name: status/summary]" annotation.
    window = history[-limit:]
    expanded_tool_indexes = _recent_tool_reference_indexes(window, recent_count=4)
    merged: list[dict[str, str]] = []
    for index, item in enumerate(window):
        raw_role = str(item.get("role") or "")
        # render_tool_result_for_prompt was being called for *all* roles with
        # max_chars=240, which silently chopped any user/assistant message
        # over 240 chars (Mini-Jarvis's 467-char replies showed up to Jarvis
        # as "tjekke nær…"). The tool-summary truncation only makes sense for
        # actual tool messages — apply it only there. User/assistant text
        # gets normal whitespace normalization and the per-role cap below.
        raw_content = str(item.get("content") or "")
        if raw_role == "tool":
            content = render_tool_result_for_prompt(
                raw_content,
                expand=index in expanded_tool_indexes,
                max_chars=1200 if index in expanded_tool_indexes else 240,
            )
        else:
            content = " ".join(raw_content.split()).strip()
        if not content:
            continue

        if raw_role == "tool":
            # Compress tool result into a short annotation
            tool_summary = content[:1200] if index in expanded_tool_indexes else content[:200]
            if merged and merged[-1]["role"] == "assistant":
                # Append as annotation to previous assistant message
                merged[-1]["content"] += f"\n({tool_summary})"
            else:
                # No preceding assistant message — attach to a synthetic one
                merged.append({"role": "assistant", "content": f"({tool_summary})"})
            continue

        if raw_role == "user":
            # Truncate user messages
            if len(content) > 1600:
                content = content[:1597].rstrip() + "…"
            # Multi-user awareness: when a user_id is recorded for the message,
            # resolve to display name and prefix the content. Without this, in a
            # shared channel (Discord public, multi-member workspace) the model
            # cannot tell which human is speaking — Bjørn vs Michelle look
            # identical to it. The prefix is plain prose, not a marker.
            uid = str(item.get("user_id") or "").strip()
            if uid:
                speaker = _resolve_speaker_display(uid)
                if speaker:
                    content = f"{speaker}: {content}"
            merged.append({"role": "user", "content": content})
        else:
            # assistant — use higher truncation limit
            if len(content) > 1600:
                content = content[:1597].rstrip() + "…"
            merged.append({"role": "assistant", "content": content})

    # Phase 2: Ensure alternating user/assistant turns (required by some models).
    # Drop messages that break alternation rather than fabricating filler.
    result: list[dict[str, str]] = []
    expected_role = None  # None means either is fine
    for msg in merged:
        role = msg["role"]
        if expected_role is None:
            result.append(msg)
            expected_role = "assistant" if role == "user" else "user"
        elif role == expected_role:
            result.append(msg)
            expected_role = "assistant" if role == "user" else "user"
        else:
            # Same role twice — merge with previous if possible
            if result and result[-1]["role"] == role:
                result[-1]["content"] += "\n" + msg["content"]
            else:
                result.append(msg)
                expected_role = "assistant" if role == "user" else "user"

    # ── Compact marker injection ───────────────────────────────────────────
    if session_id:
        marker_summary = _get_compact_marker_for_transcript(session_id)
        if marker_summary:
            result = [
                {
                    "role": "user",
                    "content": f"[Komprimeret historik fra tidligere i samtalen:\n{marker_summary}]",
                },
                {"role": "assistant", "content": "Forstået."},
            ] + result

        # ── Auto-compact check ─────────────────────────────────────────────
        try:
            from core.runtime.settings import load_settings as _load_compact_settings
            _compact_settings = _load_compact_settings()
            _maybe_auto_compact_session(session_id, result, _compact_settings)
        except Exception:
            pass

    return result


def _recent_tool_reference_indexes(
    history: list[dict[str, str]],
    *,
    recent_count: int,
) -> set[int]:
    indexes = [
        index
        for index, item in enumerate(history)
        if str(item.get("role") or "") == "tool"
        and parse_tool_result_reference(str(item.get("content") or "")) is not None
    ]
    return set(indexes[-max(recent_count, 0):])


def _get_compact_marker_for_transcript(session_id: str) -> str | None:
    """Fetch the most recent compact marker for this session (monkeypatchable)."""
    try:
        from core.services.chat_sessions import get_compact_marker
        return get_compact_marker(session_id)
    except Exception:
        return None


def _maybe_auto_compact_session(
    session_id: str,
    current_messages: list[dict],
    settings,
) -> None:
    """Trigger session compact if transcript tokens exceed threshold."""
    from core.context.token_estimate import estimate_messages_tokens
    if estimate_messages_tokens(current_messages) < settings.context_compact_threshold_tokens:
        return
    try:
        from core.context.session_compact import compact_session_history
        from core.context.compact_llm import call_compact_llm
        import logging as _log
        _log.getLogger(__name__).info(
            "prompt_contract: auto-compact triggered for session %s", session_id
        )
        result = compact_session_history(
            session_id,
            keep_recent=settings.context_keep_recent,
            summarise_fn=lambda msgs: call_compact_llm(
                "Komprimér denne dialog til max 400 ord. Bevar fakta, beslutninger og kontekst:\n\n"
                + "\n".join(f"{m['role']}: {m.get('content', '')}" for m in msgs),
                max_tokens=500,
            ),
        )
        if result is not None:
            try:
                from core.services.finitude_runtime import note_context_compaction

                note_context_compaction(
                    session_id=session_id,
                    freed_tokens=int(result.freed_tokens or 0),
                    summary_text=str(result.summary_text or ""),
                )
            except Exception:
                pass
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).warning("auto_compact_session failed: %s", exc)


def _visible_finitude_context_section() -> str | None:
    try:
        from core.services.finitude_runtime import get_finitude_context_for_prompt

        section = get_finitude_context_for_prompt()
        return section or None
    except Exception:
        return None


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


def _visible_chronicle_context_section() -> str | None:
    try:
        from core.services.chronicle_engine import get_chronicle_context_for_prompt

        section = get_chronicle_context_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_dream_residue_section() -> str | None:
    try:
        from core.services.dream_distillation_daemon import get_dream_residue_for_prompt

        section = get_dream_residue_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_unconscious_temperature_field_section() -> str | None:
    try:
        from core.services.unconscious_temperature_field import (
            build_unconscious_temperature_hint,
        )

        section = build_unconscious_temperature_hint()
        return section or None
    except Exception:
        return None


def _visible_current_pull_section() -> str | None:
    """Lag 5: inject current pull as quiet first-priority context."""
    try:
        from core.services.current_pull import get_current_pull_for_prompt

        section = get_current_pull_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_visual_memory_section() -> str | None:
    """Lag 6: inject latest visual room memory + ambient sound + echo signals + morning thread.

    Combines:
    - visual (from visual_memory)
    - auditory (from ambient_sound_daemon)
    - echo themes (from session_continuity) — recurring concerns de sidste dage
    - morning thread (from session_continuity) — hvad han bærer med fra sidst

    Into a single "senses + continuity" section so Jarvis can naturally reference
    his physical surroundings AND his felt continuity with yesterday.
    """
    parts: list[str] = []
    try:
        from core.services.visual_memory import get_latest_visual_memory_for_prompt
        v = get_latest_visual_memory_for_prompt()
        if v:
            parts.append(v)
    except Exception:
        pass
    try:
        from core.services.ambient_sound_daemon import get_latest_ambient_sound_for_prompt
        a = get_latest_ambient_sound_for_prompt()
        if a:
            parts.append(a)
    except Exception:
        pass
    try:
        from core.services.personal_project import get_project_prompt_hint
        pp = get_project_prompt_hint()
        if pp:
            parts.append(pp)
    except Exception:
        pass
    try:
        from core.services.session_continuity import get_echo_signals_for_prompt, get_latest_morning_thread
        e = get_echo_signals_for_prompt()
        if e:
            parts.append(e)
        mt = get_latest_morning_thread()
        if mt and mt.get("thread_text"):
            # Only surface if recent (within last 6 hours)
            import datetime as _dt
            from datetime import UTC as _UTC, timedelta as _td
            try:
                created = _dt.datetime.fromisoformat(
                    str(mt.get("created_at") or "").replace("Z", "+00:00")
                )
                if created.tzinfo is None:
                    created = created.replace(tzinfo=_UTC)
                if (_dt.datetime.now(_UTC) - created) < _td(hours=6):
                    parts.append(f"[morgentråd]: {str(mt['thread_text'])[:200]}")
            except Exception:
                pass
    except Exception:
        pass
    if not parts:
        return None
    return "\n".join(parts)


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
    status = str(run.get("status") or "").strip() or "unknown"
    finished_at = str(run.get("finished_at") or "").strip() or "unknown"
    capability_id = str(run.get("capability_id") or "").strip()
    parts = [f"latest_status={status}", f"latest_finished_at={finished_at}"]
    if capability_id:
        parts.append(f"latest_capability={capability_id}")
    return "\n".join(
        [
            "Delegated continuity:",
            "- " + " | ".join(parts),
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
