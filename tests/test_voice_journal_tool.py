"""Thin coverage test for core.tools.voice_journal_tool.

Import-smoke + assert the egress-free Central observation (record_private) is
wired at the transcription point. Does NOT record audio.
"""
from __future__ import annotations

import inspect


def test_import_smoke():
    import core.tools.voice_journal_tool as mod
    assert hasattr(mod, "_exec_voice_journal")
    assert hasattr(mod, "VOICE_JOURNAL_TOOL_DEFINITIONS")


def test_source_wires_record_private():
    import core.tools.voice_journal_tool as mod
    src = inspect.getsource(mod)
    assert "record_private" in src
