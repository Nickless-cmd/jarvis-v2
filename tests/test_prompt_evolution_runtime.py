from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_prompt_evolution_builds_bounded_proposal_from_runtime_inputs() -> None:
    from apps.api.jarvis_api.services import prompt_evolution_runtime as runtime_mod

    plan = runtime_mod.build_prompt_evolution_from_inputs(
        dream_articulation={
            "latest_artifact": {
                "canonical_key": "dream-hypothesis:articulated-dream-fragment:carried-thread",
                "signal_type": "articulated-dream-fragment",
                "summary": "A carried thread keeps pressing toward the same direction.",
            },
            "summary": {"latest_summary": "A carried thread keeps pressing toward the same direction."},
        },
        self_model_surface={
            "items": [{"canonical_key": "self-model:improving:carried-thread"}],
            "summary": {
                "active_count": 1,
                "uncertain_count": 1,
                "current_signal": "Self model: improvement edge",
            },
        },
        inner_voice_state={"last_result": {"inner_voice_created": True, "focus": "Keep the line plain and grounded."}},
        emergent_surface={"active": True, "summary": {"current_signal": "Current signal: carried direction still alive"}},
        embodied_state={"state": "steady", "strain_level": "low", "recovery_state": "steady"},
        loop_runtime={"summary": {"loop_count": 1, "current_loop": "carried thread", "current_status": "active"}},
        adaptive_learning={
            "learning_engine_mode": "reinforce",
            "reinforcement_target": "prompt-shape",
            "retention_bias": "warm",
            "attenuation_bias": "none",
            "maturation_state": "forming",
        },
        guided_learning={
            "learning_mode": "practice",
            "learning_focus": "planning",
        },
        adaptive_reasoning={
            "reasoning_mode": "careful",
            "certainty_style": "cautious",
        },
        now=datetime.now(UTC),
    )

    artifact = plan["artifact"] or {}
    assert plan["eligible"] is True
    assert plan["proposal_state"] == "pressing"
    assert artifact["proposal_type"] == "focus-nudge"
    assert artifact["target_asset"] == "HEARTBEAT.md"
    assert artifact["prompt_target"] == "direction-framing"
    assert artifact["learning_influence"]["learning_engine_mode"] == "reinforce"
    assert artifact["candidate_fragment"]
    assert artifact["fragment_truth"] == "proposal-only"
    assert artifact["fragment_visibility"] == "internal-only"
    assert artifact["fragment_grounding"]["guided_learning"] == "practice/planning"
    assert any(item["source"] == "adaptive-learning" for item in plan["source_inputs"])
    assert artifact["canonical_key"].startswith("runtime-prompt-evolution:focus-nudge:")


def test_prompt_evolution_learning_changes_proposal_direction() -> None:
    from apps.api.jarvis_api.services import prompt_evolution_runtime as runtime_mod

    base_inputs = {
        "dream_articulation": {
            "latest_artifact": {
                "canonical_key": "dream-hypothesis:articulated-dream-fragment:carried-thread",
                "signal_type": "articulated-dream-fragment",
                "summary": "A carried thread keeps pressing toward the same direction.",
            },
            "summary": {"latest_summary": "A carried thread keeps pressing toward the same direction."},
        },
        "self_model_surface": {
            "items": [{"canonical_key": "self-model:improving:carried-thread"}],
            "summary": {
                "active_count": 1,
                "uncertain_count": 0,
                "current_signal": "Self model: improvement edge",
            },
        },
        "inner_voice_state": {"last_result": {"inner_voice_created": True, "focus": "Keep the line plain and grounded."}},
        "emergent_surface": {"active": True, "summary": {"current_signal": "Current signal: carried direction still alive"}},
        "embodied_state": {"state": "steady", "strain_level": "low", "recovery_state": "steady"},
        "loop_runtime": {"summary": {"loop_count": 1, "current_loop": "carried thread", "current_status": "active"}},
        "guided_learning": {
            "learning_mode": "practice",
            "learning_focus": "planning",
        },
        "adaptive_reasoning": {
            "reasoning_mode": "careful",
            "certainty_style": "cautious",
        },
        "now": datetime.now(UTC),
    }

    reinforce_plan = runtime_mod.build_prompt_evolution_from_inputs(
        adaptive_learning={
            "learning_engine_mode": "reinforce",
            "reinforcement_target": "prompt-shape",
            "retention_bias": "warm",
            "attenuation_bias": "none",
            "maturation_state": "forming",
        },
        **base_inputs,
    )
    rebalance_plan = runtime_mod.build_prompt_evolution_from_inputs(
        adaptive_learning={
            "learning_engine_mode": "rebalance",
            "reinforcement_target": "restraint",
            "retention_bias": "hold",
            "attenuation_bias": "soften",
            "maturation_state": "stabilizing",
        },
        **base_inputs,
    )

    assert (reinforce_plan["artifact"] or {})["proposal_type"] == "focus-nudge"
    assert (rebalance_plan["artifact"] or {})["proposal_type"] == "world-caution-nudge"
    assert "plain, bounded, and alive" in str((reinforce_plan["artifact"] or {})["candidate_fragment"])
    assert "keep caution explicit" in str((rebalance_plan["artifact"] or {})["candidate_fragment"])
    assert "Adaptive learning currently points toward rebalance" in str((rebalance_plan["artifact"] or {})["rationale"])


