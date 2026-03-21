from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from core.auth.profiles import get_provider_state
from core.runtime.provider_router import resolve_provider_router_target


def cheap_lane_execution_truth() -> dict[str, object]:
    lane = "cheap"
    target = resolve_provider_router_target(lane=lane)
    status = _lane_status(target)
    return {
        "active": True,
        "lane": lane,
        "consumer": "provider-router-cheap-lane",
        "status": status,
        "can_execute": status == "ready",
        "target": target,
    }


def execute_cheap_lane(*, message: str) -> dict[str, object]:
    return _execute_lane(message=message, truth=cheap_lane_execution_truth())

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
        "credentials_ready": readiness["credentials_ready"],
        "auth_status": readiness["auth_status"],
        "provider_ready": readiness["provider_ready"],
        "coding_auth_path": readiness["coding_auth_path"],
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
            "credentials_ready": credentials_ready,
            "auth_status": "missing-target",
            "provider_ready": False,
            "coding_auth_path": coding_auth_path,
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
            "credentials_ready": True,
            "auth_status": "not-required",
            "provider_ready": True,
            "coding_auth_path": coding_auth_path,
            "live_verified": False,
            "provider_status": "local-fallback",
            "checked_at": None,
        }

    if provider == "github-copilot":
        oauth_ready = credentials_ready
        return {
            "status": "not-implemented" if oauth_ready else "oauth-required",
            "can_execute": False,
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "credentials_ready": credentials_ready,
            "auth_status": "ready" if oauth_ready else "oauth-required",
            "provider_ready": False,
            "coding_auth_path": coding_auth_path,
            "live_verified": False,
            "provider_status": "not-implemented" if oauth_ready else "oauth-required",
            "checked_at": None,
        }

    if provider in {"openai", "openrouter"}:
        auth_status = "ready" if credentials_ready else "auth-not-ready"
        provider_ready = bool(probe["provider_ready"])
        return {
            "status": str(probe["provider_status"]) if credentials_ready else "auth-not-ready",
            "can_execute": provider_ready,
            "auth_mode": auth_mode,
            "auth_profile": auth_profile,
            "credentials_ready": credentials_ready,
            "auth_status": auth_status,
            "provider_ready": provider_ready,
            "coding_auth_path": coding_auth_path,
            "live_verified": bool(probe["live_verified"]),
            "provider_status": str(probe["provider_status"]),
            "checked_at": probe["checked_at"],
        }

    return {
        "status": "unsupported-provider",
        "can_execute": False,
        "auth_mode": auth_mode,
        "auth_profile": auth_profile,
        "credentials_ready": credentials_ready,
        "auth_status": "unsupported-provider",
        "provider_ready": False,
        "coding_auth_path": coding_auth_path,
        "live_verified": False,
        "provider_status": "unsupported-provider",
        "checked_at": None,
    }


def _coding_auth_path(*, provider: str, auth_mode: str) -> str:
    if provider == "openai" and auth_mode == "api-key":
        return "openai-codex-api-key"
    if provider == "github-copilot" and auth_mode == "oauth":
        return "github-copilot-oauth"
    if provider == "openrouter" and auth_mode == "api-key":
        return "openrouter-api-key"
    if provider == "phase1-runtime":
        return "phase1-runtime"
    return "unsupported"


def _coding_lane_probe(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    credentials_ready: bool,
    base_url: str,
) -> dict[str, object]:
    if provider == "openai":
        if not credentials_ready:
            return {
                "provider_ready": False,
                "live_verified": False,
                "provider_status": "auth-not-ready",
                "checked_at": None,
            }
        return _probe_openai_coding_target(
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


def _probe_openai_coding_target(
    *, model: str, auth_profile: str, base_url: str
) -> dict[str, object]:
    checked_at = datetime.now(UTC).isoformat()
    api_key = _load_provider_api_key(provider="openai", profile=auth_profile)
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
    elif provider == "openai":
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
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or input_tokens
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
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        raise RuntimeError(f"{provider} cheap lane not ready: missing-profile")
    credentials_path = Path(str(state.get("credentials_path", "")))
    if not credentials_path.exists():
        raise RuntimeError(f"{provider} cheap lane not ready: missing-credentials")
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    api_key = str(credentials.get("api_key") or credentials.get("access_token") or "")
    if not api_key:
        raise RuntimeError(f"{provider} cheap lane not ready: missing-credentials")
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
    raise RuntimeError("Cheap lane execution returned no output_text")


def _extract_openrouter_text(data: dict) -> str:
    choices = data.get("choices") or []
    for item in choices:
        if not isinstance(item, dict):
            continue
        message = item.get("message") or {}
        text = str(message.get("content") or "").strip()
        if text:
            return text
    raise RuntimeError("Cheap lane execution returned no OpenRouter text")


def _estimate_tokens(text: str) -> int:
    normalized = " ".join((text or "").split())
    if not normalized:
        return 1
    return max(1, len(normalized) // 4)
