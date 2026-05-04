from __future__ import annotations


def test_curiosity_hypothesis_debt_registers_and_prompts(isolated_runtime) -> None:
    from core.services.curiosity_hypothesis_debt import (
        build_curiosity_debt_prompt_section,
        build_curiosity_debt_surface,
        register_hypothesis_debt,
    )

    register_hypothesis_debt(
        hypothesis="Perception change observer may improve autonomy",
        why_it_matters="It affects AGI gap closure",
        resolving_observation="Watch whether next run reacts to perceptual changes",
        priority="high",
    )

    surface = build_curiosity_debt_surface()
    assert surface["active"] is True
    assert "Perception" in surface["summary"]
    assert "resolving observation" in surface["directive"]

    section = build_curiosity_debt_prompt_section()
    assert section is not None
    assert "Curiosity hypothesis debt" in section


def test_curiosity_hypothesis_debt_detects_agi_text(isolated_runtime) -> None:
    from core.services.curiosity_hypothesis_debt import build_curiosity_debt_surface, maybe_register_from_text

    maybe_register_from_text(text="AGI learning perception thread", source="test")
    surface = build_curiosity_debt_surface()
    assert surface["active"] is True
    assert surface["items"][0]["priority"] == "high"
