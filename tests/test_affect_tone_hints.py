from __future__ import annotations


def test_no_active_concepts_returns_empty(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(ec, "get_active_emotion_concepts", lambda: [])
    assert am.compute_affect_tone_hints() == []


def test_below_threshold_intensity_filtered_out(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "joy", "intensity": 0.2}],
    )
    assert am.compute_affect_tone_hints() == []


def test_active_joy_returns_joy_tone_hint(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "joy", "intensity": 0.6}],
    )
    hints = am.compute_affect_tone_hints()
    assert len(hints) == 1
    # Commit 1e538f31 ("signals over form"): _TONE_HINTS now maps concepts to
    # bare signal names instead of prescriptive Danish instructions.
    assert hints[0] == "joy"


def test_top_3_cap_when_5_concepts_active(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [
            {"concept": "joy", "intensity": 0.8},
            {"concept": "wonder", "intensity": 0.7},
            {"concept": "warmth", "intensity": 0.6},
            {"concept": "pride", "intensity": 0.5},
            {"concept": "playfulness", "intensity": 0.4},
        ],
    )
    hints = am.compute_affect_tone_hints()
    assert len(hints) == 3


def test_ordered_by_intensity_desc(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [
            {"concept": "awe", "intensity": 0.4},
            {"concept": "wonder", "intensity": 0.8},
            {"concept": "joy", "intensity": 0.5},
        ],
    )
    hints = am.compute_affect_tone_hints()
    # Highest intensity (wonder=0.8) is surfaced first; bare signal-name form.
    assert hints[0] == "wonder"


def test_concept_without_tone_mapping_skipped(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "vigilance", "intensity": 0.7}],
    )
    assert am.compute_affect_tone_hints() == []


def test_tone_disabled_returns_empty(isolated_runtime, monkeypatch) -> None:
    from core.runtime import settings as settings_mod
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    original = settings_mod.load_settings
    def patched():
        s = original()
        s.emotion_concepts_tone_injection_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "joy", "intensity": 0.6}],
    )
    assert am.compute_affect_tone_hints() == []


def test_distress_concepts_get_tone_hints(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [
            {"concept": "frustration_blocked", "intensity": 0.5},
            {"concept": "stuck", "intensity": 0.4},
        ],
    )
    hints = am.compute_affect_tone_hints()
    # Bare signal-name form (commit 1e538f31): lowercase concept keys.
    assert "frustration_blocked" in hints
    assert "stuck" in hints
