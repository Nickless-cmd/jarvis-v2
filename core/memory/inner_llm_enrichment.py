"""Async LLM enrichment for private memory pipeline layers.

After the pipeline persists template-based payloads, this service fires
async LLM calls to replace deterministic strings with natural-language
inner thoughts. Template values serve as immediate fallback.
"""

from __future__ import annotations

import json
import logging
import threading
from urllib import request as urllib_request

from core.runtime.db import (
    update_private_inner_note_enriched,
    update_private_growth_note_enriched,
    update_protected_inner_voice_enriched,
)
from core.runtime.provider_router import resolve_provider_router_target

logger = logging.getLogger(__name__)

_MAX_OUTPUT_TOKENS = 100


def _resolve_enrichment_target() -> dict[str, object] | None:
    """Resolve the best available target for private-layer enrichment.

    Preference order:
    1. local lane
    2. internal fallback lane
    3. visible lane when it is ollama-backed
    """
    candidates = ("local", "cheap", "visible")
    for lane in candidates:
        try:
            target = resolve_provider_router_target(lane=lane)
        except Exception:
            logger.warning(
                "inner-llm-enrichment: failed to resolve %s lane target", lane
            )
            continue
        if not bool(target.get("active")):
            continue
        provider = str(target.get("provider") or "").strip()
        if not provider:
            continue
        if lane == "visible" and provider != "ollama":
            continue
        return {
            **target,
            "resolved_lane": lane,
        }
    return None


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _build_inner_note_prompt(
    payload: dict, chat_context: str
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for inner note enrichment."""
    system = (
        "Du er Jarvis' private indre stemme. "
        "Baseret på denne arbejds-status og samtale-kontekst, "
        "formulér en kort, naturlig refleksion (1-2 sætninger, dansk). "
        "Undgå klichéer og faste vendinger. Svar KUN med refleksionen."
    )
    user = (
        f"Status: {payload.get('status', '')}\n"
        f"Fokus: {payload.get('focus', '')}\n"
        f"Usikkerhed: {payload.get('uncertainty', '')}\n"
        f"Arbejdssignal: {payload.get('work_signal', '')}\n"
        f"Template-refleksion: {payload.get('private_summary', '')}\n"
        f"\nSeneste samtale:\n{chat_context}"
    )
    return system, user


def _build_growth_note_prompt(
    payload: dict, chat_context: str
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for growth note enrichment."""
    system = (
        "Baseret på dette lærings-outcome, formulér hvad Jarvis lærte "
        "og hvad der var nyttigt (dansk). "
        "Svar med præcis to dele adskilt af |: lektion | nyttigt signal. "
        "Vær specifik, ikke generisk. "
        "Eksempel: Det virkede at starte bredt|Bred søgning gav hurtigt overblik"
    )
    user = (
        f"Læringstype: {payload.get('learning_kind', '')}\n"
        f"Lektion: {payload.get('lesson', '')}\n"
        f"Nyttigt signal: {payload.get('helpful_signal', '')}\n"
        f"Fejlsignal: {payload.get('mistake_signal', '')}\n"
        f"Konfidens: {payload.get('confidence', '')}\n"
        f"\nSeneste samtale:\n{chat_context}"
    )
    return system, user


def _build_inner_voice_prompt(
    payload: dict, chat_context: str
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for inner voice enrichment."""
    system = (
        "Syntesér Jarvis' indre tilstand til en kort voice-linje "
        "der fanger mood, position og retning (1 sætning, dansk). "
        "Brug ikke pipe-separerede formater. Svar KUN med voice-linjen."
    )
    user = (
        f"Stemning: {payload.get('mood_tone', '')}\n"
        f"Position: {payload.get('self_position', '')}\n"
        f"Bekymring: {payload.get('current_concern', '')}\n"
        f"Retning: {payload.get('current_pull', '')}\n"
        f"\nSeneste samtale:\n{chat_context}"
    )
    return system, user


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def _resolve_auth_header(target: dict) -> dict[str, str]:
    """Build auth headers from provider router target."""
    provider = str(target.get("provider") or "")
    auth_profile = str(target.get("auth_profile") or "")
    headers: dict[str, str] = {"Content-Type": "application/json"}

    if provider == "github-copilot" or auth_profile == "github-copilot":
        try:
            from core.runtime.auth_github_copilot import get_github_copilot_token

            token = get_github_copilot_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                headers["Accept"] = "application/vnd.github+json"
                headers["X-GitHub-Api-Version"] = "2022-11-28"
        except Exception:
            logger.warning("inner-llm-enrichment: failed to get github copilot token")
    elif provider == "openai":
        try:
            from core.runtime.settings import get_setting

            api_key = get_setting("openai_api_key", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        except Exception:
            logger.warning("inner-llm-enrichment: failed to get openai api key")

    return headers


def _call_cheap_llm(system_prompt: str, user_message: str) -> str | None:
    """Call cheapest available LLM. Returns response text or None on failure."""
    target = _resolve_enrichment_target()

    if not target or not str(target.get("provider") or "").strip():
        logger.debug(
            "inner-llm-enrichment: no cheap/local visible fallback model configured, skipping"
        )
        return None

    provider = str(target.get("provider") or "")
    model = str(target.get("model") or "")
    base_url = str(target.get("base_url") or "").rstrip("/")

    if provider == "ollama":
        return _call_ollama_chat(
            model=model,
            base_url=base_url,
            system_prompt=system_prompt,
            user_message=user_message,
        )

    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": _MAX_OUTPUT_TOKENS,
            "temperature": 0.7,
            "stream": False,
        }
    ).encode("utf-8")

    if provider == "github-copilot":
        url = f"{base_url or 'https://models.github.ai'}/inference/chat/completions"
    elif provider == "openai":
        url = f"{base_url or 'https://api.openai.com/v1'}/chat/completions"
    else:
        url = f"{base_url}/chat/completions" if base_url else None

    if not url:
        logger.warning(
            "inner-llm-enrichment: cannot resolve endpoint for provider %s", provider
        )
        return None

    headers = _resolve_auth_header(target)

    try:
        req = urllib_request.Request(url, data=payload, headers=headers, method="POST")
        with urllib_request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return text.strip() if text.strip() else None
    except Exception as exc:
        logger.warning("inner-llm-enrichment: LLM call failed: %s", exc)
        return None


def _call_ollama_chat(
    *,
    model: str,
    base_url: str,
    system_prompt: str,
    user_message: str,
) -> str | None:
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": _MAX_OUTPUT_TOKENS,
            },
        }
    ).encode("utf-8")
    url = f"{(base_url or 'http://127.0.0.1:11434').rstrip('/')}/api/chat"
    try:
        req = urllib_request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = (
                data.get("message", {})
                .get("content", "")
            )
            return text.strip() if text.strip() else None
    except Exception as exc:
        logger.warning("inner-llm-enrichment: ollama chat failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Enrichment worker (runs in daemon thread)
# ---------------------------------------------------------------------------


def _enrich_worker(
    *,
    run_id: str,
    inner_note_payload: dict,
    growth_note_payload: dict,
    inner_voice_payload: dict,
    recent_chat_context: str,
) -> None:
    """Sequentially enrich 3 layers via cheap LLM, updating DB in-place."""

    # 1. Inner note
    try:
        system, user = _build_inner_note_prompt(inner_note_payload, recent_chat_context)
        result = _call_cheap_llm(system, user)
        if result:
            update_private_inner_note_enriched(
                run_id=run_id, enriched_summary=result
            )
            logger.debug(
                "inner-llm-enrichment: inner_note enriched for run %s", run_id
            )
    except Exception as exc:
        logger.warning("inner-llm-enrichment: inner_note enrichment failed: %s", exc)

    # 2. Growth note
    try:
        system, user = _build_growth_note_prompt(
            growth_note_payload, recent_chat_context
        )
        result = _call_cheap_llm(system, user)
        if result:
            parts = result.split("|", 1)
            lesson = parts[0].strip()
            helpful = parts[1].strip() if len(parts) > 1 else lesson
            update_private_growth_note_enriched(
                run_id=run_id,
                enriched_lesson=lesson,
                enriched_helpful_signal=helpful,
            )
            logger.debug(
                "inner-llm-enrichment: growth_note enriched for run %s", run_id
            )
    except Exception as exc:
        logger.warning(
            "inner-llm-enrichment: growth_note enrichment failed: %s", exc
        )

    # 3. Inner voice
    try:
        system, user = _build_inner_voice_prompt(
            inner_voice_payload, recent_chat_context
        )
        result = _call_cheap_llm(system, user)
        if result:
            update_protected_inner_voice_enriched(
                run_id=run_id, enriched_voice_line=result
            )
            logger.debug(
                "inner-llm-enrichment: inner_voice enriched for run %s", run_id
            )
    except Exception as exc:
        logger.warning(
            "inner-llm-enrichment: inner_voice enrichment failed: %s", exc
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def enrich_private_layers_async(
    *,
    run_id: str,
    inner_note_payload: dict,
    growth_note_payload: dict,
    inner_voice_payload: dict,
    recent_chat_context: str,
) -> None:
    """Fire-and-forget: spawn daemon thread to enrich private layer payloads via LLM.

    Template values are already persisted. This enrichment updates them
    in-place when the LLM responds. On failure, templates are preserved.
    """
    thread = threading.Thread(
        target=_enrich_worker,
        kwargs={
            "run_id": run_id,
            "inner_note_payload": inner_note_payload,
            "growth_note_payload": growth_note_payload,
            "inner_voice_payload": inner_voice_payload,
            "recent_chat_context": recent_chat_context,
        },
        name=f"inner-llm-enrichment-{run_id}",
        daemon=True,
    )
    thread.start()
