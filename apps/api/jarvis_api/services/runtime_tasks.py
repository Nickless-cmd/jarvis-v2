from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
from uuid import uuid4

from core.runtime import db as runtime_db
from core.identity.workspace_bootstrap import workspace_memory_paths

_VALID_STATUSES = {"queued", "running", "blocked", "succeeded", "failed", "cancelled"}
_VALID_PRIORITIES = {"low", "medium", "high"}
_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


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
    requested_priority = (
        priority.strip().lower()
        if priority.strip().lower() in _VALID_PRIORITIES
        else "medium"
    )
    normalized_priority = _priority_with_runtime_bias(
        requested_priority,
        kind=str(kind or "generic").strip(),
        goal=str(goal or "").strip(),
        scope=str(scope or "").strip(),
        origin=str(origin or "unknown").strip(),
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
    items = runtime_db.list_runtime_tasks(
        status=normalized_status,
        kind=normalized_kind,
        limit=limit,
    )
    items.sort(key=_task_sort_key)
    return items[: max(limit, 1)]


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


def _task_sort_key(task: dict[str, object]) -> tuple[int, str, str]:
    priority_rank = {"high": 0, "medium": 1, "low": 2}.get(
        str(task.get("priority") or "medium").strip().lower(),
        1,
    )
    retry_at = str(task.get("retry_at") or "").strip()
    updated_at = str(task.get("updated_at") or "").strip()
    return (priority_rank, retry_at or updated_at, updated_at)


def _priority_with_runtime_bias(
    requested_priority: str,
    *,
    kind: str,
    goal: str,
    scope: str,
    origin: str,
) -> str:
    current = requested_priority if requested_priority in _VALID_PRIORITIES else "medium"
    try:
        paths = workspace_memory_paths()
        standing_orders_path = Path(paths["workspace_dir"]) / "STANDING_ORDERS.md"
        standing_orders = (
            standing_orders_path.read_text(encoding="utf-8", errors="replace")
            if standing_orders_path.exists()
            else ""
        )
        daily_missing = not Path(paths["daily_memory"]).exists()
    except Exception:
        standing_orders = ""
        daily_missing = False

    haystack = " ".join(part for part in [kind, goal, scope, origin] if part).lower()
    task_tokens = set(_TOKEN_RE.findall(haystack))
    standing_tokens = set(_TOKEN_RE.findall(standing_orders.lower()))
    overlap = len(task_tokens & standing_tokens)

    memory_related = any(
        token in haystack
        for token in ("memory", "continuity", "standing", "workspace", "repo", "hook", "flow")
    )

    if current == "low" and (overlap >= 2 or (daily_missing and memory_related)):
        return "medium"
    if current == "medium" and (overlap >= 3 or (daily_missing and memory_related)):
        return "high"
    return current
