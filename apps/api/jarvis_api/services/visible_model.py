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

from core.auth.profiles import get_provider_state, list_auth_profiles
from core.identity.visible_identity import load_visible_identity_prompt
from core.runtime.db import (
    recent_private_inner_notes,
    recent_private_growth_notes,
    recent_capability_invocations,
    recent_visible_runs,
    visible_session_continuity,
)
from core.runtime.settings import load_settings
from core.tools.workspace_capabilities import load_workspace_capabilities

READINESS_PROBE_TTL_SECONDS = 15
_READINESS_PROBE_CACHE: dict[tuple[str, str, str], dict[str, str | bool]] = {}
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


class VisibleModelStreamCancelled(RuntimeError):
    pass


def execute_visible_model(*, message: str, provider: str, model: str) -> VisibleModelResult:
    if provider == "openai":
        return _execute_openai_model(message=message, model=model)
    if provider == "phase1-runtime":
        return _execute_phase1_model(message=message, provider=provider, model=model)
    raise ValueError(f"Unsupported visible model provider: {provider}")


def stream_visible_model(
    *, message: str, provider: str, model: str, controller=None
) -> Iterator[VisibleModelDelta | VisibleModelStreamDone]:
    if provider == "openai":
        yield from _stream_openai_model(message=message, model=model, controller=controller)
        return

    result = execute_visible_model(message=message, provider=provider, model=model)
    for chunk in _chunk_text(result.text):
        yield VisibleModelDelta(delta=chunk)
    yield VisibleModelStreamDone(result=result)


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


def _execute_openai_model(*, message: str, model: str) -> VisibleModelResult:
    api_key = _load_openai_api_key()
    payload = {
        "model": model,
        "input": _build_visible_input(message),
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


def _stream_openai_model(
    *, message: str, model: str, controller=None
) -> Iterator[VisibleModelDelta | VisibleModelStreamDone]:
    api_key = _load_openai_api_key()
    payload = {
        "model": model,
        "stream": True,
        "input": _build_visible_input(message),
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
        "expires_at": (now + timedelta(seconds=READINESS_PROBE_TTL_SECONDS)).isoformat(),
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


def _build_visible_input(message: str) -> list[dict]:
    instruction = _visible_system_instruction()
    if not instruction:
        return [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": message}],
            }
        ]
    return [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": instruction}],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": message}],
        },
    ]


def _visible_system_instruction() -> str | None:
    parts = [
        load_visible_identity_prompt(),
        _visible_session_continuity_instruction(),
        _visible_continuity_instruction(),
        _capability_continuity_instruction(),
        _visible_work_instruction(),
        _private_support_signal_instruction(),
        _growth_support_signal_instruction(),
        _capability_instruction(),
    ]
    text = "\n\n".join(part for part in parts if part)
    return text or None


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

    lines.append("Use this only as short recent continuity context, not as transcript memory.")
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

    lines.append("Use this only as short recent capability continuity, not as tool history.")
    return "\n".join(lines)


def _visible_work_instruction() -> str | None:
    from apps.api.jarvis_api.services.visible_runs import get_visible_selected_work_item

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
        parts.append(
            f"preview={selected_work_item['selected_user_message_preview']}"
        )
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
        f'- {item["capability_id"]}: {item.get("name", "")}'
        for item in runnable[:8]
    ]
    return "\n".join(
        [
            "Visible lane capability rule:",
            "Use a workspace capability only by replying with exactly one line in this exact form and nothing else:",
            '<capability-call id="capability_id" />',
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


def _calculate_openai_cost_usd(*, model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = OPENAI_TEXT_PRICING_PER_1M_TOKENS.get(model.strip().lower())
    if pricing is None:
        return 0.0

    input_rate, output_rate = pricing
    total = (
        Decimal(int(input_tokens)) * input_rate / Decimal(1_000_000)
        + Decimal(int(output_tokens)) * output_rate / Decimal(1_000_000)
    )
    return float(total.quantize(Decimal("0.00000001")))


def _chunk_text(text: str, size: int = 48) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


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
