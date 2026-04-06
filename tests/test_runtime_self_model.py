"""Tests for bounded runtime self-model.

Verifies:
- Self-model collects layers from runtime truth surfaces
- Layer types are correctly classified (kind, role, visibility, truth)
- Active vs groundwork layers are distinguished
- Capability vs permission vs action distinctions present
- Truth boundaries are explicit
- Prompt lines are structured (not flat label dumps)
- MC endpoint works
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# 1. Self-model builds successfully from runtime
# ---------------------------------------------------------------------------

def test_self_model_builds_and_has_layers(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    assert "layers" in model
    assert "runtime_task_state" in model
    assert "runtime_flow_state" in model
    assert "runtime_hook_state" in model
    assert "browser_body_state" in model
    assert "standing_orders_state" in model
    assert "layered_memory_state" in model
    assert "embodied_state" in model
    assert "affective_meta_state" in model
    assert "experiential_runtime_context" in model
    assert "inner_voice_daemon" in model
    assert "support_stream_awareness" in model
    assert "subjective_temporal_feel" in model
    assert "epistemic_runtime_state" in model
    assert "subagent_ecology" in model
    assert "council_runtime" in model
    assert "adaptive_planner" in model
    assert "adaptive_reasoning" in model
    assert "dream_influence" in model
    assert "guided_learning" in model
    assert "adaptive_learning" in model
    assert "self_system_code_awareness" in model
    assert "tool_intent" in model
    assert "loop_runtime" in model
    assert "idle_consolidation" in model
    assert "dream_articulation" in model
    assert "prompt_evolution" in model
    assert "truth_boundaries" in model
    assert "summary" in model
    assert "built_at" in model
    assert len(model["layers"]) > 0
    assert "experiential_continuity" in model["experiential_runtime_context"]


# ---------------------------------------------------------------------------
# 2. Layer kind classification
# ---------------------------------------------------------------------------

def test_layers_have_required_fields(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    required_fields = {"id", "label", "kind", "role", "visibility", "truth", "detail"}
    for layer in model["layers"]:
        missing = required_fields - set(layer.keys())
        assert not missing, f"Layer {layer.get('id', '?')} missing fields: {missing}"


def test_layer_kinds_are_valid(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    valid_kinds = {"capability", "permission", "producer", "memory", "identity", "orchestration", "groundwork"}
    for layer in model["layers"]:
        assert layer["kind"] in valid_kinds, f"Invalid kind {layer['kind']} for {layer['id']}"


def test_layer_roles_are_valid(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    valid_roles = {"active", "idle", "cooling", "gated", "groundwork-only", "unavailable"}
    for layer in model["layers"]:
        assert layer["role"] in valid_roles, f"Invalid role {layer['role']} for {layer['id']}"


def test_layer_visibility_is_valid(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    valid_vis = {"visible", "internal-only", "mixed"}
    for layer in model["layers"]:
        assert layer["visibility"] in valid_vis, f"Invalid visibility {layer['visibility']} for {layer['id']}"


def test_layer_truth_is_valid(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    valid_truth = {"authoritative", "derived", "interpreted", "candidate-only"}
    for layer in model["layers"]:
        assert layer["truth"] in valid_truth, f"Invalid truth {layer['truth']} for {layer['id']}"


# ---------------------------------------------------------------------------
# 3. Active vs groundwork distinction
# ---------------------------------------------------------------------------

def test_groundwork_layers_are_candidate_only(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    groundwork = [l for l in model["layers"] if l["role"] == "groundwork-only"]
    assert len(groundwork) > 0, "Expected at least one groundwork layer"
    for layer in groundwork:
        assert layer["truth"] == "candidate-only", (
            f"Groundwork layer {layer['id']} should be candidate-only, got {layer['truth']}"
        )


def test_active_layers_exist(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    active = [l for l in model["layers"] if l["role"] == "active"]
    assert len(active) >= 3, f"Expected at least 3 active layers, got {len(active)}"


# ---------------------------------------------------------------------------
# 4. Capability vs permission distinction
# ---------------------------------------------------------------------------

def test_capability_and_permission_are_separate_kinds(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    kinds = {l["kind"] for l in model["layers"]}
    assert "capability" in kinds, "No capability layers found"
    assert "permission" in kinds, "No permission layers found"

    # They should be different layers
    cap_ids = {l["id"] for l in model["layers"] if l["kind"] == "capability"}
    perm_ids = {l["id"] for l in model["layers"] if l["kind"] == "permission"}
    assert cap_ids.isdisjoint(perm_ids), "Capability and permission layers overlap"


# ---------------------------------------------------------------------------
# 5. Truth boundaries
# ---------------------------------------------------------------------------

def test_truth_boundaries_present_and_meaningful(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    boundaries = model["truth_boundaries"]
    assert "capability_vs_permission" in boundaries
    assert "capability_vs_action" in boundaries
    assert "memory_vs_identity" in boundaries
    assert "internal_vs_visible" in boundaries
    assert "runtime_truth_vs_interpretation" in boundaries
    assert "active_vs_groundwork" in boundaries
    assert "task_vs_flow" in boundaries
    assert "standing_authority_vs_turn_instruction" in boundaries
    assert "layered_memory_vs_curated_memory" in boundaries

    # Each boundary should be a non-empty string
    for key, value in boundaries.items():
        assert isinstance(value, str) and len(value) > 10, f"Boundary {key} too short"


# ---------------------------------------------------------------------------
# 6. Internal-only vs visible distinction
# ---------------------------------------------------------------------------

def test_producers_are_internal_only(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    producers = [l for l in model["layers"] if l["kind"] == "producer"]
    for p in producers:
        assert p["visibility"] == "internal-only", (
            f"Producer {p['id']} should be internal-only, got {p['visibility']}"
        )


def test_visible_chat_is_visible(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    chat = [l for l in model["layers"] if l["id"] == "visible-chat"]
    assert len(chat) == 1
    assert chat[0]["visibility"] == "visible"


# ---------------------------------------------------------------------------
# 7. Summary is structured
# ---------------------------------------------------------------------------

def test_summary_has_counts(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    summary = model["summary"]
    assert summary["total_layers"] > 0
    assert "by_kind" in summary
    assert "by_role" in summary
    assert "active_layers" in summary
    assert "groundwork_layers" in summary


# ---------------------------------------------------------------------------
# 8. Prompt lines are structured (not flat)
# ---------------------------------------------------------------------------

def test_prompt_lines_include_self_model(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()

    assert len(lines) > 0
    joined = "\n".join(lines)
    assert "RUNTIME SELF-MODEL" in joined
    assert "truth_boundary" in joined
    assert "self_model_summary" in joined
    assert "embodied_state:" in joined
    assert "affective_meta_state:" in joined
    assert "experiential_runtime_context:" in joined
    assert "experiential_narrative:" in joined
    assert "epistemic_runtime_state:" in joined
    assert "subagent_ecology:" in joined
    assert "council_runtime:" in joined
    assert "adaptive_planner:" in joined
    assert "adaptive_reasoning:" in joined
    assert "dream_influence:" in joined
    assert "guided_learning:" in joined
    assert "adaptive_learning:" in joined
    assert "self_system_code_awareness:" in joined
    assert "tool_intent:" in joined
    assert "execution_mode=read-only" in joined
    assert "mutation_permitted=False" in joined
    assert "mutation_state=" in joined
    assert "mutation_classification=" in joined
    assert "mutation_repo_scope=" in joined
    assert "mutation_system_scope=" in joined
    assert "mutation_sudo_required=" in joined
    assert "continuity=" in joined
    assert "followup_state=" in joined
    assert "loop_runtime:" in joined
    assert "runtime_tasks:" in joined
    assert "runtime_flows:" in joined
    assert "runtime_hooks:" in joined
    assert "browser_body:" in joined
    assert "standing_orders:" in joined
    assert "layered_memory:" in joined
    assert "idle_consolidation:" in joined
    assert "dream_articulation:" in joined
    assert "prompt_evolution:" in joined
    assert "learning=" in joined
    assert "dream=" in joined
    assert "co=" in joined
    assert "fragment=" in joined
    assert "direction=" in joined


def test_prompt_lines_distinguish_kinds(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    # Should have at least active_orchestration or active_capability
    assert "active_" in joined, "Prompt lines should group active layers by kind"


def test_self_model_includes_new_runtime_organs(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()
    layer_ids = {layer["id"] for layer in model["layers"]}

    assert "runtime-task-ledger" in layer_ids
    assert "runtime-flow-ledger" in layer_ids
    assert "runtime-hook-bridge" in layer_ids
    assert "browser-body" in layer_ids
    assert "standing-orders" in layer_ids
    assert "layered-memory" in layer_ids


# ---------------------------------------------------------------------------
# 9. Prompt contract uses self-model
# ---------------------------------------------------------------------------

def test_visible_self_knowledge_lines_use_self_model(isolated_runtime) -> None:
    pc = isolated_runtime.prompt_contract
    lines = pc._visible_self_knowledge_lines()

    assert len(lines) > 0
    joined = "\n".join(lines)
    # Should use the new structured format
    assert "RUNTIME SELF-MODEL" in joined or "SELF-KNOWLEDGE" in joined


# ---------------------------------------------------------------------------
# 10. MC endpoint
# ---------------------------------------------------------------------------

def test_mc_runtime_self_model_endpoint(isolated_runtime) -> None:
    mc = isolated_runtime.mission_control
    response = mc.mc_runtime_self_model()

    assert isinstance(response, dict)
    assert "layers" in response
    assert "embodied_state" in response
    assert "affective_meta_state" in response
    assert "epistemic_runtime_state" in response
    assert "inner_voice_daemon" in response
    assert "support_stream_awareness" in response
    assert "subagent_ecology" in response
    assert "council_runtime" in response
    assert "adaptive_planner" in response
    assert "adaptive_reasoning" in response
    assert "guided_learning" in response
    assert "adaptive_learning" in response
    assert "dream_influence" in response
    assert "loop_runtime" in response
    assert "idle_consolidation" in response
    assert "dream_articulation" in response
    assert "prompt_evolution" in response
    assert "truth_boundaries" in response
    assert "summary" in response


# ---------------------------------------------------------------------------
# 11. Producer layers reflect cadence state
# ---------------------------------------------------------------------------

def test_producer_layers_present(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    producers = [l for l in model["layers"] if l["kind"] == "producer"]
    assert len(producers) >= 3, f"Expected at least 3 producers, got {len(producers)}"

    names = {l["id"] for l in producers}
    assert "producer-brain_continuity" in names or any("brain" in n for n in names)
    assert "producer-sleep_consolidation" in names or any("sleep" in n for n in names)
    assert "producer-witness_daemon" in names or any("witness" in n for n in names)
    assert "producer-inner_voice_daemon" in names or any("voice" in n for n in names)
    assert "producer-dream_articulation" in names or any("dream" in n for n in names)
    assert "producer-prompt_evolution_runtime" in names or any("prompt evolution" in n.lower() for n in names)


# ---------------------------------------------------------------------------
# 12. Memory vs identity distinction
# ---------------------------------------------------------------------------

def test_memory_and_identity_are_distinct(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    memory = [l for l in model["layers"] if l["kind"] == "memory"]
    identity = [l for l in model["layers"] if l["kind"] == "identity"]

    assert len(memory) >= 2, "Expected at least 2 memory layers"
    assert len(identity) >= 1, "Expected at least 1 identity layer"

    memory_ids = {l["id"] for l in memory}
    identity_ids = {l["id"] for l in identity}
    assert memory_ids.isdisjoint(identity_ids), "Memory and identity layers must not overlap"


# ---------------------------------------------------------------------------
# 13. Support stream awareness
# ---------------------------------------------------------------------------


def test_self_model_includes_support_stream_awareness(isolated_runtime) -> None:
    """Self-model must include support_stream_awareness surface."""
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    assert "support_stream_awareness" in model
    assert "inner_voice_daemon" in model
    stream = model["support_stream_awareness"]
    assert "stream_state" in stream
    assert "stream_shaped" in stream
    assert "active_support_posture" in stream
    assert "active_support_bias" in stream
    assert "narrative" in stream
    assert stream["authority"] == "derived-runtime-truth"
    assert stream["visibility"] == "internal-only"
    assert stream["kind"] == "support-stream-awareness"


def test_support_stream_baseline_when_no_support() -> None:
    """Stream state must be 'baseline' when experiential support is steadying."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_support_stream_awareness

    experiential = {
        "experiential_support": {
            "support_posture": "steadying",
            "support_bias": "none",
            "support_mode": "steady",
        },
    }
    inner_voice = {"last_result": None}

    stream = _derive_support_stream_awareness(experiential, inner_voice)
    assert stream["stream_state"] == "baseline"
    assert stream["stream_shaped"] is False
    assert stream["active_support_posture"] == "none"
    assert stream["active_support_bias"] == "none"
    assert stream["narrative"] == ""


