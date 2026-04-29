import pytest
from pathlib import Path

from core.tools.claude_dispatch.jail import (
    JAIL_ROOT, WORKTREE_ROOT, JailViolation,
    assert_inside_jail, build_worktree_path,
)


def test_jail_root_is_jarvis_repo():
    assert JAIL_ROOT == Path("/media/projects/jarvis-v2")


def test_worktree_root_is_under_jail():
    assert WORKTREE_ROOT == Path("/media/projects/jarvis-v2/.claude/worktrees")
    assert WORKTREE_ROOT.is_relative_to(JAIL_ROOT)


def test_assert_inside_jail_accepts_subpath():
    assert_inside_jail(Path("/media/projects/jarvis-v2/core/foo.py"))


def test_assert_inside_jail_rejects_outside():
    with pytest.raises(JailViolation):
        assert_inside_jail(Path("/etc/passwd"))


def test_assert_inside_jail_rejects_traversal_resolved():
    with pytest.raises(JailViolation):
        assert_inside_jail(Path("/media/projects/jarvis-v2/../other/x.py"))


def test_build_worktree_path_under_worktree_root():
    p = build_worktree_path("abc123")
    assert p == Path("/media/projects/jarvis-v2/.claude/worktrees/claude-task-abc123")
    assert p.is_relative_to(WORKTREE_ROOT)


def test_build_worktree_path_rejects_path_chars():
    with pytest.raises(JailViolation):
        build_worktree_path("../escape")
    with pytest.raises(JailViolation):
        build_worktree_path("a/b")
