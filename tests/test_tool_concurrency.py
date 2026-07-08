# tests/test_tool_concurrency.py
from core.services.tool_concurrency import (
    is_parallelizable, concurrency_mode, _PARALLEL_SAFE, _MAX_CONCURRENCY,
)


def _call(name):
    return {"function": {"name": name, "arguments": {}}}


def test_allowlist_has_core_readers_not_writers():
    assert "read_file" in _PARALLEL_SAFE
    assert "search_memory" in _PARALLEL_SAFE
    assert "write_file" not in _PARALLEL_SAFE
    assert "operator_bash" not in _PARALLEL_SAFE
    assert "operator_write_file" not in _PARALLEL_SAFE


def test_all_safe_two_plus_on_is_parallelizable():
    calls = [_call("read_file"), _call("search_memory")]
    assert is_parallelizable(calls, mode="on") is True


def test_one_unsafe_present_blocks_whole_round():
    calls = [_call("read_file"), _call("write_file")]
    assert is_parallelizable(calls, mode="on") is False


def test_single_call_not_parallelizable():
    assert is_parallelizable([_call("read_file")], mode="on") is False


def test_mode_off_never_parallelizes():
    calls = [_call("read_file"), _call("search_memory")]
    assert is_parallelizable(calls, mode="off") is False


def test_unknown_tool_not_parallelizable():
    calls = [_call("read_file"), _call("some_new_tool_xyz")]
    assert is_parallelizable(calls, mode="on") is False


def test_empty_or_malformed_calls_safe():
    assert is_parallelizable([], mode="on") is False
    assert is_parallelizable([{"function": {}}, {"function": {}}], mode="on") is False


def test_concurrency_mode_defaults_off(monkeypatch):
    monkeypatch.delenv("JARVIS_TOOL_CONCURRENCY_MODE", raising=False)
    monkeypatch.setattr("core.runtime.settings.load_settings",
                        lambda: type("S", (), {"extra": {}})())
    assert concurrency_mode() == "off"


def test_concurrency_mode_env_wins(monkeypatch):
    monkeypatch.setenv("JARVIS_TOOL_CONCURRENCY_MODE", "on")
    assert concurrency_mode() == "on"


def test_max_concurrency_is_positive():
    assert _MAX_CONCURRENCY >= 2
