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
                "proposal_only": False,
                "execution_allowed": False,
                "mutation_near": False,
                "scope_classification": "none",
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
            "proposal_only": True,
            "execution_allowed": False,
            "mutation_near": bool(intent_surface.get("mutation_near", False)),
            "scope_classification": str(
                intent_surface.get("mutation_intent_classification") or "read-only"
            ),
        },
        "execution_state": str(request.get("execution_state") or execution_state),
    }


def resolve_tool_intent_approval(
    intent_surface: dict[str, object],
    *,
    approval_state: str,
    approval_source: str,
    resolution_reason: str,
    resolution_message: str = "",
    session_id: str = "",
    resolved_at: str | None = None,
) -> dict[str, object]:
    normalized_state = str(approval_state or "").strip().lower()
    if normalized_state not in {"approved", "denied"}:
        raise ValueError("approval_state must be approved or denied")

    intent_state = str(intent_surface.get("intent_state") or "idle")
    approval_required = bool(intent_surface.get("approval_required", True))
    if intent_state == "idle" or not approval_required:
        raise ValueError("No active approval-gated tool intent is present.")

    intent_key = tool_intent_approval_key(intent_surface)
    request = get_tool_intent_approval_request(intent_key)
    if request is None:
        raise ValueError("Tool intent approval request not found for current runtime intent.")

    current_state = str(request.get("approval_state") or "pending")
    if current_state != "pending":
        raise ValueError(
            f"Tool intent approval is not pending; current state is {current_state}."
        )

    resolved_request = resolve_tool_intent_approval_request(
        intent_key,
        approval_state=normalized_state,
        approval_source=str(approval_source or "mc"),
        resolved_at=resolved_at or datetime.now(UTC).isoformat(),
        resolution_reason=resolution_reason,
        resolution_message=resolution_message,
        session_id=session_id,
    )
    if resolved_request is None:
        raise RuntimeError("tool intent approval request could not be resolved")
    return resolved_request


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
    mutation_classification = str(
        intent_surface.get("mutation_intent_classification") or "read-only"
    )
    mutation_repo_scope = str(intent_surface.get("mutation_repo_scope") or "")
    mutation_system_scope = str(intent_surface.get("mutation_system_scope") or "")
    write_proposal_type = str(intent_surface.get("write_proposal_type") or "none")
    write_proposal_scope = str(intent_surface.get("write_proposal_scope") or "none")
    write_proposal_targets = list(intent_surface.get("write_proposal_targets") or [])
    write_proposal_reason = str(intent_surface.get("write_proposal_reason") or "")
    write_proposal_criticality = str(
        intent_surface.get("write_proposal_criticality") or "none"
    )
    write_proposal_target = str(intent_surface.get("write_proposal_target") or "none")
    write_proposal_content_state = str(
        intent_surface.get("write_proposal_content_state") or "none"
    )
    write_proposal_content_summary = str(
        intent_surface.get("write_proposal_content_summary") or "none"
    )
    write_proposal_content_fingerprint = str(
        intent_surface.get("write_proposal_content_fingerprint") or "none"
    )
    mutating_exec_proposal_state = str(
        intent_surface.get("mutating_exec_proposal_state") or "none"
    )
    mutating_exec_proposal_command = str(
        intent_surface.get("mutating_exec_proposal_command") or "none"
    )
    mutating_exec_proposal_scope = str(
        intent_surface.get("mutating_exec_proposal_scope") or "none"
    )
    mutating_exec_proposal_reason = str(
        intent_surface.get("mutating_exec_proposal_reason") or "none"
    )
    mutating_exec_requires_sudo = bool(
        intent_surface.get("mutating_exec_requires_sudo", False)
    )
    mutating_exec_criticality = str(
        intent_surface.get("mutating_exec_criticality") or "none"
    )
    sudo_exec_proposal_state = str(
        intent_surface.get("sudo_exec_proposal_state") or "none"
    )
    sudo_exec_proposal_command = str(
        intent_surface.get("sudo_exec_proposal_command") or "none"
    )
    sudo_exec_proposal_scope = str(
        intent_surface.get("sudo_exec_proposal_scope") or "none"
    )
    sudo_exec_proposal_reason = str(
        intent_surface.get("sudo_exec_proposal_reason") or "none"
    )
    sudo_exec_requires_sudo = bool(intent_surface.get("sudo_exec_requires_sudo", False))
    sudo_exec_criticality = str(intent_surface.get("sudo_exec_criticality") or "none")
    return (
        "Intent remains proposal-only until explicitly approved within bounded scope; "
        f"scope={intent_surface.get('approval_scope') or 'repo-read'}; "
        f"mutation_classification={mutation_classification}; "
        f"repo_scope={mutation_repo_scope or 'none'}; "
        f"system_scope={mutation_system_scope or 'none'}; "
        f"write_proposal_type={write_proposal_type}; "
        f"write_proposal_scope={write_proposal_scope}; "
        f"write_proposal_targets={','.join(str(item) for item in write_proposal_targets[:4]) or 'none'}; "
        f"write_proposal_target={write_proposal_target}; "
        f"write_proposal_criticality={write_proposal_criticality}; "
        f"write_proposal_reason={write_proposal_reason or 'none'}; "
        f"write_proposal_content_state={write_proposal_content_state}; "
        f"write_proposal_content_summary={write_proposal_content_summary}; "
        f"write_proposal_content_fingerprint={write_proposal_content_fingerprint}; "
        f"mutating_exec_proposal_state={mutating_exec_proposal_state}; "
        f"mutating_exec_proposal_scope={mutating_exec_proposal_scope}; "
        f"mutating_exec_proposal_command={mutating_exec_proposal_command}; "
        f"mutating_exec_requires_sudo={mutating_exec_requires_sudo}; "
        f"mutating_exec_criticality={mutating_exec_criticality}; "
        f"mutating_exec_proposal_reason={mutating_exec_proposal_reason}; "
        f"sudo_exec_proposal_state={sudo_exec_proposal_state}; "
        f"sudo_exec_proposal_scope={sudo_exec_proposal_scope}; "
        f"sudo_exec_proposal_command={sudo_exec_proposal_command}; "
        f"sudo_exec_requires_sudo={sudo_exec_requires_sudo}; "
        f"sudo_exec_criticality={sudo_exec_criticality}; "
        f"sudo_exec_proposal_reason={sudo_exec_proposal_reason}; "
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
