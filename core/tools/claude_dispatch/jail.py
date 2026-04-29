from __future__ import annotations

import re
from pathlib import Path

JAIL_ROOT = Path("/media/projects/jarvis-v2")
WORKTREE_ROOT = JAIL_ROOT / ".claude" / "worktrees"

_TASK_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class JailViolation(RuntimeError):
    pass


def assert_inside_jail(path: Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(JAIL_ROOT)
    except ValueError:
        raise JailViolation(f"path escapes jail: {path} -> {resolved}")


def build_worktree_path(task_id: str) -> Path:
    if not _TASK_ID_RE.match(task_id):
        raise JailViolation(f"task_id contains illegal characters: {task_id!r}")
    p = WORKTREE_ROOT / f"claude-task-{task_id}"
    assert_inside_jail(p)
    return p
