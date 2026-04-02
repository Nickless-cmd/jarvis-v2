from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta

from apps.api.jarvis_api.services.chat_sessions import (
    list_chat_sessions,
    recent_chat_session_messages,
)
from core.runtime.db import (
    create_tool_intent_approval_request,
    expire_tool_intent_approval_request,
    get_tool_intent_approval_request,
    resolve_tool_intent_approval_request,
)

_APPROVAL_TTL = timedelta(minutes=15)
_APPROVE_PATTERNS = (
    re.compile(r"\bapprove\b"),
    re.compile(r"\bgodkend\b"),
    re.compile(r"\bgo ahead\b"),
    re.compile(r"\bproceed\b"),
    re.compile(r"\ballow\b"),
    re.compile(r"\bja godkend\b"),
)
_DENY_PATTERNS = (
    re.compile(r"\bdeny\b"),
    re.compile(r"\bafvis\b"),
    re.compile(r"\breject\b"),
    re.compile(r"\bikke godkend\b"),
    re.compile(r"\bdon't approve\b"),
    re.compile(r"\bdo not approve\b"),
    re.compile(r"\bnej afvis\b"),
)


def build_tool_intent_approval_surface(
    intent_surface: dict[str, object],
    *,
    requested_at: str,
) -> dict[str, object]:
    intent_state = str(intent_surface.get("intent_state") or "idle")
    approval_required = bool(intent_surface.get("approval_required", True))
    execution_state = str(intent_surface.get("execution_state") or "not-executed")
    if intent_state == "idle" or not approval_required:
        return {
            "approval_state": "none",
            "approval_source": "none",
            "approval_reason": "No active approval-gated tool intent is present.",
            "approval_requested_at": "",
            "approval_expires_at": "",
            "approval_resolved_at": "",
            "approval_resolution_reason": "",
            "approval_resolution_message": "",
            "approval_session_id": "",
            "approval_lifecycle": "bounded-approval-surface-light",
            "approval_semantics": {
                "verbal_supported": True,
                "mc_supported": True,
                "mode": "explicit-bounded-approval-only",
            },
            "execution_state": execution_state,
        }

    intent_key = tool_intent_approval_key(intent_surface)
    request = get_tool_intent_approval_request(intent_key)
    if request is None:
        requested_dt = _parse_iso(requested_at) or datetime.now(UTC)
        request = create_tool_intent_approval_request(
            intent_key=intent_key,
            intent_type=str(intent_surface.get("intent_type") or "inspect-repo-status"),
            intent_target=str(intent_surface.get("intent_target") or "workspace"),
            approval_scope=str(intent_surface.get("approval_scope") or "repo-read"),
            approval_required=approval_required,
            approval_reason=_approval_reason(intent_surface),
            requested_at=requested_dt.isoformat(),
            expires_at=(requested_dt + _APPROVAL_TTL).isoformat(),
            execution_state=execution_state,
        )

    if str(request.get("approval_state") or "pending") == "pending":
        expires_dt = _parse_iso(request.get("expires_at"))
        now = datetime.now(UTC)
        if expires_dt is not None and now >= expires_dt:
            request = expire_tool_intent_approval_request(
                intent_key,
                expired_at=now.isoformat(),
                resolution_reason="Approval window elapsed without an explicit bounded decision.",
            ) or request
        else:
            verbal_resolution = _find_verbal_resolution(intent_surface, request)
            if verbal_resolution is not None:
                request = resolve_tool_intent_approval_request(
                    intent_key,
                    approval_state=str(verbal_resolution["approval_state"]),
                    approval_source="verbal",
                    resolved_at=str(verbal_resolution["resolved_at"]),
                    resolution_reason=str(verbal_resolution["resolution_reason"]),
                    resolution_message=str(verbal_resolution["resolution_message"]),
                    session_id=str(verbal_resolution["session_id"]),
                ) or request

    return {
        "approval_state": str(request.get("approval_state") or "pending"),
        "approval_source": str(request.get("approval_source") or "none"),
        "approval_reason": str(request.get("approval_reason") or _approval_reason(intent_surface)),
        "approval_requested_at": str(request.get("requested_at") or ""),
        "approval_expires_at": str(request.get("expires_at") or ""),
        "approval_resolved_at": str(request.get("resolved_at") or ""),
        "approval_resolution_reason": str(request.get("resolution_reason") or ""),
        "approval_resolution_message": str(request.get("resolution_message") or ""),
        "approval_session_id": str(request.get("session_id") or ""),
        "approval_lifecycle": "bounded-approval-surface-light",
        "approval_semantics": {
            "verbal_supported": True,
            "mc_supported": True,
            "mode": "explicit-bounded-approval-only",
        },
        "execution_state": str(request.get("execution_state") or execution_state),
    }


def tool_intent_approval_key(intent_surface: dict[str, object]) -> str:
    raw = "::".join(
        [
            str(intent_surface.get("intent_type") or "inspect-repo-status"),
            str(intent_surface.get("intent_target") or "workspace"),
            str(intent_surface.get("approval_scope") or "repo-read"),
        ]
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"tool-intent::{digest}"


def _approval_reason(intent_surface: dict[str, object]) -> str:
    return (
        "Intent remains proposal-only until explicitly approved within bounded scope; "
        f"scope={intent_surface.get('approval_scope') or 'repo-read'}; "
        f"execution={intent_surface.get('execution_state') or 'not-executed'}."
    )


def _find_verbal_resolution(
    intent_surface: dict[str, object],
    request: dict[str, object],
) -> dict[str, object] | None:
    sessions = list_chat_sessions()
    if not sessions:
        return None
    latest_session = sessions[0]
    requested_at = _parse_iso(request.get("requested_at"))
    for message in reversed(
        recent_chat_session_messages(str(latest_session.get("id") or ""), limit=8)
    ):
        if str(message.get("role") or "") != "user":
            continue
        created_at = _parse_iso(message.get("created_at"))
        if requested_at is not None and created_at is not None and created_at < requested_at:
            continue
        content = str(message.get("content") or "")
        decision = _decision_from_text(content)
        if decision is None:
            continue
        if not _matches_intent_context(content, intent_surface):
            continue
        return {
            "approval_state": decision,
            "resolved_at": (created_at or datetime.now(UTC)).isoformat(),
            "resolution_reason": (
                "Explicit bounded verbal approval matched the current tool-intent context."
                if decision == "approved"
                else "Explicit bounded verbal denial matched the current tool-intent context."
            ),
            "resolution_message": content,
            "session_id": str(latest_session.get("id") or ""),
        }
    return None


def _decision_from_text(content: str) -> str | None:
    normalized = _normalize(content)
    for pattern in _DENY_PATTERNS:
        if pattern.search(normalized):
            return "denied"
    for pattern in _APPROVE_PATTERNS:
        if pattern.search(normalized):
            return "approved"
    return None


def _matches_intent_context(content: str, intent_surface: dict[str, object]) -> bool:
    normalized = _normalize(content)
    context_tokens = {
        "tool intent",
        "approval",
        _normalize(str(intent_surface.get("intent_type") or "inspect-repo-status")),
        _normalize(str(intent_surface.get("intent_target") or "workspace")),
        _normalize(str(intent_surface.get("approval_scope") or "repo-read")),
    }
    context_tokens = {token for token in context_tokens if token}
    return any(token in normalized for token in context_tokens)


def _normalize(value: str) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
        .split()
    )


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)