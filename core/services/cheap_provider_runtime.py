from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
import httpx

from core.auth.profiles import get_provider_credentials, provider_has_real_credentials
from core.costing.ledger import record_cost
from core.eventbus.bus import event_bus
from core.runtime.db import (
    count_cheap_provider_invocations,
    get_cheap_provider_runtime_state,
    list_cheap_provider_runtime_states,
    record_cheap_provider_invocation,
    upsert_cheap_provider_runtime_state,
)
from core.runtime.provider_router import load_provider_router_registry, resolve_provider_router_target

_DEFAULT_TIMEOUT_SECONDS = 30
_QUOTA_RESET_HOURS = 24

# Hot-path TTL caches (2026-05-13). Profile under load showed
# _candidate_adaptive_snapshot + _candidate_quota_snapshot dominating
# CPU due to 30-45 DB queries per surface build, called repeatedly
# by MC polling + awareness builders. These caches keep semantics
# (still re-reads recent state) but eliminate the per-request stampede.
#
# 2026-05-15: migrated from per-process dicts to shared_cache (SQLite-
# backed, cross-worker). Was hit rate ~25% with 4 uvicorn workers —
# each worker had its own dict. Now all 4 workers see the same cache,
# pushing hit rate toward 95%+ for the request-stampede pattern.
_STATUS_SURFACE_TTL_SECONDS = 5.0
_QUOTA_SNAPSHOT_TTL_SECONDS = 2.0
_STATUS_SURFACE_CACHE_KEY = "cheap_lane:status_surface"
_QUOTA_SNAPSHOT_PREFIX = "cheap_lane:quota:"
_OPENAI_COMPATIBLE_PROVIDERS = {
    "groq",
    "nvidia-nim",
    "openrouter",
    "mistral",
    "sambanova",
    "opencode",
    "deepseek",
}

# Codex uses a distinct responses-based protocol via chatgpt.com/backend-api.
# NOT OpenAI-compatible — separate dispatch path.
_OPENAI_CODEX_PROVIDER = "openai-codex"

CHEAP_PROVIDER_DEFAULTS: dict[str, dict[str, object]] = {
    # Phase A re-prioritization (2026-04-26): groq was hogging the chain
    # with priority=10 even though it's frequently rate-limited and in
    # cooldown. Spread load across nvidia-nim / openrouter / sambanova /
    # mistral first; let groq be a backup. Re-prioritize on observed
    # capacity, not historical assumption.
    "nvidia-nim": {
        "label": "NVIDIA NIM",
        "priority": 10,
        "base_url": "https://integrate.api.nvidia.com/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 40,
        "daily_limit": 500,
    },
    "openrouter": {
        "label": "OpenRouter",
        "priority": 20,
        "base_url": "https://openrouter.ai/api/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 20,
        "daily_limit": 100,
    },
    "sambanova": {
        "label": "SambaNova",
        "priority": 30,
        "base_url": "https://api.sambanova.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 100,
    },
    "mistral": {
        "label": "Mistral",
        "priority": 40,
        "base_url": "https://api.mistral.ai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 10,
        "daily_limit": 200,
    },
    "gemini": {
        "label": "Gemini",
        "priority": 50,
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "auth_kind": "api-key-query",
        "protocol": "gemini-native",
        "models_endpoint": "/models",
        "rpm_limit": 15,
        "daily_limit": 1000,
    },
    "groq": {
        "label": "Groq",
        "priority": 60,
        "base_url": "https://api.groq.com/openai/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": 30,
        "daily_limit": 10000,
    },
    "cloudflare": {
        "label": "Cloudflare Workers AI",
        "priority": 70,
        "base_url": "https://api.cloudflare.com/client/v4",
        "auth_kind": "bearer+account-id",
        "protocol": "cloudflare-ai",
        "models_endpoint": "/accounts/{account_id}/ai/models/search",
        "rpm_limit": None,
        "daily_limit": None,
        "daily_neurons": 10000,
    },
    "ollamafreeapi": {
        "label": "OllamaFreeAPI",
        "priority": 95,
        "base_url": "",
        "auth_kind": "none",
        "protocol": "ollamafreeapi",
        "models_endpoint": "",
        "rpm_limit": None,
        "daily_limit": None,
    },
    "arko": {
        # Third-party agent platform (https://arko.arcaelas.com). Used as a
        # cheap-lane fallback alongside ollamafreeapi. Auth via API key
        # stored in runtime.json (arko_api_key + arko_cheap_agent_id) — not
        # via the auth_profile system. Priority 90 sits between OpenCode (80)
        # and OllamaFreeAPI (95): tried before OFA when Groq is rate-limited
        # but after the providers we trust most.
        "label": "Arko Studio",
        "priority": 90,
        "base_url": "https://arko.arcaelas.com",
        "auth_kind": "runtime-key",
        "protocol": "arko",
        "models_endpoint": "",
        "rpm_limit": None,
        "daily_limit": None,
        "static_models": ["jarvis-cheap-lane"],
    },
    "deepseek": {
        # Paid provider — Bjørn's $100 wallet, V4 Pro promo until 2026-05-31.
        # Auto prefix-caching on the server side (no params needed); cached
        # input tokens billed at lower rate. Keep system prompt prefix stable
        # for cache hits to actually land. Visible-lane only for now.
        "label": "DeepSeek",
        "priority": 5,
        "base_url": "https://api.deepseek.com/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        "models_endpoint": "/models",
        "rpm_limit": None,
        "daily_limit": None,
        # deepseek-chat = compat-alias for v4-flash non-thinking mode.
        # Listet først så det er default-pick i classification-paths
        # (relevance, memory_selection) — ingen reasoning overhead.
        "static_models": ["deepseek-chat", "deepseek-v4-flash", "deepseek-v4-pro"],
    },
    "opencode": {
        "label": "OpenCode Zen",
        "priority": 80,
        "base_url": "https://opencode.ai/zen/v1",
        "auth_kind": "bearer",
        "protocol": "openai-chat",
        # No dynamic /models endpoint — models listed in static_models below.
        "models_endpoint": "",
        "rpm_limit": None,
        "daily_limit": None,
        "static_models": [
            "big-pickle",
            "minimax-m2.5-free",
            "nemotron-3-super-free",
        ],
    },
    "openai-codex": {
        "label": "OpenAI Codex (ChatGPT Plus OAuth)",
        "priority": 15,
        "base_url": "https://chatgpt.com/backend-api",
        "auth_kind": "oauth",
        "protocol": "openai-codex-responses",
        "models_endpoint": "",
        "rpm_limit": None,
        "daily_limit": None,
        "static_models": [
            "gpt-5.3-codex",
            "gpt-5.4",
        ],
    },
}


