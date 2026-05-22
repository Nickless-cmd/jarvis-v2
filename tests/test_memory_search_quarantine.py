"""2026-05-22: Quarantine filter in memory_search.

After hallucinations were found in daily memory (Codex diagnosis),
search_memory was extended to filter chunks marked with [QUARANTINED
or [QUARANTINE NOTE prefixes. The marker stays in source files for
audit but cannot resurface as evidence.
"""
from __future__ import annotations

from core.services.memory_search import _is_quarantined


def test_quarantined_marker_detected():
    quarantined = (
        "[QUARANTINED 2026-05-22 — HALLUCINATION] "
        "~~Assets domain assets.srvlab.dk serves...~~ FALSE."
    )
    assert _is_quarantined(quarantined) is True


def test_quarantine_note_detected():
    note = "[QUARANTINE NOTE 2026-05-22 (Claude)]: this entry corrects ..."
    assert _is_quarantined(note) is True


def test_normal_text_not_quarantined():
    assert _is_quarantined("Subdomains: jarvis.srvlab.dk, admin.srvlab.dk") is False
    assert _is_quarantined("Just regular memory content.") is False


def test_empty_text_not_quarantined():
    assert _is_quarantined("") is False
    assert _is_quarantined(None) is False  # type: ignore[arg-type]


def test_quarantine_token_in_middle_still_detected():
    """Even if [QUARANTINED is not at line start, it still filters."""
    text = "Some note. [QUARANTINED 2026-05-22] Earlier claim was false."
    assert _is_quarantined(text) is True
