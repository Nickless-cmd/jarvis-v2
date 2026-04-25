from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal
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
from core.services.cheap_provider_runtime import (
    list_provider_models as list_live_provider_models,
    supported_cheap_providers,
)
from core.services.prompt_contract import (
    build_visible_chat_prompt_assembly,
)
from core.memory.private_retained_memory_projection import (
    build_private_retained_memory_projection,
)
from core.services.ollama_visible_prompt import (
    serialize_ollama_visible_prompt,
)
from core.runtime.provider_router import resolve_provider_router_target
from core.runtime.db import (
    get_private_temporal_promotion_signal,
    get_private_retained_memory_record,
    get_private_self_model,
    recent_private_growth_notes,
    recent_private_inner_notes,
    recent_private_retained_memory_records,
    recent_capability_invocations,
    recent_visible_runs,
    visible_session_continuity,
)
from core.runtime.settings import load_settings
from core.tools.workspace_capabilities import load_workspace_capabilities
from core.runtime.provider_router import load_provider_router_registry

READINESS_PROBE_TTL_SECONDS = 15
_READINESS_PROBE_CACHE: dict[tuple[str, str, str], dict[str, str | bool]] = {}
GITHUB_VISIBLE_COOLDOWN_TTL_MINUTES = 10
_GITHUB_VISIBLE_COOLDOWN_UNTIL: dict[str, datetime] = {}
OPENAI_TEXT_PRICING_PER_1M_TOKENS: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-5": (Decimal("1.25"), Decimal("10.00")),
    "gpt-5-mini": (Decimal("0.25"), Decimal("2.00")),
    "gpt-5-nano": (Decimal("0.05"), Decimal("0.40")),
}


@dataclass(slots=True)
class VisibleModelResult:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


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
    pass


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
        available_models = fetch_github_copilot_models(profile=profile)
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


def _configured_provider_models(provider: str) -> list[str]:
    normalized_provider = str(provider or "").strip()
    if not normalized_provider:
        return []

    registry = load_provider_router_registry()
    models: list[str] = []
    seen: set[str] = set()
    for item in registry.get("models") or []:
        if not bool(item.get("enabled", True)):
            continue
        if str(item.get("provider") or "").strip() != normalized_provider:
            continue
        model = str(item.get("model") or "").strip()
        if not model or model in seen:
            continue
        seen.add(model)
        models.append(model)
    models.sort()
    return models


def available_provider_models(*, provider: str, auth_profile: str = "") -> dict[str, object]:
    normalized_provider = str(provider or "").strip()
    normalized_profile = str(auth_profile or "").strip()
    cheap_providers = {
        str(item.get("provider") or "").strip()
        for item in supported_cheap_providers()
    }
    if not normalized_provider:
        return {
            "provider": "",
            "auth_profile": normalized_profile,
            "source": "missing-provider",
            "status": "missing-provider",
            "models": [],
        }

    if normalized_provider == "ollama":
        data = available_ollama_models_for_visible_target()
        return {
            "provider": normalized_provider,
            "auth_profile": "",
            "source": "provider-live",
            "status": str(data.get("status") or "unknown"),
            "base_url": str(data.get("base_url") or ""),
            "models": [
                {
                    "id": str(item.get("name") or "").strip(),
                    "label": str(item.get("name") or "").strip(),
                    "family": str(item.get("family") or "").strip(),
                    "parameter_size": str(item.get("parameter_size") or "").strip(),
                    "quantization_level": str(
                        item.get("quantization_level") or ""
                    ).strip(),
                }
                for item in data.get("models", [])
                if isinstance(item, dict) and str(item.get("name") or "").strip()
            ],
        }

    if normalized_provider == "github-copilot":
        profile = normalized_profile or load_settings().visible_auth_profile or "default"
        oauth_truth = get_copilot_oauth_truth(profile=profile)
        has_real_credentials = bool(oauth_truth.get("has_real_credentials", False))
        oauth_state = str(oauth_truth.get("oauth_state") or "")

        if not has_real_credentials or oauth_state != "real-stored":
            return {
                "provider": normalized_provider,
                "auth_profile": profile,
                "source": "provider-live",
                "status": "auth-not-ready",
                "models": [],
            }

        models = fetch_github_copilot_models(profile=profile)
        return {
            "provider": normalized_provider,
            "auth_profile": profile,
            "source": "provider-live",
            "status": "ready" if models else "unavailable",
            "models": [
                {
                    "id": item,
                    "label": item,
                }
                for item in models
                if str(item).strip()
            ],
        }

    if normalized_provider in cheap_providers:
        return list_live_provider_models(
            provider=normalized_provider,
            auth_profile=normalized_profile,
        )

    configured_models = _configured_provider_models(normalized_provider)
    return {
        "provider": normalized_provider,
        "auth_profile": normalized_profile,
        "source": "configured-targets",
        "status": "configured-only" if configured_models else "unconfigured",
        "models": [
            {
                "id": item,
                "label": item,
            }
            for item in configured_models
        ],
    }


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


