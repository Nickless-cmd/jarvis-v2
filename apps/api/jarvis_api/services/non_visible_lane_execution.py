from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from core.auth.profiles import (
    get_provider_state,
)
from core.auth.copilot_oauth import get_copilot_oauth_truth
from core.auth.openai_oauth import get_openai_bearer_token, get_openai_oauth_truth
from core.runtime.provider_router import resolve_provider_router_target
from apps.api.jarvis_api.services.cheap_provider_runtime import (
    cheap_lane_status_surface,
    execute_cheap_lane_via_pool,
    select_cheap_lane_target,
)


def cheap_lane_execution_truth() -> dict[str, object]:
    lane = "cheap"
    target = select_cheap_lane_target()
    status_surface = cheap_lane_status_surface()
    selected_provider = str(target.get("provider") or "").strip()
    selected_model = str(target.get("model") or "").strip()
    active = bool(selected_provider and selected_model and bool(target.get("active", True)))
    status = str(target.get("status") or target.get("selection_reason") or "no-healthy-provider")
    return {
        "active": True,
        "lane": lane,
        "consumer": "provider-router-internal-fallback-lane",
        "status": status,
        "can_execute": active,
        "target": target,
        "provider_count": int(status_surface.get("provider_count") or 0),
        "providers": list(status_surface.get("providers") or []),
    }


def execute_cheap_lane(*, message: str) -> dict[str, object]:
    return execute_cheap_lane_via_pool(message=message)


def local_lane_execution_truth() -> dict[str, object]:
    lane = "local"
    target = resolve_provider_router_target(lane=lane)
    readiness = _local_lane_readiness(target)
    return {
        "active": True,
        "lane": lane,
        "consumer": "provider-router-local-lane",
        "status": readiness["status"],
        "can_execute": readiness["can_execute"],
        "auth_mode": readiness["auth_mode"],
        "auth_profile": readiness["auth_profile"],
        "provider_ready": readiness["provider_ready"],
        "local_auth_path": readiness["local_auth_path"],
        "live_verified": readiness["live_verified"],
        "provider_status": readiness["provider_status"],
        "checked_at": readiness["checked_at"],
        "target": target,
    }


def coding_lane_execution_truth() -> dict[str, object]:
    lane = "coding"
    target = resolve_provider_router_target(lane=lane)
    readiness = _coding_lane_readiness(target)
    return {
        "active": True,
        "lane": lane,
        "consumer": "provider-router-coding-lane",
        "status": readiness["status"],
        "can_execute": readiness["can_execute"],
        "auth_mode": readiness["auth_mode"],
        "auth_profile": readiness["auth_profile"],
        "auth_state": readiness["auth_state"],
        "auth_material_kind": readiness["auth_material_kind"],
        "oauth_state": readiness["oauth_state"],
        "credentials_ready": readiness["credentials_ready"],
        "auth_status": readiness["auth_status"],
        "provider_ready": readiness["provider_ready"],
        "coding_auth_path": readiness["coding_auth_path"],
        "launch_result_state": readiness["launch_result_state"],
        "launch_freshness": readiness["launch_freshness"],
        "callback_validation_state": readiness["callback_validation_state"],
        "exchange_readiness": readiness["exchange_readiness"],
        "callback_intent_consistency": readiness["callback_intent_consistency"],
        "live_verified": readiness["live_verified"],
        "provider_status": readiness["provider_status"],
        "checked_at": readiness["checked_at"],
        "target": target,
    }


def execute_coding_lane(*, message: str) -> dict[str, object]:
    return _execute_lane(message=message, truth=coding_lane_execution_truth())


def _lane_status(target: dict[str, object]) -> str:
    if not bool(target.get("active")):
        return "missing-target"

    provider = str(target.get("provider") or "").strip()
    if provider == "phase1-runtime":
        return "ready"
    if provider in {"openai", "openrouter"}:
        return "ready" if bool(target.get("credentials_ready")) else "auth-not-ready"
    return "unsupported-provider"


