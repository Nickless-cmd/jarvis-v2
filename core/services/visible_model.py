from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)
from datetime import UTC, datetime
from typing import Iterator

from urllib import error as urllib_error
from urllib import request as urllib_request

from core.auth.copilot_oauth import get_copilot_oauth_truth
from core.auth.copilot_session import get_copilot_session_token  # noqa: F401
from core.services.cheap_provider_runtime import (
    list_provider_models as list_live_provider_models,
    supported_cheap_providers,
)
from core.services.non_visible_lane_execution import (  # noqa: F401
    _github_copilot_request_headers,
    _load_github_copilot_token,
    _post_github_copilot_chat_completion,
    fetch_github_copilot_models,
)
from core.services.prompt_contract import build_visible_chat_prompt_assembly
from core.runtime.provider_router import resolve_provider_router_target
from core.runtime.settings import load_settings
from core.runtime.provider_router import load_provider_router_registry

# Boy-scout split (2026-07-07): value classes, observe helpers, SSE/util helpers,
# prompt/continuity builders, the per-provider adapters (openai/codex/copilot/
# openai-compat + ollama) and auth/probe/readiness helpers were extracted to
# sibling modules and are re-exported here so ``core.services.visible_model``
# stays the single import surface (blast 37). CRITICAL: the value classes are
# re-exported verbatim (SAME class objects) because never-reloaded consumers
# isinstance-check them — see the sibling docstrings + tests/conftest.py
# class-identity anchor. The adapter modules import the two prompt-input builders
# below from THIS module, so they are imported at the BOTTOM of this file (after
# those builders are defined) to avoid an import cycle.
from core.services.visible_model_types import (  # noqa: F401
    VisibleModelDelta,
    VisibleModelRateLimited,
    VisibleModelResult,
    VisibleModelStreamCancelled,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)
from core.services.visible_model_observe import (  # noqa: F401
    _observe_content_empty_thinking_fallback,
    _observe_malformed_stream_payload,
    _observe_visible_provider_error,
    _strip_thinking_delimiters,
)
from core.services.visible_model_sse import (  # noqa: F401
    OPENAI_TEXT_PRICING_PER_1M_TOKENS,
    _calculate_openai_cost_usd,
    _chat_completion_stream_is_terminal,
    _chunk_text,
    _estimate_tokens,
    _extract_chat_completion_delta,
    _extract_chat_completion_reasoning,
    _finalize_openai_tool_calls,
    _iter_sse_events,
    _merge_openai_tool_call_deltas,
    _parse_utc,
)
from core.services.visible_model_prompt import (  # noqa: F401
    _capability_continuity_instruction,
    _capability_instruction,
    _growth_support_signal_instruction,
    _private_support_signal_instruction,
    _retained_memory_support_signal_instruction,
    _self_model_support_signal_instruction,
    _temporal_support_signal_instruction,
    _visible_continuity_instruction,
    _visible_session_continuity_instruction,
    _visible_work_instruction,
    visible_capability_continuity_summary,
    visible_continuity_summary,
    visible_session_continuity_summary,
)



# ── WS5: deepseek-v4-pro cost-gate (owner + visible-lane only) ──────────────
# v4-pro er ~3× dyrere pr. token end v4-flash. Politik (spec 2026-07-13, WS5):
# pro må KUN bruges i visible lane, KUN for owner (Bjørn), og KUN når runtime-
# kill-switch-flaget ``visible_v4pro_enabled`` er tændt. Alt andet → v4-flash.
# FAIL-SAFE: default = pro IKKE brugt (nedgradér til flash), så kost aldrig kan
# lække — hverken ved manglende flag, ikke-owner-tur, eller læsefejl.
_V4PRO_ENABLE_FLAG = "visible_v4pro_enabled"
_V4PRO_FALLBACK_MODEL = "deepseek-v4-flash"


def _model_is_deepseek_pro_tier(model: str) -> bool:
    """True hvis modellen er den dyre deepseek-pro/reasoner-pro-tier.

    Matcher ``deepseek-v4-pro`` og enhver pro-variant, men IKKE ``deepseek-v4-flash``,
    ``deepseek-chat`` eller ``deepseek-reasoner`` (sidstnævnte er en flash-thinking-alias,
    ikke pro-tier — jf. WS4)."""
    normalized = str(model or "").strip().lower()
    if not normalized:
        return False
    return "pro" in normalized


def _turn_is_owner_scoped() -> bool:
    """Er den aktuelle tur owner-scoped (Bjørn)? Self-safe → False ved fejl."""
    try:
        from core.identity.workspace_context import current_user_id
        from core.services.security_guard import is_owner
        uid = current_user_id()
        return bool(uid) and is_owner(uid)
    except Exception:
        return False


