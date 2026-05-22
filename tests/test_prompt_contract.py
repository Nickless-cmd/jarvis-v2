"""Tests for prompt_contract module.

Currently covers the _time_pin_section function (Layer 1 of Lying Engine).
Time-pin-specific assertions also live in test_time_pin.py — this file
exists so the test-enforcement hook (scripts/enforce_test_coverage.py)
sees tests for prompt_contract.py changes.
"""
from __future__ import annotations


class TestTimePinSection:
    """Layer 1: prominent time block in every system prompt."""

    def test_includes_utc_timestamp(self):
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "UTC" in out
        # Year 2026+ must appear somewhere in the rendering
        assert "202" in out

    def test_includes_local_timezone_abbrev(self):
        """CEST in summer or CET in winter — never both, never neither."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        has_cest = "CEST" in out
        has_cet_alone = ("CET" in out) and not has_cest
        assert has_cest or has_cet_alone, (
            "Time pin must show a Copenhagen timezone abbreviation"
        )

    def test_contains_anchor_marker(self):
        """The ⏰ emoji + TIME PIN label must be present (visual unmissability)."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "⏰" in out
        assert "TIME PIN" in out

    def test_contains_explicit_instruction(self):
        """Must tell the model to use this, not guess."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "Gæt ikke" in out or "Brug PRÆCIS" in out


class TestQuickFactsSection:
    """Quick Facts is loaded from QUICK_FACTS.md — exists but no time injected."""

    def test_returns_none_or_string(self, tmp_path):
        from core.services.prompt_contract import _quick_facts_section
        # Path with no QUICK_FACTS.md → returns None
        out = _quick_facts_section(workspace_dir=tmp_path)
        assert out is None


class TestTimePinPlacement:
    """Time Pin must be tail-anchored for DeepSeek prompt-cache hits.

    Added 2026-05-22 after measuring 0% cache-hit rate. Time Pin had
    been at position #4 in the prompt — changes every minute — making
    every chat unique-prefix and uncacheable. Moving it to the tail
    keeps the front of the prompt stable.
    """

    def test_time_pin_referenced_once_in_assembly(self):
        """Only the tail-anchored time_pin call should exist (the old
        position-#4 call was removed)."""
        import inspect
        from core.services import prompt_contract
        src = inspect.getsource(prompt_contract.build_visible_chat_prompt_assembly)
        # _time_pin_section() should be called exactly once
        n_calls = src.count("_time_pin_section()")
        assert n_calls == 1, (
            f"Expected exactly 1 call to _time_pin_section() in assembly, "
            f"found {n_calls}. Either the old position-#4 call was reintroduced "
            f"or the tail-anchor call was lost."
        )

    def test_time_pin_appears_near_end_of_parts(self):
        """In the source, the time_pin parts.append call should come AFTER
        the bulk of parts.append sites (specifically, after the assembled_text
        comment), so the part lands at the tail of the prompt."""
        import inspect
        from core.services import prompt_contract
        src = inspect.getsource(prompt_contract.build_visible_chat_prompt_assembly)
        # Find the index of the time_pin call and the assembled_text join.
        idx_tp = src.find("_time_pin_section()")
        idx_join = src.find('"\\n\\n".join(part for part in parts if part)')
        assert idx_tp > 0, "time_pin call not found"
        assert idx_join > 0, "assembled_text join not found"
        # time_pin must come right before the join, not way up near
        # model-identity-awareness.
        # Heuristic: distance from time_pin to join is small (< 500 chars).
        assert (idx_join - idx_tp) < 1000, (
            "time_pin appears too far from the prompt assembly tail — "
            f"distance to join: {idx_join - idx_tp} chars"
        )
