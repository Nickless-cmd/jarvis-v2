from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from core.services.attributed_git_commit import commit_with_attribution
from core.services.commit_attribution import CommitAttribution


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    (tmp_path / "one.py").write_text("one = 1\n")
    (tmp_path / "two.py").write_text("two = 1\n")
    _git(tmp_path, "add", "one.py", "two.py")
    _git(tmp_path, "commit", "-qm", "initial")
    return tmp_path


def _attribution(**overrides: str) -> CommitAttribution:
    values = {
        "actor": "codex",
        "actor_type": "agent",
        "run_id": "task-1",
        "session_id": "none",
        "origin": "delegated",
        "approved_by": "bjorn",
    }
    values.update(overrides)
    return CommitAttribution(**values)


def test_commit_with_attribution_creates_only_requested_commit(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 2\n")
    (git_repo / "two.py").write_text("two = 2\n")
    _git(git_repo, "add", "one.py")

    result = commit_with_attribution(
        repo=git_repo,
        message="fix: update one",
        attribution=_attribution(),
        paths=("one.py",),
    )

    assert result.returncode == 0
    body = _git(git_repo, "show", "-s", "--format=%B", "HEAD").stdout
    assert "Actor: codex" in body
    assert "Run-ID: task-1" in body
    assert "two.py" in _git(git_repo, "status", "--short").stdout


def test_executor_does_not_stage_unstaged_path(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 3\n")

    result = commit_with_attribution(
        repo=git_repo,
        message="fix: should not stage",
        attribution=_attribution(),
        paths=("one.py",),
    )

    assert result.returncode != 0
    assert _git(git_repo, "log", "-1", "--format=%s").stdout.strip() == "initial"


def test_executor_can_preserve_explicit_author(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 4\n")
    _git(git_repo, "add", "one.py")

    result = commit_with_attribution(
        repo=git_repo,
        message="fix: authored",
        attribution=_attribution(actor="jarvis", origin="interactive"),
        paths=("one.py",),
        author="Jarvis <jarvis@srvlab.dk>",
    )

    assert result.returncode == 0
    assert _git(git_repo, "show", "-s", "--format=%an <%ae>").stdout.strip() == (
        "Jarvis <jarvis@srvlab.dk>"
    )


def test_executor_rejects_invalid_attribution_before_git(git_repo: Path) -> None:
    before = _git(git_repo, "rev-parse", "HEAD").stdout.strip()

    result = commit_with_attribution(
        repo=git_repo,
        message="fix: invalid",
        attribution=_attribution(actor="attacker"),
    )

    assert result.returncode == 2
    assert "unknown Actor" in result.stderr
    assert _git(git_repo, "rev-parse", "HEAD").stdout.strip() == before


def test_executor_rewrites_managed_trailers_on_amend(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 5\n")
    _git(git_repo, "add", "one.py")
    first = commit_with_attribution(
        repo=git_repo,
        message="fix: first",
        attribution=_attribution(actor="opus", run_id="task-old"),
        paths=("one.py",),
    )
    assert first.returncode == 0
    old_message = _git(git_repo, "show", "-s", "--format=%B", "HEAD").stdout

    amended = commit_with_attribution(
        repo=git_repo,
        message=old_message,
        attribution=_attribution(run_id="task-new"),
        amend=True,
    )

    assert amended.returncode == 0
    body = _git(git_repo, "show", "-s", "--format=%B", "HEAD").stdout
    assert "Actor: codex" in body
    assert "Actor: opus" not in body
    assert "Run-ID: task-new" in body
    assert body.count("Run-ID:") == 1


def test_cli_imports_core_and_creates_attributed_commit(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 6\n")
    _git(git_repo, "add", "one.py")
    script = Path(__file__).resolve().parents[1] / "scripts" / "commit_with_attribution.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo",
            str(git_repo),
            "--message",
            "fix: cli",
            "--actor",
            "codex",
            "--run-id",
            "task-cli",
            "--session-id",
            "none",
            "--origin",
            "delegated",
            "--approved-by",
            "bjorn",
            "--path",
            "one.py",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "commit=" in result.stdout
    body = _git(git_repo, "show", "-s", "--format=%B", "HEAD").stdout
    assert "Actor: codex" in body
    assert "Run-ID: task-cli" in body
