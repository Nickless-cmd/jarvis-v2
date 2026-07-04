"""Thin coverage test for core.tools.screen_tool.

Import-smoke + assert the egress-free Central observation (record_private) is
wired at the action dispatch point. Does NOT run xset.
"""
from __future__ import annotations

import inspect


def test_import_smoke():
    import core.tools.screen_tool as mod
    assert hasattr(mod, "_exec_screen_control")
    assert hasattr(mod, "SCREEN_TOOL_DEFINITIONS")


def test_source_wires_record_private():
    import core.tools.screen_tool as mod
    src = inspect.getsource(mod)
    assert "record_private" in src