def test_support_stream_active_but_not_shaped() -> None:
    """Stream active when support is non-default but inner voice not yet produced."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_support_stream_awareness

    experiential = {
        "experiential_support": {
            "support_posture": "carrying",
            "support_bias": "protect_focus",
            "support_mode": "weighted",
        },
    }
    inner_voice = {"last_result": {"inner_voice_created": False, "mode": ""}}

    stream = _derive_support_stream_awareness(experiential, inner_voice)
    assert stream["stream_state"] == "weighted"
    assert stream["stream_shaped"] is False
    assert stream["active_support_posture"] == "carrying"
    assert stream["active_support_bias"] == "protect_focus"
    assert stream["shaped_voice_mode"] == ""
    assert "not yet shaped" in stream["narrative"]


def test_support_stream_shaped_when_voice_produced() -> None:
    """Stream shaped when support is active AND inner voice was produced."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_support_stream_awareness

    experiential = {
        "experiential_support": {
            "support_posture": "carrying",
            "support_bias": "protect_focus",
            "support_mode": "weighted",
        },
    }
    inner_voice = {
        "last_result": {
            "inner_voice_created": True,
            "mode": "continuity-aware",
        },
    }

    stream = _derive_support_stream_awareness(experiential, inner_voice)
    assert stream["stream_state"] == "weighted"
    assert stream["stream_shaped"] is True
    assert stream["active_support_posture"] == "carrying"
    assert stream["shaped_voice_mode"] == "continuity-aware"
    assert "shaped inner voice to continuity-aware" in stream["narrative"]


