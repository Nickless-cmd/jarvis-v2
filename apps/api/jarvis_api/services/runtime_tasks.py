from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.runtime import db as runtime_db

_VALID_STATUSES = {"queued", "running", "blocked", "succeeded", "failed", "cancelled"}
_VALID_PRIORITIES = {"low", "medium", "high"}


def create_task(
    *,
    kind: str,
    goal: str,
    origin: str,
    scope: str = "",
    priority: str = "medium",
    flow_id: str = "",
    session_id: str = "",
    run_id: str = "",
    owner: str = "",
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    normalized_priority = (
        priority.strip().lower()
        if priority.strip().lower() in _VALID_PRIORITIES
        else "medium"
    )
    return runtime_db.create_runtime_task(
        task_id=f"task-{uuid4().hex[:12]}",
        kind=str(kind or "generic").strip() or "generic",
        origin=str(origin or "unknown").strip() or "unknown",
        status="queued",
        goal=str(goal or "").strip(),
        scope=str(scope or "").strip(),
        priority=normalized_priority,
        flow_id=str(flow_id or "").strip(),
        session_id=str(session_id or "").strip(),
        run_id=str(run_id or "").strip(),
        owner=str(owner or "").strip(),
        created_at=now,
        updated_at=now,
    )


def list_tasks(
    *,
    status: str | None = None,
    kind: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    normalized_status = (
        str(status or "").strip().lower() if status is not None else None
    )
    normalized_kind = str(kind or "").strip() if kind is not None else None
    return runtime_db.list_runtime_tasks(
        status=normalized_status,
        kind=normalized_kind,
        limit=limit,
    )


def get_task(task_id: str) -> dict[str, object] | None:
    return runtime_db.get_runtime_task(str(task_id or "").strip())


def update_task(
    task_id: str,
    *,
    status: str | None = None,
    flow_id: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    owner: str | None = None,
    retry_at: str | None = None,
    blocked_reason: str | None = None,
    result_summary: str | None = None,
    artifact_ref: str | None = None,
) -> dict[str, object] | None:
    normalized_status = None
    if status is not None:
        candidate = str(status or "").strip().lower()
        normalized_status = candidate if candidate in _VALID_STATUSES else "queued"
    return runtime_db.update_runtime_task(
        str(task_id or "").strip(),
        status=normalized_status,
        flow_id=str(flow_id or "").strip() if flow_id is not None else None,
        session_id=str(session_id or "").strip() if session_id is not None else None,
        run_id=str(run_id or "").strip() if run_id is not None else None,
        owner=str(owner or "").strip() if owner is not None else None,
        retry_at=str(retry_at or "").strip() if retry_at is not None else None,
        blocked_reason=(
            str(blocked_reason or "").strip() if blocked_reason is not None else None
        ),
        result_summary=(
            str(result_summary or "").strip() if result_summary is not None else None
        ),
        artifact_ref=str(artifact_ref or "").strip() if artifact_ref is not None else None,
        updated_at=datetime.now(UTC).isoformat(),
    )
