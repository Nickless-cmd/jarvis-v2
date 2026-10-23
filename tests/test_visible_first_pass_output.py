"""Den første synlige modelstrøm må beholde tid internt, ikke på skærmen."""
from __future__ import annotations

import pathlib

import pytest

from core.services.visible_first_pass_output import FirstPassOutputFilter


def _stream(text: str, chunk: int) -> str:
    output = FirstPassOutputFilter()
    shown = "".join(output.feed(text[i:i + chunk]) for i in range(0, len(text), chunk))
    return shown + output.flush()


@pytest.mark.parametrize("chunk", range(1, 48))
def test_first_pass_skjuler_transskript_tid_for_alle_chunkgraenser(chunk):
    text = (
        "[2026-10-23 21:59] [2026-10-23 21:59] "
        "Det synlige svar."
    )
    assert _stream(text, chunk) == "Det synlige svar."


def test_first_pass_bevarer_capability_filteret():
    text = 'før <capability-call id="tool:read" /> efter'
    shown = _stream(text, 3)
    assert "capability-call" not in shown
    assert "før" in shown and "efter" in shown


def test_filteret_er_koblet_paa_first_pass_i_runtime():
    source = pathlib.Path("core/services/visible_runs.py").read_text()
    assert "markup_buffer = FirstPassOutputFilter()" in source
    assert "safe_text = markup_buffer.feed(item.delta)" in source
    assert "remaining = markup_buffer.flush()" in source