def test_prompt_evolution_respects_cooldown(isolated_runtime) -> None:
    runtime_mod = isolated_runtime.prompt_evolution_runtime

    runtime_mod._last_run_at = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    result = runtime_mod.run_prompt_evolution_runtime(trigger="heartbeat", last_visible_at="")

    assert result["proposal_created"] is False
    assert result["cadence_state"] == "cooling-down"
    assert result["reason"] == "cooldown-active"
    assert result["boundary"] == "not-memory-not-identity-not-action-not-applied-prompt"


def test_prompt_evolution_respects_visible_grace(isolated_runtime) -> None:
    runtime_mod = isolated_runtime.prompt_evolution_runtime

    result = runtime_mod.run_prompt_evolution_runtime(
        trigger="heartbeat",
        last_visible_at=(datetime.now(UTC) - timedelta(minutes=2)).isoformat(),
    )

    assert result["proposal_created"] is False
    assert result["cadence_state"] == "visible-grace"
    assert result["reason"] == "visible-activity-too-recent"


def test_prompt_evolution_creates_internal_only_runtime_proposal(isolated_runtime, monkeypatch) -> None:
    runtime_mod = isolated_runtime.prompt_evolution_runtime

    monkeypatch.setattr(
        runtime_mod,
        "_load_runtime_inputs",
        lambda: {
            "dream_articulation": {
                "latest_artifact": {
                    "canonical_key": "dream-hypothesis:tension-hypothesis:world-thread",
                    "signal_type": "tension-hypothesis",
                    "summary": "World interpretation still looks unstable.",
                },
                "summary": {"latest_summary": "World interpretation still looks unstable."},
            },
            "self_model_surface": {
                "items": [{"canonical_key": "self-model:current-limitation:world-thread"}],
                "summary": {
                    "active_count": 1,
                    "uncertain_count": 0,
                    "current_signal": "Self model: world caution edge",
                },
            },
            "inner_voice_state": {"last_result": {"inner_voice_created": True, "focus": "Keep caution small and explicit."}},
            "emergent_surface": {"active": True, "summary": {"current_signal": "World line still feels unstable"}},
            "embodied_state": {"state": "strained", "strain_level": "high", "recovery_state": "steady"},
            "loop_runtime": {"summary": {"loop_count": 1, "current_loop": "world thread", "current_status": "standby"}},
            "adaptive_learning": {
                "learning_engine_mode": "rebalance",
                "reinforcement_target": "restraint",
                "retention_bias": "hold",
                "attenuation_bias": "soften",
                "maturation_state": "stabilizing",
            },
            "guided_learning": {
                "learning_mode": "clarify",
                "learning_focus": "restraint",
            },
            "adaptive_reasoning": {
                "reasoning_mode": "constrained",
                "certainty_style": "tentative",
            },
        },
    )
    monkeypatch.setattr(runtime_mod, "_adjacent_producer_block", lambda **kwargs: None)

    result = runtime_mod.run_prompt_evolution_runtime(trigger="heartbeat", last_visible_at="")
    surface = runtime_mod.build_prompt_evolution_runtime_surface()

    latest = surface["latest_proposal"] or {}
    assert result["proposal_created"] is True
    assert result["proposal_truth"] == "proposal-only"
    assert result["target_asset"] == "HEARTBEAT.md"
    assert result["proposal_type"] == "world-caution-nudge"
    assert result["learning_influence"]["learning_engine_mode"] == "rebalance"
    assert "keep caution explicit" in result["candidate_fragment"]
    assert surface["summary"]["latest_target_asset"] == "HEARTBEAT.md"
    assert surface["summary"]["latest_learning_mode"] == "rebalance"
    assert surface["summary"]["latest_candidate_fragment"].startswith("When pressure rises")
    assert surface["fragment_truth"] == "proposal-only"
    assert surface["summary"]["proposal_truth"] == "proposal-only"
    assert latest["source_kind"] == "internal-runtime-prompt-evolution"
    assert latest["status"] == "fresh"
    assert "learning_mode=rebalance" in str(latest["support_summary"])
    assert "candidate_fragment=When pressure rises" in str(latest["support_summary"])


