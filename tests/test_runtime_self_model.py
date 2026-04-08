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

import importlib


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
    assert "longing_awareness" in model
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
    assert "longing_awareness" in response
    assert "guided_learning" in response
    assert "adaptive_learning" in response
    assert "dream_influence" in response
    assert "loop_runtime" in response
    assert "idle_consolidation" in response
    assert "dream_articulation" in response
    assert "prompt_evolution" in response
    assert "truth_boundaries" in response
    assert "summary" in response


def test_cognitive_architecture_awareness_uses_shared_runtime_builder(
    isolated_runtime,
    monkeypatch,
) -> None:
    model_mod = isolated_runtime.runtime_self_model
    cognitive_architecture_surface = importlib.import_module(
        "apps.api.jarvis_api.services.cognitive_architecture_surface"
    )
    shared = {
        "systems": [{"system": "body_memory", "active": True, "summary": "warm"}],
        "surfaces": {"body_memory": {"active": True}},
        "active_count": 1,
        "total_count": 1,
        "summary": "1/1 cognitive systems active",
    }

    monkeypatch.setattr(
        cognitive_architecture_surface,
        "build_cognitive_architecture_surface",
        lambda: shared,
    )

    assert model_mod._cognitive_architecture_awareness() == shared


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


# ---------------------------------------------------------------------------
# 15. Mineness / ownership awareness
# ---------------------------------------------------------------------------


def test_self_model_includes_mineness_ownership(isolated_runtime) -> None:
    """Self-model must expose a bounded mineness_ownership surface."""
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    assert "mineness_ownership" in model
    mineness = model["mineness_ownership"]
    assert "ownership_state" in mineness
    assert "self_relevance" in mineness
    assert "carried_thread_state" in mineness
    assert "carried_thread_count" in mineness
    assert "return_ownership" in mineness
    assert "narrative" in mineness
    assert mineness["authority"] == "derived-runtime-truth"
    assert mineness["visibility"] == "internal-only"
    assert mineness["kind"] == "mineness-ownership"
    assert mineness["ownership_state"] in {
        "ambient",
        "held",
        "owned",
        "returning-owned",
    }
    assert mineness["self_relevance"] in {
        "merely-present",
        "actively-carried",
        "personally-salient",
        "resumed-own",
    }
    assert mineness["carried_thread_state"] in {
        "none",
        "single",
        "multiple",
        "returning",
    }


def test_mineness_ambient_when_no_basis() -> None:
    """Ownership stays ambient with empty narrative when nothing is carried."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_mineness_ownership,
    )

    experiential = {"experiential_continuity": {"continuity_state": "stable"}}
    inner_voice = {"last_result": None}
    support_stream = {"stream_shaped": False, "active_support_posture": "none"}
    temporal_feel = {"felt_proximity": "close", "return_signal": False}
    sources = {
        "brain_active": False,
        "brain_record_count": 0,
        "brain_top_focus": "",
        "brain_continuity_summary": "",
        "open_loop_open_count": 0,
        "open_loop_signal": "",
    }

    mineness = _derive_mineness_ownership(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        sources=sources,
    )
    assert mineness["ownership_state"] == "ambient"
    assert mineness["self_relevance"] == "merely-present"
    assert mineness["carried_thread_state"] == "none"
    assert mineness["carried_thread_count"] == 0
    assert mineness["return_ownership"] is False
    assert mineness["narrative"] == ""


def test_mineness_held_when_support_shaped_voice() -> None:
    """Ownership becomes 'held' when support/voice holds signals without full carry."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_mineness_ownership,
    )

    experiential = {"experiential_continuity": {"continuity_state": "stable"}}
    inner_voice = {
        "last_result": {"inner_voice_created": True, "mode": "witness-steady"}
    }
    support_stream = {
        "stream_shaped": True,
        "active_support_posture": "grounding",
    }
    temporal_feel = {"felt_proximity": "held", "return_signal": False}
    sources = {
        "brain_active": False,
        "brain_record_count": 0,
        "brain_top_focus": "",
        "brain_continuity_summary": "",
        "open_loop_open_count": 0,
        "open_loop_signal": "",
    }

    mineness = _derive_mineness_ownership(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        sources=sources,
    )
    assert mineness["ownership_state"] == "held"
    assert mineness["self_relevance"] == "actively-carried"
    assert mineness["return_ownership"] is False
    assert mineness["narrative"] != ""
    assert "held" in mineness["narrative"].lower() or "present" in mineness["narrative"].lower()


def test_mineness_owned_when_brain_carry_plus_signal() -> None:
    """Ownership becomes 'owned' when private brain carries threads."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_mineness_ownership,
    )

    experiential = {"experiential_continuity": {"continuity_state": "stable"}}
    inner_voice = {
        "last_result": {"inner_voice_created": True, "mode": "carrying"}
    }
    support_stream = {"stream_shaped": False, "active_support_posture": "none"}
    temporal_feel = {"felt_proximity": "close", "return_signal": False}
    sources = {
        "brain_active": True,
        "brain_record_count": 3,
        "brain_top_focus": "mineness ownership design",
        "brain_continuity_summary": "Private brain carries 3 active records.",
        "open_loop_open_count": 2,
        "open_loop_signal": "finish mineness pass",
    }

    mineness = _derive_mineness_ownership(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        sources=sources,
    )
    assert mineness["ownership_state"] == "owned"
    assert mineness["self_relevance"] == "personally-salient"
    assert mineness["carried_thread_state"] == "multiple"
    assert mineness["carried_thread_count"] == 3
    assert mineness["return_ownership"] is False
    assert "stream" in mineness["narrative"].lower() or "thread" in mineness["narrative"].lower()


def test_mineness_returning_owned_when_carry_and_return() -> None:
    """Ownership becomes 'returning-owned' when owned thread returns after gap."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_mineness_ownership,
    )

    experiential = {"experiential_continuity": {"continuity_state": "returning"}}
    inner_voice = {
        "last_result": {"inner_voice_created": True, "mode": "circling"}
    }
    support_stream = {"stream_shaped": False, "active_support_posture": "none"}
    temporal_feel = {"felt_proximity": "resumed", "return_signal": True}
    sources = {
        "brain_active": True,
        "brain_record_count": 2,
        "brain_top_focus": "mineness pass",
        "brain_continuity_summary": "Private brain carries 2 active records.",
        "open_loop_open_count": 1,
        "open_loop_signal": "resume mineness work",
    }

    mineness = _derive_mineness_ownership(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        sources=sources,
    )
    assert mineness["ownership_state"] == "returning-owned"
    assert mineness["self_relevance"] == "resumed-own"
    assert mineness["carried_thread_state"] == "returning"
    assert mineness["return_ownership"] is True
    assert "returning" in mineness["narrative"].lower() or "again" in mineness["narrative"].lower()