class CheapProviderError(RuntimeError):
    def __init__(
        self,
        *,
        provider: str,
        code: str,
        message: str,
        retry_after_seconds: int = 0,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.message = message
        self.retry_after_seconds = int(max(0, retry_after_seconds))
        self.status_code = status_code


def supported_cheap_providers() -> list[dict[str, object]]:
    return [
        {"provider": provider, **metadata}
        for provider, metadata in sorted(
            CHEAP_PROVIDER_DEFAULTS.items(),
            key=lambda item: int(item[1].get("priority") or 9999),
        )
    ]


def provider_runtime_defaults(provider: str) -> dict[str, object]:
    return dict(CHEAP_PROVIDER_DEFAULTS.get(str(provider or "").strip(), {}))


def provider_auth_ready(*, provider: str, auth_profile: str) -> bool:
    normalized_provider = str(provider or "").strip()
    profile = str(auth_profile or "").strip()
    if normalized_provider not in CHEAP_PROVIDER_DEFAULTS:
        return False
    if normalized_provider == "ollamafreeapi":
        return True
    if normalized_provider == "arko":
        # Arko's credentials live in runtime.json, not in auth profiles.
        from core.runtime.arko_provider import is_configured as arko_is_configured
        return arko_is_configured()
    if normalized_provider == _OPENAI_CODEX_PROVIDER:
        # Codex uses OAuth tokens imported from ~/.codex/auth.json.
        # Check that the auth profile exists and has usable credentials.
        from core.auth.openai_oauth import get_openai_bearer_token
        try:
            token = get_openai_bearer_token(profile=profile, auto_reimport=False)
            return bool(token)
        except Exception:
            return False
    if not profile:
        return False
    credentials = get_provider_credentials(profile=profile, provider=normalized_provider)
    if not credentials:
        return False
    if normalized_provider == "cloudflare":
        return bool(
            str(credentials.get("api_key") or "").strip()
            and str(credentials.get("account_id") or "").strip()
        )
    return provider_has_real_credentials(profile=profile, provider=normalized_provider)


def list_provider_models(
    *,
    provider: str,
    auth_profile: str = "",
    base_url: str = "",
) -> dict[str, object]:
    normalized_provider = str(provider or "").strip()
    defaults = provider_runtime_defaults(normalized_provider)
    profile = str(auth_profile or "").strip()
    root = str(base_url or defaults.get("base_url") or "").strip()
    if not normalized_provider:
        return _listing_surface(
            provider="",
            auth_profile=profile,
            status="missing-provider",
            source="missing-provider",
            models=[],
        )
    if normalized_provider not in CHEAP_PROVIDER_DEFAULTS:
        return _listing_surface(
            provider=normalized_provider,
            auth_profile=profile,
            status="unsupported-provider",
            source="unsupported-provider",
            models=[],
        )
    if not provider_auth_ready(provider=normalized_provider, auth_profile=profile):
        return _listing_surface(
            provider=normalized_provider,
            auth_profile=profile,
            status="auth-not-ready",
            source="provider-live",
            models=[],
            base_url=root,
        )
    try:
        if normalized_provider in _OPENAI_COMPATIBLE_PROVIDERS:
            models = _list_openai_compatible_models(
                provider=normalized_provider,
                auth_profile=profile,
                base_url=root,
            )
        elif normalized_provider == "ollamafreeapi":
            models = _list_ollamafreeapi_models()
        elif normalized_provider == "gemini":
            models = _list_gemini_models(auth_profile=profile, base_url=root)
        elif normalized_provider == "cloudflare":
            models = _list_cloudflare_models(auth_profile=profile, base_url=root)
        elif normalized_provider == _OPENAI_CODEX_PROVIDER:
            models = _list_openai_codex_models()
        else:
            models = []
    except CheapProviderError as exc:
        return _listing_surface(
            provider=normalized_provider,
            auth_profile=profile,
            status=exc.code,
            source="provider-live",
            models=[],
            base_url=root,
        )
    return _listing_surface(
        provider=normalized_provider,
        auth_profile=profile,
        status="ready" if models else "unavailable",
        source="provider-live",
        models=models,
        base_url=root,
    )


def cheap_lane_status_surface() -> dict[str, object]:
    # TTL cache (5s) via shared_cache: MC polls this + awareness builders
    # include it. Cross-worker visibility means 4 workers share the same
    # cached surface — was hit rate ~25% with per-process dict, now ~95%.
    from core.services import shared_cache as _sc
    _cached = _sc.get(_STATUS_SURFACE_CACHE_KEY)
    if isinstance(_cached, dict):
        return _cached
    candidates = _configured_cheap_candidates(include_public_proxy=True)
    states = {
        (str(item["provider"]), str(item["model"])): item
        for item in list_cheap_provider_runtime_states(lane="cheap")
    }
    selected = select_cheap_lane_target()
    items: list[dict[str, object]] = []
    for candidate in candidates:
        provider = str(candidate["provider"])
        model = str(candidate["model"])
        state = states.get((provider, model), {})
        quota = _candidate_quota_snapshot(candidate)
        adaptive = _candidate_adaptive_snapshot(candidate, state=state)
        items.append(
            {
                "provider": provider,
                "model": model,
                "auth_profile": str(candidate.get("auth_profile") or ""),
                "priority": int(candidate.get("priority") or 9999),
                "effective_priority": adaptive["effective_priority"],
                "adaptive_penalty": adaptive["adaptive_penalty"],
                "status": str(state.get("status") or quota["status"]),
                "auth_ready": bool(candidate.get("credentials_ready")),
                "quota": quota,
                "cooldown_until": state.get("cooldown_until"),
                "last_error_code": str(state.get("last_error_code") or ""),
                "adaptive": adaptive,
                "selected": (
                    provider == str(selected.get("provider") or "")
                    and model == str(selected.get("model") or "")
                ),
            }
        )
    surface = {
        "active": bool(items),
        "selected_target": selected,
        "provider_count": len(items),
        "providers": items,
    }
    _sc.set(_STATUS_SURFACE_CACHE_KEY, surface, ttl_seconds=_STATUS_SURFACE_TTL_SECONDS)
    return surface


def invalidate_cheap_lane_status_cache() -> None:
    """Force-clear the status-surface and quota caches.

    Call after recording a success/failure if you need MC to reflect
    the change immediately (rare — TTL handles it in <=5s normally).
    Cross-worker invalidation: clears the shared_cache entries so all
    workers see the cleared state on next read.
    """
    from core.services import shared_cache as _sc
    _sc.delete(_STATUS_SURFACE_CACHE_KEY)
    _sc.invalidate_prefix(_QUOTA_SNAPSHOT_PREFIX)


def test_provider_target(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str = "",
    message: str = "Return exactly: cheap-lane-ok",
) -> dict[str, object]:
    started_at = datetime.now(UTC)
    result = _execute_provider_chat(
        provider=provider,
        model=model,
        auth_profile=auth_profile,
        base_url=base_url,
        message=message,
    )
    latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
    return {
        "provider": provider,
        "model": model,
        "auth_profile": auth_profile,
        "latency_ms": latency_ms,
        "text": str(result.get("text") or ""),
        "output_tokens": int(result.get("output_tokens") or 0),
        "cost_usd": float(result.get("cost_usd") or 0.0),
    }


def smoke_cheap_lane(
    *,
    message: str = "Return exactly: cheap-lane-ok",
) -> dict[str, object]:
    candidates = _configured_cheap_candidates(include_public_proxy=False)
    results: list[dict[str, object]] = []
    success_count = 0
    failure_count = 0
    for candidate in candidates:
        provider = str(candidate.get("provider") or "")
        model = str(candidate.get("model") or "")
        auth_profile = str(candidate.get("auth_profile") or "")
        if not bool(candidate.get("credentials_ready")):
            results.append(
                {
                    "provider": provider,
                    "model": model,
                    "auth_profile": auth_profile,
                    "status": "auth-not-ready",
                    "ok": False,
                }
            )
            failure_count += 1
            continue
        started_at = datetime.now(UTC)
        input_tokens = _estimate_tokens(message)
        try:
            probe = test_provider_target(
                provider=provider,
                model=model,
                auth_profile=auth_profile,
                base_url=str(candidate.get("base_url") or ""),
                message=message,
            )
        except CheapProviderError as exc:
            latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
            _register_provider_failure(
                provider=provider,
                model=model,
                auth_profile=auth_profile,
                error=exc,
                smoke_test=True,
            )
            results.append(
                {
                    "provider": provider,
                    "model": model,
                    "auth_profile": auth_profile,
                    "status": exc.code,
                    "ok": False,
                    "latency_ms": latency_ms,
                    "status_code": exc.status_code,
                    "retry_after_seconds": exc.retry_after_seconds,
                    "message": exc.message,
                }
            )
            failure_count += 1
            continue

        output_tokens = int(probe.get("output_tokens") or 0)
        latency_ms = int(probe.get("latency_ms") or 0)
        quality_score = _smoke_quality_score(
            expected="cheap-lane-ok",
            actual=str(probe.get("text") or ""),
        )
        record_cheap_provider_invocation(
            provider=provider,
            model=model,
            status="smoke-ok",
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=float(probe.get("cost_usd") or 0.0),
        )
        _record_provider_success(
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            quality_score=quality_score,
            smoke_test=True,
        )
        results.append(
            {
                "status": "ready",
                "ok": True,
                "quality_score": quality_score,
                **probe,
            }
        )
        success_count += 1

    return {
        "ok": failure_count == 0,
        "lane": "cheap",
        "provider_count": len(results),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results,
    }


# ── Task-kind tiering for cheap-lane routing ─────────────────────────────
# The cheap lane has many consumers — relevance scoring, memory selection,
# inner voice, dreams, daemon_llm calls, graph extraction, etc. Without
# tiering, all of them queue behind Groq/NVIDIA/Gemini and burn the best
# free quotas on background work. By the time the visible lane wants real
# inference, the good providers are rate-limited.
#
# task_kind="background"  inner-layer noise. PREFERS public proxies
#                         (OllamaFreeAPI, Arko, OpenCode) so paid quotas
#                         are saved for meaningful work. Falls through to
#                         paid only if every public provider is blocked.
# task_kind="default"     historical behaviour: paid first, public as
#                         fallback. Use this when the call shape isn't
#                         strongly background but still doesn't deserve
#                         visible-lane treatment.
# task_kind="important"   paid only, no public fallback. For council
#                         deliberation, agent reasoning, anywhere quality
#                         matters and we'd rather fail than degrade.

_PUBLIC_PROXY_PROVIDERS = ("ollamafreeapi", "arko", "opencode")

# Round-robin counter so consecutive background calls spread across the
# public-proxy providers rather than draining one. Module-level + thread-
# safe enough for single-process Jarvis runtime; if we ever scale out,
# replace with a DB-backed counter or a hash on request_id.
import itertools as _itertools
_BACKGROUND_ROTATOR = _itertools.cycle(_PUBLIC_PROXY_PROVIDERS)


def _is_public_proxy(provider: str) -> bool:
    return str(provider or "").strip().lower() in _PUBLIC_PROXY_PROVIDERS


def select_cheap_lane_target(
    *,
    skip_providers: frozenset[str] = frozenset(),
    task_kind: str = "default",
) -> dict[str, object]:
    """Pick a cheap-lane provider. See task_kind notes above for routing.

    Phase B (2026-04-26): public-proxies are kept in the candidate list
    so that callers fall through gracefully instead of collapsing when
    paid quotas are blown.
    Phase C (2026-04-28): task_kind tiering so background callers prefer
    public proxies up front, saving paid quota for meaningful work.
    """
    kind = (task_kind or "default").strip().lower()

    candidates = _configured_cheap_candidates(
        include_public_proxy=True, skip_providers=skip_providers
    )

    # For "important" calls, drop public proxies entirely.
    if kind == "important":
        candidates = [c for c in candidates if not _is_public_proxy(c.get("provider", ""))]

    # For "background" calls, reorder so public proxies come first and rotate
    # which one is preferred this call.
    if kind == "background" and candidates:
        preferred_first = next(_BACKGROUND_ROTATOR)
        public = [c for c in candidates if _is_public_proxy(c.get("provider", ""))]
        paid = [c for c in candidates if not _is_public_proxy(c.get("provider", ""))]
        # Within the public group, put the rotator's choice first; keep the
        # rest in their stable priority order so quota state still matters.
        public.sort(key=lambda c: (
            0 if str(c.get("provider", "")).lower() == preferred_first else 1,
            int(c.get("priority") or 9999),
        ))
        candidates = public + paid

    blocked: list[dict[str, object]] = []
    for candidate in candidates:
        if not bool(candidate.get("credentials_ready")):
            blocked.append(
                {
                    "provider": candidate["provider"],
                    "model": candidate["model"],
                    "reason": "auth-not-ready",
                }
            )
            continue
        quota = _candidate_quota_snapshot(candidate)
        if quota["blocked"]:
            blocked.append(
                {
                    "provider": candidate["provider"],
                    "model": candidate["model"],
                    "reason": quota["status"],
                }
            )
            continue
        adaptive = _candidate_adaptive_snapshot(candidate)
        return {
            **candidate,
            "effective_priority": adaptive["effective_priority"],
            "adaptive_penalty": adaptive["adaptive_penalty"],
            "selection_reason": f"healthy-headroom:{kind}",
            "task_kind": kind,
            "blocked_candidates": blocked,
        }
    return {
        "active": False,
        "lane": "cheap",
        "status": "no-healthy-provider",
        "task_kind": kind,
        "blocked_candidates": blocked,
    }


def execute_cheap_lane_via_pool(
    *,
    message: str,
    skip_providers: frozenset[str] = frozenset(),
    task_kind: str = "default",
) -> dict[str, object]:
    target = select_cheap_lane_target(
        skip_providers=skip_providers,
        task_kind=task_kind,
    )
    if not bool(target.get("active", True)) or not str(target.get("provider") or "").strip():
        raise RuntimeError("cheap lane not executable: no-healthy-provider")

    provider = str(target.get("provider") or "").strip()
    model = str(target.get("model") or "").strip()
    profile = str(target.get("auth_profile") or "").strip()
    started_at = datetime.now(UTC)
    input_tokens = _estimate_tokens(message)
    try:
        result = _execute_provider_chat(
            provider=provider,
            model=model,
            auth_profile=profile,
            base_url=str(target.get("base_url") or "").strip(),
            message=message,
        )
    except CheapProviderError as exc:
        _register_provider_failure(
            provider=provider,
            model=model,
            auth_profile=profile,
            error=exc,
            smoke_test=False,
        )
        fallback = _fallback_after_failure(
            failed_provider=provider,
            failed_model=model,
        )
        if fallback is not None:
            event_bus.publish(
                "runtime.cheap_lane_provider_failed_over",
                {
                    "from_provider": provider,
                    "from_model": model,
                    "to_provider": fallback["provider"],
                    "to_model": fallback["model"],
                    "reason": exc.code,
                },
            )
            return execute_cheap_lane_via_pool(message=message, skip_providers=skip_providers | {provider})
        raise RuntimeError(f"{provider} cheap lane failed: {exc.code}: {exc.message}")

    output_tokens = int(result.get("output_tokens") or _estimate_tokens(result["text"]))
    latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
    record_cheap_provider_invocation(
        provider=provider,
        model=model,
        status="completed",
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=float(result.get("cost_usd") or 0.0),
    )
    _record_provider_success(
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        quality_score=None,
        smoke_test=False,
    )
    record_cost(
        lane="cheap",
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=float(result.get("cost_usd") or 0.0),
    )
    event_bus.publish(
        "runtime.cheap_lane_provider_completed",
        {
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )
    return {
        "lane": "cheap",
        "provider": provider,
        "model": model,
        "status": "completed",
        "execution_mode": "cheap-provider-pool",
        "source": "cheap-provider-runtime",
        "text": str(result["text"]),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": float(result.get("cost_usd") or 0.0),
    }


def _public_safe_candidates() -> list[dict[str, object]]:
    """Build the public-safe candidate pool: ollamafreeapi (lane=cheap)
    plus local ollama (lane=local). Local ollama is included even though
    it's not registered under lane=cheap because the cloud-passthrough
    models there are the actual reliable public-safe path.

    Added 2026-05-14: was selecting only lane=cheap candidates filtered to
    ollamafreeapi, missing the entire local-ollama provider which has
    much better uptime.
    """
    registry = load_provider_router_registry()
    provider_entries = {
        str(item.get("provider") or "").strip(): item
        for item in registry.get("providers") or []
        if bool(item.get("enabled", True))
    }
    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in registry.get("models") or []:
        if not bool(item.get("enabled", True)):
            continue
        provider = str(item.get("provider") or "").strip()
        lane = str(item.get("lane") or "").strip()
        # Accept ollamafreeapi at any lane (was cheap-only), and ollama
        # at lane=local since that's the configured shape today.
        if provider == "ollamafreeapi":
            pass  # accept
        elif provider == "ollama" and lane in {"local", "cheap"}:
            pass  # accept
        else:
            continue
        model = str(item.get("model") or "").strip()
        if not provider or not model:
            continue
        key = (provider, model)
        if key in seen:
            continue
        seen.add(key)
        provider_entry = provider_entries.get(provider, {})
        defaults = provider_runtime_defaults(provider)
        auth_profile = str(provider_entry.get("auth_profile") or "").strip()
        # Local ollama uses auth_mode='none' and isn't in CHEAP_PROVIDER_DEFAULTS
        # — provider_auth_ready would return False even though no auth is
        # needed. Special-case: trust local ollama at base_url when auth_mode
        # is 'none' or empty.
        auth_mode = str(provider_entry.get("auth_mode") or "").strip().lower()
        if provider == "ollama":
            credentials_ready = auth_mode in {"", "none"}
            # Honor per-model priority override from the registry if set,
            # else default to 50 (between top-tier commercial and the
            # ollamafreeapi fallback at 95). Lower is better.
            priority_val = int(item.get("priority") or 50)
        else:
            credentials_ready = provider_auth_ready(
                provider=provider,
                auth_profile=auth_profile,
            )
            priority_val = int(defaults.get("priority") or 9999)
        candidates.append(
            {
                "active": True,
                "lane": "cheap",  # treated as cheap for selection
                "provider": provider,
                "model": model,
                "auth_profile": auth_profile,
                "auth_mode": auth_mode,
                "base_url": str(provider_entry.get("base_url") or defaults.get("base_url") or "").strip(),
                "credentials_ready": credentials_ready,
                "priority": priority_val,
                "rpm_limit": defaults.get("rpm_limit"),
                "daily_limit": defaults.get("daily_limit"),
                "daily_neurons": defaults.get("daily_neurons"),
                "source": "public-safe-pool",
                "updated_at": str(item.get("updated_at") or ""),
            }
        )
    return candidates


def select_public_safe_cheap_lane_target() -> dict[str, object]:
    """Pick the highest-priority ready public-safe provider for cheap-lane work.

    Public-safe = provider where outbound messages don't expose identity
    to a commercial API. Two providers qualify:
      - ollamafreeapi (public proxy, no logging)
      - ollama (local Ollama on 127.0.0.1, including :cloud suffixed
        models which go through Ollama's own passthrough — still under
        Ollama's privacy boundary, not direct commercial API)

    Walks both providers' candidates by base priority (lower = better),
    skipping blocked/unauthorized ones, and returns the first ready hit.
    Updated 2026-05-14: was hardcoded to ollamafreeapi only — ollamafreeapi
    is too often down, so local Ollama is the more reliable public-safe lane.
    """
    candidates = _public_safe_candidates()
    # Prefer local ollama before ollamafreeapi (better uptime), then by priority
    candidates.sort(key=lambda c: (
        0 if c.get("provider") == "ollama" else 1,
        int(c.get("priority") or 9999),
    ))
    for candidate in candidates:
        if not bool(candidate.get("credentials_ready")):
            continue
        quota = _candidate_quota_snapshot(candidate)
        if quota["blocked"]:
            continue
        adaptive = _candidate_adaptive_snapshot(candidate)
        return {
            **candidate,
            "effective_priority": adaptive["effective_priority"],
            "adaptive_penalty": adaptive["adaptive_penalty"],
            "selection_reason": f"public-safe-{candidate.get('provider')}",
        }
    return {
        "active": False,
        "lane": "cheap",
        "status": "no-public-safe-provider",
    }


def execute_public_safe_cheap_lane(*, message: str) -> dict[str, object]:
    target = select_public_safe_cheap_lane_target()
    provider = str(target.get("provider") or "").strip()
    model = str(target.get("model") or "").strip()
    if provider and model:
        profile = str(target.get("auth_profile") or "").strip()
        started_at = datetime.now(UTC)
        try:
            result = _execute_provider_chat(
                provider=provider,
                model=model,
                auth_profile=profile,
                base_url=str(target.get("base_url") or "").strip(),
                message=message,
            )
        except CheapProviderError as exc:
            _register_provider_failure(
                provider=provider,
                model=model,
                auth_profile=profile,
                error=exc,
                smoke_test=False,
            )
        else:
            latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
            _record_provider_success(
                provider=provider,
                model=model,
                latency_ms=latency_ms,
                quality_score=None,
                smoke_test=False,
            )
            return {
                "lane": "cheap",
                "provider": provider,
                "model": model,
                "status": "completed",
                "execution_mode": "public-safe-cheap-provider",
                "source": "cheap-provider-runtime",
                "text": str(result.get("text") or ""),
                "input_tokens": _estimate_tokens(message),
                "output_tokens": int(
                    result.get("output_tokens") or _estimate_tokens(str(result.get("text") or ""))
                ),
                "cost_usd": float(result.get("cost_usd") or 0.0),
            }
    return _execute_public_safe_local_ollama(message=message)


def _configured_cheap_candidates(
    *, include_public_proxy: bool, skip_providers: frozenset[str] = frozenset()
) -> list[dict[str, object]]:
    registry = load_provider_router_registry()
    provider_entries = {
        str(item.get("provider") or "").strip(): item
        for item in registry.get("providers") or []
        if bool(item.get("enabled", True))
    }
    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in registry.get("models") or []:
        if not bool(item.get("enabled", True)):
            continue
        if str(item.get("lane") or "").strip() != "cheap":
            continue
        provider = str(item.get("provider") or "").strip()
        model = str(item.get("model") or "").strip()
        if provider in ("ollamafreeapi", "arko") and not include_public_proxy:
            # Both are third-party public-proxy lanes — only enabled when
            # callers explicitly opt in (e.g. final-fallback chains).
            continue
        if skip_providers and provider in skip_providers:
            continue
        if not provider or not model:
            continue
        key = (provider, model)
        if key in seen:
            continue
        seen.add(key)
        provider_entry = provider_entries.get(provider, {})
        defaults = provider_runtime_defaults(provider)
        auth_profile = str(provider_entry.get("auth_profile") or "").strip()
        candidates.append(
            {
                "active": True,
                "lane": "cheap",
                "provider": provider,
                "model": model,
                "auth_profile": auth_profile,
                "auth_mode": str(provider_entry.get("auth_mode") or "").strip(),
                "base_url": str(provider_entry.get("base_url") or defaults.get("base_url") or "").strip(),
                "credentials_ready": provider_auth_ready(
                    provider=provider,
                    auth_profile=auth_profile,
                ),
                "priority": int(defaults.get("priority") or 9999),
                "rpm_limit": defaults.get("rpm_limit"),
                "daily_limit": defaults.get("daily_limit"),
                "daily_neurons": defaults.get("daily_neurons"),
                "source": "provider-router-registry",
                "updated_at": str(item.get("updated_at") or ""),
            }
        )
    # Phase D (2026-05-14): also inject models from provider defaults' static_models
    # for providers that have no explicit model entries in the registry.
    # This lets us remove redundant model entries for providers like opencode
    # whose models are already declared in CHEAP_PROVIDER_DEFAULTS.
    for provider_name, provider_cfg in CHEAP_PROVIDER_DEFAULTS.items():
        static_models = provider_cfg.get("static_models") or []
        if not static_models:
            continue
        provider_entry = provider_entries.get(provider_name, {})
        auth_profile = str(provider_entry.get("auth_profile") or "").strip()
        for sm in static_models:
            key = (provider_name, sm)
            if key in seen:
                continue
            if skip_providers and provider_name in skip_providers:
                continue
            if provider_name in ("ollamafreeapi", "arko") and not include_public_proxy:
                continue
            seen.add(key)
            candidates.append(
                {
                    "active": True,
                    "lane": "cheap",
                    "provider": provider_name,
                    "model": sm,
                    "auth_profile": auth_profile,
                    "auth_mode": str(provider_entry.get("auth_mode") or "").strip(),
                    "base_url": str(
                        provider_entry.get("base_url")
                        or provider_cfg.get("base_url")
                        or ""
                    ).strip(),
                    "credentials_ready": provider_auth_ready(
                        provider=provider_name,
                        auth_profile=auth_profile,
                    ),
                    "priority": int(provider_cfg.get("priority") or 9999),
                    "rpm_limit": provider_cfg.get("rpm_limit"),
                    "daily_limit": provider_cfg.get("daily_limit"),
                    "daily_neurons": provider_cfg.get("daily_neurons"),
                    "source": "provider-defaults-static-models",
                    "updated_at": "",
                }
            )
    candidates.sort(
        key=lambda item: (
            _candidate_adaptive_snapshot(item)["effective_priority"],
            str(item.get("updated_at") or ""),
        )
    )
    return candidates


def _candidate_quota_snapshot(candidate: dict[str, object]) -> dict[str, object]:
    provider = str(candidate["provider"])
    model = str(candidate["model"])
    # TTL cache via shared_cache (2026-05-15): SQLite-backed so all 4
    # workers see the same cached quota state. Quota counts barely move
    # on the 2s timescale, and MC polling + awareness builders hammer
    # this repeatedly.
    from core.services import shared_cache as _sc
    _qkey = f"{_QUOTA_SNAPSHOT_PREFIX}{provider}/{model}"
    _cached = _sc.get(_qkey)
    if isinstance(_cached, dict):
        return _cached
    state = get_cheap_provider_runtime_state(provider=provider, model=model) or {}
    now = datetime.now(UTC)
    cooldown_until_raw = str(state.get("cooldown_until") or "").strip()
    cooldown_active = False
    if cooldown_until_raw:
        try:
            cooldown_active = datetime.fromisoformat(cooldown_until_raw) > now
        except ValueError:
            cooldown_active = False
    minute_since = (now - timedelta(minutes=1)).isoformat()
    day_since = (now - timedelta(hours=_QUOTA_RESET_HOURS)).isoformat()
    requests_last_minute = count_cheap_provider_invocations(
        provider=provider,
        since=minute_since,
    )
    requests_last_day = count_cheap_provider_invocations(
        provider=provider,
        since=day_since,
    )
    rpm_limit = candidate.get("rpm_limit")
    daily_limit = candidate.get("daily_limit")
    rpm_exhausted = isinstance(rpm_limit, int) and requests_last_minute >= rpm_limit
    daily_exhausted = isinstance(daily_limit, int) and requests_last_day >= daily_limit
    status = "ready"
    if cooldown_active:
        status = "cooldown-active"
    elif rpm_exhausted:
        status = "rpm-exhausted"
    elif daily_exhausted:
        status = "daily-exhausted"
    snapshot = {
        "status": status,
        "blocked": cooldown_active or rpm_exhausted or daily_exhausted,
        "cooldown_active": cooldown_active,
        "cooldown_until": cooldown_until_raw or None,
        "requests_last_minute": requests_last_minute,
        "requests_last_day": requests_last_day,
        "rpm_limit": rpm_limit,
        "daily_limit": daily_limit,
        "daily_neurons": candidate.get("daily_neurons"),
    }
    _sc.set(_qkey, snapshot, ttl_seconds=_QUOTA_SNAPSHOT_TTL_SECONDS)
    return snapshot


def _fallback_after_failure(*, failed_provider: str, failed_model: str) -> dict[str, object] | None:
    target = select_cheap_lane_target()
    provider = str(target.get("provider") or "")
    model = str(target.get("model") or "")
    if provider and model and (provider, model) != (failed_provider, failed_model):
        return target
    return None


def _candidate_adaptive_snapshot(
    candidate: dict[str, object],
    *,
    state: dict[str, object] | None = None,
) -> dict[str, object]:
    current_state = state or get_cheap_provider_runtime_state(
        provider=str(candidate["provider"]),
        model=str(candidate["model"]),
    ) or {}
    metadata = _decode_state_metadata(current_state)
    base_priority = int(candidate.get("priority") or 9999)
    success_count = int(metadata.get("success_count") or 0)
    failure_count = int(metadata.get("failure_count") or 0)
    smoke_success_count = int(metadata.get("smoke_success_count") or 0)
    smoke_failure_count = int(metadata.get("smoke_failure_count") or 0)
    avg_latency_ms = float(metadata.get("avg_latency_ms") or 0.0)
    avg_quality_score = float(metadata.get("avg_quality_score") or 1.0)
    total_runs = success_count + failure_count
    success_ratio = 1.0 if total_runs <= 0 else success_count / total_runs
    total_smokes = smoke_success_count + smoke_failure_count
    smoke_success_ratio = 1.0 if total_smokes <= 0 else smoke_success_count / total_smokes
    quality_penalty = max(0.0, (1.0 - avg_quality_score) * 8.0)
    reliability_penalty = max(0.0, (1.0 - success_ratio) * 10.0)
    smoke_penalty = max(0.0, (1.0 - smoke_success_ratio) * 8.0)
    latency_penalty = min(6.0, avg_latency_ms / 1200.0)
    adaptive_penalty = int(round(quality_penalty + reliability_penalty + smoke_penalty + latency_penalty))
    return {
        "base_priority": base_priority,
        "effective_priority": base_priority + adaptive_penalty,
        "adaptive_penalty": adaptive_penalty,
        "success_count": success_count,
        "failure_count": failure_count,
        "smoke_success_count": smoke_success_count,
        "smoke_failure_count": smoke_failure_count,
        "success_ratio": round(success_ratio, 4),
        "smoke_success_ratio": round(smoke_success_ratio, 4),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "avg_quality_score": round(avg_quality_score, 4),
    }


def _record_provider_success(
    *,
    provider: str,
    model: str,
    latency_ms: int,
    quality_score: float | None,
    smoke_test: bool,
) -> None:
    current_state = get_cheap_provider_runtime_state(provider=provider, model=model) or {}
    metadata = _decode_state_metadata(current_state)
    success_count = int(metadata.get("success_count") or 0) + 1
    smoke_success_count = int(metadata.get("smoke_success_count") or 0) + (1 if smoke_test else 0)
    avg_latency_ms = _rolling_average(
        current_avg=float(metadata.get("avg_latency_ms") or 0.0),
        current_count=int(metadata.get("success_count") or 0),
        new_value=float(latency_ms),
    )
    avg_quality_score = float(metadata.get("avg_quality_score") or 1.0)
    quality_count = int(metadata.get("quality_count") or 0)
    if quality_score is not None:
        avg_quality_score = _rolling_average(
            current_avg=avg_quality_score,
            current_count=quality_count,
            new_value=float(quality_score),
        )
        quality_count += 1
    upsert_cheap_provider_runtime_state(
        provider=provider,
        model=model,
        status="ready",
        auth_ready=True,
        quota_limited=False,
        cooldown_until=None,
        last_error_code="",
        last_error_message="",
        last_success_at=datetime.now(UTC).isoformat(),
        metadata_json=json.dumps(
            {
                **metadata,
                "protocol": provider_runtime_defaults(provider).get("protocol"),
                "success_count": success_count,
                "smoke_success_count": smoke_success_count,
                "avg_latency_ms": avg_latency_ms,
                "avg_quality_score": avg_quality_score,
                "quality_count": quality_count,
            },
            ensure_ascii=False,
        ),
    )


def _register_provider_failure(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    error: CheapProviderError,
    smoke_test: bool = False,
) -> None:
    now = datetime.now(UTC)
    cooldown_until = None
    quota_limited = False
    auth_ready = provider_auth_ready(provider=provider, auth_profile=auth_profile)
    current_state = get_cheap_provider_runtime_state(provider=provider, model=model) or {}
    metadata = _decode_state_metadata(current_state)
    if error.code in {"rate-limited", "quota-exhausted", "credits-exhausted"}:
        quota_limited = True
        retry_after = error.retry_after_seconds or _default_failure_cooldown_seconds(error.code)
        cooldown_until = (now + timedelta(seconds=retry_after)).isoformat()
    elif error.code == "auth-rejected":
        auth_ready = False
    elif error.code in {"provider-blocked", "provider-error", "model-not-found", "model-unavailable", "request-failed"}:
        retry_after = error.retry_after_seconds or _default_failure_cooldown_seconds(error.code)
        cooldown_until = (now + timedelta(seconds=retry_after)).isoformat()
    record_cheap_provider_invocation(
        provider=provider,
        model=model,
        status="failed",
        error_code=error.code,
        error_message=error.message,
        retry_after_seconds=error.retry_after_seconds,
    )
    upsert_cheap_provider_runtime_state(
        provider=provider,
        model=model,
        status=error.code,
        auth_ready=auth_ready,
        quota_limited=quota_limited,
        cooldown_until=cooldown_until,
        last_error_code=error.code,
        last_error_message=error.message,
        last_failure_at=now.isoformat(),
        metadata_json=json.dumps(
            {
                **metadata,
                "failure_count": int(metadata.get("failure_count") or 0) + 1,
                "smoke_failure_count": int(metadata.get("smoke_failure_count") or 0)
                + (1 if smoke_test else 0),
                "status_code": error.status_code,
                "retry_after_seconds": error.retry_after_seconds,
            },
            ensure_ascii=False,
        ),
    )
    event_bus.publish(
        "runtime.cheap_lane_provider_failed",
        {
            "provider": provider,
            "model": model,
            "code": error.code,
            "retry_after_seconds": error.retry_after_seconds,
            "status_code": error.status_code,
        },
    )


def _execute_provider_chat(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
) -> dict[str, object]:
    if provider in _OPENAI_COMPATIBLE_PROVIDERS:
        return _execute_openai_compatible_chat(
            provider=provider,
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            message=message,
        )
    if provider == "gemini":
        return _execute_gemini_chat(
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            message=message,
        )
    if provider == "cloudflare":
        return _execute_cloudflare_chat(
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            message=message,
        )
    if provider == "ollamafreeapi":
        return _execute_ollamafreeapi_chat(
            model=model,
            message=message,
        )
    if provider == "ollama":
        return _execute_local_ollama_chat(
            model=model,
            base_url=base_url,
            message=message,
        )
    if provider == "arko":
        return _execute_arko_chat(message=message)
    if provider == _OPENAI_CODEX_PROVIDER:
        return _execute_openai_codex_chat(
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            message=message,
        )
    raise CheapProviderError(
        provider=provider,
        code="unsupported-provider",
        message=f"cheap provider not supported: {provider}",
    )


def _execute_openai_compatible_chat(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str | None = None,
    messages: list[dict] | None = None,
    tools: list[dict] | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
) -> dict[str, object]:
    credentials = _require_credentials(profile=auth_profile, provider=provider)
    root = str(base_url or provider_runtime_defaults(provider).get("base_url") or "").rstrip("/")
    headers = {
        "Authorization": f"Bearer {str(credentials.get('api_key') or '').strip()}",
    }
    if messages is None:
        if message is None:
            raise ValueError("Either 'messages' or 'message' must be provided")
        messages = [{"role": "user", "content": message}]
    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
        # Without an explicit max_tokens, OpenCode/MiniMax defaults to ~512
        # which truncates Jarvis mid-sentence (observed cutoff at "**Capability"
        # after exactly 549 output tokens). 4096 is generous enough for any
        # single visible reply without burning the free quota.
        "max_tokens": 4096,
    }
    # Lag 10 Phase 1 (2026-05-12): caller may pass modulated values.
    # When None, omit from payload so server-side defaults apply (cheap-lane
    # callers don't pass them; only visible-lane wrappers do).
    if temperature is not None:
        payload["temperature"] = float(temperature)
    if top_p is not None:
        payload["top_p"] = float(top_p)
    if tools:
        payload["tools"] = _normalize_tools_for_openai_chat(tools)
    if provider == "groq":
        data, _headers = _http_json_httpx(
            f"{root}/chat/completions",
            payload=payload,
            headers=headers,
            provider=provider,
        )
    else:
        data, _headers = _http_json(
            f"{root}/chat/completions",
            payload=payload,
            headers=headers,
            provider=provider,
        )
    first_msg = ((data.get("choices") or [{}])[0] or {}).get("message") or {}
    tool_calls = list(first_msg.get("tool_calls") or [])
    # Tool-only responses (no assistant text) are valid when tools are in
    # play — don't raise empty-response in that case.
    if tool_calls:
        try:
            text = _extract_openai_compatible_text(provider=provider, data=data)
        except CheapProviderError:
            text = ""
    else:
        text = _extract_openai_compatible_text(provider=provider, data=data)
    usage = data.get("usage") or {}
    prompt_estimate = sum(len(str(m.get("content", ""))) for m in messages) // 4
    # Deepseek (and a few other openai-compat providers) report cache hit/miss
    # split inside usage. Plumb through so cost calc and observability can
    # distinguish — Deepseek charges ~50x less for cache hits ($0.0028/M vs
    # $0.14/M on v4-flash). If absent, downstream pricing falls back to
    # treating all input as cache miss.
    cache_hit = int(usage.get("prompt_cache_hit_tokens") or 0)
    cache_miss = int(usage.get("prompt_cache_miss_tokens") or 0)
    enriched_usage = dict(usage)
    if provider == "deepseek":
        enriched_usage.setdefault("prompt_cache_hit_tokens", cache_hit)
        enriched_usage.setdefault("prompt_cache_miss_tokens", cache_miss)
        enriched_usage.setdefault("model", model)
    return {
        "text": text,
        "tool_calls": tool_calls,
        "input_tokens": int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or prompt_estimate
        ),
        "output_tokens": int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or _estimate_tokens(text)
        ),
        "cache_hit_tokens": cache_hit,
        "cache_miss_tokens": cache_miss,
        "cost_usd": float(_estimate_cheap_cost(provider=provider, usage=enriched_usage)),
    }


