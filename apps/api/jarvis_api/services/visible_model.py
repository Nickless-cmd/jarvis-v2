from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from core.auth.profiles import get_provider_state, list_auth_profiles
from core.runtime.settings import load_settings


@dataclass(slots=True)
class VisibleModelResult:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


def execute_visible_model(*, message: str, provider: str, model: str) -> VisibleModelResult:
    if provider == "openai":
        return _execute_openai_model(message=message, model=model)
    if provider == "phase1-runtime":
        return _execute_phase1_model(message=message, provider=provider, model=model)
    raise ValueError(f"Unsupported visible model provider: {provider}")


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
        }

    if provider == "openai":
        profile, status = _resolve_openai_profile()
        provider_reachable = False
        live_verified = False
        provider_status = "auth-not-ready"

        if status == "ready" and profile is not None:
            provider_reachable, live_verified, provider_status = _probe_openai_model(
                profile=profile,
                model=model,
            )
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


def _execute_openai_model(*, message: str, model: str) -> VisibleModelResult:
    api_key = _load_openai_api_key()
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": message}],
            }
        ],
    }
    data = _post_openai_responses(payload=payload, api_key=api_key)
    text = _extract_output_text(data)
    usage = data.get("usage", {})
    return VisibleModelResult(
        text=text,
        input_tokens=int(usage.get("input_tokens", _estimate_tokens(message))),
        output_tokens=int(usage.get("output_tokens", _estimate_tokens(text))),
        cost_usd=0.0,
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


def _probe_openai_model(*, profile: str, model: str) -> tuple[bool, bool, str]:
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
        return True, True, "reachable"
    except urllib_error.HTTPError as exc:
        if exc.code == 404:
            return True, False, "model-not-found"
        if exc.code in {401, 403}:
            return False, False, "auth-rejected"
        return False, False, f"http-{exc.code}"
    except urllib_error.URLError:
        return False, False, "unreachable"


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


def _estimate_tokens(text: str) -> int:
    words = [part for part in text.strip().split() if part]
    return max(1, len(words))
