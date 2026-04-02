from __future__ import annotations


def test_dream_influence_builds_bounded_runtime_state(isolated_runtime) -> None:
    dream_influence = isolated_runtime.dream_influence_runtime

    surface = dream_influence.build_dream_influence_runtime_from_sources(
        dream_articulation={
            "summary": {
                "last_state": "pressing",
                "last_reason": "dream-articulated",
                "latest_summary": "A quiet synthesis keeps pulling toward clearer prompting.",
            },
            "latest_artifact": {
                "summary": "A quiet synthesis keeps pulling toward clearer prompting.",
            },
        },
        guided_learning={
            "learning_mode": "explore",
            "learning_focus": "self-knowledge",
            "learning_posture": "active",
            "learning_pressure": "medium",
        },
        adaptive_learning={
            "learning_engine_mode": "reinforce",
            "reinforcement_target": "prompt-shape",
            "retention_bias": "warm",
            "maturation_state": "forming",
        },
        adaptive_reasoning={
            "reasoning_mode": "exploratory",
            "reasoning_posture": "open",
            "certainty_style": "tentative",
        },
        affective_meta_state={
            "state": "reflective",
            "bearing": "inward",
        },
        epistemic_runtime_state={
            "wrongness_state": "clear",
            "regret_signal": "none",
            "counterfactual_mode": "none",
        },
        prompt_evolution={
            "summary": {
                "last_state": "forming",
                "latest_target_asset": "HEARTBEAT.md",
            }
        },
    )

    assert surface["influence_state"] == "active"
    assert surface["influence_target"] == "prompting"
    assert surface["influence_mode"] == "reinforce"
    assert surface["influence_strength"] == "medium"
    assert surface["visibility"] == "internal-only"
    assert surface["boundary"] == "not-memory-not-identity-not-action"
    assert surface["seam_usage"]["guided_learning_enrichment"] is True


def test_mission_control_runtime_and_endpoint_expose_dream_influence(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "influence_state": "present",
        "influence_target": "learning",
        "influence_mode": "explore",
        "influence_strength": "low",
        "influence_hint": "explore learning around self-knowledge",
        "confidence": "medium",
        "summary": "dream influence present toward learning via explore (low)",
        "source_contributors": [],
        "freshness": {"built_at": "2026-04-02T10:00:00+00:00", "state": "fresh"},
        "seam_usage": {
            "guided_learning_enrichment": True,
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "boundary": "not-memory-not-identity-not-action",
        "kind": "dream-influence-runtime-state",
    }

    monkeypatch.setattr(
        isolated_runtime.dream_influence_runtime,
        "build_dream_influence_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_dream_influence_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(
        isolated_runtime.runtime_self_model,
        "_dream_influence_surface",
        lambda: runtime_surface,
    )

    endpoint = isolated_runtime.mission_control.mc_dream_influence()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["influence_state"] == "present"
    assert runtime["runtime_dream_influence"]["influence_mode"] == "explore"
    assert self_model["dream_influence"]["influence_target"] == "learning"
