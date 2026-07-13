"""Per-provider visible-lane adapters + auth/probe/readiness helpers.

Split out of ``core.services.visible_model`` (boy-scout, 2026-07-07). Contains
the openai / openai-codex / github-copilot / openai-compat execute+stream
adapters, the GitHub Copilot model-catalog + cooldown helpers, the OpenAI
auth-profile resolution + probe helpers, and ``visible_execution_readiness``.
The Ollama adapter lives in ``visible_model_ollama``. All symbols are
re-exported verbatim from ``core.services.visible_model`` (blast 37).

Import direction: ``visible_model`` imports THIS module at the BOTTOM of its
body (after ``_build_visible_input`` / ``_build_visible_chat_messages_for_github``
are defined) and re-exports these symbols. This module imports those two
prompt-input builders from ``visible_model`` at top — safe because by the time
``visible_model`` reaches its bottom import, its own body has defined them.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterator
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from core.auth.copilot_oauth import get_copilot_oauth_truth
from core.auth.copilot_session import (
    get_copilot_session_token,
    invalidate_session_cache as invalidate_copilot_session_cache,
)
from core.auth.profiles import get_provider_state, list_auth_profiles
from core.services.non_visible_lane_execution import (
    _COPILOT_API_ROOT,
    _extract_github_copilot_text,
    _github_copilot_request_headers,
    _load_github_copilot_token,
    _post_github_copilot_chat_completion,
    fetch_github_copilot_models,
)
from core.runtime.provider_router import resolve_provider_router_target
from core.runtime.settings import load_settings
from core.runtime.provider_router import load_provider_router_registry

from core.services.visible_model_types import (
    VisibleModelDelta,
    VisibleModelRateLimited,
    VisibleModelResult,
    VisibleModelStreamCancelled,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)
from core.services.visible_model_observe import (
    _observe_content_empty_thinking_fallback,
    _observe_visible_provider_error,
    _strip_thinking_delimiters,
)
from core.services.visible_model_sse import (
    _calculate_openai_cost_usd,
    _chat_completion_stream_is_terminal,
    _estimate_tokens,
    _extract_chat_completion_delta,
    _finalize_openai_tool_calls,
    _iter_sse_events,
    _merge_openai_tool_call_deltas,
    _parse_utc,
)
from core.services.visible_model_ollama import _probe_ollama_visible_target
from core.services.visible_model import (
    _build_visible_chat_messages_for_github,
    _build_visible_input,
)

READINESS_PROBE_TTL_SECONDS = 15
_READINESS_PROBE_CACHE: dict[tuple[str, str, str], dict[str, str | bool]] = {}
GITHUB_VISIBLE_COOLDOWN_TTL_MINUTES = 10
_GITHUB_VISIBLE_COOLDOWN_UNTIL: dict[str, datetime] = {}


def _vm():
    """Return the ``visible_model`` facade module.

    Boy-scout split seam (2026-07-07): several patchable helpers
    (``_load_openai_api_key`` / ``_build_visible_input`` / ``_iter_sse_events``
    / ``urllib_request``) are re-exported from the facade, and tests +
    monkeypatches target the facade binding. Resolving them through the facade
    at call time keeps ``monkeypatch.setattr(visible_model, ...)`` effective
    across the module boundary — the same behaviour as before the split, when
    every symbol lived in one module. Pure seam plumbing: no behaviour change.
    """
    from core.services import visible_model as _vm_mod

    return _vm_mod



def _normalize_github_models_model_id(model: str) -> str:
    # Copilot's api.githubcopilot.com accepts flat model IDs verbatim
    # (e.g. "gpt-5.4", "claude-sonnet-4.6", "gemini-3.1-pro-preview").
    # No provider prefix rewriting — that was for the old models.github.ai
    # free tier. Case and whitespace normalization only.
    if not model:
        raise ValueError("Copilot: empty model ID")
    trimmed = model.strip()
    if trimmed.startswith("/"):
        raise ValueError(f"Copilot: invalid model ID with leading slash: {model}")
    return trimmed


def _github_model_matches_requested(*, requested: str, candidate: str) -> bool:
    requested_clean = str(requested or "").strip()
    candidate_clean = str(candidate or "").strip()
    if not requested_clean or not candidate_clean:
        return False

    def _strip_provider_prefix(model_id: str) -> str:
        # "openai/gpt-5-mini" → "gpt-5-mini", so a user-typed flat ID matches
        # the catalog's provider-prefixed form.
        if "/" in model_id and not model_id.startswith("/"):
            return model_id.split("/", 1)[1]
        return model_id

    req_lower = requested_clean.lower().replace(" ", "-")
    cand_lower = candidate_clean.lower()
    if req_lower == cand_lower:
        return True
    return _strip_provider_prefix(req_lower) == _strip_provider_prefix(cand_lower)


def _probe_github_copilot_model(*, profile: str, model: str) -> dict[str, str | bool | None]:
    checked_at = datetime.now(UTC).isoformat()
    try:
        available_models = _vm().fetch_github_copilot_models(profile=profile)
    except Exception:
        available_models = []

    if available_models:
        if any(
            _github_model_matches_requested(requested=model, candidate=item)
            for item in available_models
        ):
            return {
                "provider_reachable": True,
                "live_verified": True,
                "provider_status": "ready",
                "checked_at": checked_at,
                "available_models": available_models,
            }
        return {
            "provider_reachable": True,
            "live_verified": False,
            "provider_status": "model-not-available",
            "checked_at": checked_at,
            "available_models": available_models,
        }

    return {
        "provider_reachable": True,
        "live_verified": False,
        "provider_status": "not-verified",
        "checked_at": checked_at,
        "available_models": available_models,
    }


def _ensure_github_copilot_model_available(*, profile: str, model: str) -> None:
    probe = _probe_github_copilot_model(profile=profile, model=model)
    if str(probe.get("provider_status") or "") != "model-not-available":
        return

    available_models = [
        str(item).strip()
        for item in (probe.get("available_models") or [])
        if str(item).strip()
    ]
    available_preview = ", ".join(available_models[:6])
    detail = (
        f" Available for this auth profile: {available_preview}."
        if available_preview
        else ""
    )
    raise RuntimeError(
        f"GitHub Copilot visible model '{model}' is not available for auth profile '{profile}'."
        f"{detail}"
    )


def _set_github_visible_cooldown(
    profile: str, ttl_minutes: int = GITHUB_VISIBLE_COOLDOWN_TTL_MINUTES
) -> None:
    from datetime import timedelta

    global _GITHUB_VISIBLE_COOLDOWN_UNTIL
    _GITHUB_VISIBLE_COOLDOWN_UNTIL[profile] = datetime.now(UTC) + timedelta(
        minutes=ttl_minutes
    )


def _is_github_visible_cooled_down(profile: str) -> bool:
    global _GITHUB_VISIBLE_COOLDOWN_UNTIL
    cooldown_until = _GITHUB_VISIBLE_COOLDOWN_UNTIL.get(profile)
    if cooldown_until is None:
        return False
    if datetime.now(UTC) >= cooldown_until:
        _GITHUB_VISIBLE_COOLDOWN_UNTIL.pop(profile, None)
        return False
    return True


def _get_github_visible_cooldown_status(profile: str) -> dict[str, object]:
    global _GITHUB_VISIBLE_COOLDOWN_UNTIL
    cooldown_until = _GITHUB_VISIBLE_COOLDOWN_UNTIL.get(profile)
    if cooldown_until is None:
        return {
            "cooled_down": False,
            "cooldown_until": None,
            "seconds_remaining": 0,
        }
    remaining = (cooldown_until - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        _GITHUB_VISIBLE_COOLDOWN_UNTIL.pop(profile, None)
        return {
            "cooled_down": False,
            "cooldown_until": None,
            "seconds_remaining": 0,
        }
    return {
        "cooled_down": True,
        "cooldown_until": cooldown_until.isoformat(),
        "seconds_remaining": int(remaining),
    }


def _stream_openai_compatible_model(
    *,
    provider: str,
    model: str,
    message: str,
    session_id: str | None = None,
    controller=None,
    thinking_mode: str = "think",
) -> Iterator[VisibleModelDelta | VisibleModelStreamDone | VisibleModelToolCalls]:
    """Native SSE streaming for openai-compat providers (deepseek, groq, ...).

    Mirrors _stream_openai_codex_model: bridges the
    _iter_openai_compatible_chat_events generator into the VisibleModel*
    discriminated union the visible-runs pump expects. Yields deltas as
    they arrive — no fake-chunking, real token-by-token UX.

    thinking_mode plumbes for Deepseek så "fast" composer-mode swap'er til
    deepseek-chat (non-thinking compat-alias). Andre openai-compat
    providere ignorerer (de har ikke thinking-mode).
    """
    from core.services.cheap_provider_runtime import (
        _iter_openai_compatible_chat_events,
        deepseek_model_for_thinking_mode,
        provider_runtime_defaults,
    )
    if provider == "deepseek":
        model = deepseek_model_for_thinking_mode(model, thinking_mode)
    # Thinking-mode-modeller (deepseek-v4-flash thinking, deepseek-v4-pro,
    # deepseek-reasoner) kræver at PRIOR assistant turns indeholder
    # reasoning_content. Legacy chat-history rækker uden det vil fejle
    # requesten. Strip assistant-messages uden reasoning_content når vi
    # går til thinking-mode model. Pris: tab af gamle assistant-turns.
    # Værdi: API'et accepterer requesten.
    _is_thinking_model = (
        provider == "deepseek"
        and model in ("deepseek-v4-flash", "deepseek-v4-pro", "deepseek-reasoner")
    )
    # NB: filtreringen anvendes nedenfor på chat_messages efter de er bygget
    from core.tools.simple_tools import get_tool_definitions
    from core.tools.copilot_tool_pruning import select_tools_for_visible

    defaults = provider_runtime_defaults(provider)
    base_url = str(defaults.get("base_url") or "")

    # Auth profile lookup — same logic as _run_openai_compatible_visible.
    try:
        from core.runtime.provider_router import load_provider_router_registry
        _registry = load_provider_router_registry()
        auth_profile = ""
        for _p in _registry.get("providers") or []:
            if str(_p.get("provider") or "") == provider:
                auth_profile = str(_p.get("auth_profile") or "").strip()
                break
        auth_profile = auth_profile or provider
    except Exception:
        auth_profile = provider

    chat_messages = _build_visible_chat_messages_for_github(
        message=message, session_id=session_id, provider=provider, model=model,
    )
    # Legacy assistant-turns uden reasoning_content: Deepseek thinking-mode
    # afviser requesten hvis et felt mangler. Vi STRIP'ede tidligere hele
    # turn'en — det fjernede kontekst og fik Jarvis til at "glemme" prior
    # samtale (Bjørn observerede 7. maj). Bedre: tilføj placeholder-reasoning
    # så API'et accepterer requesten OG indholdet bevares. Verificeret at
    # Deepseek accepterer placeholder og recall stadig virker.
    if _is_thinking_model:
        _LEGACY_REASONING_PLACEHOLDER = (
            "[legacy turn — reasoning trace not preserved before "
            "reasoning_content persistence shipped]"
        )
        chat_messages = [
            (
                m if not (
                    m.get("role") == "assistant"
                    and not str(m.get("reasoning_content") or "").strip()
                )
                else {**m, "reasoning_content": _LEGACY_REASONING_PLACEHOLDER}
            )
            for m in chat_messages
        ]
    tools = select_tools_for_visible(
        get_tool_definitions(), user_message=message, session_id=session_id,
    )

    collected_tool_calls: list[dict] = []

    # Lag 10 Phase 1 (2026-05-12): unconscious modulation of sampling params.
    # Visible-lane only — cheap-lane callers of _iter_openai_compatible_chat_events
    # don't pass these kwargs, so server-side defaults are preserved for them.
    from core.services.unconscious_modulation import compute_unconscious_modulation
    _mod_temp, _mod_top_p = compute_unconscious_modulation(
        base_temperature=None,
        base_top_p=None,
        workspace_id="default",
    )

    try:
        for ev in _iter_openai_compatible_chat_events(
            provider=provider,
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            messages=chat_messages,
            tools=tools or None,
            temperature=_mod_temp,
            top_p=_mod_top_p,
        ):
            if controller is not None and controller.is_cancelled():
                raise VisibleModelStreamCancelled("visible-run-cancelled")
            kind = ev.get("kind")
            if kind == "delta":
                delta = str(ev.get("text") or "")
                if delta:
                    yield VisibleModelDelta(delta=delta)
            elif kind == "tool_call":
                tc = {
                    "id": str(ev.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(ev.get("name") or ""),
                        "arguments": str(ev.get("arguments") or ""),
                    },
                }
                collected_tool_calls.append(tc)
            elif kind == "done":
                if collected_tool_calls:
                    yield VisibleModelToolCalls(tool_calls=collected_tool_calls)
                full_text = str(ev.get("full_text") or "")
                _reasoning = str(ev.get("reasoning_content") or "")
                # I1-heal (port fra ollama-stien linje 1854, 2026-06-30 — DEN ægte
                # cutoff-rod): deepseek-v4-flash/v4-pro/reasoner (thinking) lægger NOGLE
                # GANGE hele svaret i reasoning_content mens content er TOM. reasoning-
                # deltaerne streames til klienten (brugeren SER teksten), men content-
                # accumulatoren forblev tom → text_preview='' → falsk empty_completion →
                # fallback wiper det ægte (streamede) svar. Denne openai-compat-sti (native
                # deepseek) MANGLEDE heal'en ollama-stien har. Nu: tom content + ingen
                # tools + reasoning har indhold → surfacér reasoning som svaret. Fallback,
                # ikke default: uændret når content er til stede.
                if not full_text and not collected_tool_calls and _reasoning.strip():
                    full_text = _strip_thinking_delimiters(_reasoning)
                    _observe_content_empty_thinking_fallback(
                        provider, model, "openai_compat_first_pass", len(_reasoning),
                    )
                # 2026-05-22 (Claude): pull cache_hit/miss from the streaming
                # done-event. cheap_provider_runtime already yields them
                # (search for "cache_hit_tokens" in that file's done-yield),
                # but this handler only read input/output/cost/reasoning —
                # which is why cost.recorded events still showed 0% cache
                # hit even after we plumbed the VisibleModelResult fields.
                yield VisibleModelStreamDone(
                    result=VisibleModelResult(
                        text=full_text,
                        input_tokens=int(ev.get("input_tokens") or _estimate_tokens(message)),
                        output_tokens=int(ev.get("output_tokens") or _estimate_tokens(full_text)),
                        cost_usd=float(ev.get("cost_usd") or 0.0),
                        reasoning_content=str(ev.get("reasoning_content") or ""),
                        cache_hit_tokens=int(ev.get("cache_hit_tokens") or 0),
                        cache_miss_tokens=int(ev.get("cache_miss_tokens") or 0),
                    )
                )
                return
    except VisibleModelStreamCancelled:
        raise
    except Exception as _prov_exc:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        # Stream-cluster: visible-lanens DEFAULT-provider-sti (deepseek/glm/openai-
        # compat) var blind — en 429/4xx/timeout her forsvandt mod visible_runs uden
        # spor i Centralen. Nu synlig (rate-limit vs øvrig fejl). Self-safe, re-raiser.
        try:
            from core.services.central_core import central
            _sc = getattr(_prov_exc, "status_code", None)
            central().observe({
                "cluster": "stream",
                "nerve": "provider_rate_limited" if _sc == 429 else "provider_error",
                "lane": "visible", "provider": str(provider or ""),
                "model": str(model or ""), "status_code": _sc,
                "detail": f"{type(_prov_exc).__name__}: {_prov_exc}"[:200],
            })
        except Exception:
            pass
        raise


def _run_openai_compatible_visible(
    *, provider: str, model: str, message: str, session_id: str | None,
    extra_body: dict | None = None,
) -> tuple[VisibleModelResult, list[dict]]:
    """Shared entry point for openai-compat visible providers.

    Builds Jarvis-identity chat messages, passes tool definitions so the
    model can actually call tools, and returns (result, tool_calls) so
    callers can choose whether to drive an agentic follow-up loop.
    """
    from core.services.cheap_provider_runtime import (
        _execute_openai_compatible_chat,
        provider_runtime_defaults,
    )
    from core.tools.simple_tools import get_tool_definitions

    defaults = provider_runtime_defaults(provider)
    base_url = str(defaults.get("base_url") or "")
    import time as _time
    import sys as _sys
    _t_assembly = _time.monotonic()
    chat_messages = _build_visible_chat_messages_for_github(
        message=message,
        session_id=session_id,
        provider=provider,
        model=model,
    )
    _assembly_ms = int((_time.monotonic() - _t_assembly) * 1000)
    from core.tools.copilot_tool_pruning import select_tools_for_visible
    tools = select_tools_for_visible(
        get_tool_definitions(), user_message=message, session_id=session_id,
    )
    _prompt_chars = sum(len(str(m.get("content", ""))) for m in chat_messages)
    _t_api = _time.monotonic()
    # Lookup auth_profile fra provider_router registry — provider name og
    # auth profile er ikke altid det samme (deepseek bruger fx "default"
    # profil, ikke "deepseek"). Fald tilbage til provider name hvis
    # registry-entry mangler eller er tom.
    try:
        from core.runtime.provider_router import load_provider_router_registry
        _registry = load_provider_router_registry()
        _auth_profile = ""
        for _p in _registry.get("providers") or []:
            if str(_p.get("provider") or "") == provider:
                _auth_profile = str(_p.get("auth_profile") or "").strip()
                break
        _auth_profile = _auth_profile or provider
    except Exception:
        _auth_profile = provider
    # Lag 10 Phase 1 (2026-05-12): unconscious modulation of sampling params.
    # Visible-lane only — cheap-lane callers of _execute_openai_compatible_chat
    # don't pass these kwargs, so server-side defaults are preserved for them.
    from core.services.unconscious_modulation import compute_unconscious_modulation
    _mod_temp, _mod_top_p = compute_unconscious_modulation(
        base_temperature=None,
        base_top_p=None,
        workspace_id="default",
    )
    raw = _execute_openai_compatible_chat(
        provider=provider,
        model=model,
        auth_profile=_auth_profile,
        base_url=base_url,
        messages=chat_messages,
        tools=tools or None,
        temperature=_mod_temp,
        top_p=_mod_top_p,
        extra_body=extra_body,
    )
    _api_ms = int((_time.monotonic() - _t_api) * 1000)
    print(
        f"visible-latency provider={provider} model={model} round=first-pass "
        f"assembly_ms={_assembly_ms} api_ms={_api_ms} "
        f"prompt_chars={_prompt_chars} text_chars={len(str(raw.get('text') or ''))} "
        f"tool_calls={len(list(raw.get('tool_calls') or []))} "
        f"input_tokens={raw.get('input_tokens')} output_tokens={raw.get('output_tokens')}",
        file=_sys.stderr,
        flush=True,
    )
    result = VisibleModelResult(
        text=str(raw.get("text") or ""),
        input_tokens=int(raw.get("input_tokens") or 0),
        output_tokens=int(raw.get("output_tokens") or 0),
        cost_usd=float(raw.get("cost_usd") or 0.0),
        cache_hit_tokens=int(raw.get("cache_hit_tokens") or 0),
        cache_miss_tokens=int(raw.get("cache_miss_tokens") or 0),
    )
    tool_calls = list(raw.get("tool_calls") or [])
    return result, tool_calls


def visible_execution_readiness() -> dict[str, str | bool | None]:
    settings = load_settings()
    provider = settings.visible_model_provider
    model = settings.visible_model_name
    configured_profile = settings.visible_auth_profile or None

    if provider == "phase1-runtime":
        return {
            "provider": provider,
            "model": model,
            "mode": "fallback",
            "auth_ready": True,
            "auth_status": "not-required",
            "auth_profile": configured_profile,
            "provider_reachable": True,
            "live_verified": False,
            "provider_status": "local-fallback",
            "probe_cache": "local",
            "checked_at": None,
        }

    if provider == "openai":
        profile, status = _resolve_openai_profile()
        provider_reachable = False
        live_verified = False
        provider_status = "auth-not-ready"
        probe_cache = "not-run"
        checked_at = None

        if status == "ready" and profile is not None:
            probe = _probe_openai_model(
                profile=profile,
                model=model,
            )
            provider_reachable = bool(probe["provider_reachable"])
            live_verified = bool(probe["live_verified"])
            provider_status = str(probe["provider_status"])
            probe_cache = str(probe["probe_cache"])
            checked_at = str(probe["checked_at"])
        return {
            "provider": provider,
            "model": model,
            "mode": "provider-backed",
            "auth_ready": status == "ready",
            "auth_status": status,
            "auth_profile": profile,
            "provider_reachable": provider_reachable,
            "live_verified": live_verified,
            "provider_status": provider_status,
            "probe_cache": probe_cache,
            "checked_at": checked_at,
        }

    if provider == "openai-codex":
        provider_config = _provider_router_config(provider="openai-codex")
        profile = (
            str(provider_config.get("auth_profile") or "").strip()
            or configured_profile
            or "codex"
        )
        status = _provider_profile_status(provider="openai-codex", profile=profile)
        return {
            "provider": provider,
            "model": model,
            "mode": "provider-backed",
            "auth_ready": status == "ready",
            "auth_status": status,
            "auth_profile": profile,
            "provider_reachable": status == "ready",
            "live_verified": False,
            "provider_status": "not-probed" if status == "ready" else "auth-not-ready",
            "probe_cache": "not-run",
            "checked_at": None,
        }

    if provider == "ollama":
        target = resolve_provider_router_target(lane="visible")
        probe = _probe_ollama_visible_target(
            model=model,
            base_url=str(target.get("base_url") or "").strip(),
        )
        return {
            "provider": provider,
            "model": model,
            "mode": "provider-backed",
            "auth_ready": True,
            "auth_status": "not-required",
            "auth_profile": configured_profile,
            "provider_reachable": bool(probe["provider_reachable"]),
            "live_verified": bool(probe["live_verified"]),
            "provider_status": str(probe["provider_status"]),
            "probe_cache": "fresh",
            "checked_at": str(probe["checked_at"]),
        }

    if provider == "github-copilot":
        profile = configured_profile or "default"
        oauth_truth = _vm().get_copilot_oauth_truth(profile=profile)
        oauth_state = str(oauth_truth.get("oauth_state", ""))
        auth_material_kind = str(oauth_truth.get("auth_material_kind", ""))
        has_real_credentials = bool(oauth_truth.get("has_real_credentials", False))
        exchange_readiness = str(oauth_truth.get("exchange_readiness", ""))

        cooldown_status = _get_github_visible_cooldown_status(profile)
        is_cooled_down = bool(cooldown_status.get("cooled_down"))

        auth_ready = (
            has_real_credentials and oauth_state == "real-stored" and not is_cooled_down
        )

        if is_cooled_down:
            auth_status = "rate-limited-cooldown"
            provider_status = "rate-limited"
            live_verified = False
            checked_at = None
        elif auth_ready:
            auth_status = "ready-github-models"
            probe = _probe_github_copilot_model(profile=profile, model=model)
            provider_status = str(probe["provider_status"])
            live_verified = bool(probe["live_verified"])
            checked_at = str(probe["checked_at"])
        else:
            auth_status = f"not-ready-{exchange_readiness}"
            provider_status = "auth-not-ready"
            live_verified = False
            checked_at = None

        return {
            "provider": provider,
            "model": model,
            "mode": "provider-backed",
            "auth_ready": auth_ready,
            "auth_status": auth_status,
            "auth_profile": profile,
            "auth_note": "requires-models-read-scope" if auth_ready else None,
            "provider_reachable": auth_ready,
            "live_verified": live_verified,
            "provider_status": provider_status,
            "probe_cache": "not-run",
            "checked_at": checked_at,
            "cooldown": cooldown_status,
        }

    return {
        "provider": provider,
        "model": model,
        "mode": "provider-backed",
        "auth_ready": False,
        "auth_status": "unsupported-provider",
        "auth_profile": None,
        "provider_reachable": False,
        "live_verified": False,
        "provider_status": "unsupported-provider",
        "probe_cache": "not-run",
        "checked_at": None,
    }


def _execute_phase1_model(
    *, message: str, provider: str, model: str
) -> VisibleModelResult:
    text = (
        "Jarvis visible lane behandler din besked gennem runtime-graensen. "
        f"Phase 1 modtog: {message}. "
        f"Execution-adapteren kører nu via provider={provider} model={model}. "
        "Reel provider-integration kan senere erstatte denne adapter uden at aendre visible-run kontrakten."
    )
    return VisibleModelResult(
        text=text,
        input_tokens=_estimate_tokens(message),
        output_tokens=_estimate_tokens(text),
        cost_usd=0.0,
    )


def _execute_openai_model(
    *, message: str, model: str, session_id: str | None = None
) -> VisibleModelResult:
    api_key = _load_openai_api_key()
    payload = {
        "model": model,
        "input": _build_visible_input(message, session_id=session_id),
    }
    data = _post_openai_responses(payload=payload, api_key=api_key)
    text = _extract_output_text(data)
    usage = data.get("usage", {})
    input_tokens = int(usage.get("input_tokens", _estimate_tokens(message)))
    output_tokens = int(usage.get("output_tokens", _estimate_tokens(text)))
    return VisibleModelResult(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=_calculate_openai_cost_usd(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
    )


def _stream_openai_codex_model(
    *,
    message: str,
    model: str,
    session_id: str | None = None,
    controller=None,
) -> Iterator[VisibleModelDelta | VisibleModelStreamDone | VisibleModelToolCalls]:
    """Real token-by-token streaming for the openai-codex provider.

    Bridges _iter_openai_codex_chat_events (which uses httpx.stream and
    yields raw SSE deltas as they arrive) into the VisibleModel*
    discriminated union the visible-runs pump expects.

    Now also passes the simple_tools registry as native function tools
    so gpt-5.4 / gpt-5.3-codex can actually call them — without that,
    the visible lane couldn't show "thinking → reading file → ..." for
    Codex models because they had no tools to call.

    Tool-call events from the SSE stream get accumulated (function name
    + streamed argument deltas) and yielded as a single
    VisibleModelToolCalls when each tool call completes.
    """
    from core.services.cheap_provider_runtime import _iter_openai_codex_chat_events
    from core.tools.simple_tools import get_tool_definitions
    from core.tools.copilot_tool_pruning import select_tools_for_visible

    provider_config = _provider_router_config(provider="openai-codex")
    profile = str(provider_config.get("auth_profile") or "").strip() or "codex"
    base_url = str(provider_config.get("base_url") or "").strip()
    prompt = _vm()._build_openai_codex_visible_prompt(
        message=message, model=model, session_id=session_id,
    )
    tools = select_tools_for_visible(
        get_tool_definitions(), user_message=message, session_id=session_id,
    )

    collected_tool_calls: list[dict] = []

    try:
        for ev in _iter_openai_codex_chat_events(
            model=model,
            auth_profile=profile,
            base_url=base_url,
            message=prompt,
            tools=tools or None,
        ):
            if controller is not None and controller.is_cancelled():
                raise VisibleModelStreamCancelled("visible-run-cancelled")
            kind = ev.get("kind")
            if kind == "delta":
                delta = str(ev.get("text") or "")
                if delta:
                    yield VisibleModelDelta(delta=delta)
            elif kind == "tool_call":
                # Build the Chat-Completions-shaped tool_call dict the
                # rest of visible_runs expects (it normalises via
                # _parse_tc_args / _execute_simple_tool_calls).
                tc = {
                    "id": str(ev.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(ev.get("name") or ""),
                        "arguments": str(ev.get("arguments") or ""),
                    },
                }
                collected_tool_calls.append(tc)
            elif kind == "done":
                # If we collected tool calls, surface them BEFORE the
                # stream-done event so visible_runs picks them up while
                # _collected_native_tool_calls is being populated.
                if collected_tool_calls:
                    yield VisibleModelToolCalls(tool_calls=collected_tool_calls)
                full_text = str(ev.get("full_text") or "")
                input_tokens = int(ev.get("input_tokens") or _estimate_tokens(prompt))
                output_tokens = int(ev.get("output_tokens") or _estimate_tokens(full_text))
                yield VisibleModelStreamDone(
                    result=VisibleModelResult(
                        text=full_text,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=0.0,  # Codex via ChatGPT Plus has no per-token billing
                    )
                )
                return
            # tool_call_start events are informational only; the
            # consumer doesn't need a separate "started" signal because
            # working_step is emitted later by visible_runs once the
            # full tool_call lands.
    except VisibleModelStreamCancelled:
        raise
    except Exception as _codex_exc:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        # H4 (spec §2/§4.5): openai-codex-banen kastede UDEN nogen Central-observe
        # (modsat ollama-lanen). En GPT-5.x/codex stream-fejl surfacede men var
        # USYNLIG i Centralen → cut-offs på den bane kunne ikke tælles. Observe nu
        # FØR re-raise. Self-safe: _observe_visible_provider_error sluger selv alt,
        # så den kan aldrig maskere/erstatte den oprindelige fejl.
        _observe_visible_provider_error(
            "openai-codex", model, 0, f"codex stream error: {_codex_exc}")
        raise


def _execute_openai_codex_model(
    *, message: str, model: str, session_id: str | None = None
) -> VisibleModelResult:
    from core.services.cheap_provider_runtime import _execute_openai_codex_chat

    provider_config = _provider_router_config(provider="openai-codex")
    profile = str(provider_config.get("auth_profile") or "").strip() or "codex"
    raw = _execute_openai_codex_chat(
        model=model,
        auth_profile=profile,
        base_url=str(provider_config.get("base_url") or "").strip(),
        message=_vm()._build_openai_codex_visible_prompt(
            message=message,
            model=model,
            session_id=session_id,
        ),
    )
    text = str(raw.get("text") or "")
    return VisibleModelResult(
        text=text,
        input_tokens=int(raw.get("input_tokens") or _estimate_tokens(message)),
        output_tokens=int(raw.get("output_tokens") or _estimate_tokens(text)),
        cost_usd=0.0,
    )


def _build_openai_codex_visible_prompt(
    *, message: str, model: str, session_id: str | None
) -> str:
    messages = _build_visible_chat_messages_for_github(
        message=message,
        session_id=session_id,
        provider="openai-codex",
        model=model,
    )
    parts: list[str] = []
    for item in messages:
        role = str(item.get("role") or "user").strip() or "user"
        content = str(item.get("content") or "").strip()
        if content:
            parts.append(f"{role.upper()}:\n{content}")
    return "\n\n".join(parts).strip() or message


def _execute_github_copilot_visible_model(
    *, message: str, model: str, session_id: str | None = None
) -> VisibleModelResult:
    from core.runtime.settings import load_settings
    from urllib import error as urllib_error

    settings = load_settings()
    profile = settings.visible_auth_profile or "default"

    if _is_github_visible_cooled_down(profile):
        raise VisibleModelRateLimited(
            "GitHub Copilot visible lane is temporarily rate-limited. Please try again in a few minutes, or switch to a local lane."
        )

    _facade = _vm()
    _facade._load_github_copilot_token(profile=profile)

    normalized_model = _normalize_github_models_model_id(model)
    _ensure_github_copilot_model_available(profile=profile, model=normalized_model)

    messages = _facade._build_visible_chat_messages_for_github(
        message=message,
        session_id=session_id,
    )

    from core.tools.simple_tools import get_tool_definitions
    from core.tools.copilot_tool_pruning import select_tools_for_copilot
    tools = select_tools_for_copilot(
        get_tool_definitions(),
        user_message=message,
        session_id=session_id,
    )

    payload: dict[str, object] = {
        "model": normalized_model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
    try:
        data = _facade._post_github_copilot_chat_completion(
            payload=payload,
            profile=profile,
        )
    except RuntimeError as exc:
        error_msg = str(exc)
        if "HTTP 429" in error_msg:
            _set_github_visible_cooldown(profile)
            raise VisibleModelRateLimited(
                "GitHub Copilot visible lane is temporarily rate-limited. Please try again in a few minutes, or switch to a local lane."
            )
        if "HTTP" in error_msg:
            code = (
                error_msg.split("HTTP ")[1].split(":")[0]
                if "HTTP " in error_msg
                else "unknown"
            )
            raise VisibleModelRateLimited(
                f"Backend returned HTTP {code}. This may be temporary. Please try again."
            )
        raise
    text = _extract_github_copilot_text(data)
    usage = data.get("usage", {})
    input_tokens = int(
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or _estimate_tokens(message)
    )
    output_tokens = int(
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or _estimate_tokens(text)
    )
    return VisibleModelResult(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=0.0,
    )


def _stream_openai_model(
    *, message: str, model: str, session_id: str | None = None, controller=None
) -> Iterator[VisibleModelDelta | VisibleModelStreamDone]:
    _facade = _vm()
    api_key = _facade._load_openai_api_key()
    payload = {
        "model": model,
        "stream": True,
        "input": _facade._build_visible_input(message, session_id=session_id),
    }
    req = _facade.urllib_request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    parts: list[str] = []
    usage: dict = {}

    try:
        with _facade.urllib_request.urlopen(req, timeout=60) as response:
            if controller is not None:
                controller.attach_stream(response)
            for event in _facade._iter_sse_events(response, provider="openai", model=model):
                event_type = str(event.get("type", ""))
                if event_type == "response.output_text.delta":
                    delta = str(event.get("delta", ""))
                    if not delta:
                        continue
                    parts.append(delta)
                    yield VisibleModelDelta(delta=delta)
                elif event_type == "response.completed":
                    usage = dict(event.get("response", {}).get("usage", {}))
                elif event_type == "error":
                    raise RuntimeError(
                        f"OpenAI visible streaming failed: {event.get('message', 'unknown-error')}"
                    )
    except Exception as _resp_exc:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        # H4 (spec §2/§4.5): openai-responses-banen (GPT-5.x via /v1/responses)
        # kastede UDEN nogen Central-observe (modsat ollama-lanen). Stream-fejl
        # surfacede men var USYNLIG i Centralen. Observe nu FØR re-raise.
        # Self-safe: helper'en sluger selv alt → kan ikke maskere fejlen.
        _observe_visible_provider_error(
            "openai", model, 0, f"responses stream error: {_resp_exc}")
        raise
    finally:
        if controller is not None:
            controller.clear_stream()

    text = "".join(parts).strip()
    if not text:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        raise RuntimeError("OpenAI visible execution returned no streamed output_text")

    input_tokens = int(usage.get("input_tokens", _estimate_tokens(message)))
    output_tokens = int(usage.get("output_tokens", _estimate_tokens(text)))
    yield VisibleModelStreamDone(
        result=VisibleModelResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_calculate_openai_cost_usd(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
        )
    )


def _resolve_copilot_profile(preferred: str) -> str:
    """Find profilen der faktisk HAR github-copilot-creds.

    2026-06-13: copilot-auth (VSCode-session-impersonation) gemmes typisk under
    en EGEN profil ("copilot"), ikke den globale visible_auth_profile ("default").
    Når owner valgte Copilot i composeren looked vi i "default" → missing-profile
    → tavst run-fejl, selvom token var gyldigt. Self-healing: brug preferred hvis
    den har copilot-state; ellers find en profil der har."""
    try:
        from core.auth.profiles import get_provider_state, list_auth_profiles
        if get_provider_state(profile=preferred, provider="github-copilot") is not None:
            return preferred
        for p in ["copilot", *list_auth_profiles()]:
            if p and get_provider_state(profile=p, provider="github-copilot") is not None:
                return p
    except Exception:
        pass
    return preferred


def _stream_github_copilot_model(
    *, message: str, model: str, session_id: str | None = None, controller=None
) -> Iterator[VisibleModelDelta | VisibleModelToolCalls | VisibleModelStreamDone]:
    settings = load_settings()
    profile = _resolve_copilot_profile(settings.visible_auth_profile or "default")

    if _is_github_visible_cooled_down(profile):
        raise VisibleModelRateLimited(
            "GitHub Copilot visible lane is temporarily rate-limited. Please try again in a few minutes, or switch to a local lane."
        )

    _facade = _vm()
    _facade._load_github_copilot_token(profile=profile)
    session_token = _facade.get_copilot_session_token(profile=profile)
    normalized_model = _normalize_github_models_model_id(model)
    _ensure_github_copilot_model_available(profile=profile, model=normalized_model)

    from core.tools.simple_tools import get_tool_definitions
    from core.tools.copilot_tool_pruning import select_tools_for_copilot
    tools = select_tools_for_copilot(
        get_tool_definitions(),
        user_message=message,
        session_id=session_id,
    )

    payload: dict[str, object] = {
        "model": normalized_model,
        "messages": _facade._build_visible_chat_messages_for_github(
            message=message,
            session_id=session_id,
        ),
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
    req = _facade.urllib_request.Request(
        f"{_COPILOT_API_ROOT}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=_github_copilot_request_headers(session_token, accept="text/event-stream"),
        method="POST",
    )

    parts: list[str] = []
    tool_call_accumulator: dict[int, dict] = {}

    try:
        with _facade.urllib_request.urlopen(req, timeout=180) as response:
            if controller is not None:
                controller.attach_stream(response)
            for event in _facade._iter_sse_events(response, provider="github-copilot", model=model):
                delta = _extract_chat_completion_delta(event)
                if delta:
                    parts.append(delta)
                    yield VisibleModelDelta(delta=delta)
                _merge_openai_tool_call_deltas(tool_call_accumulator, event)
                if _chat_completion_stream_is_terminal(event):
                    break
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        error_msg = f"GitHub Copilot API error: HTTP {exc.code}: {body}"
        if exc.code == 429:
            _set_github_visible_cooldown(profile)
            raise VisibleModelRateLimited(
                "GitHub Copilot visible lane is temporarily rate-limited. Please try again in a few minutes, or switch to a local lane."
            )
        if exc.code in (401, 403):
            invalidate_copilot_session_cache(profile=profile)
        raise RuntimeError(error_msg)
    except Exception:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        raise
    finally:
        if controller is not None:
            controller.clear_stream()

    collected_tool_calls = [
        tool_call_accumulator[idx] for idx in sorted(tool_call_accumulator.keys())
    ]
    collected_tool_calls = _finalize_openai_tool_calls(collected_tool_calls)
    if collected_tool_calls:
        yield VisibleModelToolCalls(tool_calls=collected_tool_calls)

    text = "".join(parts).strip()
    if not text and not collected_tool_calls:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        raise RuntimeError("GitHub Copilot visible execution returned no streamed text")

    yield VisibleModelStreamDone(
        result=VisibleModelResult(
            text=text,
            input_tokens=_estimate_tokens(message),
            output_tokens=_estimate_tokens(text),
            cost_usd=0.0,
        )
    )


def _load_openai_api_key() -> str:
    profile, status = _resolve_openai_profile()
    if profile is None:
        raise RuntimeError(f"OpenAI visible execution not ready: {status}")

    return _load_openai_api_key_for_profile(profile)


def _load_openai_api_key_for_profile(profile: str) -> str:
    state = get_provider_state(profile=profile, provider="openai")
    credentials_path = Path(str(state.get("credentials_path", "")))
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    api_key = str(credentials.get("api_key") or credentials.get("access_token") or "")
    if api_key:
        return api_key
    raise RuntimeError("OpenAI visible execution not ready: missing-credentials")


def _resolve_openai_profile() -> tuple[str | None, str]:
    settings = load_settings()
    configured_profile = settings.visible_auth_profile.strip()
    if configured_profile:
        return _openai_profile_status(configured_profile)

    profiles = ["default", *[item["profile"] for item in list_auth_profiles()]]
    seen: set[str] = set()
    for profile in profiles:
        if profile in seen:
            continue
        seen.add(profile)
        resolved_profile, status = _openai_profile_status(profile)
        if status == "ready":
            return resolved_profile, status
    return None, "missing-credentials"


def _openai_profile_status(profile: str) -> tuple[str | None, str]:
    state = get_provider_state(profile=profile, provider="openai")
    if state is None:
        return profile, "missing-profile"
    if state.get("status") != "active":
        return profile, "inactive-profile"

    credentials_path = Path(str(state.get("credentials_path", "")))
    if not credentials_path.exists():
        return profile, "missing-credentials"

    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    api_key = str(credentials.get("api_key") or credentials.get("access_token") or "")
    if not api_key:
        return profile, "missing-credentials"
    return profile, "ready"


def _provider_profile_status(*, provider: str, profile: str) -> str:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return "missing-profile"
    if state.get("status") != "active":
        return "inactive-profile"
    credentials_path = Path(str(state.get("credentials_path", "")))
    if not credentials_path.exists():
        return "missing-credentials"
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    api_key = str(credentials.get("api_key") or credentials.get("access_token") or "")
    if not api_key:
        return "missing-credentials"
    return "ready"


def _provider_router_config(*, provider: str) -> dict[str, object]:
    registry = load_provider_router_registry()
    for item in registry.get("providers") or []:
        if not bool(item.get("enabled", True)):
            continue
        if str(item.get("provider") or "").strip() == provider:
            return dict(item)
    return {}


def _post_openai_responses(
    *, payload: dict, api_key: str, base_url: str = "https://api.openai.com/v1"
) -> dict:
    root = (base_url or "https://api.openai.com/v1").rstrip("/")
    req = urllib_request.Request(
        f"{root}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _probe_openai_model(*, profile: str, model: str) -> dict[str, str | bool]:
    cache_key = ("openai", profile, model)
    now = datetime.now(UTC)
    cached = _READINESS_PROBE_CACHE.get(cache_key)
    if cached:
        expires_at = _parse_utc(cached["expires_at"])
        if expires_at > now:
            return {
                "provider_reachable": bool(cached["provider_reachable"]),
                "live_verified": bool(cached["live_verified"]),
                "provider_status": str(cached["provider_status"]),
                "probe_cache": "cached",
                "checked_at": str(cached["checked_at"]),
            }

    api_key = _load_openai_api_key_for_profile(profile)
    model_ref = urllib_parse.quote(model, safe="")
    req = urllib_request.Request(
        f"https://api.openai.com/v1/models/{model_ref}",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            response.read()
        result = {
            "provider_reachable": True,
            "live_verified": True,
            "provider_status": "reachable",
        }
    except urllib_error.HTTPError as exc:
        if exc.code == 404:
            result = {
                "provider_reachable": True,
                "live_verified": False,
                "provider_status": "model-not-found",
            }
        elif exc.code in {401, 403}:
            result = {
                "provider_reachable": False,
                "live_verified": False,
                "provider_status": "auth-rejected",
            }
        else:
            result = {
                "provider_reachable": False,
                "live_verified": False,
                "provider_status": f"http-{exc.code}",
            }
    except urllib_error.URLError:
        result = {
            "provider_reachable": False,
            "live_verified": False,
            "provider_status": "unreachable",
        }

    checked_at = now.isoformat()
    _READINESS_PROBE_CACHE[cache_key] = {
        **result,
        "checked_at": checked_at,
        "expires_at": (
            now + timedelta(seconds=READINESS_PROBE_TTL_SECONDS)
        ).isoformat(),
    }
    return {
        **result,
        "probe_cache": "fresh",
        "checked_at": checked_at,
    }


def _extract_output_text(data: dict) -> str:
    parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(str(content.get("text", "")))
    text = "".join(parts).strip()
    if not text:
        raise RuntimeError("OpenAI visible execution returned no output_text")
    return text