def _coding_lane_readiness(target: dict[str, object]) -> dict[str, object]:
    provider = str(target.get("provider") or "").strip()
    auth_mode = str(target.get("auth_mode") or "").strip() or "none"
    auth_profile = str(target.get("auth_profile") or "").strip()
    credentials_ready = bool(target.get("credentials_ready"))
    coding_auth_path = _coding_auth_path(provider=provider, auth_mode=auth_mode)
    probe = _coding_lane_probe(
        provider=provider,
        model=str(target.get("model") or "").strip(),
        auth_profile=auth_profile,
        credentials_ready=credentials_ready,
        base_url=str(target.get("base_url") or "").strip(),
    )

    if not bool(target.get("active")):
        return {
            "status": "missing-target",
            "can_execute": False,
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "auth_state": "missing-target",
            "auth_material_kind": "missing",
            "oauth_state": "missing",
            "credentials_ready": credentials_ready,
            "auth_status": "missing-target",
            "provider_ready": False,
            "coding_auth_path": coding_auth_path,
            "launch_result_state": "not-started",
            "launch_freshness": "not-applicable",
            "callback_validation_state": "not-applicable",
            "exchange_readiness": "not-applicable",
            "callback_intent_consistency": "not-applicable",
            "live_verified": False,
            "provider_status": "missing-target",
            "checked_at": None,
        }

    if provider == "phase1-runtime":
        return {
            "status": "ready",
            "can_execute": True,
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "auth_state": "not-required",
            "auth_material_kind": "not-required",
            "oauth_state": "not-applicable",
            "credentials_ready": True,
            "auth_status": "not-required",
            "provider_ready": True,
            "coding_auth_path": coding_auth_path,
            "launch_result_state": "not-applicable",
            "launch_freshness": "not-applicable",
            "callback_validation_state": "not-applicable",
            "exchange_readiness": "not-applicable",
            "callback_intent_consistency": "not-applicable",
            "live_verified": False,
            "provider_status": "local-fallback",
            "checked_at": None,
        }

    if provider == "github-copilot":
        oauth_truth = get_copilot_oauth_truth(profile=auth_profile)
        oauth_state = str(oauth_truth["oauth_state"])
        auth_state = _github_copilot_auth_state(oauth_state=oauth_state)
        auth_material_kind = str(oauth_truth["auth_material_kind"])
        launch_result_state = str(oauth_truth["launch_result_state"])
        launch_freshness = str(oauth_truth["launch_freshness"])
        callback_validation_state = str(oauth_truth["callback_validation_state"])
        exchange_readiness = str(oauth_truth["exchange_readiness"])
        callback_intent_consistency = str(oauth_truth["callback_intent_consistency"])
        copilot_status = _github_copilot_status(auth_state=auth_state)
        return {
            "status": copilot_status,
            "can_execute": copilot_status == "ready" and credentials_ready,
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "auth_state": auth_state,
            "auth_material_kind": auth_material_kind,
            "oauth_state": oauth_state,
            "credentials_ready": credentials_ready,
            "auth_status": _github_copilot_auth_status(
                auth_state=auth_state,
                exchange_readiness=exchange_readiness,
            ),
            "provider_ready": False,
            "coding_auth_path": coding_auth_path,
            "launch_result_state": launch_result_state,
            "launch_freshness": launch_freshness,
            "callback_validation_state": callback_validation_state,
            "exchange_readiness": exchange_readiness,
            "callback_intent_consistency": callback_intent_consistency,
            "live_verified": False,
            "provider_status": _github_copilot_provider_status(auth_state=auth_state),
            "checked_at": None,
        }

    if provider == "openai-codex":
        oauth_truth = get_openai_oauth_truth(profile=auth_profile)
        oauth_state = str(oauth_truth["oauth_state"])
        auth_state = _github_copilot_auth_state(oauth_state=oauth_state)
        auth_material_kind = str(oauth_truth["auth_material_kind"])
        launch_result_state = str(oauth_truth["launch_result_state"])
        launch_freshness = str(oauth_truth["launch_freshness"])
        callback_validation_state = str(oauth_truth["callback_validation_state"])
        exchange_readiness = str(oauth_truth["exchange_readiness"])
        callback_intent_consistency = str(oauth_truth["callback_intent_consistency"])
        provider_ready = bool(probe["provider_ready"])
        provider_status = str(probe["provider_status"])
        return {
            "status": provider_status
            if provider_ready
            else _github_copilot_status(auth_state=auth_state),
            "can_execute": provider_ready,
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "auth_state": auth_state,
            "auth_material_kind": auth_material_kind,
            "oauth_state": oauth_state,
            "credentials_ready": credentials_ready,
            "auth_status": _github_copilot_auth_status(
                auth_state=auth_state,
                exchange_readiness=exchange_readiness,
            ),
            "provider_ready": provider_ready,
            "coding_auth_path": coding_auth_path,
            "launch_result_state": launch_result_state,
            "launch_freshness": launch_freshness,
            "callback_validation_state": callback_validation_state,
            "exchange_readiness": exchange_readiness,
            "callback_intent_consistency": callback_intent_consistency,
            "live_verified": bool(probe["live_verified"]),
            "provider_status": provider_status,
            "checked_at": probe["checked_at"],
        }

    if provider in {"openai", "openrouter"}:
        auth_status = "ready" if credentials_ready else "auth-not-ready"
        provider_ready = bool(probe["provider_ready"])
        return {
            "status": str(probe["provider_status"])
            if credentials_ready
            else "auth-not-ready",
            "can_execute": provider_ready,
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "auth_state": auth_status,
            "auth_material_kind": "real" if credentials_ready else "missing",
            "oauth_state": "not-applicable",
            "credentials_ready": credentials_ready,
            "auth_status": auth_status,
            "provider_ready": provider_ready,
            "coding_auth_path": coding_auth_path,
            "launch_result_state": "not-applicable",
            "launch_freshness": "not-applicable",
            "callback_validation_state": "not-applicable",
            "exchange_readiness": "not-applicable",
            "callback_intent_consistency": "not-applicable",
            "live_verified": bool(probe["live_verified"]),
            "provider_status": str(probe["provider_status"]),
            "checked_at": probe["checked_at"],
        }

    return {
        "status": "unsupported-provider",
        "can_execute": False,
        "auth_mode": auth_mode,
        "auth_profile": auth_profile,
        "auth_state": "unsupported-provider",
        "auth_material_kind": "missing",
        "oauth_state": "not-applicable",
        "credentials_ready": credentials_ready,
        "auth_status": "unsupported-provider",
        "provider_ready": False,
        "coding_auth_path": coding_auth_path,
        "launch_result_state": "not-applicable",
        "launch_freshness": "not-applicable",
        "callback_validation_state": "not-applicable",
        "exchange_readiness": "not-applicable",
        "callback_intent_consistency": "not-applicable",
        "live_verified": False,
        "provider_status": "unsupported-provider",
        "checked_at": None,
    }


