from __future__ import annotations

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
