"""Bounded, redacted payload capture for Cheap Lane invocations."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_cheap_lane_control import record_redacted_payload
from core.runtime.db_cheap_provider import _ensure_invocation_schema
from core.runtime.db_core import connect

_MAX_PAYLOAD_BYTES = 64 * 1024
_DEFAULT_RETENTION_DAYS = 7
_REDACTED = "[REDACTED]"
_SECRET_FIELDS = {
    "authorization", "proxy-authorization", "cookie", "set-cookie",
    "api_key", "apikey", "api-key", "secret", "secret_key", "password",
    "passwd", "token", "access_token", "refresh_token", "client_secret",
}
_PREFIX_PATTERN = re.compile(
    r"(?i)\b(?:jvs-|sk-|gh[pousr]_|glpat-|xox[baprs]-|AIza)"
    r"[A-Za-z0-9._+/=-]{8,}"
)


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redacted_count: int
    truncated: bool = False


def _configured_patterns() -> list[str]:
    try:
        from core.runtime.settings import load_settings

        value = load_settings().extra.get("cheap_lane_sensitive_patterns", [])
        return [str(item) for item in value] if isinstance(value, list) else []
    except Exception:
        return []


def _retention_days() -> int:
    try:
        from core.runtime.settings import load_settings

        value = int(load_settings().extra.get(
            "cheap_lane_payload_retention_days", _DEFAULT_RETENTION_DAYS
        ))
        return max(1, value)
    except Exception:
        return _DEFAULT_RETENTION_DAYS


def _redact_fields(value: object) -> tuple[object, int]:
    if isinstance(value, dict):
        result: dict[str, object] = {}
        count = 0
        for key, item in value.items():
            name = str(key)
            if name.casefold() in _SECRET_FIELDS:
                result[name] = _REDACTED
                count += 1
            else:
                result[name], nested = _redact_fields(item)
                count += nested
        return result, count
    if isinstance(value, (list, tuple)):
        result_list: list[object] = []
        count = 0
        for item in value:
            cleaned, nested = _redact_fields(item)
            result_list.append(cleaned)
            count += nested
        return result_list, count
    return value, 0


def _bounded_utf8(text: str) -> tuple[str, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= _MAX_PAYLOAD_BYTES:
        return text, False
    suffix = "\n[TRUNCATED]"
    budget = _MAX_PAYLOAD_BYTES - len(suffix.encode("utf-8"))
    clipped = encoded[:budget].decode("utf-8", errors="ignore")
    return clipped + suffix, True


def redact_payload(value: object) -> RedactionResult:
    """Return a JSON-safe or textual payload with secrets removed and size bounded."""
    cleaned, count = _redact_fields(value)
    text = cleaned if isinstance(cleaned, str) else json.dumps(
        cleaned, ensure_ascii=False, sort_keys=True, default=str
    )
    from core.services.secret_redaction import redact as redact_known_secrets

    known_redacted = redact_known_secrets(text)
    if known_redacted != text:
        count += 1
    text = _PREFIX_PATTERN.sub(_REDACTED, known_redacted)
    if text != known_redacted:
        count += 1
    for configured in _configured_patterns():
        try:
            text, replacements = re.subn(configured, _REDACTED, text)
        except re.error as exc:
            raise ValueError("invalid configured payload redaction pattern") from exc
        count += replacements
    text, truncated = _bounded_utf8(text)
    return RedactionResult(text=text, redacted_count=count, truncated=truncated)


def capture_invocation_payload(
    *, invocation_id: str, prompt: object, response: object
) -> str:
    """Redact and persist payloads without ever failing the provider call."""
    expires_at = (datetime.now(UTC) + timedelta(days=_retention_days())).isoformat()
    status = "captured"
    prompt_text: str | None = None
    response_text: str | None = None
    try:
        prompt_text = redact_payload(prompt).text
        response_text = redact_payload(response).text
    except Exception:
        status = "redaction_failed"
    try:
        record_redacted_payload(
            invocation_id=invocation_id,
            prompt=prompt_text if status == "captured" else None,
            response=response_text if status == "captured" else None,
            status=status,
            expires_at=expires_at,
        )
        from core.eventbus.bus import event_bus

        event_bus.publish("runtime.cheap_lane_payload_captured", {
            "invocation_id": invocation_id,
            "status": status,
        })
    except Exception:
        return "capture_failed"
    return status


def purge_expired_payloads(now: datetime | None = None) -> int:
    """Delete expired payload bodies while retaining invocation metadata."""
    instant = now or datetime.now(UTC)
    with connect() as conn:
        from core.runtime.db_cheap_lane_control import _ensure_control_schema

        _ensure_control_schema(conn)
        _ensure_invocation_schema(conn)
        ids = [
            str(row["invocation_id"])
            for row in conn.execute(
                "SELECT invocation_id FROM cheap_lane_redacted_payloads "
                "WHERE expires_at < ?",
                (instant.isoformat(),),
            ).fetchall()
        ]
        if ids:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(
                f"UPDATE cheap_provider_invocations SET payload_status = 'expired' "
                f"WHERE invocation_id IN ({placeholders})",
                tuple(ids),
            )
        cursor = conn.execute(
            "DELETE FROM cheap_lane_redacted_payloads WHERE expires_at < ?",
            (instant.isoformat(),),
        )
        conn.commit()
    return int(cursor.rowcount or 0)
