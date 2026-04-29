from __future__ import annotations

import subprocess
from typing import Any

from core.eventbus.bus import EventBus
from core.tools.claude_dispatch.audit import read_audit_row
from core.tools.claude_dispatch.budget import BudgetExceeded
from core.tools.claude_dispatch.runner import run_dispatch
from core.tools.claude_dispatch.spec import parse_spec, SpecValidationError


_BUS_SINGLETON: EventBus | None = None


def _eventbus() -> EventBus:
    global _BUS_SINGLETON
    if _BUS_SINGLETON is None:
        _BUS_SINGLETON = EventBus()
    return _BUS_SINGLETON


def _exec_dispatch_to_claude_code(args: dict[str, Any]) -> dict[str, Any]:
    try:
        spec = parse_spec(args)
    except SpecValidationError as e:
        return {"status": "error", "error": f"spec validation: {e}"}

    try:
        return run_dispatch(spec, _eventbus())
    except BudgetExceeded as e:
        return {"status": "error", "error": f"budget: {e}"}
    except RuntimeError as e:
        return {"status": "error", "error": str(e)}


def _exec_dispatch_status(args: dict[str, Any]) -> dict[str, Any]:
    task_id = str(args.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "error": "task_id required"}
    row = read_audit_row(task_id)
    if row is None:
        return {"status": "error", "error": f"task_id not found: {task_id}"}
    return {"status": "ok", "row": row}


def _exec_dispatch_cancel(args: dict[str, Any]) -> dict[str, Any]:
    task_id = str(args.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "error": "task_id required"}
    worktree = f"/media/projects/jarvis-v2/.claude/worktrees/claude-task-{task_id}"
    result = subprocess.run(
        ["pkill", "-f", f"claude.*{worktree}"],
        capture_output=True, text=True,
    )
    return {"status": "ok", "task_id": task_id, "killed": result.returncode == 0}