def gate_visible_model_tier(
    provider: str, model: str, *, is_owner: bool | None = None
) -> str:
    """WS5-gate: nedgradér deepseek-v4-pro → v4-flash medmindre (a) kill-switch-
    flaget er tændt OG (b) turen er owner-scoped. Fail-safe: enhver usikkerhed
    (flag af, ikke-owner, læsefejl) → flash. Returnerer den (evt. nedgraderede)
    model. Ikke-deepseek eller ikke-pro-tier passerer uændret igennem."""
    if str(provider or "").strip().lower() != "deepseek":
        return model
    if not _model_is_deepseek_pro_tier(model):
        return model

    try:
        from core.runtime.db_core import get_runtime_state_bool
        flag_on = get_runtime_state_bool(_V4PRO_ENABLE_FLAG, False)
    except Exception:
        flag_on = False

    owner = _turn_is_owner_scoped() if is_owner is None else bool(is_owner)

    if flag_on and owner:
        return model

    logger.info(
        "WS5 v4-pro gate: nedgraderer %s → %s (flag_on=%s owner=%s)",
        model, _V4PRO_FALLBACK_MODEL, flag_on, owner,
    )
    return _V4PRO_FALLBACK_MODEL


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


def execute_visible_model(
    *, message: str, provider: str, model: str, session_id: str | None = None,
    thinking_mode: str | None = None,
) -> VisibleModelResult:
    # WS5: enforce v4-pro cost-gate at the execution seam (fail-safe → flash).
    model = gate_visible_model_tier(provider, model)
    if provider == "openai":
        return _execute_openai_model(
            message=message, model=model, session_id=session_id
        )
    if provider == "openai-codex":
        return _execute_openai_codex_model(
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
            _extra = None
            if provider == "deepseek" and thinking_mode:
                from core.services.cheap_provider_runtime_adapters import (
                    deepseek_request_for_thinking_mode,
                )
                model, _extra = deepseek_request_for_thinking_mode(
                    model, thinking_mode
                )
            result, _tool_calls = _run_openai_compatible_visible(
                provider=provider,
                model=model,
                message=message,
                session_id=session_id,
                extra_body=_extra,
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
    # WS5: enforce v4-pro cost-gate at the streaming seam (fail-safe → flash).
    model = gate_visible_model_tier(provider, model)
    if provider == "openai":
        yield from _stream_openai_model(
            message=message,
            model=model,
            session_id=session_id,
            controller=controller,
        )
        return
    if provider == "openai-codex":
        yield from _stream_openai_codex_model(
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

    # openai-compat providers (deepseek, opencode, groq, openrouter, nvidia-nim,
    # mistral, sambanova) — native SSE streaming via /chat/completions.
    # Yields tokens as they arrive and surfaces tool_calls before the done
    # event so working_step reaches the user instantly.
    from core.services.cheap_provider_runtime import _OPENAI_COMPATIBLE_PROVIDERS
    if provider in _OPENAI_COMPATIBLE_PROVIDERS:
        yield from _stream_openai_compatible_model(
            provider=provider,
            model=model,
            message=message,
            session_id=session_id,
            controller=controller,
            thinking_mode=thinking_mode,
        )
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
                # Historik-ekspansion (paste-store): en HISTORISK besked kan bære en
                # [paste:<id>]-reference (composer-eksternalisering) — ekspandér den til
                # fuld tekst så modellen ser hvad brugeren pastede (default ON, degradér
                # ved ukendt id, aldrig kast). Kun bruger-beskeder bærer paste-refs.
                if role == "user" and "[paste:" in content:
                    try:
                        from core.services.paste_store import project_paste_for_model
                        content = project_paste_for_model(content)
                    except Exception:
                        pass
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

    # Cache-fix (2026-06-13, lever #3): flyt HELE den per-turn-dynamiske hale UD af
    # system-beskeden og ned på den SIDSTE bruger-besked. prompt_contract markerer
    # halen (finitude/Sessions-alder, wakeup-digest, kausal-mønstre, counterfactuals,
    # subagent, rum-entiteter, time_pin) med DYNAMIC_TAIL_SENTINEL. Alt efter den
    # varierer per turn; lå det i system-beskeden cap'ede det cachen FØR historikken.
    # Flyttet til den nye bruger-tur (altid en miss) → [system + historik] bliver én
    # stor stabil cachebar prefix. Jarvis ser de live-felter lige før sit svar.
    if items and items[0].get("role") == "system" and items[0].get("content"):
        try:
            from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL
            _sys_text = str(items[0]["content"][0].get("text", ""))
            _sidx = _sys_text.find(DYNAMIC_TAIL_SENTINEL)
            if _sidx != -1:
                _tail_block = _sys_text[_sidx + len(DYNAMIC_TAIL_SENTINEL):].strip()
                items[0]["content"][0]["text"] = _sys_text[:_sidx].rstrip()
                if _tail_block:
                    for _it in reversed(items):
                        if _it.get("role") == "user" and _it.get("content"):
                            _ut = str(_it["content"][0].get("text", ""))
                            _it["content"][0]["text"] = (
                                (_ut.rstrip() + "\n\n" + _tail_block) if _ut else _tail_block
                            )
                            break
        except Exception:
            pass

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
                msg_dict: dict[str, str] = {"role": role, "content": content}
                # Thinking-mode replay (Deepseek v4-flash/v4-pro): prior
                # assistant turns must carry reasoning_content if produced.
                # _build_structured_transcript_messages threader feltet ind
                # på dict'en når det findes i chat_messages-tabellen.
                if role == "assistant":
                    r_content = str(tmsg.get("reasoning_content") or "").strip()
                    if r_content:
                        msg_dict["reasoning_content"] = r_content
                messages.append(msg_dict)
    # Hallucination guard: injectér memory for faktuelle spørgsmål
    try:
        from core.services.hallucination_guard import inject_memory_into_prompt
        messages = inject_memory_into_prompt(message, messages)
    except Exception:
        logger.warning("hallucination_guard inject failed", exc_info=True)

    messages.append({"role": "user", "content": message})

    # Cache-fix (2026-06-30): port DYNAMIC_TAIL_SENTINEL-splittet fra
    # _build_visible_input til DENNE builder. Den betjener ALLE openai-compat
    # visible-providere (deepseek/groq/openrouter/…). Uden splittet sad HELE
    # den per-tur-dynamiske hale (recall, mood, continuity, time_pin, anchor)
    # inde i system-beskeden → brød DeepSeek-cachen ~5-15k tokens inde og fik
    # hele historikken til at misse (målt 2-10% hit i produktion vs 92% potentiale).
    # Flyt halen efter sentinel'en ud på den SIDSTE bruger-besked → [system +
    # tools + historik] bliver byte-stabil og cachebar; kun halen+turen misser.
    if messages and messages[0].get("role") == "system":
        try:
            from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL
            _sys_text = str(messages[0].get("content") or "")
            _sidx = _sys_text.find(DYNAMIC_TAIL_SENTINEL)
            if _sidx != -1:
                _tail_block = _sys_text[_sidx + len(DYNAMIC_TAIL_SENTINEL):].strip()
                messages[0]["content"] = _sys_text[:_sidx].rstrip()
                if _tail_block:
                    for _it in reversed(messages):
                        if _it.get("role") == "user":
                            _ut = str(_it.get("content") or "")
                            _it["content"] = (
                                (_ut.rstrip() + "\n\n" + _tail_block) if _ut else _tail_block
                            )
                            break
        except Exception:
            pass

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


# ── Bottom re-exports (boy-scout split, 2026-07-07) ─────────────────────────
# The adapter modules import ``_build_visible_input`` /
# ``_build_visible_chat_messages_for_github`` from THIS module. Import them here,
# at the bottom, so those builders are already defined when the adapter modules
# execute their top-level `from core.services.visible_model import ...`. Symbols
# are re-exported so ``core.services.visible_model`` stays the single import
# surface (blast 37) — external callers keep importing them from here.
from core.services.visible_model_ollama import (  # noqa: E402,F401
    _OLLAMA_FIRST_BYTE_BUDGET_S,
    _OLLAMA_INTER_BYTE_BUDGET_S,
    _VISIBLE_OLLAMA_NUM_CTX,
    _VISIBLE_OLLAMA_NUM_PREDICT,
    _apply_thinking_mode,
    _apply_visible_ollama_options,
    _build_ollama_prompt,
    _execute_ollama_model,
    _probe_ollama_visible_target,
    _stream_ollama_model,
)
from core.services.visible_model_adapters import (  # noqa: E402,F401
    GITHUB_VISIBLE_COOLDOWN_TTL_MINUTES,
    READINESS_PROBE_TTL_SECONDS,
    _GITHUB_VISIBLE_COOLDOWN_UNTIL,
    _READINESS_PROBE_CACHE,
    _build_openai_codex_visible_prompt,
    _ensure_github_copilot_model_available,
    _execute_github_copilot_visible_model,
    _execute_openai_codex_model,
    _execute_openai_model,
    _execute_phase1_model,
    _extract_output_text,
    _get_github_visible_cooldown_status,
    _github_model_matches_requested,
    _is_github_visible_cooled_down,
    _load_openai_api_key,
    _load_openai_api_key_for_profile,
    _normalize_github_models_model_id,
    _openai_profile_status,
    _post_openai_responses,
    _probe_github_copilot_model,
    _probe_openai_model,
    _provider_profile_status,
    _provider_router_config,
    _resolve_copilot_profile,
    _resolve_openai_profile,
    _run_openai_compatible_visible,
    _set_github_visible_cooldown,
    _stream_github_copilot_model,
    _stream_openai_codex_model,
    _stream_openai_compatible_model,
    _stream_openai_model,
    visible_execution_readiness,
)
