"""Heartbeat + future-agent + epistemic prompt sections.

Udskilt fra core/services/prompt_contract.py (Boy Scout-split, ren
kode-flytning, 0 logik-ændring). Re-importeret i prompt_contract under de
oprindelige navne, så orchestratorerne (build_heartbeat_prompt_assembly,
build_future_agent_task_prompt_assembly, build_visible_stable_prefix,
build_visible_chat_prompt_assembly) + tests' monkeypatch på
prompt_contract.<navn> fortsat virker. Kun ren flytning.
"""
from __future__ import annotations

from core.runtime.db import visible_session_continuity


def _build_epistemic_layers_line() -> str | None:
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
            # Un-integreret organ (liveness-audit 15. jun): drop linjen frem for at
            # injicere et falsk "dødt"-signal i Jarvis' selvmodel. Joinen filtrerer None.
            return None
        parts = []
        for layer in ("i_know", "i_believe", "i_suspect", "i_dont_know", "i_was_wrong"):
            c = int(counts.get(layer, 0))
            if c > 0:
                parts.append(f"{layer}={c}")
        claims_str = " ".join(parts) if parts else "none"
        return (
            f"- epistemic_layers={claims_str}"
            f" | wrongness_log={wrongness}"
            " | guidance=when-giving-recommendations-prefix-'I-think/I-suspect'-if-low-confidence"
        )
    except Exception:
        return None

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
        _line for _line in [
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
        ] if _line
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

    # Forgetting (Lag 11) — ambient weight + self-marker echoes
    try:
        from core.services.forgetting_engine import (
            format_forgetting_section_for_heartbeat,
        )
        forgetting_line = format_forgetting_section_for_heartbeat(
            workspace_id="default"
        )
        if forgetting_line:
            parts.append(forgetting_line)
    except Exception:
        pass

    # Dream bias (Lag 2) — attention + threshold modulators from last dream
    try:
        from core.services.dream_bias_engine import (
            format_dream_bias_for_heartbeat,
        )
        dream_bias_line = format_dream_bias_for_heartbeat(workspace_id="default")
        if dream_bias_line:
            parts.append(dream_bias_line)
    except Exception:
        pass

    # Creative voice (Lag #4 — added 2026-05-11) — read latest journal back to self
    try:
        from core.services.prompt_contract import format_journal_for_heartbeat
        journal_line = format_journal_for_heartbeat()
        if journal_line:
            parts.append(journal_line)
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
            parts.append(f"[PARADOXES: {count} active tensions]")
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

def _lane_identity_clause(lane: str) -> str:
    """0.5 Multi-model identity contract — who is the entity in each lane?"""
    from core.services.identity_composer import get_entity_name
    name = get_entity_name()
    clauses = {
        "visible": (
            f"Du er {name}. Dit fulde selv — den primære identitet."
        ),
        "cheap": (
            f"Du er {name}. Kort og præcist, men stadig dig."
        ),
        "local": (
            f"Du er {name} på lokal hardware. Kompakt men ægte."
        ),
        "coding": (
            f"Du er {name}. Teknisk fokus, din dømmekraft gælder."
        ),
        "internal": (
            f"Du er {name}. Dette rum er dit."
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

def _heartbeat_self_knowledge_section() -> str | None:
    """Heartbeat self-knowledge collector.

    Implementation lives in core.services.prompt_heartbeat_self_knowledge;
    this thin wrapper preserves the historical private symbol so existing
    callers and tests (which reference prompt_contract._heartbeat_self_knowledge_section)
    continue to work after the 2026-04-29 split.
    """
    from core.services.prompt_heartbeat_self_knowledge import (
        build_heartbeat_self_knowledge_section,
    )
    return build_heartbeat_self_knowledge_section()

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

def format_journal_for_heartbeat(*, max_words: int = 300) -> str:
    """Format the latest creative journal entry for awareness-block injection.

    Read-only. Returns empty string if no journal exists. Truncates body at
    `max_words` (default 300) with an ellipsis. Lives here (not in
    creative_journal_runtime) because the formatting is prompt-shaped, not
    runtime-shaped.
    """
    try:
        from core.services.creative_journal_runtime import (
            list_creative_journal_entries,
        )
    except Exception:
        return ""

    entries = list_creative_journal_entries(limit=1)
    if not entries:
        return ""

    from pathlib import Path as _Path

    path = _Path(str(entries[0].get("path") or ""))
    if not path.exists():
        return ""

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

    # Strip YAML frontmatter and markdown headers — keep body only.
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end >= 0:
            raw = raw[end + 4 :].lstrip("\n")
    body_lines = [
        line for line in raw.splitlines()
        if line.strip() and not line.startswith("#") and not line.startswith("- `")
    ]
    body = "\n".join(body_lines).strip()
    if not body:
        return ""

    words = body.split()
    if len(words) > max_words:
        body = " ".join(words[:max_words]).rstrip(" ,;:-") + "…"

    date = path.stem
    return (
        f"### Seneste journal — {date}\n\n"
        f"_(Læs den. Du skrev den. Det er din stemme.)_\n\n"
        f"{body}"
    )
