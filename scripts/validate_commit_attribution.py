#!/usr/bin/env python3
"""Validate commit attribution for commit-msg and pre-push hooks."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.services.commit_attribution import validate_commit_message


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=20,
    )


def validate_message_file(path: Path) -> tuple[str, ...]:
    """Validate one COMMIT_EDITMSG-style file."""

    try:
        message = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return (f"cannot read commit message {path}: {exc}",)
    return validate_commit_message(message)


def _rev_list(repo: Path, revision: str) -> tuple[str, ...]:
    result = _git(repo, "rev-list", "--reverse", revision)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "git rev-list failed").strip()
        raise ValueError(detail)
    return tuple(line for line in result.stdout.splitlines() if line)


def commits_in_enforced_range(
    repo: Path,
    baseline: str,
    from_ref: str,
    to_ref: str,
) -> tuple[str, ...]:
    """Return pushed commits that are also newer than the activation baseline."""

    root = Path(repo).resolve()
    ancestor = _git(root, "merge-base", "--is-ancestor", baseline, to_ref)
    if ancestor.returncode != 0:
        raise ValueError(
            f"commit attribution baseline {baseline[:12]} is not an ancestor of {to_ref}"
        )
    after_baseline = _rev_list(root, f"{baseline}..{to_ref}")
    if not from_ref:
        return after_baseline
    pushed = set(_rev_list(root, f"{from_ref}..{to_ref}"))
    return tuple(commit for commit in after_baseline if commit in pushed)


def validate_range(
    repo: Path,
    commits: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    """Return validation failures keyed by commit hash."""

    failures: dict[str, tuple[str, ...]] = {}
    for commit in commits:
        shown = _git(Path(repo), "show", "-s", "--format=%B", commit)
        if shown.returncode != 0:
            failures[commit] = (
                (shown.stderr or shown.stdout or "cannot read commit").strip(),
            )
            continue
        errors = validate_commit_message(shown.stdout)
        if errors:
            failures[commit] = errors
    return failures


def _print_failures(failures: dict[str, tuple[str, ...]]) -> None:
    for commit, errors in failures.items():
        print(f"commit attribution failed for {commit}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)


def _pre_push(repo: Path) -> int:
    baseline_path = repo / ".commit-attribution-baseline"
    if not baseline_path.is_file():
        print("commit attribution: audit mode (no baseline)")
        return 0
    baseline = baseline_path.read_text(encoding="utf-8").strip()
    if not baseline:
        print("commit attribution: baseline file is empty", file=sys.stderr)
        return 1
    from_ref = os.environ.get("PRE_COMMIT_FROM_REF", "").strip()
    to_ref = os.environ.get("PRE_COMMIT_TO_REF", "").strip()
    if not to_ref:
        local_branch = os.environ.get("PRE_COMMIT_LOCAL_BRANCH", "").strip()
        to_ref = local_branch or "HEAD"
    try:
        commits = commits_in_enforced_range(repo, baseline, from_ref, to_ref)
        failures = validate_range(repo, commits)
    except (OSError, ValueError) as exc:
        print(f"commit attribution: {exc}", file=sys.stderr)
        return 1
    if failures:
        _print_failures(failures)
        return 1
    print(f"commit attribution: validated {len(commits)} pushed commit(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--message-file", type=Path)
    mode.add_argument("--pre-push", action="store_true")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.message_file is not None:
        errors = validate_message_file(args.message_file)
        if errors:
            _print_failures({"COMMIT_EDITMSG": errors})
            return 1
        return 0
    return _pre_push(args.repo.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