def deepseek_model_for_thinking_mode(model: str, thinking_mode: str) -> str:
    """Map composer's thinking_mode to the right Deepseek model alias.

    Deepseek toggler thinking-mode via MODEL-NAVN (ikke via param):
      - deepseek-chat       = v4-flash non-thinking (compat alias)
      - deepseek-v4-flash   = thinking-mode default
      - deepseek-reasoner   = v4-flash thinking (compat alias)
      - deepseek-v4-pro     = ALWAYS thinking (kan ikke slås fra)

    Composer modes:
      - fast  → ingen thinking, hurtig respons
      - think → default thinking
      - deep  → thinking + reasoning_effort hvis modellen understøtter

    Mapping for v4-flash:
      - fast  → swap til deepseek-chat (non-thinking)
      - think → deepseek-v4-flash som er
      - deep  → deepseek-v4-flash som er

    Mapping for v4-pro:
      - alle modes → uændret (kan ikke slås fra)

    Andre modeller (deepseek-chat, deepseek-reasoner) returneres uændret —
    bruger har eksplicit valgt en bestemt mode-variant.
    """
    mode = (thinking_mode or "think").strip().lower()
    m = (model or "").strip()
    if m == "deepseek-v4-flash" and mode == "fast":
        return "deepseek-chat"
    return m


