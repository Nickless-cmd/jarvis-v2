from __future__ import annotations


def test_adaptive_learning_changes_mechanics_from_runtime_inputs(isolated_runtime) -> None:
    learning = isolated_runtime.adaptive_learning_runtime

    rebalance = learning.build_adaptive_learning_runtime_from_sources(
        guided_learning={
            "learning_mode": "stabilize",
            "learning_focus": "restraint",
            "learning_posture": "watchful",
            "learning_pressure": "high",
        },
        adaptive_planner={
            "planner_mode": "hold",
            "plan_horizon": "immediate",
            "risk_posture": "constrained",
        },
        adaptive_reasoning={
            "reasoning_mode": "constrained",
            "certainty_style": "cautious",
        },
        epistemic_runtime_state={
            "wrongness_state": "strained",
            "counterfactual_mode": "blocked-path",
        },
        prompt_evolution={"summary": {"last_state": "idle", "latest_target_asset": "none"}},
        dream_articulation={"summary": {"last_state": "idle", "last_reason": "no-run-yet"}},
        idle_consolidation={"summary": {"last_state": "idle", "last_reason": "no-run-yet"}},
        loop_runtime={"summary": {"current_status": "standby", "active_count": 0, "standby_count": 2}},
    )

    assert rebalance["learning_engine_mode"] == "rebalance"
    assert rebalance["reinforcement_target"] == "restraint"
    assert rebalance["retention_bias"] == "warm"
    assert rebalance["attenuation_bias"] == "soften"
    assert rebalance["maturation_state"] == "forming"
    assert rebalance["visibility"] == "internal-only"
    assert rebalance["boundary"] == "not-memory-not-identity-not-action"

    consolidate = learning.build_adaptive_learning_runtime_from_sources(
        guided_learning={
            "learning_mode": "practice",
            "learning_focus": "prompting",
            "learning_posture": "active",
            "learning_pressure": "medium",
        },
        adaptive_planner={
            "planner_mode": "forward-push",
            "plan_horizon": "short-span",
            "risk_posture": "balanced",
        },
        adaptive_reasoning={
            "reasoning_mode": "direct",
            "certainty_style": "crisp",
        },
        epistemic_runtime_state={
            "wrongness_state": "clear",
            "counterfactual_mode": "none",
        },
        prompt_evolution={"summary": {"last_state": "forming", "latest_target_asset": "HEARTBEAT.md"}},
        dream_articulation={"summary": {"last_state": "forming", "last_reason": "candidate-formed"}},
        idle_consolidation={"summary": {"last_state": "settling", "last_reason": "sleep-consolidation-articulated"}},
        loop_runtime={"summary": {"current_status": "active", "active_count": 2, "standby_count": 0}},
    )

    assert consolidate["learning_engine_mode"] == "consolidate"
    assert consolidate["reinforcement_target"] == "prompt-shape"
    assert consolidate["retention_bias"] == "hold"
    assert consolidate["attenuation_bias"] == "none"
    assert consolidate["maturation_state"] == "stabilizing"


def test_adaptive_learning_prompt_section_is_grounded(isolated_runtime) -> None:
    learning = isolated_runtime.adaptive_learning_runtime

    section = learning.build_adaptive_learning_prompt_section(
        {
            "learning_engine_mode": "retain",
            "reinforcement_target": "reasoning",
            "retention_bias": "warm",
            "attenuation_bias": "soften",
            "maturation_state": "forming",
            "confidence": "medium",
            "source_contributors": [
                {"source": "guided-learning", "signal": "clarify / focus=reasoning / pressure=medium"},
                {"source": "idle-consolidation", "signal": "settling / reason=sleep-consolidation-articulated"},
            ],
            "freshness": {"state": "fresh"},
        }
    )

    assert "Adaptive learning engine light" in section
    assert "mode=retain" in section
    assert "target=reasoning" in section
    assert "maturation=forming" in section


def test_heartbeat_runtime_truth_instruction_includes_adaptive_learning(isolated_runtime) -> None:
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
            "guided_learning": {
                "learning_mode": "clarify",
                "learning_focus": "reasoning",
                "learning_posture": "gentle",
                "learning_pressure": "medium",
            },
            "adaptive_learning": {
                "learning_engine_mode": "retain",
                "reinforcement_target": "reasoning",
                "retention_bias": "warm",
                "maturation_state": "forming",
            },
            "loop_runtime": {"summary": {"current_status": "standby", "active_count": 0, "standby_count": 1, "resumed_count": 0}},
        }
    )

    assert "adaptive_learning=retain" in instruction
    assert "target=reasoning" in instruction
    assert "maturation=forming" in instruction


def test_mission_control_runtime_and_endpoint_expose_adaptive_learning(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "learning_engine_mode": "consolidate",
        "reinforcement_target": "prompt-shape",
        "retention_bias": "hold",
        "attenuation_bias": "none",
        "maturation_state": "stabilizing",
        "confidence": "medium",
        "summary": "consolidate adaptive learning around prompt-shape with stabilizing maturation",
        "source_contributors": [],
        "freshness": {"built_at": "2026-04-01T20:00:00+00:00", "state": "fresh"},
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
            "guided_learning_enrichment": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "boundary": "not-memory-not-identity-not-action",
        "kind": "adaptive-learning-runtime-state",
    }

    monkeypatch.setattr(
        isolated_runtime.adaptive_learning_runtime,
        "build_adaptive_learning_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_adaptive_learning_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.runtime_self_model,
        "_adaptive_learning_surface",
        lambda: runtime_surface,
    )

    endpoint = isolated_runtime.mission_control.mc_adaptive_learning()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["learning_engine_mode"] == "consolidate"
    assert runtime["runtime_adaptive_learning"]["reinforcement_target"] == "prompt-shape"
    assert self_model["adaptive_learning"]["retention_bias"] == "hold"
