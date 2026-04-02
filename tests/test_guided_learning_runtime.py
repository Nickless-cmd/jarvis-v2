from __future__ import annotations

from apps.api.jarvis_api.services.runtime_surface_cache import runtime_surface_cache


def test_guided_learning_changes_direction_from_runtime_inputs(isolated_runtime) -> None:
    learning = isolated_runtime.guided_learning_runtime

    stabilize = learning.build_guided_learning_runtime_from_sources(
        adaptive_planner={
            "planner_mode": "hold",
            "plan_horizon": "immediate",
            "planning_posture": "held",
            "risk_posture": "constrained",
        },
        adaptive_reasoning={
            "reasoning_mode": "constrained",
            "reasoning_posture": "guarded",
            "certainty_style": "cautious",
            "constraint_bias": "strong",
        },
        epistemic_runtime_state={
            "wrongness_state": "strained",
            "regret_signal": "active",
            "counterfactual_mode": "blocked-path",
        },
        prompt_evolution={"summary": {"last_state": "idle", "latest_target_asset": "none"}},
        dream_articulation={"summary": {"last_state": "idle", "last_reason": "no-run-yet"}},
        dream_influence={"influence_state": "quiet", "influence_target": "none", "influence_mode": "stabilize", "influence_strength": "none"},
        loop_runtime={"summary": {"current_status": "standby", "active_count": 0, "standby_count": 2}},
        council_runtime={"council_state": "checking", "recommendation": "bounded-check", "divergence_level": "high"},
    )

    assert stabilize["learning_mode"] == "stabilize"
    assert stabilize["learning_focus"] == "restraint"
    assert stabilize["learning_posture"] == "watchful"
    assert stabilize["learning_pressure"] == "high"
    assert stabilize["visibility"] == "internal-only"
    assert stabilize["boundary"] == "not-memory-not-identity-not-action"

    practice = learning.build_guided_learning_runtime_from_sources(
        adaptive_planner={
            "planner_mode": "forward-push",
            "plan_horizon": "short-span",
            "planning_posture": "forward",
            "risk_posture": "balanced",
        },
        adaptive_reasoning={
            "reasoning_mode": "direct",
            "reasoning_posture": "balanced",
            "certainty_style": "crisp",
            "constraint_bias": "light",
        },
        epistemic_runtime_state={
            "wrongness_state": "clear",
            "regret_signal": "none",
            "counterfactual_mode": "none",
        },
        prompt_evolution={"summary": {"last_state": "forming", "latest_target_asset": "HEARTBEAT.md"}},
        dream_articulation={"summary": {"last_state": "tentative", "last_reason": "candidate-formed"}},
        dream_influence={"influence_state": "present", "influence_target": "prompting", "influence_mode": "reinforce", "influence_strength": "low"},
        loop_runtime={"summary": {"current_status": "active", "active_count": 2, "standby_count": 0}},
        council_runtime={"council_state": "aligned", "recommendation": "carry-forward", "divergence_level": "low"},
    )

    assert practice["learning_mode"] == "practice"
    assert practice["learning_focus"] == "prompting"
    assert practice["next_learning_bias"] == "rehearse-framing"
    assert practice["learning_posture"] == "active"


def test_guided_learning_accepts_dream_influence_nudge(isolated_runtime) -> None:
    learning = isolated_runtime.guided_learning_runtime

    explore = learning.build_guided_learning_runtime_from_sources(
        adaptive_planner={
            "planner_mode": "incremental",
            "plan_horizon": "near",
            "planning_posture": "staged",
            "risk_posture": "balanced",
        },
        adaptive_reasoning={
            "reasoning_mode": "direct",
            "reasoning_posture": "balanced",
            "certainty_style": "crisp",
            "constraint_bias": "light",
        },
        epistemic_runtime_state={
            "wrongness_state": "clear",
            "regret_signal": "none",
            "counterfactual_mode": "none",
        },
        prompt_evolution={"summary": {"last_state": "idle", "latest_target_asset": "none"}},
        dream_articulation={"summary": {"last_state": "forming", "last_reason": "candidate-formed"}},
        dream_influence={
            "influence_state": "active",
            "influence_target": "learning",
            "influence_mode": "explore",
            "influence_strength": "medium",
        },
        loop_runtime={"summary": {"current_status": "standby", "active_count": 0, "standby_count": 1}},
        council_runtime={"council_state": "held", "recommendation": "hold", "divergence_level": "low"},
    )

    assert explore["learning_focus"] == "self-knowledge"
    assert explore["learning_mode"] == "explore"
    assert explore["next_learning_bias"] == "follow-dream-explore-learning"
    assert any(item["source"] == "dream-influence" for item in explore["source_contributors"])