_DSML_OPEN = "<｜｜DSML｜｜tool_calls>"
_DSML_CLOSE = "</｜｜DSML｜｜tool_calls>"


def _strip_dsml_leak(buffer: str, in_block: bool) -> tuple[str, str, bool]:
    """Strip Deepseek thinking-mode tool_call DSL from streaming content.

    Deepseek v4-pro can spill its internal tool_call DSL — wrapped in
    ``<｜｜DSML｜｜tool_calls>...</｜｜DSML｜｜tool_calls>`` (U+FF5C fullwidth
    bars) — into delta.content alongside the proper structured tool_calls
    array. Without this filter the user sees raw special-token markup,
    AND any tool arguments embedded there (which has previously included
    secrets the model planned to use). Strip the entire block; structured
    tool_calls.tool_calls path is unaffected.

    Returns ``(safe_chunk, remaining_buffer, in_block)``.

    The remaining_buffer holds either:
    - in_block=False: the tail that *might* be the start of a DSML opener
      we haven't fully matched yet (so we don't emit it prematurely).
    - in_block=True: bytes we're still skipping until the closer arrives.
    """
    safe: list[str] = []
    while buffer:
        if in_block:
            close_idx = buffer.find(_DSML_CLOSE)
            if close_idx == -1:
                # We're still inside the block; no close yet. Keep buffer
                # but cap it so a never-closing block doesn't grow unbounded.
                if len(buffer) > 8192:
                    buffer = buffer[-1024:]
                return "".join(safe), buffer, in_block
            buffer = buffer[close_idx + len(_DSML_CLOSE):]
            in_block = False
            continue
        # Not in block — find next opener
        open_idx = buffer.find(_DSML_OPEN)
        if open_idx == -1:
            # No full opener. But the buffer's tail could still be a partial
            # opener mid-stream (e.g. ends with "<｜｜D"). Hold back any tail
            # that *could* be a prefix of the opener to avoid emitting "<｜"
            # before deciding.
            tail_keep = 0
            for k in range(1, min(len(_DSML_OPEN), len(buffer)) + 1):
                if _DSML_OPEN.startswith(buffer[-k:]):
                    tail_keep = k
            if tail_keep:
                safe.append(buffer[:-tail_keep])
                return "".join(safe), buffer[-tail_keep:], in_block
            safe.append(buffer)
            return "".join(safe), "", in_block
        # Emit prefix before the opener, then enter block
        if open_idx > 0:
            safe.append(buffer[:open_idx])
        buffer = buffer[open_idx + len(_DSML_OPEN):]
        in_block = True
    return "".join(safe), "", in_block


