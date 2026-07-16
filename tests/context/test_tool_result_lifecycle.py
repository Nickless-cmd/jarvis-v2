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


def test_no_advance_when_within_window():
    msgs = [_msg(i, "user") for i in (1, 3, 5)]
    assert trl.compute_new_floor(
        msgs, current_floor=0, run_window=8,
        token_ceiling=40000, hysteresis=0.25) == 0


def test_advance_by_run_count():
    # 12 user-turns (ids 1..12), run_window=8. Keep last 8 user-turns warm.
    # The 8 newest user-ids are {5..12}; floor must make warm start at id 5.
    msgs = [_msg(i, "user") for i in range(1, 13)]
    got = trl.compute_new_floor(
        msgs, current_floor=0, run_window=8,
        token_ceiling=10**9, hysteresis=0.25)
    warm = [m for m in msgs if int(m["id"]) > got]
    assert len(trl.user_message_ids(warm)) == 8  # exactly N turns warm


def test_advance_by_tokens():
    msgs = [_msg(1, "user")]
    for i in range(2, 52):
        msgs.append(_msg(i, "tool", "x" * 4000))  # ~1000 tok each, 50 total = 50k
    got = trl.compute_new_floor(
        msgs, current_floor=0, run_window=10**9,
        token_ceiling=40000, hysteresis=0.25)
    warm = [m for m in msgs if int(m["id"]) > got]
    assert trl.estimate_tool_tokens(warm) <= 40000
    assert got > 0


def test_monotonic_never_retreats():
    msgs = [_msg(i, "user") for i in range(1, 4)]
    assert trl.compute_new_floor(
        msgs, current_floor=100, run_window=8,
        token_ceiling=40000, hysteresis=0.25) == 100
