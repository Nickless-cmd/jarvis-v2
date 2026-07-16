from core.runtime.settings import RuntimeSettings
from core.context import tool_result_lifecycle as trl


def _msg(mid, role, content="x"):
    return {"id": mid, "role": role, "content": content}


def test_lifecycle_settings_defaults():
    s = RuntimeSettings()
    assert s.tool_result_lifecycle_enabled is False
    assert s.tool_warm_run_window == 8
    assert s.tool_warm_token_ceiling == 40000
    assert s.tool_warm_hysteresis == 0.25
    assert s.tool_run_hot_budget == 30000


def test_user_message_ids_ascending():
    msgs = [_msg(1, "user"), _msg(2, "assistant"), _msg(3, "tool"),
            _msg(4, "user"), _msg(5, "assistant")]
    assert trl.user_message_ids(msgs) == [1, 4]


def test_estimate_tool_tokens_only_tool_role():
    msgs = [_msg(1, "user", "a" * 40), _msg(2, "tool", "b" * 40),
            _msg(3, "tool", "c" * 80)]
    assert trl.estimate_tool_tokens(msgs) == (40 // 4) + (80 // 4)
