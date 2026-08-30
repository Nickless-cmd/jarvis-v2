from __future__ import annotations

import subprocess

from apps.api.jarvis_api.routes import system_health as system_health_module


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_system_git_commit_records_human_attribution(monkeypatch, tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("before\n")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-qm", "initial")
    tracked.write_text("after\n")
    monkeypatch.setattr(system_health_module, "_REPO_ROOT", str(tmp_path))

    result = system_health_module.system_git_commit(
        system_health_module.CommitRequest(message="update tracked")
    )

    assert result["ok"] is True
    body = _git(tmp_path, "log", "-1", "--pretty=%B").stdout
    assert "Actor: bjorn" in body
    assert "Actor-Type: human" in body
    assert "Origin: interactive" in body
    assert "Approved-By: bjorn" in body
