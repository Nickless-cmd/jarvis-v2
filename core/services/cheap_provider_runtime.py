from __future__ import annotations

# ── cheap_provider_runtime (facade) ──────────────────────────────────────────
# This module was split (Boy-Scout rule, behavior-preserving) into:
#   - cheap_provider_runtime_adapters.py   provider dispatch/adapters/http/cost
#   - cheap_provider_runtime_streaming.py  SSE streamers + OpenAI-Codex protocol
#   - cheap_provider_runtime_selection.py  routing/quota/adaptive/failover/state
#
# This file stays the public import surface (blast-radius 45 across the codebase)
# and re-exports every symbol from the submodules, plus the shared third-party /
# db / eventbus imports that must remain module attributes here because tests
# monkeypatch them (httpx, urllib_request, record_cheap_provider_invocation, …).
#
# Nothing below changes behaviour — it only relocates definitions and re-exports
# them. Import stability and monkeypatch seams are preserved: patching
# cheap_provider_runtime.<name> still works because the selection/adapter
# submodules resolve the patchable dispatch/db symbols through this facade at
# call time.

# ── Shared imports kept on the facade (module attributes tests patch/read) ────
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

# ── Adapter layer (provider dispatch, HTTP, cost, extractors, circuit breakers) ──
from core.services.cheap_provider_runtime_adapters import (
    CHEAP_PROVIDER_DEFAULTS,
    CheapProviderError,
    _ARKO_CB_OPEN_DURATION_S,
    _ARKO_CB_THRESHOLD,
    _ARKO_PROVIDER_ID,
    _DEEPSEEK_PRICES_PER_M,
    _DEEPSEEK_PROMO_END_ISO,
    _DEFAULT_TIMEOUT_SECONDS,
    _DSML_CLOSE,
    _DSML_OPEN,
    _OFA_CB_OPEN_DURATION_S,
    _OFA_CB_THRESHOLD,
    _OFA_PROVIDER_ID,
    _OLLAMA_LOCAL_TIMEOUT_SECONDS,
    _OPENAI_CODEX_PROVIDER,
    _OPENAI_COMPATIBLE_PROVIDERS,
    _arko_circuit_open,
    _arko_circuit_record_failure,
    _arko_circuit_record_success,
    _classify_http_error,
    _deepseek_price_table,
    _default_failure_cooldown_seconds,
    _estimate_cheap_cost,
    _estimate_deepseek_cost,
    _estimate_tokens,
    _execute_arko_chat,
    _execute_cloudflare_chat,
    _execute_gemini_chat,
    _execute_local_ollama_chat,
    _execute_ollamafreeapi_chat,
    _execute_openai_compatible_chat,
    _execute_provider_chat,
    _execute_public_safe_local_ollama,
    _extract_cloudflare_text,
    _extract_gemini_text,
    _extract_openai_compatible_text,
    _flatten_messages_to_text,
    _http_json,
    _http_json_httpx,
    _list_cloudflare_models,
    _list_gemini_models,
    _list_ollamafreeapi_models,
    _list_openai_compatible_models,
    _listing_surface,
    _normalize_tools_for_openai_chat,
    _ofa_circuit_open,
    _ofa_circuit_record_failure,
    _ofa_circuit_record_success,
    _require_credentials,
    _strip_dsml_leak,
    deepseek_model_for_thinking_mode,
    list_provider_models,
    provider_auth_ready,
    provider_runtime_defaults,
    supported_cheap_providers,
)

# ── Streaming layer (SSE iterators + OpenAI-Codex Responses adapter) ──────────
from core.services.cheap_provider_runtime_streaming import (
    _convert_tools_to_responses_format,
    _execute_openai_codex_chat,
    _iter_openai_codex_chat_events,
    _iter_openai_compatible_chat_events,
    _list_openai_codex_models,
)

# ── Selection layer (routing, quota, adaptive priority, failover, state) ──────
from core.services.cheap_provider_runtime_selection import (
    _BACKGROUND_ROTATOR,
    _PUBLIC_PROXY_PROVIDERS,
    _QUOTA_RESET_HOURS,
    _QUOTA_SNAPSHOT_PREFIX,
    _QUOTA_SNAPSHOT_TTL_SECONDS,
    _STATUS_SURFACE_CACHE_KEY,
    _STATUS_SURFACE_TTL_SECONDS,
    _candidate_adaptive_snapshot,
    _candidate_quota_snapshot,
    _configured_cheap_candidates,
    _decode_state_metadata,
    _fallback_after_failure,
    _is_public_proxy,
    _itertools,
    _normalize_probe_text,
    _public_safe_candidates,
    _record_provider_success,
    _register_provider_failure,
    _rolling_average,
    _smoke_quality_score,
    cheap_lane_status_surface,
    execute_cheap_lane_via_pool,
    execute_public_safe_cheap_lane,
    invalidate_cheap_lane_status_cache,
    select_cheap_lane_target,
    select_public_safe_cheap_lane_target,
    smoke_cheap_lane,
    test_provider_target,
)

__all__ = [
    # shared re-exports
    "Any",
    "CHEAP_PROVIDER_DEFAULTS",
    "CheapProviderError",
    "count_cheap_provider_invocations",
    "get_cheap_provider_runtime_state",
    "get_provider_credentials",
    "list_cheap_provider_runtime_states",
    "load_provider_router_registry",
    "provider_has_real_credentials",
    "record_cheap_provider_invocation",
    "record_cost",
    "resolve_provider_router_target",
    "upsert_cheap_provider_runtime_state",
    # adapters
    "deepseek_model_for_thinking_mode",
    "list_provider_models",
    "provider_auth_ready",
    "provider_runtime_defaults",
    "supported_cheap_providers",
    # selection
    "cheap_lane_status_surface",
    "execute_cheap_lane_via_pool",
    "execute_public_safe_cheap_lane",
    "invalidate_cheap_lane_status_cache",
    "select_cheap_lane_target",
    "select_public_safe_cheap_lane_target",
    "smoke_cheap_lane",
    "test_provider_target",
]
