from __future__ import annotations
from core.tools.simple_tools import _exec_read_memory_topic, _exec_write_memory_topic

def test_write_then_read_tool_roundtrip(isolated_runtime):
    w = _exec_write_memory_topic({"slug": "alpha", "title": "Alpha",
                                  "hook": "om alpha", "body": "fuld krop"})
    assert w.get("confirmed") is True
    r = _exec_read_memory_topic({"slug": "alpha"})
    assert "fuld krop" in (r.get("content") or "")

def test_read_missing_tool_returns_not_found(isolated_runtime):
    r = _exec_read_memory_topic({"slug": "nope"})
    assert r.get("found") is False
