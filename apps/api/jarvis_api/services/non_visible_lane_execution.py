from __future__ import annotations

import json
from pathlib import Path
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
    status = _lane_status(target)
    return {
        "active": True,
        "lane": lane,
        "consumer": "provider-router-coding-lane",
        "status": status,
        "can_execute": status == "ready",
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
