from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
import uuid
from typing import Any

from core.tools.claude_dispatch.audit import (
    start_audit_row, finalize_audit_row,
)
from core.tools.claude_dispatch.budget import BudgetTracker
from core.tools.claude_dispatch.host_oauth import find_host_oauth_token
from core.tools.claude_dispatch.spec import TaskSpec
from core.tools.claude_dispatch.stream import parse_stream_line
from core.tools.claude_dispatch.worktree import create_worktree, worktree_diff

logger = logging.getLogger(__name__)


def _build_prompt(spec: TaskSpec) -> str:
    parts = [
        f"GOAL: {spec.goal}",
        "",
        "SCOPE (touch only these paths):",
        *[f"  - {p}" for p in spec.scope_files],
    ]
    if spec.forbidden_paths:
        parts += ["", "FORBIDDEN:", *[f"  - {p}" for p in spec.forbidden_paths]]
    if spec.success_criteria:
        parts += ["", f"SUCCESS CRITERIA: {spec.success_criteria}"]
    parts += [
        "",
        "Operate strictly within SCOPE. Do not modify files outside it.",
        "",
        "When you have finished writing or editing files, you MUST commit "
        "your changes with a short descriptive commit message. Use: "
        "git add -A && git commit -m '<short summary>'",
        "",
        "After committing, summarize what you changed in one paragraph.",
    ]
    return "\n".join(parts)


def _new_task_id() -> str:
    return uuid.uuid4().hex[:12]


def run_dispatch(spec: TaskSpec, eventbus: Any) -> dict[str, Any]:
    task_id = _new_task_id()
    branch = f"claude/{task_id}"

    budget = BudgetTracker()
    budget.check_and_reserve()  # raises BudgetExceeded if cap hit

    start_audit_row(task_id, spec)
    eventbus.publish("tool.dispatch.started", {"task_id": task_id, "goal": spec.goal})

    worktree_path = create_worktree(task_id)

    cmd = [
        "claude", "-p", _build_prompt(spec),
        "--add-dir", str(worktree_path),
        "--allowed-tools", ",".join(spec.allowed_tools),
        "--permission-mode", spec.permission_mode,
        "--output-format", "stream-json",
        "--verbose",
    ]

    tokens_total = 0
    error: str | None = None
    status = "ok"
    exit_code: int | None = None
    deadline = time.monotonic() + spec.max_wall_seconds

    # 2026-04-29: `claude -p` headless calls authenticate via the host's
    # session-specific CLAUDE_CODE_OAUTH_TOKEN env var. The token in
    # ~/.claude/.credentials.json alone returns 401 for headless calls.
    # We look up a live host token from any running Claude Code process
    # owned by the same user and inject it into the spawn env.
    spawn_env = os.environ.copy()
    if not spawn_env.get("CLAUDE_CODE_OAUTH_TOKEN"):
        host_token = find_host_oauth_token()
        if host_token:
            spawn_env["CLAUDE_CODE_OAUTH_TOKEN"] = host_token
        else:
            error = (
                "no host Claude Code OAuth token available — "
                "open Claude Code (desktop or terminal) so its session "
                "exports CLAUDE_CODE_OAUTH_TOKEN, then retry"
            )
            status = "error"
            finalize_audit_row(
                task_id, status=status, tokens_used=0,
                exit_code=None, diff_summary="", error=error,
            )
            eventbus.publish("tool.dispatch.finished", {
                "task_id": task_id, "status": status,
                "tokens": 0, "branch": branch,
            })
            return {
                "task_id": task_id, "status": status, "tokens": 0,
                "branch": branch, "diff_summary": "", "error": error,
            }

    proc = subprocess.Popen(
        cmd, cwd=str(worktree_path),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, env=spawn_env,
    )

    def _watchdog() -> None:
        while proc.poll() is None:
            if time.monotonic() >= deadline:
                proc.kill()
                return
            time.sleep(1.0)

    wd = threading.Thread(target=_watchdog, daemon=True)
    wd.start()

    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                ev = parse_stream_line(line)
                if ev is None:
                    continue
                tokens_total += ev.tokens
                eventbus.publish(
                    f"tool.dispatch.{ev.kind}",
                    {"task_id": task_id, "text": ev.text[:500], "tokens": ev.tokens},
                )
        proc.wait()
        exit_code = proc.returncode
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        status = "error"
        try:
            proc.kill()
        except Exception:
            pass

    if exit_code != 0 and status == "ok":
        status = "error"
        if error is None:
            error = f"claude exited with code {exit_code}"

    if time.monotonic() >= deadline:
        status = "timeout"
        if error is None:
            error = f"exceeded max_wall_seconds={spec.max_wall_seconds}"

    diff_summary = ""
    try:
        diff_summary = worktree_diff(task_id)[:8000]
    except Exception:
        pass

    budget.record_usage(tokens_total)
    finalize_audit_row(
        task_id, status=status, tokens_used=tokens_total,
        exit_code=exit_code, diff_summary=diff_summary, error=error,
    )
    eventbus.publish("tool.dispatch.finished", {
        "task_id": task_id, "status": status,
        "tokens": tokens_total, "branch": branch,
    })

    return {
        "task_id": task_id,
        "status": status,
        "tokens": tokens_total,
        "branch": branch,
        "diff_summary": diff_summary,
        "error": error,
    }
