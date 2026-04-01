from __future__ import annotations


def test_adaptive_planner_changes_shape_from_runtime_inputs(isolated_runtime) -> None:
    planner = isolated_runtime.adaptive_planner_runtime

    held = planner.build_adaptive_planner_runtime_from_sources(
        embodied_state={
            "state": "strained",
            "strain_level": "high",
        },
        affective_meta_state={
            "state": "tense",
            "bearing": "taut",
        },
        epistemic_runtime_state={
            "wrongness_state": "off",
            "regret_signal": "active",
        },
        loop_runtime={
            "summary": {
                "current_status": "active",
                "active_count": 1,
                "standby_count": 0,
                "resumed_count": 0,
            }
        },
        council_runtime={
            "council_state": "checking",
            "recommendation": "bounded-check",
            "divergence_level": "medium",
        },
        conflict_trace={
            "outcome": "defer",
            "reason_code": "policy-blocked",
        },
        quiet_initiative={
            "active": True,
            "state": "holding",
            "hold_count": 2,
        },
    )

    assert held["planner_mode"] == "hold"
    assert held["plan_horizon"] == "immediate"
    assert held["risk_posture"] == "constrained"
    assert held["next_planning_bias"] == "stabilize-first"
    assert held["visibility"] == "internal-only"
    assert held["boundary"] == "not-memory-not-identity-not-action"

    forward = planner.build_adaptive_planner_runtime_from_sources(
        embodied_state={
            "state": "steady",
            "strain_level": "low",
        },
        affective_meta_state={
            "state": "attentive",
            "bearing": "forward",
        },
        epistemic_runtime_state={
            "wrongness_state": "clear",
            "regret_signal": "none",
        },
        loop_runtime={
            "summary": {
                "current_status": "active",
                "active_count": 2,
                "standby_count": 0,
                "resumed_count": 1,
            }
        },
        council_runtime={
            "council_state": "aligned",
            "recommendation": "carry-forward",
            "divergence_level": "low",
        },
        conflict_trace={
            "outcome": "continue_internal",
            "reason_code": "execute-continuation",
        },
        quiet_initiative={
            "active": False,
        },
    )

    assert forward["planner_mode"] == "forward-push"
    assert forward["planning_posture"] == "forward"
    assert forward["risk_posture"] == "balanced"
    assert forward["confidence"] == "high"


def test_adaptive_planner_prompt_section_is_grounded(isolated_runtime) -> None:
    planner = isolated_runtime.adaptive_planner_runtime

    section = planner.build_adaptive_planner_prompt_section(
        {
            "planner_mode": "cautious-step",
            "plan_horizon": "immediate",
            "planning_posture": "narrow",
            "risk_posture": "careful",
            "next_planning_bias": "verify-before-push",
            "confidence": "medium",
            "source_contributors": [
                {"source": "epistemic-runtime-state", "signal": "off / regret=slight"},
                {"source": "council-runtime", "signal": "checking / recommend=bounded-check / divergence=medium"},
            ],
            "freshness": {"state": "fresh"},
        }
    )

    assert "Adaptive planner light" in section
    assert "mode=cautious-step" in section
    assert "risk=careful" in section
    assert "verify-before-push" in section


def test_heartbeat_runtime_truth_instruction_includes_adaptive_planner(isolated_runtime) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    instruction = prompt_contract._heartbeat_runtime_truth_instruction(
        {
            "schedule_status": "scheduled",
            "budget_status": "healthy",
            "kill_switch": "enabled",
            "embodied_state": {"state": "steady", "strain_level": "low"},
            "affective_meta_state": {"state": "attentive", "bearing": "forward", "monitoring_mode": "watchful-check"},
            "epistemic_runtime_state": {"wrongness_state": "uneasy", "regret_signal": "slight", "counterfactual_mode": "nearby-alternative"},
            "adaptive_planner": {
                "planner_mode": "cautious-step",
                "plan_horizon": "immediate",
                "planning_posture": "narrow",
                "risk_posture": "careful",
            },
            "loop_runtime": {"summary": {"current_status": "active", "active_count": 1, "standby_count": 0, "resumed_count": 0}},
        }
    )

    assert "adaptive_planner=cautious-step" in instruction
    assert "horizon=immediate" in instruction
    assert "risk=careful" in instruction


def test_mission_control_runtime_and_endpoint_expose_adaptive_planner(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "planner_mode": "reflective-planning",
        "plan_horizon": "near",
        "planning_posture": "reflective",
        "risk_posture": "careful",
        "next_planning_bias": "observe-before-move",
        "confidence": "medium",
        "summary": "reflective-planning adaptive planner with near horizon and careful risk posture",
        "source_contributors": [],
        "freshness": {
            "built_at": "2026-04-01T20:00:00+00:00",
            "state": "fresh",
        },
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "boundary": "not-memory-not-identity-not-action",
        "kind": "adaptive-planner-runtime-state",
    }

    monkeypatch.setattr(
        isolated_runtime.adaptive_planner_runtime,
        "build_adaptive_planner_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_adaptive_planner_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.runtime_self_model,
        "_adaptive_planner_surface",
        lambda: runtime_surface,
    )

    endpoint = isolated_runtime.mission_control.mc_adaptive_planner()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["planner_mode"] == "reflective-planning"
    assert runtime["runtime_adaptive_planner"]["risk_posture"] == "careful"
    assert self_model["adaptive_planner"]["planning_posture"] == "reflective"
