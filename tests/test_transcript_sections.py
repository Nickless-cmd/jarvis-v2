"""Tests for the compaction summariser's mechanical fallback (audit 2026-07-23).

When the cheap-lane summariser returns nothing usable, the fallback must NOT
collapse the whole arc into 200-char stubs — user turns (the intent) are kept
fuller than assistant turns, and the raw DB record is referenced.
"""

from __future__ import annotations

from unittest.mock import patch

from core.services.prompt_sections import transcript_sections as ts


def _fallback_summary(old_msgs):
    # Force the LLM path to yield nothing usable → mechanical fallback fires.
    with patch("core.context.compact_llm.call_compact_llm", return_value=""), \
         patch("core.context.compaction_policy.summary_looks_valid", return_value=False), \
         patch("core.context.compaction_policy.extract_summary", return_value=""), \
         patch("core.context.compaction_policy.fold_old_tool_results", side_effect=lambda m, keep=0: (m, [])), \
         patch("core.context.compaction_policy.build_structured_summary_prompt", return_value="x"), \
         patch.object(ts, "_ground_truth_for", return_value=""):
        fn = ts._make_structured_summariser(None, session_id="s1")
        return fn(old_msgs)


def test_fallback_keeps_user_turns_fuller_than_assistant():
    long_user = "u" * 900
    long_asst = "a" * 900
    out = _fallback_summary([
        {"role": "user", "content": long_user},
        {"role": "assistant", "content": long_asst},
    ])
    assert "<summary>" in out and "</summary>" in out
    # User kept up to 800, assistant only up to 400.
    assert out.count("u") >= 780
    assert 380 <= out.count("a") <= 430


def test_fallback_never_empty_and_references_raw():
    out = _fallback_summary([{"role": "user", "content": "hello"}])
    assert out.strip().startswith("<summary>")
    assert "raw messages remain" in out.lower()
    assert "[user] hello" in out
