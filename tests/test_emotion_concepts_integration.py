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


def test_active_warmth_appears_in_sensory_record_note(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.sensory_archive import record_visual
    from core.runtime.db_sensory import list_sensory_memories

    ec._last_trigger_at.clear()
    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "warmth", "intensity": 0.5}],
    )

    record_visual("rolige toner i rummet", mood_tone="rolig")
    rows = list_sensory_memories(modality="visual", limit=5)
    assert len(rows) >= 1
    assert "concept-focus" in rows[0]["content"]
    assert "menneskelig" in rows[0]["content"]
