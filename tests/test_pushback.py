from __future__ import annotations

from core.services.emotional_controls import EmotionalSnapshot


def test_affective_pushback_firm_when_feeling_and_evidence_align(monkeypatch):
    from core.services import pushback

    monkeypatch.setattr(
        "core.services.emotional_controls.read_emotional_snapshot",
        lambda: EmotionalSnapshot(
            frustration=0.82,
            confidence=0.6,
            fatigue=0.1,
            primary_mood="distressed",
            intensity=0.8,
        ),
    )
    monkeypatch.setattr(pushback, "_conflict_with_decisions", lambda _message: [])

    section = pushback.affective_pushback_section("bare push nu uden test")

    assert section is not None
    assert "feeling=irritation" in section
    assert "action=firm_pushback" in section
    assert "risk marker" in section
    assert "Følelser må starte pushback" in section


def test_affective_pushback_checks_when_feeling_has_weak_evidence(monkeypatch):
    from core.services import pushback

    monkeypatch.setattr(
        "core.services.emotional_controls.read_emotional_snapshot",
        lambda: EmotionalSnapshot(
            frustration=0.1,
            confidence=0.42,
            fatigue=0.2,
            primary_mood="neutral",
            intensity=0.1,
        ),
    )
    monkeypatch.setattr(pushback, "_conflict_with_decisions", lambda _message: [])

    section = pushback.affective_pushback_section("hvad tænker du?")

    assert section is not None
    assert "feeling=unease" in section
    assert "action=ask_or_check" in section
    assert "evidence: weak/none" in section


def test_affective_pushback_omits_when_no_affective_pressure(monkeypatch):
    from core.services import pushback

    monkeypatch.setattr(
        "core.services.emotional_controls.read_emotional_snapshot",
        lambda: EmotionalSnapshot(
            frustration=0.1,
            confidence=0.9,
            fatigue=0.1,
            primary_mood="content",
            intensity=0.2,
        ),
    )

    assert pushback.affective_pushback_section("deploy nu") is None


def test_conflict_with_decisions_detects_conflict():
    """Integration test: _conflict_with_decisions should find conflicts
    against active behavioral decisions without being mocked away."""
    from core.services import pushback
    from core.runtime.db_decisions import create_decision, set_status

    # Create an active decision with a short target that appears in user msg
    d = create_decision(
        directive="undgå at slette filer",
        rationale="Backup-first policy",
    )
    set_status(d["decision_id"], "active")

    try:
        flags = pushback._conflict_with_decisions("slette filer nu")
        assert len(flags) >= 1, f"Expected conflict flag, got: {flags}"
        assert "forpligtelse" in flags[0]
    finally:
        set_status(d["decision_id"], "revoked")
