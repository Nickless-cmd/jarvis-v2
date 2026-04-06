from __future__ import annotations


def test_affective_meta_state_builds_bounded_state_from_runtime_inputs(isolated_runtime) -> None:
    affective = isolated_runtime.affective_meta_state

    surface = affective.build_affective_meta_state_from_sources(
        embodied_state={
            "state": "strained",
            "strain_level": "high",
            "recovery_state": "steady",
        },
        loop_runtime={
            "summary": {
                "loop_count": 2,
                "current_status": "active",
                "active_count": 1,
                "standby_count": 1,
            }
        },
        regulation_homeostasis={
            "active": True,
            "summary": {
                "current_state": "watchful-regulation",
                "current_pressure": "high",
            },
        },
        metabolism_state={
            "active": True,
            "summary": {
                "current_state": "holding",
                "current_direction": "holding",
                "current_weight": "high",
            },
        },
        quiet_initiative={"active": True, "state": "holding", "hold_count": 2},
        idle_consolidation={"summary": {"last_state": "settling"}},
        dream_articulation={"summary": {"last_state": "forming"}},
        inner_voice_state={"last_result": {"inner_voice_created": True, "focus": "hold the line plainly"}},
        personality_vector={
            "current_bearing": "careful",
            "emotional_baseline": '{"confidence": 0.7, "fatigue": 0.1, "curiosity": 0.4}',
        },
        relationship_texture={
            "trust_trajectory": "[0.5, 0.52]",
        },
        rhythm_state={
            "phase": "social",
            "energy": "low",
            "social": "high",
        },
    )

    assert surface["state"] == "burdened"
    assert surface["bearing"] == "compressed"
    assert surface["monitoring_mode"] == "strain-watch"
    assert surface["reflective_load"] == "high"
    assert surface["authority"] == "derived-runtime-truth"
    assert surface["visibility"] == "internal-only"
    assert surface["kind"] == "affective-meta-runtime-state"
    assert surface["seam_usage"]["heartbeat_context"] is True
    assert surface["live_emotional_state"]["confidence"] == 0.7
    assert surface["live_emotional_state"]["fatigue"] == 0.1
    assert surface["live_emotional_state"]["trust"] == 0.52
    assert surface["live_emotional_state"]["rhythm_phase"] == "social"


def test_affective_meta_prompt_section_includes_guidance(isolated_runtime) -> None:
    affective = isolated_runtime.affective_meta_state

    section = affective.build_affective_meta_prompt_section(
        {
            "state": "reflective",
            "bearing": "inward",
            "monitoring_mode": "reflective-scan",
            "reflective_load": "medium",
            "freshness": {"state": "fresh"},
            "source_contributors": [
                {"source": "idle-consolidation", "signal": "settling"},
                {"source": "dream-articulation", "signal": "forming"},
            ],
        }
    )

    assert "Affective/meta state" in section
    assert "state=reflective" in section
    assert "bearing=inward" in section
    assert "monitoring=reflective-scan" in section
    assert "Prefer synthesis, settling, and bounded review over extra outward push." in section


def test_heartbeat_self_knowledge_section_includes_affective_meta_guidance(isolated_runtime, monkeypatch) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    monkeypatch.setattr(
        isolated_runtime.affective_meta_state,
        "build_affective_meta_prompt_section",
        lambda surface=None: (
            "Affective/meta state (derived runtime truth, internal-only):\n"
            "- state=attentive | bearing=forward | monitoring=watchful-check | reflective_load=low | freshness=fresh\n"
            "- guidance=Prefer watchful forward carry without overstating momentum."
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()

    assert section is not None
    assert "Affective/meta state (derived runtime truth, internal-only):" in section
    assert "state=attentive" in section
    assert "Prefer watchful forward carry without overstating momentum." in section


def test_mission_control_runtime_and_endpoint_expose_affective_meta_state(isolated_runtime, monkeypatch) -> None:
    runtime_surface = {
        "state": "tense",
        "bearing": "taut",
        "monitoring_mode": "pressure-watch",
        "reflective_load": "medium",
        "summary": "tense affective/meta state with taut bearing",
        "source_contributors": [
            {"source": "embodied-state", "signal": "loaded / strain=medium"},
            {"source": "loop-runtime", "signal": "active / active=1 / standby=0"},
        ],
        "freshness": {"built_at": "2026-04-01T20:00:00+00:00", "state": "fresh"},
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "affective-meta-runtime-state",
    }

    monkeypatch.setattr(
        isolated_runtime.affective_meta_state,
        "build_affective_meta_state_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(isolated_runtime.mission_control, "build_affective_meta_state_surface", lambda: runtime_surface)
    monkeypatch.setattr(isolated_runtime.runtime_self_model, "_affective_meta_state_surface", lambda: runtime_surface)

    endpoint = isolated_runtime.mission_control.mc_affective_meta_state()
    runtime = isolated_runtime.mission_control.mc_runtime()
    self_model = isolated_runtime.runtime_self_model.build_runtime_self_model()

    assert endpoint["state"] == "tense"
    assert runtime["runtime_affective_meta_state"]["bearing"] == "taut"
    assert runtime["runtime_affective_meta_state"]["visibility"] == "internal-only"
    assert self_model["affective_meta_state"]["monitoring_mode"] == "pressure-watch"
