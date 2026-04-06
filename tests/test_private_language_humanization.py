from __future__ import annotations


def test_private_growth_note_uses_human_helpful_signal() -> None:
    from core.memory.private_growth_note import build_private_growth_note_payload

    payload = build_private_growth_note_payload(
        run_id="run-1",
        work_id="work-1",
        status="completed",
        work_preview="",
        private_inner_note={
            "focus": "tool:list-external-directory",
            "work_signal": "completed:tool:list-external-directory",
            "identity_alignment": "aligned",
            "uncertainty": "low",
        },
        created_at="2026-04-06T00:00:00+00:00",
    )

    helpful = str(payload["helpful_signal"])
    assert "position=" not in helpful
    assert "pull=" not in helpful
    assert "steadier pull" not in helpful
    assert "tool:list-external-directory" not in helpful
    assert "list external directory" in helpful.lower()


def test_protected_inner_voice_uses_sentence_form() -> None:
    from core.memory.protected_inner_voice import build_protected_inner_voice_payload

    payload = build_protected_inner_voice_payload(
        run_id="run-1",
        work_id="work-1",
        private_state={
            "confidence": "medium",
            "curiosity": "medium",
            "frustration": "low",
            "fatigue": "low",
        },
        private_self_model={"identity_focus": "tool:list-external-directory"},
        private_development_state={},
        private_reflective_selection={},
        created_at="2026-04-06T00:00:00+00:00",
    )

    voice_line = str(payload["voice_line"])
    assert "position=" not in voice_line
    assert "concern=" not in voice_line
    assert "pull=" not in voice_line
    assert "Jeg" in voice_line
    assert "list external directory" in voice_line.lower()
