"""Dispatch maa ikke melde ok naar HEAD ikke flyttede sig (maalt 5/11-2026)."""
from __future__ import annotations

import subprocess
import types
from pathlib import Path

import pytest

from core.tools.claude_dispatch import runner
from core.tools.claude_dispatch.spec import TaskSpec


class _Bus:
    def __init__(self):
        self.events = []

    def publish(self, kind, payload):
        self.events.append((kind, payload))


class _FakeProc:
    returncode = 0
    stdout = iter(())
    stderr = iter(())

    def poll(self):
        return 0

    def wait(self):
        return 0

    def kill(self):
        pass


def _git(path, *args):
    return subprocess.run(["git", *args], cwd=path, check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.py").write_text("x = 1\n")
    _git(tmp_path, "add", "a.py")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


@pytest.fixture
def harness(monkeypatch, worktree):
    audit: list[dict] = []
    monkeypatch.setattr(runner, "BudgetTracker", lambda: type(
        "B", (), {"check_and_reserve": lambda s: None,
                  "record_usage": lambda s, t: None})())
    monkeypatch.setattr(runner, "start_audit_row", lambda *a, **k: None)
    monkeypatch.setattr(runner, "finalize_audit_row",
                        lambda task_id, **k: audit.append(k))
    monkeypatch.setattr(runner, "quota_preflight", lambda *_: {"allow": True})
    monkeypatch.setattr(runner, "create_worktree", lambda task_id: worktree)
    monkeypatch.setattr(runner, "worktree_diff", lambda task_id: "diff")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "x")
    _patch_subprocess(monkeypatch, popen=lambda *a, **k: _FakeProc())
    return audit


_REAL_RUN = subprocess.run


def _patch_subprocess(monkeypatch, *, popen=None, run=None):
    """Proxy kun for runner-modulet; det globale subprocess roeres ikke."""
    current = runner.subprocess
    monkeypatch.setattr(runner, "subprocess", types.SimpleNamespace(
        Popen=popen or current.Popen,
        run=run or current.run,
        CompletedProcess=subprocess.CompletedProcess,
        PIPE=subprocess.PIPE,
    ))


def _spec() -> TaskSpec:
    return TaskSpec(goal="g", scope_files=("a.py",), allowed_tools=("Bash",))


def _fake_wrapper(monkeypatch, worktree, *, succeed: bool):
    """Erstat attribution-wrapperen (kraever hooks/baseline) med en plain commit."""
    real_run = _REAL_RUN

    def fake_run(cmd, **kw):
        if any("commit_with_attribution" in str(c) for c in cmd):
            if not succeed:
                return subprocess.CompletedProcess(cmd, 1, "", "hook afviste")
            return real_run(["git", "commit", "-q", "-m", "feat(worker): g"],
                            cwd=kw["cwd"], capture_output=True, text=True)
        return real_run(cmd, **kw)

    _patch_subprocess(monkeypatch, run=fake_run)


def test_ok_without_head_move_and_nothing_to_commit_is_error(harness, worktree):
    result = runner.run_dispatch(_spec(), _Bus())
    assert result["status"] == "error"
    assert result["failure_kind"] == "no_commit"
    assert result["needs_human"] is True
    assert result["committed_by"] == ""
    assert "ingen aendringer" in result["error"]
    assert harness[-1]["status"] == "error"
    assert harness[-1]["failure_kind"] == "no_commit"


def test_staged_work_is_committed_by_runner(harness, worktree, monkeypatch):
    base = _git(worktree, "rev-parse", "HEAD")
    (worktree / "a.py").write_text("x = 2\n")
    _git(worktree, "add", "a.py")
    _fake_wrapper(monkeypatch, worktree, succeed=True)
    result = runner.run_dispatch(_spec(), _Bus())
    assert result["status"] == "ok"
    assert result["failure_kind"] == "none"
    assert result["error"] is None
    assert result["committed_by"] == "runner"
    assert _git(worktree, "rev-parse", "HEAD") != base
    assert _git(worktree, "status", "--porcelain") == ""


def test_rejected_commit_is_error_not_ok(harness, worktree, monkeypatch):
    (worktree / "a.py").write_text("x = 2\n")
    _git(worktree, "add", "a.py")
    _fake_wrapper(monkeypatch, worktree, succeed=False)
    result = runner.run_dispatch(_spec(), _Bus())
    assert result["status"] == "error"
    assert result["failure_kind"] == "no_commit"
    assert "hook afviste" in result["error"]
    assert result["committed_by"] == ""


def test_agent_commit_is_recognised(harness, worktree, monkeypatch):
    class _Committing(_FakeProc):
        pass

    def popen(*a, **k):
        (worktree / "a.py").write_text("x = 3\n")
        _git(worktree, "commit", "-q", "-am", "agent")
        return _Committing()

    _patch_subprocess(monkeypatch, popen=popen)
    result = runner.run_dispatch(_spec(), _Bus())
    assert result["status"] == "ok"
    assert result["committed_by"] == "agent"
    assert result["failure_kind"] == "none"