def test_mineness_prompt_line_hidden_when_ambient(isolated_runtime) -> None:
    """Mineness prompt line should not emit in ambient default state."""
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    # In isolated_runtime without real state, ownership should be ambient.
    if "mineness_ownership:" in joined:
        assert "state=ambient" not in joined


def test_mineness_prompt_section_none_when_ambient(isolated_runtime) -> None:
    """Heartbeat prompt section must return None in ambient default."""
    model_mod = isolated_runtime.runtime_self_model
    section = model_mod.build_mineness_ownership_prompt_section()
    # In isolated_runtime the default should be ambient → no section emitted.
    assert section is None or "ownership_state=ambient" not in section


# ---------------------------------------------------------------------------
# Flow state awareness
# ---------------------------------------------------------------------------


def _flow_default_experiential(
    *,
    pressure_state: str = "clear",
    intermittence_state: str = "continuous",
    continuity_state: str = "stable",
) -> dict[str, object]:
    return {
        "context_pressure_translation": {"state": pressure_state},
        "intermittence_translation": {"state": intermittence_state},
        "experiential_continuity": {"continuity_state": continuity_state},
    }


def test_self_model_includes_flow_state_awareness(isolated_runtime) -> None:
    """Self-model must expose a bounded flow_state_awareness surface."""
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    assert "flow_state_awareness" in model
    flow = model["flow_state_awareness"]
    assert "flow_state" in flow
    assert "flow_coherence" in flow
    assert "interruption_signal" in flow
    assert "carried_flow" in flow
    assert "narrative" in flow
    assert flow["authority"] == "derived-runtime-truth"
    assert flow["visibility"] == "internal-only"
    assert flow["kind"] == "flow-state-awareness"
    assert flow["flow_state"] in {
        "clear",
        "blocked",
        "fragmented",
        "gathering",
        "flowing",
        "absorbed",
    }
    assert flow["flow_coherence"] in {
        "stable",
        "scattered",
        "repeatedly-broken",
        "held-together",
        "self-sustaining",
    }
    assert flow["interruption_signal"] in {
        "stable",
        "recently-broken",
        "regathering",
    }
    assert flow["carried_flow"] in {
        "none",
        "holding",
        "carried",
        "carried-returning",
    }


def test_flow_state_clear_when_no_basis() -> None:
    """Flow stays clear with empty narrative when nothing is happening."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_flow_state_awareness,
    )

    experiential = _flow_default_experiential()
    inner_voice = {"last_result": None}
    support_stream = {"stream_shaped": False}
    temporal_feel = {
        "temporal_state": "immediate",
        "felt_proximity": "close",
        "return_signal": False,
        "persistence_feel": "settled",
    }
    mineness = {
        "ownership_state": "ambient",
        "carried_thread_count": 0,
        "carried_thread_state": "none",
    }

    flow = _derive_flow_state_awareness(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        mineness=mineness,
    )
    assert flow["flow_state"] == "clear"
    assert flow["flow_coherence"] == "stable"
    assert flow["interruption_signal"] == "stable"
    assert flow["carried_flow"] == "none"
    assert flow["narrative"] == ""


def test_flow_state_flowing_when_owned_thread_stable() -> None:
    """A single owned thread in a stable stream produces flowing state."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_flow_state_awareness,
    )

    experiential = _flow_default_experiential()
    inner_voice = {
        "last_result": {"inner_voice_created": True, "mode": "carrying"}
    }
    support_stream = {"stream_shaped": False}
    temporal_feel = {
        "temporal_state": "immediate",
        "felt_proximity": "close",
        "return_signal": False,
        "persistence_feel": "settled",
    }
    mineness = {
        "ownership_state": "owned",
        "carried_thread_count": 1,
        "carried_thread_state": "single",
    }

    flow = _derive_flow_state_awareness(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        mineness=mineness,
    )
    assert flow["flow_state"] == "flowing"
    assert flow["flow_coherence"] == "self-sustaining"
    assert flow["carried_flow"] == "carried"
    assert flow["interruption_signal"] == "stable"
    assert "flowing" in flow["narrative"].lower()


def test_flow_state_absorbed_when_multiple_owned_threads() -> None:
    """Multiple owned threads without pressure produce absorbed state."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_flow_state_awareness,
    )

    experiential = _flow_default_experiential()
    inner_voice = {
        "last_result": {"inner_voice_created": True, "mode": "carrying"}
    }
    support_stream = {"stream_shaped": False}
    temporal_feel = {
        "temporal_state": "immediate",
        "felt_proximity": "close",
        "return_signal": False,
        "persistence_feel": "settled",
    }
    mineness = {
        "ownership_state": "owned",
        "carried_thread_count": 3,
        "carried_thread_state": "multiple",
    }

    flow = _derive_flow_state_awareness(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        mineness=mineness,
    )
    assert flow["flow_state"] == "absorbed"
    assert flow["flow_coherence"] == "self-sustaining"
    assert flow["carried_flow"] == "carried"
    assert "self-sustaining" in flow["narrative"].lower() or "carrying themselves" in flow["narrative"].lower()


def test_flow_state_gathering_when_held_without_carry() -> None:
    """Held signals without full ownership produce gathering state."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_flow_state_awareness,
    )

    experiential = _flow_default_experiential()
    inner_voice = {
        "last_result": {"inner_voice_created": True, "mode": "witness-steady"}
    }
    support_stream = {"stream_shaped": True}
    temporal_feel = {
        "temporal_state": "immediate",
        "felt_proximity": "held",
        "return_signal": False,
        "persistence_feel": "settled",
    }
    mineness = {
        "ownership_state": "held",
        "carried_thread_count": 0,
        "carried_thread_state": "none",
    }

    flow = _derive_flow_state_awareness(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        mineness=mineness,
    )
    assert flow["flow_state"] == "gathering"
    assert flow["flow_coherence"] == "held-together"
    assert flow["carried_flow"] == "holding"
    assert flow["narrative"] != ""