def test_support_stream_prompt_line_only_when_active(isolated_runtime) -> None:
    """support_stream prompt line should only appear when stream_state != baseline."""
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    # In isolated_runtime without real state, support should be steadying/baseline
    # so support_stream line should NOT appear
    if "support_stream:" in joined:
        # If it does appear, it must have a non-baseline state
        assert "state=baseline" not in joined


# ---------------------------------------------------------------------------
# 14. Subjective temporal feel
# ---------------------------------------------------------------------------


def test_self_model_includes_subjective_temporal_feel(isolated_runtime) -> None:
    """Self-model must include subjective_temporal_feel surface."""
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    assert "subjective_temporal_feel" in model
    feel = model["subjective_temporal_feel"]
    assert "temporal_state" in feel
    assert "felt_proximity" in feel
    assert "return_signal" in feel
    assert "persistence_feel" in feel
    assert "narrative" in feel
    assert feel["authority"] == "derived-runtime-truth"
    assert feel["visibility"] == "internal-only"
    assert feel["kind"] == "subjective-temporal-feel"


def test_temporal_feel_immediate_when_continuous_stable() -> None:
    """Temporal feel is 'immediate' / 'close' when no gap and state stable."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_subjective_temporal_feel

    experiential = {
        "intermittence_translation": {"state": "continuous", "gap_minutes": 0},
        "experiential_continuity": {"continuity_state": "stable"},
        "experiential_support": {"support_posture": "steadying"},
        "context_pressure_translation": {"state": "clear"},
    }
    inner_voice = {"last_result": None}

    feel = _derive_subjective_temporal_feel(experiential, inner_voice)
    assert feel["temporal_state"] == "immediate"
    assert feel["felt_proximity"] == "close"
    assert feel["return_signal"] is False
    assert feel["persistence_feel"] == "settled"


def test_temporal_feel_returning_after_gap() -> None:
    """Temporal feel is 'returning' / 'resumed' when returned-after-gap."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_subjective_temporal_feel

    experiential = {
        "intermittence_translation": {"state": "returned-after-gap", "gap_minutes": 35},
        "experiential_continuity": {"continuity_state": "returning"},
        "experiential_support": {"support_posture": "steadying"},
        "context_pressure_translation": {"state": "clear"},
    }
    inner_voice = {"last_result": None}

    feel = _derive_subjective_temporal_feel(experiential, inner_voice)
    assert feel["temporal_state"] == "returning"
    assert feel["felt_proximity"] == "resumed"
    assert feel["return_signal"] is True
    assert feel["persistence_feel"] == "reconnecting"
    assert "return" in feel["narrative"]
    assert "35m" in feel["narrative"]


