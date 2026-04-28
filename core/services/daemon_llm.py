"""Shared LLM call for daemons — cheap lane first, heartbeat model fallback.

Includes prompt-hash response cache (Layer A) that skips LLM calls when
the same prompt is seen within the daemon's TTL window.
"""
from __future__ import annotations

import hashlib
import time

# ---------------------------------------------------------------------------
# Response cache — Layer A
# ---------------------------------------------------------------------------

_response_cache: dict[str, tuple[str, float]] = {}
# key: SHA256(prompt), value: (response_text, expires_at_timestamp)

_DAEMON_TTL: dict[str, int] = {
    # Fast (2-3 min cadence)
    "somatic": 90,
    "thought_stream": 90,
    # Medium (5-10 min cadence)
    "curiosity": 180,
    "conflict": 180,
    "reflection_cycle": 180,
    "user_model": 180,
    # Slow (30min+ cadence)
    "meta_reflection": 600,
    "irony": 600,
    "aesthetic_taste": 600,
    "development_narrative": 600,
    "existential_wonder": 600,
    "code_aesthetic": 600,
    # No cache
    "session_summary": 0,
}
_DEFAULT_TTL = 120


def _get_cache_ttl(daemon_name: str) -> int:
    """Return TTL in seconds for a daemon. 0 means no caching."""
    return _DAEMON_TTL.get(daemon_name, _DEFAULT_TTL)


def _check_cache(cache_key: str) -> str | None:
    """Return cached response if present and not expired, else None."""
    entry = _response_cache.get(cache_key)
    if entry is None:
        return None
    text, expires_at = entry
    if time.time() > expires_at:
        del _response_cache[cache_key]
        return None
    return text


def _store_cache(cache_key: str, text: str, daemon_name: str) -> None:
    """Store response in cache with daemon-specific TTL."""
    ttl = _get_cache_ttl(daemon_name)
    if ttl <= 0:
        return
    _response_cache[cache_key] = (text, time.time() + ttl)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def daemon_llm_call(
    prompt: str,
    *,
    max_len: int = 200,
    fallback: str = "",
    daemon_name: str = "",
) -> str:
    """Call LLM for daemon output. Tries cache first, then cheap lane (Groq),
    then heartbeat model. Returns stripped text or fallback on failure. Never raises.
    Logs raw output to daemon_output_log when daemon_name is provided.
    """
    return _daemon_llm_call_impl(
        prompt,
        max_len=max_len,
        fallback=fallback,
        daemon_name=daemon_name,
        public_safe=False,
    )


def daemon_public_safe_llm_call(
    prompt: str,
    *,
    max_len: int = 200,
    fallback: str = "",
    daemon_name: str = "",
) -> str:
    """Call path reserved for PUBLIC-SAFE prompts.

    Prefers the OllamaFreeAPI-backed public-safe provider pool and falls back to
    local Ollama. This must only be used for stateless prompts without private
    user or self-context.
    """
    return _daemon_llm_call_impl(
        prompt,
        max_len=max_len,
        fallback=fallback,
        daemon_name=daemon_name,
        public_safe=True,
    )


def _daemon_llm_call_impl(
    prompt: str,
    *,
    max_len: int,
    fallback: str,
    daemon_name: str,
    public_safe: bool,
) -> str:
    # --- Layer A: check response cache ---
    cache_key = ""
    if daemon_name and _get_cache_ttl(daemon_name) > 0:
        cache_key = hashlib.sha256(prompt.encode()).hexdigest()
        cached = _check_cache(cache_key)
        if cached is not None:
            # Log cache hit for observability
            if daemon_name:
                try:
                    from core.runtime.db import daemon_output_log_insert

                    daemon_output_log_insert(
                        daemon_name=daemon_name,
                        raw_llm_output=cached[:2000],
                        parsed_result=cached[:500],
                        success=True,
                        provider="cache",
                    )
                except Exception:
                    pass
            return cached

    text = ""
    provider = ""

    # 1. Try primary execution path
    try:
        if public_safe:
            from core.services.cheap_provider_runtime import (
                execute_public_safe_cheap_lane,
            )

            result = execute_public_safe_cheap_lane(message=prompt)
        else:
            from core.services.non_visible_lane_execution import (
                execute_cheap_lane,
            )

            # Daemons are inner-layer noise — relevance scoring, mood
            # introspection, dream distillation, etc. They run on every
            # heartbeat tick. Send them through the public-proxy tier so
            # they don't drain Groq/NVIDIA/Gemini quotas that the visible
            # lane and council deliberation actually need.
            result = execute_cheap_lane(message=prompt, task_kind="background")
        text = str(result.get("text") or "").strip()
        provider = str(
            result.get("provider") or ("public-safe" if public_safe else "cheap")
        )
    except Exception:
        pass

    # 2. Fallback to heartbeat model (Ollama / configured provider)
    if not text:
        try:
            from core.services.heartbeat_runtime import (
                _execute_heartbeat_model,
                _select_heartbeat_target,
                load_heartbeat_policy,
            )

            policy = load_heartbeat_policy()
            target = _select_heartbeat_target()
            result = _execute_heartbeat_model(
                prompt=prompt,
                target=target,
                policy=policy,
                open_loops=[],
                liveness=None,
            )
            text = str(result.get("text") or "").strip()
            provider = str(target.get("provider") or "heartbeat")
        except Exception:
            pass

    # 3. Clean up quotes
    raw_text = text
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    final = text[:max_len] if text else fallback

    # --- Layer A: store in cache (only successful responses) ---
    if cache_key and text:
        _store_cache(cache_key, final, daemon_name)

    # 4. Log output for debugging
    if daemon_name:
        try:
            from core.runtime.db import daemon_output_log_insert

            daemon_output_log_insert(
                daemon_name=daemon_name,
                raw_llm_output=raw_text[:2000],
                parsed_result=final[:500],
                success=bool(text),
                provider=provider,
            )
        except Exception:
            pass

    return final