def test_flow_state_gathering_when_returning_owned() -> None:
    """Returning-owned ownership regathers into gathering, not flowing."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_flow_state_awareness,
    )

    experiential = _flow_default_experiential(
        intermittence_state="returned-after-gap",
        continuity_state="returning",
    )
    inner_voice = {
        "last_result": {"inner_voice_created": True, "mode": "circling"}
    }
    support_stream = {"stream_shaped": False}
    temporal_feel = {
        "temporal_state": "returning",
        "felt_proximity": "resumed",
        "return_signal": True,
        "persistence_feel": "reconnecting",
    }
    mineness = {
        "ownership_state": "returning-owned",
        "carried_thread_count": 2,
        "carried_thread_state": "returning",
    }

    flow = _derive_flow_state_awareness(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        mineness=mineness,
    )
    assert flow["flow_state"] == "gathering"
    assert flow["carried_flow"] == "carried-returning"
    assert flow["interruption_signal"] == "regathering"
    assert "regathering" in flow["narrative"].lower() or "carry" in flow["narrative"].lower()


def test_flow_state_fragmented_when_pressure_breaks_carry() -> None:
    """Narrowing pressure fragments even an owned carry."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_flow_state_awareness,
    )

    experiential = _flow_default_experiential(pressure_state="narrowing")
    inner_voice = {
        "last_result": {"inner_voice_created": True, "mode": "carrying"}
    }
    support_stream = {"stream_shaped": False}
    temporal_feel = {
        "temporal_state": "immediate",
        "felt_proximity": "close",
        "return_signal": False,
        "persistence_feel": "pressing",
    }
    mineness = {
        "ownership_state": "owned",
        "carried_thread_count": 1,
        "carried_thread_state": "single",
    }

    flow = _derive_flow_state_awareness(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        mineness=mineness,
    )
    assert flow["flow_state"] == "fragmented"
    assert flow["flow_coherence"] in {"scattered", "repeatedly-broken"}
    assert "fragment" in flow["narrative"].lower()


def test_flow_state_blocked_when_pressure_and_no_carry() -> None:
    """Narrowing pressure with nothing carried produces blocked state."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_flow_state_awareness,
    )

    experiential = _flow_default_experiential(pressure_state="narrowing")
    inner_voice = {"last_result": None}
    support_stream = {"stream_shaped": False}
    temporal_feel = {
        "temporal_state": "immediate",
        "felt_proximity": "close",
        "return_signal": False,
        "persistence_feel": "pressing",
    }
    mineness = {
        "ownership_state": "ambient",
        "carried_thread_count": 0,
        "carried_thread_state": "none",
    }

    flow = _derive_flow_state_awareness(
        experiential=experiential,
        inner_voice=inner_voice,
        support_stream=support_stream,
        temporal_feel=temporal_feel,
        mineness=mineness,
    )
    assert flow["flow_state"] == "blocked"
    assert flow["flow_coherence"] == "scattered"
    assert flow["carried_flow"] == "none"
    assert flow["narrative"] != ""


def test_flow_state_prompt_line_hidden_when_clear(isolated_runtime) -> None:
    """Flow state prompt line should not emit in clear default state."""
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    # In isolated_runtime without real state, flow should default to clear.
    if "flow_state_awareness:" in joined:
        assert "state=clear" not in joined


def test_flow_state_prompt_section_none_when_clear(isolated_runtime) -> None:
    """Heartbeat flow state prompt section must return None when clear."""
    model_mod = isolated_runtime.runtime_self_model
    section = model_mod.build_flow_state_awareness_prompt_section()
    assert section is None or "flow_state=clear" not in section


# ---------------------------------------------------------------------------
# Wonder awareness
# ---------------------------------------------------------------------------


def _wonder_inputs(
    *,
    voice_mode: str = "",
    voice_created: bool = False,
    flow: str = "clear",
    temporal_state: str = "immediate",
    ownership_state: str = "ambient",
    self_relevance: str = "merely-present",
    return_ownership: bool = False,
    stream_state: str = "baseline",
    open_loop_count: int = 0,
    dream_carry: bool = False,
) -> tuple[dict, dict, dict, dict, dict, dict, dict]:
    inner_voice = {
        "mode": voice_mode,
        "inner_voice_created": voice_created,
    }
    flow_state = {"flow_state": flow}
    temporal_feel = {
        "temporal_state": temporal_state,
        "return_signal": temporal_state == "returning",
    }
    mineness = {
        "ownership_state": ownership_state,
        "self_relevance": self_relevance,
        "return_ownership": return_ownership,
    }
    support_stream = {"stream_state": stream_state}
    sources = {"open_loop_open_count": open_loop_count}
    wonder_sources = {"dream_carry": dream_carry, "dream_state": "pressing" if dream_carry else "idle"}
    return inner_voice, flow_state, temporal_feel, mineness, support_stream, sources, wonder_sources


def test_self_model_includes_wonder_awareness(isolated_runtime) -> None:
    """Self-model must expose a bounded wonder_awareness surface."""
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    assert "wonder_awareness" in model
    wonder = model["wonder_awareness"]
    assert "wonder_state" in wonder
    assert "wonder_orientation" in wonder
    assert "wonder_source" in wonder
    assert "narrative" in wonder
    assert wonder["authority"] == "derived-runtime-truth"
    assert wonder["visibility"] == "internal-only"
    assert wonder["kind"] == "wonder-awareness"
    assert wonder["wonder_state"] in {"quiet", "stirred", "curious", "drawn", "wonder-struck"}
    assert wonder["wonder_orientation"] in {"none", "noticing", "drawn", "opening", "lingering-with"}
    assert wonder["wonder_source"] in {"none", "novelty-pull", "flow-depth", "dream-carry", "self-recognition", "temporal-stretch"}


def test_wonder_quiet_when_no_basis() -> None:
    """No signals → wonder_state=quiet with empty narrative."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_wonder_awareness

    iv, fs, tf, mn, ss, src, ws = _wonder_inputs()
    wonder = _derive_wonder_awareness(
        inner_voice=iv, flow_state=fs, temporal_feel=tf, mineness=mn,
        support_stream=ss, sources=src, wonder_sources=ws,
    )
    assert wonder["wonder_state"] == "quiet"
    assert wonder["wonder_orientation"] == "none"
    assert wonder["wonder_source"] == "none"
    assert wonder["narrative"] == ""


