"""Inner-LLM enrichment must not use the deprecated deepseek-chat/-reasoner
aliases (they die 2026-07-24). Instead it keeps deepseek-v4-flash and disables
thinking-mode via the request param {"thinking": {"type": "disabled"}}.
"""
from core.memory.inner_llm_enrichment import _build_inner_llm_body


def test_deepseek_v4flash_kept_and_thinking_disabled():
    body = _build_inner_llm_body(
        provider="deepseek",
        model="deepseek-v4-flash",
        system_prompt="sys",
        user_message="hi",
    )
    assert body["model"] == "deepseek-v4-flash"
    assert body["thinking"] == {"type": "disabled"}


def test_deprecated_aliases_remapped_to_v4flash_with_thinking_disabled():
    for alias in ("deepseek-chat", "deepseek-reasoner"):
        body = _build_inner_llm_body(
            provider="deepseek",
            model=alias,
            system_prompt="sys",
            user_message="hi",
        )
        assert body["model"] == "deepseek-v4-flash"
        assert body["model"] not in ("deepseek-chat", "deepseek-reasoner")
        assert body["thinking"] == {"type": "disabled"}


def test_non_deepseek_provider_unchanged_no_thinking_key():
    body = _build_inner_llm_body(
        provider="groq",
        model="llama-3.3-70b",
        system_prompt="sys",
        user_message="hi",
    )
    assert body["model"] == "llama-3.3-70b"
    assert "thinking" not in body
    # existing keys preserved
    assert body["max_tokens"] == 300
    assert body["temperature"] == 0.7
    assert body["stream"] is False
    assert body["messages"][0]["role"] == "system"