def _local_lane_readiness(target: dict[str, object]) -> dict[str, object]:
    provider = str(target.get("provider") or "").strip()
    auth_mode = str(target.get("auth_mode") or "").strip() or "none"
    auth_profile = str(target.get("auth_profile") or "").strip()

    if not bool(target.get("active")):
        return {
            "status": "missing-target",
            "can_execute": False,
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "provider_ready": False,
            "local_auth_path": _local_auth_path(provider=provider, auth_mode=auth_mode),
            "live_verified": False,
            "provider_status": "missing-target",
            "checked_at": None,
        }

    if provider == "ollama":
        probe = _probe_ollama_local_target(
            model=str(target.get("model") or "").strip(),
            base_url=str(target.get("base_url") or "").strip(),
        )
        return {
            "status": str(probe["provider_status"]),
            "can_execute": bool(probe["provider_ready"]),
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "provider_ready": bool(probe["provider_ready"]),
            "local_auth_path": _local_auth_path(provider=provider, auth_mode=auth_mode),
            "live_verified": bool(probe["live_verified"]),
            "provider_status": str(probe["provider_status"]),
            "checked_at": probe["checked_at"],
        }

    if provider == "phase1-runtime":
        return {
            "status": "ready",
            "can_execute": True,
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "provider_ready": True,
            "local_auth_path": _local_auth_path(provider=provider, auth_mode=auth_mode),
            "live_verified": False,
            "provider_status": "local-fallback",
            "checked_at": None,
        }

    return {
        "status": "unsupported-provider",
        "can_execute": False,
        "auth_mode": auth_mode,
        "auth_profile": auth_profile,
        "provider_ready": False,
        "local_auth_path": _local_auth_path(provider=provider, auth_mode=auth_mode),
        "live_verified": False,
        "provider_status": "unsupported-provider",
        "checked_at": None,
    }


def _coding_auth_path(*, provider: str, auth_mode: str) -> str:
    if provider == "openai" and auth_mode == "api-key":
        return "openai-api-key"
    if provider == "openai-codex" and auth_mode == "oauth":
        return "openai-codex-oauth"
    if provider == "github-copilot" and auth_mode == "oauth":
        return "github-copilot-oauth"
    if provider == "openrouter" and auth_mode == "api-key":
        return "openrouter-api-key"
    if provider == "phase1-runtime":
        return "phase1-runtime"
    return "unsupported"