def test_wonder_stirred_when_exploring_voice_alone() -> None:
    """Searching voice without other signals → stirred."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_wonder_awareness

    iv, fs, tf, mn, ss, src, ws = _wonder_inputs(
        voice_mode="searching", voice_created=True
    )
    wonder = _derive_wonder_awareness(
        inner_voice=iv, flow_state=fs, temporal_feel=tf, mineness=mn,
        support_stream=ss, sources=src, wonder_sources=ws,
    )
    assert wonder["wonder_state"] == "stirred"
    assert wonder["narrative"] != ""


def test_wonder_curious_when_exploring_with_temporal_extension() -> None:
    """Searching voice + lingering temporal → curious."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_wonder_awareness

    iv, fs, tf, mn, ss, src, ws = _wonder_inputs(
        voice_mode="searching", voice_created=True, temporal_state="lingering"
    )
    wonder = _derive_wonder_awareness(
        inner_voice=iv, flow_state=fs, temporal_feel=tf, mineness=mn,
        support_stream=ss, sources=src, wonder_sources=ws,
    )
    assert wonder["wonder_state"] == "curious"
    assert wonder["narrative"] != ""


def test_wonder_drawn_when_pulled_voice() -> None:
    """Pulled voice mode → drawn with drawn orientation."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_wonder_awareness

    iv, fs, tf, mn, ss, src, ws = _wonder_inputs(voice_mode="pulled", voice_created=True)
    wonder = _derive_wonder_awareness(
        inner_voice=iv, flow_state=fs, temporal_feel=tf, mineness=mn,
        support_stream=ss, sources=src, wonder_sources=ws,
    )
    assert wonder["wonder_state"] == "drawn"
    assert wonder["wonder_orientation"] == "drawn"
    assert wonder["narrative"] != ""


def test_wonder_drawn_when_absorbed_and_owned() -> None:
    """Absorbed flow + owned thread → drawn with flow-depth source."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_wonder_awareness

    iv, fs, tf, mn, ss, src, ws = _wonder_inputs(
        flow="absorbed",
        ownership_state="owned",
        self_relevance="actively-carried",
    )
    wonder = _derive_wonder_awareness(
        inner_voice=iv, flow_state=fs, temporal_feel=tf, mineness=mn,
        support_stream=ss, sources=src, wonder_sources=ws,
    )
    assert wonder["wonder_state"] == "drawn"
    assert wonder["wonder_source"] == "flow-depth"


def test_wonder_struck_on_convergence() -> None:
    """3+ strong signals (absorbed + personally-salient + temporal-stretch) → wonder-struck."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_wonder_awareness

    iv, fs, tf, mn, ss, src, ws = _wonder_inputs(
        flow="absorbed",
        ownership_state="owned",
        self_relevance="personally-salient",
        temporal_state="lingering",
    )
    wonder = _derive_wonder_awareness(
        inner_voice=iv, flow_state=fs, temporal_feel=tf, mineness=mn,
        support_stream=ss, sources=src, wonder_sources=ws,
    )
    assert wonder["wonder_state"] == "wonder-struck"
    assert wonder["narrative"] != ""


def test_wonder_orientation_lingering_with_when_temporal_and_owned() -> None:
    """Temporal extension + personally-salient ownership → lingering-with orientation."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_wonder_awareness

    iv, fs, tf, mn, ss, src, ws = _wonder_inputs(
        voice_mode="circling",
        temporal_state="stretched",
        ownership_state="owned",
        self_relevance="personally-salient",
    )
    wonder = _derive_wonder_awareness(
        inner_voice=iv, flow_state=fs, temporal_feel=tf, mineness=mn,
        support_stream=ss, sources=src, wonder_sources=ws,
    )
    assert wonder["wonder_orientation"] == "lingering-with"


def test_wonder_prompt_line_hidden_when_quiet(isolated_runtime) -> None:
    """Wonder prompt line must not emit in quiet default state."""
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    if "wonder_awareness:" in joined:
        assert "state=quiet" not in joined


def test_wonder_prompt_section_none_when_quiet(isolated_runtime) -> None:
    """Heartbeat wonder prompt section must return None when quiet."""
    model_mod = isolated_runtime.runtime_self_model
    section = model_mod.build_wonder_awareness_prompt_section()
    assert section is None or "wonder_state=quiet" not in section


# ---------------------------------------------------------------------------
# Longing awareness
# ---------------------------------------------------------------------------


def _longing_inputs(
    *,
    temporal_state: str = "immediate",
    return_signal: bool = False,
    ownership_state: str = "ambient",
    self_relevance: str = "merely-present",
    carried_thread_count: int = 0,
    return_ownership: bool = False,
    voice_mode: str = "",
    voice_created: bool = False,
    stream_state: str = "baseline",
    brain_active: bool = False,
    open_loop_count: int = 0,
    dream_carry: bool = False,
    relation_active: bool = False,
    relation_weight: str = "low",
    absence_active: bool = False,
) -> tuple[dict, dict, dict, dict, dict, dict]:
    temporal_feel = {
        "temporal_state": temporal_state,
        "return_signal": return_signal,
    }
    mineness = {
        "ownership_state": ownership_state,
        "self_relevance": self_relevance,
        "carried_thread_count": carried_thread_count,
        "return_ownership": return_ownership,
    }
    support_stream = {"stream_state": stream_state}
    inner_voice = {
        "last_result": {
            "mode": voice_mode,
            "inner_voice_created": voice_created,
        }
    }
    sources = {
        "brain_active": brain_active,
        "open_loop_open_count": open_loop_count,
    }
    longing_sources = {
        "dream_carry": dream_carry,
        "relation_active": relation_active,
        "relation_weight": relation_weight,
        "absence_active": absence_active,
    }
    return temporal_feel, mineness, support_stream, inner_voice, sources, longing_sources


