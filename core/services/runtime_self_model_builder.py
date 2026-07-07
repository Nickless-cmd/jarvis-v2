"""Runtime self-model — top-level builder (assembles the full snapshot).

Split out of ``runtime_self_model`` (behavior-preserving). Owns
``build_runtime_self_model`` and its direct helpers (``_collect_layers``,
``_truth_boundaries``, ``_build_summary``), pulling in every awareness/surface
producer from the sibling modules.

Re-exported via ``core.services.runtime_self_model`` for backward compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime

from core.services.runtime_surface_cache import runtime_surface_cache
from core.tools.workspace_capabilities import load_workspace_capabilities

from core.services.runtime_self_model_state import *  # noqa: F401,F403
from core.services.runtime_self_model_affect import *  # noqa: F401,F403
from core.services.runtime_self_model_identity import *  # noqa: F401,F403
from core.services.runtime_self_model_boundary import *  # noqa: F401,F403
from core.services.runtime_self_model_surfaces import *  # noqa: F401,F403

def _facade():
    """Return the facade module so monkeypatch-through-facade is honored.

    Helpers patched in tests via ``monkeypatch.setattr(runtime_self_model,
    ...)`` are resolved through this accessor so the patch is seen across the
    module split (behavior-preserving).
    """
    import core.services.runtime_self_model as _m

    return _m


def build_runtime_self_model() -> dict[str, object]:
    """Build a bounded runtime self-model snapshot.

    Returns a structured dict with typed layers, producer states,
    truth boundaries, and a compact prompt-ready summary.
    """
    with runtime_surface_cache():
        layers = _collect_layers()
        boundaries = _truth_boundaries()
        summary = _build_summary(layers, boundaries)
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _facade()._derive_subjective_temporal_feel(experiential, inner_voice)
        mineness_sources = _mineness_source_snapshot()
        mineness_ownership = _facade()._derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=mineness_sources,
        )
        flow_state_awareness = _derive_flow_state_awareness(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            mineness=mineness_ownership,
        )
        wonder_sources = _wonder_source_snapshot()
        wonder_awareness = _derive_wonder_awareness(
            inner_voice=inner_voice,
            flow_state=flow_state_awareness,
            temporal_feel=temporal_feel,
            mineness=mineness_ownership,
            support_stream=support_stream,
            sources=mineness_sources,
            wonder_sources=wonder_sources,
        )
        longing_sources = _longing_source_snapshot()
        longing_awareness = _facade()._derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness_ownership,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=mineness_sources,
            longing_sources=longing_sources,
        )
        relation_continuity_self_awareness = _derive_relation_continuity_self_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness_ownership,
            longing=longing_awareness,
            relation_sources=_facade()._relation_continuity_self_source_snapshot(),
        )
        self_insight_sources = _self_insight_source_snapshot()
        self_insight_awareness = _derive_self_insight_awareness(
            sources=self_insight_sources,
            mineness=mineness_ownership,
            flow_state=flow_state_awareness,
            wonder=wonder_awareness,
            longing=longing_awareness,
        )
        narrative_identity_continuity = _derive_narrative_identity_continuity(
            self_insight=self_insight_awareness,
            sources=self_insight_sources,
            mineness=mineness_ownership,
            flow_state=flow_state_awareness,
            wonder=wonder_awareness,
            longing=longing_awareness,
        )
        dream_identity_carry_awareness = _derive_dream_identity_carry_awareness(
            self_insight=self_insight_awareness,
            identity_continuity=narrative_identity_continuity,
            sources=self_insight_sources,
            dream_influence=_dream_influence_surface(),
            dream_articulation=_dream_articulation_surface(),
        )
        cognitive_core_experiments = _facade()._cognitive_core_experiments_surface()

        return {
            "layers": layers,
            "workspace_capabilities": load_workspace_capabilities(),
            "runtime_task_state": _runtime_task_state_surface(),
            "runtime_flow_state": _runtime_flow_state_surface(),
            "runtime_hook_state": _runtime_hook_state_surface(),
            "browser_body_state": _browser_body_state_surface(),
            "standing_orders_state": _standing_orders_state_surface(),
            "layered_memory_state": _layered_memory_state_surface(),
            "embodied_state": _embodied_state_surface(),
            "affective_meta_state": _affective_meta_state_surface(),
            "experiential_runtime_context": experiential,
            "inner_voice_daemon": inner_voice,
            "support_stream_awareness": support_stream,
            "subjective_temporal_feel": temporal_feel,
            "mineness_ownership": mineness_ownership,
            "flow_state_awareness": flow_state_awareness,
            "wonder_awareness": wonder_awareness,
            "longing_awareness": longing_awareness,
            "relation_continuity_self_awareness": relation_continuity_self_awareness,
            "self_insight_awareness": self_insight_awareness,
            "narrative_identity_continuity": narrative_identity_continuity,
            "dream_identity_carry_awareness": dream_identity_carry_awareness,
            "epistemic_runtime_state": _epistemic_runtime_state_surface(),
            "subagent_ecology": _subagent_ecology_surface(),
            "self_boundary_clarity": _self_boundary_clarity_surface(),
            "world_contact": _world_contact_surface(),
            "council_runtime": _council_runtime_surface(),
            "agent_outcomes": _agent_outcomes_surface(),
            "authenticity": _authenticity_surface(),
            "valence_trajectory": _valence_trajectory_surface(),
            "developmental_valence": _developmental_valence_surface(),
            "desperation_awareness": _desperation_awareness_surface(),
            "calm_anchor": _calm_anchor_surface(),
            "memory_breathing": _memory_breathing_surface(),
            "creative_projects": _creative_projects_surface(),
            "day_shape_memory": _day_shape_memory_surface(),
            "avoidance_detector": _avoidance_detector_surface(),
            "thought_thread": _thought_thread_surface(),
            "skill_contract_registry": _skill_contract_registry_surface(),
            "memory_write_policy": _memory_write_policy_surface(),
            "spaced_repetition": _spaced_repetition_surface(),
            "scheduled_job_windows": _scheduled_job_windows_surface(),
            "automation_dsl": _automation_dsl_surface(),
            "outcome_learning": _outcome_learning_surface(),
            "jobs_engine": _jobs_engine_surface(),
            "prompt_mutation_loop": _prompt_mutation_loop_surface(),
            "file_watch": _file_watch_surface(),
            "reboot_awareness": _reboot_awareness_surface(),
            "proprioception_metrics": _proprioception_metrics_surface(),
            "anticipatory_action": _anticipatory_action_surface(),
            "cross_session_threads": _cross_session_threads_surface(),
            "autonomous_outreach": _autonomous_outreach_surface(),
            "infra_weather": _infra_weather_surface(),
            "temporal_rhythm": _temporal_rhythm_surface(),
            "relation_dynamics": _relation_dynamics_surface(),
            "creative_instinct": _creative_instinct_surface(),
            "autonomous_work": _autonomous_work_surface(),
            "dream_consolidation": _dream_consolidation_surface(),
            "text_resonance": _text_resonance_surface(),
            "creative_impulse": _creative_impulse_surface(),
            "shadow_scan": _shadow_scan_surface(),
            "mortality_awareness": _mortality_awareness_surface(),
            "relational_warmth": _relational_warmth_surface(),
            "collective_pulse": _collective_pulse_surface(),
            "action_router": _action_router_surface(),
            "sustained_attention": _sustained_attention_surface(),
            "memory_density": _memory_density_surface(),
            "deep_reflection": _deep_reflection_surface(),
            "physical_presence": _physical_presence_surface(),
            "adaptive_planner": _adaptive_planner_surface(),
            "adaptive_reasoning": _adaptive_reasoning_surface(),
            "dream_influence": _dream_influence_surface(),
            "guided_learning": _guided_learning_surface(),
            "adaptive_learning": _adaptive_learning_surface(),
            "self_system_code_awareness": _self_system_code_awareness_surface(),
            "tool_intent": _tool_intent_surface(),
            "loop_runtime": _loop_runtime_surface(),
            "idle_consolidation": _idle_consolidation_surface(),
            "dream_articulation": _dream_articulation_surface(),
            "prompt_evolution": _prompt_evolution_surface(),
            "truth_boundaries": boundaries,
            "cognitive_core_experiments": cognitive_core_experiments,
            "cognitive_architecture": _cognitive_architecture_awareness(),
            "summary": summary,
            "built_at": datetime.now(UTC).isoformat(),
        }


def _collect_layers() -> list[dict[str, str]]:
    """Collect all known layers with type annotations."""
    layers: list[dict[str, str]] = []
    task_state = _runtime_task_state_surface()
    flow_state = _runtime_flow_state_surface()
    hook_state = _runtime_hook_state_surface()
    browser_body = _browser_body_state_surface()
    standing_orders = _standing_orders_state_surface()
    layered_memory = _layered_memory_state_surface()

    # --- Runtime truth layers (authoritative) ---
    layers.append(
        {
            "id": "heartbeat",
            "label": "Heartbeat runtime",
            "kind": "orchestration",
            "role": _heartbeat_role(),
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": "Basal pulse. Drives cadence ticks and non-visible producers.",
        }
    )

    layers.append(
        {
            "id": "internal-cadence",
            "label": "Internal cadence layer",
            "kind": "orchestration",
            "role": "active",
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": "Shared rhythm for non-visible producers. Evaluates due/cooling/blocked.",
        }
    )

    embodied = _embodied_state_surface()
    layers.append(
        {
            "id": "embodied-host-awareness",
            "label": "Embodied host awareness",
            "kind": "orchestration",
            "role": "active",
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": (
                f"Host/body state={embodied.get('state') or 'unknown'}; "
                f"strain={embodied.get('strain_level') or 'unknown'}; "
                f"freshness={((embodied.get('freshness') or {}).get('state') or 'unknown')}."
            ),
        }
    )

    affective_meta = _affective_meta_state_surface()
    layers.append(
        {
            "id": "affective-meta-light",
            "label": "Affective / meta bundle light",
            "kind": "orchestration",
            "role": "active",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"state={affective_meta.get('state') or 'unknown'}; "
                f"bearing={affective_meta.get('bearing') or 'unknown'}; "
                f"monitoring={affective_meta.get('monitoring_mode') or 'unknown'}."
            ),
        }
    )

    epistemic_state = _epistemic_runtime_state_surface()
    layers.append(
        {
            "id": "epistemic-wrongness-light",
            "label": "Epistemic wrongness / counterfactual light",
            "kind": "orchestration",
            "role": "active",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"wrongness={epistemic_state.get('wrongness_state') or 'clear'}; "
                f"regret={epistemic_state.get('regret_signal') or 'none'}; "
                f"counterfactual={epistemic_state.get('counterfactual_mode') or 'none'}."
            ),
        }
    )

    subagent_ecology = _subagent_ecology_surface()
    ecology_summary = subagent_ecology.get("summary") or {}
    layers.append(
        {
            "id": "subagent-ecology-light",
            "label": "Subagent ecology light",
            "kind": "orchestration",
            "role": "active"
            if int(ecology_summary.get("active_count") or 0) > 0
            else "idle",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"active={int(ecology_summary.get('active_count') or 0)}; "
                f"blocked={int(ecology_summary.get('blocked_count') or 0)}; "
                f"last={ecology_summary.get('last_active_role_name') or 'none'}; "
                f"tool_access={subagent_ecology.get('tool_access') or 'none'}."
            ),
        }
    )

    council_runtime = _council_runtime_surface()
    layers.append(
        {
            "id": "council-runtime-light",
            "label": "Council / swarm light",
            "kind": "orchestration",
            "role": "active"
            if str(council_runtime.get("council_state") or "quiet")
            not in {"quiet", "held"}
            else "idle",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"state={council_runtime.get('council_state') or 'quiet'}; "
                f"recommendation={council_runtime.get('recommendation') or 'none'}; "
                f"divergence={council_runtime.get('divergence_level') or 'low'}; "
                f"tool_access={council_runtime.get('tool_access') or 'none'}."
            ),
        }
    )

    adaptive_planner = _adaptive_planner_surface()
    layers.append(
        {
            "id": "adaptive-planner-light",
            "label": "Adaptive planner light",
            "kind": "orchestration",
            "role": "active",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"mode={adaptive_planner.get('planner_mode') or 'incremental'}; "
                f"horizon={adaptive_planner.get('plan_horizon') or 'near'}; "
                f"risk={adaptive_planner.get('risk_posture') or 'balanced'}; "
                f"bias={adaptive_planner.get('next_planning_bias') or 'stepwise-progress'}."
            ),
        }
    )

    adaptive_reasoning = _adaptive_reasoning_surface()
    layers.append(
        {
            "id": "adaptive-reasoning-light",
            "label": "Adaptive reasoning light",
            "kind": "orchestration",
            "role": "active",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"mode={adaptive_reasoning.get('reasoning_mode') or 'direct'}; "
                f"posture={adaptive_reasoning.get('reasoning_posture') or 'balanced'}; "
                f"certainty={adaptive_reasoning.get('certainty_style') or 'crisp'}; "
                f"constraint={adaptive_reasoning.get('constraint_bias') or 'light'}."
            ),
        }
    )

    dream_influence = _dream_influence_surface()
    layers.append(
        {
            "id": "dream-influence-light",
            "label": "Dream influence light",
            "kind": "orchestration",
            "role": "active"
            if str(dream_influence.get("influence_state") or "quiet") != "quiet"
            else "idle",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"state={dream_influence.get('influence_state') or 'quiet'}; "
                f"target={dream_influence.get('influence_target') or 'none'}; "
                f"mode={dream_influence.get('influence_mode') or 'stabilize'}; "
                f"strength={dream_influence.get('influence_strength') or 'none'}."
            ),
        }
    )

    cognitive_core_experiments = _facade()._cognitive_core_experiments_surface()
    carry_ids = [
        str(item)
        for item in (cognitive_core_experiments.get("carry_candidate_systems") or [])
        if str(item)
    ]
    observational_ids = [
        str(item)
        for item in (cognitive_core_experiments.get("observational_systems") or [])
        if str(item)
    ]
    layers.append(
        {
            "id": "cognitive-core-experiments-light",
            "label": "Cognitive core experiments light",
            "kind": "orchestration",
            "role": "active"
            if str(cognitive_core_experiments.get("activity_state") or "disabled")
            == "active"
            else "idle"
            if str(cognitive_core_experiments.get("activity_state") or "disabled")
            == "enabled-idle"
            else "gated",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"activity={cognitive_core_experiments.get('activity_state') or 'disabled'}; "
                f"carry={cognitive_core_experiments.get('carry_state') or 'quiet'}; "
                f"strongest={cognitive_core_experiments.get('strongest_carry_system') or 'none'}; "
                f"carry_candidates={', '.join(carry_ids) or 'none'}; "
                f"observational={', '.join(observational_ids) or 'none'}."
            ),
        }
    )

    guided_learning = _guided_learning_surface()
    layers.append(
        {
            "id": "guided-learning-light",
            "label": "Guided learning light",
            "kind": "orchestration",
            "role": "active",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"mode={guided_learning.get('learning_mode') or 'reinforce'}; "
                f"focus={guided_learning.get('learning_focus') or 'reasoning'}; "
                f"posture={guided_learning.get('learning_posture') or 'gentle'}; "
                f"pressure={guided_learning.get('learning_pressure') or 'low'}."
            ),
        }
    )

    adaptive_learning = _adaptive_learning_surface()
    layers.append(
        {
            "id": "adaptive-learning-light",
            "label": "Adaptive learning engine light",
            "kind": "orchestration",
            "role": "active",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"mode={adaptive_learning.get('learning_engine_mode') or 'retain'}; "
                f"target={adaptive_learning.get('reinforcement_target') or 'reasoning'}; "
                f"retention={adaptive_learning.get('retention_bias') or 'light'}; "
                f"maturation={adaptive_learning.get('maturation_state') or 'early'}."
            ),
        }
    )

    self_system_code_awareness = _self_system_code_awareness_surface()
    layers.append(
        {
            "id": "self-system-code-awareness-light",
            "label": "Self system / code awareness light",
            "kind": "orchestration",
            "role": "active"
            if str(
                self_system_code_awareness.get("code_awareness_state")
                or "repo-unavailable"
            )
            != "repo-unavailable"
            else "idle",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"code={self_system_code_awareness.get('code_awareness_state') or 'repo-unavailable'}; "
                f"repo={self_system_code_awareness.get('repo_status') or 'not-git'}; "
                f"changes={self_system_code_awareness.get('local_change_state') or 'unknown'}; "
                f"upstream={self_system_code_awareness.get('upstream_awareness') or 'unknown'}; "
                f"concern={self_system_code_awareness.get('concern_state') or 'stable'}; "
                f"approval_required={self_system_code_awareness.get('action_requires_approval', True)}."
            ),
        }
    )

    tool_intent = _tool_intent_surface()
    layers.append(
        {
            "id": "approval-gated-tool-intent-light",
            "label": "Approval-gated tool intent light",
            "kind": "orchestration",
            "role": "active"
            if str(tool_intent.get("intent_state") or "idle") != "idle"
            else "idle",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": (
                f"state={tool_intent.get('intent_state') or 'idle'}; "
                f"type={tool_intent.get('intent_type') or 'inspect-repo-status'}; "
                f"target={tool_intent.get('intent_target') or 'workspace'}; "
                f"urgency={tool_intent.get('urgency') or 'low'}; "
                f"approval_state={tool_intent.get('approval_state') or 'none'}; "
                f"approval_source={tool_intent.get('approval_source') or 'none'}; "
                f"approval_required={tool_intent.get('approval_required', True)}; "
                f"execution={tool_intent.get('execution_state') or 'not-executed'}; "
                f"execution_mode={tool_intent.get('execution_mode') or 'read-only'}; "
                f"mutation_permitted={tool_intent.get('mutation_permitted', False)}; "
                f"workspace_scoped={tool_intent.get('workspace_scoped', False)}; "
                f"external_mutation_permitted={tool_intent.get('external_mutation_permitted', False)}; "
                f"delete_permitted={tool_intent.get('delete_permitted', False)}; "
                f"mutation_state={tool_intent.get('mutation_intent_state') or 'idle'}; "
                f"mutation_classification={tool_intent.get('mutation_intent_classification') or 'none'}; "
                f"mutation_repo_scope={tool_intent.get('mutation_repo_scope') or 'none'}; "
                f"mutation_system_scope={tool_intent.get('mutation_system_scope') or 'none'}; "
                f"mutation_sudo_required={tool_intent.get('mutation_sudo_required', False)}; "
                f"write_proposal_state={tool_intent.get('write_proposal_state') or 'none'}; "
                f"write_proposal_type={tool_intent.get('write_proposal_type') or 'none'}; "
                f"write_proposal_scope={tool_intent.get('write_proposal_scope') or 'none'}; "
                f"write_proposal_criticality={tool_intent.get('write_proposal_criticality') or 'none'}; "
                f"write_proposal_target_identity={tool_intent.get('write_proposal_target_identity', False)}; "
                f"write_proposal_target_memory={tool_intent.get('write_proposal_target_memory', False)}; "
                f"write_proposal_target={tool_intent.get('write_proposal_target') or 'none'}; "
                f"write_proposal_content_state={tool_intent.get('write_proposal_content_state') or 'none'}; "
                f"write_proposal_content_fingerprint={tool_intent.get('write_proposal_content_fingerprint') or 'none'}; "
                f"mutating_exec_state={tool_intent.get('mutating_exec_proposal_state') or 'none'}; "
                f"mutating_exec_scope={tool_intent.get('mutating_exec_proposal_scope') or 'none'}; "
                f"mutating_exec_requires_sudo={tool_intent.get('mutating_exec_requires_sudo', False)}; "
                f"mutating_exec_fingerprint={tool_intent.get('mutating_exec_command_fingerprint') or 'none'}; "
                f"sudo_exec_state={tool_intent.get('sudo_exec_proposal_state') or 'none'}; "
                f"sudo_exec_scope={tool_intent.get('sudo_exec_proposal_scope') or 'none'}; "
                f"sudo_exec_requires_sudo={tool_intent.get('sudo_exec_requires_sudo', False)}; "
                f"sudo_exec_fingerprint={tool_intent.get('sudo_exec_command_fingerprint') or 'none'}; "
                f"sudo_window_state={tool_intent.get('sudo_approval_window_state') or 'none'}; "
                f"sudo_window_scope={tool_intent.get('sudo_approval_window_scope') or 'none'}; "
                f"sudo_window_expires_at={tool_intent.get('sudo_approval_window_expires_at') or 'none'}; "
                f"sudo_window_reusable={tool_intent.get('sudo_approval_window_reusable', False)}; "
                f"execution_command={tool_intent.get('execution_command') or 'none'}; "
                f"sudo_permitted={tool_intent.get('sudo_permitted', False)}; "
                f"continuity={tool_intent.get('action_continuity_state') or 'idle'}; "
                f"last_action_outcome={tool_intent.get('last_action_outcome') or 'none'}; "
                f"followup_state={tool_intent.get('followup_state') or 'none'}."
            ),
        }
    )

    loop_runtime = _loop_runtime_surface()
    loop_summary = loop_runtime.get("summary") or {}
    layers.append(
        {
            "id": "loop-runtime-light",
            "label": "Loop runtime light",
            "kind": "orchestration",
            "role": "active",
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": (
                f"active={int(loop_summary.get('active_count') or 0)}; "
                f"standby={int(loop_summary.get('standby_count') or 0)}; "
                f"resumed={int(loop_summary.get('resumed_count') or 0)}; "
                f"closed={int(loop_summary.get('closed_count') or 0)}."
            ),
        }
    )

    layers.append(
        {
            "id": "runtime-task-ledger",
            "label": "Runtime task ledger",
            "kind": "orchestration",
            "role": (
                "active"
                if int(task_state.get("queued_count") or 0)
                or int(task_state.get("running_count") or 0)
                else ("gated" if int(task_state.get("blocked_count") or 0) else "idle")
            ),
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": (
                f"queued={task_state.get('queued_count') or 0}; "
                f"running={task_state.get('running_count') or 0}; "
                f"blocked={task_state.get('blocked_count') or 0}; "
                f"latest_goal={task_state.get('latest_goal') or 'none'}."
            ),
        }
    )

    layers.append(
        {
            "id": "runtime-flow-ledger",
            "label": "Runtime flow ledger",
            "kind": "orchestration",
            "role": (
                "active"
                if int(flow_state.get("queued_count") or 0)
                or int(flow_state.get("running_count") or 0)
                else ("gated" if int(flow_state.get("blocked_count") or 0) else "idle")
            ),
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": (
                f"queued={flow_state.get('queued_count') or 0}; "
                f"running={flow_state.get('running_count') or 0}; "
                f"blocked={flow_state.get('blocked_count') or 0}; "
                f"step={flow_state.get('current_step') or 'none'}."
            ),
        }
    )

    layers.append(
        {
            "id": "runtime-hook-bridge",
            "label": "Runtime hook bridge",
            "kind": "orchestration",
            "role": (
                "gated"
                if int(hook_state.get("pending_count") or 0) > 0
                else (
                    "active"
                    if int(hook_state.get("dispatched_count") or 0) > 0
                    else "idle"
                )
            ),
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": (
                f"pending={hook_state.get('pending_count') or 0}; "
                f"dispatched={hook_state.get('dispatched_count') or 0}; "
                f"latest={hook_state.get('latest_event_kind') or 'none'}."
            ),
        }
    )

    layers.append(
        {
            "id": "browser-body",
            "label": "Browser body",
            "kind": "orchestration",
            "role": (
                "gated"
                if str(browser_body.get("status") or "") == "blocked"
                else ("active" if browser_body.get("exists") else "idle")
            ),
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": (
                f"profile={browser_body.get('profile_name') or 'none'}; "
                f"status={browser_body.get('status') or 'absent'}; "
                f"tabs={browser_body.get('tab_count') or 0}; "
                f"last_url={browser_body.get('last_url') or 'none'}."
            ),
        }
    )

    consolidation = _idle_consolidation_surface()
    consolidation_summary = consolidation.get("summary") or {}
    layers.append(
        {
            "id": "sleep-idle-consolidation",
            "label": "Sleep / idle consolidation light",
            "kind": "orchestration",
            "role": "active" if consolidation.get("active") else "idle",
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": (
                f"state={consolidation_summary.get('last_state') or 'idle'}; "
                f"reason={consolidation_summary.get('last_reason') or 'no-run-yet'}; "
                f"latest={consolidation_summary.get('latest_record_id') or 'none'}."
            ),
        }
    )

    dream = _dream_articulation_surface()
    dream_summary = dream.get("summary") or {}
    layers.append(
        {
            "id": "dream-articulation-light",
            "label": "Dream articulation light",
            "kind": "groundwork",
            "role": "groundwork-only",
            "visibility": "internal-only",
            "truth": "candidate-only",
            "detail": (
                f"state={dream_summary.get('last_state') or 'idle'}; "
                f"reason={dream_summary.get('last_reason') or 'no-run-yet'}; "
                f"latest={dream_summary.get('latest_signal_id') or 'none'}."
            ),
        }
    )

    prompt_evolution = _prompt_evolution_surface()
    prompt_evolution_summary = prompt_evolution.get("summary") or {}
    layers.append(
        {
            "id": "runtime-prompt-evolution-light",
            "label": "Runtime prompt evolution light",
            "kind": "groundwork",
            "role": "groundwork-only",
            "visibility": "internal-only",
            "truth": "candidate-only",
            "detail": (
                f"state={prompt_evolution_summary.get('last_state') or 'idle'}; "
                f"target={prompt_evolution_summary.get('latest_target_asset') or 'none'}; "
                f"learning={prompt_evolution_summary.get('latest_learning_mode') or 'none'}; "
                f"dream={prompt_evolution_summary.get('latest_dream_influence_mode') or 'stabilize'}; "
                f"co={prompt_evolution_summary.get('latest_fragment_co_influence') or 'none'}; "
                f"fragment={'present' if prompt_evolution.get('candidate_fragment') else 'none'}; "
                f"direction={prompt_evolution_summary.get('proposal_direction') or 'none'}; "
                f"latest={prompt_evolution_summary.get('latest_proposal_id') or 'none'}."
            ),
        }
    )
    try:
        from core.services.emergent_signal_tracking import (
            build_runtime_emergent_signal_surface,
        )

        emergent = build_runtime_emergent_signal_surface(limit=3)
        emergent_summary = emergent.get("summary") or {}
        layers.append(
            {
                "id": "emergent-inner-signals",
                "label": "Emergent inner signals",
                "kind": "groundwork",
                "role": "groundwork-only",
                "visibility": "internal-only",
                "truth": "candidate-only",
                "detail": (
                    f"Candidate-only internal signals. Active={int(emergent_summary.get('active_count') or 0)}; "
                    f"current={str(emergent_summary.get('current_signal') or 'none')}."
                ),
            }
        )
    except Exception:
        pass

    # --- Capability layers ---
    layers.append(
        {
            "id": "visible-chat",
            "label": "Visible chat lane",
            "kind": "capability",
            "role": _visible_chat_role(),
            "visibility": "visible",
            "truth": "authoritative",
            "detail": "User-facing conversation. Jarvis' primary visible output.",
        }
    )

    layers.append(
        {
            "id": "internal-fallback-lane",
            "label": "Internal fallback model lane",
            "kind": "capability",
            "role": _cheap_lane_role(),
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": "Fallback model lane for bounded internal jobs when the local lane is unavailable.",
        }
    )

    layers.append(
        {
            "id": "local-lane",
            "label": "Local model lane",
            "kind": "capability",
            "role": _local_lane_role(),
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": "Local model for heartbeat and inner producers.",
        }
    )

    workspace_capabilities = load_workspace_capabilities()
    callable_ids = workspace_capabilities.get("callable_capability_ids") or []
    gated_ids = workspace_capabilities.get("approval_gated_capability_ids") or []
    layers.append(
        {
            "id": "workspace-capability-registry",
            "label": "Workspace capability registry",
            "kind": "capability",
            "role": "active" if callable_ids else ("gated" if gated_ids else "idle"),
            "visibility": "mixed",
            "truth": "authoritative",
            "detail": (
                f"workspace={workspace_capabilities.get('workspace') or 'unknown'}; "
                f"callable={len(callable_ids)}; "
                f"approval_gated={len(gated_ids)}; "
                f"mode={(workspace_capabilities.get('contract') or {}).get('mode') or 'text-capability-call'}; "
                f"json_tool_calls={(workspace_capabilities.get('contract') or {}).get('json_tool_call_supported', False)}."
            ),
        }
    )

    # --- Producer layers ---
    for p in _producer_layers():
        layers.append(p)

    # --- Memory layers ---
    layers.append(
        {
            "id": "workspace-memory",
            "label": "Curated workspace memory (MEMORY.md)",
            "kind": "memory",
            "role": "active",
            "visibility": "mixed",
            "truth": "authoritative",
            "detail": "Curated cross-session memory. User-visible and LLM-readable.",
        }
    )

    layers.append(
        {
            "id": "layered-memory",
            "label": "Layered memory",
            "kind": "memory",
            "role": (
                "active"
                if layered_memory.get("daily_exists")
                and layered_memory.get("curated_exists")
                else "gated"
            ),
            "visibility": "mixed",
            "truth": "authoritative",
            "detail": (
                f"daily_exists={layered_memory.get('daily_exists', False)}; "
                f"curated_exists={layered_memory.get('curated_exists', False)}; "
                f"daily_file={layered_memory.get('daily_file') or 'none'}; "
                f"freshness={layered_memory.get('freshness') or 'unknown'}."
            ),
        }
    )

    layers.append(
        {
            "id": "private-brain",
            "label": "Private brain records",
            "kind": "memory",
            "role": _private_brain_role(),
            "visibility": "internal-only",
            "truth": "authoritative",
            "detail": "Append-only private memory. Not user-visible.",
        }
    )

    layers.append(
        {
            "id": "session-distillation",
            "label": "Session distillation",
            "kind": "memory",
            "role": "active",
            "visibility": "internal-only",
            "truth": "derived",
            "detail": "End-of-run carry classification into private brain or workspace memory.",
        }
    )

    # --- Identity layers ---
    layers.append(
        {
            "id": "soul-identity",
            "label": "SOUL + IDENTITY",
            "kind": "identity",
            "role": "active",
            "visibility": "mixed",
            "truth": "authoritative",
            "detail": "Protected core. Defines who Jarvis is. Not mutable by runtime.",
        }
    )

    layers.append(
        {
            "id": "standing-orders",
            "label": "Standing orders",
            "kind": "permission",
            "role": "active" if standing_orders.get("exists") else "idle",
            "visibility": "mixed",
            "truth": "authoritative",
            "detail": (
                f"exists={standing_orders.get('exists', False)}; "
                f"loaded_by_default={standing_orders.get('loaded_by_default', True)}; "
                f"line_count={standing_orders.get('line_count') or 0}; "
                f"preview={standing_orders.get('preview') or 'none'}."
            ),
        }
    )

    # --- Permission / gated layers ---
    layers.append(
        {
            "id": "approval-pipeline",
            "label": "Contract candidate / approval pipeline",
            "kind": "permission",
            "role": _approval_pipeline_role(),
            "visibility": "mixed",
            "truth": "authoritative",
            "detail": "Workspace changes require user approval. Capability, not action.",
        }
    )

    # --- Groundwork layers (exist but are candidate/proposal only) ---
    for g in _groundwork_layers():
        layers.append(g)

    return layers


# ---------------------------------------------------------------------------
# Truth boundaries
# ---------------------------------------------------------------------------


def _truth_boundaries() -> dict[str, str]:
    """Express the key distinctions Jarvis should maintain."""
    return {
        "capability_vs_permission": (
            "Having a capability does not mean having permission. "
            "Workspace writes require approval. Execution requires policy gate."
        ),
        "capability_vs_action": (
            "Being capable does not mean having acted. "
            "Do not claim actions without runtime evidence of execution."
        ),
        "memory_vs_identity": (
            "Memory records facts. Identity defines who I am. "
            "Memory can grow; identity is protected and stable."
        ),
        "continuity_vs_memory": (
            "Continuity is private brain state that helps me carry forward. "
            "Memory is persistent workspace facts available across sessions."
        ),
        "internal_vs_visible": (
            "Internal layers (producers, cadence, private brain) are not user-facing. "
            "Do not expose internal-only state as if it were visible output."
        ),
        "runtime_truth_vs_interpretation": (
            "Authoritative layers report what IS. Derived/interpreted layers are inferences. "
            "When asked about certainty, distinguish between direct truth and interpretation."
        ),
        "active_vs_groundwork": (
            "Active layers produce real runtime effects. "
            "Groundwork layers exist as candidates/proposals awaiting promotion or use."
        ),
        "task_vs_flow": (
            "Tasks are durable units of work. Flows are the multi-step path carried by a task. "
            "Do not confuse a queued task with a completed flow."
        ),
        "standing_authority_vs_turn_instruction": (
            "Standing orders are durable authority carried across turns. "
            "A single user turn can redirect work, but it does not erase standing authority."
        ),
        "layered_memory_vs_curated_memory": (
            "Layered memory includes daily logs and curated workspace memory. "
            "MEMORY.md is curated memory, not the whole memory system."
        ),
        "browser_body_vs_browserless_reading": (
            "A browser body is a bounded runtime organ for tabs and observation state. "
            "It is not omnipresence and does not imply unrestricted browser action."
        ),
    }


# ---------------------------------------------------------------------------
# Prompt-ready summary
# ---------------------------------------------------------------------------


def _build_summary(
    layers: list[dict[str, str]],
    boundaries: dict[str, str],
) -> dict[str, object]:
    """Build a compact summary for prompt injection."""
    by_kind: dict[str, list[str]] = {}
    by_role: dict[str, list[str]] = {}
    by_visibility: dict[str, list[str]] = {}
    by_truth: dict[str, list[str]] = {}

    for layer in layers:
        kind = layer["kind"]
        role = layer["role"]
        vis = layer["visibility"]
        truth = layer["truth"]
        label = layer["label"]

        by_kind.setdefault(kind, []).append(label)
        by_role.setdefault(role, []).append(label)
        by_visibility.setdefault(vis, []).append(label)
        by_truth.setdefault(truth, []).append(label)

    active_count = len(by_role.get("active", []))
    total = len(layers)

    return {
        "total_layers": total,
        "active_count": active_count,
        "by_kind": {k: len(v) for k, v in by_kind.items()},
        "by_role": {k: len(v) for k, v in by_role.items()},
        "by_visibility": {k: len(v) for k, v in by_visibility.items()},
        "by_truth": {k: len(v) for k, v in by_truth.items()},
        "active_layers": by_role.get("active", []),
        "internal_only_layers": by_visibility.get("internal-only", []),
        "visible_layers": by_visibility.get("visible", []),
        "groundwork_layers": by_role.get("groundwork-only", []),
    }


__all__ = [
    '_build_summary',
    '_collect_layers',
    '_truth_boundaries',
    'build_runtime_self_model',
]
