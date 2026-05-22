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


class TestCandidatePenalty:
    """2026-05-22 (Claude): [CANDIDATE→ entries (legacy bulk-rewrite of
    fake `[MEMORY.md]` provenance) get 0.3x score penalty so they don't
    surface above curated workspace memory. They're NOT quarantined —
    still usable as low-confidence hints if nothing else is available.
    """

    def test_candidate_token_not_quarantined(self):
        """CANDIDATE entries are NOT quarantined — they're just demoted."""
        from core.services.memory_search import _is_quarantined
        text = "- [CANDIDATE→MEMORY.md] some proposed fact"
        assert _is_quarantined(text) is False

    def test_candidate_penalty_applied(self):
        """A candidate entry with high raw similarity must rank below
        non-candidate entries with comparable similarity."""
        # Behavioral test: query something that matches both candidate and
        # curated entries; verify the top result is not a candidate.
        from core.services.memory_search import search_memory
        results = search_memory("ChiefOne hardware", limit=5)
        if not results:
            return  # nothing to verify (empty corpus)
        # Top result should not be a candidate when curated content exists
        top = results[0]
        assert not top.get("candidate_penalty", False), (
            f"Top result is CANDIDATE — penalty failed:\n{top}"
        )
