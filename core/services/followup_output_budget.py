"""Output-token budget for agentic follow-up rounds + the "reasoning ate the
budget" backstop.

Root cause (measured 2026-09-04, Bjørn's "cutoff" ghost): every openai-compat
follow-up round was sent with ``max_tokens=4096`` — a cap written for MiniMax/
OpenCode (which otherwise stop at ~512). On DeepSeek's paid API in thinking
mode the reasoning counts against ``max_tokens``; once a round's reasoning hit
~4096 tokens (10-12k chars) DeepSeek closed the stream with
``finish_reason="length"``, empty content and no tool call. The loop's
"continue where you stopped" needs partial TEXT, so with 0 chars it exited
``completed-truncated`` — status completed, the previous round's "henter det
sidste stykke:" on screen, then silence. Four of Bjørn's turns died this way in
one evening; 25 answers in 30 days sat exactly in the 9-13k-char band.

Two knobs, both provider-scoped so MiniMax/OpenCode keep their 4096:

* :func:`followup_max_tokens` — DeepSeek gets a budget that fits reasoning +
  answer (DeepSeek allows up to 384K output).
* :func:`reasoning_exhausted` + :func:`nonthinking_retry_body` — if a round
  still ends ``length`` with no text and no tool call, the adapter re-runs the
  round ONCE with thinking disabled instead of returning an empty round.
"""
from __future__ import annotations

from typing import Any

DEFAULT_FOLLOWUP_MAX_TOKENS = 4096
DEEPSEEK_FOLLOWUP_MAX_TOKENS = 32_768

_DEEPSEEK_THINKING_MODELS = frozenset({
    "deepseek-v4-flash", "deepseek-v4-pro", "deepseek-reasoner", "deepseek-chat",
})


def followup_max_tokens(provider: str, model: str = "") -> int:
    """Output budget for one follow-up round on ``provider``."""
    p = str(provider or "").strip().lower()
    if p == "deepseek":
        return DEEPSEEK_FOLLOWUP_MAX_TOKENS
    return DEFAULT_FOLLOWUP_MAX_TOKENS


def reasoning_exhausted(*, finish_reason: str, text: str, tool_calls: list[Any] | None) -> bool:
    """True when the provider stopped for length and nothing usable came out:
    the whole budget went to reasoning (or nothing at all)."""
    if str(finish_reason or "").strip().lower() != "length":
        return False
    if str(text or "").strip():
        return False
    return not tool_calls


def supports_nonthinking_retry(provider: str, model: str) -> bool:
    """Only DeepSeek thinking models can be re-run with thinking disabled.
    deepseek-v4-pro cannot disable thinking → no retry."""
    p = str(provider or "").strip().lower()
    m = str(model or "").strip().lower()
    return p == "deepseek" and m in _DEEPSEEK_THINKING_MODELS and m != "deepseek-v4-pro"


def nonthinking_retry_body() -> dict[str, Any]:
    """Extra request fields that disable DeepSeek thinking for the retry round."""
    return {"thinking": {"type": "disabled"}}