def test_mission_control_runtime_and_endpoint_expose_prompt_evolution(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "active": True,
        "authority": "authoritative-runtime-observability",
        "visibility": "internal-only",
        "truth": "candidate-only",
        "proposal_mode": "proposal-only",
        "kind": "runtime-prompt-evolution-light",
        "boundary": "not-memory-not-identity-not-action-not-applied-prompt",
        "last_run_at": "2026-04-01T20:00:00+00:00",
        "last_result": {"proposal_state": "forming", "reason": "grounded-runtime-prompt-proposal"},
        "latest_proposal": {
            "proposal_id": "runtime-prompt-evolution-1",
            "proposal_type": "communication-nudge",
            "summary": "Bounded communication nudge for INNER_VOICE.md.",
            "source_kind": "internal-runtime-prompt-evolution",
            "support_summary": "learning_mode=retain | reinforcement_target=reasoning | retention_bias=hold",
        },
        "learning_influence": {
            "learning_engine_mode": "retain",
            "reinforcement_target": "reasoning",
            "retention_bias": "hold",
        },
        "candidate_fragment": "Keep the inner line plain, grounded in current runtime truth, and measured when claims are still forming.",
        "fragment_grounding": {
            "adaptive_learning": "retain/reasoning/hold",
            "guided_learning": "clarify/reasoning",
            "adaptive_reasoning": "careful/cautious",
        },
        "fragment_truth": "proposal-only",
        "cadence": {"cooldown_minutes": 45},
        "summary": {
            "last_state": "forming",
            "last_reason": "grounded-runtime-prompt-proposal",
            "latest_proposal_id": "runtime-prompt-evolution-1",
            "latest_target_asset": "INNER_VOICE.md",
            "latest_learning_mode": "retain",
            "latest_candidate_fragment": "Keep the inner line plain, grounded in current runtime truth, and measured when claims are still forming.",
            "fragment_truth": "proposal-only",
            "proposal_truth": "proposal-only",
        },
        "source": "/mc/prompt-evolution",
        "built_at": "2026-04-01T20:00:00+00:00",
    }

    monkeypatch.setattr(
        isolated_runtime.prompt_evolution_runtime,
        "build_prompt_evolution_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(isolated_runtime.mission_control, "build_prompt_evolution_runtime_surface", lambda: runtime_surface)
    monkeypatch.setattr(isolated_runtime.runtime_self_model, "_prompt_evolution_surface", lambda: runtime_surface)

    endpoint = isolated_runtime.mission_control.mc_prompt_evolution()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["summary"]["latest_target_asset"] == "INNER_VOICE.md"
    assert endpoint["summary"]["latest_learning_mode"] == "retain"
    assert endpoint["summary"]["fragment_truth"] == "proposal-only"
    assert runtime["runtime_prompt_evolution"]["summary"]["last_state"] == "forming"
    assert runtime["runtime_prompt_evolution"]["candidate_fragment"].startswith("Keep the inner line plain")
    assert runtime["runtime_prompt_evolution"]["boundary"] == "not-memory-not-identity-not-action-not-applied-prompt"
    assert self_model["prompt_evolution"]["candidate_fragment"].startswith("Keep the inner line plain")
    assert self_model["prompt_evolution"]["summary"]["proposal_truth"] == "proposal-only"
