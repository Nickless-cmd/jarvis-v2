"""Container-exec terminal (§17 terminal v2) — cwd-containment sikkerhed."""
from __future__ import annotations

import os


def test_escape_attempt_falls_back_to_repo() -> None:
    from apps.api.jarvis_api.routes.chat import _terminal_run_sync, _repo_root
    repo = str(_repo_root())
    r = _terminal_run_sync("pwd", "../../../etc")
    assert r["stdout"].strip() == repo  # escape afvist → repo-rod


def test_absolute_path_outside_repo_falls_back() -> None:
    from apps.api.jarvis_api.routes.chat import _terminal_run_sync, _repo_root
    repo = str(_repo_root())
    r = _terminal_run_sync("pwd", "/etc")
    assert r["stdout"].strip() == repo


def test_valid_subdir_allowed() -> None:
    from apps.api.jarvis_api.routes.chat import _terminal_run_sync, _repo_root
    repo = str(_repo_root())
    r = _terminal_run_sync("pwd", "core")
    assert r["stdout"].strip() == os.path.join(repo, "core")


def test_command_runs_and_returns_exit_code() -> None:
    from apps.api.jarvis_api.routes.chat import _terminal_run_sync
    r = _terminal_run_sync("echo hej", "")
    assert r["stdout"].strip() == "hej"
    assert r["exit_code"] == 0


def test_nonzero_exit_captured() -> None:
    from apps.api.jarvis_api.routes.chat import _terminal_run_sync
    r = _terminal_run_sync("exit 3", "")
    assert r["exit_code"] == 3