def _iter_openai_compatible_chat_events(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
):
    """Stream OpenAI-compatible /chat/completions deltas via SSE.

    Yields dicts:
      {"kind": "delta", "text": "..."}                   — content token
      {"kind": "tool_call", "id":..., "name":..., "arguments":...}
      {"kind": "done",
       "input_tokens": N, "output_tokens": M,
       "cache_hit_tokens": H, "cache_miss_tokens": MS,
       "full_text": "...", "cost_usd": X}

    Tool-call accumulation: Chat Completions streams tool_calls in
    fragments keyed by index. First fragment usually has id+name+start
    of arguments; subsequent fragments append to arguments. We merge
    by index then yield one tool_call event per index when stream ends.

    stream_options.include_usage=true makes the server send a final
    chunk with full usage stats (incl. Deepseek's prompt_cache_*
    fields) before the [DONE] sentinel.
    """
    credentials = _require_credentials(profile=auth_profile, provider=provider)
    api_key = str(credentials.get("api_key") or "").strip()
    root = str(base_url or provider_runtime_defaults(provider).get("base_url") or "").rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    # Lag 10 Phase 1 (2026-05-12): caller may pass modulated values.
    # When None, omit from payload so server-side defaults apply (cheap-lane
    # callers don't pass them; only visible-lane wrappers do).
    if temperature is not None:
        payload["temperature"] = float(temperature)
    if top_p is not None:
        payload["top_p"] = float(top_p)
    if tools:
        payload["tools"] = _normalize_tools_for_openai_chat(tools)

    # 2026-05-22 (Claude): cache-mystery investigation. When the sentinel file
    # /tmp/jarvis-payload-dump exists, dump full payload JSON to
    # /tmp/jarvis-payload-dumps/payload-<ts>.json so two back-to-back live
    # calls can be byte-diffed to find the cache-breaking content. Provider-
    # gated to deepseek so cheap-lane bursts don't flood the dir.
    try:
        import os as _os
        if provider == "deepseek" and _os.path.exists("/tmp/jarvis-payload-dump"):
            from pathlib import Path as _P
            import time as _t
            _dump_dir = _P("/tmp/jarvis-payload-dumps")
            _dump_dir.mkdir(exist_ok=True)
            _dump_path = _dump_dir / f"payload-{int(_t.time()*1000)}-{model}.json"
            _dump_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, default=str)
            )
    except Exception:
        pass

    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    pending_tool_calls: dict[int, dict] = {}
    final_usage: dict = {}
    # DSML-leak filter (Deepseek v4-pro). The thinking-mode model can spill
    # its internal tool-call DSL ("<｜｜DSML｜｜tool_calls>...</｜｜DSML｜｜tool_calls>")
    # into delta.content before firing the proper structured tool_calls.
    # Without filtering, users see raw special-token markup AND any tool
    # arguments embedded there (which has previously included secrets the
    # model planned to use). Strip the entire block from user-visible
    # deltas. The structured tool_calls.tool_calls path is unaffected.
    _dsml_in_block = False
    _dsml_buffer = ""

    try:
        with httpx.stream(
            "POST", f"{root}/chat/completions",
            json=payload, headers=headers,
            timeout=httpx.Timeout(connect=15, read=None, write=15, pool=15),
        ) as response:
            if response.status_code == 401:
                raise CheapProviderError(
                    provider=provider, code="auth-failed",
                    message=f"{provider} API key rejected (HTTP 401)",
                    status_code=401,
                )
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", "60") or "60")
                raise CheapProviderError(
                    provider=provider, code="rate-limited",
                    message=f"{provider} rate limited (HTTP 429)",
                    retry_after_seconds=retry_after, status_code=429,
                )
            if response.status_code >= 400:
                body = b""
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) > 2000:
                        break
                raise CheapProviderError(
                    provider=provider, code="provider-error",
                    message=f"HTTP {response.status_code}: {body.decode('utf-8', errors='replace')[:500]}",
                    status_code=response.status_code,
                )
            for line in response.iter_lines():
                line = (line or "").strip()
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                # Usage-only chunks (stream_options=include_usage) have
                # empty choices but a populated usage block.
                usage_block = event.get("usage") or {}
                if usage_block:
                    final_usage = dict(usage_block)
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0] or {}).get("delta") or {}
                content = delta.get("content")
                if content:
                    _dsml_buffer += str(content)
                    safe_chunk, _dsml_buffer, _dsml_in_block = _strip_dsml_leak(
                        _dsml_buffer, _dsml_in_block
                    )
                    if safe_chunk:
                        text_parts.append(safe_chunk)
                        yield {"kind": "delta", "text": safe_chunk}
                # Deepseek thinking-mode emits reasoning as separate stream
                # field — capture but don't yield as user-visible delta
                # (UI renders it differently, and we need it for followup
                # replay regardless of UI choice).
                reasoning = delta.get("reasoning_content")
                if reasoning:
                    reasoning_parts.append(str(reasoning))
                    yield {"kind": "reasoning_delta", "text": str(reasoning)}
                tc_fragments = delta.get("tool_calls") or []
                for frag in tc_fragments:
                    if not isinstance(frag, dict):
                        continue
                    idx = int(frag.get("index") or 0)
                    slot = pending_tool_calls.setdefault(
                        idx, {"id": "", "name": "", "arguments": ""}
                    )
                    if frag.get("id"):
                        slot["id"] = str(frag.get("id"))
                    fn = frag.get("function") or {}
                    if fn.get("name"):
                        slot["name"] = str(fn.get("name"))
                    args_frag = fn.get("arguments")
                    if args_frag:
                        slot["arguments"] += str(args_frag)
    except CheapProviderError:
        raise
    except Exception as exc:
        raise CheapProviderError(
            provider=provider, code="stream-error",
            message=f"{provider} streaming failed: {exc}",
        ) from exc

    # Emit accumulated tool calls in index order (consumer expects them
    # before the done event so working_step gets surfaced correctly).
    for idx in sorted(pending_tool_calls.keys()):
        slot = pending_tool_calls[idx]
        if slot.get("name"):
            yield {
                "kind": "tool_call",
                "id": slot.get("id") or f"call_{idx}",
                "name": slot["name"],
                "arguments": slot.get("arguments") or "",
            }

    full_text = "".join(text_parts)
    input_tokens = int(final_usage.get("prompt_tokens") or final_usage.get("input_tokens") or 0)
    output_tokens = int(final_usage.get("completion_tokens") or final_usage.get("output_tokens") or 0)
    cache_hit = int(final_usage.get("prompt_cache_hit_tokens") or 0)
    cache_miss = int(final_usage.get("prompt_cache_miss_tokens") or 0)
    enriched_usage = dict(final_usage)
    if provider == "deepseek":
        enriched_usage.setdefault("model", model)
    cost_usd = float(_estimate_cheap_cost(provider=provider, usage=enriched_usage))
    yield {
        "kind": "done",
        "full_text": full_text,
        "reasoning_content": "".join(reasoning_parts),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_hit_tokens": cache_hit,
        "cache_miss_tokens": cache_miss,
        "cost_usd": cost_usd,
    }


def _execute_gemini_chat(
    *,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
) -> dict[str, object]:
    credentials = _require_credentials(profile=auth_profile, provider="gemini")
    api_key = str(credentials.get("api_key") or "").strip()
    root = str(base_url or provider_runtime_defaults("gemini").get("base_url") or "").rstrip("/")
    safe_model = urllib_parse.quote(model, safe="")
    url = f"{root}/models/{safe_model}:generateContent?key={urllib_parse.quote(api_key, safe='')}"
    data, _headers = _http_json(
        url,
        payload={"contents": [{"parts": [{"text": message}]}]},
        headers={},
        provider="gemini",
    )
    text = _extract_gemini_text(data)
    usage = data.get("usageMetadata") or {}
    return {
        "text": text,
        "output_tokens": int(usage.get("candidatesTokenCount") or _estimate_tokens(text)),
        "cost_usd": 0.0,
    }


