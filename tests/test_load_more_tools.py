from __future__ import annotations

from core.tools.load_more_tools import _tool_load_more_tools


def test_load_more_tools_returns_full_native_schema():
    out = _tool_load_more_tools({"names": ["read_file"]})

    assert out["status"] == "ok"
    assert out["added"] == ["read_file"]
    assert out["tool_definitions"][0]["type"] == "function"
    assert out["tool_definitions"][0]["function"]["name"] == "read_file"