def _local_auth_path(*, provider: str, auth_mode: str) -> str:
    if provider == "ollama" and auth_mode in {"none", ""}:
        return "ollama-local"
    if provider == "phase1-runtime":
        return "phase1-runtime"
    return "unsupported"


def _github_copilot_auth_state(*, oauth_state: str) -> str:
    if oauth_state == "prepared":
        return "oauth-prepared"
    if oauth_state == "handshake-started":
        return "oauth-handshake-started"
    if oauth_state == "handshake-stubbed":
        return "oauth-handshake-stubbed"
    if oauth_state == "launch-stubbed":
        return "oauth-launch-stubbed"
    if oauth_state == "launch-intent-created":
        return "oauth-launch-intent-created"
    if oauth_state == "browser-launch-attempted":
        return "oauth-browser-launch-attempted"
    if oauth_state == "callback-received":
        return "oauth-callback-received"
    if oauth_state == "placeholder-stored":
        return "oauth-placeholder-stored"
    if oauth_state == "real-stored":
        return "oauth-stored"
    if oauth_state == "revoked":
        return "oauth-revoked"
    return "oauth-required"


def _github_copilot_status(*, auth_state: str) -> str:
    if auth_state == "oauth-stored":
        return "ready"
    if auth_state == "oauth-callback-received":
        return "oauth-callback-received"
    if auth_state == "oauth-browser-launch-attempted":
        return "oauth-browser-launch-attempted"
    if auth_state == "oauth-launch-intent-created":
        return "oauth-launch-intent-created"
    if auth_state == "oauth-launch-stubbed":
        return "oauth-launch-stubbed"
    if auth_state == "oauth-handshake-stubbed":
        return "oauth-handshake-stubbed"
    if auth_state == "oauth-handshake-started":
        return "oauth-handshake-started"
    if auth_state == "oauth-placeholder-stored":
        return "placeholder-only"
    if auth_state == "oauth-prepared":
        return "oauth-prepared"
    if auth_state == "oauth-revoked":
        return "oauth-revoked"
    return "oauth-required"


def _github_copilot_auth_status(*, auth_state: str, exchange_readiness: str) -> str:
    if auth_state == "oauth-stored":
        return (
            exchange_readiness
            if exchange_readiness != "not-applicable"
            else "exchange-complete"
        )
    if auth_state == "oauth-callback-received":
        return (
            exchange_readiness
            if exchange_readiness != "not-applicable"
            else "exchange-ready"
        )
    if auth_state == "oauth-browser-launch-attempted":
        return "oauth-browser-launch-attempted"
    if auth_state == "oauth-launch-intent-created":
        return "oauth-launch-intent-created"
    if auth_state == "oauth-launch-stubbed":
        return "oauth-launch-stubbed"
    if auth_state == "oauth-handshake-stubbed":
        return "oauth-handshake-stubbed"
    if auth_state == "oauth-handshake-started":
        return "oauth-handshake-started"
    if auth_state == "oauth-placeholder-stored":
        return "placeholder-only"
    if auth_state == "oauth-prepared":
        return "oauth-prepared"
    if auth_state == "oauth-revoked":
        return "oauth-revoked"
    return "oauth-required"


def _github_copilot_provider_status(*, auth_state: str) -> str:
    if auth_state == "oauth-stored":
        return "ready"
    if auth_state == "oauth-callback-received":
        return "oauth-callback-received"
    if auth_state == "oauth-browser-launch-attempted":
        return "oauth-browser-launch-attempted"
    if auth_state == "oauth-launch-intent-created":
        return "oauth-launch-intent-created"
    if auth_state == "oauth-launch-stubbed":
        return "oauth-launch-stubbed"
    if auth_state == "oauth-handshake-stubbed":
        return "oauth-handshake-stubbed"
    if auth_state == "oauth-handshake-started":
        return "oauth-handshake-started"
    if auth_state == "oauth-placeholder-stored":
        return "placeholder-only"
    if auth_state == "oauth-prepared":
        return "oauth-prepared"
    if auth_state == "oauth-revoked":
        return "oauth-revoked"
    return "oauth-required"