def _execute_cloudflare_chat(
    *,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
) -> dict[str, object]:
    credentials = _require_credentials(profile=auth_profile, provider="cloudflare")
    api_key = str(credentials.get("api_key") or "").strip()
    account_id = str(credentials.get("account_id") or "").strip()
    root = str(base_url or provider_runtime_defaults("cloudflare").get("base_url") or "").rstrip("/")
    encoded_model = urllib_parse.quote(model, safe="@/-")
    url = f"{root}/accounts/{account_id}/ai/run/{encoded_model}"
    data, _headers = _http_json(
        url,
        payload={"messages": [{"role": "user", "content": message}]},
        headers={"Authorization": f"Bearer {api_key}"},
        provider="cloudflare",
    )
    text = _extract_cloudflare_text(data)
    return {
        "text": text,
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


def _list_openai_compatible_models(
    *,
    provider: str,
    auth_profile: str,
    base_url: str,
) -> list[dict[str, object]]:
    credentials = _require_credentials(profile=auth_profile, provider=provider)
    root = str(base_url or provider_runtime_defaults(provider).get("base_url") or "").rstrip("/")
    data, _headers = _http_json(
        f"{root}/models",
        headers={"Authorization": f"Bearer {str(credentials.get('api_key') or '').strip()}"},
        provider=provider,
        method="GET",
    )
    models = data.get("data") or []
    return [
        {
            "id": str(item.get("id") or "").strip(),
            "label": str(item.get("id") or item.get("name") or "").strip(),
        }
        for item in models
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]


def _list_gemini_models(*, auth_profile: str, base_url: str) -> list[dict[str, object]]:
    credentials = _require_credentials(profile=auth_profile, provider="gemini")
    api_key = str(credentials.get("api_key") or "").strip()
    root = str(base_url or provider_runtime_defaults("gemini").get("base_url") or "").rstrip("/")
    url = f"{root}/models?key={urllib_parse.quote(api_key, safe='')}"
    data, _headers = _http_json(url, headers={}, provider="gemini", method="GET")
    models = data.get("models") or []
    return [
        {
            "id": str(item.get("name") or "").replace("models/", "").strip(),
            "label": str(item.get("displayName") or item.get("name") or "").strip(),
        }
        for item in models
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]


def _list_cloudflare_models(*, auth_profile: str, base_url: str) -> list[dict[str, object]]:
    credentials = _require_credentials(profile=auth_profile, provider="cloudflare")
    api_key = str(credentials.get("api_key") or "").strip()
    account_id = str(credentials.get("account_id") or "").strip()
    root = str(base_url or provider_runtime_defaults("cloudflare").get("base_url") or "").rstrip("/")
    url = f"{root}/accounts/{account_id}/ai/models/search"
    data, _headers = _http_json(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        provider="cloudflare",
        method="GET",
    )
    results = data.get("result") or data.get("models") or []
    return [
        {
            "id": str(item.get("id") or item.get("name") or item.get("model") or "").strip(),
            "label": str(item.get("name") or item.get("id") or item.get("model") or "").strip(),
        }
        for item in results
        if isinstance(item, dict)
        and str(item.get("id") or item.get("name") or item.get("model") or "").strip()
    ]


def _list_ollamafreeapi_models() -> list[dict[str, object]]:
    from core.runtime.ollamafreeapi_provider import list_ollamafreeapi_models

    return [{"id": model, "label": model} for model in list_ollamafreeapi_models()]


def _list_openai_codex_models() -> list[dict[str, object]]:
    """Static model list for OpenAI Codex (ChatGPT Plus OAuth).

    The chatgpt.com/backend-api does not expose a /models endpoint.
    Models are discovered through Codex CLI and documentation.
    """
    static_models = provider_runtime_defaults(_OPENAI_CODEX_PROVIDER).get(
        "static_models", ["gpt-5.3-codex", "gpt-5.4"]
    )
    return [{"id": m, "label": m} for m in static_models]


_OFA_CB_FAILURES = 0
_OFA_CB_OPEN_UNTIL = 0.0
_OFA_CB_THRESHOLD = 3        # open after 3 consecutive fails
_OFA_CB_OPEN_DURATION_S = 300.0  # stay open 5 minutes
_OFA_CB_LOCK = __import__("threading").Lock()


def _ofa_circuit_open() -> bool:
    import time as _t
    with _OFA_CB_LOCK:
        return _t.time() < _OFA_CB_OPEN_UNTIL


def _ofa_circuit_record_failure() -> None:
    import time as _t
    global _OFA_CB_FAILURES, _OFA_CB_OPEN_UNTIL
    with _OFA_CB_LOCK:
        _OFA_CB_FAILURES += 1
        if _OFA_CB_FAILURES >= _OFA_CB_THRESHOLD:
            _OFA_CB_OPEN_UNTIL = _t.time() + _OFA_CB_OPEN_DURATION_S
            _OFA_CB_FAILURES = 0  # reset for next window


def _ofa_circuit_record_success() -> None:
    global _OFA_CB_FAILURES
    with _OFA_CB_LOCK:
        _OFA_CB_FAILURES = 0


def _execute_ollamafreeapi_chat(
    *,
    model: str,
    message: str,
) -> dict[str, object]:
    from core.runtime.ollamafreeapi_provider import call_ollamafreeapi

    if _ofa_circuit_open():
        raise CheapProviderError(
            provider="ollamafreeapi",
            code="circuit-open",
            message=(
                f"ollamafreeapi circuit breaker open (after "
                f"{_OFA_CB_THRESHOLD}+ consecutive failures, retrying in "
                f"{int(_OFA_CB_OPEN_DURATION_S/60)}m)"
            ),
        )

    try:
        data = call_ollamafreeapi(model=model, prompt=message, timeout=_DEFAULT_TIMEOUT_SECONDS)
    except Exception as exc:
        _ofa_circuit_record_failure()
        raise CheapProviderError(
            provider="ollamafreeapi",
            code="provider-error",
            message=str(exc),
        ) from exc
    _ofa_circuit_record_success()
    text = str((data.get("message") or {}).get("content") or "").strip()
    return {
        "text": text,
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


# ── Arko circuit breaker (mirror of the OllamaFreeAPI one) ────────────────
_ARKO_CB_THRESHOLD = 3        # consecutive failures before opening
_ARKO_CB_OPEN_DURATION_S = 180  # stay open for 3 minutes before retrying
_arko_cb_failures = 0
_arko_cb_opened_at: float = 0.0


def _arko_circuit_open() -> bool:
    global _arko_cb_failures, _arko_cb_opened_at
    if _arko_cb_failures < _ARKO_CB_THRESHOLD:
        return False
    if (time.time() - _arko_cb_opened_at) >= _ARKO_CB_OPEN_DURATION_S:
        # Cooldown elapsed — let one probe through.
        _arko_cb_failures = 0
        _arko_cb_opened_at = 0.0
        return False
    return True


def _arko_circuit_record_failure() -> None:
    global _arko_cb_failures, _arko_cb_opened_at
    _arko_cb_failures += 1
    if _arko_cb_failures >= _ARKO_CB_THRESHOLD and _arko_cb_opened_at == 0.0:
        _arko_cb_opened_at = time.time()


def _arko_circuit_record_success() -> None:
    global _arko_cb_failures, _arko_cb_opened_at
    _arko_cb_failures = 0
    _arko_cb_opened_at = 0.0


def _execute_arko_chat(*, message: str) -> dict[str, object]:
    from core.runtime.arko_provider import call_arko

    if _arko_circuit_open():
        raise CheapProviderError(
            provider="arko",
            code="circuit-open",
            message=(
                f"arko circuit breaker open (after {_ARKO_CB_THRESHOLD}+ "
                f"consecutive failures, retrying in "
                f"{int(_ARKO_CB_OPEN_DURATION_S/60)}m)"
            ),
        )

    try:
        data = call_arko(prompt=message, timeout=_DEFAULT_TIMEOUT_SECONDS)
    except Exception as exc:
        _arko_circuit_record_failure()
        raise CheapProviderError(
            provider="arko",
            code="provider-error",
            message=str(exc),
        ) from exc
    _arko_circuit_record_success()
    text = str((data.get("message") or {}).get("content") or "").strip()
    return {
        "text": text,
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


def _execute_openai_codex_chat(
    *,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
) -> dict[str, object]:
    """Execute a chat call via OpenAI's Codex Responses API.

    Uses OAuth bearer token obtained via get_openai_bearer_token() (which
    auto-reimports from ~/.codex/auth.json when the refresh token is stale).
    The endpoint is chatgpt.com/backend-api/codex/responses with SSE streaming.
    """
    from core.auth.openai_oauth import get_openai_bearer_token

    root = str(base_url or "https://chatgpt.com/backend-api").rstrip("/")
    bearer_token = get_openai_bearer_token(profile=auth_profile, auto_reimport=True)

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload: dict[str, object] = {
        "model": model,
        "instructions": "You are a helpful assistant. Respond concisely.",
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": message}],
            }
        ],
        "store": False,
        "stream": True,
    }
    # Codex Responses API lives under /codex/responses on chatgpt.com.
    # The plain /responses endpoint requires api.responses.write scope
    # which ChatGPT OAuth tokens don't include. The /codex/responses
    # endpoint accepts ChatGPT Plus OAuth bearer tokens (same path the
    # official Codex CLI uses). See OpenClaw issue #64133.
    url = f"{root}/codex/responses"

    try:
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )
    except httpx.ConnectError as exc:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="connection-error",
            message=f"Cannot connect to {url}: {exc}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="timeout",
            message=f"Request timed out after {_DEFAULT_TIMEOUT_SECONDS}s",
            retry_after_seconds=60,
        ) from exc

    if response.status_code == 401:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="auth-failed",
            message="OAuth bearer token rejected (HTTP 401). Token may be expired.",
        )
    if response.status_code == 403:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="forbidden",
            message="Access denied (HTTP 403). Account may lack codex scope.",
        )
    if response.status_code == 429:
        retry_after = int(response.headers.get("retry-after", "60") or "60")
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="rate-limited",
            message="Rate limited (HTTP 429)",
            retry_after_seconds=retry_after,
            status_code=429,
        )
    if response.status_code >= 400:
        body = response.text[:500]
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="provider-error",
            message=f"HTTP {response.status_code}: {body}",
            status_code=response.status_code,
        )

    # Parse SSE stream to extract text and usage
    text_parts: list[str] = []
    input_tokens = 0
    output_tokens = 0
    model_used = model

    for line in response.text.splitlines():
        line = line.strip()
        if not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            break
        try:
            event = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        event_type = str(event.get("type") or "")
        if event_type == "response.output_text.delta":
            delta = str(event.get("delta") or "")
            text_parts.append(delta)
        elif event_type == "response.output_text.done":
            # Full text aggregation event — override accumulated deltas
            full_text = str(event.get("text") or "")
            if full_text:
                text_parts = [full_text]
        elif event_type == "response.completed":
            # Final event with usage and model info
            response_obj = event.get("response") or event.get("result") or {}
            usage = response_obj.get("usage") or {}
            input_tokens = int(usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("output_tokens") or 0)
            model_from_response = str(response_obj.get("model") or "").strip()
            if model_from_response:
                model_used = model_from_response

    full_text = "".join(text_parts).strip()
    if not full_text and not text_parts:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="empty-response",
            message="Codex Responses API returned no text content",
        )

    # Fall back to estimation if usage wasn't provided
    if not input_tokens:
        input_tokens = _estimate_tokens(message)
    if not output_tokens:
        output_tokens = _estimate_tokens(full_text)

    return {
        "text": full_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": 0.0,  # Codex via ChatGPT Plus has no per-token billing
        "model_used": model_used,
    }