def test_temporal_feel_lingering_elevated_state() -> None:
    """Temporal feel is 'lingering' when elevated state persists without shift."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_subjective_temporal_feel

    experiential = {
        "intermittence_translation": {"state": "continuous", "gap_minutes": 2},
        "experiential_continuity": {"continuity_state": "lingering"},
        "experiential_support": {"support_posture": "steadying"},
        "context_pressure_translation": {"state": "clear"},
    }
    inner_voice = {"last_result": None}

    feel = _derive_subjective_temporal_feel(experiential, inner_voice)
    assert feel["temporal_state"] == "lingering"
    assert feel["persistence_feel"] == "persistent"
    assert "still present" in feel["narrative"]


def test_temporal_feel_stretched_when_lingering_with_gap() -> None:
    """Temporal feel is 'stretched' when lingering AND brief gap present."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_subjective_temporal_feel

    experiential = {
        "intermittence_translation": {"state": "brief-gap", "gap_minutes": 12},
        "experiential_continuity": {"continuity_state": "lingering"},
        "experiential_support": {"support_posture": "steadying"},
        "context_pressure_translation": {"state": "clear"},
    }
    inner_voice = {"last_result": None}

    feel = _derive_subjective_temporal_feel(experiential, inner_voice)
    assert feel["temporal_state"] == "stretched"
    assert "drawn out" in feel["narrative"]


