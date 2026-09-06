from __future__ import annotations

from core.services import followup_output_budget as fob


def test_deepseek_gets_a_budget_that_fits_reasoning_plus_answer():
    assert fob.followup_max_tokens("deepseek", "deepseek-v4-flash") == 32_768
    assert fob.followup_max_tokens("DeepSeek ") == 32_768


def test_other_compat_providers_keep_the_minimax_cap():
    for p in ("opencode", "groq", "openrouter", "mistral", "github-copilot", "minimax"):
        assert fob.followup_max_tokens(p, "x") == 4096


def test_reasoning_exhausted_only_when_length_and_nothing_usable():
    assert fob.reasoning_exhausted(finish_reason="length", text="", tool_calls=[])
    assert fob.reasoning_exhausted(finish_reason="LENGTH", text="  ", tool_calls=None)
    assert not fob.reasoning_exhausted(finish_reason="length", text="delvis svar", tool_calls=[])
    assert not fob.reasoning_exhausted(finish_reason="length", text="", tool_calls=[{"id": "c1"}])
    assert not fob.reasoning_exhausted(finish_reason="stop", text="", tool_calls=[])
    assert not fob.reasoning_exhausted(finish_reason="", text="", tool_calls=[])


def test_nonthinking_retry_is_deepseek_flash_only():
    assert fob.supports_nonthinking_retry("deepseek", "deepseek-v4-flash")
    assert fob.supports_nonthinking_retry("deepseek", "deepseek-reasoner")
    assert not fob.supports_nonthinking_retry("deepseek", "deepseek-v4-pro")
    assert not fob.supports_nonthinking_retry("opencode", "deepseek-v4-flash")
    assert not fob.supports_nonthinking_retry("deepseek", "")
    assert fob.nonthinking_retry_body() == {"thinking": {"type": "disabled"}}
