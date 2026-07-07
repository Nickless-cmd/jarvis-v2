"""Value/result classes and typed exceptions for the visible model lane.

Split out of ``core.services.visible_model`` (boy-scout, 2026-07-07) so the
densely-coupled provider-adapter file shrinks below the size limit. These are
pure data containers plus two RuntimeError subclasses whose ``__init__``
surface a Central observation (self-safe, lazy import).

CRITICAL — class identity: these classes are used in ``isinstance`` checks by
never-reloaded consumers (``core.services.visible_runs`` imports them at module
level). ``core.services.visible_model`` re-exports them verbatim, and the test
harness (tests/conftest.py) reloads ONLY ``visible_model`` — not this module —
so the class objects stay identical across reloads. Do NOT move these back
inline into a reloaded module without re-checking that invariant.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VisibleModelResult:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    # Reasoning trace from thinking-mode models (Deepseek v4-pro/reasoner).
    # Must be threaded back into the assistant message on followup turns
    # — Deepseek rejects requests with "reasoning_content must be passed
    # back to the API" if we strip it. Empty for non-thinking models.
    reasoning_content: str = ""
    # 2026-05-22 (Claude): prompt-cache hit/miss split from the provider's
    # usage object. DeepSeek reports these as prompt_cache_hit_tokens and
    # prompt_cache_miss_tokens; cheap_provider_runtime plumbs them through
    # as cache_hit_tokens / cache_miss_tokens. Without these fields on
    # VisibleModelResult, the data was dropped at this layer boundary and
    # downstream cost.recorded events showed 0% cache hit for every chat
    # — even when DeepSeek was actually serving cached prefixes.
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0


@dataclass(slots=True)
class VisibleModelDelta:
    delta: str


@dataclass(slots=True)
class VisibleModelStreamDone:
    result: VisibleModelResult


@dataclass(slots=True)
class VisibleModelToolCalls:
    tool_calls: list[dict]


class VisibleModelStreamCancelled(RuntimeError):
    pass


class VisibleModelRateLimited(RuntimeError):
    """Visible-lanens provider er rate-limited (429) eller returnerede en
    midlertidig HTTP-fejl. Instrumenteret i __init__ så HVER rate-limit på tværs
    af ALLE providers (copilot + openai-compat streaming) bliver synlig i
    Centralen — også en FIRST-pass 429 (hver chat-tur, uden for followup-loopet,
    var pt. usynlig). Self-safe: observabilitet må aldrig forstyrre fejl-stien."""

    def __init__(self, *args: object, provider: str = "", model: str = "") -> None:
        super().__init__(*args)
        try:
            from core.services.central_core import central
            central().observe({
                "cluster": "stream", "nerve": "provider_rate_limited",
                "lane": "visible", "provider": str(provider or ""),
                "model": str(model or ""),
                "detail": str(args[0] if args else "")[:200],
            })
        except Exception:
            pass
