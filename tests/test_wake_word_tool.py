"""Thin coverage test for core.tools.wake_word_tool.

Import-smoke + assert the egress-free Central observation (record_private) is
wired at the wake detection point. Does NOT start the listener.
"""
from __future__ import annotations

import inspect


def test_import_smoke():
    import core.tools.wake_word_tool as mod
    assert hasattr(mod, "wake_word_status")
    assert hasattr(mod, "WAKE_WORD_TOOL_DEFINITIONS")


def test_source_wires_record_private():
    import core.tools.wake_word_tool as mod
    src = inspect.getsource(mod)
    assert "record_private" in src
