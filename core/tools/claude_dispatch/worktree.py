from __future__ import annotations

import subprocess
from pathlib import Path

from core.tools.claude_dispatch.jail import JAIL_ROOT, build_worktree_path


def create_worktree(task_id: str) -> Path:
    path = build_worktree_path(task_id)
    branch = f"claude/{task_id}"
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(path), "main"],
        cwd=str(JAIL_ROOT),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git worktree add failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return path


def cleanup_worktree(task_id: str) -> None:
    path = build_worktree_path(task_id)
    branch = f"claude/{task_id}"
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(path)],
        cwd=str(JAIL_ROOT), capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "branch", "-D", branch],
        cwd=str(JAIL_ROOT), capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=str(JAIL_ROOT), capture_output=True, text=True,
    )


def worktree_diff(task_id: str) -> str:
    branch = f"claude/{task_id}"
    result = subprocess.run(
        ["git", "diff", f"main...{branch}"],
        cwd=str(JAIL_ROOT), capture_output=True, text=True,
    )
    return result.stdout
