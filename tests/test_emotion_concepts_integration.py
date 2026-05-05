from __future__ import annotations


def test_emotion_concept_tone_section_includes_active_hint(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.prompt_contract import _emotion_concept_tone_section

    ec._last_trigger_at.clear()
    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "wonder", "intensity": 0.6}],
    )

    section = _emotion_concept_tone_section()
    assert section is not None
    assert "Tone right now" in section
    assert "Wonder er aktiv" in section


def test_emotion_concept_tone_section_returns_none_when_no_active(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.prompt_contract import _emotion_concept_tone_section

    monkeypatch.setattr(ec, "get_active_emotion_concepts", lambda: [])
    assert _emotion_concept_tone_section() is None
