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
    update_private_retained_memory_record_enriched,
    update_protected_inner_voice_enriched,
)
from core.runtime.provider_router import resolve_provider_router_target

logger = logging.getLogger(__name__)

# Bumped from 100 → 300 because local thinking-models (gemma4:e2b
# etc.) burn the entire token budget on the `thinking` field and
# return empty `content` if num_predict is too low. 300 leaves room
# for both the chain-of-thought and a short final answer.
_MAX_OUTPUT_TOKENS = 300


def _sanitize_private_inner_note_enrichment(text: str) -> str:
    cleaned = _sanitize_private_layer_text(text, max_len=200)
    return cleaned


def _sanitize_private_growth_note_enrichment(text: str) -> tuple[str, str] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    parts = raw.split("|", 1)
    if len(parts) != 2:
        return None
    lesson = _sanitize_private_layer_text(parts[0], max_len=160)
    helpful = _sanitize_private_layer_text(parts[1], max_len=160)
    if not lesson or not helpful:
        return None
    return lesson, helpful


def _sanitize_inner_voice_enrichment(text: str) -> str:
    """Reuse inner-voice sanitization before writing enriched voice lines."""
    try:
        from apps.api.jarvis_api.services.inner_voice_daemon import _sanitize_inner_voice_text

        return _sanitize_inner_voice_text(text, max_len=200)
    except Exception:
        return str(text or "").strip()[:200]


def _sanitize_private_layer_text(text: str, *, max_len: int = 200) -> str:
    cleaned = str(text or "").replace("\r", "\n").strip()
    if not cleaned:
        return ""
    for token in ("* ", "**", "__", "`", "#"):
        cleaned = cleaned.replace(token, " ")
    cleaned = " ".join(cleaned.split()).strip(" -:|")
    lowered = cleaned.lower()
    banned_prefixes = (
        "attempt ",
        "draft ",
        "version ",
        "refining for",
        "rewriting for",
        "a bit too",
        "too technical",
        "too long",
    )
    if any(lowered.startswith(prefix) for prefix in banned_prefixes):
        return ""
    return cleaned[:max_len]


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
        "You are Jarvis' private inner voice. "
        "Based on this work-status and chat context, "
        "write a short, natural reflection (1-2 sentences, English). "
        "Avoid cliches, template-like phrasing, labels, and editorial notes. "
        "Use only the given signals. Reply ONLY with the reflection."
    )
    user = (
        f"Status: {payload.get('status', '')}\n"
        f"Focus: {payload.get('focus', '')}\n"
        f"Uncertainty: {payload.get('uncertainty', '')}\n"
        f"Work signal: {payload.get('work_signal', '')}\n"
        f"Template reflection: {payload.get('private_summary', '')}\n"
        f"\nRecent chat:\n{chat_context}"
    )
    return system, user


def _build_growth_note_prompt(
    payload: dict, chat_context: str
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for growth note enrichment."""
    system = (
        "Based on this learning outcome, write what Jarvis learned "
        "and what was useful (English). "
        "Reply with exactly two parts separated by |: lesson | helpful signal. "
        "Be specific, not generic, and avoid labels or editorial notes. "
        "Example: Starting broad helped first|The broad search gave quick orientation"
    )
    user = (
        f"Learning kind: {payload.get('learning_kind', '')}\n"
        f"Lesson: {payload.get('lesson', '')}\n"
        f"Helpful signal: {payload.get('helpful_signal', '')}\n"
        f"Mistake signal: {payload.get('mistake_signal', '')}\n"
        f"Confidence: {payload.get('confidence', '')}\n"
        f"\nRecent chat:\n{chat_context}"
    )
    return system, user


def _build_inner_voice_prompt(
    payload: dict, chat_context: str
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for inner voice enrichment."""
    system = (
        "Syntesér Jarvis' indre tilstand til en kort voice-linje "
        "der fanger mood, position og retning (1 sætning, dansk). "
        "Skriv selve voice-linjen, ikke redaktionelle noter om længde, tone, flow, mood eller versioner. "
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
            from core.auth.openai_oauth import get_openai_bearer_token

            api_key = get_openai_bearer_token(profile=auth_profile or "default")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        except Exception:
            logger.warning("inner-llm-enrichment: failed to get openai bearer token")

    return headers


def call_cheap_llm(system_prompt: str, user_message: str) -> str | None:
    """Public alias for _call_cheap_llm so other services can reuse it.

    Same behaviour: tries local lane → cheap lane → visible-ollama
    fallback. Returns text or None on failure. Bounded output tokens.
    """
    return _call_cheap_llm(system_prompt, user_message)


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
            message = data.get("message", {}) or {}
            text = str(message.get("content") or "").strip()
            if text:
                return text
            # Thinking-model fallback: when num_predict is exhausted on
            # the chain-of-thought, content can come back empty even
            # though the model produced something useful in `thinking`.
            # Take the last sentence of `thinking` as a degraded answer
            # rather than dropping the response entirely.
            thinking = str(message.get("thinking") or "").strip()
            if thinking:
                # Pick the last non-trivial sentence
                sentences = [
                    s.strip()
                    for s in thinking.replace("\n", " ").split(".")
                    if len(s.strip()) > 4
                ]
                if sentences:
                    return sentences[-1]
            return None
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
            cleaned_result = _sanitize_private_inner_note_enrichment(result)
            if not cleaned_result:
                cleaned_result = str(inner_note_payload.get("private_summary") or "").strip()[:200]
            update_private_inner_note_enriched(
                run_id=run_id, enriched_summary=cleaned_result
            )
            logger.debug(
                "inner-llm-enrichment: inner_note enriched for run %s", run_id
            )
    except Exception as exc:
        logger.warning("inner-llm-enrichment: inner_note enrichment failed: %s", exc)

    # 2. Growth note
    enriched_lesson: str | None = None
    try:
        system, user = _build_growth_note_prompt(
            growth_note_payload, recent_chat_context
        )
        result = _call_cheap_llm(system, user)
        if result:
            parsed = _sanitize_private_growth_note_enrichment(result)
            if parsed is None:
                lesson = str(growth_note_payload.get("lesson") or "").strip()[:160]
                helpful = str(growth_note_payload.get("helpful_signal") or "").strip()[:160]
            else:
                lesson, helpful = parsed
            enriched_lesson = lesson
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

    # 2b. Retained memory — use enriched lesson so retained_value reflects real content
    if enriched_lesson:
        try:
            update_private_retained_memory_record_enriched(
                run_id=run_id, enriched_value=enriched_lesson
            )
            logger.debug(
                "inner-llm-enrichment: retained_memory enriched for run %s", run_id
            )
        except Exception as exc:
            logger.warning(
                "inner-llm-enrichment: retained_memory enrichment failed: %s", exc
            )

    # 3. Inner voice
    try:
        system, user = _build_inner_voice_prompt(
            inner_voice_payload, recent_chat_context
        )
        result = _call_cheap_llm(system, user)
        if result:
            cleaned_result = _sanitize_inner_voice_enrichment(result)
            if not cleaned_result:
                cleaned_result = str(inner_voice_payload.get("voice_line") or "").strip()[:200]
            update_protected_inner_voice_enriched(
                run_id=run_id, enriched_voice_line=cleaned_result
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
