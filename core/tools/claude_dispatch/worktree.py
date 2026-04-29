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
    worktree_path = build_worktree_path(task_id)

    # Primary: diff between main and the dispatch branch.
    primary = subprocess.run(
        ["git", "diff", f"main...{branch}"],
        cwd=str(JAIL_ROOT), capture_output=True, text=True,
    )
    if primary.stdout.strip():
        return primary.stdout

    # Fallback: Claude may not have committed. Gather uncommitted changes
    # inside the worktree (staged, unstaged, and untracked).
    parts: list[str] = []

    # Short status for human readability
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(worktree_path), capture_output=True, text=True,
    )
    if status.stdout.strip():
        parts.append(f"[git status --short]\n{status.stdout}")

    # Diff of tracked changes (staged + unstaged)
    diff = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=str(worktree_path), capture_output=True, text=True,
    )
    if diff.stdout.strip():
        parts.append(f"[git diff HEAD]\n{diff.stdout}")

    # Diff of untracked files (newly created by Claude)
    ls_files = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(worktree_path), capture_output=True, text=True,
    )
    untracked = [f for f in ls_files.stdout.splitlines() if f.strip()]
    for fname in untracked:
        fp = worktree_path / fname
        try:
            content = fp.read_text(errors="replace")[:4000]
            parts.append(f"[new file: {fname}]\n{content}")
        except OSError:
            pass

    return "\n\n".join(parts) if parts else "(no changes detected)"
