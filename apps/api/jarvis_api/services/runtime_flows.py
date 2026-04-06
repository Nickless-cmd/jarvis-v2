from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from apps.api.jarvis_api.services import runtime_tasks
from core.runtime import db as runtime_db

_VALID_STATUSES = {"queued", "running", "blocked", "succeeded", "failed", "cancelled"}


def create_flow(
    *,
    task_id: str,
    current_step: str = "",
    step_state: str = "",
    plan: list[dict[str, object]] | None = None,
    next_action: str = "",
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    resolved_task_id = str(task_id or "").strip()
    flow = runtime_db.create_runtime_flow(
        flow_id=f"flow-{uuid4().hex[:12]}",
        task_id=resolved_task_id,
        status="queued",
        current_step=str(current_step or "").strip(),
        step_state=str(step_state or "").strip(),
        plan_json=json.dumps(plan or [], ensure_ascii=False, sort_keys=True),
        next_action=str(next_action or "").strip(),
        created_at=now,
        updated_at=now,
    )
    runtime_tasks.update_task(
        resolved_task_id,
        flow_id=flow["flow_id"],
    )
    return _decode_flow(flow)


def get_flow(flow_id: str) -> dict[str, object] | None:
    flow = runtime_db.get_runtime_flow(str(flow_id or "").strip())
    if flow is None:
        return None
    return _decode_flow(flow)


def list_flows(
    *,
    status: str | None = None,
    task_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    normalized_status = (
        str(status or "").strip().lower() if status is not None else None
    )
    resolved_task_id = str(task_id or "").strip() if task_id is not None else None
    return [
        _decode_flow(flow)
        for flow in runtime_db.list_runtime_flows(
            status=normalized_status,
            task_id=resolved_task_id,
            limit=limit,
        )
    ]


def update_flow(
    flow_id: str,
    *,
    status: str | None = None,
    current_step: str | None = None,
    step_state: str | None = None,
    plan: list[dict[str, object]] | None = None,
    next_action: str | None = None,
    last_error: str | None = None,
    attempt_count: int | None = None,
) -> dict[str, object] | None:
    normalized_status = None
    if status is not None:
        candidate = str(status or "").strip().lower()
        normalized_status = candidate if candidate in _VALID_STATUSES else "queued"
    flow = runtime_db.update_runtime_flow(
        str(flow_id or "").strip(),
        status=normalized_status,
        current_step=str(current_step or "").strip() if current_step is not None else None,
        step_state=str(step_state or "").strip() if step_state is not None else None,
        plan_json=(
            json.dumps(plan or [], ensure_ascii=False, sort_keys=True)
            if plan is not None
            else None
        ),
        next_action=str(next_action or "").strip() if next_action is not None else None,
        last_error=str(last_error or "").strip() if last_error is not None else None,
        attempt_count=attempt_count,
        updated_at=datetime.now(UTC).isoformat(),
    )
    if flow is None:
        return None
    return _decode_flow(flow)


def _decode_flow(flow: dict[str, object]) -> dict[str, object]:
    decoded = dict(flow)
    raw_plan = str(flow.get("plan_json") or "[]").strip() or "[]"
    try:
        decoded["plan"] = json.loads(raw_plan)
    except json.JSONDecodeError:
        decoded["plan"] = []
    return decoded
