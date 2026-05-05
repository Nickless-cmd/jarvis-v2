from __future__ import annotations


def test_self_repair_settings_have_defaults(isolated_runtime) -> None:
    from core.runtime.settings import load_settings

    settings = load_settings()
    assert settings.self_repair_engine_enabled is True
    assert settings.self_repair_default_cooldown_seconds == 300
    assert settings.self_repair_default_max_attempts_per_window == 3
    assert settings.self_repair_default_window_seconds == 3600
    assert settings.self_repair_default_auto_disable_after_escalations == 3
    assert settings.self_repair_default_auto_disable_window_hours == 24
