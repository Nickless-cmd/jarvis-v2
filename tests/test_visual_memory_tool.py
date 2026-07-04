"""Thin coverage test for core.tools.visual_memory_tool.

Import-smoke + assert the egress-free Central observation (record_private) is
wired at the perception point. Does NOT read the visual memory DB.
"""
from __future__ import annotations

import inspect


def test_import_smoke():
    import core.tools.visual_memory_tool as mod
    assert hasattr(mod, "_exec_read_visual_memory")
    assert hasattr(mod, "VISUAL_MEMORY_TOOL_DEFINITIONS")


def test_source_wires_record_private():
    import core.tools.visual_memory_tool as mod
    src = inspect.getsource(mod)
    assert "record_private" in src
