"""Arko Studio adapter for cheap-lane inference.

Why Arko: Groq's free tier rate-limits, OllamaFreeAPI is occasionally
unstable. Arko (https://arko.arcaelas.com) is a third-party agent platform
with a stateless inference path we can use as another fallback for the
cheap lane. Same shape as ollamafreeapi_provider — translate Jarvis's
prompt/messages into Arko's REST call, return an Ollama-compatible
response dict so the rest of the cheap-lane runtime doesn't need to
care which backend served the call.

Notes:
- Uses an agent we created with memory=false — every call is isolated.
- The agent_id and API key live in runtime.json. Never hardcode.
- Arko's /v3/messages endpoint returns either NDJSON streaming or a
  single JSON object when ``stream: false``. We use stream:false because
  cheap-lane consumers want the full text back, not deltas.
- Rate limits are not documented; in practice the service has been
  responsive in initial tests. Add backoff if we start seeing 429s.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://arko.arcaelas.com"
_DEFAULT_TIMEOUT = 60


def _config() -> tuple[str, str, str] | None:
    """Pull base_url, api_key, agent_id from runtime.json. Returns None
    if any are missing — caller treats that as 'provider not configured'."""
    try:
        from core.runtime.secrets import read_runtime_key
        base_url = (read_runtime_key("arko_base_url") or _DEFAULT_BASE_URL).rstrip("/")
        api_key = read_runtime_key("arko_api_key") or ""
        agent_id = read_runtime_key("arko_cheap_agent_id") or ""
    except Exception as exc:
        logger.debug("arko: config load failed: %s", exc)
        return None
    if not api_key or not agent_id:
        return None
    return base_url, api_key, agent_id


def collapse_messages_to_prompt(messages: list[dict[str, object]] | None) -> str:
    """Flatten OpenAI-style messages into one labelled prompt for Arko.

    Arko's stateless agent takes a single ``content`` string. We preserve
    role labels in plain text so the model can follow turn structure.
    """
    parts: list[str] = []
    for item in messages or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "user").strip() or "user"
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        parts.append(f"{role.upper()}: {content}")
    return "\n\n".join(parts).strip()


def call_arko(
    *,
    messages: list[dict[str, object]] | None = None,
    prompt: str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Send a message to the Arko cheap-lane agent and return an
    Ollama-compatible response shape.

    Raises RuntimeError when the provider is unconfigured or the API
    call fails — the cheap-lane router will catch that and fall through
    to the next provider in line.
    """
    cfg = _config()
    if cfg is None:
        raise RuntimeError("arko provider not configured (missing api_key or agent_id)")
    base_url, api_key, agent_id = cfg

    prompt_text = (prompt or "").strip()
    if not prompt_text:
        prompt_text = collapse_messages_to_prompt(messages)
    if not prompt_text:
        raise ValueError("call_arko requires prompt or messages")

    started = time.time_ns()
    content = ""
    last_body: dict[str, Any] = {}
    # Retry once if Arko returns success but no assistant content — we've
    # seen this happen sporadically on the first call after an idle period.
    for attempt in (1, 2):
        payload = {
            "aid": agent_id,
            "content": prompt_text,
            "stream": False,
        }
        req = urllib.request.Request(
            f"{base_url}/v3/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"arko HTTP {exc.code}: {detail}") from exc
        except Exception as exc:
            raise RuntimeError(f"arko call failed: {exc}") from exc

        last_body = body
        if not body.get("success"):
            raise RuntimeError(f"arko error: {body.get('message') or body!r}")

        msgs = body.get("data", {}).get("messages", [])
        assistant_msg = next(
            (m for m in reversed(msgs) if m.get("role") == "assistant"),
            None,
        )
        content = str(assistant_msg.get("content") or "").strip() if assistant_msg else ""
        if content:
            break
        logger.info("arko: empty content on attempt %d, retrying", attempt)

    if not content:
        raise RuntimeError(f"arko returned empty assistant content after retry: {last_body!r}")

    return {
        "message": {"content": content},
        "done": True,
        "total_duration": max(0, time.time_ns() - started),
    }


def is_configured() -> bool:
    """Cheap probe so the cheap-lane router can skip Arko silently when
    the user hasn't set it up."""
    return _config() is not None