def _coding_lane_probe(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    credentials_ready: bool,
    base_url: str,
) -> dict[str, object]:
    if provider in {"openai", "openai-codex"}:
        if not credentials_ready:
            return {
                "provider_ready": False,
                "live_verified": False,
                "provider_status": "auth-not-ready",
                "checked_at": None,
            }
        return _probe_openai_coding_target(
            provider=provider,
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
        )

    if provider == "openrouter":
        return {
            "provider_ready": credentials_ready,
            "live_verified": False,
            "provider_status": "not-probed" if credentials_ready else "auth-not-ready",
            "checked_at": None,
        }

    return {
        "provider_ready": False,
        "live_verified": False,
        "provider_status": "unsupported-provider",
        "checked_at": None,
    }


def _probe_ollama_local_target(*, model: str, base_url: str) -> dict[str, object]:
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
                "provider_ready": False,
                "live_verified": False,
                "provider_status": "model-not-found",
                "checked_at": checked_at,
            }
        return {
            "provider_ready": True,
            "live_verified": True,
            "provider_status": "ready",
            "checked_at": checked_at,
        }
    except urllib_error.HTTPError as exc:
        return {
            "provider_ready": False,
            "live_verified": False,
            "provider_status": f"http-{exc.code}",
            "checked_at": checked_at,
        }
    except Exception:
        return {
            "provider_ready": False,
            "live_verified": False,
            "provider_status": "unreachable",
            "checked_at": checked_at,
        }


def _probe_openai_coding_target(
    *, provider: str, model: str, auth_profile: str, base_url: str
) -> dict[str, object]:
    checked_at = datetime.now(UTC).isoformat()
    api_key = _load_provider_api_key(provider=provider, profile=auth_profile)
    root = (base_url or "https://api.openai.com/v1").rstrip("/")
    model_ref = urllib_parse.quote(model, safe="")
    req = urllib_request.Request(
        f"{root}/models/{model_ref}",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            response.read()
        return {
            "provider_ready": True,
            "live_verified": True,
            "provider_status": "ready",
            "checked_at": checked_at,
        }
    except urllib_error.HTTPError as exc:
        if exc.code == 404:
            status = "model-not-found"
        elif exc.code in {401, 403}:
            status = "auth-rejected"
        else:
            status = f"http-{exc.code}"
        return {
            "provider_ready": False,
            "live_verified": False,
            "provider_status": status,
            "checked_at": checked_at,
        }
    except Exception:
        return {
            "provider_ready": False,
            "live_verified": False,
            "provider_status": "unreachable",
            "checked_at": checked_at,
        }


def _execute_lane(*, message: str, truth: dict[str, object]) -> dict[str, object]:
    if not truth["can_execute"]:
        raise RuntimeError(
            f"{str(truth.get('lane') or 'lane')} lane not executable: {truth['status']}"
        )

    lane = str(truth.get("lane") or "unknown")
    target = dict(truth.get("target") or {})
    provider = str(target.get("provider") or "").strip()
    model = str(target.get("model") or "").strip()
    text = ""
    input_tokens = _estimate_tokens(message)
    output_tokens = 0
    cost_usd = 0.0

    if provider == "phase1-runtime":
        text = (
            f"Jarvis {lane} lane executed through provider-router truth. "
            f"{lane.capitalize()} lane received: {message}"
        )
        output_tokens = _estimate_tokens(text)
    elif provider in {"openai", "openai-codex"}:
        profile = str(target.get("auth_profile") or "").strip()
        api_key = _load_provider_api_key(provider=provider, profile=profile)
        data = _post_openai_responses(
            base_url=str(target.get("base_url") or "").strip(),
            payload={"model": model, "input": message},
            api_key=api_key,
        )
        text = _extract_output_text(data)
        usage = data.get("usage", {})
        input_tokens = int(usage.get("input_tokens", input_tokens))
        output_tokens = int(usage.get("output_tokens", _estimate_tokens(text)))
    elif provider == "github-copilot":
        profile = str(target.get("auth_profile") or "").strip()
        access_token = _load_github_copilot_token(profile=profile)
        data = _post_github_copilot_chat_completion(
            payload={
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "stream": False,
            },
            access_token=access_token,
        )
        text = _extract_github_copilot_text(data)
        usage = data.get("usage", {})
        input_tokens = int(
            usage.get("prompt_tokens") or usage.get("input_tokens") or input_tokens
        )
        output_tokens = int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or _estimate_tokens(text)
        )
    elif provider == "openrouter":
        profile = str(target.get("auth_profile") or "").strip()
        api_key = _load_provider_api_key(provider=provider, profile=profile)
        data = _post_openrouter_chat_completion(
            base_url=str(target.get("base_url") or "").strip(),
            payload={
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "stream": False,
            },
            api_key=api_key,
        )
        text = _extract_openrouter_text(data)
        usage = data.get("usage", {})
        input_tokens = int(
            usage.get("prompt_tokens") or usage.get("input_tokens") or input_tokens
        )
        output_tokens = int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or _estimate_tokens(text)
        )
    else:
        raise RuntimeError(f"{lane} lane provider not supported: {provider}")

    return {
        "lane": lane,
        "provider": provider,
        "model": model,
        "status": "completed",
        "execution_mode": f"provider-router-{lane}-lane",
        "source": str(target.get("source") or ""),
        "text": text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
    }


