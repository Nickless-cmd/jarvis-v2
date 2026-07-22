"""Test for the unconditional memory-consolidation nudge section."""

from __future__ import annotations

from core.services.memory_consolidation_nudge import memory_consolidation_nudge_section


def test_nudge_is_english_and_actionable():
    s = memory_consolidation_nudge_section()
    assert s
    # English after audit #3 (2026-07-22) — no leftover Danish.
    assert "Before you finish" in s
    assert "Call the tool" in s
    assert "I'll remember that" in s
    # Old Danish phrasing gone.
    assert "Inden du afslutter" not in s
    assert "jeg husker det" not in s


def test_nudge_is_stable_single_line_reminder():
    # Fires every turn — must stay short and deterministic.
    assert memory_consolidation_nudge_section() == memory_consolidation_nudge_section()
    assert memory_consolidation_nudge_section().startswith("💾")