def _normalize_tools_for_openai_chat(tools: list[dict] | None) -> list[dict] | None:
    """Normalize tool defs to OpenAI Chat Completions format.

    Some tools in our registry are registered in Anthropic shape:
        {"name": "...", "description": "...", "input_schema": {...}}
    OpenAI Chat Completions (and Deepseek/Groq/etc.) require:
        {"type":"function", "function":{"name":"...","description":"...","parameters":{...}}}

    Without this conversion, deepseek rejects the request with HTTP 400
    "missing field type" on the offending tool. Run on every tool list
    before dispatching to /chat/completions.
    """
    if not tools:
        return None
    out: list[dict] = []
    seen_names: set[str] = set()

    def _add(tool: dict, name: str) -> None:
        # Deepseek (og strict OpenAI-compat) afviser med
        # "Tool names must be unique" hvis samme function-navn
        # registreres flere gange. Vores tool-registry har 3 dubletter
        # (process_list, goal_create, goal_list). Drop første-vinder —
        # bedre at miste en duplikat end at tabe hele turn'en.
        if not name or name in seen_names:
            return
        seen_names.add(name)
        out.append(tool)

    for t in tools:
        if not isinstance(t, dict):
            continue
        # Already Chat-Completions-shaped
        if t.get("type") == "function" and isinstance(t.get("function"), dict):
            _add(t, str((t.get("function") or {}).get("name") or ""))
            continue
        # Anthropic shape → convert
        if "input_schema" in t and "name" in t:
            _add(
                {
                    "type": "function",
                    "function": {
                        "name": str(t.get("name") or ""),
                        "description": str(t.get("description") or ""),
                        "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                    },
                },
                str(t.get("name") or ""),
            )
            continue
        # Bare-name shape (rare) — wrap minimally
        if "name" in t:
            _add(
                {
                    "type": "function",
                    "function": {
                        "name": str(t.get("name") or ""),
                        "description": str(t.get("description") or ""),
                        "parameters": t.get("parameters") or t.get("input_schema") or {"type": "object", "properties": {}},
                    },
                },
                str(t.get("name") or ""),
            )
    return out or None


def _convert_tools_to_responses_format(tools: list[dict] | None) -> list[dict] | None:
    """Convert Chat-Completions tool defs to Responses API format.

    Chat Completions:   {"type":"function", "function":{"name", "description", "parameters"}}
    Responses API:      {"type":"function", "name", "description", "parameters"}

    The Responses API flattens the function fields onto the tool object
    instead of nesting them. Both formats use type="function" but the
    location of name/description/parameters differs.
    """
    if not tools:
        return None
    out: list[dict] = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        # Already Responses-shaped
        if "name" in t and "function" not in t:
            out.append(t)
            continue
        fn = t.get("function") or {}
        if not fn:
            continue
        out.append({
            "type": "function",
            "name": str(fn.get("name") or ""),
            "description": str(fn.get("description") or ""),
            "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return out or None


def _iter_openai_codex_chat_events(
    *,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
    tools: list[dict] | None = None,
):
    """Stream raw SSE events from the OpenAI Codex Responses API.

    Yields dicts with shape:
      {"kind": "delta", "text": "..."}                — text token
      {"kind": "done", "input_tokens": N,
                       "output_tokens": M,
                       "model_used": "...",
                       "full_text": "..."}            — final event

    Uses httpx.stream() so deltas reach the consumer as the server
    emits them — the previous _execute_openai_codex_chat collects
    the entire response body before parsing, which made the visible
    lane look frozen for 5–30s while gpt-5.4 wrote.

    Caller is responsible for handling CheapProviderError; we raise
    the same shape as the sync version.
    """
    from core.auth.openai_oauth import get_openai_bearer_token

    root = str(base_url or "https://chatgpt.com/backend-api").rstrip("/")
    bearer_token = get_openai_bearer_token(profile=auth_profile, auto_reimport=True)

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload: dict[str, object] = {
        "model": model,
        "instructions": "You are a helpful assistant. Respond concisely.",
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": message}],
            }
        ],
        "store": False,
        "stream": True,
    }
    responses_tools = _convert_tools_to_responses_format(tools)
    if responses_tools:
        payload["tools"] = responses_tools
        # tool_choice: 'auto' lets the model decide; we keep it implicit
        # which Responses API treats as auto when tools are present.
    url = f"{root}/codex/responses"

    text_parts: list[str] = []
    input_tokens = 0
    output_tokens = 0
    model_used = model

    # Tool-call accumulation. Responses API streams a function_call as:
    #   1. response.output_item.added with item.type=='function_call'
    #      → records id + name (arguments may be empty initially)
    #   2. zero or more response.function_call_arguments.delta events
    #      → arguments accumulate as a JSON string
    #   3. response.output_item.done with the same item
    #      → final commit; we yield the tool_call event then
    # We key by item_id (Responses uses a stable id per output item).
    pending_tool_calls: dict[str, dict] = {}

    try:
        with httpx.stream(
            "POST", url, json=payload, headers=headers,
            timeout=httpx.Timeout(_DEFAULT_TIMEOUT_SECONDS, read=None),
        ) as response:
            if response.status_code == 401:
                raise CheapProviderError(
                    provider=_OPENAI_CODEX_PROVIDER,
                    code="auth-failed",
                    message="OAuth bearer token rejected (HTTP 401). Token may be expired.",
                )
            if response.status_code == 403:
                raise CheapProviderError(
                    provider=_OPENAI_CODEX_PROVIDER,
                    code="forbidden",
                    message="Access denied (HTTP 403). Account may lack codex scope.",
                )
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", "60") or "60")
                raise CheapProviderError(
                    provider=_OPENAI_CODEX_PROVIDER,
                    code="rate-limited",
                    message="Rate limited (HTTP 429)",
                    retry_after_seconds=retry_after,
                    status_code=429,
                )
            if response.status_code >= 400:
                # Read the body so we can report something useful
                body_bytes = b""
                for chunk in response.iter_bytes():
                    body_bytes += chunk
                    if len(body_bytes) > 2000:
                        break
                raise CheapProviderError(
                    provider=_OPENAI_CODEX_PROVIDER,
                    code="provider-error",
                    message=f"HTTP {response.status_code}: {body_bytes.decode('utf-8', errors='replace')[:500]}",
                    status_code=response.status_code,
                )

            # Iterate SSE lines as they arrive
            for line in response.iter_lines():
                line = (line or "").strip()
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                event_type = str(event.get("type") or "")
                if event_type == "response.output_text.delta":
                    delta = str(event.get("delta") or "")
                    if delta:
                        text_parts.append(delta)
                        yield {"kind": "delta", "text": delta}
                elif event_type == "response.output_text.done":
                    full_text = str(event.get("text") or "")
                    if full_text and not text_parts:
                        # Server didn't emit deltas, only a single done
                        text_parts.append(full_text)
                        yield {"kind": "delta", "text": full_text}
                elif event_type == "response.output_item.added":
                    # New output item — could be a function_call. Record
                    # the id+name so subsequent argument deltas can find it.
                    item = event.get("item") or {}
                    if isinstance(item, dict) and str(item.get("type") or "") == "function_call":
                        item_id = str(item.get("id") or item.get("call_id") or "")
                        name = str(item.get("name") or "")
                        call_id = str(item.get("call_id") or item_id)
                        if item_id and name:
                            pending_tool_calls[item_id] = {
                                "id": call_id,
                                "name": name,
                                "arguments": str(item.get("arguments") or ""),
                            }
                            yield {
                                "kind": "tool_call_start",
                                "id": call_id,
                                "name": name,
                            }
                elif event_type == "response.function_call_arguments.delta":
                    item_id = str(event.get("item_id") or "")
                    delta = str(event.get("delta") or "")
                    if item_id in pending_tool_calls and delta:
                        pending_tool_calls[item_id]["arguments"] += delta
                elif event_type == "response.function_call_arguments.done":
                    # Final aggregate — overrides accumulated args if provided
                    item_id = str(event.get("item_id") or "")
                    final_args = str(event.get("arguments") or "")
                    if item_id in pending_tool_calls and final_args:
                        pending_tool_calls[item_id]["arguments"] = final_args
                elif event_type == "response.output_item.done":
                    item = event.get("item") or {}
                    if isinstance(item, dict) and str(item.get("type") or "") == "function_call":
                        item_id = str(item.get("id") or item.get("call_id") or "")
                        if item_id in pending_tool_calls:
                            tc = pending_tool_calls.pop(item_id)
                            # Some servers include the final arguments here too
                            final_args = str(item.get("arguments") or "") or tc["arguments"]
                            yield {
                                "kind": "tool_call",
                                "id": tc["id"],
                                "name": tc["name"],
                                "arguments": final_args,
                            }
                elif event_type == "response.completed":
                    response_obj = event.get("response") or event.get("result") or {}
                    usage = response_obj.get("usage") or {}
                    input_tokens = int(usage.get("input_tokens") or 0)
                    output_tokens = int(usage.get("output_tokens") or 0)
                    model_from_response = str(response_obj.get("model") or "").strip()
                    if model_from_response:
                        model_used = model_from_response
    except httpx.ConnectError as exc:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="connection-error",
            message=f"Cannot connect to {url}: {exc}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="timeout",
            message=f"Request timed out after {_DEFAULT_TIMEOUT_SECONDS}s",
            retry_after_seconds=60,
        ) from exc

    full_text = "".join(text_parts).strip()
    if not full_text and not text_parts:
        raise CheapProviderError(
            provider=_OPENAI_CODEX_PROVIDER,
            code="empty-response",
            message="Codex Responses API returned no text content",
        )

    if not input_tokens:
        input_tokens = _estimate_tokens(message)
    if not output_tokens:
        output_tokens = _estimate_tokens(full_text)

    yield {
        "kind": "done",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_used": model_used,
        "full_text": full_text,
    }


_OLLAMA_LOCAL_TIMEOUT_SECONDS = 120