def execute_visible_model(
    *, message: str, provider: str, model: str, session_id: str | None = None
) -> VisibleModelResult:
    if provider == "openai":
        return _execute_openai_model(
            message=message, model=model, session_id=session_id
        )
    if provider == "ollama":
        return _execute_ollama_model(
            message=message, model=model, session_id=session_id
        )
    if provider == "github-copilot":
        return _execute_github_copilot_visible_model(
            message=message, model=model, session_id=session_id
        )
    if provider == "phase1-runtime":
        return _execute_phase1_model(message=message, provider=provider, model=model)

    # Fallback: openai-chat-compatible providers (groq, nvidia-nim, openrouter,
    # mistral, sambanova, opencode) — dispatch via cheap_provider_runtime's
    # _execute_openai_compatible_chat so visible lane can use them too.
    try:
        from core.services.cheap_provider_runtime import (
            _OPENAI_COMPATIBLE_PROVIDERS,
            _execute_openai_compatible_chat,
            provider_runtime_defaults,
        )
        if provider in _OPENAI_COMPATIBLE_PROVIDERS:
            result, _tool_calls = _run_openai_compatible_visible(
                provider=provider,
                model=model,
                message=message,
                session_id=session_id,
            )
            return result
    except Exception as exc:
        raise ValueError(
            f"Visible model dispatch failed for {provider}/{model}: {exc}"
        ) from exc

    raise ValueError(f"Unsupported visible model provider: {provider}")


def stream_visible_model(
    *,
    message: str,
    provider: str,
    model: str,
    session_id: str | None = None,
    controller=None,
    thinking_mode: str = "think",
) -> Iterator[VisibleModelDelta | VisibleModelStreamDone]:
    if provider == "openai":
        yield from _stream_openai_model(
            message=message,
            model=model,
            session_id=session_id,
            controller=controller,
        )
        return
    if provider == "ollama":
        yield from _stream_ollama_model(
            message=message,
            model=model,
            session_id=session_id,
            controller=controller,
            thinking_mode=thinking_mode,
        )
        return
    if provider == "github-copilot":
        yield from _stream_github_copilot_model(
            message=message,
            model=model,
            session_id=session_id,
            controller=controller,
        )
        return

    # openai-compat providers (opencode, groq, openrouter, nvidia-nim, mistral,
    # sambanova) — non-streaming call with tools, then yield chunks + tool_calls
    # so the agentic loop can pick them up and run the follow-up round.
    from core.services.cheap_provider_runtime import _OPENAI_COMPATIBLE_PROVIDERS
    if provider in _OPENAI_COMPATIBLE_PROVIDERS:
        result, tool_calls = _run_openai_compatible_visible(
            provider=provider,
            model=model,
            message=message,
            session_id=session_id,
        )
        for chunk in _chunk_text(result.text):
            yield VisibleModelDelta(delta=chunk)
        if tool_calls:
            yield VisibleModelToolCalls(tool_calls=tool_calls)
        yield VisibleModelStreamDone(result=result)
        return

    result = execute_visible_model(
        message=message,
        provider=provider,
        model=model,
        session_id=session_id,
    )
    for chunk in _chunk_text(result.text):
        yield VisibleModelDelta(delta=chunk)
    yield VisibleModelStreamDone(result=result)


