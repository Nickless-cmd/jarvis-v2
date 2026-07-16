from core.runtime.settings import RuntimeSettings


def test_lifecycle_settings_defaults():
    s = RuntimeSettings()
    assert s.tool_result_lifecycle_enabled is False
    assert s.tool_warm_run_window == 8
    assert s.tool_warm_token_ceiling == 40000
    assert s.tool_warm_hysteresis == 0.25
    assert s.tool_run_hot_budget == 30000
