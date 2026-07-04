"""Thin coverage test for core.tools.mic_listen_tool.

Import-smoke + assert the egress-free Central observation (record_private) is
wired at the perception point. Does NOT capture audio or hit the network.
"""
from __future__ import annotations

import inspect


def test_import_smoke():
    import core.tools.mic_listen_tool as mod
    assert hasattr(mod, "listen_and_transcribe")
    assert hasattr(mod, "MIC_LISTEN_TOOL_DEFINITIONS")


def test_source_wires_record_private():
    import core.tools.mic_listen_tool as mod
    src = inspect.getsource(mod)
    assert "record_private" in src
