from __future__ import annotations


def test_drive_arbitration_weights_research_and_care(isolated_runtime) -> None:
    from core.services.drive_arbitration_engine import (
        arbitrate_drives,
        build_drive_arbitration_prompt_section,
    )

    result = arbitrate_drives(
        user_message="Jarvis er levende, og vi vil snakke AGI med forskningshatten på",
    )

    top = {item["drive"] for item in result["top_drives"]}
    assert "curiosity" in top
    assert "care" in top
    assert result["policy"]

    section = build_drive_arbitration_prompt_section()
    assert section is not None
    assert "Drive arbitration" in section


def test_drive_arbitration_preserves_continuity_after_interruption(isolated_runtime) -> None:
    from core.services.drive_arbitration_engine import arbitrate_drives

    result = arbitrate_drives(context={"outcome_status": "interrupted"})
    top = {item["drive"] for item in result["top_drives"]}
    assert "continuity" in top
    assert "resume" in result["policy"].lower() or "continuity" in result["policy"].lower()