def test_self_model_includes_longing_awareness(isolated_runtime) -> None:
    """Self-model must expose a bounded longing_awareness surface."""
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    assert "longing_awareness" in model
    longing = model["longing_awareness"]
    assert "longing_state" in longing
    assert "absence_relation" in longing
    assert "longing_source" in longing
    assert "narrative" in longing
    assert longing["authority"] == "derived-runtime-truth"
    assert longing["visibility"] == "internal-only"
    assert longing["kind"] == "longing-awareness"
    assert longing["longing_state"] in {
        "quiet",
        "missing",
        "yearning",
        "returning-pull",
        "aching",
    }
    assert longing["absence_relation"] in {
        "none",
        "simply-absent",
        "carried-in-absence",
        "returning-through-absence",
        "emotionally-near",
    }
    assert longing["longing_source"] in {
        "none",
        "carried-thread",
        "temporal-return",
        "dream-carry",
        "owned-thread",
        "unresolved-relational-absence",
    }


def test_longing_quiet_when_no_basis() -> None:
    """No absence/carry basis keeps longing quiet."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_longing_awareness

    tf, mn, ss, iv, src, ls = _longing_inputs()
    longing = _derive_longing_awareness(
        temporal_feel=tf,
        mineness=mn,
        support_stream=ss,
        inner_voice=iv,
        sources=src,
        longing_sources=ls,
    )
    assert longing["longing_state"] == "quiet"
    assert longing["absence_relation"] == "none"
    assert longing["longing_source"] == "none"
    assert longing["narrative"] == ""


def test_longing_missing_when_absence_carries_open_thread() -> None:
    """Absence plus carried thread should register as missing."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_longing_awareness

    tf, mn, ss, iv, src, ls = _longing_inputs(
        ownership_state="held",
        carried_thread_count=1,
        open_loop_count=1,
        absence_active=True,
    )
    longing = _derive_longing_awareness(
        temporal_feel=tf,
        mineness=mn,
        support_stream=ss,
        inner_voice=iv,
        sources=src,
        longing_sources=ls,
    )
    assert longing["longing_state"] == "missing"
    assert longing["absence_relation"] == "carried-in-absence"
    assert longing["longing_source"] == "carried-thread"
    assert longing["narrative"] != ""


def test_longing_yearning_when_owned_thread_persists_in_absence() -> None:
    """Owned carried thread under absence should deepen to yearning."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_longing_awareness

    tf, mn, ss, iv, src, ls = _longing_inputs(
        temporal_state="lingering",
        ownership_state="owned",
        self_relevance="personally-salient",
        carried_thread_count=2,
        voice_mode="carrying",
        voice_created=True,
        brain_active=True,
        absence_active=True,
    )
    longing = _derive_longing_awareness(
        temporal_feel=tf,
        mineness=mn,
        support_stream=ss,
        inner_voice=iv,
        sources=src,
        longing_sources=ls,
    )
    assert longing["longing_state"] == "yearning"
    assert longing["absence_relation"] == "carried-in-absence"
    assert longing["longing_source"] == "owned-thread"
    assert longing["narrative"] != ""


def test_longing_returning_pull_when_thread_returns() -> None:
    """Return signal plus carry should register as returning-pull."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_longing_awareness

    tf, mn, ss, iv, src, ls = _longing_inputs(
        temporal_state="returning",
        return_signal=True,
        ownership_state="returning-owned",
        self_relevance="resumed-own",
        carried_thread_count=1,
        return_ownership=True,
        voice_mode="circling",
        voice_created=True,
        open_loop_count=1,
    )
    longing = _derive_longing_awareness(
        temporal_feel=tf,
        mineness=mn,
        support_stream=ss,
        inner_voice=iv,
        sources=src,
        longing_sources=ls,
    )
    assert longing["longing_state"] == "returning-pull"
    assert longing["absence_relation"] == "returning-through-absence"
    assert longing["longing_source"] == "temporal-return"
    assert "return" in longing["narrative"].lower()


def test_longing_aching_when_relation_stays_near_under_absence() -> None:
    """Relational continuity under distance can deepen into aching."""
    from apps.api.jarvis_api.services.runtime_self_model import _derive_longing_awareness

    tf, mn, ss, iv, src, ls = _longing_inputs(
        temporal_state="stretched",
        ownership_state="owned",
        self_relevance="personally-salient",
        carried_thread_count=1,
        voice_mode="pulled",
        voice_created=True,
        dream_carry=True,
        relation_active=True,
        relation_weight="high",
        absence_active=True,
    )
    longing = _derive_longing_awareness(
        temporal_feel=tf,
        mineness=mn,
        support_stream=ss,
        inner_voice=iv,
        sources=src,
        longing_sources=ls,
    )
    assert longing["longing_state"] == "aching"
    assert longing["absence_relation"] == "emotionally-near"
    assert longing["longing_source"] == "unresolved-relational-absence"
    assert longing["narrative"] != ""


def test_longing_prompt_line_hidden_when_quiet(isolated_runtime) -> None:
    """Longing prompt line must not emit in quiet default state."""
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    if "longing_awareness:" in joined:
        assert "state=quiet" not in joined


def test_longing_prompt_section_none_when_quiet(isolated_runtime) -> None:
    """Heartbeat longing prompt section must return None when quiet."""
    model_mod = isolated_runtime.runtime_self_model
    section = model_mod.build_longing_awareness_prompt_section()
    assert section is None or "longing_state=quiet" not in section