def _execute_local_ollama_chat(
    *, model: str, base_url: str, message: str
) -> dict[str, object]:
    """Call the local Ollama instance with a specific model.

    Added 2026-05-14 to support per-model selection from the public-safe
    cheap-lane pool (vs. _execute_public_safe_local_ollama which picks
    via resolve_provider_router_target and only respects lane=local).

    Uses a 120s timeout (vs the 30s default) because cloud-passthrough
    models on local Ollama can be slow on first call / cold start, and
    counterfactual prompts are longer than the typical heartbeat probe.
    """
    url = str(base_url or "http://127.0.0.1:11434").rstrip("/")
    payload = {
        "model": str(model or "").strip(),
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    try:
        # Use urllib directly with extended timeout — _http_json is locked
        # to _DEFAULT_TIMEOUT_SECONDS and shared by many providers.
        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            f"{url}/api/chat",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "jarvis-v2/cheap-lane",
            },
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=_OLLAMA_LOCAL_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise CheapProviderError(
            provider="ollama", code="request-failed", message=str(exc)
        )
    text = str((data.get("message") or {}).get("content") or "").strip()
    return {
        "lane": "cheap",
        "provider": "ollama",
        "model": model,
        "status": "completed",
        "execution_mode": "public-safe-local-ollama",
        "source": "cheap-provider-runtime",
        "text": text,
        "input_tokens": _estimate_tokens(message),
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


def _execute_public_safe_local_ollama(*, message: str) -> dict[str, object]:
    target = resolve_provider_router_target(lane="local")
    if not bool(target.get("active")) or str(target.get("provider") or "").strip() != "ollama":
        raise RuntimeError("public-safe local fallback unavailable")
    base_url = str(target.get("base_url") or "http://127.0.0.1:11434").rstrip("/")
    payload = {
        "model": str(target.get("model") or "").strip(),
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    data, _headers = _http_json(
        f"{base_url}/api/chat",
        payload=payload,
        headers={},
        provider="ollama",
    )
    text = str((data.get("message") or {}).get("content") or "").strip()
    return {
        "lane": "local",
        "provider": "ollama",
        "model": str(target.get("model") or "").strip(),
        "status": "completed",
        "execution_mode": "public-safe-local-fallback",
        "source": "cheap-provider-runtime",
        "text": text,
        "input_tokens": _estimate_tokens(message),
        "output_tokens": _estimate_tokens(text),
        "cost_usd": 0.0,
    }


def _require_credentials(*, profile: str, provider: str) -> dict[str, object]:
    credentials = get_provider_credentials(profile=profile, provider=provider)
    if not credentials:
        raise CheapProviderError(
            provider=provider,
            code="auth-not-ready",
            message=f"{provider} credentials missing for profile {profile}",
        )
    api_key = str(credentials.get("api_key") or "").strip()
    if provider == "cloudflare":
        if not api_key or not str(credentials.get("account_id") or "").strip():
            raise CheapProviderError(
                provider=provider,
                code="auth-not-ready",
                message="cloudflare requires api_key and account_id",
            )
    elif not api_key:
        raise CheapProviderError(
            provider=provider,
            code="auth-not-ready",
            message=f"{provider} api_key missing for profile {profile}",
        )
    return credentials


def _http_json(
    url: str,
    *,
    provider: str,
    method: str = "POST",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[dict[str, object], dict[str, str]]:
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "jarvis-v2/cheap-lane",
        **(headers or {}),
    }
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib_request.urlopen(req, timeout=_DEFAULT_TIMEOUT_SECONDS) as response:
            raw_headers = {key.lower(): value for key, value in response.headers.items()}
            data = json.loads(response.read().decode("utf-8"))
        return data, raw_headers
    except urllib_error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        retry_after = int(exc.headers.get("Retry-After", "0") or 0)
        code = _classify_http_error(provider=provider, status_code=exc.code, body=body_text)
        raise CheapProviderError(
            provider=provider,
            code=code,
            message=body_text[:500] or f"HTTP {exc.code}",
            retry_after_seconds=retry_after,
            status_code=exc.code,
        )
    except urllib_error.URLError as exc:
        raise CheapProviderError(
            provider=provider,
            code="unreachable",
            message=str(exc.reason),
        )
    except Exception as exc:
        raise CheapProviderError(
            provider=provider,
            code="request-failed",
            message=str(exc),
        )


def _http_json_httpx(
    url: str,
    *,
    provider: str,
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[dict[str, object], dict[str, str]]:
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "jarvis-v2/cheap-lane",
        **(headers or {}),
    }
    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = client.post(
                url,
                json=payload,
                headers=request_headers,
            )
            raw_headers = {key.lower(): value for key, value in response.headers.items()}
            response.raise_for_status()
            data = response.json()
        return data, raw_headers
    except httpx.HTTPStatusError as exc:
        body_text = exc.response.text
        retry_after = int(exc.response.headers.get("Retry-After", "0") or 0)
        code = _classify_http_error(
            provider=provider,
            status_code=exc.response.status_code,
            body=body_text,
        )
        raise CheapProviderError(
            provider=provider,
            code=code,
            message=body_text[:500] or f"HTTP {exc.response.status_code}",
            retry_after_seconds=retry_after,
            status_code=exc.response.status_code,
        )
    except httpx.RequestError as exc:
        raise CheapProviderError(
            provider=provider,
            code="unreachable",
            message=str(exc),
        )
    except Exception as exc:
        raise CheapProviderError(
            provider=provider,
            code="request-failed",
            message=str(exc),
        )


def _classify_http_error(*, provider: str, status_code: int, body: str) -> str:
    lowered = str(body or "").lower()
    if status_code == 402:
        return "credits-exhausted"
    if status_code == 404:
        if "no endpoints found" in lowered or "endpoint" in lowered:
            return "model-unavailable"
        return "model-not-found"
    if status_code == 401:
        return "auth-rejected"
    if status_code == 403:
        if "error code: 1010" in lowered or "access denied" in lowered or "forbidden" in lowered:
            return "provider-blocked"
        return "auth-rejected"
    if status_code == 429:
        if "quota" in lowered or "daily" in lowered or "insufficient credits" in lowered:
            return "quota-exhausted"
        return "rate-limited"
    if status_code >= 500:
        return "provider-error"
    return f"http-{status_code}"


def _default_failure_cooldown_seconds(code: str) -> int:
    normalized = str(code or "").strip()
    if normalized == "rate-limited":
        return 300
    if normalized in {"quota-exhausted", "credits-exhausted"}:
        return 3600
    if normalized in {"provider-blocked", "provider-error"}:
        return 1800
    if normalized in {"model-not-found", "model-unavailable"}:
        return 900
    return 300


def _decode_state_metadata(state: dict[str, object]) -> dict[str, object]:
    raw = state.get("metadata_json")
    if not raw:
        return {}
    try:
        decoded = json.loads(str(raw))
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _rolling_average(*, current_avg: float, current_count: int, new_value: float) -> float:
    if current_count <= 0:
        return float(new_value)
    return ((current_avg * current_count) + new_value) / float(current_count + 1)


def _smoke_quality_score(*, expected: str, actual: str) -> float:
    normalized_expected = _normalize_probe_text(expected)
    normalized_actual = _normalize_probe_text(actual)
    if normalized_actual == normalized_expected:
        return 1.0
    if normalized_expected and normalized_expected in normalized_actual:
        return 0.9
    return 0.4


def _normalize_probe_text(value: str) -> str:
    text = str(value or "").strip().strip("\"'`")
    return " ".join(text.lower().split())


def _extract_openai_compatible_text(*, provider: str, data: dict[str, object]) -> str:
    choices = data.get("choices") or []
    for item in choices:
        if not isinstance(item, dict):
            continue
        message = item.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts = [
                str(part.get("text") or "").strip()
                for part in content
                if isinstance(part, dict) and str(part.get("text") or "").strip()
            ]
            if parts:
                return "\n".join(parts).strip()
    raise CheapProviderError(
        provider=provider,
        code="empty-response",
        message="provider returned no assistant text",
    )


def _extract_gemini_text(data: dict[str, object]) -> str:
    candidates = data.get("candidates") or []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        texts = [
            str(part.get("text") or "").strip()
            for part in parts
            if isinstance(part, dict) and str(part.get("text") or "").strip()
        ]
        if texts:
            return "\n".join(texts).strip()
    raise CheapProviderError(
        provider="gemini",
        code="empty-response",
        message="gemini returned no candidate text",
    )


def _extract_cloudflare_text(data: dict[str, object]) -> str:
    result = data.get("result") or {}
    if isinstance(result, dict):
        response = str(result.get("response") or "").strip()
        if response:
            return response
        messages = result.get("messages") or []
        for item in messages:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if content:
                return content
    raise CheapProviderError(
        provider="cloudflare",
        code="empty-response",
        message="cloudflare returned no text response",
    )


def _listing_surface(
    *,
    provider: str,
    auth_profile: str,
    status: str,
    source: str,
    models: list[dict[str, object]],
    base_url: str = "",
) -> dict[str, object]:
    return {
        "provider": provider,
        "auth_profile": auth_profile,
        "source": source,
        "status": status,
        "base_url": base_url,
        "models": models,
    }


# DeepSeek pricing (per 1M tokens, USD). Source: https://api-docs.deepseek.com/
# Pulled 2026-05-07. v4-pro has a 75% promo until 2026-05-31 15:59 UTC — after
# that the full price kicks in. v4-flash flat priced; cache-hit ~50x cheaper
# than cache-miss. Update if Deepseek changes pricing.
_DEEPSEEK_PROMO_END_ISO = "2026-05-31T15:59:00+00:00"

_DEEPSEEK_PRICES_PER_M: dict[str, dict[str, Decimal]] = {
    "deepseek-v4-flash": {
        "cache_hit": Decimal("0.0028"),
        "cache_miss": Decimal("0.14"),
        "output": Decimal("0.28"),
    },
    "deepseek-v4-pro_promo": {
        "cache_hit": Decimal("0.003625"),
        "cache_miss": Decimal("0.435"),
        "output": Decimal("0.87"),
    },
    "deepseek-v4-pro_full": {
        "cache_hit": Decimal("0.0145"),
        "cache_miss": Decimal("1.74"),
        "output": Decimal("3.48"),
    },
}


def _deepseek_price_table(model: str) -> dict[str, Decimal] | None:
    if model == "deepseek-v4-flash":
        return _DEEPSEEK_PRICES_PER_M["deepseek-v4-flash"]
    if model == "deepseek-v4-pro":
        from datetime import datetime, timezone
        promo_end = datetime.fromisoformat(_DEEPSEEK_PROMO_END_ISO)
        in_promo = datetime.now(timezone.utc) < promo_end
        key = "deepseek-v4-pro_promo" if in_promo else "deepseek-v4-pro_full"
        return _DEEPSEEK_PRICES_PER_M[key]
    return None


def _estimate_deepseek_cost(usage: dict[str, object]) -> Decimal:
    model = str(usage.get("model") or "").strip()
    table = _deepseek_price_table(model)
    if table is None:
        return Decimal("0")
    prompt_total = Decimal(str(usage.get("prompt_tokens") or 0))
    cache_hit = Decimal(str(usage.get("prompt_cache_hit_tokens") or 0))
    cache_miss = Decimal(str(usage.get("prompt_cache_miss_tokens") or 0))
    # If the API didn't split it, treat all prompt tokens as cache miss
    # (conservative — tracks higher cost rather than under-reporting).
    if cache_hit == 0 and cache_miss == 0:
        cache_miss = prompt_total
    output = Decimal(str(usage.get("completion_tokens") or usage.get("output_tokens") or 0))
    million = Decimal("1000000")
    cost = (
        cache_hit * table["cache_hit"]
        + cache_miss * table["cache_miss"]
        + output * table["output"]
    ) / million
    return cost


def _estimate_cheap_cost(*, provider: str, usage: dict[str, object]) -> Decimal:
    if provider == "deepseek":
        return _estimate_deepseek_cost(usage)
    # Free-tier cheap providers are tracked primarily by quota rather than spend.
    if provider != "openrouter":
        return Decimal("0")
    prompt_tokens = Decimal(str(usage.get("prompt_tokens") or usage.get("input_tokens") or 0))
    completion_tokens = Decimal(str(usage.get("completion_tokens") or usage.get("output_tokens") or 0))
    return (prompt_tokens + completion_tokens) * Decimal("0")


def _estimate_tokens(text: str) -> int:
    normalized = " ".join((text or "").split())
    if not normalized:
        return 1
    return max(1, len(normalized) // 4)
