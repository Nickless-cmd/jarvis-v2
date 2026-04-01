from __future__ import annotations


def test_adaptive_reasoning_changes_shape_from_runtime_inputs(isolated_runtime) -> None:
    reasoning = isolated_runtime.adaptive_reasoning_runtime

    constrained = reasoning.build_adaptive_reasoning_runtime_from_sources(
        embodied_state={"state": "strained", "strain_level": "high"},
        affective_meta_state={"state": "tense", "bearing": "taut"},
        epistemic_runtime_state={
            "wrongness_state": "off",
            "regret_signal": "active",
            "counterfactual_mode": "blocked-path",
        },
        loop_runtime={"summary": {"current_status": "active", "active_count": 1, "standby_count": 0}},
        council_runtime={"council_state": "checking", "recommendation": "bounded-check", "divergence_level": "medium"},
        adaptive_planner={"planner_mode": "hold", "planning_posture": "held", "risk_posture": "constrained"},
        conflict_trace={"outcome": "defer", "reason_code": "policy-blocked"},
        quiet_initiative={"active": True, "state": "holding", "hold_count": 2},
    )

    assert constrained["reasoning_mode"] == "constrained"
    assert constrained["reasoning_posture"] == "guarded"
    assert constrained["certainty_style"] == "cautious"
    assert constrained["constraint_bias"] == "strong"
    assert constrained["visibility"] == "internal-only"
    assert constrained["boundary"] == "not-memory-not-identity-not-action"

    direct = reasoning.build_adaptive_reasoning_runtime_from_sources(
        embodied_state={"state": "steady", "strain_level": "low"},
        affective_meta_state={"state": "attentive", "bearing": "forward"},
        epistemic_runtime_state={
            "wrongness_state": "clear",
            "regret_signal": "none",
            "counterfactual_mode": "none",
        },
        loop_runtime={"summary": {"current_status": "active", "active_count": 2, "standby_count": 0}},
        council_runtime={"council_state": "aligned", "recommendation": "carry-forward", "divergence_level": "low"},
        adaptive_planner={"planner_mode": "forward-push", "planning_posture": "forward", "risk_posture": "balanced"},
        conflict_trace={"outcome": "continue_internal", "reason_code": "execute-continuation"},
        quiet_initiative={"active": False},
    )

    assert direct["reasoning_mode"] == "direct"
    assert direct["reasoning_posture"] == "balanced"
    assert direct["certainty_style"] == "crisp"
    assert direct["confidence"] == "high"


def test_adaptive_reasoning_prompt_section_is_grounded(isolated_runtime) -> None:
    reasoning = isolated_runtime.adaptive_reasoning_runtime

    section = reasoning.build_adaptive_reasoning_prompt_section(
        {
            "reasoning_mode": "careful",
            "reasoning_posture": "narrow",
            "certainty_style": "cautious",
            "exploration_bias": "limited",
            "constraint_bias": "moderate",
            "confidence": "medium",
            "source_contributors": [
                {"source": "epistemic-runtime-state", "signal": "off / regret=slight / counterfactual=nearby-alternative"},
                {"source": "adaptive-planner", "signal": "cautious-step / posture=narrow / risk=careful"},
            ],
            "freshness": {"state": "fresh"},
        }
    )

    assert "Adaptive reasoning light" in section
    assert "mode=careful" in section
    assert "certainty=cautious" in section
    assert "moderate" in section


def test_heartbeat_runtime_truth_instruction_includes_adaptive_reasoning(isolated_runtime) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    instruction = prompt_contract._heartbeat_runtime_truth_instruction(
        {
            "schedule_status": "scheduled",
            "budget_status": "healthy",
            "kill_switch": "enabled",
            "embodied_state": {"state": "steady", "strain_level": "low"},
            "affective_meta_state": {"state": "reflective", "bearing": "inward", "monitoring_mode": "reflective-scan"},
            "epistemic_runtime_state": {"wrongness_state": "uneasy", "regret_signal": "slight", "counterfactual_mode": "nearby-alternative"},
            "adaptive_planner": {"planner_mode": "reflective-planning", "plan_horizon": "near", "planning_posture": "reflective", "risk_posture": "careful"},
            "adaptive_reasoning": {
                "reasoning_mode": "reflective",
                "reasoning_posture": "open",
                "certainty_style": "tentative",
                "constraint_bias": "moderate",
            },
            "loop_runtime": {"summary": {"current_status": "standby", "active_count": 0, "standby_count": 1, "resumed_count": 0}},
        }
    )

    assert "adaptive_reasoning=reflective" in instruction
    assert "certainty=tentative" in instruction
    assert "constraint=moderate" in instruction


def test_mission_control_runtime_and_endpoint_expose_adaptive_reasoning(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "reasoning_mode": "reflective",
        "reasoning_posture": "open",
        "certainty_style": "tentative",
        "exploration_bias": "alternative-seeking",
        "constraint_bias": "moderate",
        "confidence": "medium",
        "summary": "reflective adaptive reasoning with tentative certainty and moderate constraint bias",
        "source_contributors": [],
        "freshness": {"built_at": "2026-04-01T20:00:00+00:00", "state": "fresh"},
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "boundary": "not-memory-not-identity-not-action",
        "kind": "adaptive-reasoning-runtime-state",
    }

    monkeypatch.setattr(
        isolated_runtime.adaptive_reasoning_runtime,
        "build_adaptive_reasoning_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_adaptive_reasoning_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.runtime_self_model,
        "_adaptive_reasoning_surface",
        lambda: runtime_surface,
    )

    endpoint = isolated_runtime.mission_control.mc_adaptive_reasoning()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["reasoning_mode"] == "reflective"
    assert runtime["runtime_adaptive_reasoning"]["constraint_bias"] == "moderate"
    assert self_model["adaptive_reasoning"]["certainty_style"] == "tentative"
