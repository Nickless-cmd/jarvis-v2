"""Regressionstests for core.tools.simple_tools_web.

Fokus: bash-output-klipning må ALDRIG NameError'e. _exec_bash brugte
_clip_head_tail uden at importere den → "'_clip_head_tail' is not defined"
ramte ethvert bash-kald med >16k output (fx `ls -la /tmp`) og fejlede
tool-kaldet i kode-lanen (2026-07-23).
"""
from __future__ import annotations

import core.tools.simple_tools_web as stw


def test_clip_head_tail_is_bound_in_module():
    """Symbolet skal være importeret i modulets namespace — ellers NameError
    ved runtime på stor bash-output."""
    assert hasattr(stw, "_clip_head_tail")
    assert callable(stw._clip_head_tail)


def test_clip_head_tail_clips_large_output_without_error():
    """Præcis den sti _exec_bash tager for stor output: klip til grænsen uden
    at kaste NameError, og resultatet er kortere end input."""
    big = "x" * (stw.MAX_BASH_OUTPUT_CHARS * 3)
    clipped = stw._clip_head_tail(big, limit=stw.MAX_BASH_OUTPUT_CHARS)
    assert isinstance(clipped, str)
    assert len(clipped) < len(big)


def test_exec_bash_empty_command_is_guarded():
    """Tom kommando kortsluttes før nogen exec/klip — ren fejl, ingen crash."""
    out = stw._exec_bash({"command": "   "})
    assert out.get("status") == "error"
    assert "command" in (out.get("error") or "").lower()
