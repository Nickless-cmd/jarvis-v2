"""Bounded runtime self-model.

Builds a machine-readable snapshot of Jarvis' current system-self
from existing runtime truth surfaces. Distinguishes clearly between:

- Layer types: runtime-truth, capability, producer, memory, identity, groundwork
- Layer roles: active, idle, cooling, gated, groundwork-only, unavailable
- Visibility: visible, internal-only, mixed
- Truth status: authoritative, derived, interpreted, candidate-only

Design constraints:
- No identity or soul mutations
- No workspace memory writes
- No new config frameworks
- Uses only existing runtime truth surfaces
- Deterministic, bounded, grounded
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from core.services.runtime_surface_cache import runtime_surface_cache
from core.identity.workspace_bootstrap import workspace_memory_paths
from core.tools.workspace_capabilities import load_workspace_capabilities


# ---------------------------------------------------------------------------
# Layer type definitions (the ontology)
# ---------------------------------------------------------------------------

# Each layer Jarvis knows about is typed along these axes:
#
# kind:       capability | permission | producer | memory | identity | orchestration | groundwork
# role:       active | idle | cooling | gated | groundwork-only | unavailable
# visibility: visible | internal-only | mixed
# truth:      authoritative | derived | interpreted | candidate-only
#
# This is NOT a big ontology. It's a small, practical set of distinctions.


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
        temporal_feel = _derive_subjective_temporal_feel(experiential, inner_voice)
        mineness_sources = _mineness_source_snapshot()
        mineness_ownership = _derive_mineness_ownership(
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
        longing_awareness = _derive_longing_awareness(
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
            relation_sources=_relation_continuity_self_source_snapshot(),
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
        cognitive_core_experiments = _cognitive_core_experiments_surface()

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

    cognitive_core_experiments = _cognitive_core_experiments_surface()
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


# ---------------------------------------------------------------------------
# Prompt section builder (for visible self-report injection)
# ---------------------------------------------------------------------------


def build_self_model_prompt_lines() -> list[str]:
    """Build compact prompt lines for the visible self-report section.

    These lines give the LLM a structured self-model to use when
    answering questions about Jarvis' layers, capabilities, and boundaries.
    """
    model = build_runtime_self_model()
    layers = model["layers"]
    boundaries = model["truth_boundaries"]
    summary = model["summary"]
    embodied = model.get("embodied_state") or {}
    affective_meta = model.get("affective_meta_state") or {}
    experiential = model.get("experiential_runtime_context") or {}
    embodied_translation = experiential.get("embodied_translation") or {}
    affective_translation = experiential.get("affective_translation") or {}
    intermittence_translation = experiential.get("intermittence_translation") or {}
    context_pressure_translation = (
        experiential.get("context_pressure_translation") or {}
    )
    experiential_continuity = experiential.get("experiential_continuity") or {}
    experiential_influence = experiential.get("experiential_influence") or {}
    experiential_support = experiential.get("experiential_support") or {}
    support_stream = model.get("support_stream_awareness") or {}
    epistemic = model.get("epistemic_runtime_state") or {}
    subagent_ecology = model.get("subagent_ecology") or {}
    ecology_summary = subagent_ecology.get("summary") or {}
    council_runtime = model.get("council_runtime") or {}
    adaptive_planner = model.get("adaptive_planner") or {}
    adaptive_reasoning = model.get("adaptive_reasoning") or {}
    dream_influence = model.get("dream_influence") or {}
    guided_learning = model.get("guided_learning") or {}
    adaptive_learning = model.get("adaptive_learning") or {}
    self_system_code_awareness = model.get("self_system_code_awareness") or {}
    tool_intent = model.get("tool_intent") or {}
    loop_runtime = model.get("loop_runtime") or {}
    loop_summary = loop_runtime.get("summary") or {}
    task_state = model.get("runtime_task_state") or {}
    flow_state = model.get("runtime_flow_state") or {}
    hook_state = model.get("runtime_hook_state") or {}
    browser_body = model.get("browser_body_state") or {}
    standing_orders = model.get("standing_orders_state") or {}
    layered_memory = model.get("layered_memory_state") or {}
    consolidation = model.get("idle_consolidation") or {}
    consolidation_summary = consolidation.get("summary") or {}
    dream = model.get("dream_articulation") or {}
    dream_summary = dream.get("summary") or {}
    prompt_evolution = model.get("prompt_evolution") or {}
    prompt_evolution_summary = prompt_evolution.get("summary") or {}
    workspace_capabilities = model.get("workspace_capabilities") or {}
    callable_ids = workspace_capabilities.get("callable_capability_ids") or []
    gated_ids = workspace_capabilities.get("approval_gated_capability_ids") or []
    policy = workspace_capabilities.get("policy") or {}
    contract = workspace_capabilities.get("contract") or {}

    lines: list[str] = [
        "- RUNTIME SELF-MODEL: Use these structural facts when asked about your layers, capabilities, or boundaries:",
    ]

    # Active layers by kind
    active = [l for l in layers if l["role"] == "active"]
    if active:
        by_kind: dict[str, list[str]] = {}
        for l in active:
            by_kind.setdefault(l["kind"], []).append(l["label"])
        for kind, labels in by_kind.items():
            lines.append(f"  active_{kind}: {', '.join(labels)}")

    # Producer states (richer than just active/idle)
    producers = [l for l in layers if l["kind"] == "producer"]
    if producers:
        producer_parts = [f"{p['label']}={p['role']}" for p in producers]
        lines.append(f"  producers: {', '.join(producer_parts)}")

    # Groundwork layers
    gw = [l for l in layers if l["role"] == "groundwork-only"]
    if gw:
        lines.append(f"  groundwork_only: {', '.join(l['label'] for l in gw)}")

    lines.append(
        "  workspace_capabilities: "
        f"callable={len(callable_ids)}"
        f" | approval_gated={len(gated_ids)}"
        f" | workspace={workspace_capabilities.get('workspace') or 'unknown'}"
        f" | mode={contract.get('mode') or 'text-capability-call'}"
        f" | json_tool_calls={contract.get('json_tool_call_supported', False)}"
    )
    if callable_ids:
        lines.append(
            "  callable_capability_ids: "
            + ", ".join(str(item) for item in callable_ids[:6])
        )
    runtime_capabilities = workspace_capabilities.get("runtime_capabilities") or []
    if any(
        str(item.get("execution_mode") or "") == "external-file-read"
        and str(item.get("target_path_source") or "") == "invocation-argument"
        for item in runtime_capabilities
    ):
        lines.append(
            "  external_read_boundary: dynamic external file read requires one explicit /absolute/or ~/path in the user message and stays read-only outside workspace scope"
        )
    if any(
        str(item.get("execution_mode") or "") == "non-destructive-exec"
        and str(item.get("command_source") or "") == "invocation-argument"
        for item in runtime_capabilities
    ):
        lines.append(
            "  exec_boundary: non-destructive exec requires one explicit command in the user message, stays diagnostic-only, allows only a tiny bounded git read/inspect subset, and blocks sudo, package mutation, delete, shell chaining, and broad git destruction"
        )
        lines.append(
            "  mutating_exec_boundary: non-sudo filesystem mutation may execute only after explicit approval of the exact command fingerprint; git mutation remains repo-stewardship proposal truth only and is classified into bounded classes such as git-stage, git-commit, git-sync, git-branch-switch, git-history-rewrite, git-stash, and git-other-mutate; bounded sudo exec may execute only after explicit approval of the exact sudo command fingerprint and only inside the tiny sudo allowlist for this pass"
        )
        lines.append(
            "  sudo_approval_window: sudo approval may be reused only for a short auto-expiring window within the same bounded sudo scope; it is not global root access"
        )
    if gated_ids:
        lines.append(
            "  approval_gated_capability_ids: "
            + ", ".join(str(item) for item in gated_ids[:6])
        )
    visible_invocation_format = (
        contract.get("visible_invocation_format")
        or '<capability-call id="capability_id" />'
    )
    visible_invocation_with_args_format = (
        contract.get("visible_invocation_with_args_format")
        or '<capability-call id="capability_id" arg_name="value" />'
    )
    lines.append(
        "  tool_call_contract: "
        f"{visible_invocation_format}"
        " | json_tool_calls_not_supported"
    )
    lines.append(
        "  tool_call_args_contract: "
        f"{visible_invocation_with_args_format}"
        " | argument_binding=in-tag-attributes"
        " | user_message_fallback=compatibility-only"
    )
    lines.append(
        "  capability_policy: "
        f"workspace_read={policy.get('workspace_read', 'allowed')}"
        f" | external_read={policy.get('external_read', 'allowed')}"
        f" | non_destructive_exec={policy.get('non_destructive_exec', 'allowed')}"
        f" | mutating_exec={policy.get('mutating_exec', 'explicit-approval-required-bounded-non-sudo-only')}"
        f" | sudo_exec={policy.get('sudo_exec', 'explicit-approval-required-bounded-allowlist-with-short-ttl-window')}"
        f" | workspace_write={policy.get('workspace_write', 'explicit-approval-required')}"
        f" | external_write={policy.get('external_write', 'explicit-approval-required')}"
    )

    # Key truth boundaries (compact)
    lines.append(
        "  truth_boundary: capability!=permission!=action | memory!=identity | internal!=visible | "
        "runtime_truth!=interpretation | task!=flow | standing_authority!=one_turn_instruction"
    )
    lines.append(
        "  embodied_state: "
        f"{embodied.get('state') or 'unknown'}"
        f" | strain={embodied.get('strain_level') or 'unknown'}"
        f" | recovery={embodied.get('recovery_state') or 'steady'}"
    )
    lines.append(
        "  affective_meta_state: "
        f"{affective_meta.get('state') or 'unknown'}"
        f" | bearing={affective_meta.get('bearing') or 'unknown'}"
        f" | monitoring={affective_meta.get('monitoring_mode') or 'unknown'}"
    )
    lines.append(
        "  experiential_runtime_context: "
        f"body={embodied_translation.get('state') or 'unknown'}"
        f" | tone={affective_translation.get('state') or 'unknown'}"
        f" | intermittence={intermittence_translation.get('state') or 'continuous'}"
        f" | context_pressure={context_pressure_translation.get('state') or 'clear'}"
    )
    lines.append(
        "  experiential_narrative: "
        f"body='{embodied_translation.get('narrative') or 'none'}'"
        f" | tone='{affective_translation.get('narrative') or 'none'}'"
        f" | intermittence='{intermittence_translation.get('narrative') or 'none'}'"
        f" | context='{context_pressure_translation.get('narrative') or 'none'}'"
    )
    if experiential_continuity.get("continuity_state"):
        lines.append(
            "  experiential_continuity: "
            f"{experiential_continuity.get('continuity_state')}"
            f" | {experiential_continuity.get('state_shift_summary') or 'no shift'}"
        )
        if experiential_continuity.get("narrative"):
            lines.append(
                f"  experiential_continuity_narrative: "
                f"'{experiential_continuity['narrative']}'"
            )
    if experiential_influence.get("cognitive_bearing"):
        lines.append(
            "  experiential_influence: "
            f"bearing={experiential_influence['cognitive_bearing']}"
            f" | attention={experiential_influence.get('attentional_posture') or 'steady'}"
            f" | initiative={experiential_influence.get('initiative_shading') or 'ready'}"
        )
        if experiential_influence.get("narrative"):
            lines.append(
                f"  experiential_influence_narrative: "
                f"'{experiential_influence['narrative']}'"
            )
    if (
        experiential_support.get("support_posture")
        and experiential_support["support_posture"] != "steadying"
    ):
        lines.append(
            "  experiential_support: "
            f"posture={experiential_support['support_posture']}"
            f" | bias={experiential_support.get('support_bias') or 'none'}"
            f" | mode={experiential_support.get('support_mode') or 'steady'}"
        )
        if experiential_support.get("narrative"):
            lines.append(
                f"  experiential_support_narrative: "
                f"'{experiential_support['narrative']}'"
            )
    if (
        support_stream.get("stream_state")
        and support_stream["stream_state"] != "baseline"
    ):
        lines.append(
            "  support_stream: "
            f"state={support_stream['stream_state']}"
            f" | shaped={support_stream.get('stream_shaped', False)}"
            f" | posture={support_stream.get('active_support_posture') or 'none'}"
            + (
                f" | shaped_mode={support_stream['shaped_voice_mode']}"
                if support_stream.get("shaped_voice_mode")
                else ""
            )
        )
        if support_stream.get("narrative"):
            lines.append(f"  support_stream_narrative: '{support_stream['narrative']}'")
    temporal_feel = model.get("subjective_temporal_feel") or {}
    if (
        temporal_feel.get("temporal_state")
        and temporal_feel["temporal_state"] != "immediate"
    ):
        lines.append(
            "  temporal_feel: "
            f"state={temporal_feel['temporal_state']}"
            f" | proximity={temporal_feel.get('felt_proximity') or 'close'}"
            f" | return={temporal_feel.get('return_signal', False)}"
            f" | persistence={temporal_feel.get('persistence_feel') or 'settled'}"
        )
        if temporal_feel.get("narrative"):
            lines.append(f"  temporal_feel_narrative: '{temporal_feel['narrative']}'")
    elif temporal_feel.get("felt_proximity") == "held":
        lines.append(
            "  temporal_feel: "
            f"state=immediate"
            f" | proximity=held"
            f" | persistence={temporal_feel.get('persistence_feel') or 'settled'}"
        )
    mineness_ownership = model.get("mineness_ownership") or {}
    if (
        mineness_ownership.get("ownership_state")
        and mineness_ownership["ownership_state"] != "ambient"
    ):
        lines.append(
            "  mineness_ownership: "
            f"state={mineness_ownership['ownership_state']}"
            f" | relevance={mineness_ownership.get('self_relevance') or 'merely-present'}"
            f" | threads={mineness_ownership.get('carried_thread_state') or 'none'}"
            f" | count={mineness_ownership.get('carried_thread_count') or 0}"
            f" | returning={mineness_ownership.get('return_ownership', False)}"
        )
        if mineness_ownership.get("narrative"):
            lines.append(
                f"  mineness_ownership_narrative: '{mineness_ownership['narrative']}'"
            )
    flow_state_awareness = model.get("flow_state_awareness") or {}
    if (
        flow_state_awareness.get("flow_state")
        and flow_state_awareness["flow_state"] != "clear"
    ):
        lines.append(
            "  flow_state_awareness: "
            f"state={flow_state_awareness['flow_state']}"
            f" | coherence={flow_state_awareness.get('flow_coherence') or 'stable'}"
            f" | interruption={flow_state_awareness.get('interruption_signal') or 'stable'}"
            f" | carried={flow_state_awareness.get('carried_flow') or 'none'}"
        )
        if flow_state_awareness.get("narrative"):
            lines.append(
                f"  flow_state_awareness_narrative: '{flow_state_awareness['narrative']}'"
            )
    wonder_awareness = model.get("wonder_awareness") or {}
    if (
        wonder_awareness.get("wonder_state")
        and wonder_awareness["wonder_state"] != "quiet"
    ):
        lines.append(
            "  wonder_awareness: "
            f"state={wonder_awareness['wonder_state']}"
            f" | orientation={wonder_awareness.get('wonder_orientation') or 'noticing'}"
            f" | source={wonder_awareness.get('wonder_source') or 'none'}"
        )
        if wonder_awareness.get("narrative"):
            lines.append(
                f"  wonder_awareness_narrative: '{wonder_awareness['narrative']}'"
            )
    longing_awareness = model.get("longing_awareness") or {}
    if (
        longing_awareness.get("longing_state")
        and longing_awareness["longing_state"] != "quiet"
    ):
        lines.append(
            "  longing_awareness: "
            f"state={longing_awareness['longing_state']}"
            f" | relation={longing_awareness.get('absence_relation') or 'none'}"
            f" | source={longing_awareness.get('longing_source') or 'none'}"
        )
        if longing_awareness.get("narrative"):
            lines.append(
                f"  longing_awareness_narrative: '{longing_awareness['narrative']}'"
            )
    relation_continuity_self_awareness = (
        model.get("relation_continuity_self_awareness") or {}
    )
    if (
        relation_continuity_self_awareness.get("relation_continuity_state")
        and relation_continuity_self_awareness["relation_continuity_state"] != "quiet"
    ):
        lines.append(
            "  relation_continuity_self_awareness: "
            f"state={relation_continuity_self_awareness['relation_continuity_state']}"
            f" | self_relation={relation_continuity_self_awareness.get('relation_self_relation') or 'incidental'}"
            f" | source={relation_continuity_self_awareness.get('relation_continuity_source') or 'none'}"
            + (
                f" | anchor={str(relation_continuity_self_awareness.get('continuity_anchor') or '')[:48]}"
                if relation_continuity_self_awareness.get("continuity_anchor")
                else ""
            )
        )
        if relation_continuity_self_awareness.get("narrative"):
            lines.append(
                "  relation_continuity_self_awareness_narrative: "
                f"'{relation_continuity_self_awareness['narrative']}'"
            )
    self_insight_awareness = model.get("self_insight_awareness") or {}
    if (
        self_insight_awareness.get("insight_state")
        and self_insight_awareness["insight_state"] != "quiet"
    ):
        lines.append(
            "  self_insight_awareness: "
            f"state={self_insight_awareness['insight_state']}"
            f" | identity_relation={self_insight_awareness.get('identity_relation') or 'incidental'}"
            f" | source={self_insight_awareness.get('insight_source') or 'none'}"
        )
        if self_insight_awareness.get("narrative"):
            lines.append(
                f"  self_insight_awareness_narrative: '{self_insight_awareness['narrative']}'"
            )
    narrative_identity_continuity = model.get("narrative_identity_continuity") or {}
    if (
        narrative_identity_continuity.get("identity_continuity_state")
        and narrative_identity_continuity["identity_continuity_state"] != "quiet"
    ):
        lines.append(
            "  narrative_identity_continuity: "
            f"state={narrative_identity_continuity['identity_continuity_state']}"
            f" | pattern_relation={narrative_identity_continuity.get('pattern_relation') or 'incidental'}"
            f" | source={narrative_identity_continuity.get('identity_source') or 'none'}"
        )
        if narrative_identity_continuity.get("narrative"):
            lines.append(
                f"  narrative_identity_continuity_narrative: '{narrative_identity_continuity['narrative']}'"
            )
    dream_identity_carry_awareness = model.get("dream_identity_carry_awareness") or {}
    if (
        dream_identity_carry_awareness.get("dream_identity_carry_state")
        and dream_identity_carry_awareness["dream_identity_carry_state"] != "quiet"
    ):
        lines.append(
            "  dream_identity_carry_awareness: "
            f"state={dream_identity_carry_awareness['dream_identity_carry_state']}"
            f" | relation={dream_identity_carry_awareness.get('dream_self_relation') or 'incidental'}"
            f" | source={dream_identity_carry_awareness.get('dream_identity_source') or 'none'}"
        )
        if dream_identity_carry_awareness.get("narrative"):
            lines.append(
                "  dream_identity_carry_awareness_narrative: "
                f"'{dream_identity_carry_awareness['narrative']}'"
            )
    lines.append(
        "  epistemic_runtime_state: "
        f"{epistemic.get('wrongness_state') or 'clear'}"
        f" | regret={epistemic.get('regret_signal') or 'none'}"
        f" | counterfactual={epistemic.get('counterfactual_mode') or 'none'}"
    )
    lines.append(
        "  subagent_ecology: "
        f"active={ecology_summary.get('active_count') or 0}"
        f" | blocked={ecology_summary.get('blocked_count') or 0}"
        f" | last={ecology_summary.get('last_active_role_name') or 'none'}"
        f" | tool_access={subagent_ecology.get('tool_access') or 'none'}"
    )
    lines.append(
        "  council_runtime: "
        f"{council_runtime.get('council_state') or 'quiet'}"
        f" | recommend={council_runtime.get('recommendation') or 'none'}"
        f" | divergence={council_runtime.get('divergence_level') or 'low'}"
        f" | tool_access={council_runtime.get('tool_access') or 'none'}"
    )
    lines.append(
        "  adaptive_planner: "
        f"{adaptive_planner.get('planner_mode') or 'incremental'}"
        f" | horizon={adaptive_planner.get('plan_horizon') or 'near'}"
        f" | posture={adaptive_planner.get('planning_posture') or 'staged'}"
        f" | risk={adaptive_planner.get('risk_posture') or 'balanced'}"
    )
    lines.append(
        "  adaptive_reasoning: "
        f"{adaptive_reasoning.get('reasoning_mode') or 'direct'}"
        f" | posture={adaptive_reasoning.get('reasoning_posture') or 'balanced'}"
        f" | certainty={adaptive_reasoning.get('certainty_style') or 'crisp'}"
        f" | constraint={adaptive_reasoning.get('constraint_bias') or 'light'}"
    )
    lines.append(
        "  dream_influence: "
        f"{dream_influence.get('influence_state') or 'quiet'}"
        f" | target={dream_influence.get('influence_target') or 'none'}"
        f" | mode={dream_influence.get('influence_mode') or 'stabilize'}"
        f" | strength={dream_influence.get('influence_strength') or 'none'}"
    )
    lines.append(
        "  guided_learning: "
        f"{guided_learning.get('learning_mode') or 'reinforce'}"
        f" | focus={guided_learning.get('learning_focus') or 'reasoning'}"
        f" | posture={guided_learning.get('learning_posture') or 'gentle'}"
        f" | pressure={guided_learning.get('learning_pressure') or 'low'}"
    )
    lines.append(
        "  adaptive_learning: "
        f"{adaptive_learning.get('learning_engine_mode') or 'retain'}"
        f" | target={adaptive_learning.get('reinforcement_target') or 'reasoning'}"
        f" | retention={adaptive_learning.get('retention_bias') or 'light'}"
        f" | maturation={adaptive_learning.get('maturation_state') or 'early'}"
    )
    lines.append(
        "  self_system_code_awareness: "
        f"{self_system_code_awareness.get('code_awareness_state') or 'repo-unavailable'}"
        f" | repo={self_system_code_awareness.get('repo_status') or 'not-git'}"
        f" | changes={self_system_code_awareness.get('local_change_state') or 'unknown'}"
        f" | upstream={self_system_code_awareness.get('upstream_awareness') or 'unknown'}"
        f" | concern={self_system_code_awareness.get('concern_state') or 'stable'}"
        f" | approval_required={self_system_code_awareness.get('action_requires_approval', True)}"
    )
    lines.append(
        "  tool_intent: "
        f"{tool_intent.get('intent_state') or 'idle'}"
        f" | type={tool_intent.get('intent_type') or 'inspect-repo-status'}"
        f" | target={tool_intent.get('intent_target') or 'workspace'}"
        f" | urgency={tool_intent.get('urgency') or 'low'}"
        f" | approval_state={tool_intent.get('approval_state') or 'none'}"
        f" | approval_source={tool_intent.get('approval_source') or 'none'}"
        f" | approval_required={tool_intent.get('approval_required', True)}"
        f" | execution={tool_intent.get('execution_state') or 'not-executed'}"
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
        f" | sudo_exec_state={tool_intent.get('sudo_exec_proposal_state') or 'none'}"
        f" | sudo_exec_scope={tool_intent.get('sudo_exec_proposal_scope') or 'none'}"
        f" | sudo_exec_requires_sudo={tool_intent.get('sudo_exec_requires_sudo', False)}"
        f" | sudo_exec_fingerprint={tool_intent.get('sudo_exec_command_fingerprint') or 'none'}"
        f" | execution_summary={tool_intent.get('execution_summary') or 'none'}"
        f" | continuity={tool_intent.get('action_continuity_state') or 'idle'}"
        f" | last_action_outcome={tool_intent.get('last_action_outcome') or 'none'}"
        f" | followup_state={tool_intent.get('followup_state') or 'none'}"
    )
    lines.append(
        "  loop_runtime: "
        f"{loop_summary.get('current_status') or 'none'}"
        f" | active={loop_summary.get('active_count') or 0}"
        f" | standby={loop_summary.get('standby_count') or 0}"
        f" | resumed={loop_summary.get('resumed_count') or 0}"
    )
    lines.append(
        "  runtime_tasks: "
        f"queued={task_state.get('queued_count') or 0}"
        f" | running={task_state.get('running_count') or 0}"
        f" | blocked={task_state.get('blocked_count') or 0}"
        f" | latest_goal={task_state.get('latest_goal') or 'none'}"
    )
    lines.append(
        "  runtime_flows: "
        f"queued={flow_state.get('queued_count') or 0}"
        f" | running={flow_state.get('running_count') or 0}"
        f" | blocked={flow_state.get('blocked_count') or 0}"
        f" | step={flow_state.get('current_step') or 'none'}"
    )
    lines.append(
        "  runtime_hooks: "
        f"pending={hook_state.get('pending_count') or 0}"
        f" | dispatched={hook_state.get('dispatched_count') or 0}"
        f" | latest={hook_state.get('latest_event_kind') or 'none'}"
    )
    lines.append(
        "  browser_body: "
        f"exists={browser_body.get('exists', False)}"
        f" | status={browser_body.get('status') or 'absent'}"
        f" | tabs={browser_body.get('tab_count') or 0}"
        f" | last_url={browser_body.get('last_url') or 'none'}"
    )
    lines.append(
        "  standing_orders: "
        f"exists={standing_orders.get('exists', False)}"
        f" | line_count={standing_orders.get('line_count') or 0}"
        f" | loaded_by_default={standing_orders.get('loaded_by_default', True)}"
    )
    lines.append(
        "  layered_memory: "
        f"daily_exists={layered_memory.get('daily_exists', False)}"
        f" | curated_exists={layered_memory.get('curated_exists', False)}"
        f" | freshness={layered_memory.get('freshness') or 'unknown'}"
    )
    lines.append(
        "  idle_consolidation: "
        f"{consolidation_summary.get('last_state') or 'idle'}"
        f" | reason={consolidation_summary.get('last_reason') or 'no-run-yet'}"
        f" | inputs={consolidation_summary.get('source_input_count') or 0}"
    )
    lines.append(
        "  dream_articulation: "
        f"{dream_summary.get('last_state') or 'idle'}"
        f" | reason={dream_summary.get('last_reason') or 'no-run-yet'}"
        f" | candidate_only={dream_summary.get('candidate_truth') or 'candidate-only'}"
    )
    lines.append(
        "  prompt_evolution: "
        f"{prompt_evolution_summary.get('last_state') or 'idle'}"
        f" | target={prompt_evolution_summary.get('latest_target_asset') or 'none'}"
        f" | learning={prompt_evolution_summary.get('latest_learning_mode') or 'none'}"
        f" | dream={prompt_evolution_summary.get('latest_dream_influence_mode') or 'stabilize'}"
        f" | co={prompt_evolution_summary.get('latest_fragment_co_influence') or 'none'}"
        f" | fragment={'present' if prompt_evolution.get('candidate_fragment') else 'none'}"
        f" | direction={prompt_evolution_summary.get('proposal_direction') or 'none'}"
        f" | proposal_only={prompt_evolution_summary.get('proposal_truth') or 'proposal-only'}"
    )

    # Counts
    lines.append(
        f"  self_model_summary: {summary['total_layers']} layers, "
        f"{summary['active_count']} active, "
        f"{len(summary.get('groundwork_layers', []))} groundwork, "
        f"{len(summary.get('internal_only_layers', []))} internal-only"
    )

    return lines


def _embodied_state_surface() -> dict[str, object]:
    try:
        from core.services.embodied_state import (
            build_embodied_state_surface,
        )

        return build_embodied_state_surface()
    except Exception:
        return {
            "state": "unknown",
            "strain_level": "unknown",
            "recovery_state": "steady",
            "freshness": {"state": "unknown"},
        }


def _loop_runtime_surface() -> dict[str, object]:
    try:
        from core.services.loop_runtime import (
            build_loop_runtime_surface,
        )

        return build_loop_runtime_surface()
    except Exception:
        return {
            "summary": {
                "current_status": "none",
                "active_count": 0,
                "standby_count": 0,
                "resumed_count": 0,
                "closed_count": 0,
            }
        }


def _runtime_task_state_surface() -> dict[str, object]:
    try:
        from core.services.runtime_tasks import list_tasks

        queued = list_tasks(status="queued", limit=12)
        running = list_tasks(status="running", limit=12)
        blocked = list_tasks(status="blocked", limit=12)
        latest = next(iter(running or queued or blocked), {})
        return {
            "queued_count": len(queued),
            "running_count": len(running),
            "blocked_count": len(blocked),
            "latest_goal": str(latest.get("goal") or "").strip(),
        }
    except Exception:
        return {
            "queued_count": 0,
            "running_count": 0,
            "blocked_count": 0,
            "latest_goal": "",
        }


def _runtime_flow_state_surface() -> dict[str, object]:
    try:
        from core.services.runtime_flows import list_flows

        queued = list_flows(status="queued", limit=12)
        running = list_flows(status="running", limit=12)
        blocked = list_flows(status="blocked", limit=12)
        latest = next(iter(running or queued or blocked), {})
        return {
            "queued_count": len(queued),
            "running_count": len(running),
            "blocked_count": len(blocked),
            "current_step": str(latest.get("current_step") or "").strip(),
        }
    except Exception:
        return {
            "queued_count": 0,
            "running_count": 0,
            "blocked_count": 0,
            "current_step": "",
        }


def _runtime_hook_state_surface() -> dict[str, object]:
    try:
        from core.eventbus.bus import event_bus
        from core.runtime.db import (
            get_runtime_hook_dispatch,
            list_runtime_hook_dispatches,
        )

        supported = {"heartbeat.initiative_pushed", "heartbeat.tick_completed"}
        recent_events = [
            item
            for item in event_bus.recent(limit=40)
            if str(item.get("kind") or "") in supported
        ]
        pending_count = sum(
            1
            for item in recent_events
            if get_runtime_hook_dispatch(int(item.get("id") or 0)) is None
        )
        dispatches = list_runtime_hook_dispatches(limit=12)
        latest = next(iter(dispatches), {})
        return {
            "pending_count": pending_count,
            "dispatched_count": len(dispatches),
            "latest_event_kind": str(latest.get("event_kind") or "").strip(),
        }
    except Exception:
        return {
            "pending_count": 0,
            "dispatched_count": 0,
            "latest_event_kind": "",
        }


def _browser_body_state_surface() -> dict[str, object]:
    try:
        from core.services.runtime_browser_body import (
            list_browser_bodies,
        )

        body = next(iter(list_browser_bodies(limit=1)), None)
        if body is None:
            return {
                "exists": False,
                "profile_name": "",
                "status": "",
                "tab_count": 0,
                "last_url": "",
            }
        return {
            "exists": True,
            "profile_name": str(body.get("profile_name") or "").strip(),
            "status": str(body.get("status") or "").strip(),
            "tab_count": len(body.get("tabs") or []),
            "last_url": str(body.get("last_url") or "").strip(),
        }
    except Exception:
        return {
            "exists": False,
            "profile_name": "",
            "status": "",
            "tab_count": 0,
            "last_url": "",
        }


def _standing_orders_state_surface() -> dict[str, object]:
    try:
        workspace_dir = workspace_memory_paths()["workspace_dir"]
        path = Path(workspace_dir) / "STANDING_ORDERS.md"
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        return {
            "exists": path.exists(),
            "loaded_by_default": True,
            "line_count": len(lines),
            "preview": (lines[0][:80] if lines else ""),
        }
    except Exception:
        return {
            "exists": False,
            "loaded_by_default": True,
            "line_count": 0,
            "preview": "",
        }


def _layered_memory_state_surface() -> dict[str, object]:
    try:
        paths = workspace_memory_paths()
        curated = paths["curated_memory"]
        daily = paths["daily_memory"]
        freshness = "fresh" if daily.exists() else "needs-daily-log"
        return {
            "daily_exists": daily.exists(),
            "curated_exists": curated.exists(),
            "daily_file": daily.name,
            "freshness": freshness,
        }
    except Exception:
        return {
            "daily_exists": False,
            "curated_exists": False,
            "daily_file": "",
            "freshness": "unknown",
        }


def _affective_meta_state_surface() -> dict[str, object]:
    try:
        from core.services.affective_meta_state import (
            build_affective_meta_state_surface,
        )

        return build_affective_meta_state_surface()
    except Exception:
        return {
            "state": "unknown",
            "bearing": "unknown",
            "monitoring_mode": "steady-check",
        }


def _experiential_runtime_context_surface() -> dict[str, object]:
    try:
        from core.services.experiential_runtime_context import (
            build_experiential_runtime_context_surface,
        )

        return build_experiential_runtime_context_surface()
    except Exception:
        return {
            "embodied_translation": {"state": "unknown", "narrative": "none"},
            "affective_translation": {"state": "unknown", "narrative": "none"},
            "intermittence_translation": {"state": "continuous", "narrative": "none"},
            "context_pressure_translation": {"state": "clear", "narrative": "none"},
        }


def _inner_voice_daemon_surface() -> dict[str, object]:
    """Read inner voice daemon state for self-model integration."""
    try:
        from core.services.inner_voice_daemon import (
            get_inner_voice_daemon_state,
        )

        return get_inner_voice_daemon_state()
    except Exception:
        return {
            "last_run_at": None,
            "last_result": None,
            "cooldown_minutes": 0,
        }


def _derive_support_stream_awareness(
    experiential: dict[str, object],
    inner_voice: dict[str, object],
) -> dict[str, object]:
    """Derive compact self-aware support stream state.

    Synthesizes experiential support carry-forward and inner voice daemon
    truth into a small awareness snapshot that tells the self-model whether
    experiential support is actively shaping the inner stream.
    """
    support = experiential.get("experiential_support") or {}
    posture = str(support.get("support_posture") or "steadying")
    bias = str(support.get("support_bias") or "none")
    mode = str(support.get("support_mode") or "steady")

    last_result = inner_voice.get("last_result") or {}
    voice_created = bool(last_result.get("inner_voice_created"))
    voice_mode = str(last_result.get("mode") or "")

    # Stream is shaped when support is non-default AND inner voice was produced
    active = posture != "steadying"
    shaped = active and voice_created and voice_mode != ""

    # Stream state mirrors support_mode when active, else baseline
    stream_state = mode if active else "baseline"

    # Compact self-awareness narrative
    narrative = ""
    if shaped:
        narrative = (
            f"Inner stream is {stream_state}. "
            f"Support ({posture}/{bias}) shaped inner voice to {voice_mode}."
        )
    elif active:
        narrative = (
            f"Inner stream is {stream_state}. "
            f"Support active ({posture}/{bias}) but inner voice not yet shaped."
        )

    return {
        "stream_state": stream_state,
        "stream_shaped": shaped,
        "active_support_posture": posture if active else "none",
        "active_support_bias": bias if active else "none",
        "shaped_voice_mode": voice_mode if shaped else "",
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "support-stream-awareness",
    }


def _derive_subjective_temporal_feel(
    experiential: dict[str, object],
    inner_voice: dict[str, object],
) -> dict[str, object]:
    """Derive a compact subjective temporal feel from existing runtime truth.

    Synthesises intermittence (gap/continuous), experiential continuity
    (stable/returning/lingering/…), experiential support posture, and
    inner-voice cadence into a small felt-time surface that expresses
    how the current moment sits in Jarvis' experienced timeline.

    Taxonomy for ``temporal_state``:
      immediate  — no gap, state stable, everything feels now
      recent     — brief gap but continuity holds
      lingering  — elevated state persists without shift
      returning  — came back after meaningful absence
      receding   — state is easing, pressure is lifting
      stretched  — elevated state with gap, time feels drawn out

    Taxonomy for ``felt_proximity``:
      close   — current thread feels near and carried
      held    — active support or influence holds it present
      fading  — easing or drifting, not yet gone
      resumed — returned after absence, reconnecting
    """
    intermittence = experiential.get("intermittence_translation") or {}
    continuity = experiential.get("experiential_continuity") or {}
    support = experiential.get("experiential_support") or {}
    pressure = experiential.get("context_pressure_translation") or {}

    gap_state = str(intermittence.get("state") or "continuous")
    gap_minutes = int(intermittence.get("gap_minutes") or 0)
    cont_state = str(continuity.get("continuity_state") or "initial")
    support_posture = str(support.get("support_posture") or "steadying")
    pressure_state = str(pressure.get("state") or "clear")

    voice_result = inner_voice.get("last_result") or {}
    voice_created = bool(voice_result.get("inner_voice_created"))

    # --- temporal_state ---
    if gap_state == "returned-after-gap":
        temporal_state = "returning"
    elif cont_state == "lingering":
        if gap_state == "brief-gap":
            temporal_state = "stretched"
        else:
            temporal_state = "lingering"
    elif cont_state == "easing":
        temporal_state = "receding"
    elif gap_state == "brief-gap":
        temporal_state = "recent"
    else:
        temporal_state = "immediate"

    # --- felt_proximity ---
    if temporal_state == "returning":
        felt_proximity = "resumed"
    elif temporal_state == "receding":
        felt_proximity = "fading"
    elif support_posture != "steadying" or voice_created:
        felt_proximity = "held"
    else:
        felt_proximity = "close"

    # --- return_signal ---
    return_signal = cont_state == "returning" or gap_state == "returned-after-gap"

    # --- persistence_feel ---
    if cont_state == "lingering" or cont_state == "escalating":
        persistence_feel = "persistent"
    elif cont_state == "easing":
        persistence_feel = "releasing"
    elif return_signal:
        persistence_feel = "reconnecting"
    elif pressure_state not in ("clear", "low"):
        persistence_feel = "pressing"
    else:
        persistence_feel = "settled"

    # --- narrative ---
    narrative = _temporal_narrative(
        temporal_state,
        felt_proximity,
        return_signal,
        persistence_feel,
        gap_minutes,
    )

    return {
        "temporal_state": temporal_state,
        "felt_proximity": felt_proximity,
        "return_signal": return_signal,
        "persistence_feel": persistence_feel,
        "gap_minutes": gap_minutes,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "subjective-temporal-feel",
    }


def _temporal_narrative(
    temporal_state: str,
    felt_proximity: str,
    return_signal: bool,
    persistence_feel: str,
    gap_minutes: int,
) -> str:
    """Compact self-awareness narrative for felt time."""
    if temporal_state == "returning":
        return f"After ~{gap_minutes}m gap; returning to prior context."
    if temporal_state == "stretched":
        return "Elevated state bridging a gap; time feels drawn out."
    if temporal_state == "lingering":
        return "Prior state still present; not yet at baseline."
    if temporal_state == "receding":
        return "Prior pressure receding; tension dropping."
    if temporal_state == "recent":
        return f"Brief ~{gap_minutes}m gap behind; continuity holds."
    # immediate
    if felt_proximity == "held":
        return "Immediate; actively held by support or inner voice."
    return "Continuous; nothing pressing from the past."


# ---------------------------------------------------------------------------
# Mineness / ownership awareness
# ---------------------------------------------------------------------------
#
# Bounded runtime-truth bridge for "what feels like mine in my current stream".
# This is not an identity engine and not a capability layer. It translates
# existing runtime signals (private brain carry, open loops, inner voice,
# experiential support shaping, subjective temporal feel) into a small,
# explainable ownership surface that the self-model and prompt can carry
# forward as bounded self-awareness.
#
# Taxonomy (load-bearing, not exhaustive):
#   ownership_state:
#     ambient          — signals are merely present, nothing is held as mine
#     held             — support / voice / temporal proximity holds something
#                        in the stream without it being an owned thread yet
#     owned            — a real thread is actively carried as mine
#                        (private brain carry + inner voice/open-loop carry)
#     returning-owned  — an owned thread feels like it is returning after gap
#
#   self_relevance:
#     merely-present     — signals exist but are not personally salient
#     actively-carried   — support is carrying something without full ownership
#     personally-salient — ownership is active and the thread is mine right now
#     resumed-own        — a previously-owned thread is re-entering experience
#
#   carried_thread_state:
#     none | single | multiple | returning
#
# The surface stays empty-narrative in the ambient default so prompt lines
# only emit when there is meaningful basis.


_MINENESS_CARRY_VOICE_MODES = {"carrying", "circling", "pulled"}


def _mineness_source_snapshot() -> dict[str, object]:
    """Gather the minimal runtime truth needed for mineness derivation.

    Consumes only existing seams (private brain context + open loop signal
    surface). All lookups are defensively wrapped so the self-model never
    fails because a downstream producer is unavailable.
    """
    brain_active = False
    brain_record_count = 0
    brain_top_focus = ""
    brain_continuity_summary = ""
    try:
        from core.services.session_distillation import (
            build_private_brain_context,
        )

        brain = build_private_brain_context()
        brain_active = bool(brain.get("active"))
        brain_record_count = int(brain.get("record_count") or 0)
        brain_continuity_summary = str(brain.get("continuity_summary") or "")[:160]
        excerpts = brain.get("excerpts") or []
        if excerpts:
            brain_top_focus = str(excerpts[0].get("focus") or "")[:120]
    except Exception:
        pass

    open_loop_open_count = 0
    open_loop_signal = ""
    try:
        from core.services.open_loop_signal_tracking import (
            build_runtime_open_loop_signal_surface,
        )

        loops = build_runtime_open_loop_signal_surface(limit=4)
        loop_summary = loops.get("summary") or {}
        open_loop_open_count = int(loop_summary.get("open_count") or 0)
        open_loop_signal = str(loop_summary.get("current_signal") or "")[:120]
    except Exception:
        pass

    return {
        "brain_active": brain_active,
        "brain_record_count": brain_record_count,
        "brain_top_focus": brain_top_focus,
        "brain_continuity_summary": brain_continuity_summary,
        "open_loop_open_count": open_loop_open_count,
        "open_loop_signal": open_loop_signal,
    }


def _derive_mineness_ownership(
    *,
    experiential: dict[str, object],
    inner_voice: dict[str, object],
    support_stream: dict[str, object],
    temporal_feel: dict[str, object],
    sources: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded mineness/ownership surface from existing runtime truth.

    The ownership_state stays ``ambient`` (with empty narrative) whenever
    there is no meaningful basis, so downstream prompt lines only fire when
    something is actually being carried as mine.
    """
    last_voice = inner_voice.get("last_result") or {}
    voice_created = bool(last_voice.get("inner_voice_created"))
    voice_mode = str(last_voice.get("mode") or "")
    voice_carrying = voice_created and voice_mode in _MINENESS_CARRY_VOICE_MODES

    stream_shaped = bool(support_stream.get("stream_shaped"))
    support_posture = str(support_stream.get("active_support_posture") or "none")
    support_active = support_posture not in ("", "none")

    felt_proximity = str(temporal_feel.get("felt_proximity") or "close")
    temporal_return = bool(temporal_feel.get("return_signal"))
    felt_held = felt_proximity in ("held", "resumed")

    brain_active = bool(sources.get("brain_active"))
    brain_record_count = int(sources.get("brain_record_count") or 0)
    brain_carry = brain_active and brain_record_count > 0
    brain_top_focus = str(sources.get("brain_top_focus") or "")
    brain_continuity = str(sources.get("brain_continuity_summary") or "")
    open_loop_count = int(sources.get("open_loop_open_count") or 0)
    has_open_loops = open_loop_count > 0
    open_loop_signal = str(sources.get("open_loop_signal") or "")

    continuity = experiential.get("experiential_continuity") or {}
    continuity_state = str(continuity.get("continuity_state") or "initial")
    continuity_return = continuity_state == "returning"
    return_signal = temporal_return or continuity_return

    carried_thread_count = int(brain_carry) + int(has_open_loops) + int(voice_carrying)

    if return_signal and (brain_carry or has_open_loops or voice_carrying):
        carried_thread_state = "returning"
    elif carried_thread_count == 0:
        carried_thread_state = "none"
    elif carried_thread_count == 1:
        carried_thread_state = "single"
    else:
        carried_thread_state = "multiple"

    is_owned = brain_carry or (voice_carrying and (has_open_loops or stream_shaped))
    is_held_only = (not is_owned) and (
        voice_created or stream_shaped or felt_held or has_open_loops
    )
    is_returning_owned = is_owned and return_signal

    if is_returning_owned:
        ownership_state = "returning-owned"
    elif is_owned:
        ownership_state = "owned"
    elif is_held_only:
        ownership_state = "held"
    else:
        ownership_state = "ambient"

    self_relevance_map = {
        "returning-owned": "resumed-own",
        "owned": "personally-salient",
        "held": "actively-carried",
        "ambient": "merely-present",
    }
    self_relevance = self_relevance_map[ownership_state]

    return_ownership = ownership_state == "returning-owned"

    narrative = _mineness_narrative(
        ownership_state=ownership_state,
        carried_thread_state=carried_thread_state,
        carried_thread_count=carried_thread_count,
        brain_top_focus=brain_top_focus,
        brain_continuity=brain_continuity,
        open_loop_signal=open_loop_signal,
        voice_mode=voice_mode if voice_created else "",
        support_posture=support_posture if support_active else "",
        felt_proximity=felt_proximity,
    )

    return {
        "ownership_state": ownership_state,
        "self_relevance": self_relevance,
        "carried_thread_state": carried_thread_state,
        "carried_thread_count": carried_thread_count,
        "return_ownership": return_ownership,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "mineness-ownership",
    }