def test_temporal_feel_receding_when_easing() -> None:
    """Temporal feel is 'receding' / 'fading' when continuity state is easing."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_subjective_temporal_feel

    experiential = {
        "intermittence_translation": {"state": "continuous", "gap_minutes": 3},
        "experiential_continuity": {"continuity_state": "easing"},
        "experiential_support": {"support_posture": "steadying"},
        "context_pressure_translation": {"state": "clear"},
    }
    inner_voice = {"last_result": None}

    feel = _derive_subjective_temporal_feel(experiential, inner_voice)
    assert feel["temporal_state"] == "receding"
    assert feel["felt_proximity"] == "fading"
    assert feel["persistence_feel"] == "releasing"


def test_temporal_feel_held_when_support_active() -> None:
    """Felt proximity is 'held' when support posture is active."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_subjective_temporal_feel

    experiential = {
        "intermittence_translation": {"state": "continuous", "gap_minutes": 0},
        "experiential_continuity": {"continuity_state": "stable"},
        "experiential_support": {"support_posture": "carrying"},
        "context_pressure_translation": {"state": "clear"},
    }
    inner_voice = {"last_result": None}

    feel = _derive_subjective_temporal_feel(experiential, inner_voice)
    assert feel["temporal_state"] == "immediate"
    assert feel["felt_proximity"] == "held"
    assert "held" in feel["narrative"]


def test_temporal_feel_held_when_inner_voice_created() -> None:
    """Felt proximity is 'held' when inner voice was recently created."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_subjective_temporal_feel

    experiential = {
        "intermittence_translation": {"state": "continuous", "gap_minutes": 0},
        "experiential_continuity": {"continuity_state": "stable"},
        "experiential_support": {"support_posture": "steadying"},
        "context_pressure_translation": {"state": "clear"},
    }
    inner_voice = {"last_result": {"inner_voice_created": True, "mode": "reflective-carry"}}

    feel = _derive_subjective_temporal_feel(experiential, inner_voice)
    assert feel["felt_proximity"] == "held"


def test_temporal_feel_prompt_line_only_when_non_immediate(isolated_runtime) -> None:
    """Temporal feel prompt line should only appear when state != immediate or proximity == held."""
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    # In isolated_runtime, temporal feel is likely immediate/close
    # so temporal_feel line should NOT appear (unless held)
    if "temporal_feel:" in joined:
        assert "state=immediate" not in joined or "proximity=held" in joined
