"""Task worker — consumes queued runtime_tasks in heartbeat tick cadence.

Responsibilities:
- Claim the next queued task ordered by priority and age
- Dispatch to a handler based on the task's `kind`
- Mark `succeeded`/`failed` with a short result_summary

This worker is deliberately thin: it converts tasks from `queued` to a terminal
state so Jarvis' runtime no longer accumulates dead queue entries. Richer
handlers (hooking into runtime_action_executor, LLM-driven follow-through) can
be layered on top in subsequent work.
"""
from __future__ import annotations

from typing import Any

from . import runtime_tasks

_DEFAULT_KINDS: tuple[str, ...] = (
    "initiative-followup",
    "heartbeat-followup",
    "generic",
    "open-loop-follow-up",
)


def claim_next_task(
    kinds: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any] | None:
    """Claim the next queued task and mark it `running`.

    Returns the updated task dict, or ``None`` if nothing is queued.
    """
    allowed = tuple(kinds) if kinds else _DEFAULT_KINDS
    # runtime_tasks.list_tasks already sorts by (priority_rank, retry_at/updated_at).
    queued = runtime_tasks.list_tasks(status="queued", limit=50)
    candidates = [t for t in queued if str(t.get("kind") or "") in allowed]
    if not candidates:
        return None
    task = candidates[0]
    updated = runtime_tasks.update_task(str(task["task_id"]), status="running")
    return updated or task


def _handle_initiative_followup(task: dict[str, Any]) -> str:
    goal = str(task.get("goal") or "(no goal)")
    return f"initiative-followup acknowledged: {goal[:300]}"


def _handle_heartbeat_followup(task: dict[str, Any]) -> str:
    goal = str(task.get("goal") or "(no goal)")
    return f"heartbeat-followup acknowledged: {goal[:300]}"


def _handle_open_loop_followup(task: dict[str, Any]) -> str:
    goal = str(task.get("goal") or "(no goal)")
    return f"open-loop-follow-up acknowledged: {goal[:300]}"


def _execute_task(task: dict[str, Any]) -> None:
    """Execute a single task and persist its final status. Never raises."""
    kind = str(task.get("kind") or "")
    task_id = str(task.get("task_id") or "")
    try:
        if kind == "initiative-followup":
            summary = _handle_initiative_followup(task)
        elif kind == "heartbeat-followup":
            summary = _handle_heartbeat_followup(task)
        elif kind == "open-loop-follow-up":
            summary = _handle_open_loop_followup(task)
        elif kind == "generic":
            summary = f"generic task acknowledged: {str(task.get('goal') or '')[:120]}"
        else:
            runtime_tasks.update_task(
                task_id,
                status="failed",
                result_summary=f"unknown kind: {kind}",
            )
            return
        runtime_tasks.update_task(
            task_id,
            status="succeeded",
            result_summary=(summary or "ok")[:500],
        )
    except Exception as exc:  # noqa: BLE001
        runtime_tasks.update_task(
            task_id,
            status="failed",
            result_summary=f"error: {type(exc).__name__}: {exc}"[:500],
        )


def tick_task_worker(budget: int = 3) -> dict[str, Any]:
    """Run one worker tick: claim and execute up to ``budget`` tasks.

    Returns a summary dict suitable for ``daemon_manager.record_daemon_tick``.
    """
    processed = 0
    succeeded = 0
    failed = 0
    allowed = _DEFAULT_KINDS
    for _ in range(max(0, int(budget))):
        task = claim_next_task(kinds=allowed)
        if task is None:
            break
        _execute_task(task)
        reloaded = runtime_tasks.get_task(str(task["task_id"]))
        processed += 1
        status = str((reloaded or {}).get("status") or "")
        if status == "succeeded":
            succeeded += 1
        elif status == "failed":
            failed += 1
    remaining = [
        t
        for t in runtime_tasks.list_tasks(status="queued", limit=50)
        if str(t.get("kind") or "") in allowed
    ]
    return {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "remaining_queued": len(remaining),
    }
