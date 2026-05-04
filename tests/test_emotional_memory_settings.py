from __future__ import annotations


def test_emotional_memory_settings_have_defaults(isolated_runtime) -> None:
    from core.runtime.settings import load_settings

    settings = load_settings()
    assert settings.emotional_memory_min_anchors == 2
    assert settings.emotional_memory_retention_recent_days == 30
    assert settings.emotional_memory_retention_aging_days == 180
    assert settings.emotional_memory_significance_intensity == 0.7
    assert settings.emotional_memory_significance_outcome == -0.3
