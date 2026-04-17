"""LLM-based narrativizer for cognitive state lines.

Replaces the hardcoded danish template strings in
`cognitive_state_assembly.py` with LLM-generated narratives grounded
in the actual runtime data. Uses the local lane (cheap LLM) and
caches output by state-fingerprint so we never call the model more
than necessary.

Design principles:
- Real data in, real narrative out — no static fallback templates
  unless the LLM fails entirely.
- Cache by fingerprint of the *input state*, not by time. The
  narrative only changes when the underlying state changes.
- Background refresh: callers always get an immediate cached value;
  refresh happens off the request path.
- Bounded: each line is one short Danish sentence. We never let the
  LLM ramble.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable
from urllib import request as urllib_request

logger = logging.getLogger(__name__)

# Local-lane model used for narrative generation. This stays on the
# Ollama path, but points at the currently selected cloud-backed local
# target so we do not need a resident local 8B model in VRAM.
_NARRATIVIZER_MODEL = "glm-5.1:cloud"
_NARRATIVIZER_BASE_URL = "http://127.0.0.1:11434"
_NARRATIVIZER_TIMEOUT_SECONDS = 25
_NARRATIVIZER_MAX_TOKENS = 80


def _call_narrativizer_llm(system_prompt: str, user_message: str) -> str | None:
    """Call the compact LLM (heartbeat model) for narrative line generation.

    Uses call_compact_llm so the narrativizer automatically follows
    whatever heartbeat model is configured (e.g. Groq) instead of
    being hardcoded to a slow cloud-backed Ollama model.
    """
    try:
        from core.context.compact_llm import call_compact_llm

        prompt = f"{system_prompt}\n\n{user_message}"
        result = call_compact_llm(prompt, max_tokens=_NARRATIVIZER_MAX_TOKENS)
        return result.strip() or None
    except Exception as exc:
        logger.warning("cognitive_state_narrativizer ollama call failed: %s", exc)
        return None

# How long a cached narrative survives without input-state change.
# After this it is considered "stale" and will be regenerated on the
# next read regardless of fingerprint.
_CACHE_TTL_SECONDS = 30 * 60  # 30 min hard cap

# How long we wait before allowing a *new* fingerprint to fire its
# own LLM call (per-line cooldown so we don't hammer ollama).
_PER_LINE_COOLDOWN_SECONDS = 8


@dataclass(slots=True)
class _CachedNarrative:
    fingerprint: str
    narrative: str
    generated_at: float


# line_key → cached narrative
_CACHE: dict[str, _CachedNarrative] = {}
_LAST_LLM_CALL_AT: dict[str, float] = {}
_CACHE_LOCK = threading.Lock()
_REFRESH_INFLIGHT: set[str] = set()


def _fingerprint(state: dict[str, object]) -> str:
    blob = json.dumps(state, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(blob, usedforsecurity=False).hexdigest()[:16]


def _generate_in_background(
    *,
    line_key: str,
    fingerprint: str,
    system_prompt: str,
    user_message: str,
) -> None:
    """Run the LLM call in a background thread and update cache."""

    def _worker() -> None:
        try:
            text = _call_narrativizer_llm(system_prompt, user_message)
        except Exception as exc:  # pragma: no cover
            logger.warning("cognitive narrativizer LLM call failed: %s", exc)
            text = None
        with _CACHE_LOCK:
            _REFRESH_INFLIGHT.discard(line_key)
            if not text:
                return
            cleaned = " ".join(text.strip().split())
            if len(cleaned) > 240:
                cleaned = cleaned[:239].rstrip() + "…"
            _CACHE[line_key] = _CachedNarrative(
                fingerprint=fingerprint,
                narrative=cleaned,
                generated_at=time.time(),
            )

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def narrativize_line(
    *,
    line_key: str,
    state: dict[str, object],
    system_prompt: str,
    user_message_builder: Callable[[], str],
    fallback: str | None = None,
) -> str | None:
    """Return an LLM-narrativized line for this state, or fallback.

    The first time a fingerprint is seen the LLM call is dispatched
    asynchronously and the fallback (or previous cached narrative) is
    returned. Subsequent calls with the same fingerprint return the
    cached narrative immediately.

    Args:
        line_key: Stable identifier for this line type
            (e.g. "body", "affect", "self_anchor").
        state: The actual runtime state dict that this line narrativizes.
        system_prompt: Bounded system instructions for the LLM.
        user_message_builder: Lazy builder for the user message — only
            called when we actually need to fire an LLM call.
        fallback: Optional fallback string if no narrative is cached
            yet. If None, the line is omitted on first cold start.
    """
    fingerprint = _fingerprint(state)
    now = time.time()

    with _CACHE_LOCK:
        cached = _CACHE.get(line_key)
        last_call = _LAST_LLM_CALL_AT.get(line_key, 0.0)
        cache_fresh = (
            cached is not None
            and cached.fingerprint == fingerprint
            and (now - cached.generated_at) < _CACHE_TTL_SECONDS
        )
        cooling = (now - last_call) < _PER_LINE_COOLDOWN_SECONDS
        in_flight = line_key in _REFRESH_INFLIGHT
        if cache_fresh:
            return cached.narrative

        # Need refresh — but rate-limit per line and avoid duplicate
        # in-flight requests for the same line.
        if not cooling and not in_flight:
            _LAST_LLM_CALL_AT[line_key] = now
            _REFRESH_INFLIGHT.add(line_key)
            should_dispatch = True
        else:
            should_dispatch = False

    if should_dispatch:
        try:
            user_message = user_message_builder()
        except Exception as exc:
            logger.warning(
                "cognitive narrativizer user message build failed for %s: %s",
                line_key,
                exc,
            )
            with _CACHE_LOCK:
                _REFRESH_INFLIGHT.discard(line_key)
        else:
            _generate_in_background(
                line_key=line_key,
                fingerprint=fingerprint,
                system_prompt=system_prompt,
                user_message=user_message,
            )

    # Return previous cached narrative if any (even with stale
    # fingerprint) — better than nothing while the new one is
    # generating.
    if cached is not None and cached.narrative:
        return cached.narrative
    return fallback


def cache_snapshot() -> dict[str, dict[str, object]]:
    """Expose current cache state for MC observability."""
    with _CACHE_LOCK:
        return {
            key: {
                "fingerprint": item.fingerprint,
                "generated_at": item.generated_at,
                "narrative": item.narrative,
            }
            for key, item in _CACHE.items()
        }
