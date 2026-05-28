"""Smoke tests for tier-3 operator tools: notify, watch_folder, unwatch_folder, watch_events, record_audio.

Tests the Python-side wrappers and exec stubs, mocking the bridge call.
Full E2E tests require a running JarvisX Electron with OS notification support / arecord / ffmpeg.
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


# ── operator_notify ───────────────────────────────────────────────────────

def test_notify_dispatches():
    from core.tools.simple_tools import _exec_operator_notify
    with _patch_bridge({"shown": True}) as mock:
        result = _exec_operator_notify({
            "_runtime_user_id": "test-user",
            "title": "Hello",
            "body": "World",
        })
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_notify"
        assert kwargs.get("args", {}).get("title") == "Hello"
        assert kwargs.get("args", {}).get("body") == "World"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("shown") is True


def test_notify_with_icon():
    from core.tools.simple_tools import _exec_operator_notify
    with _patch_bridge({"shown": True}) as mock:
        _exec_operator_notify({
            "_runtime_user_id": "test-user",
            "title": "Hi",
            "body": "Test",
            "icon": "/home/user/icon.png",
        })
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("icon") == "/home/user/icon.png"


def test_notify_without_icon():
    from core.tools.simple_tools import _exec_operator_notify
    with _patch_bridge({"shown": True}) as mock:
        _exec_operator_notify({
            "_runtime_user_id": "test-user",
            "title": "Hi",
            "body": "No icon",
        })
        args_sent = mock.call_args.kwargs.get("args", {})
        assert "icon" not in args_sent


def test_notify_requires_title():
    from core.tools.simple_tools import _exec_operator_notify
    result = _exec_operator_notify({"_runtime_user_id": "test-user", "body": "test"})
    assert result.get("status") == "error"
    assert "title" in result.get("error", "").lower()


def test_notify_requires_nonempty_title():
    from core.tools.simple_tools import _exec_operator_notify
    result = _exec_operator_notify({"_runtime_user_id": "test-user", "title": "", "body": "test"})
    assert result.get("status") == "error"


def test_notify_requires_body():
    from core.tools.simple_tools import _exec_operator_notify
    result = _exec_operator_notify({"_runtime_user_id": "test-user", "title": "Hi"})
    assert result.get("status") == "error"
    assert "body" in result.get("error", "").lower()


# ── operator_watch_folder ─────────────────────────────────────────────────

def test_watch_folder_dispatches():
    from core.tools.simple_tools import _exec_operator_watch_folder
    with _patch_bridge({"watching": True, "watcher_id": "abc-123"}) as mock:
        result = _exec_operator_watch_folder({
            "_runtime_user_id": "test-user",
            "path": "/tmp/test-watch",
        })
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_watch_folder"
        assert kwargs.get("args", {}).get("path") == "/tmp/test-watch"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("watching") is True


def test_watch_folder_default_recursive_false():
    from core.tools.simple_tools import _exec_operator_watch_folder
    with _patch_bridge({"watching": True, "watcher_id": "x"}) as mock:
        _exec_operator_watch_folder({"_runtime_user_id": "test-user", "path": "/tmp"})
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("recursive") is False


def test_watch_folder_custom_options():
    from core.tools.simple_tools import _exec_operator_watch_folder
    with _patch_bridge({"watching": True, "watcher_id": "y"}) as mock:
        _exec_operator_watch_folder({
            "_runtime_user_id": "test-user",
            "path": "/home/user/docs",
            "recursive": True,
            "debounce_ms": 1000,
        })
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("recursive") is True
        assert args_sent.get("debounce_ms") == 1000


def test_watch_folder_requires_path():
    from core.tools.simple_tools import _exec_operator_watch_folder
    result = _exec_operator_watch_folder({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"
    assert "path" in result.get("error", "").lower()


def test_watch_folder_requires_nonempty_path():
    from core.tools.simple_tools import _exec_operator_watch_folder
    result = _exec_operator_watch_folder({"_runtime_user_id": "test-user", "path": ""})
    assert result.get("status") == "error"


# ── operator_unwatch_folder ───────────────────────────────────────────────

def test_unwatch_folder_dispatches():
    from core.tools.simple_tools import _exec_operator_unwatch_folder
    with _patch_bridge({"stopped": True, "watcher_id": "abc-123"}) as mock:
        result = _exec_operator_unwatch_folder({
            "_runtime_user_id": "test-user",
            "watcher_id": "abc-123",
        })
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_unwatch_folder"
        assert kwargs.get("args", {}).get("watcher_id") == "abc-123"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("stopped") is True


def test_unwatch_folder_requires_watcher_id():
    from core.tools.simple_tools import _exec_operator_unwatch_folder
    result = _exec_operator_unwatch_folder({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"
    assert "watcher_id" in result.get("error", "").lower()


def test_unwatch_folder_requires_nonempty_watcher_id():
    from core.tools.simple_tools import _exec_operator_unwatch_folder
    result = _exec_operator_unwatch_folder({"_runtime_user_id": "test-user", "watcher_id": ""})
    assert result.get("status") == "error"


# ── operator_watch_events ─────────────────────────────────────────────────

def test_watch_events_dispatches():
    from core.tools.simple_tools import _exec_operator_watch_events
    events = [{"path": "/tmp/foo.txt", "event_type": "change", "timestamp": 1234567890}]
    with _patch_bridge({"events": events, "count": 1}) as mock:
        result = _exec_operator_watch_events({
            "_runtime_user_id": "test-user",
            "watcher_id": "abc-123",
        })
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_watch_events"
        assert kwargs.get("args", {}).get("watcher_id") == "abc-123"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("count") == 1


def test_watch_events_default_max():
    from core.tools.simple_tools import _exec_operator_watch_events
    with _patch_bridge({"events": [], "count": 0}) as mock:
        _exec_operator_watch_events({"_runtime_user_id": "test-user", "watcher_id": "x"})
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("max") == 100


def test_watch_events_custom_max():
    from core.tools.simple_tools import _exec_operator_watch_events
    with _patch_bridge({"events": [], "count": 0}) as mock:
        _exec_operator_watch_events({
            "_runtime_user_id": "test-user",
            "watcher_id": "x",
            "max": 50,
        })
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("max") == 50


def test_watch_events_max_clamped():
    from core.tools.simple_tools import _exec_operator_watch_events
    with _patch_bridge({"events": [], "count": 0}) as mock:
        _exec_operator_watch_events({
            "_runtime_user_id": "test-user",
            "watcher_id": "x",
            "max": 99999,
        })
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("max") <= 1000


def test_watch_events_requires_watcher_id():
    from core.tools.simple_tools import _exec_operator_watch_events
    result = _exec_operator_watch_events({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"
    assert "watcher_id" in result.get("error", "").lower()


# ── operator_record_audio ─────────────────────────────────────────────────

def test_record_audio_dispatches():
    from core.tools.simple_tools import _exec_operator_record_audio
    with _patch_bridge({"recorded": True, "path": "/tmp/rec.wav", "duration_s": 5, "size_bytes": 441044}) as mock:
        result = _exec_operator_record_audio({
            "_runtime_user_id": "test-user",
            "duration_s": 5,
        })
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_record_audio"
        assert kwargs.get("args", {}).get("duration_s") == 5
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("recorded") is True


def test_record_audio_with_output_path():
    from core.tools.simple_tools import _exec_operator_record_audio
    with _patch_bridge({"recorded": True, "path": "/custom/out.wav", "duration_s": 3, "size_bytes": 264000}) as mock:
        _exec_operator_record_audio({
            "_runtime_user_id": "test-user",
            "duration_s": 3,
            "output_path": "/custom/out.wav",
        })
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("output_path") == "/custom/out.wav"


def test_record_audio_with_device():
    from core.tools.simple_tools import _exec_operator_record_audio
    with _patch_bridge({"recorded": True, "path": "/tmp/x.wav", "duration_s": 2, "size_bytes": 176400}) as mock:
        _exec_operator_record_audio({
            "_runtime_user_id": "test-user",
            "duration_s": 2,
            "device": "hw:1,0",
        })
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("device") == "hw:1,0"


def test_record_audio_requires_duration():
    from core.tools.simple_tools import _exec_operator_record_audio
    result = _exec_operator_record_audio({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"
    assert "duration" in result.get("error", "").lower()


def test_record_audio_rejects_zero_duration():
    from core.tools.simple_tools import _exec_operator_record_audio
    result = _exec_operator_record_audio({"_runtime_user_id": "test-user", "duration_s": 0})
    assert result.get("status") == "error"


def test_record_audio_rejects_too_long():
    from core.tools.simple_tools import _exec_operator_record_audio
    result = _exec_operator_record_audio({"_runtime_user_id": "test-user", "duration_s": 999})
    assert result.get("status") == "error"


def test_record_audio_rejects_non_integer_duration():
    from core.tools.simple_tools import _exec_operator_record_audio
    result = _exec_operator_record_audio({"_runtime_user_id": "test-user", "duration_s": "bad"})
    assert result.get("status") == "error"


def test_record_audio_skip_approval_from_trust_all():
    """_runtime_trust_all flag sets skip_approval=True (bypasses dialog in E2E)."""
    from core.tools.simple_tools import _exec_operator_record_audio
    with _patch_bridge({"recorded": False, "reason": "user_rejected"}) as mock:
        _exec_operator_record_audio({
            "_runtime_user_id": "test-user",
            "_runtime_trust_all": True,
            "duration_s": 1,
        })
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("skip_approval") is True


def test_record_audio_approval_not_skipped_by_default():
    from core.tools.simple_tools import _exec_operator_record_audio
    with _patch_bridge({"recorded": True, "path": "/tmp/r.wav", "duration_s": 1, "size_bytes": 88200}) as mock:
        _exec_operator_record_audio({
            "_runtime_user_id": "test-user",
            "duration_s": 1,
        })
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("skip_approval") is False


# ── async wrappers (operator_tools.py) ───────────────────────────────────

@pytest.mark.asyncio
async def test_notify_async_passes_args():
    from core.tools.operator_tools import operator_notify_async
    with _patch_bridge({"shown": True}) as mock:
        result = await operator_notify_async(
            title="Alert", body="Something happened", user_id="test-user",
            icon="/path/to/icon.png",
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_notify"
        args_sent = kwargs.get("args", {})
        assert args_sent.get("title") == "Alert"
        assert args_sent.get("body") == "Something happened"
        assert args_sent.get("icon") == "/path/to/icon.png"
    assert result.get("shown") is True


@pytest.mark.asyncio
async def test_watch_folder_async_passes_args():
    from core.tools.operator_tools import operator_watch_folder_async
    with _patch_bridge({"watching": True, "watcher_id": "w-1"}) as mock:
        result = await operator_watch_folder_async(
            path="/tmp/watched", user_id="test-user", recursive=True, debounce_ms=1000,
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_watch_folder"
        args_sent = kwargs.get("args", {})
        assert args_sent.get("path") == "/tmp/watched"
        assert args_sent.get("recursive") is True
        assert args_sent.get("debounce_ms") == 1000
    assert result.get("watcher_id") == "w-1"


@pytest.mark.asyncio
async def test_unwatch_folder_async_passes_args():
    from core.tools.operator_tools import operator_unwatch_folder_async
    with _patch_bridge({"stopped": True, "watcher_id": "w-1"}) as mock:
        result = await operator_unwatch_folder_async(watcher_id="w-1", user_id="test-user")
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_unwatch_folder"
        assert kwargs.get("args", {}).get("watcher_id") == "w-1"
    assert result.get("stopped") is True


@pytest.mark.asyncio
async def test_watch_events_async_passes_args():
    from core.tools.operator_tools import operator_watch_events_async
    with _patch_bridge({"events": [], "count": 0}) as mock:
        result = await operator_watch_events_async(
            watcher_id="w-2", user_id="test-user", max=50,
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_watch_events"
        args_sent = kwargs.get("args", {})
        assert args_sent.get("watcher_id") == "w-2"
        assert args_sent.get("max") == 50
    assert result.get("count") == 0


@pytest.mark.asyncio
async def test_record_audio_async_passes_args():
    from core.tools.operator_tools import operator_record_audio_async
    with _patch_bridge({"recorded": True, "path": "/tmp/r.wav", "duration_s": 10, "size_bytes": 882000}) as mock:
        result = await operator_record_audio_async(
            duration_s=10, user_id="test-user",
            output_path="/tmp/r.wav", device="hw:0,0", skip_approval=True,
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_record_audio"
        args_sent = kwargs.get("args", {})
        assert args_sent.get("duration_s") == 10
        assert args_sent.get("output_path") == "/tmp/r.wav"
        assert args_sent.get("device") == "hw:0,0"
        assert args_sent.get("skip_approval") is True
    assert result.get("recorded") is True
