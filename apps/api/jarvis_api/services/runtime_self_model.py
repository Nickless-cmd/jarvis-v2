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

from apps.api.jarvis_api.services.runtime_surface_cache import runtime_surface_cache


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

        return {
            "layers": layers,
            "embodied_state": _embodied_state_surface(),
            "affective_meta_state": _affective_meta_state_surface(),
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
            "summary": summary,
            "built_at": datetime.now(UTC).isoformat(),
        }


def _collect_layers() -> list[dict[str, str]]:
    """Collect all known layers with type annotations."""
    layers: list[dict[str, str]] = []

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
            f"approval_required={tool_intent.get('approval_required', True)}; "
            f"execution={tool_intent.get('execution_state') or 'not-executed'}."
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
        "id": "cheap-lane",
        "label": "Cheap model lane",
        "kind": "capability",
        "role": _cheap_lane_role(),
        "visibility": "internal-only",
        "truth": "authoritative",
        "detail": "Low-cost model for internal small jobs.",
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

    # --- Producer layers ---
    for p in _producer_layers():
        layers.append(p)

    # --- Memory layers ---
    layers.append({
        "id": "workspace-memory",
        "label": "Workspace memory (MEMORY.md)",
        "kind": "memory",
        "role": "active",
        "visibility": "mixed",
        "truth": "authoritative",
        "detail": "Persistent cross-session memory. User-visible and LLM-readable.",
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
    consolidation = model.get("idle_consolidation") or {}
    consolidation_summary = consolidation.get("summary") or {}
    dream = model.get("dream_articulation") or {}
    dream_summary = dream.get("summary") or {}
    prompt_evolution = model.get("prompt_evolution") or {}
    prompt_evolution_summary = prompt_evolution.get("summary") or {}

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

    # Key truth boundaries (compact)
    lines.append(f"  truth_boundary: capability!=permission!=action | memory!=identity | internal!=visible | runtime_truth!=interpretation")
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
        f" | approval_required={tool_intent.get('approval_required', True)}"
        f" | execution={tool_intent.get('execution_state') or 'not-executed'}"
    )
    lines.append(
        "  loop_runtime: "
        f"{loop_summary.get('current_status') or 'none'}"
        f" | active={loop_summary.get('active_count') or 0}"
        f" | standby={loop_summary.get('standby_count') or 0}"
        f" | resumed={loop_summary.get('resumed_count') or 0}"
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
        from apps.api.jarvis_api.services.heartbeat_runtime import heartbeat_runtime_surface
        hb = heartbeat_runtime_surface()
        return "active" if hb.get("state", {}).get("enabled") else "idle"
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
