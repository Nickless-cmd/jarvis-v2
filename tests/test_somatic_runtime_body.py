from __future__ import annotations


def test_somatic_body_reacts_to_interruption(isolated_runtime) -> None:
    from core.services.somatic_runtime_body import build_somatic_body_prompt_section, update_somatic_body

    result = update_somatic_body(event_type="runtime-interruption", intensity=0.9, detail="timeout")
    assert result["posture"] == "startled"
    assert "resume" in result["regulation"].lower()

    section = build_somatic_body_prompt_section()
    assert section is not None
    assert "Somatic runtime body" in section


def test_perceptual_event_updates_somatic_body(isolated_runtime) -> None:
    from core.services.perceptual_event_engine import record_perceptual_event
    from core.services.somatic_runtime_body import build_somatic_body_surface

    record_perceptual_event(change_type="tool-error", summary="Tool failed", salience="high")
    surface = build_somatic_body_surface()
    assert surface["active"] is True
    assert surface["levels"]["frustration"] > 0
