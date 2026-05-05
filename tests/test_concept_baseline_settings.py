from __future__ import annotations


def test_emotion_concepts_baseline_settings_have_defaults(isolated_runtime) -> None:
    from core.runtime.settings import load_settings

    s = load_settings()
    assert s.emotion_concepts_tone_injection_enabled is True
    assert s.emotion_concepts_perception_focus_enabled is True
    assert s.concept_baseline_tracker_enabled is True
    assert s.emotion_concepts_tone_intensity_threshold == 0.3
    assert s.emotion_concepts_tone_max_hints == 3
    assert s.emotion_concepts_perception_max_foci == 3
    assert s.concept_baseline_drift_min_sustained_days == 14
    assert s.concept_baseline_drift_min_confidence == 0.7
    assert s.emotion_concepts_default_trigger_cooldown_seconds == 30
