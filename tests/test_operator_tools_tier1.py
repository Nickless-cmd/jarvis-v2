"""Smoke tests for tier-1 operator tools (clipboard, windows, scroll/drag, processes).

These test the Python-side wrappers and exec stubs, mocking the bridge call.
Full E2E tests require a running JarvisX Electron — out of scope here.
"""

from unittest.mock import AsyncMock, patch
import pytest


# ── helpers ──────────────────────────────────────────────────────────────

def _patch_bridge(return_value: dict):
    """Patch _bridge_call in operator_tools with an AsyncMock."""
    return patch(
        "core.tools.operator_tools._bridge_call",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── clipboard ─────────────────────────────────────────────────────────────

def test_clipboard_read_dispatches():
    from core.tools.simple_tools import _exec_operator_clipboard_read
    with _patch_bridge({"text": "hello"}) as mock:
        result = _exec_operator_clipboard_read({"_runtime_user_id": "test-user"})
        assert mock.called
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("tool") == "operator_clipboard_read"
    # _run_operator_async wraps results as {"status": "ok", "result": {...}}
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("text") == "hello"


def test_clipboard_write_dispatches():
    from core.tools.simple_tools import _exec_operator_clipboard_write
    with _patch_bridge({"written": True, "length": 5}) as mock:
        result = _exec_operator_clipboard_write({"_runtime_user_id": "test-user", "text": "hello"})
        assert mock.called
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("tool") == "operator_clipboard_write"
        # Verify text was forwarded.
        assert call_kwargs.get("args", {}).get("text") == "hello"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("written") is True


def test_clipboard_write_requires_text():
    from core.tools.simple_tools import _exec_operator_clipboard_write
    result = _exec_operator_clipboard_write({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"
    assert "text" in result.get("error", "").lower()


# ── windows ───────────────────────────────────────────────────────────────

def test_list_windows_dispatches():
    from core.tools.simple_tools import _exec_operator_list_windows
    fake = {"count": 2, "windows": [{"title": "Foo", "id": 1}, {"title": "Bar", "id": 2}]}
    with _patch_bridge(fake) as mock:
        result = _exec_operator_list_windows({"_runtime_user_id": "test-user"})
        assert mock.called
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("tool") == "operator_list_windows"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("count") == 2


def test_focus_window_dispatches_by_title():
    from core.tools.simple_tools import _exec_operator_focus_window
    with _patch_bridge({"focused": True, "title": "Firefox", "id": 42}) as mock:
        result = _exec_operator_focus_window({"_runtime_user_id": "test-user", "title_substring": "fire"})
        assert mock.called
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("tool") == "operator_focus_window"
        assert call_kwargs.get("args", {}).get("title_substring") == "fire"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("focused") is True


def test_focus_window_dispatches_by_handle():
    from core.tools.simple_tools import _exec_operator_focus_window
    with _patch_bridge({"focused": True, "title": "Terminal", "id": 99}) as mock:
        _exec_operator_focus_window({"_runtime_user_id": "test-user", "handle": 99})
        assert mock.called
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("args", {}).get("handle") == 99


def test_focus_window_requires_arg():
    from core.tools.simple_tools import _exec_operator_focus_window
    result = _exec_operator_focus_window({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"


# ── scroll / drag ─────────────────────────────────────────────────────────

def test_mouse_scroll_dispatches():
    from core.tools.simple_tools import _exec_operator_mouse_scroll
    with _patch_bridge({"scrolled": True, "direction": "down", "amount": 3}) as mock:
        result = _exec_operator_mouse_scroll({"_runtime_user_id": "test-user", "direction": "down"})
        assert mock.called
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("tool") == "operator_mouse_scroll"
        assert call_kwargs.get("args", {}).get("direction") == "down"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("scrolled") is True


def test_mouse_scroll_invalid_direction():
    from core.tools.simple_tools import _exec_operator_mouse_scroll
    result = _exec_operator_mouse_scroll({"_runtime_user_id": "test-user", "direction": "diagonal"})
    assert result.get("status") == "error"


def test_mouse_scroll_default_amount():
    from core.tools.simple_tools import _exec_operator_mouse_scroll
    with _patch_bridge({"scrolled": True, "direction": "up", "amount": 3}) as mock:
        _exec_operator_mouse_scroll({"_runtime_user_id": "test-user", "direction": "up"})
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("args", {}).get("amount") == 3


def test_mouse_drag_dispatches():
    from core.tools.simple_tools import _exec_operator_mouse_drag
    with _patch_bridge({"dragged": True, "from_x": 10, "from_y": 20, "to_x": 100, "to_y": 200, "button": "left"}) as mock:
        result = _exec_operator_mouse_drag({
            "_runtime_user_id": "test-user",
            "from_x": 10, "from_y": 20, "to_x": 100, "to_y": 200,
        })
        assert mock.called
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("tool") == "operator_mouse_drag"
        a = call_kwargs.get("args", {})
        assert a.get("from_x") == 10
        assert a.get("to_y") == 200
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("dragged") is True


def test_mouse_drag_requires_coords():
    from core.tools.simple_tools import _exec_operator_mouse_drag
    result = _exec_operator_mouse_drag({"_runtime_user_id": "test-user", "from_x": 10})
    assert result.get("status") == "error"


def test_mouse_drag_button_forwarded():
    from core.tools.simple_tools import _exec_operator_mouse_drag
    with _patch_bridge({"dragged": True}) as mock:
        _exec_operator_mouse_drag({
            "_runtime_user_id": "test-user",
            "from_x": 0, "from_y": 0, "to_x": 50, "to_y": 50,
            "button": "right",
        })
        a = mock.call_args.kwargs.get("args", {})
        assert a.get("button") == "right"


# ── processes ─────────────────────────────────────────────────────────────

def test_list_processes_dispatches():
    from core.tools.simple_tools import _exec_operator_list_processes
    fake = {"count": 3, "processes": [{"pid": 1, "name": "bash", "cpu": 0.1, "memMB": 10}]}
    with _patch_bridge(fake) as mock:
        result = _exec_operator_list_processes({"_runtime_user_id": "test-user"})
        assert mock.called
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("tool") == "operator_list_processes"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("count") == 3


def test_list_processes_filter_forwarded():
    from core.tools.simple_tools import _exec_operator_list_processes
    with _patch_bridge({"count": 1, "processes": []}) as mock:
        _exec_operator_list_processes({"_runtime_user_id": "test-user", "filter": "python"})
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("args", {}).get("filter") == "python"


def test_kill_process_dispatches():
    from core.tools.simple_tools import _exec_operator_kill_process
    with _patch_bridge({"approved": True, "killed": True, "pid": 1234}) as mock:
        result = _exec_operator_kill_process({
            "_runtime_user_id": "test-user",
            "pid": 1234,
            "_runtime_trust_all": True,  # skip approval in test
        })
        assert mock.called
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("tool") == "operator_kill_process"
        assert call_kwargs.get("args", {}).get("pid") == 1234
        assert call_kwargs.get("args", {}).get("skip_approval") is True
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("killed") is True


def test_kill_process_requires_pid():
    from core.tools.simple_tools import _exec_operator_kill_process
    result = _exec_operator_kill_process({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"
    assert "pid" in result.get("error", "").lower()


def test_kill_process_skip_approval_off_by_default():
    from core.tools.simple_tools import _exec_operator_kill_process
    with _patch_bridge({"approved": False, "killed": False, "pid": 999}) as mock:
        _exec_operator_kill_process({"_runtime_user_id": "test-user", "pid": 999})
        call_kwargs = mock.call_args.kwargs
        # Without _runtime_trust_all, skip_approval must be False.
        assert call_kwargs.get("args", {}).get("skip_approval") is False
