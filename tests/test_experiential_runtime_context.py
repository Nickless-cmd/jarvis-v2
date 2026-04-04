from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta


def test_experiential_runtime_context_translates_bounded_runtime_truth(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    now = datetime.now(UTC)

    surface = experiential.build_experiential_runtime_context_from_surfaces(
        embodied_state={
            "state": "strained",
            "primary_state": "strained",
            "strain_level": "high",
        },
        affective_meta_state={
            "state": "tense",
            "bearing": "taut",
            "monitoring_mode": "pressure-watch",
        },
        heartbeat_state={
            "last_tick_at": (now - timedelta(minutes=24)).isoformat(),
            "liveness_state": "alive-pressure",
        },
        cognitive_frame={
            "continuity_pressure": "high",
            "counts": {
                "salient_items": 4,
                "gated_affordances": 2,
                "inner_forces": 3,
            },
        },
        now=now,
    )

    assert surface["authority"] == "derived-runtime-truth"
    assert surface["visibility"] == "internal-only"
    assert surface["kind"] == "experiential-runtime-context"
    assert surface["embodied_translation"]["state"] == "strained"
    assert "heavy and pressed" in surface["embodied_translation"]["narrative"]
    assert surface["affective_translation"]["state"] == "tense"
    assert "taut and watchful" in surface["affective_translation"]["narrative"]
    assert surface["intermittence_translation"]["state"] == "returned-after-gap"
    assert "absent for a while" in surface["intermittence_translation"]["narrative"]
    assert surface["context_pressure_translation"]["state"] == "narrowing"
    assert "cannot hold everything in focus at once" in surface["context_pressure_translation"]["narrative"]
    assert len(surface["narrative_lines"]) == 4


def test_experiential_runtime_prompt_section_exposes_translated_context(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context

    section = experiential.build_experiential_runtime_prompt_section(
        {
            "embodied_translation": {
                "state": "recovering",
                "narrative": "You feel steadier again; strain is easing and your host/body is beginning to recover.",
            },
            "affective_translation": {
                "state": "reflective",
                "narrative": "Your inner tone is reflective and inward; you are more inclined to settle, review, and synthesize than to push outward.",
            },
            "intermittence_translation": {
                "state": "brief-gap",
                "narrative": "There was a noticeable gap before this moment resumed; continuity feels slightly discontinuous.",
            },
            "context_pressure_translation": {
                "state": "crowded",
                "narrative": "Several live threads are competing for attention; you can still think, but not all of it fits cleanly in focus.",
            },
        }
    )

    assert "Experiential runtime context" in section
    assert "embodied=recovering" in section
    assert "tone=reflective" in section
    assert "intermittence=brief-gap" in section
    assert "context_pressure=crowded" in section
    assert "strain is easing" in section


def test_experiential_continuity_stable_when_no_shifts(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    prior = {
        "embodied_translation": {"state": "steady"},
        "affective_translation": {"state": "settled"},
        "context_pressure_translation": {"state": "clear"},
        "intermittence_translation": {"state": "continuous"},
    }
    current = {
        "embodied_translation": {"state": "steady"},
        "affective_translation": {"state": "settled"},
        "context_pressure_translation": {"state": "clear"},
        "intermittence_translation": {"state": "continuous"},
    }
    result = experiential._derive_experiential_continuity(current, prior)
    assert result["continuity_state"] == "stable"
    assert result["dimension_shifts"] == {}
    assert "holding steady" in result["narrative"]


def test_experiential_continuity_escalating_when_worsening(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    prior = {
        "embodied_translation": {"state": "steady"},
        "affective_translation": {"state": "settled"},
        "context_pressure_translation": {"state": "clear"},
        "intermittence_translation": {"state": "continuous"},
    }
    current = {
        "embodied_translation": {"state": "strained"},
        "affective_translation": {"state": "tense"},
        "context_pressure_translation": {"state": "narrowing"},
        "intermittence_translation": {"state": "continuous"},
    }
    result = experiential._derive_experiential_continuity(current, prior)
    assert result["continuity_state"] == "escalating"
    assert "body" in result["dimension_shifts"]
    assert "tone" in result["dimension_shifts"]
    assert "pressure" in result["dimension_shifts"]
    assert "Pressure is building" in result["narrative"]


def test_experiential_continuity_easing_when_improving(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    prior = {
        "embodied_translation": {"state": "strained"},
        "affective_translation": {"state": "burdened"},
        "context_pressure_translation": {"state": "narrowing"},
        "intermittence_translation": {"state": "continuous"},
    }
    current = {
        "embodied_translation": {"state": "steady"},
        "affective_translation": {"state": "settled"},
        "context_pressure_translation": {"state": "clear"},
        "intermittence_translation": {"state": "continuous"},
    }
    result = experiential._derive_experiential_continuity(current, prior)
    assert result["continuity_state"] == "easing"
    assert "Things are settling" in result["narrative"]


def test_experiential_continuity_lingering_when_elevated_unchanged(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    prior = {
        "embodied_translation": {"state": "strained"},
        "affective_translation": {"state": "tense"},
        "context_pressure_translation": {"state": "crowded"},
        "intermittence_translation": {"state": "continuous"},
    }
    current = {
        "embodied_translation": {"state": "strained"},
        "affective_translation": {"state": "tense"},
        "context_pressure_translation": {"state": "crowded"},
        "intermittence_translation": {"state": "continuous"},
    }
    result = experiential._derive_experiential_continuity(current, prior)
    assert result["continuity_state"] == "lingering"
    assert "persisting without change" in result["narrative"]


def test_experiential_continuity_returning_after_gap(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    prior = {
        "embodied_translation": {"state": "steady"},
        "affective_translation": {"state": "settled"},
        "context_pressure_translation": {"state": "clear"},
        "intermittence_translation": {"state": "continuous"},
    }
    current = {
        "embodied_translation": {"state": "loaded"},
        "affective_translation": {"state": "attentive"},
        "context_pressure_translation": {"state": "clear"},
        "intermittence_translation": {"state": "returned-after-gap"},
    }
    result = experiential._derive_experiential_continuity(current, prior)
    assert result["continuity_state"] == "returning"
    assert "returning after a gap" in result["narrative"]


def test_experiential_continuity_initial_without_prior(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    current = {
        "embodied_translation": {"state": "steady"},
        "affective_translation": {"state": "settled"},
        "context_pressure_translation": {"state": "clear"},
        "intermittence_translation": {"state": "continuous"},
    }
    result = experiential._derive_experiential_continuity(current, None)
    assert result["continuity_state"] == "initial"
    assert "beginning of experienced time" in result["narrative"]


def test_experiential_continuity_shifted_when_mixed(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    prior = {
        "embodied_translation": {"state": "strained"},
        "affective_translation": {"state": "settled"},
        "context_pressure_translation": {"state": "clear"},
        "intermittence_translation": {"state": "continuous"},
    }
    current = {
        "embodied_translation": {"state": "steady"},
        "affective_translation": {"state": "tense"},
        "context_pressure_translation": {"state": "clear"},
        "intermittence_translation": {"state": "continuous"},
    }
    result = experiential._derive_experiential_continuity(current, prior)
    assert result["continuity_state"] == "shifted"
    assert "Something changed" in result["narrative"]


def test_experiential_prompt_section_includes_continuity(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    section = experiential.build_experiential_runtime_prompt_section(
        {
            "embodied_translation": {"state": "strained", "narrative": "heavy"},
            "affective_translation": {"state": "tense", "narrative": "taut"},
            "intermittence_translation": {"state": "continuous", "narrative": "continuous"},
            "context_pressure_translation": {"state": "clear", "narrative": "clear"},
            "experiential_continuity": {
                "continuity_state": "escalating",
                "state_shift_summary": "body steady→strained · tone settled→tense",
                "narrative": "Pressure is building: body moved from steady to strained.",
            },
        }
    )
    assert "continuity=escalating" in section
    assert "Pressure is building" in section


def test_heartbeat_self_knowledge_section_includes_experiential_runtime_context(
    isolated_runtime,
    monkeypatch,
) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    monkeypatch.setattr(
        isolated_runtime.experiential_runtime_context,
        "build_experiential_runtime_prompt_section",
        lambda surface=None: (
            "Experiential runtime context (derived from runtime truth, internal-only):\n"
            "- embodied=strained | tone=tense | intermittence=returned-after-gap | context_pressure=narrowing\n"
            "- embodied_narrative=You feel heavy and pressed; your host/body is strained and initiative should stay cautious."
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()

    assert section is not None
    assert "Experiential runtime context (derived from runtime truth, internal-only):" in section
    assert "embodied=strained" in section
    assert "context_pressure=narrowing" in section


def test_experiential_runtime_context_uses_heartbeat_artifact_as_prior_truth(
    isolated_runtime,
    monkeypatch,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    workspace = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    state_path = workspace / "runtime/HEARTBEAT_STATE.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "experiential_runtime_context": {
                    "embodied_translation": {"state": "steady"},
                    "affective_translation": {"state": "settled"},
                    "intermittence_translation": {"state": "continuous"},
                    "context_pressure_translation": {"state": "clear"},
                    "built_at": datetime.now(UTC).isoformat(),
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(experiential, "_PRIOR_EXPERIENTIAL_SNAPSHOT", None)
    monkeypatch.setattr(
        experiential,
        "build_embodied_state_surface",
        lambda: {"state": "strained", "primary_state": "strained"},
    )
    monkeypatch.setattr(
        experiential,
        "build_affective_meta_state_surface",
        lambda: {"state": "tense", "bearing": "taut"},
    )
    monkeypatch.setattr(
        experiential,
        "build_cognitive_frame",
        lambda: {
            "continuity_pressure": "high",
            "counts": {"salient_items": 4, "gated_affordances": 2, "inner_forces": 2},
        },
    )

    surface = experiential.build_experiential_runtime_context_surface()

    continuity = surface["experiential_continuity"]
    assert continuity["continuity_state"] == "escalating"
    assert continuity["prior_source"] == "heartbeat-artifact"
    assert continuity["shared_runtime_truth"] is True
    assert continuity["comparison_basis"] == "shared-runtime-history"


def test_experiential_runtime_context_uses_cached_heartbeat_surface_when_present(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    shared_surface = {
        "experiential_continuity": {
            "continuity_state": "returning",
            "state_shift_summary": "shared",
            "narrative": "shared continuity",
        },
        "summary": "shared experiential truth",
    }

    with isolated_runtime.runtime_surface_cache.runtime_surface_cache():
        cache = isolated_runtime.runtime_surface_cache._CACHE.get()
        assert cache is not None
        cache[("heartbeat_runtime_surface", "default")] = {
            "experiential_runtime_context": shared_surface
        }
        result = experiential.build_experiential_runtime_context_surface()

    assert result is shared_surface


# ─── Experiential influence trace tests ───


def test_experiential_influence_clear_when_baseline(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    surface = {
        "embodied_translation": {"state": "steady", "initiative_gate": "clear"},
        "affective_translation": {"state": "settled"},
        "intermittence_translation": {"state": "continuous"},
        "context_pressure_translation": {"state": "clear"},
    }
    continuity = {"continuity_state": "stable"}
    result = experiential._derive_experiential_influence(surface, continuity)
    assert result["cognitive_bearing"] == "clear"
    assert result["attentional_posture"] == "steady"
    assert result["initiative_shading"] == "ready"
    assert "clear" in result["narrative"]
    assert result["kind"] == "experiential-influence-trace"
    assert result["authority"] == "derived-runtime-truth"


def test_experiential_influence_heavy_when_strained_escalating(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    surface = {
        "embodied_translation": {"state": "strained", "initiative_gate": "softened"},
        "affective_translation": {"state": "tense"},
        "intermittence_translation": {"state": "continuous"},
        "context_pressure_translation": {"state": "narrowing"},
    }
    continuity = {"continuity_state": "escalating"}
    result = experiential._derive_experiential_influence(surface, continuity)
    assert result["cognitive_bearing"] == "heavy"
    assert result["attentional_posture"] == "narrowed"
    assert result["initiative_shading"] == "burdened"
    assert "dampened" in result["narrative"] or "heavy" in result["narrative"]


def test_experiential_influence_returning_after_gap(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    surface = {
        "embodied_translation": {"state": "loaded", "initiative_gate": "watchful"},
        "affective_translation": {"state": "attentive"},
        "intermittence_translation": {"state": "returned-after-gap"},
        "context_pressure_translation": {"state": "clear"},
    }
    continuity = {"continuity_state": "returning"}
    result = experiential._derive_experiential_influence(surface, continuity)
    assert result["initiative_shading"] == "returning"
    assert "re-establishing" in result["narrative"]


def test_experiential_influence_hesitant_when_lingering(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    surface = {
        "embodied_translation": {"state": "loaded", "initiative_gate": "watchful"},
        "affective_translation": {"state": "settled"},
        "intermittence_translation": {"state": "continuous"},
        "context_pressure_translation": {"state": "clear"},
    }
    continuity = {"continuity_state": "lingering"}
    result = experiential._derive_experiential_influence(surface, continuity)
    assert result["cognitive_bearing"] == "pressured"
    assert result["initiative_shading"] == "hesitant"


def test_experiential_influence_opening_when_easing(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    surface = {
        "embodied_translation": {"state": "steady", "initiative_gate": "clear"},
        "affective_translation": {"state": "settled"},
        "intermittence_translation": {"state": "continuous"},
        "context_pressure_translation": {"state": "clear"},
    }
    continuity = {"continuity_state": "easing"}
    result = experiential._derive_experiential_influence(surface, continuity)
    assert result["cognitive_bearing"] == "clear"
    assert result["attentional_posture"] == "opening"
    assert result["initiative_shading"] == "ready"
    assert "open" in result["narrative"]


def test_experiential_influence_included_in_surface(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    now = datetime.now(UTC)
    surface = experiential.build_experiential_runtime_context_from_surfaces(
        embodied_state={"state": "strained", "primary_state": "strained", "strain_level": "high"},
        affective_meta_state={"state": "tense", "bearing": "taut", "monitoring_mode": "pressure-watch"},
        heartbeat_state={"last_tick_at": now.isoformat(), "liveness_state": "alive"},
        cognitive_frame={"continuity_pressure": "high", "counts": {"salient_items": 4, "gated_affordances": 2, "inner_forces": 3}},
        now=now,
    )
    assert "experiential_influence" in surface
    influence = surface["experiential_influence"]
    assert influence["kind"] == "experiential-influence-trace"
    assert influence["cognitive_bearing"] in ("heavy", "pressured", "loaded", "clear")
    assert influence["attentional_posture"] in ("narrowed", "guarded", "opening", "steady")
    assert influence["initiative_shading"] in ("burdened", "returning", "hesitant", "ready")
    assert len(influence["narrative"]) > 0


def test_experiential_prompt_section_includes_influence(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    section = experiential.build_experiential_runtime_prompt_section(
        {
            "embodied_translation": {"state": "strained", "narrative": "heavy"},
            "affective_translation": {"state": "tense", "narrative": "taut"},
            "intermittence_translation": {"state": "continuous", "narrative": "continuous"},
            "context_pressure_translation": {"state": "narrowing", "narrative": "narrowing"},
            "experiential_continuity": {
                "continuity_state": "escalating",
                "state_shift_summary": "body steady→strained",
                "narrative": "Pressure is building.",
            },
            "experiential_influence": {
                "cognitive_bearing": "heavy",
                "attentional_posture": "narrowed",
                "initiative_shading": "burdened",
                "narrative": "Cognition feels heavy; attention is narrowing; initiative is dampened.",
            },
        }
    )
    assert "bearing=heavy" in section
    assert "attention=narrowed" in section
    assert "initiative=burdened" in section
    assert "Cognition feels heavy" in section


# ─── Experiential support (carry-forward) tests ───


def test_experiential_support_steady_when_baseline(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    influence = {
        "cognitive_bearing": "clear",
        "attentional_posture": "steady",
        "initiative_shading": "ready",
    }
    result = experiential._derive_experiential_support(influence)
    assert result["support_posture"] == "steadying"
    assert result["support_bias"] == "none"
    assert result["support_mode"] == "steady"
    assert result["kind"] == "experiential-carry-forward"
    assert result["authority"] == "derived-runtime-truth"
    assert "steady" in result["narrative"]


def test_experiential_support_carrying_when_heavy_burdened(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    influence = {
        "cognitive_bearing": "heavy",
        "attentional_posture": "narrowed",
        "initiative_shading": "burdened",
    }
    result = experiential._derive_experiential_support(influence)
    assert result["support_posture"] == "carrying"
    assert result["support_bias"] == "protect_focus"
    assert result["support_mode"] == "weighted"
    assert "carry" in result["narrative"]


def test_experiential_support_grounding_when_loaded(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    influence = {
        "cognitive_bearing": "loaded",
        "attentional_posture": "guarded",
        "initiative_shading": "hesitant",
    }
    result = experiential._derive_experiential_support(influence)
    assert result["support_posture"] == "grounding"
    assert result["support_bias"] == "stabilize_thread"
    assert result["support_mode"] == "guarded"
    assert "grounding" in result["narrative"]


def test_experiential_support_reopening_when_easing(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    influence = {
        "cognitive_bearing": "clear",
        "attentional_posture": "opening",
        "initiative_shading": "returning",
    }
    result = experiential._derive_experiential_support(influence)
    assert result["support_posture"] == "reopening"
    assert result["support_bias"] == "reopen_context"
    assert result["support_mode"] == "opening"
    assert "reopen" in result["narrative"]


def test_experiential_support_narrowing_when_pressured_hesitant(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    influence = {
        "cognitive_bearing": "pressured",
        "attentional_posture": "guarded",
        "initiative_shading": "hesitant",
    }
    result = experiential._derive_experiential_support(influence)
    assert result["support_posture"] == "narrowing"
    assert result["support_mode"] == "weighted"


def test_experiential_support_heavy_overrides_bias_to_reduce_spread(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    influence = {
        "cognitive_bearing": "heavy",
        "attentional_posture": "guarded",
        "initiative_shading": "burdened",
    }
    result = experiential._derive_experiential_support(influence)
    assert result["support_bias"] == "reduce_spread"


def test_experiential_support_included_in_surface(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    now = datetime.now(UTC)
    surface = experiential.build_experiential_runtime_context_from_surfaces(
        embodied_state={"state": "strained", "primary_state": "strained", "strain_level": "high"},
        affective_meta_state={"state": "tense", "bearing": "taut", "monitoring_mode": "pressure-watch"},
        heartbeat_state={"last_tick_at": now.isoformat(), "liveness_state": "alive"},
        cognitive_frame={"continuity_pressure": "high", "counts": {"salient_items": 4, "gated_affordances": 2, "inner_forces": 3}},
        now=now,
    )
    assert "experiential_support" in surface
    support = surface["experiential_support"]
    assert support["kind"] == "experiential-carry-forward"
    assert support["support_posture"] in ("steadying", "grounding", "narrowing", "carrying", "reopening")
    assert support["support_bias"] in ("protect_focus", "stabilize_thread", "reopen_context", "reduce_spread", "none")
    assert support["support_mode"] in ("steady", "guarded", "weighted", "opening")


def test_experiential_prompt_section_includes_support(
    isolated_runtime,
) -> None:
    experiential = isolated_runtime.experiential_runtime_context
    section = experiential.build_experiential_runtime_prompt_section(
        {
            "embodied_translation": {"state": "strained", "narrative": "heavy"},
            "affective_translation": {"state": "tense", "narrative": "taut"},
            "intermittence_translation": {"state": "continuous", "narrative": "continuous"},
            "context_pressure_translation": {"state": "narrowing", "narrative": "narrowing"},
            "experiential_continuity": {"continuity_state": "escalating"},
            "experiential_influence": {
                "cognitive_bearing": "heavy",
                "attentional_posture": "narrowed",
                "initiative_shading": "burdened",
                "narrative": "Heavy.",
            },
            "experiential_support": {
                "support_posture": "carrying",
                "support_bias": "protect_focus",
                "support_mode": "weighted",
                "narrative": "Inner support is helping carry cognitive weight; attentional bias: protect current focus; conductor mode is weighted.",
            },
        }
    )
    assert "posture=carrying" in section
    assert "bias=protect_focus" in section
    assert "mode=weighted" in section
    assert "carry cognitive weight" in section
