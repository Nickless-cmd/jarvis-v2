"""Thin coverage test for core.tools.speak_tool.

Import-smoke + assert the egress-free Central observation (record_private) is
wired at the voice-output point. Does NOT synthesize speech.
"""
from __future__ import annotations

import inspect


def test_import_smoke():
    import core.tools.speak_tool as mod
    assert hasattr(mod, "_exec_speak")
    assert hasattr(mod, "SPEAK_TOOL_DEFINITIONS")


def test_source_wires_record_private():
    import core.tools.speak_tool as mod
    src = inspect.getsource(mod)
    assert "record_private" in src
