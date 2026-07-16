import pytest

from core.runtime.settings import RuntimeSettings
from core.context import tool_result_lifecycle as trl

# These tests use fixed session-ids against the shared runtime DB. The cold_floor
# table is monotonic + persistent, so residue from a prior run would break the
# "starts at 0" assertions. Wipe the test session-ids around each test to keep
# the suite hermetic (does not touch any other session's floor).
_TEST_SIDS = ("sess-trl-test-1", "sess-trl-test-2",
              "sess-trl-eval-1", "sess-trl-eval-2")


@pytest.fixture(autouse=True)
def _clean_cold_floor_rows():
    def _wipe():
        try:
            from core.runtime.db import connect
            with connect() as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS tool_result_cold_floor ("
                    "session_id TEXT PRIMARY KEY, floor_id INTEGER NOT NULL, "
                    "updated_at TEXT NOT NULL)"
                )
                conn.executemany(
                    "DELETE FROM tool_result_cold_floor WHERE session_id = ?",
                    [(s,) for s in _TEST_SIDS],
                )
        except Exception:
            pass
    _wipe()
    yield
    _wipe()


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


def test_cold_floor_storage_roundtrip():
    sid = "sess-trl-test-1"
    assert trl.get_cold_floor(sid) == 0
    trl.set_cold_floor(sid, 42)
    assert trl.get_cold_floor(sid) == 42
    trl.set_cold_floor(sid, 100)
    assert trl.get_cold_floor(sid) == 100


def test_cold_floor_monotonic_write():
    sid = "sess-trl-test-2"
    trl.set_cold_floor(sid, 100)
    trl.set_cold_floor(sid, 50)
    assert trl.get_cold_floor(sid) == 100


def test_evaluate_and_advance_moves_floor(monkeypatch):
    sid = "sess-trl-eval-1"
    msgs = [_msg(i, "user") for i in range(1, 13)]
    monkeypatch.setattr(trl, "_load_session_messages", lambda s: msgs)

    class _S:
        tool_result_lifecycle_enabled = True
        tool_warm_run_window = 8
        tool_warm_token_ceiling = 40000
        tool_warm_hysteresis = 0.25

    new_floor = trl.evaluate_and_advance(sid, settings=_S())
    assert new_floor > 0
    assert trl.get_cold_floor(sid) == new_floor


def test_evaluate_noop_when_disabled(monkeypatch):
    sid = "sess-trl-eval-2"
    msgs = [_msg(i, "user") for i in range(1, 13)]
    monkeypatch.setattr(trl, "_load_session_messages", lambda s: msgs)

    class _S:
        tool_result_lifecycle_enabled = False
        tool_warm_run_window = 8
        tool_warm_token_ceiling = 40000
        tool_warm_hysteresis = 0.25

    assert trl.evaluate_and_advance(sid, settings=_S()) == 0
    assert trl.get_cold_floor(sid) == 0
