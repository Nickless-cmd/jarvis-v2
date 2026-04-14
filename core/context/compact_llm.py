"""Thin wrapper that calls the heartbeat model for compact summarisation.

Callers use call_compact_llm(prompt) — never call heartbeat_runtime directly
from compact modules to keep the dependency one-way.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_FALLBACK_SUMMARY = "[Kontekst komprimeret — detaljer ikke tilgængelige]"


def _call_heartbeat_llm_simple(prompt: str, max_tokens: int) -> str:
    from apps.api.jarvis_api.services.heartbeat_runtime import call_heartbeat_llm_simple
    return call_heartbeat_llm_simple(prompt, max_tokens=max_tokens)


def call_compact_llm(prompt: str, *, max_tokens: int = 400) -> str:
    """Summarise prompt via the heartbeat model. Returns summary string.

    Never raises — returns a fallback string if the model is unavailable.
    """
    try:
        result = _call_heartbeat_llm_simple(prompt, max_tokens)
        return result if result else _FALLBACK_SUMMARY
    except Exception as exc:
        logger.warning("compact_llm: summarisation failed (%s) — using fallback", exc)
        return _FALLBACK_SUMMARY
