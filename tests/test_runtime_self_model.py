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
    assert "embodied_state" in model
    assert "loop_runtime" in model
    assert "idle_consolidation" in model
    assert "dream_articulation" in model
    assert "prompt_evolution" in model
    assert "truth_boundaries" in model
    assert "summary" in model
    assert "built_at" in model
    assert len(model["layers"]) > 0


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
    assert "loop_runtime:" in joined
    assert "idle_consolidation:" in joined
    assert "dream_articulation:" in joined
    assert "prompt_evolution:" in joined


def test_prompt_lines_distinguish_kinds(isolated_runtime) -> None:
    model_mod = isolated_runtime.runtime_self_model
    lines = model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)

    # Should have at least active_orchestration or active_capability
    assert "active_" in joined, "Prompt lines should group active layers by kind"


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