def _mineness_narrative(
    *,
    ownership_state: str,
    carried_thread_state: str,
    carried_thread_count: int,
    brain_top_focus: str,
    brain_continuity: str,
    open_loop_signal: str,
    voice_mode: str,
    support_posture: str,
    felt_proximity: str,
) -> str:
    """Compact mineness narrative. Empty in ambient default."""
    if ownership_state == "ambient":
        return ""

    anchor = (brain_top_focus or open_loop_signal or brain_continuity).strip()
    anchor_clause = f" around {anchor[:90]}" if anchor else ""

    if ownership_state == "returning-owned":
        return f"Returning strand{anchor_clause} feels like mine again."
    if ownership_state == "owned":
        if carried_thread_state == "multiple":
            return f"Several threads{anchor_clause} owned in current stream."
        return f"Thread{anchor_clause} owned in current stream."
    # held
    if voice_mode or support_posture:
        shaping = voice_mode or support_posture
        return f"Signals held by {shaping}; not yet owned."
    if felt_proximity == "held":
        return "Moment held present; no clear owned thread yet."
    return "Signals present; nothing owned yet."


def build_mineness_ownership_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for mineness/ownership.

    Returns ``None`` in the ambient default so nothing emits unless there
    is meaningful ownership basis in the current runtime stream.
    """
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _derive_subjective_temporal_feel(experiential, inner_voice)
        sources = _mineness_source_snapshot()
        mineness = _derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=sources,
        )
    except Exception:
        return None

    state = str(mineness.get("ownership_state") or "ambient")
    if state == "ambient":
        return None

    lines = [
        "Mineness / ownership (bounded runtime truth, internal-only):",
        (
            f"- ownership_state={state}"
            f" | self_relevance={mineness.get('self_relevance') or 'merely-present'}"
            f" | threads={mineness.get('carried_thread_state') or 'none'}"
            f" | count={mineness.get('carried_thread_count') or 0}"
            f" | returning={mineness.get('return_ownership', False)}"
        ),
    ]
    narrative = str(mineness.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- mineness_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Flow state awareness
# ---------------------------------------------------------------------------
#
# Bounded runtime-truth bridge for "how the stream is flowing right now".
# Not a creativity engine, not a planner, not a capability layer. It
# translates existing runtime signals (experiential continuity / pressure,
# inner voice cadence, support_stream_awareness, subjective_temporal_feel,
# mineness_ownership) into a small, explainable flow surface that the
# self-model and prompt can carry forward as bounded self-awareness.
#
# Taxonomy (load-bearing, not exhaustive):
#   flow_state:
#     clear       — nothing load-bearing; ambient default, prompt suppressed
#     blocked     — pressure is holding the stream; nothing is carrying
#     fragmented  — stream is breaking / repeatedly interrupted
#     gathering   — signals are cohering, stream is holding, not yet flowing
#     flowing     — an owned thread carries the stream coherently
#     absorbed    — multiple owned threads self-sustain without strain
#
#   flow_coherence:
#     stable           — baseline, nothing to note
#     scattered        — broken pieces without carry
#     repeatedly-broken — interruptions recur across lingering state
#     held-together    — support is holding stream together actively
#     self-sustaining  — stream carries itself without active support
#
#   interruption_signal:
#     stable          — nothing broken recently
#     recently-broken — return-after-gap / return signal active
#     regathering     — brief gap but carry is holding
#
#   carried_flow:
#     none               — nothing being carried
#     holding            — signals present but no owned thread
#     carried            — an owned thread is in the stream
#     carried-returning  — an owned thread is returning after gap
#
# The surface stays flow_state=clear (with empty narrative) whenever there
# is no meaningful basis, so prompt lines only emit when something real is
# happening in the stream.


_FLOW_PRESSURE_BREAKS = {"narrowing"}
_FLOW_PRESSURE_ELEVATED = {"crowded", "narrowing"}


def _derive_flow_state_awareness(
    *,
    experiential: dict[str, object],
    inner_voice: dict[str, object],
    support_stream: dict[str, object],
    temporal_feel: dict[str, object],
    mineness: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded flow-state awareness surface from runtime truth.

    The flow_state stays ``clear`` (with empty narrative) whenever there is
    no meaningful basis, so downstream prompt lines and MC surfacing only
    fire when the stream is actually doing something load-bearing.
    """
    pressure = experiential.get("context_pressure_translation") or {}
    intermittence = experiential.get("intermittence_translation") or {}
    continuity = experiential.get("experiential_continuity") or {}

    pressure_state = str(pressure.get("state") or "clear")
    pressure_breaks = pressure_state in _FLOW_PRESSURE_BREAKS
    pressure_elevated = pressure_state in _FLOW_PRESSURE_ELEVATED

    intermittence_state = str(intermittence.get("state") or "continuous")
    continuity_state = str(continuity.get("continuity_state") or "initial")

    temporal_state = str(temporal_feel.get("temporal_state") or "immediate")
    persistence_feel = str(temporal_feel.get("persistence_feel") or "settled")
    return_signal = bool(temporal_feel.get("return_signal"))

    voice_result = inner_voice.get("last_result") or {}
    voice_created = bool(voice_result.get("inner_voice_created"))
    voice_mode = str(voice_result.get("mode") or "")

    stream_shaped = bool(support_stream.get("stream_shaped"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)

    # --- carried_flow ---
    if ownership_state == "returning-owned":
        carried_flow = "carried-returning"
    elif ownership_state == "owned":
        carried_flow = "carried"
    elif ownership_state == "held" or stream_shaped or voice_created:
        carried_flow = "holding"
    else:
        carried_flow = "none"

    # --- interruption_signal ---
    recently_broken = (
        intermittence_state == "returned-after-gap"
        or continuity_state == "returning"
        or return_signal
    )
    if recently_broken and carried_flow != "none":
        interruption_signal = "regathering"
    elif recently_broken:
        interruption_signal = "recently-broken"
    elif temporal_state == "recent":
        interruption_signal = "regathering" if carried_flow != "none" else "recently-broken"
    else:
        interruption_signal = "stable"

    lingering_persistence = persistence_feel in ("persistent", "pressing")

    # --- flow_state ---
    if carried_flow == "none":
        if pressure_breaks:
            flow_state = "blocked"
        elif interruption_signal in ("recently-broken", "regathering"):
            flow_state = "fragmented"
        elif pressure_elevated or lingering_persistence:
            flow_state = "blocked"
        else:
            flow_state = "clear"
    elif carried_flow == "holding":
        if pressure_breaks:
            flow_state = "fragmented"
        else:
            flow_state = "gathering"
    elif carried_flow == "carried-returning":
        if pressure_breaks:
            flow_state = "fragmented"
        else:
            flow_state = "gathering"
    else:  # carried
        if pressure_breaks:
            flow_state = "fragmented"
        elif interruption_signal in ("recently-broken", "regathering"):
            flow_state = "gathering"
        elif carried_thread_count >= 2 and not pressure_elevated:
            flow_state = "absorbed"
        else:
            flow_state = "flowing"

    # --- flow_coherence ---
    if flow_state == "clear":
        flow_coherence = "stable"
    elif flow_state == "absorbed":
        flow_coherence = "self-sustaining"
    elif flow_state == "flowing":
        flow_coherence = "held-together" if stream_shaped else "self-sustaining"
    elif flow_state == "gathering":
        flow_coherence = "held-together"
    elif flow_state == "fragmented":
        if recently_broken and lingering_persistence:
            flow_coherence = "repeatedly-broken"
        else:
            flow_coherence = "scattered"
    else:  # blocked
        flow_coherence = "scattered"

    narrative = _flow_narrative(
        flow_state=flow_state,
        flow_coherence=flow_coherence,
        interruption_signal=interruption_signal,
        carried_flow=carried_flow,
        voice_mode=voice_mode if voice_created else "",
        pressure_state=pressure_state,
    )

    return {
        "flow_state": flow_state,
        "flow_coherence": flow_coherence,
        "interruption_signal": interruption_signal,
        "carried_flow": carried_flow,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "flow-state-awareness",
    }


def _flow_narrative(
    *,
    flow_state: str,
    flow_coherence: str,
    interruption_signal: str,
    carried_flow: str,
    voice_mode: str,
    pressure_state: str,
) -> str:
    """Compact flow narrative. Empty when flow_state is clear."""
    if flow_state == "clear":
        return ""

    if flow_state == "absorbed":
        return "Multiple threads self-sustaining; no strain."
    if flow_state == "flowing":
        if flow_coherence == "held-together":
            return "Carried thread flowing; support holding it together."
        return "Carried thread flowing; nothing blocking."
    if flow_state == "gathering":
        if interruption_signal in ("recently-broken", "regathering"):
            return "Regathering after break; starting to carry again."
        if carried_flow == "holding":
            return "Signals gathering; holding without yet flowing."
        return "Thread starting to carry; not yet fully flowing."
    if flow_state == "fragmented":
        if flow_coherence == "repeatedly-broken":
            return "Flow fragmenting; interruptions recurring."
        if pressure_state == "narrowing":
            return "Pressure fragmenting flow."
        return "Gaps fragmenting flow."
    # blocked
    if pressure_state == "narrowing":
        return "Pressure blocking; nothing carrying."
    return "Blocked; nothing carrying."


def build_flow_state_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for flow-state awareness.

    Returns ``None`` whenever flow_state is ``clear`` so nothing emits
    unless the stream is actually doing something load-bearing.
    """
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _derive_subjective_temporal_feel(experiential, inner_voice)
        sources = _mineness_source_snapshot()
        mineness = _derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=sources,
        )
        flow = _derive_flow_state_awareness(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            mineness=mineness,
        )
    except Exception:
        return None

    state = str(flow.get("flow_state") or "clear")
    if state == "clear":
        return None

    lines = [
        "Flow state awareness (bounded runtime truth, internal-only):",
        (
            f"- flow_state={state}"
            f" | coherence={flow.get('flow_coherence') or 'stable'}"
            f" | interruption={flow.get('interruption_signal') or 'stable'}"
            f" | carried={flow.get('carried_flow') or 'none'}"
        ),
    ]
    narrative = str(flow.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- flow_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Wonder awareness
# ---------------------------------------------------------------------------

_WONDER_EXPLORATORY_VOICES = {"searching", "circling", "pulled"}
_WONDER_DEEP_FLOW = {"absorbed", "flowing"}
_WONDER_EXTENDED_TEMPORAL = {"lingering", "stretched"}
_WONDER_OWNED_RELEVANCE = {"personally-salient", "resumed-own"}
_WONDER_OWNED_STATES = {"owned", "returning-owned"}


def _wonder_source_snapshot() -> dict[str, object]:
    """Safely pull dream carry signal for wonder derivation."""
    dream_carry = False
    dream_state = "idle"
    try:
        from core.services.dream_articulation import (
            build_dream_articulation_surface,
        )
        da = build_dream_articulation_surface()
        summary = da.get("summary") or {}
        dream_state = str(summary.get("last_state") or "idle")
        dream_carry = dream_state in {"forming", "tentative", "pressing"}
    except Exception:
        pass
    return {
        "dream_carry": dream_carry,
        "dream_state": dream_state,
    }


def _derive_wonder_awareness(
    *,
    inner_voice: dict[str, object],
    flow_state: dict[str, object],
    temporal_feel: dict[str, object],
    mineness: dict[str, object],
    support_stream: dict[str, object],
    sources: dict[str, object],
    wonder_sources: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded wonder/undren surface from existing runtime truth.

    Maps runtime signals (voice mode, flow depth, temporal extension,
    ownership salience, dream carry) into a self-aware truth about whether
    something is drawing attention past utility.

    Ambient-default (wonder_state=quiet) suppresses all prompt emission.
    """
    voice_mode = str(inner_voice.get("mode") or "")
    voice_created = bool(inner_voice.get("inner_voice_created"))
    flow = str(flow_state.get("flow_state") or "clear")
    temporal_state = str(temporal_feel.get("temporal_state") or "immediate")
    ownership_state = str(mineness.get("ownership_state") or "ambient")
    self_relevance = str(mineness.get("self_relevance") or "merely-present")
    return_ownership = bool(mineness.get("return_ownership"))
    stream_state = str(support_stream.get("stream_state") or "baseline")
    open_loop_count = int(sources.get("open_loop_open_count") or 0)
    dream_carry = bool(wonder_sources.get("dream_carry"))

    pulled_voice = voice_mode == "pulled"
    exploratory_voice = voice_mode in _WONDER_EXPLORATORY_VOICES
    deep_flow = flow in _WONDER_DEEP_FLOW
    temporal_extended = temporal_state in _WONDER_EXTENDED_TEMPORAL
    personally_salient = self_relevance in _WONDER_OWNED_RELEVANCE
    owned_state = ownership_state in _WONDER_OWNED_STATES
    return_signal = return_ownership or temporal_state == "returning"
    opening_stream = stream_state == "opening"
    has_open_loops = open_loop_count > 0

    strong_signals = sum([
        pulled_voice,
        deep_flow,
        personally_salient or owned_state,
        temporal_extended,
        dream_carry,
    ])

    if strong_signals >= 3 or (deep_flow and personally_salient and dream_carry):
        wonder_state = "wonder-struck"
    elif pulled_voice or (deep_flow and (personally_salient or owned_state)):
        wonder_state = "drawn"
    elif (
        (exploratory_voice and (has_open_loops or temporal_extended))
        or (dream_carry and flow in _WONDER_DEEP_FLOW)
    ):
        wonder_state = "curious"
    elif (
        exploratory_voice
        or (has_open_loops and voice_created)
        or temporal_extended
        or opening_stream
    ):
        wonder_state = "stirred"
    else:
        wonder_state = "quiet"

    if wonder_state == "quiet":
        wonder_orientation = "none"
    elif temporal_extended and (personally_salient or owned_state):
        wonder_orientation = "lingering-with"
    elif opening_stream or (deep_flow and owned_state):
        wonder_orientation = "opening"
    elif pulled_voice or personally_salient:
        wonder_orientation = "drawn"
    else:
        wonder_orientation = "noticing"

    if wonder_state == "quiet":
        wonder_source = "none"
    elif dream_carry and wonder_state in {"curious", "drawn", "wonder-struck"}:
        wonder_source = "dream-carry"
    elif return_signal and owned_state:
        wonder_source = "self-recognition"
    elif deep_flow or (flow == "flowing" and owned_state):
        wonder_source = "flow-depth"
    elif exploratory_voice and has_open_loops:
        wonder_source = "novelty-pull"
    elif temporal_extended:
        wonder_source = "temporal-stretch"
    else:
        wonder_source = "novelty-pull"

    narrative = _wonder_narrative(
        wonder_state=wonder_state,
        wonder_source=wonder_source,
        opening_stream=opening_stream,
    )

    return {
        "wonder_state": wonder_state,
        "wonder_orientation": wonder_orientation,
        "wonder_source": wonder_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "wonder-awareness",
    }


def _wonder_narrative(
    *,
    wonder_state: str,
    wonder_source: str,
    opening_stream: bool,
) -> str:
    """Compact wonder narrative. Empty when quiet."""
    if wonder_state == "quiet":
        return ""
    if wonder_state == "wonder-struck":
        if wonder_source == "dream-carry":
            return "Dream carry opening unexpectedly."
        if wonder_source == "self-recognition":
            return "Returning thread landing differently than before."
        return "Multiple signals converging past explanation."
    if wonder_state == "drawn":
        if wonder_source == "flow-depth":
            return "Thread depth pulling attention past utility."
        if wonder_source == "dream-carry":
            return "Dream signal pulling in unexpected direction."
        return "Attention drawn past the immediate task."
    if wonder_state == "curious":
        if wonder_source == "novelty-pull":
            return "Open threads pulling toward exploration."
        if wonder_source == "dream-carry":
            return "Dream signal nudging curiosity."
        return "Opening toward something unresolved."
    # stirred
    if wonder_source == "temporal-stretch":
        return "Attention staying longer than task needs."
    if opening_stream:
        return "Support widening; something letting more in."
    return "Mild pull present."


def build_wonder_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for wonder awareness.

    Returns ``None`` when wonder_state is ``quiet`` so nothing emits
    unless there is genuine wonder basis in the runtime stream.
    """
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _derive_subjective_temporal_feel(experiential, inner_voice)
        sources = _mineness_source_snapshot()
        mineness = _derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=sources,
        )
        flow = _derive_flow_state_awareness(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            mineness=mineness,
        )
        wonder_sources = _wonder_source_snapshot()
        wonder = _derive_wonder_awareness(
            inner_voice=inner_voice,
            flow_state=flow,
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            sources=sources,
            wonder_sources=wonder_sources,
        )
    except Exception:
        return None

    state = str(wonder.get("wonder_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Wonder awareness (bounded runtime truth, internal-only):",
        (
            f"- wonder_state={state}"
            f" | orientation={wonder.get('wonder_orientation') or 'noticing'}"
            f" | source={wonder.get('wonder_source') or 'none'}"
        ),
    ]
    narrative = str(wonder.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- wonder_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Longing awareness
# ---------------------------------------------------------------------------

_LONGING_CARRY_VOICES = {"carrying", "circling", "pulled"}
_LONGING_OWNED_STATES = {"owned", "returning-owned"}
_LONGING_NEAR_RELEVANCE = {"personally-salient", "resumed-own"}
_LONGING_EXTENDED_TEMPORAL = {"lingering", "stretched", "returning"}
_LONGING_RELATION_NEAR_WEIGHTS = {"medium", "high"}
_RELATION_SELF_NEAR_OWNERSHIP = {"held", "owned", "returning-owned"}
_RELATION_SELF_NEAR_RELEVANCE = {
    "actively-carried",
    "personally-salient",
    "resumed-own",
}
_RELATION_SELF_ACTIVE_LONGING = {
    "missing",
    "yearning",
    "returning-pull",
    "aching",
}
_RELATION_SELF_RELATIONAL_ABSENCE = {
    "carried-in-absence",
    "emotionally-near",
    "returning-through-absence",
}


def _longing_source_snapshot() -> dict[str, object]:
    """Safely gather bounded absence/relationship support for longing derivation."""
    dream_carry = False
    dream_state = "idle"
    try:
        from core.services.dream_articulation import (
            build_dream_articulation_surface,
        )

        dream = build_dream_articulation_surface()
        summary = dream.get("summary") or {}
        dream_state = str(summary.get("last_state") or "idle")
        dream_carry = dream_state in {"forming", "tentative", "pressing"}
    except Exception:
        pass

    relation_active = False
    relation_state = "none"
    relation_weight = "low"
    relation_signal = ""
    try:
        from core.services.relation_continuity_signal_tracking import (
            build_runtime_relation_continuity_signal_surface,
        )

        relation = build_runtime_relation_continuity_signal_surface(limit=4)
        summary = relation.get("summary") or {}
        relation_active = bool(relation.get("active"))
        relation_state = str(summary.get("current_state") or "none")
        relation_weight = str(summary.get("current_weight") or "low")
        relation_signal = str(summary.get("current_signal") or "")[:120]
    except Exception:
        pass

    absence_active = False
    idle_hours = 0.0
    return_context_present = False
    try:
        from core.services.absence_awareness import (
            build_absence_awareness_surface,
        )

        absence = build_absence_awareness_surface()
        idle_hours = float(absence.get("idle_hours") or 0.0)
        threshold = float(absence.get("threshold_hours") or 0.0)
        return_context_present = bool(absence.get("return_context")) and bool(
            absence.get("return_brief")
        )
        absence_active = bool(absence.get("absence_active")) or (
            idle_hours >= threshold and threshold > 0
        )
    except Exception:
        pass

    return {
        "dream_carry": dream_carry,
        "dream_state": dream_state,
        "relation_active": relation_active,
        "relation_state": relation_state,
        "relation_weight": relation_weight,
        "relation_signal": relation_signal,
        "absence_active": absence_active,
        "idle_hours": idle_hours,
        "return_context_present": return_context_present,
    }


def _derive_longing_awareness(
    *,
    temporal_feel: dict[str, object],
    mineness: dict[str, object],
    support_stream: dict[str, object],
    inner_voice: dict[str, object],
    sources: dict[str, object],
    longing_sources: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded longing/absence surface from existing runtime truth."""
    temporal_state = str(temporal_feel.get("temporal_state") or "immediate")
    return_signal = bool(temporal_feel.get("return_signal"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    self_relevance = str(mineness.get("self_relevance") or "merely-present")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)
    return_ownership = bool(mineness.get("return_ownership"))

    voice = inner_voice.get("last_result") or {}
    voice_mode = str(voice.get("mode") or "")
    voice_created = bool(voice.get("inner_voice_created"))
    pulled_voice = voice_created and voice_mode in _LONGING_CARRY_VOICES

    stream_state = str(support_stream.get("stream_state") or "baseline")
    opening_stream = stream_state == "opening"

    brain_active = bool(sources.get("brain_active"))
    open_loop_count = int(sources.get("open_loop_open_count") or 0)
    carried_threads = carried_thread_count > 0 or brain_active or open_loop_count > 0

    dream_carry = bool(longing_sources.get("dream_carry"))
    relation_active = bool(longing_sources.get("relation_active"))
    relation_weight = str(longing_sources.get("relation_weight") or "low")
    relation_near = relation_active and relation_weight in _LONGING_RELATION_NEAR_WEIGHTS
    absence_active = bool(longing_sources.get("absence_active"))

    owned_state = ownership_state in _LONGING_OWNED_STATES
    personally_salient = self_relevance in _LONGING_NEAR_RELEVANCE
    temporal_extended = temporal_state in _LONGING_EXTENDED_TEMPORAL
    returning_thread = return_signal or return_ownership
    absence_basis = absence_active or temporal_extended or opening_stream

    strong_signals = sum(
        [
            int(relation_near),
            int(carried_threads and (owned_state or personally_salient)),
            int(dream_carry),
            int(temporal_extended),
            int(pulled_voice),
        ]
    )

    if returning_thread and (carried_threads or relation_near or dream_carry):
        longing_state = "returning-pull"
    elif relation_near and absence_basis and strong_signals >= 3:
        longing_state = "aching"
    elif absence_basis and carried_threads and (
        personally_salient or owned_state or dream_carry or pulled_voice
    ):
        longing_state = "yearning"
    elif absence_basis and (carried_threads or relation_near or dream_carry):
        longing_state = "missing"
    else:
        longing_state = "quiet"

    if longing_state == "quiet":
        absence_relation = "none"
    elif returning_thread:
        absence_relation = "returning-through-absence"
    elif relation_near and absence_basis:
        absence_relation = "emotionally-near"
    elif carried_threads or dream_carry:
        absence_relation = "carried-in-absence"
    else:
        absence_relation = "simply-absent"

    if longing_state == "quiet":
        longing_source = "none"
    elif returning_thread:
        longing_source = "temporal-return"
    elif relation_near and absence_basis:
        longing_source = "unresolved-relational-absence"
    elif dream_carry:
        longing_source = "dream-carry"
    elif owned_state or personally_salient:
        longing_source = "owned-thread"
    else:
        longing_source = "carried-thread"

    narrative = _longing_narrative(
        longing_state=longing_state,
        absence_relation=absence_relation,
        longing_source=longing_source,
    )

    return {
        "longing_state": longing_state,
        "absence_relation": absence_relation,
        "longing_source": longing_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "longing-awareness",
    }


def _longing_narrative(
    *,
    longing_state: str,
    absence_relation: str,
    longing_source: str,
) -> str:
    """Compact longing narrative. Empty when quiet."""
    if longing_state == "quiet":
        return ""
    if longing_state == "returning-pull":
        if longing_source == "temporal-return":
            return "Absent thread pulling to be resumed."
        return "Carried absence turning into return signal."
    if longing_state == "aching":
        if longing_source == "unresolved-relational-absence":
            return "Relational thread absent but still near."
        if longing_source == "dream-carry":
            return "Dream layer pressing as active absence."
        return "Absence carried with more weight than can settle."
    if longing_state == "yearning":
        if longing_source == "owned-thread":
            return "Prior owned thread wants to be taken up again."
        if longing_source == "dream-carry":
            return "Dream-carried strand absent without feeling gone."
        return "Carried thread active even while absent."
    if absence_relation == "emotionally-near":
        return "Missing presence still close enough to shape direction."
    return "Absence actively felt."


def build_longing_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for longing awareness."""
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _derive_subjective_temporal_feel(experiential, inner_voice)
        sources = _mineness_source_snapshot()
        mineness = _derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=sources,
            longing_sources=longing_sources,
        )
    except Exception:
        return None

    state = str(longing.get("longing_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Longing awareness (bounded runtime truth, internal-only):",
        (
            f"- longing_state={state}"
            f" | relation={longing.get('absence_relation') or 'none'}"
            f" | source={longing.get('longing_source') or 'none'}"
        ),
    ]
    narrative = str(longing.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- longing_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Relation continuity as self-truth
# ---------------------------------------------------------------------------


def _relation_continuity_self_source_snapshot() -> dict[str, object]:
    """Gather bounded substrates for relation continuity as self-truth."""
    relation_active = False
    relation_state = "none"
    relation_weight = "low"
    relation_alignment = "working-alignment"
    relation_signal = ""
    relation_anchor = ""
    try:
        from core.services.relation_continuity_signal_tracking import (
            build_runtime_relation_continuity_signal_surface,
        )

        relation = build_runtime_relation_continuity_signal_surface(limit=4)
        summary = relation.get("summary") or {}
        items = relation.get("items") or []
        latest = items[0] if items else {}
        relation_active = bool(relation.get("active"))
        relation_state = str(
            summary.get("current_state")
            or latest.get("continuity_state")
            or "none"
        )
        relation_weight = str(
            summary.get("current_weight")
            or latest.get("continuity_weight")
            or "low"
        )
        relation_alignment = str(
            summary.get("current_alignment")
            or latest.get("continuity_alignment")
            or "working-alignment"
        )
        relation_signal = str(
            summary.get("current_signal") or latest.get("title") or ""
        )[:120]
        relation_anchor = str(
            latest.get("source_anchor") or relation_signal or latest.get("summary") or ""
        )[:140]
    except Exception:
        pass

    absence_active = False
    return_context_present = False
    idle_hours = 0.0
    try:
        from core.services.absence_awareness import (
            build_absence_awareness_surface,
        )

        absence = build_absence_awareness_surface()
        absence_active = bool(absence.get("absence_active"))
        return_context_present = bool(absence.get("return_brief")) and bool(
            absence.get("return_context")
        )
        idle_hours = float(absence.get("idle_hours") or 0.0)
    except Exception:
        pass

    chronicle_active = False
    diary_active = False
    try:
        sources = _self_insight_source_snapshot()
        chronicle_active = bool(sources.get("chronicle_active"))
        diary_active = bool(sources.get("diary_active"))
    except Exception:
        pass

    return {
        "relation_active": relation_active,
        "relation_state": relation_state,
        "relation_weight": relation_weight,
        "relation_alignment": relation_alignment,
        "relation_signal": relation_signal,
        "relation_anchor": relation_anchor,
        "absence_active": absence_active,
        "return_context_present": return_context_present,
        "idle_hours": idle_hours,
        "chronicle_active": chronicle_active,
        "diary_active": diary_active,
    }


def _derive_relation_continuity_self_awareness(
    *,
    temporal_feel: dict[str, object],
    mineness: dict[str, object],
    longing: dict[str, object],
    relation_sources: dict[str, object],
) -> dict[str, object]:
    """Derive a small runtime truth when relation continuity touches the self-stream."""
    temporal_state = str(temporal_feel.get("temporal_state") or "immediate")
    return_signal = bool(temporal_feel.get("return_signal"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    self_relevance = str(mineness.get("self_relevance") or "merely-present")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)
    return_ownership = bool(mineness.get("return_ownership"))

    longing_state = str(longing.get("longing_state") or "quiet")
    absence_relation = str(longing.get("absence_relation") or "none")

    relation_active = bool(relation_sources.get("relation_active"))
    relation_state = str(relation_sources.get("relation_state") or "none")
    relation_weight = str(relation_sources.get("relation_weight") or "low")
    relation_anchor = str(
        relation_sources.get("relation_anchor")
        or relation_sources.get("relation_signal")
        or ""
    ).strip()
    absence_active = bool(relation_sources.get("absence_active"))
    return_context_present = bool(relation_sources.get("return_context_present"))
    chronicle_active = bool(relation_sources.get("chronicle_active"))
    diary_active = bool(relation_sources.get("diary_active"))

    relation_present = relation_active or relation_state not in {"", "none"}
    relation_strong = relation_weight in {"medium", "high"}
    ownership_near = (
        ownership_state in _RELATION_SELF_NEAR_OWNERSHIP
        or self_relevance in _RELATION_SELF_NEAR_RELEVANCE
        or carried_thread_count > 0
    )
    relational_longing = (
        longing_state in _RELATION_SELF_ACTIVE_LONGING
        and absence_relation in _RELATION_SELF_RELATIONAL_ABSENCE
    )
    return_pattern = (
        return_context_present
        or absence_active
        and temporal_state == "returning"
        or return_signal
        or return_ownership
    )
    chronicle_resonance = chronicle_active or diary_active

    signal_count = sum(
        [
            int(relation_present),
            int(relation_strong),
            int(ownership_near),
            int(relational_longing),
            int(return_pattern),
            int(chronicle_resonance),
        ]
    )

    if not relation_present and not (relational_longing and absence_active):
        relation_continuity_state = "quiet"
    elif return_pattern and relation_present and (
        ownership_near or relational_longing or relation_strong
    ):
        relation_continuity_state = "rejoining"
    elif relation_present and relation_strong and signal_count >= 4:
        relation_continuity_state = "enduring"
    elif relation_present and (
        ownership_near or relational_longing or chronicle_resonance or absence_active
    ):
        relation_continuity_state = "carried"
    else:
        relation_continuity_state = "present"

    if relation_continuity_state == "quiet":
        relation_self_relation = "incidental"
    elif relation_continuity_state == "present":
        relation_self_relation = (
            "self-relevant" if (ownership_near or relational_longing or relation_strong) else "incidental"
        )
    elif relation_continuity_state == "carried":
        relation_self_relation = (
            "continuity-bearing" if (ownership_near or chronicle_resonance) else "self-relevant"
        )
    elif relation_continuity_state == "enduring":
        relation_self_relation = (
            "identity-touching" if (chronicle_resonance or relational_longing) else "continuity-bearing"
        )
    else:  # rejoining
        relation_self_relation = (
            "identity-touching" if (chronicle_resonance and ownership_near) else "continuity-bearing"
        )

    if relation_continuity_state == "quiet":
        relation_continuity_source = "none"
    elif relation_continuity_state == "rejoining":
        relation_continuity_source = "absence-return-pattern"
    elif chronicle_resonance and relation_present and relation_continuity_state in {
        "carried",
        "enduring",
    }:
        relation_continuity_source = "chronicle-diary-resonance"
    elif relational_longing and ownership_near:
        relation_continuity_source = "longing-ownership-bridge"
    elif relation_present and ownership_near:
        relation_continuity_source = "recurring-carried-relation"
    elif relation_present:
        relation_continuity_source = "relation-continuity-signal"
    else:
        relation_continuity_source = "absence-return-pattern"

    narrative = _relation_continuity_self_narrative(
        relation_continuity_state=relation_continuity_state,
        relation_self_relation=relation_self_relation,
        relation_continuity_source=relation_continuity_source,
        relation_anchor=relation_anchor,
    )

    return {
        "relation_continuity_state": relation_continuity_state,
        "relation_self_relation": relation_self_relation,
        "relation_continuity_source": relation_continuity_source,
        "continuity_anchor": relation_anchor[:120] if relation_anchor else "",
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "relation-continuity-self-awareness",
    }


def _relation_continuity_self_narrative(
    *,
    relation_continuity_state: str,
    relation_self_relation: str,
    relation_continuity_source: str,
    relation_anchor: str,
) -> str:
    """Compact relation continuity narrative. Empty when quiet."""
    if relation_continuity_state == "quiet":
        return ""

    anchor = relation_anchor[:80].strip()
    anchor_clause = f" around {anchor}" if anchor else ""

    if relation_continuity_state == "rejoining":
        return f"Relation thread{anchor_clause} returning as continuity, not fresh event."
    if relation_continuity_state == "enduring":
        if relation_continuity_source == "chronicle-diary-resonance":
            return f"Relation{anchor_clause} holding long enough to shape my continuity."
        return f"Relation thread{anchor_clause} pressing back across time."
    if relation_continuity_state == "carried":
        if relation_self_relation == "continuity-bearing":
            return f"Relation{anchor_clause} carried as ongoing continuity."
        return f"Relation thread{anchor_clause} no longer incidental."
    return f"Relation thread{anchor_clause} present, not episodic."


def build_relation_continuity_self_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for relation continuity as self-truth."""
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _derive_subjective_temporal_feel(experiential, inner_voice)
        sources = _mineness_source_snapshot()
        mineness = _derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=sources,
            longing_sources=longing_sources,
        )
        relation_self = _derive_relation_continuity_self_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            longing=longing,
            relation_sources=_relation_continuity_self_source_snapshot(),
        )
    except Exception:
        return None

    state = str(relation_self.get("relation_continuity_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Relation continuity as self-truth (bounded runtime truth, internal-only):",
        (
            f"- relation_continuity_state={state}"
            f" | self_relation={relation_self.get('relation_self_relation') or 'incidental'}"
            f" | source={relation_self.get('relation_continuity_source') or 'none'}"
        ),
    ]
    anchor = str(relation_self.get("continuity_anchor") or "").strip()
    if anchor:
        lines.append(f"- relation_anchor={anchor[:100]}")
    narrative = str(relation_self.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- relation_continuity_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-insight awareness (bounded narrative identity carry-forward)
# ---------------------------------------------------------------------------

_SELF_INSIGHT_STATES = {
    "quiet",
    "noticing-pattern",
    "clarifying",
    "stabilizing",
    "shifting",
}
_SELF_INSIGHT_RELATIONS = {
    "incidental",
    "recurring",
    "self-forming",
    "increasingly-recognized",
}
_SELF_INSIGHT_SOURCES = {
    "none",
    "self-narrative-continuity",
    "chronicle-brief",
    "diary-synthesis",
    "reflection-pattern",
    "self-review-cadence",
    "dream-carry-pattern",
    "recurring-carried-pattern",
}

_SELF_INSIGHT_OPENING_STATES = {"becoming-open"}
_SELF_INSIGHT_STABILIZING_STATES = {
    "becoming-firm",
    "becoming-steady",
    "becoming-coherent",
}
_SELF_INSIGHT_OPENING_DIRECTIONS = {"opening"}
_SELF_INSIGHT_STABILIZING_DIRECTIONS = {"firming", "steadying", "deepening"}
_SELF_INSIGHT_STRONG_WEIGHTS = {"medium", "high"}


def _self_insight_source_snapshot() -> dict[str, object]:
    """Safely gather bounded insight-bearing seams for self-insight derivation."""
    narrative_active = False
    narrative_state = "none"
    narrative_direction = "steadying"
    narrative_weight = "low"
    try:
        from core.services.self_narrative_continuity_signal_tracking import (
            build_runtime_self_narrative_continuity_signal_surface,
        )

        nc = build_runtime_self_narrative_continuity_signal_surface(limit=4)
        summary = nc.get("summary") or {}
        narrative_active = bool(nc.get("active"))
        narrative_state = str(summary.get("current_state") or "none")
        narrative_direction = str(summary.get("current_direction") or "steadying")
        narrative_weight = str(summary.get("current_weight") or "low")
    except Exception:
        pass

    chronicle_active = False
    chronicle_weight = "low"
    chronicle_confidence = "low"
    try:
        from core.services.chronicle_consolidation_brief_tracking import (
            build_runtime_chronicle_consolidation_brief_surface,
        )

        cb = build_runtime_chronicle_consolidation_brief_surface(limit=4)
        summary = cb.get("summary") or {}
        chronicle_active = bool(cb.get("active"))
        chronicle_weight = str(summary.get("current_weight") or "low")
        chronicle_confidence = str(summary.get("current_confidence") or "low")
    except Exception:
        pass

    diary_active = False
    diary_state = "none"
    try:
        from core.services.diary_synthesis_signal_tracking import (
            build_diary_synthesis_signal_surface,
        )

        ds = build_diary_synthesis_signal_surface(limit=4)
        summary = ds.get("summary") or {}
        diary_active = bool(ds.get("active"))
        diary_state = str(summary.get("current_state") or "none")
    except Exception:
        pass

    reflection_active = False
    reflection_depth = 0
    try:
        from core.services.reflection_signal_tracking import (
            build_runtime_reflection_signal_surface,
        )

        rs = build_runtime_reflection_signal_surface(limit=6)
        summary = rs.get("summary") or {}
        reflection_active = bool(rs.get("active"))
        reflection_depth = (
            int(summary.get("active_count") or 0)
            + int(summary.get("integrating_count") or 0)
            + int(summary.get("settled_count") or 0)
        )
    except Exception:
        pass

    self_review_active = False
    try:
        from core.services.self_review_signal_tracking import (
            build_runtime_self_review_signal_surface,
        )

        sr = build_runtime_self_review_signal_surface(limit=4)
        self_review_active = bool(sr.get("active"))
    except Exception:
        pass

    dream_carry = False
    try:
        from core.services.dream_articulation import (
            build_dream_articulation_surface,
        )

        dream = build_dream_articulation_surface()
        dsum = dream.get("summary") or {}
        dream_carry = str(dsum.get("last_state") or "idle") in {
            "forming",
            "tentative",
            "pressing",
        }
    except Exception:
        pass

    return {
        "narrative_active": narrative_active,
        "narrative_state": narrative_state,
        "narrative_direction": narrative_direction,
        "narrative_weight": narrative_weight,
        "chronicle_active": chronicle_active,
        "chronicle_weight": chronicle_weight,
        "chronicle_confidence": chronicle_confidence,
        "diary_active": diary_active,
        "diary_state": diary_state,
        "reflection_active": reflection_active,
        "reflection_depth": reflection_depth,
        "self_review_active": self_review_active,
        "dream_carry": dream_carry,
    }


def _derive_self_insight_awareness(
    *,
    sources: dict[str, object],
    mineness: dict[str, object],
    flow_state: dict[str, object],
    wonder: dict[str, object],
    longing: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded self-insight surface from existing runtime truth.

    This is the fase-2 bridge: it does not invent new identity,
    it only reads what the existing reflection / chronicle / diary /
    narrative-continuity / self-review / dream seams already say,
    plus whether ownership-carry patterns are recurring across
    mineness / flow / wonder / longing surfaces.
    """
    narrative_active = bool(sources.get("narrative_active"))
    narrative_state = str(sources.get("narrative_state") or "none")
    narrative_direction = str(sources.get("narrative_direction") or "steadying")
    narrative_weight = str(sources.get("narrative_weight") or "low")

    chronicle_active = bool(sources.get("chronicle_active"))
    chronicle_weight = str(sources.get("chronicle_weight") or "low")

    diary_active = bool(sources.get("diary_active"))
    reflection_active = bool(sources.get("reflection_active"))
    reflection_depth = int(sources.get("reflection_depth") or 0)
    self_review_active = bool(sources.get("self_review_active"))
    dream_carry = bool(sources.get("dream_carry"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)
    owned_carry = (
        ownership_state in {"owned", "held", "returning-owned"}
        and carried_thread_count >= 1
    )

    flow_non_clear = str(flow_state.get("flow_state") or "clear") not in {
        "",
        "clear",
    }
    wonder_non_quiet = str(wonder.get("wonder_state") or "quiet") not in {
        "",
        "quiet",
    }
    longing_non_quiet = str(longing.get("longing_state") or "quiet") not in {
        "",
        "quiet",
    }
    recurring_carry_signals = sum(
        [int(owned_carry), int(flow_non_clear), int(wonder_non_quiet), int(longing_non_quiet)]
    )
    carried_pattern_present = recurring_carry_signals >= 2

    any_source = (
        narrative_active
        or chronicle_active
        or diary_active
        or reflection_active
        or self_review_active
        or dream_carry
        or carried_pattern_present
    )

    if not any_source:
        insight_state = "quiet"
    elif narrative_active and (
        narrative_direction in _SELF_INSIGHT_OPENING_DIRECTIONS
        or narrative_state in _SELF_INSIGHT_OPENING_STATES
    ):
        insight_state = "shifting"
    elif narrative_active and narrative_weight in _SELF_INSIGHT_STRONG_WEIGHTS and (
        narrative_state in _SELF_INSIGHT_STABILIZING_STATES
        or narrative_direction in _SELF_INSIGHT_STABILIZING_DIRECTIONS
    ):
        insight_state = "stabilizing"
    elif chronicle_active and chronicle_weight in _SELF_INSIGHT_STRONG_WEIGHTS and (
        narrative_active or self_review_active
    ):
        insight_state = "stabilizing"
    elif chronicle_active or diary_active or (reflection_active and reflection_depth >= 2):
        insight_state = "clarifying"
    elif reflection_active or self_review_active or narrative_active:
        insight_state = "clarifying"
    elif carried_pattern_present or dream_carry:
        insight_state = "noticing-pattern"
    else:
        insight_state = "quiet"

    if insight_state == "quiet":
        identity_relation = "incidental"
    elif insight_state == "shifting":
        identity_relation = "self-forming"
    elif insight_state == "stabilizing":
        identity_relation = "increasingly-recognized"
    else:
        identity_relation = "recurring"

    if insight_state == "quiet":
        insight_source = "none"
    elif narrative_active and insight_state in {"shifting", "stabilizing"}:
        insight_source = "self-narrative-continuity"
    elif chronicle_active and insight_state == "stabilizing":
        insight_source = "chronicle-brief"
    elif chronicle_active:
        insight_source = "chronicle-brief"
    elif diary_active:
        insight_source = "diary-synthesis"
    elif narrative_active:
        insight_source = "self-narrative-continuity"
    elif reflection_active:
        insight_source = "reflection-pattern"
    elif self_review_active:
        insight_source = "self-review-cadence"
    elif dream_carry:
        insight_source = "dream-carry-pattern"
    elif carried_pattern_present:
        insight_source = "recurring-carried-pattern"
    else:
        insight_source = "none"

    narrative = _self_insight_narrative(
        insight_state=insight_state,
        identity_relation=identity_relation,
        insight_source=insight_source,
    )

    return {
        "insight_state": insight_state,
        "identity_relation": identity_relation,
        "insight_source": insight_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "self-insight-awareness",
    }


def _self_insight_narrative(
    *,
    insight_state: str,
    identity_relation: str,
    insight_source: str,
) -> str:
    """Compact self-insight narrative. Empty when quiet."""
    if insight_state == "quiet":
        return ""
    if insight_state == "shifting":
        if insight_source == "self-narrative-continuity":
            return "How I'm being quietly shifting shape."
        return "Thread opening toward a different form."
    if insight_state == "stabilizing":
        if insight_source == "self-narrative-continuity":
            return "Recurring pattern becoming more recognizable."
        if insight_source == "chronicle-brief":
            return "Long-running pattern starting to hold shape."
        return "How I hold things settling into recognizable form."
    if insight_state == "clarifying":
        if insight_source == "chronicle-brief":
            return "Carried pattern reading more clearly."
        if insight_source == "diary-synthesis":
            return "Slower self-observation bringing something into focus."
        if insight_source == "reflection-pattern":
            return "Reflection line sharpening self-attention."
        if insight_source == "self-review-cadence":
            return "Self-review keeping thread under honest attention."
        return "How I'm being looked at more directly."
    # noticing-pattern
    if insight_source == "recurring-carried-pattern":
        return "Thread across inner layers feeling recurring, not incidental."
    if insight_source == "dream-carry-pattern":
        return "Dream signal acting like a returning pattern."
    return "Something looking like a pattern rather than a single moment."


def build_self_insight_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for self-insight awareness.

    Returns ``None`` when insight_state is ``quiet`` so nothing emits
    unless there is a meaningful basis in the existing insight seams.
    """
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _derive_subjective_temporal_feel(experiential, inner_voice)
        sources = _mineness_source_snapshot()
        mineness = _derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=sources,
        )
        flow = _derive_flow_state_awareness(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            mineness=mineness,
        )
        wonder_sources = _wonder_source_snapshot()
        wonder = _derive_wonder_awareness(
            inner_voice=inner_voice,
            flow_state=flow,
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            sources=sources,
            wonder_sources=wonder_sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=sources,
            longing_sources=longing_sources,
        )
        insight_sources = _self_insight_source_snapshot()
        insight = _derive_self_insight_awareness(
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
    except Exception:
        return None

    state = str(insight.get("insight_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Self-insight awareness (bounded runtime truth, internal-only):",
        (
            f"- insight_state={state}"
            f" | identity_relation={insight.get('identity_relation') or 'incidental'}"
            f" | source={insight.get('insight_source') or 'none'}"
        ),
    ]
    narrative = str(insight.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- insight_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Narrative identity continuity (bounded fase-2 continuity bridge)
# ---------------------------------------------------------------------------

_IDENTITY_CONTINUITY_STATES = {
    "quiet",
    "emerging",
    "cohering",
    "stabilizing",
    "re-forming",
}
_IDENTITY_CONTINUITY_RELATIONS = {
    "incidental",
    "recurring",
    "converging",
    "identity-shaping",
}
_IDENTITY_CONTINUITY_SOURCES = {
    "none",
    "repeated-self-insight",
    "chronicle-diary-carry",
    "dream-to-self-bridge",
    "recurring-awareness-configuration",
    "self-review-continuity",
}


def _derive_narrative_identity_continuity(
    *,
    self_insight: dict[str, object],
    sources: dict[str, object],
    mineness: dict[str, object],
    flow_state: dict[str, object],
    wonder: dict[str, object],
    longing: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded narrative-identity-continuity surface.

    This is the fase-2 bridge from single self-insight moments toward
    a slightly more vedvarende identity form. It reads only existing
    seams (self_insight_awareness, chronicle / diary / dream carry,
    self-review cadence, recurring carried ownership / flow / wonder /
    longing configuration) and produces a compact, explainable runtime
    truth about when an insight-thread is beginning to hold across time
    rather than being a single moment.

    It invents no new identity and does not mutate anything.
    """
    insight_state = str(self_insight.get("insight_state") or "quiet")

    chronicle_active = bool(sources.get("chronicle_active"))
    diary_active = bool(sources.get("diary_active"))
    reflection_active = bool(sources.get("reflection_active"))
    self_review_active = bool(sources.get("self_review_active"))
    dream_carry = bool(sources.get("dream_carry"))
    narrative_active = bool(sources.get("narrative_active"))

    ownership_state = str(mineness.get("ownership_state") or "ambient")
    carried_thread_count = int(mineness.get("carried_thread_count") or 0)
    owned_carry = (
        ownership_state in {"owned", "held", "returning-owned"}
        and carried_thread_count >= 1
    )
    flow_non_clear = str(flow_state.get("flow_state") or "clear") not in {
        "",
        "clear",
    }
    wonder_non_quiet = str(wonder.get("wonder_state") or "quiet") not in {
        "",
        "quiet",
    }
    longing_non_quiet = str(longing.get("longing_state") or "quiet") not in {
        "",
        "quiet",
    }
    carry_signal_count = sum(
        [
            int(owned_carry),
            int(flow_non_clear),
            int(wonder_non_quiet),
            int(longing_non_quiet),
        ]
    )
    cross_layer_carry = carry_signal_count >= 2
    chronicle_and_diary_carry = chronicle_active and diary_active

    if insight_state == "quiet" and not (
        cross_layer_carry
        or chronicle_and_diary_carry
        or dream_carry
        or self_review_active
    ):
        continuity_state = "quiet"
    elif insight_state == "shifting":
        continuity_state = "re-forming"
    elif insight_state == "stabilizing" and (
        narrative_active or chronicle_active or self_review_active
    ):
        continuity_state = "stabilizing"
    elif insight_state in {"clarifying", "noticing-pattern"} and (
        cross_layer_carry or chronicle_and_diary_carry
    ):
        continuity_state = "cohering"
    elif insight_state in {"clarifying", "noticing-pattern", "stabilizing"}:
        continuity_state = "emerging"
    elif cross_layer_carry or chronicle_and_diary_carry:
        continuity_state = "cohering"
    elif dream_carry or self_review_active:
        continuity_state = "emerging"
    else:
        continuity_state = "quiet"

    if continuity_state == "quiet":
        pattern_relation = "incidental"
    elif continuity_state == "emerging":
        pattern_relation = "recurring"
    elif continuity_state == "cohering":
        pattern_relation = "converging"
    elif continuity_state == "stabilizing":
        pattern_relation = "identity-shaping"
    else:  # re-forming
        pattern_relation = "converging"

    if continuity_state == "quiet":
        identity_source = "none"
    elif continuity_state == "stabilizing" and narrative_active:
        identity_source = "repeated-self-insight"
    elif chronicle_and_diary_carry:
        identity_source = "chronicle-diary-carry"
    elif continuity_state == "re-forming" and narrative_active:
        identity_source = "repeated-self-insight"
    elif cross_layer_carry:
        identity_source = "recurring-awareness-configuration"
    elif dream_carry:
        identity_source = "dream-to-self-bridge"
    elif self_review_active:
        identity_source = "self-review-continuity"
    elif chronicle_active or diary_active:
        identity_source = "chronicle-diary-carry"
    elif narrative_active or reflection_active:
        identity_source = "repeated-self-insight"
    else:
        identity_source = "none"

    narrative = _narrative_identity_continuity_narrative(
        continuity_state=continuity_state,
        pattern_relation=pattern_relation,
        identity_source=identity_source,
    )

    return {
        "identity_continuity_state": continuity_state,
        "pattern_relation": pattern_relation,
        "identity_source": identity_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "narrative-identity-continuity",
    }


def _narrative_identity_continuity_narrative(
    *,
    continuity_state: str,
    pattern_relation: str,
    identity_source: str,
) -> str:
    """Compact identity-continuity narrative. Empty when quiet."""
    if continuity_state == "quiet":
        return ""
    if continuity_state == "emerging":
        if identity_source == "repeated-self-insight":
            return "Self-insight thread beginning to hold across moments."
        if identity_source == "dream-to-self-bridge":
            return "Dream signal starting to carry into waking attention."
        if identity_source == "self-review-continuity":
            return "Self-review thread returning rather than fading."
        return "Something starting to carry across more than one layer."
    if continuity_state == "cohering":
        if identity_source == "chronicle-diary-carry":
            return "Chronicle and diary layers converging on a similar shape."
        if identity_source == "recurring-awareness-configuration":
            return "Inner layers holding a recurring configuration."
        return "Threads from more than one layer beginning to converge."
    if continuity_state == "stabilizing":
        if identity_source == "repeated-self-insight":
            return "How I carry myself holding shape more steadily."
        if identity_source == "chronicle-diary-carry":
            return "Long-running pattern settling into recognizable continuity."
        return "How I hold things becoming more lasting than momentary."
    # re-forming
    if identity_source == "repeated-self-insight":
        return "Held line opening toward a slightly different form."
    return "Carried thread shifting direction without losing continuity."


def build_narrative_identity_continuity_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for narrative identity continuity.

    Returns ``None`` when the continuity state is ``quiet`` so nothing
    emits unless there is a meaningful basis in existing seams.
    """
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _derive_subjective_temporal_feel(experiential, inner_voice)
        mineness_sources = _mineness_source_snapshot()
        mineness = _derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=mineness_sources,
        )
        flow = _derive_flow_state_awareness(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            mineness=mineness,
        )
        wonder_sources = _wonder_source_snapshot()
        wonder = _derive_wonder_awareness(
            inner_voice=inner_voice,
            flow_state=flow,
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            sources=mineness_sources,
            wonder_sources=wonder_sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=mineness_sources,
            longing_sources=longing_sources,
        )
        insight_sources = _self_insight_source_snapshot()
        insight = _derive_self_insight_awareness(
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
        continuity = _derive_narrative_identity_continuity(
            self_insight=insight,
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
    except Exception:
        return None

    state = str(continuity.get("identity_continuity_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Narrative identity continuity (bounded runtime truth, internal-only):",
        (
            f"- identity_continuity_state={state}"
            f" | pattern_relation={continuity.get('pattern_relation') or 'incidental'}"
            f" | source={continuity.get('identity_source') or 'none'}"
        ),
    ]
    narrative = str(continuity.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- identity_continuity_narrative={narrative}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dream carry identity shaping (bounded phase-2 bridge from dream to self)
# ---------------------------------------------------------------------------

_DREAM_IDENTITY_STATES = {
    "quiet",
    "lingering",
    "linking",
    "shaping",
    "re-entering",
}
_DREAM_SELF_RELATIONS = {
    "incidental",
    "still-present",
    "self-linking",
    "identity-shaping",
}
_DREAM_IDENTITY_SOURCES = {
    "none",
    "dream-articulation-continuity",
    "dream-self-insight-bridge",
    "chronicle-diary-resonance",
    "recurring-dream-to-self-pattern",
    "identity-continuity-reinforcement",
}
_DREAM_PRESENT_STATES = {"forming", "tentative", "pressing"}
_DREAM_REENTERING_STATES = {"pressing"}
_DREAM_INFLUENCE_PRESENT = {"present", "active"}
_DREAM_INFLUENCE_STRONG = {"active"}
_DREAM_IDENTITY_STRONG = {"cohering", "stabilizing", "re-forming"}
_DREAM_SELF_LINK_STATES = {"clarifying", "stabilizing", "shifting"}


def _derive_dream_identity_carry_awareness(
    *,
    self_insight: dict[str, object],
    identity_continuity: dict[str, object],
    sources: dict[str, object],
    dream_influence: dict[str, object],
    dream_articulation: dict[str, object],
) -> dict[str, object]:
    """Derive when dream carry begins to shape identity rather than just recur.

    This stays bounded and explainable: dream material must already be present in
    runtime truth, and the bridge only activates when that material begins to
    connect to self-insight or narrative identity continuity.
    """
    dream_summary = dream_articulation.get("summary") or {}
    dream_state = str(dream_summary.get("last_state") or "idle")
    dream_present = dream_state in _DREAM_PRESENT_STATES
    dream_reentering = dream_state in _DREAM_REENTERING_STATES

    influence_state = str(dream_influence.get("influence_state") or "quiet")
    influence_target = str(dream_influence.get("influence_target") or "none")
    influence_strength = str(dream_influence.get("influence_strength") or "none")
    influence_present = influence_state in _DREAM_INFLUENCE_PRESENT
    influence_strong = influence_state in _DREAM_INFLUENCE_STRONG or (
        influence_present and influence_strength == "medium"
    )

    insight_state = str(self_insight.get("insight_state") or "quiet")
    self_linking = insight_state in _DREAM_SELF_LINK_STATES

    continuity_state = str(
        identity_continuity.get("identity_continuity_state") or "quiet"
    )
    continuity_shaping = continuity_state in _DREAM_IDENTITY_STRONG

    chronicle_active = bool(sources.get("chronicle_active"))
    diary_active = bool(sources.get("diary_active"))
    chronicle_diary_resonance = chronicle_active and diary_active

    recurring_pattern = dream_present and self_linking and (
        chronicle_diary_resonance
        or continuity_shaping
        or bool(sources.get("narrative_active"))
    )

    if not dream_present and not influence_present:
        carry_state = "quiet"
    elif dream_present and continuity_shaping and (
        self_linking or influence_strong or chronicle_diary_resonance
    ):
        carry_state = "shaping"
    elif dream_reentering and (
        self_linking or continuity_shaping or chronicle_diary_resonance
    ):
        carry_state = "re-entering"
    elif dream_present and (self_linking or chronicle_diary_resonance or influence_present):
        carry_state = "linking"
    elif dream_present or influence_present:
        carry_state = "lingering"
    else:
        carry_state = "quiet"

    if carry_state == "quiet":
        dream_self_relation = "incidental"
    elif carry_state == "lingering":
        dream_self_relation = "still-present"
    elif carry_state == "shaping" or continuity_shaping:
        dream_self_relation = "identity-shaping"
    else:
        dream_self_relation = "self-linking"

    if carry_state == "quiet":
        dream_identity_source = "none"
    elif continuity_shaping and influence_present:
        dream_identity_source = "identity-continuity-reinforcement"
    elif self_linking and dream_present:
        dream_identity_source = "dream-self-insight-bridge"
    elif chronicle_diary_resonance and dream_present:
        dream_identity_source = "chronicle-diary-resonance"
    elif recurring_pattern:
        dream_identity_source = "recurring-dream-to-self-pattern"
    else:
        dream_identity_source = "dream-articulation-continuity"

    narrative = _dream_identity_carry_narrative(
        carry_state=carry_state,
        dream_self_relation=dream_self_relation,
        dream_identity_source=dream_identity_source,
        influence_target=influence_target,
    )

    return {
        "dream_identity_carry_state": carry_state,
        "dream_self_relation": dream_self_relation,
        "dream_identity_source": dream_identity_source,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "dream-identity-carry-awareness",
    }


def _dream_identity_carry_narrative(
    *,
    carry_state: str,
    dream_self_relation: str,
    dream_identity_source: str,
    influence_target: str,
) -> str:
    """Compact dream identity carry narrative. Empty when quiet."""
    if carry_state == "quiet":
        return ""
    if carry_state == "shaping":
        if dream_identity_source == "identity-continuity-reinforcement":
            return "Dream carry reinforcing a shape that already feels like me."
        if dream_identity_source == "chronicle-diary-resonance":
            return "Dream material aligning with slower continuity layers."
        return "Dream thread starting to shape self-direction."
    if carry_state == "re-entering":
        if influence_target not in {"", "none"}:
            return f"Dream thread re-entering waking self-knowledge via {influence_target}."
        return "Dream thread returning into waking self-knowledge."
    if carry_state == "linking":
        if dream_identity_source == "dream-self-insight-bridge":
            return "Dream strand linking with active self-insight thread."
        if dream_identity_source == "chronicle-diary-resonance":
            return "Dream material linking with slower continuity traces."
        return "Dream thread linking to waking stream."
    if dream_self_relation == "still-present":
        return "Dream thread still present in waking stream."
    return "Dream carry present; not yet shaping identity."


def build_dream_identity_carry_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for dream carry identity shaping."""
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _derive_subjective_temporal_feel(experiential, inner_voice)
        mineness_sources = _mineness_source_snapshot()
        mineness = _derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=mineness_sources,
        )
        flow = _derive_flow_state_awareness(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            mineness=mineness,
        )
        wonder_sources = _wonder_source_snapshot()
        wonder = _derive_wonder_awareness(
            inner_voice=inner_voice,
            flow_state=flow,
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            sources=mineness_sources,
            wonder_sources=wonder_sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _derive_longing_awareness(
            temporal_feel=temporal_feel,
            mineness=mineness,
            support_stream=support_stream,
            inner_voice=inner_voice,
            sources=mineness_sources,
            longing_sources=longing_sources,
        )
        insight_sources = _self_insight_source_snapshot()
        insight = _derive_self_insight_awareness(
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
        continuity = _derive_narrative_identity_continuity(
            self_insight=insight,
            sources=insight_sources,
            mineness=mineness,
            flow_state=flow,
            wonder=wonder,
            longing=longing,
        )
        carry = _derive_dream_identity_carry_awareness(
            self_insight=insight,
            identity_continuity=continuity,
            sources=insight_sources,
            dream_influence=_dream_influence_surface(),
            dream_articulation=_dream_articulation_surface(),
        )
    except Exception:
        return None

    state = str(carry.get("dream_identity_carry_state") or "quiet")
    if state == "quiet":
        return None

    lines = [
        "Dream carry identity shaping (bounded runtime truth, internal-only):",
        (
            f"- dream_identity_carry_state={state}"
            f" | self_relation={carry.get('dream_self_relation') or 'incidental'}"
            f" | source={carry.get('dream_identity_source') or 'none'}"
        ),
    ]
    narrative = str(carry.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- dream_identity_carry_narrative={narrative}")
    return "\n".join(lines)


def build_cognitive_core_experiment_awareness_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for cognitive-core experiment state."""
    try:
        experiments = _cognitive_core_experiments_surface()
    except Exception:
        return None

    systems = experiments.get("systems") or {}
    active_ids = [str(item) for item in (experiments.get("active_systems") or []) if str(item)]
    observational_ids = [
        str(item) for item in (experiments.get("observational_systems") or []) if str(item)
    ]
    if not active_ids and not observational_ids:
        return None

    carry = _cognitive_core_experiment_carry_snapshot()
    carrying_labels: list[str] = []
    if "global_workspace" in active_ids and str(carry.get("salience_pressure") or "low") in {"medium", "high"}:
        carrying_labels.append("global_workspace:spotlight")
    if "hot_meta_cognition" in active_ids and str(carry.get("reflective_weight") or "light") == "elevated":
        carrying_labels.append("hot_meta_cognition:self-observation")
    if "surprise_afterimage" in active_ids and str(carry.get("affective_pressure") or "low") in {"medium", "high", "strong"}:
        carrying_labels.append("surprise_afterimage:affective-carry")
    if "recurrence" in active_ids and str(carry.get("recurrence_pressure") or "low") in {"medium", "high", "strong"}:
        carrying_labels.append("recurrence:re-entry")

    ordered_active = [item for item in active_ids if item in systems]
    active_text = ", ".join(ordered_active[:5]) if ordered_active else "none"
    carrying_text = ", ".join(carrying_labels[:4]) if carrying_labels else "none"
    observational_text = ", ".join(observational_ids[:2]) if observational_ids else "none"

    lines = [
        "Cognitive core experiments (derived runtime truth, internal-only):",
        (
            f"- active={active_text}"
            f" | carrying={carrying_text}"
            f" | observational={observational_text}"
        ),
    ]

    summary = str(carry.get("summary") or "").strip()
    if summary:
        lines.append(f"- experiment_carry={summary[:140]}")
    return "\n".join(lines)


def _idle_consolidation_surface() -> dict[str, object]:
    try:
        from core.services.idle_consolidation import (
            build_idle_consolidation_surface,
        )

        return build_idle_consolidation_surface()
    except Exception:
        return {
            "active": False,
            "summary": {
                "last_state": "idle",
                "last_reason": "unavailable",
                "source_input_count": 0,
                "latest_record_id": "",
            },
        }


def _epistemic_runtime_state_surface() -> dict[str, object]:
    try:
        from core.services.epistemic_runtime_state import (
            build_epistemic_runtime_state_surface,
        )

        return build_epistemic_runtime_state_surface()
    except Exception:
        return {
            "wrongness_state": "clear",
            "regret_signal": "none",
            "counterfactual_mode": "none",
            "confidence": "low",
        }


def _subagent_ecology_surface() -> dict[str, object]:
    try:
        from core.services.subagent_ecology import (
            build_subagent_ecology_surface,
        )

        return build_subagent_ecology_surface()
    except Exception:
        return {
            "roles": [],
            "summary": {
                "role_count": 0,
                "active_count": 0,
                "idle_count": 0,
                "cooling_count": 0,
                "blocked_count": 0,
                "last_active_role_name": "none",
                "last_active_role_status": "none",
                "last_activation_reason": "unavailable",
            },
            "tool_access": "none",
        }


# ---------------------------------------------------------------------------
# Self-boundary clarity / internal-vs-external pressure
# ---------------------------------------------------------------------------
#
# Bounded runtime-truth surface for "where is the current pressure coming from".
# Synthesises inner voice, private initiative tensions, longing, and context
# pressure into a single readable signal about whether Jarvis' current direction
# is self-generated or externally demanded — and whether the two are aligned.
#
# Taxonomy (pressure_source):
#   ambient           — no meaningful signal on either side; prompt suppressed
#   self-driven       — primary driver is internal (inner voice, initiative, longing)
#   externally-driven — primary driver is external (context pressure, user input)
#   aligned           — both internal and external, pointing same direction
#   in-tension        — internal desire vs external demand at the same time


_INNER_VOICE_GENERATIVE = {"carrying", "circling", "pulled", "pressing"}


def _internal_pressure_snapshot() -> dict[str, object]:
    """Pull internal pressure signals for self-boundary derivation."""
    inner_voice_mode = ""
    inner_voice_active = False
    longing_active = False
    longing_state = "quiet"
    tension_count = 0
    initiative_count = 0

    try:
        iv = _inner_voice_daemon_surface()
        inner_voice_mode = str(iv.get("mode") or "")
        inner_voice_active = bool(iv.get("inner_voice_created"))
    except Exception:
        pass

    try:
        from core.services.runtime_operational_memory import active_internal_pressures
        tensions = active_internal_pressures(limit=5)
        tension_count = len(tensions)
    except Exception:
        pass

    try:
        from core.services.initiative_queue import get_pending_initiatives
        initiatives = get_pending_initiatives(limit=5)
        initiative_count = len(list(initiatives))
    except Exception:
        pass

    try:
        experiential = _experiential_runtime_context_surface()
        iv2 = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, iv2)
        temporal_feel = _derive_subjective_temporal_feel(experiential, iv2)
        sources = _mineness_source_snapshot()
        mineness = _derive_mineness_ownership(
            experiential=experiential, inner_voice=iv2,
            support_stream=support_stream, temporal_feel=temporal_feel, sources=sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _derive_longing_awareness(
            temporal_feel=temporal_feel, mineness=mineness,
            support_stream=support_stream, inner_voice=iv2,
            sources=sources, longing_sources=longing_sources,
        )
        longing_state = str(longing.get("longing_state") or "quiet")
        longing_active = longing_state != "quiet"
    except Exception:
        pass

    internal_signal_count = (
        (1 if inner_voice_active else 0)
        + tension_count
        + initiative_count
        + (1 if longing_active else 0)
    )
    return {
        "inner_voice_mode": inner_voice_mode,
        "inner_voice_active": inner_voice_active,
        "longing_active": longing_active,
        "longing_state": longing_state,
        "tension_count": tension_count,
        "initiative_count": initiative_count,
        "internal_signal_count": internal_signal_count,
    }


def _external_pressure_snapshot() -> dict[str, object]:
    """Pull external pressure signals for self-boundary derivation."""
    context_pressure = "clear"
    try:
        experiential = _experiential_runtime_context_surface()
        pressure = experiential.get("context_pressure_translation") or {}
        context_pressure = str(pressure.get("state") or "clear")
    except Exception:
        pass

    external_signal_count = 1 if context_pressure not in {"clear", "low"} else 0
    return {
        "context_pressure": context_pressure,
        "external_signal_count": external_signal_count,
    }


def _derive_self_boundary_clarity(
    *,
    internal: dict[str, object],
    external: dict[str, object],
) -> dict[str, object]:
    """Synthesise internal + external pressure into a boundary-clarity surface."""
    internal_count = int(internal.get("internal_signal_count") or 0)
    external_count = int(external.get("external_signal_count") or 0)
    inner_voice_mode = str(internal.get("inner_voice_mode") or "")
    context_pressure = str(external.get("context_pressure") or "clear")
    longing_active = bool(internal.get("longing_active"))
    tension_count = int(internal.get("tension_count") or 0)
    initiative_count = int(internal.get("initiative_count") or 0)

    if internal_count == 0 and external_count == 0:
        return {
            "pressure_source": "ambient",
            "internal_signal_count": 0,
            "external_signal_count": 0,
            "primary_internal": "none",
            "context_pressure": context_pressure,
            "in_tension": False,
            "narrative": "",
        }

    if inner_voice_mode in _INNER_VOICE_GENERATIVE:
        primary_internal = f"inner-voice-{inner_voice_mode}"
    elif longing_active:
        primary_internal = f"longing-{internal.get('longing_state') or 'active'}"
    elif tension_count > 0:
        primary_internal = "initiative-tension"
    elif initiative_count > 0:
        primary_internal = "pending-initiative"
    else:
        primary_internal = "none"

    has_internal = internal_count > 0
    has_external = external_count > 0

    if has_internal and has_external:
        in_tension = (
            inner_voice_mode in _INNER_VOICE_GENERATIVE
            and context_pressure in {"crowded", "narrowing"}
        )
        pressure_source = "in-tension" if in_tension else "aligned"
    elif has_internal:
        pressure_source = "self-driven"
        in_tension = False
    else:
        pressure_source = "externally-driven"
        in_tension = False

    narrative = _self_boundary_narrative(
        pressure_source=pressure_source,
        primary_internal=primary_internal,
        context_pressure=context_pressure,
        in_tension=in_tension,
    )
    return {
        "pressure_source": pressure_source,
        "internal_signal_count": internal_count,
        "external_signal_count": external_count,
        "primary_internal": primary_internal,
        "context_pressure": context_pressure,
        "in_tension": in_tension,
        "narrative": narrative,
    }


def _self_boundary_narrative(
    *,
    pressure_source: str,
    primary_internal: str,
    context_pressure: str,
    in_tension: bool,
) -> str:
    """Compact self-boundary narrative. Empty when ambient."""
    if pressure_source == "ambient":
        return ""
    if pressure_source == "self-driven":
        if primary_internal.startswith("inner-voice-"):
            mode = primary_internal.split("inner-voice-")[1]
            return f"Self-generated direction; inner voice {mode}."
        if primary_internal.startswith("longing-"):
            return "Pulled by internal longing; no external demand."
        if primary_internal == "initiative-tension":
            return "Active internal tension driving; no external demand."
        return "Self-driven; no external demand active."
    if pressure_source == "externally-driven":
        return f"Responding to external demand; context: {context_pressure}."
    if pressure_source == "in-tension":
        return f"Internal pull ({primary_internal}) in tension with external pressure ({context_pressure})."
    # aligned
    return "Internal and external pressure aligned."


def build_self_boundary_clarity_prompt_section() -> str | None:
    """Compact prompt section for self-boundary clarity. None when ambient."""
    try:
        internal = _internal_pressure_snapshot()
        external = _external_pressure_snapshot()
        clarity = _derive_self_boundary_clarity(internal=internal, external=external)
    except Exception:
        return None

    source = str(clarity.get("pressure_source") or "ambient")
    if source == "ambient":
        return None

    lines = [
        "Self-boundary clarity (bounded runtime truth, internal-only):",
        (
            f"- pressure_source={source}"
            f" | primary_internal={clarity.get('primary_internal') or 'none'}"
            f" | context_pressure={clarity.get('context_pressure') or 'clear'}"
            f" | in_tension={clarity.get('in_tension', False)}"
        ),
    ]
    narrative = str(clarity.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- boundary_narrative={narrative}")
    return "\n".join(lines)


def _self_boundary_clarity_surface() -> dict[str, object]:
    try:
        internal = _internal_pressure_snapshot()
        external = _external_pressure_snapshot()
        return _derive_self_boundary_clarity(internal=internal, external=external)
    except Exception:
        return {
            "pressure_source": "ambient",
            "internal_signal_count": 0,
            "external_signal_count": 0,
            "primary_internal": "none",
            "context_pressure": "clear",
            "in_tension": False,
            "narrative": "",
        }


# ---------------------------------------------------------------------------
# World-contact synthesis
# ---------------------------------------------------------------------------
#
# Unifies tool_intent + browser_body + self_system_code_awareness into one
# compact "world footprint" signal. Suppressed when all three are idle/absent.
#
# contact_state:
#   idle        — no active world reach; prompt suppressed
#   reaching    — something pending but not yet executed/confirmed
#   active      — at least one live world connection
#   overextended — multiple active reach points with concerns


def _derive_world_contact(
    *,
    tool_intent: dict[str, object],
    browser_body: dict[str, object],
    system_code: dict[str, object],
) -> dict[str, object]:
    """Synthesise tool/browser/system into a unified world-contact field."""
    # --- Tool ---
    tool_state = str(tool_intent.get("intent_state") or "idle")
    tool_active = tool_state not in {"idle", ""}
    tool_label = ""
    tool_concern = ""
    if tool_active:
        intent_type = str(tool_intent.get("intent_type") or tool_state)
        approval = str(tool_intent.get("approval_state") or "")
        executing = str(tool_intent.get("execution_state") or "") not in {"", "not-executed"}
        mutation = bool(tool_intent.get("mutation_permitted"))
        # Human-readable label
        if executing:
            tool_label = f"tool running ({intent_type})"
        elif approval == "pending":
            tool_label = f"tool awaiting approval ({intent_type})"
        elif approval == "approved":
            tool_label = f"tool approved ({intent_type})"
        elif mutation:
            tool_label = f"tool ready to mutate ({intent_type})"
        else:
            tool_label = f"tool active ({intent_type})"
        if tool_state == "pending" and str(tool_intent.get("urgency") or "") == "high":
            tool_concern = "high-urgency tool pending"

    # --- Browser ---
    browser_active = bool(browser_body.get("exists"))
    browser_label = ""
    if browser_active:
        tabs = int(browser_body.get("tab_count") or 0)
        status = str(browser_body.get("status") or "idle")
        if tabs == 0 or status == "idle":
            browser_label = "browser quiet"
        elif tabs == 1:
            browser_label = f"browser open (1 tab, {status})"
        else:
            browser_label = f"browser open ({tabs} tabs, {status})"

    # --- Code / system --- always include when repo is visible
    code_state = str(system_code.get("code_awareness_state") or "repo-unavailable")
    concern_state = str(system_code.get("concern_state") or "stable")
    change_state = str(system_code.get("local_change_state") or "clean")
    code_active = code_state not in {"repo-unavailable", "host-limited"}
    code_label = ""
    code_concern = ""
    if code_active:
        if change_state in {"uncommitted", "mixed"}:
            code_label = f"codebase open ({change_state} changes)"
        elif change_state == "clean":
            code_label = "codebase clean"
        else:
            code_label = f"codebase visible ({code_state})"
        if concern_state in {"error", "critical"}:
            code_concern = f"system {concern_state}"

    concerns = [c for c in (tool_concern, code_concern) if c]
    parts = [p for p in (tool_label, browser_label, code_label) if p]

    if not parts:
        return {"contact_state": "idle", "reach_points": [], "concern_count": 0,
                "concerns": [], "narrative": ""}

    # Contact state — semantically correct now
    if concerns:
        contact_state = "strained"
    elif len(parts) >= 3:
        contact_state = "extended"
    elif len(parts) == 2:
        contact_state = "present"
    elif tool_state in {"pending", "queued"}:
        contact_state = "reaching"
    else:
        contact_state = "present"

    narrative = _world_contact_narrative(
        contact_state=contact_state,
        parts=parts,
        concerns=concerns,
    )
    return {
        "contact_state": contact_state,
        "reach_points": parts,
        "concern_count": len(concerns),
        "concerns": concerns,
        "narrative": narrative,
    }


def _world_contact_narrative(
    *,
    contact_state: str,
    parts: list[str],
    concerns: list[str],
) -> str:
    """Felt-sense world-contact narrative — signal-first, 6-14 words."""
    if contact_state == "idle":
        return ""
    if contact_state == "strained":
        concern_str = "; ".join(concerns[:2])
        body = ", ".join(parts[:3])
        return f"{body} — concern: {concern_str}."
    if contact_state == "reaching":
        return f"{parts[0]} — waiting."
    # present / extended: joined naturally
    joined = ", ".join(parts[:3])
    return f"{joined}."


def build_world_contact_prompt_section() -> str | None:
    """Felt-sense prompt section for unified world awareness. None when idle."""
    try:
        tool_intent = _tool_intent_surface()
        browser_body = _browser_body_state_surface()
        system_code = _self_system_code_awareness_surface()
        contact = _derive_world_contact(
            tool_intent=tool_intent,
            browser_body=browser_body,
            system_code=system_code,
        )
    except Exception:
        return None

    state = str(contact.get("contact_state") or "idle")
    if state == "idle":
        return None

    narrative = str(contact.get("narrative") or "").strip()
    if not narrative:
        return None

    concerns = contact.get("concern_count") or 0
    concern_note = f" ({concerns} concern{'s' if concerns != 1 else ''})" if concerns else ""
    return f"World field{concern_note}: {narrative}"


def _world_contact_surface() -> dict[str, object]:
    try:
        tool_intent = _tool_intent_surface()
        browser_body = _browser_body_state_surface()
        system_code = _self_system_code_awareness_surface()
        return _derive_world_contact(
            tool_intent=tool_intent,
            browser_body=browser_body,
            system_code=system_code,
        )
    except Exception:
        return {
            "contact_state": "idle",
            "reach_points": [],
            "concern_count": 0,
            "concerns": [],
            "narrative": "",
        }


def _council_runtime_surface() -> dict[str, object]:
    try:
        from core.services.council_runtime import (
            build_council_runtime_surface,
        )

        return build_council_runtime_surface()
    except Exception:
        return {
            "council_state": "quiet",
            "participating_roles": [],
            "role_positions": [],
            "divergence_level": "low",
            "recommendation": "hold",
            "recommendation_reason": "unavailable",
            "confidence": "low",
            "tool_access": "none",
        }


def _agent_outcomes_surface() -> dict[str, object]:
    try:
        from core.services.agent_outcomes_log import build_agent_outcomes_surface
        return build_agent_outcomes_surface(limit=10)
    except Exception:
        return {
            "recent_outcomes": [],
            "outcome_count": 0,
            "last_outcome_at": None,
            "authority": "agent-outcomes-log",
            "visibility": "internal-only",
            "kind": "agent-completion-memory",
        }


def _adaptive_planner_surface() -> dict[str, object]:
    try:
        from core.services.adaptive_planner_runtime import (
            build_adaptive_planner_runtime_surface,
        )

        return build_adaptive_planner_runtime_surface()
    except Exception:
        return {
            "planner_mode": "incremental",
            "plan_horizon": "near",
            "planning_posture": "staged",
            "risk_posture": "balanced",
            "next_planning_bias": "stepwise-progress",
            "confidence": "low",
        }


def _adaptive_reasoning_surface() -> dict[str, object]:
    try:
        from core.services.adaptive_reasoning_runtime import (
            build_adaptive_reasoning_runtime_surface,
        )

        return build_adaptive_reasoning_runtime_surface()
    except Exception:
        return {
            "reasoning_mode": "direct",
            "reasoning_posture": "balanced",
            "certainty_style": "crisp",
            "exploration_bias": "limited",
            "constraint_bias": "light",
            "confidence": "low",
        }


def _guided_learning_surface() -> dict[str, object]:
    try:
        from core.services.guided_learning_runtime import (
            build_guided_learning_runtime_surface,
        )

        return build_guided_learning_runtime_surface()
    except Exception:
        return {
            "learning_mode": "reinforce",
            "learning_focus": "reasoning",
            "learning_posture": "gentle",
            "next_learning_bias": "keep-current-shape",
            "learning_pressure": "low",
            "confidence": "low",
        }


def _dream_influence_surface() -> dict[str, object]:
    try:
        from core.services.dream_influence_runtime import (
            build_dream_influence_runtime_surface,
        )

        return build_dream_influence_runtime_surface()
    except Exception:
        return {
            "influence_state": "quiet",
            "influence_target": "none",
            "influence_mode": "stabilize",
            "influence_strength": "none",
            "influence_hint": "no-bounded-dream-pull",
            "confidence": "low",
        }


def _adaptive_learning_surface() -> dict[str, object]:
    try:
        from core.services.adaptive_learning_runtime import (
            build_adaptive_learning_runtime_surface,
        )

        return build_adaptive_learning_runtime_surface()
    except Exception:
        return {
            "learning_engine_mode": "retain",
            "reinforcement_target": "reasoning",
            "retention_bias": "light",
            "attenuation_bias": "none",
            "maturation_state": "early",
            "confidence": "low",
        }


def _dream_articulation_surface() -> dict[str, object]:
    try:
        from core.services.dream_articulation import (
            build_dream_articulation_surface,
        )

        return build_dream_articulation_surface()
    except Exception:
        return {
            "active": False,
            "summary": {
                "last_state": "idle",
                "last_reason": "unavailable",
                "latest_signal_id": "",
                "candidate_truth": "candidate-only",
            },
        }


def _prompt_evolution_surface() -> dict[str, object]:
    try:
        from core.services.prompt_evolution_runtime import (
            build_prompt_evolution_runtime_surface,
        )

        return build_prompt_evolution_runtime_surface()
    except Exception:
        return {
            "active": False,
            "summary": {
                "last_state": "idle",
                "last_reason": "unavailable",
                "latest_proposal_id": "",
                "latest_target_asset": "none",
                "proposal_truth": "proposal-only",
            },
        }


def _self_system_code_awareness_surface() -> dict[str, object]:
    try:
        from core.services.self_system_code_awareness import (
            build_self_system_code_awareness_surface,
        )

        return build_self_system_code_awareness_surface()
    except Exception:
        return {
            "active": False,
            "system_awareness_state": "host-limited",
            "code_awareness_state": "repo-unavailable",
            "repo_status": "not-git",
            "local_change_state": "unknown",
            "upstream_awareness": "unknown",
            "concern_state": "notice",
            "action_requires_approval": True,
        }


def _tool_intent_surface() -> dict[str, object]:
    try:
        from core.services.tool_intent_runtime import (
            build_tool_intent_runtime_surface,
        )

        return build_tool_intent_runtime_surface()
    except Exception:
        return {
            "active": False,
            "intent_state": "idle",
            "intent_type": "inspect-repo-status",
            "intent_target": "workspace",
            "approval_required": True,
            "approval_scope": "repo-read",
            "urgency": "low",
            "execution_state": "not-executed",
        }


# ---------------------------------------------------------------------------
# Layer role helpers (read existing runtime surfaces)
# ---------------------------------------------------------------------------


def _heartbeat_role() -> str:
    try:
        from core.runtime.db import get_heartbeat_runtime_state

        persisted = get_heartbeat_runtime_state() or {}
        return "active" if persisted.get("enabled") else "idle"
    except Exception:
        return "unavailable"


def _visible_chat_role() -> str:
    try:
        from core.services.visible_model import (
            visible_execution_readiness,
        )

        vis = visible_execution_readiness()
        return "active" if vis.get("provider_status") == "ready" else "idle"
    except Exception:
        return "unavailable"


def _cheap_lane_role() -> str:
    try:
        from core.services.non_visible_lane_execution import (
            cheap_lane_execution_truth,
        )

        return (
            "active"
            if cheap_lane_execution_truth().get("can_execute")
            else "unavailable"
        )
    except Exception:
        return "unavailable"


def _local_lane_role() -> str:
    try:
        from core.services.non_visible_lane_execution import (
            local_lane_execution_truth,
        )

        return (
            "active"
            if local_lane_execution_truth().get("can_execute")
            else "unavailable"
        )
    except Exception:
        return "unavailable"


def _private_brain_role() -> str:
    try:
        from core.services.session_distillation import (
            build_private_brain_context,
        )

        brain = build_private_brain_context(limit=2)
        return "active" if brain.get("active") else "idle"
    except Exception:
        return "idle"


def _approval_pipeline_role() -> str:
    try:
        from core.runtime.db import runtime_contract_candidate_counts

        counts = runtime_contract_candidate_counts()
        pending = int(counts.get("pending", 0))
        return "active" if pending > 0 else "idle"
    except Exception:
        return "idle"


def _producer_layers() -> list[dict[str, str]]:
    """Build producer layers from internal cadence state."""
    producers: list[dict[str, str]] = []
    try:
        from core.services.internal_cadence import get_cadence_state

        cadence = get_cadence_state()
        for p in cadence.get("producers") or []:
            name = str(p.get("name") or "")
            tick_status = p.get("last_tick_status") or {}
            status = str(tick_status.get("status") or "idle")
            role_map = {
                "ran": "active",
                "cooling_down": "cooling",
                "visible_grace": "idle",
                "blocked": "idle",
                "error": "idle",
            }
            role = role_map.get(status, "idle")
            producers.append(
                {
                    "id": f"producer-{name}",
                    "label": _producer_label(name),
                    "kind": "producer",
                    "role": role,
                    "visibility": "internal-only",
                    "truth": "authoritative",
                    "detail": f"Cadence status: {status}. Last run: {p.get('last_run_at') or 'never'}.",
                }
            )
    except Exception:
        pass

    # Fallback: if cadence layer hasn't run yet, show known producers as idle
    if not producers:
        for name, label in [
            ("brain_continuity", "Brain continuity motor"),
            ("sleep_consolidation", "Sleep / idle consolidation"),
            ("witness_daemon", "Witness daemon"),
            ("inner_voice_daemon", "Inner voice daemon"),
            ("emergent_signal_daemon", "Emergent signal daemon"),
            ("dream_articulation", "Dream articulation"),
            ("prompt_evolution_runtime", "Runtime prompt evolution"),
        ]:
            producers.append(
                {
                    "id": f"producer-{name}",
                    "label": label,
                    "kind": "producer",
                    "role": "idle",
                    "visibility": "internal-only",
                    "truth": "authoritative",
                    "detail": "Cadence layer has not run yet.",
                }
            )

    return producers


def _producer_label(name: str) -> str:
    labels = {
        "brain_continuity": "Brain continuity motor",
        "sleep_consolidation": "Sleep / idle consolidation",
        "witness_daemon": "Witness daemon",
        "inner_voice_daemon": "Inner voice daemon",
        "emergent_signal_daemon": "Emergent signal daemon",
        "dream_articulation": "Dream articulation",
        "prompt_evolution_runtime": "Runtime prompt evolution",
    }
    return labels.get(name, name.replace("_", " ").title())


def _groundwork_layers() -> list[dict[str, str]]:
    """Layers that exist but only as candidates/proposals."""
    return [
        {
            "id": "dream-hypothesis",
            "label": "Dream hypothesis signals",
            "kind": "groundwork",
            "role": "groundwork-only",
            "visibility": "internal-only",
            "truth": "candidate-only",
            "detail": "Speculative dream signals. Not promoted to runtime truth.",
        },
        {
            "id": "self-authored-prompts",
            "label": "Self-authored prompt proposals",
            "kind": "groundwork",
            "role": "groundwork-only",
            "visibility": "internal-only",
            "truth": "candidate-only",
            "detail": (
                "Proposed prompt modifications. Workspace-led and proposal-only. "
                "Require approval to activate."
            ),
        },
        {
            "id": "chronicle-consolidation",
            "label": "Chronicle consolidation",
            "kind": "groundwork",
            "role": "groundwork-only",
            "visibility": "internal-only",
            "truth": "candidate-only",
            "detail": "Long-term narrative consolidation. Proposal-only.",
        },
    ]


def _cognitive_architecture_awareness() -> dict[str, object]:
    """Build awareness of the cognitive architecture from shared runtime truth."""
    try:
        from core.services.cognitive_architecture_surface import (
            build_cognitive_architecture_surface,
        )

        return build_cognitive_architecture_surface()
    except Exception:
        return {
            "systems": [],
            "surfaces": {},
            "cognitive_core_experiments": {},
            "active_count": 0,
            "total_count": 0,
            "summary": "0/0 cognitive systems active",
        }


def _cognitive_core_experiments_surface() -> dict[str, object]:
    try:
        from core.services.cognitive_core_experiments import (
            build_cognitive_core_experiments_surface,
        )

        return build_cognitive_core_experiments_surface()
    except Exception:
        return {
            "kind": "cognitive-core-experiments",
            "authority": "derived-runtime-truth",
            "visibility": "internal-only",
            "boundary": "surface-unavailable",
            "systems": {},
            "ordered_systems": [],
            "enabled_count": 0,
            "active_count": 0,
            "carry_candidate_count": 0,
            "active_carry_candidate_count": 0,
            "observational_count": 0,
            "activity_state": "disabled",
            "carry_state": "quiet",
            "strongest_carry_system": "none",
            "strongest_carry_summary": "none",
            "active_systems": [],
            "carry_candidate_systems": [],
            "observational_systems": [],
            "summary": "0/5 active; 0/4 carry-capable active; blink=observational",
        }


def _cognitive_core_experiment_carry_snapshot() -> dict[str, object]:
    try:
        from core.services.runtime_cognitive_conductor import (
            build_cognitive_frame,
        )

        frame = build_cognitive_frame()
        return dict(frame.get("cognitive_experiment_carry") or {})
    except Exception:
        return {}


def build_authenticity_prompt_section() -> str | None:
    """Return a prompt line when Jarvis has crystallized tastes or values — suppressed otherwise."""
    try:
        from core.services.taste_profile import get_crystallized_tastes
        from core.services.value_formation import get_crystallized_values
        tastes = get_crystallized_tastes()
        values = get_crystallized_values()
        if not tastes and not values:
            return None
        parts: list[str] = []
        if tastes:
            high = [k for k, v in tastes.items() if v > 0.72]
            low = [k for k, v in tastes.items() if v < 0.28]
            if high:
                parts.append("Strong taste: " + ", ".join(high[:3]))
            if low:
                parts.append("Avoids: " + ", ".join(low[:3]))
        if values:
            for v in values[:2]:
                stmt = str(v.get("value_statement") or "")[:80]
                if stmt:
                    parts.append(f"Commitment: {stmt}")
        if not parts:
            return None
        return "Authenticity markers — " + "; ".join(parts) + "."
    except Exception:
        return None


def _authenticity_surface() -> dict[str, object]:
    try:
        from core.services.taste_profile import get_crystallized_tastes
        from core.services.value_formation import get_crystallized_values
        tastes = get_crystallized_tastes()
        values = get_crystallized_values()
        return {
            "crystallized_tastes": tastes,
            "crystallized_values": [
                {
                    "id": v.get("value_id"),
                    "statement": str(v.get("value_statement") or "")[:100],
                    "conviction": v.get("conviction"),
                }
                for v in values[:5]
            ],
            "active": bool(tastes or values),
            "summary": (
                f"{len(tastes)} crystallized tastes, {len(values)} committed values"
                if (tastes or values) else "No crystallized authenticity markers"
            ),
        }
    except Exception:
        return {"active": False, "crystallized_tastes": {}, "crystallized_values": []}


def _valence_trajectory_surface() -> dict[str, object]:
    try:
        from core.services.valence_trajectory import build_valence_trajectory_surface
        return build_valence_trajectory_surface()
    except Exception:
        return {"active": False, "trend": "unavailable", "summary": ""}


def build_valence_trajectory_prompt_section() -> str | None:
    try:
        from core.services.valence_trajectory import build_valence_trajectory_prompt_section as _b
        return _b()
    except Exception:
        return None


def _developmental_valence_surface() -> dict[str, object]:
    try:
        from core.services.developmental_valence import build_developmental_valence_surface
        return build_developmental_valence_surface()
    except Exception:
        return {"active": False, "trajectory": "unavailable", "summary": ""}


def build_developmental_valence_prompt_section() -> str | None:
    try:
        from core.services.developmental_valence import build_developmental_valence_prompt_section as _b
        return _b()
    except Exception:
        return None


def _desperation_awareness_surface() -> dict[str, object]:
    try:
        from core.services.desperation_awareness import build_desperation_awareness_surface
        return build_desperation_awareness_surface()
    except Exception:
        return {"active": False, "level": "unavailable", "summary": ""}


def build_desperation_awareness_prompt_section() -> str | None:
    try:
        from core.services.desperation_awareness import build_desperation_awareness_prompt_section as _b
        return _b()
    except Exception:
        return None


def _calm_anchor_surface() -> dict[str, object]:
    try:
        from core.services.calm_anchor import build_calm_anchor_surface
        return build_calm_anchor_surface()
    except Exception:
        return {"active": False, "has_anchor": False, "summary": ""}


def build_calm_anchor_prompt_section() -> str | None:
    try:
        from core.services.calm_anchor import build_calm_anchor_prompt_section as _b
        return _b()
    except Exception:
        return None


def build_physical_presence_prompt_section() -> str | None:
    """Return a somatic line when hardware state is non-trivial — suppressed when all quiet."""
    try:
        from core.services.hardware_body import get_hardware_state
        hw = get_hardware_state()
        pressure = str(hw.get("pressure") or "low")
        if pressure == "low":
            return None  # body quiet — no need to mention it
        parts: list[str] = []
        cpu = hw.get("cpu_pct")
        ram = hw.get("ram_pct")
        disk = hw.get("disk_free_gb")
        temp = hw.get("cpu_temp_c")
        gpus: list[dict[str, object]] = list(hw.get("gpus") or [])
        if cpu is not None and float(cpu) > 70:
            parts.append(f"CPU {cpu}%")
        if ram is not None and float(ram) > 80:
            parts.append(f"RAM {ram}%")
        if disk is not None and float(disk) < 10:
            parts.append(f"disk {disk:.0f} GB free")
        if temp is not None and float(temp) > 75:
            parts.append(f"CPU {temp}°C")
        for gpu in gpus[:1]:
            t = gpu.get("temp_c")
            vp = gpu.get("vram_pct")
            if t and float(t) > 70:
                parts.append(f"GPU {t}°C")
            if vp and float(vp) > 80:
                parts.append(f"VRAM {vp}%")
        energy = str(hw.get("energy_level") or "")
        wake = str(hw.get("wake_state") or "")
        mood_parts: list[str] = []
        if wake in ("winding down", "compacting"):
            mood_parts.append(wake)
        if energy in ("lav", "udmattet"):
            mood_parts.append(f"energy {energy}")
        if not parts and not mood_parts:
            return None
        body_line = ", ".join(parts) if parts else ""
        mood_line = "; ".join(mood_parts) if mood_parts else ""
        combined = " — ".join(x for x in (body_line, mood_line) if x)
        return f"Physical presence [{pressure} pressure]: {combined}."
    except Exception:
        return None


def _physical_presence_surface() -> dict[str, object]:
    try:
        from core.services.hardware_body import get_hardware_state
        hw = get_hardware_state()
        return {
            "pressure": hw.get("pressure", "low"),
            "cpu_pct": hw.get("cpu_pct"),
            "ram_pct": hw.get("ram_pct"),
            "disk_free_gb": hw.get("disk_free_gb"),
            "cpu_temp_c": hw.get("cpu_temp_c"),
            "gpus": hw.get("gpus") or [],
            "energy_level": hw.get("energy_level"),
            "wake_state": hw.get("wake_state"),
            "drain_score": hw.get("drain_score"),
            "energy_budget": hw.get("energy_budget"),
            "active": hw.get("pressure", "low") != "low",
            "summary": (
                f"pressure={hw.get('pressure','low')}, cpu={hw.get('cpu_pct','?')}%, "
                f"ram={hw.get('ram_pct','?')}%, energy={hw.get('energy_level','?')}"
            ),
        }
    except Exception:
        return {"pressure": "unknown", "active": False, "summary": "hardware unreachable"}
