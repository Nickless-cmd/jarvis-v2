from __future__ import annotations

from uuid import uuid4

from core.runtime.db import connect
from core.runtime.db_capability_approval import capability_approval_envelope_fingerprint
from core.tools.workspace_capabilities_results import _content_fingerprint, _preview_text


def _approval_request_user_context() -> tuple[str | None, str]:
    try:
        from core.identity.workspace_context import current_user_id

        user_id = current_user_id() or None
        return user_id, f"user:{user_id}" if user_id else "jarvis-self"
    except Exception:
        return None, "jarvis-self"


def _persist_capability_approval_request(
    invocation: dict[str, object],
    *,
    requested_at: str,
    run_id: str | None = None,
) -> None:
    capability = invocation.get("capability") or {}
    approval = invocation.get("approval") or {}
    proposal_content = invocation.get("proposal_content") or {}
    scheduled_for_user_id, initiated_by = _approval_request_user_context()
    request_id = f"cap-approval-{uuid4().hex}"
    envelope_fingerprint = capability_approval_envelope_fingerprint(
        {
            "scheduled_for_user_id": scheduled_for_user_id,
            "capability_id": capability.get("capability_id") or "unknown",
            "execution_mode": invocation.get("execution_mode") or "unknown",
            "proposal_target_path": proposal_content.get("target"),
            "proposal_content": proposal_content.get("content"),
            "proposal_content_fingerprint": proposal_content.get("fingerprint"),
        }
    )
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO capability_approval_requests (
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                proposal_target_path,
                proposal_content,
                proposal_content_summary,
                proposal_content_fingerprint,
                proposal_content_source,
                proposal_reason,
                requested_at,
                status,
                scheduled_for_user_id,
                initiated_by
                , approval_envelope_fingerprint
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                capability.get("capability_id") or "unknown",
                capability.get("name"),
                capability.get("kind"),
                invocation.get("execution_mode") or "unknown",
                approval.get("policy"),
                run_id,
                proposal_content.get("target"),
                proposal_content.get("content"),
                proposal_content.get("summary"),
                proposal_content.get("fingerprint"),
                proposal_content.get("source"),
                proposal_content.get("reason"),
                requested_at,
                "pending",
                scheduled_for_user_id,
                initiated_by,
                envelope_fingerprint,
            ),
        )
        if scheduled_for_user_id:
            from core.services.approval_outbox import enqueue_approval_notification

            enqueue_approval_notification(
                conn,
                request_id=request_id,
                user_id=scheduled_for_user_id,
                envelope={
                    "request_id": request_id,
                    "capability_id": capability.get("capability_id") or "unknown",
                    "capability_name": capability.get("name") or "",
                    "execution_mode": invocation.get("execution_mode") or "unknown",
                    "target": proposal_content.get("target") or "",
                    "fingerprint": proposal_content.get("fingerprint") or "",
                    "envelope_fingerprint": envelope_fingerprint,
                },
            )
        conn.commit()


def _workspace_write_proposal_content(
    *,
    summary: dict[str, object],
    write_content: str | None,
) -> dict[str, object] | None:
    if str(summary.get("execution_mode") or "") != "workspace-file-write":
        return None
    content = str(write_content or "")
    if not content:
        return {
            "state": "content-missing",
            "type": "workspace-file-write-proposal",
            "target": str(summary.get("target_path") or ""),
            "content": "",
            "summary": "",
            "fingerprint": "",
            "source": "explicit-write-content",
            "reason": (
                "Workspace write proposal exists, but no explicit write_content has been attached yet."
            ),
            "explicit_approval_required": True,
            "approval_scope": "workspace-write",
            "confidence": "low",
            "target_identity": False,
            "target_memory": False,
            "workspace_scoped": True,
        }
    return {
        "state": "bounded-content-ready",
        "type": "workspace-file-write-proposal",
        "target": str(summary.get("target_path") or ""),
        "content": content,
        "summary": _preview_text(content, limit=160),
        "fingerprint": _content_fingerprint(content),
        "source": "explicit-write-content",
        "reason": (
            f"Scoped workspace write proposal prepared for {summary.get('target_path') or 'workspace'}."
        ),
        "explicit_approval_required": True,
        "approval_scope": "workspace-write",
        "confidence": "high",
        "target_identity": False,
        "target_memory": False,
        "workspace_scoped": True,
    }