def _load_provider_api_key(*, provider: str, profile: str) -> str:
    if provider == "openai-codex":
        try:
            return get_openai_bearer_token(profile=profile)
        except Exception as exc:
            raise RuntimeError(f"{provider} internal fallback lane not ready: {exc}")
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        raise RuntimeError(f"{provider} internal fallback lane not ready: missing-profile")
    credentials_path = Path(str(state.get("credentials_path", "")))
    if not credentials_path.exists():
        raise RuntimeError(f"{provider} internal fallback lane not ready: missing-credentials")
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    api_key = str(credentials.get("api_key") or credentials.get("access_token") or "")
    if not api_key:
        raise RuntimeError(f"{provider} internal fallback lane not ready: missing-credentials")
    return api_key


def _post_openai_responses(*, base_url: str, payload: dict, api_key: str) -> dict:
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


def _post_openrouter_chat_completion(
    *, base_url: str, payload: dict, api_key: str
) -> dict:
    root = (base_url or "https://openrouter.ai/api/v1").rstrip("/")
    req = urllib_request.Request(
        f"{root}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_output_text(data: dict) -> str:
    output = data.get("output") or []
    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            if str(content.get("type") or "") != "output_text":
                continue
            text = str(content.get("text") or "").strip()
            if text:
                parts.append(text)
    text = "\n".join(parts).strip()
    if text:
        return text
    raise RuntimeError("Internal fallback lane execution returned no output_text")


def _extract_openrouter_text(data: dict) -> str:
    choices = data.get("choices") or []
    for item in choices:
        if not isinstance(item, dict):
            continue
        message = item.get("message") or {}
        text = str(message.get("content") or "").strip()
        if text:
            return text
    raise RuntimeError("Internal fallback lane execution returned no OpenRouter text")


def _load_github_copilot_token(*, profile: str) -> str:
    state = get_provider_state(profile=profile, provider="github-copilot")
    if state is None:
        raise RuntimeError(f"github-copilot lane not ready: missing-profile")
    credentials_path = Path(str(state.get("credentials_path", "")))
    if not credentials_path.exists():
        raise RuntimeError(f"github-copilot lane not ready: missing-credentials")
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    token = str(credentials.get("access_token") or "")
    if not token:
        raise RuntimeError(f"github-copilot lane not ready: missing-access-token")
    return token


def _post_github_copilot_chat_completion(*, payload: dict, access_token: str) -> dict:
    root = "https://models.github.ai"
    req = urllib_request.Request(
        f"{root}/inference/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub Copilot API error: HTTP {exc.code}: {body}")


def _extract_github_copilot_text(data: dict) -> str:
    choices = data.get("choices") or []
    for item in choices:
        if not isinstance(item, dict):
            continue
        message = item.get("message") or {}
        text = str(message.get("content") or "").strip()
        if text:
            return text
    raise RuntimeError("GitHub Copilot lane execution returned no text")


def fetch_github_copilot_models(*, profile: str) -> list[str]:
    access_token = _load_github_copilot_token(profile=profile)
    root = "https://api.githubcopilot.com"
    req = urllib_request.Request(
        f"{root}/models",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Copilot-Integration-Id": "cli",
        },
        method="GET",
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = data.get("data", [])
        return [
            str(item.get("id") or "").strip()
            for item in models
            if isinstance(item, dict) and item.get("id")
        ]
    except Exception:
        return []


def _estimate_tokens(text: str) -> int:
    normalized = " ".join((text or "").split())
    if not normalized:
        return 1
    return max(1, len(normalized) // 4)