def _run_openai_compatible_visible(
    *, provider: str, model: str, message: str, session_id: str | None,
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
    tools = get_tool_definitions()
    _prompt_chars = sum(len(str(m.get("content", ""))) for m in chat_messages)
    _t_api = _time.monotonic()
    raw = _execute_openai_compatible_chat(
        provider=provider,
        model=model,
        auth_profile=provider,
        base_url=base_url,
        messages=chat_messages,
        tools=tools or None,
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
        oauth_truth = get_copilot_oauth_truth(profile=profile)
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


def available_ollama_models_for_visible_target() -> dict[str, object]:
    visible_target = resolve_provider_router_target(lane="visible")
    local_target = resolve_provider_router_target(lane="local")
    target = (
        visible_target
        if str(visible_target.get("provider") or "").strip() == "ollama"
        else local_target
    )
    base_url = str(target.get("base_url") or "").strip() or "http://127.0.0.1:11434"
    checked_at = datetime.now(UTC).isoformat()
    req = urllib_request.Request(f"{base_url.rstrip('/')}/api/tags", method="GET")
    try:
        with urllib_request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = [
            {
                "name": str(item.get("name") or "").strip(),
                "family": str(item.get("details", {}).get("family") or "").strip(),
                "parameter_size": str(
                    item.get("details", {}).get("parameter_size") or ""
                ).strip(),
                "quantization_level": str(
                    item.get("details", {}).get("quantization_level") or ""
                ).strip(),
            }
            for item in data.get("models", [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        return {
            "active": True,
            "provider": "ollama",
            "base_url": base_url,
            "status": "ready",
            "checked_at": checked_at,
            "models": models,
        }
    except urllib_error.HTTPError as exc:
        return {
            "active": True,
            "provider": "ollama",
            "base_url": base_url,
            "status": f"http-{exc.code}",
            "checked_at": checked_at,
            "models": [],
        }
    except urllib_error.URLError:
        return {
            "active": True,
            "provider": "ollama",
            "base_url": base_url,
            "status": "unreachable",
            "checked_at": checked_at,
            "models": [],
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


def _execute_ollama_model(
    *, message: str, model: str, session_id: str | None = None
) -> VisibleModelResult:
    from core.services.ollama_visible_prompt import (
        serialize_ollama_chat_messages,
    )
    from core.tools.simple_tools import get_tool_definitions

    target = resolve_provider_router_target(lane="visible")
    base_url = str(target.get("base_url") or "").strip() or "http://127.0.0.1:11434"

    visible_input = _build_visible_input(message, session_id=session_id)
    messages = serialize_ollama_chat_messages(visible_input)
    tools = get_tool_definitions()

    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))

    msg = data.get("message") or {}
    text = str(msg.get("content") or "").strip()
    if not text:
        raise RuntimeError("Ollama visible execution returned no response")

    prompt_estimate = sum(len(str(m.get("content", ""))) for m in messages) // 4
    prompt_eval_count = int(data.get("prompt_eval_count") or prompt_estimate)
    eval_count = int(data.get("eval_count") or _estimate_tokens(text))
    return VisibleModelResult(
        text=text,
        input_tokens=prompt_eval_count,
        output_tokens=eval_count,
        cost_usd=0.0,
    )


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

    _load_github_copilot_token(profile=profile)

    normalized_model = _normalize_github_models_model_id(model)
    _ensure_github_copilot_model_available(profile=profile, model=normalized_model)

    messages = _build_visible_chat_messages_for_github(
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
        data = _post_github_copilot_chat_completion(
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
    api_key = _load_openai_api_key()
    payload = {
        "model": model,
        "stream": True,
        "input": _build_visible_input(message, session_id=session_id),
    }
    req = urllib_request.Request(
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
        with urllib_request.urlopen(req, timeout=60) as response:
            if controller is not None:
                controller.attach_stream(response)
            for event in _iter_sse_events(response):
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
    except Exception:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
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


def _apply_thinking_mode(payload: dict, thinking_mode: str) -> None:
    """Translate UI thinking-mode label to ollama-chat payload keys.

    Models like deepseek-v4-flash expose 3 reasoning modes via the chat API:
      - 'fast' → think=False (intuitive, no <thinking> output)
      - 'think' → default (omitted; model decides) — balanced
      - 'deep' → reasoning_effort='high' (max reasoning effort)

    For models that ignore these keys (older Llama, Qwen non-reasoning)
    Ollama silently drops them, so it's safe to always send.
    """
    mode = (thinking_mode or "think").strip().lower()
    if mode == "fast":
        payload["think"] = False
    elif mode == "deep":
        payload["reasoning_effort"] = "high"
    # 'think' (default) → don't add anything; let model use its own default


def _stream_ollama_model(
    *,
    message: str,
    model: str,
    session_id: str | None = None,
    controller=None,
    thinking_mode: str = "think",
) -> Iterator[VisibleModelDelta | VisibleModelToolCalls | VisibleModelStreamDone]:
    from core.services.ollama_visible_prompt import (
        serialize_ollama_chat_messages,
    )
    from core.tools.simple_tools import get_tool_definitions

    target = resolve_provider_router_target(lane="visible")
    base_url = str(target.get("base_url") or "").strip() or "http://127.0.0.1:11434"

    visible_input = _build_visible_input(message, session_id=session_id)
    messages = serialize_ollama_chat_messages(visible_input)
    tools = get_tool_definitions()

    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    _apply_thinking_mode(payload, thinking_mode)
    if tools:
        payload["tools"] = tools

    prompt_estimate = sum(len(str(m.get("content", ""))) for m in messages) // 4

    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    parts: list[str] = []
    terminal_response = ""
    prompt_eval_count = prompt_estimate
    eval_count = 0
    collected_tool_calls: list[dict] = []

    try:
        with urllib_request.urlopen(req, timeout=180) as response:
            if controller is not None:
                controller.attach_stream(response)
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                event = json.loads(line)
                msg = event.get("message") or {}

                delta = str(msg.get("content") or "")
                if delta:
                    terminal_response = delta
                    parts.append(delta)
                    yield VisibleModelDelta(delta=delta)

                tool_calls = msg.get("tool_calls") or []
                if tool_calls:
                    collected_tool_calls.extend(tool_calls)

                if event.get("done"):
                    if not parts and delta:
                        terminal_response = delta
                    prompt_eval_count = int(
                        event.get("prompt_eval_count") or prompt_eval_count
                    )
                    eval_count = int(event.get("eval_count") or eval_count)
                    break
    except Exception:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        raise
    finally:
        if controller is not None:
            controller.clear_stream()

    text = "".join(parts).strip()
    if not text:
        text = terminal_response.strip()

    if collected_tool_calls:
        yield VisibleModelToolCalls(tool_calls=collected_tool_calls)

    if not text and not collected_tool_calls:
        if controller is not None and controller.is_cancelled():
            raise VisibleModelStreamCancelled("visible-run-cancelled")
        raise RuntimeError("Ollama visible execution returned no streamed response")

    yield VisibleModelStreamDone(
        result=VisibleModelResult(
            text=text or "[tool calls only]",
            input_tokens=prompt_eval_count,
            output_tokens=eval_count or _estimate_tokens(text),
            cost_usd=0.0,
        )
    )


def _stream_github_copilot_model(
    *, message: str, model: str, session_id: str | None = None, controller=None
) -> Iterator[VisibleModelDelta | VisibleModelToolCalls | VisibleModelStreamDone]:
    settings = load_settings()
    profile = settings.visible_auth_profile or "default"

    if _is_github_visible_cooled_down(profile):
        raise VisibleModelRateLimited(
            "GitHub Copilot visible lane is temporarily rate-limited. Please try again in a few minutes, or switch to a local lane."
        )

    _load_github_copilot_token(profile=profile)
    session_token = get_copilot_session_token(profile=profile)
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
        "messages": _build_visible_chat_messages_for_github(
            message=message,
            session_id=session_id,
        ),
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
    req = urllib_request.Request(
        f"{_COPILOT_API_ROOT}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=_github_copilot_request_headers(session_token, accept="text/event-stream"),
        method="POST",
    )

    parts: list[str] = []
    tool_call_accumulator: dict[int, dict] = {}

    try:
        with urllib_request.urlopen(req, timeout=180) as response:
            if controller is not None:
                controller.attach_stream(response)
            for event in _iter_sse_events(response):
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


def _post_openai_responses(*, payload: dict, api_key: str) -> dict:
    req = urllib_request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _probe_ollama_visible_target(*, model: str, base_url: str) -> dict[str, str | bool]:
    checked_at = datetime.now(UTC).isoformat()
    root = (base_url or "http://127.0.0.1:11434").rstrip("/")
    req = urllib_request.Request(f"{root}/api/tags", method="GET")
    try:
        with urllib_request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        names = {
            str(item.get("name") or "").strip()
            for item in data.get("models", [])
            if isinstance(item, dict)
        }
        if model and model not in names:
            return {
                "provider_reachable": True,
                "live_verified": False,
                "provider_status": "model-not-found",
                "checked_at": checked_at,
            }
        return {
            "provider_reachable": True,
            "live_verified": True,
            "provider_status": "ready",
            "checked_at": checked_at,
        }
    except urllib_error.HTTPError as exc:
        return {
            "provider_reachable": False,
            "live_verified": False,
            "provider_status": f"http-{exc.code}",
            "checked_at": checked_at,
        }
    except urllib_error.URLError:
        return {
            "provider_reachable": False,
            "live_verified": False,
            "provider_status": "unreachable",
            "checked_at": checked_at,
        }


def _build_ollama_prompt(message: str, *, model: str, session_id: str | None) -> str:
    return serialize_ollama_visible_prompt(
        _build_visible_input(message, session_id=session_id)
    )


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


def _build_visible_input(
    message: str,
    *,
    session_id: str | None,
    provider: str = "",
    model: str = "",
) -> list[dict]:
    # Resolve actual provider/model from router if not supplied
    actual_provider = provider
    actual_model = model
    if not actual_provider or not actual_model:
        target = resolve_provider_router_target(lane="visible")
        actual_provider = actual_provider or str(target.get("provider", ""))
        actual_model = actual_model or str(target.get("model", ""))
    assembly = _build_visible_prompt_assembly(
        provider=actual_provider,
        model=actual_model,
        user_message=message,
        session_id=session_id,
    )
    instruction = assembly.text
    if not instruction:
        return [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": message}],
            }
        ]

    items: list[dict] = [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": instruction}],
        },
    ]

    # Inject structured transcript as proper multi-turn messages
    # so the model sees actual conversation history, not flat text.
    if assembly.transcript_messages:
        for tmsg in assembly.transcript_messages:
            role = tmsg.get("role", "user")
            content = tmsg.get("content", "")
            if content:
                items.append({
                    "role": role,
                    "content": [{"type": "input_text", "text": content}],
                })

    # The user message is persisted to DB before the run starts, so it is
    # already the last entry in transcript_messages. Only append explicitly
    # when the transcript is empty or ends with an assistant turn.
    _last_tm = assembly.transcript_messages[-1] if assembly.transcript_messages else None
    if not (_last_tm and _last_tm.get("role") == "user"):
        items.append({
            "role": "user",
            "content": [{"type": "input_text", "text": message}],
        })

    return items


def _build_visible_chat_messages_for_github(
    message: str,
    *,
    session_id: str | None,
    provider: str = "github-copilot",
    model: str = "",
) -> list[dict[str, str]]:
    """Build OpenAI chat-completions messages for the visible lane.

    Despite the historical name, this helper now serves all OpenAI-compat
    visible providers — github-copilot, opencode, groq, openrouter, mistral,
    nvidia-nim, sambanova. Pass the actual ``provider`` so the prompt
    assembly can reflect it in model-awareness lines and provider-specific
    tweaks (e.g. compact mode for ollama, which is dispatched separately).
    """
    assembly = _build_visible_prompt_assembly(
        provider=provider,
        model=model,
        user_message=message,
        session_id=session_id,
    )
    instruction = assembly.text
    if not instruction:
        return [
            {"role": "user", "content": message},
        ]
    messages: list[dict[str, str]] = [
        {"role": "system", "content": instruction},
    ]
    # Inject structured transcript as proper multi-turn messages
    if assembly.transcript_messages:
        for tmsg in assembly.transcript_messages:
            role = tmsg.get("role", "user")
            content = tmsg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


def _visible_system_instruction_for_provider(
    *, provider: str, model: str, user_message: str, session_id: str | None
) -> str | None:
    assembly = build_visible_chat_prompt_assembly(
        provider=provider,
        model=model,
        user_message=user_message,
        session_id=session_id,
        runtime_self_report_context={
            "visible_execution_readiness": visible_execution_readiness(),
        },
    )
    return assembly.text or None


def _build_visible_prompt_assembly(
    *, provider: str, model: str, user_message: str, session_id: str | None
):
    """Return the full PromptAssembly (including structured transcript)."""
    return build_visible_chat_prompt_assembly(
        provider=provider,
        model=model,
        user_message=user_message,
        session_id=session_id,
        runtime_self_report_context={
            "visible_execution_readiness": visible_execution_readiness(),
        },
    )


def _visible_session_continuity_instruction() -> str | None:
    continuity = visible_session_continuity()
    if not continuity["active"]:
        return None

    parts = [
        f"latest_status={continuity.get('latest_status') or 'unknown'}",
        f"latest_finished_at={continuity.get('latest_finished_at') or 'unknown'}",
    ]
    if continuity.get("latest_run_id"):
        parts.append(f"latest_run_id={continuity['latest_run_id']}")
    if continuity.get("latest_capability_id"):
        parts.append(f"latest_capability={continuity['latest_capability_id']}")
    if continuity.get("latest_text_preview"):
        parts.append(f"latest_preview={continuity['latest_text_preview']}")
    if continuity.get("recent_capability_ids"):
        parts.append(
            "recent_capabilities="
            + ",".join(str(item) for item in continuity["recent_capability_ids"])
        )

    return "\n".join(
        [
            "Visible session continuity:",
            "- " + " | ".join(parts),
            "Use this only as tiny session continuity, not as transcript memory.",
        ]
    )


def _visible_continuity_instruction() -> str | None:
    recent_runs = recent_visible_runs(limit=2)
    if not recent_runs:
        return None

    lines = ["Recent visible continuity:"]
    for item in recent_runs:
        status = str(item.get("status") or "unknown")
        finished_at = str(item.get("finished_at") or "unknown")
        preview = str(item.get("text_preview") or "").strip()
        error = str(item.get("error") or "").strip()
        capability_id = str(item.get("capability_id") or "").strip()
        parts = [f"- {status} @ {finished_at}"]
        if capability_id:
            parts.append(f"capability={capability_id}")
        if preview:
            parts.append(f"preview={preview}")
        elif error:
            parts.append(f"error={error}")
        lines.append(" | ".join(parts))

    lines.append(
        "Use this only as short recent continuity context, not as transcript memory."
    )
    return "\n".join(lines)


def _capability_continuity_instruction() -> str | None:
    recent_invocations = recent_capability_invocations(limit=2)
    if not recent_invocations:
        return None

    lines = ["Recent capability continuity:"]
    for item in recent_invocations:
        capability_id = str(item.get("capability_id") or "unknown")
        status = str(item.get("status") or "unknown")
        execution_mode = str(item.get("execution_mode") or "unknown")
        finished_at = str(item.get("finished_at") or "unknown")
        preview = str(item.get("result_preview") or "").strip()
        detail = str(item.get("detail") or "").strip()
        parts = [
            f"- {capability_id}",
            f"status={status}",
            f"mode={execution_mode}",
            f"finished_at={finished_at}",
        ]
        if preview:
            parts.append(f"preview={preview}")
        elif detail:
            parts.append(f"detail={detail}")
        lines.append(" | ".join(parts))

    lines.append(
        "Use this only as short recent capability continuity, not as tool history."
    )
    return "\n".join(lines)


def _visible_work_instruction() -> str | None:
    from core.services.visible_runs import get_visible_selected_work_item

    selected_work_item = get_visible_selected_work_item()
    if not selected_work_item.get("selected_work_id"):
        return None

    parts = [
        f"selected_work_id={selected_work_item.get('selected_work_id') or 'unknown'}",
        f"selected_status={selected_work_item.get('selected_status') or 'unknown'}",
    ]
    if selected_work_item.get("selected_run_id"):
        parts.append(f"selected_run_id={selected_work_item['selected_run_id']}")
    if selected_work_item.get("selected_lane"):
        parts.append(f"lane={selected_work_item['selected_lane']}")
    if selected_work_item.get("selected_provider") or selected_work_item.get(
        "selected_model"
    ):
        parts.append(
            "provider_model="
            f"{selected_work_item.get('selected_provider') or 'unknown'}"
            f"/{selected_work_item.get('selected_model') or 'unknown'}"
        )
    if selected_work_item.get("selected_capability_id"):
        parts.append(f"capability={selected_work_item['selected_capability_id']}")
    if selected_work_item.get("selection_source"):
        parts.append(f"source={selected_work_item['selection_source']}")
    if selected_work_item.get("selected_user_message_preview"):
        parts.append(f"preview={selected_work_item['selected_user_message_preview']}")
    elif selected_work_item.get("selected_work_preview"):
        parts.append(f"work_preview={selected_work_item['selected_work_preview']}")

    return "\n".join(
        [
            "Visible work context:",
            "- " + " | ".join(parts),
            "Use this only as tiny current work context, not as planner or workflow state.",
        ]
    )


def _private_support_signal_instruction() -> str | None:
    recent_notes = recent_private_inner_notes(limit=1)
    if not recent_notes:
        return None

    note = recent_notes[0]
    identity_alignment = str(note.get("identity_alignment") or "").strip()
    if not identity_alignment:
        return None

    parts = [f"identity_alignment={identity_alignment}"]
    uncertainty = str(note.get("uncertainty") or "").strip()
    focus = str(note.get("focus") or "").strip()
    if uncertainty:
        parts.append(f"uncertainty={uncertainty}")
    if focus:
        parts.append(f"focus={focus}")

    return "\n".join(
        [
            "Private support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def _growth_support_signal_instruction() -> str | None:
    recent_notes = recent_private_growth_notes(limit=1)
    if not recent_notes:
        return None

    note = recent_notes[0]
    identity_signal = str(note.get("identity_signal") or "").strip()
    learning_kind = str(note.get("learning_kind") or "").strip()
    confidence = str(note.get("confidence") or "").strip()
    if not identity_signal or not learning_kind:
        return None

    parts = [
        f"learning_kind={learning_kind}",
        f"identity_signal={identity_signal}",
    ]
    if confidence:
        parts.append(f"confidence={confidence}")
    helpful_signal = str(note.get("helpful_signal") or "").strip()
    mistake_signal = str(note.get("mistake_signal") or "").strip()
    if helpful_signal:
        parts.append(f"helpful_signal={helpful_signal}")
    elif mistake_signal:
        parts.append(f"mistake_signal={mistake_signal}")

    return "\n".join(
        [
            "Growth support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def _self_model_support_signal_instruction() -> str | None:
    model = get_private_self_model()
    if not model:
        return None

    identity_focus = str(model.get("identity_focus") or "").strip()
    preferred_work_mode = str(model.get("preferred_work_mode") or "").strip()
    if not identity_focus or not preferred_work_mode:
        return None

    parts = [
        f"identity_focus={identity_focus}",
        f"preferred_work_mode={preferred_work_mode}",
    ]
    recurring_tension = str(model.get("recurring_tension") or "").strip()
    growth_direction = str(model.get("growth_direction") or "").strip()
    confidence = str(model.get("confidence") or "").strip()
    if recurring_tension:
        parts.append(f"recurring_tension={recurring_tension}")
    if growth_direction:
        parts.append(f"growth_direction={growth_direction}")
    if confidence:
        parts.append(f"confidence={confidence}")

    return "\n".join(
        [
            "Self-model support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def _retained_memory_support_signal_instruction() -> str | None:
    projection = build_private_retained_memory_projection(
        current_record=get_private_retained_memory_record(),
        recent_records=recent_private_retained_memory_records(limit=5),
    )
    if not projection.get("active"):
        return None

    retained_focus = str(projection.get("retained_focus") or "").strip()
    retained_kind = str(projection.get("retained_kind") or "").strip()
    retention_scope = str(projection.get("retention_scope") or "").strip()
    if not retained_focus or not retained_kind or not retention_scope:
        return None

    parts = [
        f"retained_focus={retained_focus}",
        f"retained_kind={retained_kind}",
        f"retention_scope={retention_scope}",
    ]
    confidence = str(projection.get("confidence") or "").strip()
    if confidence:
        parts.append(f"confidence={confidence}")

    return "\n".join(
        [
            "Retained memory support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def _temporal_support_signal_instruction() -> str | None:
    signal = get_private_temporal_promotion_signal()
    if not signal:
        return None

    rhythm_state = str(signal.get("rhythm_state") or "").strip()
    rhythm_window = str(signal.get("rhythm_window") or "").strip()
    promotion_action = str(signal.get("promotion_action") or "").strip()
    if not rhythm_state or not rhythm_window or not promotion_action:
        return None

    parts = [
        f"rhythm_state={rhythm_state}",
        f"rhythm_window={rhythm_window}",
        f"promotion_action={promotion_action}",
    ]
    promotion_confidence = str(signal.get("promotion_confidence") or "").strip()
    if promotion_confidence:
        parts.append(f"promotion_confidence={promotion_confidence}")

    return "\n".join(
        [
            "Temporal support signal:",
            "- " + " | ".join(parts),
            "Use this only as a subordinate helper signal. Visible and runtime truth outrank it.",
        ]
    )


def visible_capability_continuity_summary() -> dict[str, object]:
    recent_invocations = recent_capability_invocations(limit=2)
    capability_ids: list[str] = []
    statuses: list[str] = []
    preview_count = 0
    detail_count = 0

    for item in recent_invocations:
        capability_id = str(item.get("capability_id") or "").strip()
        if capability_id:
            capability_ids.append(capability_id)
        status = str(item.get("status") or "").strip()
        if status:
            statuses.append(status)
        if str(item.get("result_preview") or "").strip():
            preview_count += 1
        if str(item.get("detail") or "").strip():
            detail_count += 1

    instruction = _capability_continuity_instruction()
    return {
        "active": bool(instruction),
        "source": "persisted-capability-invocations",
        "included_rows": len(recent_invocations),
        "included_capability_ids": capability_ids,
        "statuses": statuses,
        "preview_count": preview_count,
        "detail_count": detail_count,
        "chars": len(instruction or ""),
    }


def visible_session_continuity_summary() -> dict[str, object]:
    continuity = visible_session_continuity()
    instruction = _visible_session_continuity_instruction()
    return {
        **continuity,
        "chars": len(instruction or ""),
    }


def visible_continuity_summary() -> dict[str, object]:
    recent_runs = recent_visible_runs(limit=2)
    included_run_ids: list[str] = []
    statuses: list[str] = []
    preview_count = 0
    error_count = 0
    capability_count = 0

    for item in recent_runs:
        run_id = str(item.get("run_id") or "").strip()
        if run_id:
            included_run_ids.append(run_id)
        status = str(item.get("status") or "").strip()
        if status:
            statuses.append(status)
        if str(item.get("text_preview") or "").strip():
            preview_count += 1
        if str(item.get("error") or "").strip():
            error_count += 1
        if str(item.get("capability_id") or "").strip():
            capability_count += 1

    instruction = _visible_continuity_instruction()
    return {
        "active": bool(instruction),
        "source": "persisted-visible-runs",
        "included_rows": len(recent_runs),
        "included_run_ids": included_run_ids,
        "statuses": statuses,
        "preview_count": preview_count,
        "error_count": error_count,
        "capability_count": capability_count,
        "chars": len(instruction or ""),
    }


def _capability_instruction() -> str | None:
    capabilities = load_workspace_capabilities().get("declared_capabilities", [])
    runnable = [
        item
        for item in capabilities
        if item.get("runnable") and str(item.get("capability_id", "")).strip()
    ]
    if not runnable:
        return None
    capability_lines = [
        f"- {item['capability_id']}: {item.get('name', '')}" for item in runnable[:8]
    ]
    return "\n".join(
        [
            "Visible lane capability rule:",
            "Use a workspace capability only by replying with exactly one line in this exact form and nothing else:",
            '<capability-call id="capability_id" />',
            "If the capability needs arguments, bind them in the same tag as quoted attributes, for example:",
            '<capability-call id="capability_id" command_text="pwd" />',
            "Only use one of these currently runnable capability_ids:",
            *capability_lines,
            "If no capability is needed, answer normally.",
        ]
    )


def _estimate_tokens(text: str) -> int:
    words = [part for part in text.strip().split() if part]
    return max(1, len(words))


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _calculate_openai_cost_usd(
    *, model: str, input_tokens: int, output_tokens: int
) -> float:
    pricing = OPENAI_TEXT_PRICING_PER_1M_TOKENS.get(model.strip().lower())
    if pricing is None:
        return 0.0

    input_rate, output_rate = pricing
    total = Decimal(int(input_tokens)) * input_rate / Decimal(1_000_000) + Decimal(
        int(output_tokens)
    ) * output_rate / Decimal(1_000_000)
    return float(total.quantize(Decimal("0.00000001")))


def _chunk_text(text: str, size: int = 48) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def _extract_chat_completion_delta(event: dict) -> str:
    choices = event.get("choices") or []
    parts: list[str] = []
    for item in choices:
        if not isinstance(item, dict):
            continue
        delta = item.get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            if content:
                parts.append(content)
            continue
        if isinstance(content, list):
            for chunk in content:
                if not isinstance(chunk, dict):
                    continue
                text = str(chunk.get("text") or "").strip()
                if text:
                    parts.append(text)
    return "".join(parts)


def _finalize_openai_tool_calls(tool_calls: list[dict]) -> list[dict]:
    """Normalize OpenAI-style tool_calls so arguments is a dict, not a JSON string.

    OpenAI Chat Completions returns ``function.arguments`` as a JSON-encoded
    string. Downstream executors (execute_tool) expect a dict, matching how
    Ollama returns tool_calls. Parse once here so consumers see one shape.
    """
    finalized: list[dict] = []
    for tc in tool_calls:
        if not isinstance(tc, dict):
            continue
        fn = dict(tc.get("function") or {})
        args = fn.get("arguments")
        if isinstance(args, str):
            stripped = args.strip()
            if stripped:
                try:
                    fn["arguments"] = json.loads(stripped)
                except (json.JSONDecodeError, ValueError):
                    fn["arguments"] = {}
            else:
                fn["arguments"] = {}
        elif args is None:
            fn["arguments"] = {}
        finalized.append({**tc, "function": fn})
    return finalized


def _merge_openai_tool_call_deltas(
    accumulator: dict[int, dict], event: dict
) -> None:
    """Merge OpenAI SSE tool_calls delta chunks into a per-index accumulator.

    Tool calls stream as partial objects keyed by `index`: the first chunk
    carries id/name, later chunks append to `function.arguments`. This merges
    them in-place so the caller can yield complete tool calls once the stream
    terminates.
    """
    for item in event.get("choices") or []:
        if not isinstance(item, dict):
            continue
        delta = item.get("delta") or {}
        for tc in delta.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            idx = int(tc.get("index") or 0)
            slot = accumulator.setdefault(
                idx,
                {
                    "id": None,
                    "type": "function",
                    "function": {"name": None, "arguments": ""},
                },
            )
            if tc.get("id"):
                slot["id"] = tc["id"]
            if tc.get("type"):
                slot["type"] = tc["type"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                slot["function"]["name"] = fn["name"]
            if "arguments" in fn and fn["arguments"] is not None:
                slot["function"]["arguments"] += str(fn["arguments"])


def _chat_completion_stream_is_terminal(event: dict) -> bool:
    choices = event.get("choices") or []
    if not choices:
        return False
    return all(
        isinstance(item, dict) and str(item.get("finish_reason") or "").strip()
        for item in choices
    )


def _iter_sse_events(response) -> Iterator[dict]:
    event_name = "message"
    data_lines: list[str] = []

    for raw_line in response:
        line = raw_line.decode("utf-8").strip()
        if not line:
            if not data_lines:
                event_name = "message"
                continue
            data = "\n".join(data_lines)
            data_lines = []
            if data == "[DONE]":
                break
            payload = json.loads(data)
            if "type" not in payload:
                payload["type"] = event_name
            yield payload
            event_name = "message"
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
