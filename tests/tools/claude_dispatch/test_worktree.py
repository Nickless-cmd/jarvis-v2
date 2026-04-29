import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.tools.claude_dispatch.worktree import (
    create_worktree, cleanup_worktree, worktree_diff,
)


def _ok(stdout: str = "", stderr: str = ""):
    m = MagicMock()
    m.returncode = 0
    m.stdout = stdout
    m.stderr = stderr
    return m


@patch("core.tools.claude_dispatch.worktree.subprocess.run")
def test_create_worktree_invokes_git(mock_run):
    mock_run.return_value = _ok()
    path = create_worktree("abc123")
    assert path == Path("/media/projects/jarvis-v2/.claude/worktrees/claude-task-abc123")
    cmd = mock_run.call_args.args[0]
    assert cmd[:3] == ["git", "worktree", "add"]
    assert "claude/abc123" in cmd
    assert str(path) in cmd


@patch("core.tools.claude_dispatch.worktree.subprocess.run")
def test_create_worktree_raises_on_git_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: branch exists")
    with pytest.raises(RuntimeError, match="git worktree add failed"):
        create_worktree("abc123")


@patch("core.tools.claude_dispatch.worktree.subprocess.run")
def test_cleanup_worktree_removes_and_prunes(mock_run):
    mock_run.return_value = _ok()
    cleanup_worktree("abc123")
    calls = [c.args[0] for c in mock_run.call_args_list]
    assert ["git", "worktree", "remove", "--force",
            "/media/projects/jarvis-v2/.claude/worktrees/claude-task-abc123"] in calls
    assert ["git", "branch", "-D", "claude/abc123"] in calls


@patch("core.tools.claude_dispatch.worktree.subprocess.run")
def test_worktree_diff_returns_text(mock_run):
    mock_run.return_value = _ok(stdout="diff --git a/x b/x\n+hello\n")
    text = worktree_diff("abc123")
    assert "diff --git" in text
    cmd = mock_run.call_args.args[0]
    assert cmd[:2] == ["git", "diff"]
    assert "main...claude/abc123" in cmd
