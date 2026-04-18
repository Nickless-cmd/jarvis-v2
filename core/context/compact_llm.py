"""Thin wrapper for compact summarisation.

Routing priority (to preserve Groq quota):
  1. Cheap lane excluding Groq (sambanova, mistral, openrouter, nvidia-nim, cloudflare)
  2. Heartbeat model (Groq) as last resort

Callers use call_compact_llm(prompt) — never call heartbeat_runtime directly
from compact modules to keep the dependency one-way.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_FALLBACK_SUMMARY = "[Kontekst komprimeret — detaljer ikke tilgængelige]"
_SKIP_GROQ: frozenset[str] = frozenset({"groq"})


def _call_cheap_no_groq(prompt: str) -> str | None:
    """Try cheap lane providers, skipping Groq. Returns text or None."""
    try:
        from core.services.cheap_provider_runtime import execute_cheap_lane_via_pool
        result = execute_cheap_lane_via_pool(message=prompt, skip_providers=_SKIP_GROQ)
        text = str(result.get("text") or "").strip()
        return text or None
    except Exception:
        return None


def _call_heartbeat_llm_simple(prompt: str, max_tokens: int) -> str:
    from core.services.heartbeat_runtime import call_heartbeat_llm_simple
    return call_heartbeat_llm_simple(prompt, max_tokens=max_tokens)


def call_compact_llm(prompt: str, *, max_tokens: int = 400) -> str:
    """Summarise prompt. Tries non-Groq cheap providers first, Groq as fallback.

    Never raises — returns a fallback string if all providers are unavailable.
    """
    text = _call_cheap_no_groq(prompt)
    if text:
        return text
    try:
        result = _call_heartbeat_llm_simple(prompt, max_tokens)
        return result if result else _FALLBACK_SUMMARY
    except Exception as exc:
        logger.warning("compact_llm: summarisation failed (%s) — using fallback", exc)
        return _FALLBACK_SUMMARY