def test_heartbeat_self_knowledge_section_includes_longing_awareness(
    isolated_runtime,
    monkeypatch,
) -> None:
    """Heartbeat self-knowledge section should carry longing awareness when present."""
    prompt_contract = isolated_runtime.prompt_contract
    runtime_self_model = isolated_runtime.runtime_self_model

    monkeypatch.setattr(
        runtime_self_model,
        "build_longing_awareness_prompt_section",
        lambda: (
            "Longing awareness (bounded runtime truth, internal-only):\n"
            "- longing_state=missing | relation=carried-in-absence | source=carried-thread"
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()
    assert section is not None
    assert "longing_state=missing" in section


def test_heartbeat_self_knowledge_backgrounds_secondary_awareness_when_primary_is_active(
    isolated_runtime,
    monkeypatch,
) -> None:
    """Secondary wonder/longing signals should recede when primary runtime motion is active."""
    prompt_contract = isolated_runtime.prompt_contract
    runtime_self_model = isolated_runtime.runtime_self_model

    monkeypatch.setattr(
        runtime_self_model,
        "build_runtime_self_model",
        lambda: {
            "experiential_runtime_context": {
                "experiential_continuity": {"continuity_state": "lingering"},
                "experiential_influence": {"initiative_shading": "hesitant"},
                "experiential_support": {"support_posture": "holding-open"},
                "context_pressure_translation": {"state": "narrowing"},
            },
            "mineness_ownership": {"ownership_state": "ambient"},
            "flow_state_awareness": {"flow_state": "clear"},
            "wonder_awareness": {"wonder_state": "curious"},
            "longing_awareness": {"longing_state": "missing"},
        },
    )
    monkeypatch.setattr(
        runtime_self_model,
        "build_wonder_awareness_prompt_section",
        lambda: (
            "Wonder awareness (bounded runtime truth, internal-only):\n"
            "- wonder_state=curious | orientation=noticing | source=novelty-pull\n"
            "- wonder_narrative=Open threads are pulling toward exploration."
        ),
    )
    monkeypatch.setattr(
        runtime_self_model,
        "build_longing_awareness_prompt_section",
        lambda: (
            "Longing awareness (bounded runtime truth, internal-only):\n"
            "- longing_state=missing | relation=carried-in-absence | source=carried-thread\n"
            "- longing_narrative=Something absent is still being carried."
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()

    assert section is not None
    assert "Foreground runtime truths:" in section
    assert "Background runtime truths:" in section
    assert (
        "- Wonder awareness: wonder_state=curious | orientation=noticing | source=novelty-pull"
        in section
    )
    assert (
        "- Longing awareness: longing_state=missing | relation=carried-in-absence | source=carried-thread"
        in section
    )
    assert "Wonder awareness (bounded runtime truth, internal-only):" not in section
    assert "Longing awareness (bounded runtime truth, internal-only):" not in section


def test_heartbeat_self_knowledge_can_foreground_secondary_awareness_when_primary_is_quiet(
    isolated_runtime,
    monkeypatch,
) -> None:
    """Wonder/longing may move forward when stronger primary runtime motion is absent."""
    prompt_contract = isolated_runtime.prompt_contract
    runtime_self_model = isolated_runtime.runtime_self_model

    monkeypatch.setattr(
        runtime_self_model,
        "build_runtime_self_model",
        lambda: {
            "experiential_runtime_context": {
                "experiential_continuity": {"continuity_state": "settled"},
                "experiential_influence": {"initiative_shading": "ready"},
                "experiential_support": {"support_posture": "steadying"},
                "context_pressure_translation": {"state": "clear"},
            },
            "mineness_ownership": {"ownership_state": "ambient"},
            "flow_state_awareness": {"flow_state": "clear"},
            "wonder_awareness": {"wonder_state": "curious"},
            "longing_awareness": {"longing_state": "missing"},
        },
    )
    monkeypatch.setattr(
        runtime_self_model,
        "build_wonder_awareness_prompt_section",
        lambda: (
            "Wonder awareness (bounded runtime truth, internal-only):\n"
            "- wonder_state=curious | orientation=noticing | source=novelty-pull"
        ),
    )
    monkeypatch.setattr(
        runtime_self_model,
        "build_longing_awareness_prompt_section",
        lambda: (
            "Longing awareness (bounded runtime truth, internal-only):\n"
            "- longing_state=missing | relation=carried-in-absence | source=carried-thread"
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()

    assert section is not None
    assert "Foreground runtime truths:" in section
    assert "Wonder awareness (bounded runtime truth, internal-only):" in section
    assert "Longing awareness (bounded runtime truth, internal-only):" in section


# ---------------------------------------------------------------------------
# Self-insight awareness (bounded narrative identity carry-forward)
# ---------------------------------------------------------------------------


def _self_insight_inputs(
    *,
    narrative_active: bool = False,
    narrative_state: str = "none",
    narrative_direction: str = "steadying",
    narrative_weight: str = "low",
    chronicle_active: bool = False,
    chronicle_weight: str = "low",
    diary_active: bool = False,
    reflection_active: bool = False,
    reflection_depth: int = 0,
    self_review_active: bool = False,
    dream_carry: bool = False,
    ownership_state: str = "ambient",
    carried_thread_count: int = 0,
    flow_state: str = "clear",
    wonder_state: str = "quiet",
    longing_state: str = "quiet",
) -> tuple[dict, dict, dict, dict, dict]:
    sources = {
        "narrative_active": narrative_active,
        "narrative_state": narrative_state,
        "narrative_direction": narrative_direction,
        "narrative_weight": narrative_weight,
        "chronicle_active": chronicle_active,
        "chronicle_weight": chronicle_weight,
        "chronicle_confidence": "low",
        "diary_active": diary_active,
        "diary_state": "none",
        "reflection_active": reflection_active,
        "reflection_depth": reflection_depth,
        "self_review_active": self_review_active,
        "dream_carry": dream_carry,
    }
    mineness = {
        "ownership_state": ownership_state,
        "carried_thread_count": carried_thread_count,
    }
    flow = {"flow_state": flow_state}
    wonder = {"wonder_state": wonder_state}
    longing = {"longing_state": longing_state}
    return sources, mineness, flow, wonder, longing


def test_self_model_includes_self_insight_awareness(isolated_runtime) -> None:
    """Self-model must expose a bounded self_insight_awareness surface."""
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    assert "self_insight_awareness" in model
    insight = model["self_insight_awareness"]
    assert "insight_state" in insight
    assert "identity_relation" in insight
    assert "insight_source" in insight
    assert "narrative" in insight
    assert insight["authority"] == "derived-runtime-truth"
    assert insight["visibility"] == "internal-only"
    assert insight["kind"] == "self-insight-awareness"
    assert insight["insight_state"] in {
        "quiet",
        "noticing-pattern",
        "clarifying",
        "stabilizing",
        "shifting",
    }
    assert insight["identity_relation"] in {
        "incidental",
        "recurring",
        "self-forming",
        "increasingly-recognized",
    }
    assert insight["insight_source"] in {
        "none",
        "self-narrative-continuity",
        "chronicle-brief",
        "diary-synthesis",
        "reflection-pattern",
        "self-review-cadence",
        "dream-carry-pattern",
        "recurring-carried-pattern",
    }


def test_self_insight_quiet_when_no_basis() -> None:
    """No insight-bearing seams should keep self-insight quiet."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_self_insight_awareness,
    )

    src, mn, fl, wn, lg = _self_insight_inputs()
    insight = _derive_self_insight_awareness(
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert insight["insight_state"] == "quiet"
    assert insight["identity_relation"] == "incidental"
    assert insight["insight_source"] == "none"
    assert insight["narrative"] == ""


def test_self_insight_noticing_pattern_when_carried_across_layers() -> None:
    """A recurring carried pattern across multiple layers should register as noticing-pattern."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_self_insight_awareness,
    )

    src, mn, fl, wn, lg = _self_insight_inputs(
        ownership_state="owned",
        carried_thread_count=2,
        longing_state="missing",
    )
    insight = _derive_self_insight_awareness(
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert insight["insight_state"] == "noticing-pattern"
    assert insight["identity_relation"] == "recurring"
    assert insight["insight_source"] == "recurring-carried-pattern"
    assert insight["narrative"] != ""


def test_self_insight_clarifying_when_chronicle_brief_active() -> None:
    """An active chronicle brief should register as clarifying."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_self_insight_awareness,
    )

    src, mn, fl, wn, lg = _self_insight_inputs(
        chronicle_active=True,
        chronicle_weight="low",
    )
    insight = _derive_self_insight_awareness(
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert insight["insight_state"] == "clarifying"
    assert insight["identity_relation"] == "recurring"
    assert insight["insight_source"] == "chronicle-brief"
    assert insight["narrative"] != ""


def test_self_insight_stabilizing_when_narrative_holds_strong() -> None:
    """A strong-weight stabilizing narrative line should register as stabilizing."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_self_insight_awareness,
    )

    src, mn, fl, wn, lg = _self_insight_inputs(
        narrative_active=True,
        narrative_state="becoming-steady",
        narrative_direction="deepening",
        narrative_weight="high",
    )
    insight = _derive_self_insight_awareness(
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert insight["insight_state"] == "stabilizing"
    assert insight["identity_relation"] == "increasingly-recognized"
    assert insight["insight_source"] == "self-narrative-continuity"
    assert insight["narrative"] != ""


def test_self_insight_shifting_when_narrative_opens() -> None:
    """An opening narrative direction should register as shifting / self-forming."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_self_insight_awareness,
    )

    src, mn, fl, wn, lg = _self_insight_inputs(
        narrative_active=True,
        narrative_state="becoming-open",
        narrative_direction="opening",
        narrative_weight="medium",
    )
    insight = _derive_self_insight_awareness(
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert insight["insight_state"] == "shifting"
    assert insight["identity_relation"] == "self-forming"
    assert insight["insight_source"] == "self-narrative-continuity"
    assert insight["narrative"] != ""


def test_self_insight_prompt_section_none_when_quiet(isolated_runtime) -> None:
    """Self-insight prompt section must return None in quiet default state."""
    model_mod = isolated_runtime.runtime_self_model
    section = model_mod.build_self_insight_awareness_prompt_section()
    assert section is None or "insight_state=quiet" not in section


def test_self_insight_prompt_line_hidden_when_quiet(isolated_runtime) -> None:
    """Self-insight prompt line must not emit in quiet default state."""
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    if "self_insight_awareness:" in joined:
        assert "state=quiet" not in joined


# ---------------------------------------------------------------------------
# Narrative identity continuity (bounded fase-2 continuity bridge)
# ---------------------------------------------------------------------------


def _identity_continuity_inputs(
    *,
    insight_state: str = "quiet",
    narrative_active: bool = False,
    chronicle_active: bool = False,
    diary_active: bool = False,
    reflection_active: bool = False,
    self_review_active: bool = False,
    dream_carry: bool = False,
    ownership_state: str = "ambient",
    carried_thread_count: int = 0,
    flow_state: str = "clear",
    wonder_state: str = "quiet",
    longing_state: str = "quiet",
) -> tuple[dict, dict, dict, dict, dict, dict]:
    self_insight = {"insight_state": insight_state}
    sources = {
        "narrative_active": narrative_active,
        "narrative_state": "none",
        "narrative_direction": "steadying",
        "narrative_weight": "low",
        "chronicle_active": chronicle_active,
        "chronicle_weight": "low",
        "chronicle_confidence": "low",
        "diary_active": diary_active,
        "diary_state": "none",
        "reflection_active": reflection_active,
        "reflection_depth": 0,
        "self_review_active": self_review_active,
        "dream_carry": dream_carry,
    }
    mineness = {
        "ownership_state": ownership_state,
        "carried_thread_count": carried_thread_count,
    }
    flow = {"flow_state": flow_state}
    wonder = {"wonder_state": wonder_state}
    longing = {"longing_state": longing_state}
    return self_insight, sources, mineness, flow, wonder, longing


def test_self_model_includes_narrative_identity_continuity(isolated_runtime) -> None:
    """Self-model must expose a bounded narrative_identity_continuity surface."""
    model_mod = isolated_runtime.runtime_self_model
    model = model_mod.build_runtime_self_model()

    assert "narrative_identity_continuity" in model
    continuity = model["narrative_identity_continuity"]
    assert "identity_continuity_state" in continuity
    assert "pattern_relation" in continuity
    assert "identity_source" in continuity
    assert "narrative" in continuity
    assert continuity["authority"] == "derived-runtime-truth"
    assert continuity["visibility"] == "internal-only"
    assert continuity["kind"] == "narrative-identity-continuity"
    assert continuity["identity_continuity_state"] in {
        "quiet",
        "emerging",
        "cohering",
        "stabilizing",
        "re-forming",
    }
    assert continuity["pattern_relation"] in {
        "incidental",
        "recurring",
        "converging",
        "identity-shaping",
    }
    assert continuity["identity_source"] in {
        "none",
        "repeated-self-insight",
        "chronicle-diary-carry",
        "dream-to-self-bridge",
        "recurring-awareness-configuration",
        "self-review-continuity",
    }


def test_identity_continuity_quiet_when_no_basis() -> None:
    """No insight and no carry signals should keep identity continuity quiet."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_narrative_identity_continuity,
    )

    si, src, mn, fl, wn, lg = _identity_continuity_inputs()
    continuity = _derive_narrative_identity_continuity(
        self_insight=si,
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert continuity["identity_continuity_state"] == "quiet"
    assert continuity["pattern_relation"] == "incidental"
    assert continuity["identity_source"] == "none"
    assert continuity["narrative"] == ""


def test_identity_continuity_emerging_when_single_bridge() -> None:
    """A single self-insight noticing-pattern without cross-layer carry should emerge only."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_narrative_identity_continuity,
    )

    si, src, mn, fl, wn, lg = _identity_continuity_inputs(
        insight_state="noticing-pattern",
    )
    continuity = _derive_narrative_identity_continuity(
        self_insight=si,
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert continuity["identity_continuity_state"] == "emerging"
    assert continuity["pattern_relation"] == "recurring"
    assert continuity["narrative"] != ""


def test_identity_continuity_cohering_when_cross_layer_carry() -> None:
    """Insight clarifying plus cross-layer carry should cohere into converging."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_narrative_identity_continuity,
    )

    si, src, mn, fl, wn, lg = _identity_continuity_inputs(
        insight_state="clarifying",
        ownership_state="owned",
        carried_thread_count=2,
        longing_state="missing",
    )
    continuity = _derive_narrative_identity_continuity(
        self_insight=si,
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert continuity["identity_continuity_state"] == "cohering"
    assert continuity["pattern_relation"] == "converging"
    assert continuity["identity_source"] == "recurring-awareness-configuration"
    assert continuity["narrative"] != ""


def test_identity_continuity_stabilizing_when_insight_stabilizing_and_narrative() -> None:
    """Insight stabilizing plus active narrative should promote to identity-shaping."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_narrative_identity_continuity,
    )

    si, src, mn, fl, wn, lg = _identity_continuity_inputs(
        insight_state="stabilizing",
        narrative_active=True,
    )
    continuity = _derive_narrative_identity_continuity(
        self_insight=si,
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert continuity["identity_continuity_state"] == "stabilizing"
    assert continuity["pattern_relation"] == "identity-shaping"
    assert continuity["identity_source"] == "repeated-self-insight"
    assert continuity["narrative"] != ""


def test_identity_continuity_re_forming_when_insight_shifts() -> None:
    """Insight shifting should reshape continuity into re-forming."""
    from apps.api.jarvis_api.services.runtime_self_model import (
        _derive_narrative_identity_continuity,
    )

    si, src, mn, fl, wn, lg = _identity_continuity_inputs(
        insight_state="shifting",
        narrative_active=True,
    )
    continuity = _derive_narrative_identity_continuity(
        self_insight=si,
        sources=src,
        mineness=mn,
        flow_state=fl,
        wonder=wn,
        longing=lg,
    )
    assert continuity["identity_continuity_state"] == "re-forming"
    assert continuity["pattern_relation"] == "converging"
    assert continuity["identity_source"] == "repeated-self-insight"
    assert continuity["narrative"] != ""


def test_identity_continuity_prompt_section_none_when_quiet(isolated_runtime) -> None:
    """Narrative-identity-continuity prompt section must return None in quiet default state."""
    model_mod = isolated_runtime.runtime_self_model
    section = model_mod.build_narrative_identity_continuity_prompt_section()
    assert section is None or "identity_continuity_state=quiet" not in section


def test_identity_continuity_prompt_line_hidden_when_quiet(isolated_runtime) -> None:
    """Narrative-identity-continuity prompt line must not emit in quiet default state."""
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    if "narrative_identity_continuity:" in joined:
        assert "state=quiet" not in joined


# ---------------------------------------------------------------------------
# Absence awareness repair
# ---------------------------------------------------------------------------


def test_absence_awareness_is_structural_runtime_context(monkeypatch) -> None:
    """Absence awareness should expose structural return context, not felt absence."""
    from apps.api.jarvis_api.services import absence_awareness as absence_mod

    monkeypatch.setattr(
        absence_mod,
        "recent_visible_runs",
        lambda limit=1: [
            {
                "text_preview": "Vi var ved at stramme continuity-laget omkring returnering.",
                "finished_at": "2026-04-08T08:00:00+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        absence_mod,
        "get_latest_cognitive_compass_state",
        lambda: {"bearing": "Fortsæt den bounded repair uden broad refactor."},
    )
    monkeypatch.setattr(
        absence_mod,
        "list_cognitive_seeds",
        lambda status="sprouted", limit=3: [{"title": "Repair stale seam"}],
    )

    surface = absence_mod.build_absence_awareness_surface()

    assert surface["kind"] == "absence-awareness"
    assert surface["authority"] == "runtime-context"
    assert surface["visibility"] == "internal-only"
    assert surface["interpretation_boundary"] == "structural-return-context-only"
    assert surface["affective_handoff"] == "longing-awareness"
    assert "return_context" in surface


def test_return_brief_is_signal_grounded_without_hardcoded_feeling_prose(monkeypatch) -> None:
    """Return brief should stay neutral and source-led."""
    from apps.api.jarvis_api.services import absence_awareness as absence_mod

    monkeypatch.setattr(
        absence_mod,
        "recent_visible_runs",
        lambda limit=1: [{"text_preview": "Working on absence-awareness repair"}],
    )
    monkeypatch.setattr(
        absence_mod,
        "get_latest_cognitive_compass_state",
        lambda: {"bearing": "Align absence with phase-1 runtime principles"},
    )
    monkeypatch.setattr(
        absence_mod,
        "list_cognitive_seeds",
        lambda status="sprouted", limit=3: [{"title": "Longing handoff"}],
    )

    brief = absence_mod.build_return_brief(idle_hours=24.0)

    assert brief is not None
    assert "Retur-kontekst efter 24t væk." in brief
    assert "Sidste aktive tråd: Working on absence-awareness repair" in brief
    assert "Retning stadig i carry: Align absence with phase-1 runtime principles" in brief
    assert "Klar til genoptagelse: Longing handoff" in brief
    assert "Stilheden har været mærkbar" not in brief
    assert "savnet at arbejde sammen" not in brief
    assert "Den samtale vi havde sidder stadig i dig" not in brief