def test_guided_learning_prompt_section_is_grounded(isolated_runtime) -> None:
    learning = isolated_runtime.guided_learning_runtime

    section = learning.build_guided_learning_prompt_section(
        {
            "learning_mode": "clarify",
            "learning_focus": "reasoning",
            "learning_posture": "gentle",
            "next_learning_bias": "tighten-claims",
            "learning_pressure": "medium",
            "confidence": "medium",
            "source_contributors": [
                {"source": "adaptive-reasoning", "signal": "careful / posture=narrow / certainty=cautious"},
                {"source": "epistemic-runtime-state", "signal": "uneasy / regret=slight / counterfactual=nearby-alternative"},
            ],
            "freshness": {"state": "fresh"},
        }
    )

    assert "Guided learning light" in section
    assert "mode=clarify" in section
    assert "focus=reasoning" in section
    assert "tighten-claims" in section


def test_guided_learning_does_not_force_dream_influence_rebuild_when_uncached(
    isolated_runtime,
    monkeypatch,
) -> None:
    learning = isolated_runtime.guided_learning_runtime

    monkeypatch.setattr(
        isolated_runtime.dream_influence_runtime,
        "build_dream_influence_runtime_surface",
        lambda: (_ for _ in ()).throw(AssertionError("dream influence should not be rebuilt")),
    )
    monkeypatch.setattr(
        learning,
        "_safe_adaptive_planner",
        lambda: {"planner_mode": "incremental", "plan_horizon": "near", "planning_posture": "staged", "risk_posture": "balanced"},
    )
    monkeypatch.setattr(
        learning,
        "_safe_adaptive_reasoning",
        lambda: {"reasoning_mode": "direct", "reasoning_posture": "balanced", "certainty_style": "crisp", "constraint_bias": "light"},
    )
    monkeypatch.setattr(
        learning,
        "_safe_epistemic_runtime_state",
        lambda: {"wrongness_state": "clear", "regret_signal": "none", "counterfactual_mode": "none"},
    )
    monkeypatch.setattr(
        learning,
        "_safe_prompt_evolution",
        lambda: {"summary": {"last_state": "idle", "latest_target_asset": "none"}},
    )
    monkeypatch.setattr(
        learning,
        "_safe_dream_articulation",
        lambda: {"summary": {"last_state": "idle", "last_reason": "no-run-yet"}},
    )
    monkeypatch.setattr(
        learning,
        "_safe_loop_runtime",
        lambda: {"summary": {"current_status": "active", "active_count": 1, "standby_count": 0}},
    )
    monkeypatch.setattr(
        learning,
        "_safe_council_runtime",
        lambda: {"council_state": "aligned", "recommendation": "hold", "divergence_level": "low"},
    )

    with runtime_surface_cache():
        surface = learning.build_guided_learning_runtime_surface()

    assert surface["learning_mode"] in {"reinforce", "practice", "explore", "clarify", "stabilize"}
    assert surface["kind"] == "guided-learning-runtime-state"


def test_heartbeat_runtime_truth_instruction_includes_guided_learning(isolated_runtime) -> None:
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
            "dream_influence": {
                "influence_state": "present",
                "influence_target": "learning",
                "influence_mode": "explore",
                "influence_strength": "low",
            },
            "guided_learning": {
                "learning_mode": "clarify",
                "learning_focus": "reasoning",
                "learning_posture": "gentle",
                "learning_pressure": "medium",
            },
            "loop_runtime": {"summary": {"current_status": "standby", "active_count": 0, "standby_count": 1, "resumed_count": 0}},
        }
    )

    assert "guided_learning=clarify" in instruction
    assert "dream_influence=present" in instruction
    assert "focus=reasoning" in instruction
    assert "pressure=medium" in instruction


def test_mission_control_runtime_and_endpoint_expose_guided_learning(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "learning_mode": "practice",
        "learning_focus": "prompting",
        "learning_posture": "active",
        "next_learning_bias": "rehearse-framing",
        "learning_pressure": "medium",
        "confidence": "medium",
        "summary": "practice guided learning around prompting with active posture",
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
        "kind": "guided-learning-runtime-state",
    }

    monkeypatch.setattr(
        isolated_runtime.guided_learning_runtime,
        "build_guided_learning_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_guided_learning_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.runtime_self_model,
        "_guided_learning_surface",
        lambda: runtime_surface,
    )

    endpoint = isolated_runtime.mission_control.mc_guided_learning()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["learning_mode"] == "practice"
    assert runtime["runtime_guided_learning"]["learning_focus"] == "prompting"
    assert self_model["guided_learning"]["next_learning_bias"] == "rehearse-framing"
