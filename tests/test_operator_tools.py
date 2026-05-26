"""Tests for operator_tools (JarvisX bridge tool wrappers).

Most of the dispatch logic lives in core.services.jarvisx_bridge (tested
in test_jarvisx_bridge.py). These tests cover the thin wrapper layer.
"""
from __future__ import annotations

import pytest


def test_operator_read_file_sync_wrapper_exists():
    """The sync wrapper is what _exec_operator_read_file ultimately calls."""
    from core.tools import operator_tools
    assert hasattr(operator_tools, "operator_read_file")
    assert hasattr(operator_tools, "operator_read_file_async")


@pytest.mark.asyncio
async def test_async_wrapper_raises_on_bridge_not_connected():
    """When no bridge is registered for the user, async wrapper raises."""
    from core.services.jarvisx_bridge import bridge_registry
    bridge_registry.clear()

    from core.tools.operator_tools import operator_read_file_async
    with pytest.raises(RuntimeError, match="bridge_not_connected"):
        await operator_read_file_async(
            path="/tmp/x.txt", user_id="nobody", timeout_s=0.5,
        )


# ── Phase 2 wrappers ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_phase2_wrappers_exist():
    """All Phase 2 async wrappers are importable and callable."""
    from core.tools import operator_tools
    for name in (
        "operator_write_file_async",
        "operator_edit_file_async",
        "operator_glob_async",
        "operator_grep_async",
        "operator_list_dir_async",
    ):
        assert hasattr(operator_tools, name), f"missing {name}"
        assert callable(getattr(operator_tools, name))


@pytest.mark.asyncio
async def test_write_file_dispatches_correctly(monkeypatch):
    """Wrapper passes path+content to bridge_registry.dispatch."""
    captured = {}

    async def _fake_dispatch(*, user_id, tool, args, timeout_s):
        captured.update({"tool": tool, "args": args, "user_id": user_id})
        return {"status": "ok", "result": {"bytes_written": 42, "path": args["path"]}}

    monkeypatch.setattr(
        "core.services.jarvisx_bridge.bridge_registry.dispatch", _fake_dispatch,
    )
    from core.tools.operator_tools import operator_write_file_async
    result = await operator_write_file_async(
        path="/tmp/x.txt", content="hello", user_id="u1",
    )
    assert captured["tool"] == "operator_write_file"
    assert captured["args"]["path"] == "/tmp/x.txt"
    assert captured["args"]["content"] == "hello"
    assert result["bytes_written"] == 42


@pytest.mark.asyncio
async def test_bash_dispatches_with_approval_flow(monkeypatch):
    """operator_bash_async passes command + caps timeout at 300s."""
    captured = {}

    async def _fake_dispatch(*, user_id, tool, args, timeout_s):
        captured.update({"tool": tool, "args": args, "outer_timeout": timeout_s})
        return {
            "status": "ok",
            "result": {
                "approved": True, "stdout": "hi\n", "stderr": "",
                "exit_code": 0, "timed_out": False,
            },
        }

    monkeypatch.setattr(
        "core.services.jarvisx_bridge.bridge_registry.dispatch", _fake_dispatch,
    )
    from core.tools.operator_tools import operator_bash_async
    result = await operator_bash_async(
        command="echo hi", cwd="/tmp", timeout_s=10.0, user_id="u1",
    )
    assert captured["tool"] == "operator_bash"
    assert captured["args"]["command"] == "echo hi"
    assert captured["args"]["cwd"] == "/tmp"
    # Outer bridge-call timeout = command timeout + 120s buffer for approval
    assert captured["outer_timeout"] == 10.0 + 120.0
    assert result["approved"] is True
    assert result["exit_code"] == 0


@pytest.mark.asyncio
async def test_bash_caps_timeout_at_300s(monkeypatch):
    """Excessive timeout values are clamped to 300s max."""
    captured = {}

    async def _fake_dispatch(*, user_id, tool, args, timeout_s):
        captured["args"] = args
        return {"status": "ok", "result": {}}

    monkeypatch.setattr(
        "core.services.jarvisx_bridge.bridge_registry.dispatch", _fake_dispatch,
    )
    from core.tools.operator_tools import operator_bash_async
    await operator_bash_async(command="sleep 9999", timeout_s=99999.0, user_id="u1")
    assert captured["args"]["timeout_s"] == 300.0


@pytest.mark.asyncio
async def test_grep_dispatches_with_optional_args(monkeypatch):
    """Wrapper passes through pattern + optional path/glob/case_insensitive."""
    captured = {}

    async def _fake_dispatch(*, user_id, tool, args, timeout_s):
        captured.update({"tool": tool, "args": args})
        return {"status": "ok", "result": [{"file": "/x", "line": 1, "text": "foo"}]}

    monkeypatch.setattr(
        "core.services.jarvisx_bridge.bridge_registry.dispatch", _fake_dispatch,
    )
    from core.tools.operator_tools import operator_grep_async
    result = await operator_grep_async(
        pattern="foo", path="/home/bs", case_insensitive=True, user_id="u1",
    )
    assert captured["tool"] == "operator_grep"
    assert captured["args"]["pattern"] == "foo"
    assert captured["args"]["path"] == "/home/bs"
    assert captured["args"]["case_insensitive"] is True
    assert len(result) == 1
