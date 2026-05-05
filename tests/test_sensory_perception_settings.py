from __future__ import annotations


def test_sensory_perception_settings_have_defaults(isolated_runtime) -> None:
    from core.runtime.settings import load_settings

    settings = load_settings()
    assert settings.sensory_perception_bridge_enabled is True
    assert settings.sensory_perception_jaccard_high_threshold == 0.15
    assert settings.sensory_perception_jaccard_medium_threshold == 0.25
    assert settings.sensory_perception_jaccard_change_threshold == 0.4
    assert settings.sensory_perception_time_window_hours == 2
    assert settings.sensory_perception_time_window_days == 7
    assert settings.sensory_perception_min_baseline_records == 3
    assert settings.sensory_perception_recent_baseline_size == 3
