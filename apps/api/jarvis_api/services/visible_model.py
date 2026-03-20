from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
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

    if provider == "phase1-runtime":
        return {
            "provider": provider,
            "model": model,
            "mode": "fallback",
            "auth_ready": True,
            "auth_status": "not-required",
            "auth_profile": None,
        }

    if provider == "openai":
        profile = _find_openai_ready_profile()
        return {
            "provider": provider,
            "model": model,
            "mode": "provider-backed",
            "auth_ready": profile is not None,
            "auth_status": "ready" if profile else "missing-credentials",
            "auth_profile": profile,
        }

    return {
        "provider": provider,
        "model": model,
        "mode": "provider-backed",
        "auth_ready": False,
        "auth_status": "unsupported-provider",
        "auth_profile": None,
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
    profile = _find_openai_ready_profile()
    if profile is None:
        raise RuntimeError("Missing active OpenAI credentials for visible execution")

    state = get_provider_state(profile=profile, provider="openai")
    credentials_path = Path(str(state.get("credentials_path", "")))
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    api_key = str(credentials.get("api_key") or credentials.get("access_token") or "")
    if api_key:
        return api_key
    raise RuntimeError("Missing active OpenAI credentials for visible execution")


def _find_openai_ready_profile() -> str | None:
    profiles = ["default", *[item["profile"] for item in list_auth_profiles()]]
    seen: set[str] = set()
    for profile in profiles:
        if profile in seen:
            continue
        seen.add(profile)
        state = get_provider_state(profile=profile, provider="openai")
        if not state or state.get("status") != "active":
            continue
        credentials_path = Path(str(state.get("credentials_path", "")))
        if not credentials_path.exists():
            continue
        credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
        api_key = str(credentials.get("api_key") or credentials.get("access_token") or "")
        if api_key:
            return profile
    return None


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
