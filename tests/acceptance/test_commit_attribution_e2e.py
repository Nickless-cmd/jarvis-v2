from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from core.services.commit_attribution import (
    ACTOR_REGISTRY,
    CommitAttribution,
    render_attributed_message,
)
from scripts.install_git_hooks import check_installation, install


SOURCE_ROOT = Path(__file__).resolve().parents[2]


def _git(repo: Path, *args: str, check: bool = True):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _copy_runtime(repo: Path) -> None:
    for relative in (
        "core/services/__init__.py",
        "core/services/attributed_git_commit.py",
        "core/services/commit_attribution.py",
        "scripts/commit_with_attribution.py",
        "scripts/install_git_hooks.py",
        "scripts/validate_commit_attribution.py",
    ):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE_ROOT / relative, target)
    (repo / ".pre-commit-config.yaml").write_text(
        f"""default_install_hook_types: [pre-commit, commit-msg, pre-push]
repos:
  - repo: local
    hooks:
      - id: commit-attribution-message
        name: Require commit attribution trailers
        entry: {sys.executable} scripts/validate_commit_attribution.py --message-file
        language: system
        stages: [commit-msg]
      - id: commit-attribution-range
        name: Validate pushed commit attribution range
        entry: {sys.executable} scripts/validate_commit_attribution.py --pre-push
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
""",
        encoding="utf-8",
    )


def _wrapper_commit(
    repo: Path,
    *,
    actor: str,
    origin: str,
    approved_by: str,
    run_id: str,
    content: str,
    amend: bool = False,
) -> str:
    (repo / "audit.txt").write_text(content, encoding="utf-8")
    _git(repo, "add", "audit.txt")
    command = [
        sys.executable,
        str(repo / "scripts" / "commit_with_attribution.py"),
        "--repo", str(repo),
        "--message", f"test: {actor} attribution",
        "--actor", actor,
        "--run-id", run_id,
        "--session-id", "none",
        "--origin", origin,
        "--approved-by", approved_by,
        "--path", "audit.txt",
    ]
    if amend:
        command.append("--amend")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _validate_pre_push(repo: Path, from_ref: str, to_ref: str):
    env = os.environ.copy()
    env["PRE_COMMIT_FROM_REF"] = from_ref
    env["PRE_COMMIT_TO_REF"] = to_ref
    return subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "validate_commit_attribution.py"),
            "--repo", str(repo),
            "--pre-push",
        ],
        capture_output=True,
        text=True,
        env=env,
    )


def test_commit_attribution_hooks_end_to_end(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _copy_runtime(repo)
    (repo / "audit.txt").write_text("legacy\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "legacy before activation")
    baseline = _git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / ".commit-attribution-baseline").write_text(
        baseline + "\n", encoding="utf-8"
    )
    default_hooks = repo / ".git" / "hooks"
    _git(repo, "config", "--local", "core.hooksPath", str(default_hooks))

    assert install(repo) == 0
    assert check_installation(repo) == ()
    configured_hooks = _git(
        repo, "config", "--local", "--get", "core.hooksPath"
    ).stdout.strip()
    assert configured_hooks == str(default_hooks)

    actors = (
        ("bjorn", "interactive", "bjorn"),
        ("jarvis", "autonomous", "policy:auto-commit-v1"),
        ("codex", "delegated", "bjorn"),
        ("opus", "delegated", "policy:claude-dispatch-v1"),
    )
    for index, (actor, origin, approved_by) in enumerate(actors, start=1):
        commit = _wrapper_commit(
            repo,
            actor=actor,
            origin=origin,
            approved_by=approved_by,
            run_id=f"run-{actor}",
            content=f"actor {index}\n",
        )
        body = _git(repo, "show", "-s", "--format=%B", commit).stdout
        assert f"Actor: {actor}" in body
        assert f"Actor-Type: {ACTOR_REGISTRY[actor].actor_type}" in body

    before_rejected = _git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "audit.txt").write_text("raw rejected\n", encoding="utf-8")
    _git(repo, "add", "audit.txt")
    rejected = _git(repo, "commit", "-m", "raw rejected", check=False)
    assert rejected.returncode != 0
    assert "Actor must appear exactly once" in rejected.stdout + rejected.stderr

    _git(repo, "commit", "--no-verify", "-m", "raw bypass")
    bad_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    pre_push = _validate_pre_push(repo, before_rejected, bad_head)
    assert pre_push.returncode != 0
    assert "commit attribution failed" in pre_push.stderr
    _git(repo, "reset", "--hard", before_rejected)

    original = _wrapper_commit(
        repo,
        actor="codex",
        origin="delegated",
        approved_by="bjorn",
        run_id="run-amend-original",
        content="before amend\n",
    )
    amended = _wrapper_commit(
        repo,
        actor="codex",
        origin="delegated",
        approved_by="bjorn",
        run_id="run-amended",
        content="after amend\n",
        amend=True,
    )
    assert amended != original

    main_branch = _git(repo, "branch", "--show-current").stdout.strip()
    _git(repo, "checkout", "-qb", "merge-source")
    (repo / "branch.txt").write_text("branch\n", encoding="utf-8")
    _git(repo, "add", "branch.txt")
    branch_message = render_attributed_message(
        "test: branch commit",
        CommitAttribution(
            actor="codex",
            actor_type="agent",
            run_id="run-branch",
            session_id="none",
            origin="delegated",
            approved_by="bjorn",
        ),
    )
    _git(repo, "commit", "-m", branch_message)
    _git(repo, "checkout", main_branch)
    merge_message = render_attributed_message(
        "test: valid merge",
        CommitAttribution(
            actor="bjorn",
            actor_type="human",
            run_id="run-merge",
            session_id="none",
            origin="interactive",
            approved_by="bjorn",
        ),
    )
    _git(repo, "merge", "--no-ff", "merge-source", "-m", merge_message)

    accepted = _validate_pre_push(repo, baseline, "HEAD")
    assert accepted.returncode == 0, accepted.stderr
    assert "validated" in accepted.stdout

    legacy_only = _validate_pre_push(repo, "", baseline)
    assert legacy_only.returncode == 0
    assert "validated 0 pushed commit(s)" in legacy_only.stdout
