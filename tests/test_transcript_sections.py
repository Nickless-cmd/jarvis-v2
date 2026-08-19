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


def test_reasoning_replay_cappes_ved_2400():
    """Reasoning-replay er et API-krav (Deepseek 400'er uden feltet — 949712ba),
    men længden er ligegyldig for API'et. 52d6563e bumpede cappen til 8000 chars
    sammen med tekst-caps; målt 19. aug 2026 kostede det 14,6k tokens stale
    tænkning pr. tur (31% af transkriptet). Tilbage til 2400 — feltet er der,
    vægten er væk."""
    long_reasoning = "tænk " * 2000  # 10.000 chars
    history = [
        {"id": 1, "role": "user", "content": "hej", "user_id": "", "reasoning_content": ""},
        {"id": 2, "role": "assistant", "content": "svar", "user_id": "",
         "reasoning_content": long_reasoning},
    ]
    with patch.object(ts, "chat_session_messages_since_last_compact", return_value=history), \
         patch("core.services.prompt_contract._get_compact_marker_for_transcript",
               return_value=None), \
         patch("core.services.prompt_contract._maybe_auto_compact_session"):
        out = ts._build_structured_transcript_messages("s-reason", limit=60, include=True)
    replayed = [m for m in out if m.get("reasoning_content")]
    assert replayed, "assistant-turnens reasoning_content skal stadig være der (API-krav)"
    assert len(replayed[0]["reasoning_content"]) <= 2400
