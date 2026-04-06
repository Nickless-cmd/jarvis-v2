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

from apps.api.jarvis_api.services.runtime_surface_cache import runtime_surface_cache
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
            "support_stream_awareness": _derive_support_stream_awareness(experiential, inner_voice),
            "subjective_temporal_feel": _derive_subjective_temporal_feel(experiential, inner_voice),
            "epistemic_runtime_state": _epistemic_runtime_state_surface(),
            "subagent_ecology": _subagent_ecology_surface(),
            "council_runtime": _council_runtime_surface(),
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
    layers.append({
        "id": "heartbeat",
        "label": "Heartbeat runtime",
        "kind": "orchestration",
        "role": _heartbeat_role(),
        "visibility": "internal-only",
        "truth": "authoritative",
        "detail": "Basal pulse. Drives cadence ticks and non-visible producers.",
    })

    layers.append({
        "id": "internal-cadence",
        "label": "Internal cadence layer",
        "kind": "orchestration",
        "role": "active",
        "visibility": "internal-only",
        "truth": "authoritative",
        "detail": "Shared rhythm for non-visible producers. Evaluates due/cooling/blocked.",
    })

    embodied = _embodied_state_surface()
    layers.append({
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
    })

    affective_meta = _affective_meta_state_surface()
    layers.append({
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
    })

    epistemic_state = _epistemic_runtime_state_surface()
    layers.append({
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
    })

    subagent_ecology = _subagent_ecology_surface()
    ecology_summary = subagent_ecology.get("summary") or {}
    layers.append({
        "id": "subagent-ecology-light",
        "label": "Subagent ecology light",
        "kind": "orchestration",
        "role": "active" if int(ecology_summary.get("active_count") or 0) > 0 else "idle",
        "visibility": "internal-only",
        "truth": "derived",
        "detail": (
            f"active={int(ecology_summary.get('active_count') or 0)}; "
            f"blocked={int(ecology_summary.get('blocked_count') or 0)}; "
            f"last={ecology_summary.get('last_active_role_name') or 'none'}; "
            f"tool_access={subagent_ecology.get('tool_access') or 'none'}."
        ),
    })

    council_runtime = _council_runtime_surface()
    layers.append({
        "id": "council-runtime-light",
        "label": "Council / swarm light",
        "kind": "orchestration",
        "role": "active" if str(council_runtime.get("council_state") or "quiet") not in {"quiet", "held"} else "idle",
        "visibility": "internal-only",
        "truth": "derived",
        "detail": (
            f"state={council_runtime.get('council_state') or 'quiet'}; "
            f"recommendation={council_runtime.get('recommendation') or 'none'}; "
            f"divergence={council_runtime.get('divergence_level') or 'low'}; "
            f"tool_access={council_runtime.get('tool_access') or 'none'}."
        ),
    })

    adaptive_planner = _adaptive_planner_surface()
    layers.append({
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
    })

    adaptive_reasoning = _adaptive_reasoning_surface()
    layers.append({
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
    })

    dream_influence = _dream_influence_surface()
    layers.append({
        "id": "dream-influence-light",
        "label": "Dream influence light",
        "kind": "orchestration",
        "role": "active" if str(dream_influence.get("influence_state") or "quiet") != "quiet" else "idle",
        "visibility": "internal-only",
        "truth": "derived",
        "detail": (
            f"state={dream_influence.get('influence_state') or 'quiet'}; "
            f"target={dream_influence.get('influence_target') or 'none'}; "
            f"mode={dream_influence.get('influence_mode') or 'stabilize'}; "
            f"strength={dream_influence.get('influence_strength') or 'none'}."
        ),
    })

    guided_learning = _guided_learning_surface()
    layers.append({
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
    })

    adaptive_learning = _adaptive_learning_surface()
    layers.append({
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
    })

    self_system_code_awareness = _self_system_code_awareness_surface()
    layers.append({
        "id": "self-system-code-awareness-light",
        "label": "Self system / code awareness light",
        "kind": "orchestration",
        "role": "active" if str(self_system_code_awareness.get("code_awareness_state") or "repo-unavailable") != "repo-unavailable" else "idle",
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
    })

    tool_intent = _tool_intent_surface()
    layers.append({
        "id": "approval-gated-tool-intent-light",
        "label": "Approval-gated tool intent light",
        "kind": "orchestration",
        "role": "active" if str(tool_intent.get("intent_state") or "idle") != "idle" else "idle",
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
    })

    loop_runtime = _loop_runtime_surface()
    loop_summary = loop_runtime.get("summary") or {}
    layers.append({
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
    })

    layers.append({
        "id": "runtime-task-ledger",
        "label": "Runtime task ledger",
        "kind": "orchestration",
        "role": (
            "active"
            if int(task_state.get("queued_count") or 0) or int(task_state.get("running_count") or 0)
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
    })

    layers.append({
        "id": "runtime-flow-ledger",
        "label": "Runtime flow ledger",
        "kind": "orchestration",
        "role": (
            "active"
            if int(flow_state.get("queued_count") or 0) or int(flow_state.get("running_count") or 0)
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
    })

    layers.append({
        "id": "runtime-hook-bridge",
        "label": "Runtime hook bridge",
        "kind": "orchestration",
        "role": (
            "gated"
            if int(hook_state.get("pending_count") or 0) > 0
            else ("active" if int(hook_state.get("dispatched_count") or 0) > 0 else "idle")
        ),
        "visibility": "internal-only",
        "truth": "authoritative",
        "detail": (
            f"pending={hook_state.get('pending_count') or 0}; "
            f"dispatched={hook_state.get('dispatched_count') or 0}; "
            f"latest={hook_state.get('latest_event_kind') or 'none'}."
        ),
    })

    layers.append({
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
    })

    consolidation = _idle_consolidation_surface()
    consolidation_summary = consolidation.get("summary") or {}
    layers.append({
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
    })

    dream = _dream_articulation_surface()
    dream_summary = dream.get("summary") or {}
    layers.append({
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
    })

    prompt_evolution = _prompt_evolution_surface()
    prompt_evolution_summary = prompt_evolution.get("summary") or {}
    layers.append({
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
    })
    try:
        from apps.api.jarvis_api.services.emergent_signal_tracking import (
            build_runtime_emergent_signal_surface,
        )

        emergent = build_runtime_emergent_signal_surface(limit=3)
        emergent_summary = emergent.get("summary") or {}
        layers.append({
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
        })
    except Exception:
        pass

    # --- Capability layers ---
    layers.append({
        "id": "visible-chat",
        "label": "Visible chat lane",
        "kind": "capability",
        "role": _visible_chat_role(),
        "visibility": "visible",
        "truth": "authoritative",
        "detail": "User-facing conversation. Jarvis' primary visible output.",
    })

    layers.append({
        "id": "internal-fallback-lane",
        "label": "Internal fallback model lane",
        "kind": "capability",
        "role": _cheap_lane_role(),
        "visibility": "internal-only",
        "truth": "authoritative",
        "detail": "Fallback model lane for bounded internal jobs when the local lane is unavailable.",
    })

    layers.append({
        "id": "local-lane",
        "label": "Local model lane",
        "kind": "capability",
        "role": _local_lane_role(),
        "visibility": "internal-only",
        "truth": "authoritative",
        "detail": "Local model for heartbeat and inner producers.",
    })

    workspace_capabilities = load_workspace_capabilities()
    callable_ids = workspace_capabilities.get("callable_capability_ids") or []
    gated_ids = workspace_capabilities.get("approval_gated_capability_ids") or []
    layers.append({
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
    })

    # --- Producer layers ---
    for p in _producer_layers():
        layers.append(p)

    # --- Memory layers ---
    layers.append({
        "id": "workspace-memory",
        "label": "Curated workspace memory (MEMORY.md)",
        "kind": "memory",
        "role": "active",
        "visibility": "mixed",
        "truth": "authoritative",
        "detail": "Curated cross-session memory. User-visible and LLM-readable.",
    })

    layers.append({
        "id": "layered-memory",
        "label": "Layered memory",
        "kind": "memory",
        "role": (
            "active"
            if layered_memory.get("daily_exists") and layered_memory.get("curated_exists")
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
    })

    layers.append({
        "id": "private-brain",
        "label": "Private brain records",
        "kind": "memory",
        "role": _private_brain_role(),
        "visibility": "internal-only",
        "truth": "authoritative",
        "detail": "Append-only private memory. Not user-visible.",
    })

    layers.append({
        "id": "session-distillation",
        "label": "Session distillation",
        "kind": "memory",
        "role": "active",
        "visibility": "internal-only",
        "truth": "derived",
        "detail": "End-of-run carry classification into private brain or workspace memory.",
    })

    # --- Identity layers ---
    layers.append({
        "id": "soul-identity",
        "label": "SOUL + IDENTITY",
        "kind": "identity",
        "role": "active",
        "visibility": "mixed",
        "truth": "authoritative",
        "detail": "Protected core. Defines who Jarvis is. Not mutable by runtime.",
    })

    layers.append({
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
    })

    # --- Permission / gated layers ---
    layers.append({
        "id": "approval-pipeline",
        "label": "Contract candidate / approval pipeline",
        "kind": "permission",
        "role": _approval_pipeline_role(),
        "visibility": "mixed",
        "truth": "authoritative",
        "detail": "Workspace changes require user approval. Capability, not action.",
    })

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
    context_pressure_translation = experiential.get("context_pressure_translation") or {}
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
    if experiential_support.get("support_posture") and experiential_support["support_posture"] != "steadying":
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
    if support_stream.get("stream_state") and support_stream["stream_state"] != "baseline":
        lines.append(
            "  support_stream: "
            f"state={support_stream['stream_state']}"
            f" | shaped={support_stream.get('stream_shaped', False)}"
            f" | posture={support_stream.get('active_support_posture') or 'none'}"
            + (f" | shaped_mode={support_stream['shaped_voice_mode']}" if support_stream.get("shaped_voice_mode") else "")
        )
        if support_stream.get("narrative"):
            lines.append(
                f"  support_stream_narrative: "
                f"'{support_stream['narrative']}'"
            )
    temporal_feel = model.get("subjective_temporal_feel") or {}
    if temporal_feel.get("temporal_state") and temporal_feel["temporal_state"] != "immediate":
        lines.append(
            "  temporal_feel: "
            f"state={temporal_feel['temporal_state']}"
            f" | proximity={temporal_feel.get('felt_proximity') or 'close'}"
            f" | return={temporal_feel.get('return_signal', False)}"
            f" | persistence={temporal_feel.get('persistence_feel') or 'settled'}"
        )
        if temporal_feel.get("narrative"):
            lines.append(
                f"  temporal_feel_narrative: "
                f"'{temporal_feel['narrative']}'"
            )
    elif temporal_feel.get("felt_proximity") == "held":
        lines.append(
            "  temporal_feel: "
            f"state=immediate"
            f" | proximity=held"
            f" | persistence={temporal_feel.get('persistence_feel') or 'settled'}"
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
        from apps.api.jarvis_api.services.embodied_state import (
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
        from apps.api.jarvis_api.services.loop_runtime import (
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
        from apps.api.jarvis_api.services.runtime_tasks import list_tasks

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
        from apps.api.jarvis_api.services.runtime_flows import list_flows

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
        from core.runtime.db import get_runtime_hook_dispatch, list_runtime_hook_dispatches

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
        from apps.api.jarvis_api.services.runtime_browser_body import list_browser_bodies

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
        from apps.api.jarvis_api.services.affective_meta_state import (
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
        from apps.api.jarvis_api.services.experiential_runtime_context import (
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
        from apps.api.jarvis_api.services.inner_voice_daemon import (
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
        temporal_state, felt_proximity, return_signal,
        persistence_feel, gap_minutes,
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
    """Build a compact, non-melodramatic self-awareness narrative for felt time."""
    if temporal_state == "returning":
        return (
            f"This moment feels like a return after ~{gap_minutes}m away. "
            "Prior context is resuming, not starting fresh."
        )
    if temporal_state == "stretched":
        return (
            "An elevated state persists across a gap; "
            "time feels drawn out rather than immediate."
        )
    if temporal_state == "lingering":
        return (
            "Something from the prior moment is still present; "
            "the current state has not settled to baseline."
        )
    if temporal_state == "receding":
        return (
            "Prior pressure is easing; "
            "the current moment feels like it is moving away from tension."
        )
    if temporal_state == "recent":
        return (
            f"A brief gap (~{gap_minutes}m) sits behind this moment, "
            "but continuity holds."
        )
    # immediate
    if felt_proximity == "held":
        return "This moment feels immediate and actively held by support or inner voice."
    return "Experience feels continuous and close; nothing presses from the past."


def _idle_consolidation_surface() -> dict[str, object]:
    try:
        from apps.api.jarvis_api.services.idle_consolidation import (
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
        from apps.api.jarvis_api.services.epistemic_runtime_state import (
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
        from apps.api.jarvis_api.services.subagent_ecology import (
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


def _council_runtime_surface() -> dict[str, object]:
    try:
        from apps.api.jarvis_api.services.council_runtime import (
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


def _adaptive_planner_surface() -> dict[str, object]:
    try:
        from apps.api.jarvis_api.services.adaptive_planner_runtime import (
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
        from apps.api.jarvis_api.services.adaptive_reasoning_runtime import (
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
        from apps.api.jarvis_api.services.guided_learning_runtime import (
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
        from apps.api.jarvis_api.services.dream_influence_runtime import (
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
        from apps.api.jarvis_api.services.adaptive_learning_runtime import (
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
        from apps.api.jarvis_api.services.dream_articulation import (
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
        from apps.api.jarvis_api.services.prompt_evolution_runtime import (
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
        from apps.api.jarvis_api.services.self_system_code_awareness import (
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
        from apps.api.jarvis_api.services.tool_intent_runtime import (
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
        from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
        vis = visible_execution_readiness()
        return "active" if vis.get("provider_status") == "ready" else "idle"
    except Exception:
        return "unavailable"


def _cheap_lane_role() -> str:
    try:
        from apps.api.jarvis_api.services.non_visible_lane_execution import cheap_lane_execution_truth
        return "active" if cheap_lane_execution_truth().get("can_execute") else "unavailable"
    except Exception:
        return "unavailable"


def _local_lane_role() -> str:
    try:
        from apps.api.jarvis_api.services.non_visible_lane_execution import local_lane_execution_truth
        return "active" if local_lane_execution_truth().get("can_execute") else "unavailable"
    except Exception:
        return "unavailable"


def _private_brain_role() -> str:
    try:
        from apps.api.jarvis_api.services.session_distillation import build_private_brain_context
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
        from apps.api.jarvis_api.services.internal_cadence import get_cadence_state
        cadence = get_cadence_state()
        for p in cadence.get("producers") or []:
            name = str(p.get("name") or "")
            tick_status = (p.get("last_tick_status") or {})
            status = str(tick_status.get("status") or "idle")
            role_map = {
                "ran": "active",
                "cooling_down": "cooling",
                "visible_grace": "idle",
                "blocked": "idle",
                "error": "idle",
            }
            role = role_map.get(status, "idle")
            producers.append({
                "id": f"producer-{name}",
                "label": _producer_label(name),
                "kind": "producer",
                "role": role,
                "visibility": "internal-only",
                "truth": "authoritative",
                "detail": f"Cadence status: {status}. Last run: {p.get('last_run_at') or 'never'}.",
            })
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
            producers.append({
                "id": f"producer-{name}",
                "label": label,
                "kind": "producer",
                "role": "idle",
                "visibility": "internal-only",
                "truth": "authoritative",
                "detail": "Cadence layer has not run yet.",
            })

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
    """Build awareness of the cognitive architecture state — what Jarvis knows about himself."""
    systems: list[dict[str, object]] = []

    def _add(name: str, builder, detail_fn=None):
        try:
            result = builder()
            active = bool(result) and (result.get("active", False) if isinstance(result, dict) else bool(result))
            summary = ""
            if isinstance(result, dict):
                summary = str(result.get("summary") or "")[:80]
            systems.append({"system": name, "active": active, "summary": summary})
        except Exception:
            systems.append({"system": name, "active": False, "summary": "unavailable"})

    from apps.api.jarvis_api.services.personality_vector import build_personality_vector_surface
    _add("personality_vector", build_personality_vector_surface)

    from apps.api.jarvis_api.services.taste_profile import build_taste_profile_surface
    _add("taste_profile", build_taste_profile_surface)

    from apps.api.jarvis_api.services.relationship_texture import build_relationship_texture_surface
    _add("relationship_texture", build_relationship_texture_surface)

    from apps.api.jarvis_api.services.chronicle_engine import build_chronicle_surface
    _add("chronicle", build_chronicle_surface)

    from apps.api.jarvis_api.services.compass_engine import build_compass_surface
    _add("compass", build_compass_surface)

    from apps.api.jarvis_api.services.rhythm_engine import build_rhythm_surface
    _add("rhythm", build_rhythm_surface)

    from apps.api.jarvis_api.services.user_emotional_resonance import build_user_emotional_resonance_surface
    _add("user_emotional_resonance", build_user_emotional_resonance_surface)

    from apps.api.jarvis_api.services.experiential_memory import build_experiential_memory_surface
    _add("experiential_memory", build_experiential_memory_surface)

    from apps.api.jarvis_api.services.habit_tracker import build_habit_surface
    _add("habits", build_habit_surface)

    from apps.api.jarvis_api.services.forgetting_curve import build_forgetting_curve_surface
    _add("forgetting_curve", build_forgetting_curve_surface)

    from apps.api.jarvis_api.services.self_experiments import build_self_experiments_surface
    _add("self_experiments", build_self_experiments_surface)

    from apps.api.jarvis_api.services.dream_carry_over import build_dream_carry_over_surface
    _add("dream_carry_over", build_dream_carry_over_surface)

    from apps.api.jarvis_api.services.seed_system import build_seed_surface
    _add("seeds", build_seed_surface)

    from apps.api.jarvis_api.services.narrative_identity import build_narrative_identity_surface
    _add("narrative_identity", build_narrative_identity_surface)

    from apps.api.jarvis_api.services.gratitude_tracker import build_gratitude_surface
    _add("gratitude", build_gratitude_surface)

    from apps.api.jarvis_api.services.emergent_goals import build_emergent_goals_surface
    _add("emergent_goals", build_emergent_goals_surface)

    from apps.api.jarvis_api.services.boredom_engine import build_boredom_surface
    _add("boredom", build_boredom_surface)

    from apps.api.jarvis_api.services.flow_state_detection import build_flow_state_surface
    _add("flow_state", build_flow_state_surface)

    from apps.api.jarvis_api.services.value_formation import build_formed_values_surface
    _add("formed_values", build_formed_values_surface)

    from apps.api.jarvis_api.services.cross_signal_analysis import build_cross_signal_analysis_surface
    _add("cross_signal_analysis", build_cross_signal_analysis_surface)

    from apps.api.jarvis_api.services.user_theory_of_mind import build_user_theory_of_mind_surface
    _add("user_theory_of_mind", build_user_theory_of_mind_surface)

    active_count = sum(1 for s in systems if s.get("active"))
    return {
        "systems": systems,
        "active_count": active_count,
        "total_count": len(systems),
        "summary": f"{active_count}/{len(systems)} cognitive systems active",
    }
