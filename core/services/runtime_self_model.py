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

This module was split (behavior-preserving) into focused submodules:

- ``runtime_self_model_state``    — base state + temporal/mineness awareness
- ``runtime_self_model_affect``   — flow/wonder/longing/relation awareness
- ``runtime_self_model_identity`` — self-insight/identity/dream/pressure
- ``runtime_self_model_boundary`` — self-boundary clarity + world-contact
- ``runtime_self_model_surfaces`` — small producer/subsystem surfaces + roles
- ``runtime_self_model_builder``  — top-level ``build_runtime_self_model``

Every public and private symbol that previously lived here is re-exported
from this module for full backward compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

# Re-export the full split surface. ``runtime_self_model_builder`` transitively
# re-exports state/affect/identity/surfaces, so ``import *`` here brings back
# every symbol that used to be defined in this file.
from core.services.runtime_self_model_state import *  # noqa: F401,F403
from core.services.runtime_self_model_affect import *  # noqa: F401,F403
from core.services.runtime_self_model_identity import *  # noqa: F401,F403
from core.services.runtime_self_model_boundary import *  # noqa: F401,F403
from core.services.runtime_self_model_surfaces import *  # noqa: F401,F403
from core.services.runtime_self_model_builder import *  # noqa: F401,F403

# ``build_self_model_prompt_lines`` depends on ``build_runtime_self_model``.
from core.services.runtime_self_model_builder import build_runtime_self_model  # noqa: F401

# Preserve the previously top-level imported callables as re-exports (some
# call-sites imported these names from this module historically).
from core.services.runtime_surface_cache import runtime_surface_cache  # noqa: F401
from core.identity.workspace_bootstrap import workspace_memory_paths  # noqa: F401
from core.tools.workspace_capabilities import load_workspace_capabilities  # noqa: F401


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
