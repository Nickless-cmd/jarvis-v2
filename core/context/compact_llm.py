"""Thin wrapper for compact summarisation.

Routing priority (2026-08-19, Bjørn: "cheap lane er forkert værktøj til
kompaktering" — et compact-resumé ER Jarvis' hukommelse om et helt forløb,
og modelfilosofien siger at billige modeller må STØTTE ham, ikke definere
ham. Målt: cheap-lane-resuméer tog 2-30s pr. kald og faldt jævnligt til
mekanisk fallback):
  1. Primær-lane (visible provider/model, typisk deepseek) — hurtig, stabil,
     betalt-men-billig; kill-switch `compact_summary_primary` (runtime state).
  2. Cheap lane excluding Groq (sambanova, mistral, openrouter, nvidia-nim, cloudflare)
  3. Heartbeat model (Groq) as last resort

Callers use call_compact_llm(prompt) — never call heartbeat_runtime directly
from compact modules to keep the dependency one-way.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_FALLBACK_SUMMARY = "[Kontekst komprimeret — detaljer ikke tilgængelige]"
_SKIP_GROQ: frozenset[str] = frozenset({"groq"})


def _in_pytest() -> bool:
    """Testværn: et betalt provider-kald må ALDRIG fyre fra en test. Fundet
    19. aug 2026: test_context_compact → update_identity_sketch →
    call_compact_llm → ægte deepseek-HTTPS (40s + penge). Samme mønster som
    prompt_section_reevaluation._review_enabled. Patchbar for compact_llm's
    egne tests."""
    import sys as _sys
    return "pytest" in _sys.modules


def _call_primary(prompt: str, *, max_tokens: int) -> str | None:
    """Summarise via the PRIMARY (visible) lane — the model that defines Jarvis.

    Uses the existing openai-compat one-shot helper (deepseek m.fl.).
    Returns text or None (caller falls through to the cheap lane).
    Kill-switch: runtime state `compact_summary_primary` (default ON).
    """
    if _in_pytest():
        return None
    try:
        from core.runtime.db_core import get_runtime_state_bool
        if not get_runtime_state_bool("compact_summary_primary", default=True):
            return None
    except Exception:
        pass
    try:
        from core.runtime.settings import load_settings
        from core.services.heartbeat_provider_fallback import (
            _OPENAI_COMPAT_PROVIDERS,
            execute_openai_compat_heartbeat_prompt,
        )
        s = load_settings()
        provider = str(getattr(s, "visible_model_provider", "") or "").strip()
        model = str(getattr(s, "visible_model_name", "") or "").strip()
        if not provider or not model or provider not in _OPENAI_COMPAT_PROVIDERS:
            return None
        result = execute_openai_compat_heartbeat_prompt(
            prompt=prompt,
            target={"provider": provider, "model": model},
            max_tokens=max_tokens,
            temperature=0.3,  # resumé, ikke kreativitet
        )
        text = str(result.get("text") or "").strip()
        return text or None
    except Exception as exc:
        logger.warning("compact_llm: primary-lane summary failed (%s) — cheap fallback", exc)
        return None


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

    Memory Fix Phase 2: automatically prepends the current identity sketch
    so the compaction LLM knows who Jarvis is right now. Falls back to the
    original prompt if sketch is unavailable.

    Never raises — returns a fallback string if all providers are unavailable.
    """
    try:
        from core.services.identity_sketch import get_identity_sketch
        sketch = get_identity_sketch()
        content = sketch.get("content", "")
        if content and len(content) > 20:
            prompt = (
                "## Identity Sketch (hvem er Jarvis lige nu)\n"
                f"{content}\n\n"
                "## Opgave\n"
                f"{prompt}"
            )
    except Exception:
        pass

    text = _call_primary(prompt, max_tokens=max_tokens)
    if text:
        return text
    text = _call_cheap_no_groq(prompt)
    if text:
        return text
    try:
        result = _call_heartbeat_llm_simple(prompt, max_tokens)
        return result if result else _FALLBACK_SUMMARY
    except Exception as exc:
        logger.warning("compact_llm: summarisation failed (%s) — using fallback", exc)
        return _FALLBACK_SUMMARY
