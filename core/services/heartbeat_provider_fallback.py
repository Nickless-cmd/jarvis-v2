"""Heartbeat provider fallback — cheap cloud lane when primary (Groq) fails.

Keeps heartbeat_runtime.py from growing further. Extracted per Boy Scout rule
(heartbeat_runtime.py is 7221+ lines).

Supports:
- execute_openai_compat_heartbeat_prompt: OpenAI-chat/completions compatible
  providers — sambanova, mistral, nvidia-nim, openrouter (as backup direct call)
- try_heartbeat_cheap_fallback: iterates cheap lane (skip groq + ollamafreeapi)
  when the configured heartbeat provider is rate-limited or unavailable
"""
from __future__ import annotations

import itertools
import json
import logging
from urllib import error as urllib_error
from urllib import request as urllib_request

logger = logging.getLogger(__name__)

_CHEAP_FALLBACK_TIMEOUT = 45
_SKIP_FOR_HEARTBEAT: frozenset[str] = frozenset({"groq", "ollamafreeapi"})

# Round-robin so a single provider isn't hammered by every internal job while
# the primary lane is dry (2026-06-22). Each fallback call starts from a
# different ready candidate, spreading load across the ~10 providers.
_fallback_rotation = itertools.count()

# Providers supported via OpenAI-chat/completions API. Expanded 2026-06-22 to
# include the other free/cheap openai-compatible lanes (opencode, gemini,
# cloudflare) so the fallback rotation has real breadth to spread across — not
# just mistral — while the primary (deepseek) is dry. A provider that turns out
# not to be compatible simply fails its attempt and the loop tries the next.
_OPENAI_COMPAT_PROVIDERS = frozenset(
    {
        "sambanova", "mistral", "nvidia-nim", "openrouter", "openai", "deepseek",
        "opencode", "gemini", "cloudflare",
    }
)

# Known base URLs for providers that don't require runtime config
_PROVIDER_BASE_URLS: dict[str, str] = {
    "sambanova": "https://api.sambanova.ai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "nvidia-nim": "https://integrate.api.nvidia.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "opencode": "https://opencode.ai/zen/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


def execute_openai_compat_heartbeat_prompt(
    *, prompt: str, target: dict[str, str | bool]
) -> dict[str, object]:
    """Call an OpenAI-chat/completions-compatible provider for heartbeat.

    Used for sambanova, mistral, nvidia-nim as configured heartbeat providers.
    Raises RuntimeError on failure (caller handles fallback).
    """
    from core.services.heartbeat_runtime import _load_provider_api_key

    provider = str(target.get("provider") or "").strip()
    model = str(target.get("model") or "").strip()
    auth_profile = str(target.get("auth_profile") or "").strip()
    base_url = (
        str(target.get("base_url") or "").strip()
        or _PROVIDER_BASE_URLS.get(provider, "")
    )
    if not base_url:
        raise RuntimeError(f"No base_url for provider: {provider}")

    api_key = _load_provider_api_key(provider=provider, profile=auth_profile)
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 1536,  # var 512 → trunkerede beslutnings-JSON (29. jun)
        }
    ).encode("utf-8")
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=_CHEAP_FALLBACK_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:200]
        raise RuntimeError(f"http-error:{exc.code}:{detail}") from exc
    except Exception as exc:
        raise RuntimeError(str(exc) or type(exc).__name__) from exc

    message = ((data.get("choices") or [{}])[0]).get("message") or {}
    text = str(message.get("content") or message.get("reasoning_content") or "").strip()
    if not text:
        raise RuntimeError(f"{provider} heartbeat execution returned no response")

    from core.services.heartbeat_runtime import _estimate_tokens
    usage = data.get("usage") or {}
    return {
        "text": text,
        "input_tokens": int(usage.get("prompt_tokens") or _estimate_tokens(prompt)),
        "output_tokens": int(usage.get("completion_tokens") or _estimate_tokens(text)),
        "cost_usd": 0.0,
        "execution_status": "success",
    }


def try_heartbeat_cheap_fallback(prompt: str) -> dict[str, object] | None:
    """Try cheap lane providers (skip groq + ollamafreeapi) as heartbeat fallback.

    Returns result dict on success, None if all candidates fail.
    Called when the configured heartbeat provider (Groq) is rate-limited.
    """
    try:
        from core.services.cheap_provider_runtime import (
            _configured_cheap_candidates,
            _candidate_quota_snapshot,
            _candidate_adaptive_snapshot,
        )
        candidates = _configured_cheap_candidates(
            include_public_proxy=False, skip_providers=_SKIP_FOR_HEARTBEAT
        )
    except Exception as exc:
        logger.warning("heartbeat_fallback: could not load cheap candidates: %s", exc)
        return None

    # Build the list of USABLE candidates first (ready, not quota-blocked,
    # openai-compat), then rotate among those. Rotating the full list didn't
    # spread: the blocked deepseek/nvidia prefix meant every call still fell on
    # the first usable one. Rotating the filtered list spreads load for real.
    usable: list[dict] = []
    for candidate in candidates:
        if not bool(candidate.get("credentials_ready")):
            continue
        try:
            if _candidate_quota_snapshot(candidate).get("blocked"):
                continue
        except Exception:
            pass
        provider = str(candidate.get("provider") or "").strip()
        model = str(candidate.get("model") or "").strip()
        if provider not in _OPENAI_COMPAT_PROVIDERS or not model:
            continue
        usable.append(candidate)

    if usable:
        _off = next(_fallback_rotation) % len(usable)
        usable = usable[_off:] + usable[:_off]

    for candidate in usable:
        provider = str(candidate.get("provider") or "").strip()
        model = str(candidate.get("model") or "").strip()

        target: dict[str, str | bool] = {
            "provider": provider,
            "model": model,
            "auth_profile": str(candidate.get("auth_profile") or "").strip(),
            "base_url": str(candidate.get("base_url") or "").strip(),
        }
        try:
            result = execute_openai_compat_heartbeat_prompt(prompt=prompt, target=target)
            logger.info(
                "heartbeat_fallback: succeeded via %s/%s", provider, model
            )
            return result
        except Exception as exc:
            logger.warning(
                "heartbeat_fallback: %s/%s failed (%s), trying next",
                provider, model, exc,
            )
            # B10: provider-fejl synlig i Centralen (var stille logger.warning).
            try:
                from core.services.central_core import central
                central().observe({"cluster": "stream", "nerve": "provider_call",
                                   "provider": provider, "model": model,
                                   "outcome": "failed", "error": type(exc).__name__})
            except Exception:
                pass

    # Alle usable providers fejlede → udtømning er et oppetids-signal (var helt stille).
    try:
        from core.services.central_core import central
        central().observe({"cluster": "stream", "nerve": "provider_fallback",
                           "outcome": "exhausted", "tried": len(usable)})
    except Exception:
        pass
    return None
