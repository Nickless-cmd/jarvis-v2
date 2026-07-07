"""Pure leaf helpers extracted from ``heartbeat_runtime``.

Behavior-preserving split (Boy-Scout rule): these functions are self-contained
parsers/formatters/detectors with no calls to other heartbeat-runtime functions
and no dependency on heartbeat-runtime module-global mutable state. They are
re-exported from :mod:`core.services.heartbeat_runtime` so existing imports and
test monkeypatch seams (``heartbeat_runtime.<name>``) keep working unchanged.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib import error as urllib_error

logger = logging.getLogger("uvicorn.error")

# Shared key/value line matcher used by heartbeat decision parsing.
_KEY_LINE_RE = re.compile(r"^\s*([A-Za-z][A-Za-z ]+):\s*(.+?)\s*$")


def _log_debug(message: str, **fields: object) -> None:
    detail = " ".join(
        f"{key}={json.dumps(value, ensure_ascii=False)}"
        for key, value in fields.items()
    )
    logger.debug("%s%s", message, f" | {detail}" if detail else "")


def _hours_since_iso(value: object) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - parsed.astimezone(UTC)
    return max(delta.total_seconds() / 3600.0, 0.0)


def _detect_visible_language() -> str:
    """Detect the language Bjørn is currently using in webchat.

    Returns 'da' for Danish, 'en' for English, or 'da' as a default.
    Used so heartbeat pings match the language the user is currently
    speaking, instead of being hardcoded to one or the other.
    """
    try:
        from core.services.chat_sessions import (
            list_chat_sessions,
            recent_chat_session_messages,
        )

        sessions = list_chat_sessions()
        if not sessions:
            return "da"
        session_id = str((sessions[0] or {}).get("id") or "").strip()
        if not session_id:
            return "da"
        messages = recent_chat_session_messages(session_id, limit=8)
        # Find most recent user message
        for msg in reversed(messages):
            if str(msg.get("role") or "") != "user":
                continue
            text = str(msg.get("content") or "").lower()
            if not text:
                continue
            # Danish marker words / characters
            danish_markers = (
                "æ",
                "ø",
                "å",
                " ikke ",
                " jeg ",
                " du ",
                " det ",
                " det ",
                " og ",
                " er ",
                " har ",
                " skal ",
                " kan ",
                " som ",
                " fra ",
                " til ",
                " med ",
                " hvad ",
                " hvor ",
                " hvorfor ",
            )
            if any(marker in text for marker in danish_markers):
                return "da"
            return "en"
    except Exception:
        pass
    return "da"


def _classify_heartbeat_execution_exception(exc: Exception) -> str:
    message = str(exc).strip().lower()
    if message.startswith("ollama-http-error"):
        return "http-error"
    if "request-failed" in message:
        return "request-failed"
    return "runtime-failed"


def _http_error_detail(exc: urllib_error.HTTPError) -> str:
    try:
        payload = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        payload = ""
    if not payload:
        return "no-body"
    return payload[:200]


def _parse_heartbeat_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = _KEY_LINE_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        values[key] = value
    return values


def _parse_bool(
    value: str | None,
    *,
    default: bool,
    truthy: set[str] | None = None,
) -> bool:
    if value is None:
        return default
    lowered = str(value).strip().lower()
    if truthy is None:
        truthy = {"true", "yes", "1", "on", "enabled"}
    if lowered in truthy:
        return True
    if lowered in {"false", "no", "0", "off", "disabled"}:
        return False
    return default


def _parse_int(value: str | None, *, default: int, minimum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return default
    return max(parsed, minimum)


def _extract_json_object(text: str) -> str:
    # Scan for ALL balanced top-level {...} objects and return the LAST one.
    # Reasoning models (glm/deepseek) emit thinking-præambel — som kan indeholde
    # løse '{' (kode/eksempler) — FØR det egentlige beslutnings-objekt. Den gamle
    # "første '{' + brace-match" startede så på et forkert objekt eller ramte
    # "Unterminated". Det egentlige svar kommer sidst → returnér sidste komplette
    # balancerede objekt (29. jun, sammen med token-cap-hævningen).
    objects: list[str] = []
    depth = 0
    obj_start = -1
    for index, char in enumerate(text):
        if char == "{":
            if depth == 0:
                obj_start = index
            depth += 1
        elif char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and obj_start >= 0:
                    objects.append(text[obj_start : index + 1])
                    obj_start = -1
    if objects:
        return objects[-1]
    if text.find("{") < 0:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    raise json.JSONDecodeError("Unterminated JSON object", text, max(text.find("{"), 0))


def _extract_openai_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") == "output_text":
                parts.append(str(content.get("text", "")))
    text = "".join(parts).strip()
    if not text:
        raise RuntimeError("Heartbeat OpenAI execution returned no output_text")
    return text


def _extract_openrouter_text(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Heartbeat OpenRouter execution returned no choices")
    message = choices[0].get("message") or {}
    text = str(message.get("content") or message.get("reasoning_content") or "").strip()
    if not text:
        raise RuntimeError("Heartbeat OpenRouter execution returned no content")
    return text


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _estimate_tokens(text: str) -> int:
    return max(1, len((text or "").split()))


def _value_drifted(expected: object, actual: object) -> bool:
    """True if expected ≠ actual under tolerant comparison.

    Bools are compared as bools (0/False, 1/True are equal). Other types
    are compared as strings to avoid false positives between e.g.
    ``""`` and ``None`` which both represent "no value" in the DB row.
    """
    if isinstance(expected, bool) or isinstance(actual, bool):
        return bool(expected) != bool(actual)
    return str(expected if expected is not None else "") != str(
        actual if actual is not None else ""
    )


__all__ = [
    "_log_debug",
    "_hours_since_iso",
    "_detect_visible_language",
    "_classify_heartbeat_execution_exception",
    "_http_error_detail",
    "_parse_heartbeat_key_values",
    "_parse_bool",
    "_parse_int",
    "_extract_json_object",
    "_extract_openai_text",
    "_extract_openrouter_text",
    "_parse_dt",
    "_estimate_tokens",
    "_value_drifted",
    "_KEY_LINE_RE",
]
