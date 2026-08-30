"""Execute Git commits with canonical attribution and no staging side effects."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from core.services.commit_attribution import (
    AttributionError,
    CommitAttribution,
    render_attributed_message,
)


@dataclass(frozen=True)
class AttributedCommitResult:
    """Process result plus the resulting commit hash when successful."""

    returncode: int
    stdout: str = ""
    stderr: str = ""
    sha: str = ""


def _git(
    repo: Path,
    *args: str,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _verify_staged_paths(
    repo: Path,
    paths: tuple[str, ...],
    *,
    timeout: int,
) -> str:
    if not paths:
        return ""
    staged = _git(repo, "diff", "--cached", "--name-only", "--", *paths, timeout=timeout)
    if staged.returncode != 0:
        return (staged.stderr or staged.stdout or "could not inspect staged paths").strip()
    staged_paths = set(staged.stdout.splitlines())
    missing = [path for path in paths if path not in staged_paths]
    if missing:
        return "paths are not staged: " + ", ".join(missing)
    clean = _git(repo, "diff", "--quiet", "--", *paths, timeout=timeout)
    if clean.returncode == 1:
        return "paths changed after staging: " + ", ".join(paths)
    if clean.returncode != 0:
        return (clean.stderr or "could not compare staged paths").strip()
    return ""


def commit_with_attribution(
    *,
    repo: Path,
    message: str,
    attribution: CommitAttribution,
    paths: Sequence[str] = (),
    author: str = "",
    timeout: int = 120,
    amend: bool = False,
) -> AttributedCommitResult:
    """Commit already-staged content with canonical audit trailers.

    The caller retains ownership of staging and path selection. When paths are
    supplied, each must be staged and byte-identical between index and working
    tree before Git is invoked.
    """

    root = Path(repo).resolve()
    selected = tuple(str(path) for path in paths if str(path))
    try:
        rendered = render_attributed_message(message, attribution)
    except AttributionError as exc:
        return AttributedCommitResult(returncode=2, stderr=str(exc))

    staging_error = _verify_staged_paths(root, selected, timeout=min(timeout, 15))
    if staging_error:
        return AttributedCommitResult(returncode=2, stderr=staging_error)

    message_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="jarvis-commit-",
            suffix=".msg",
            delete=False,
        ) as handle:
            message_path = handle.name
            os.chmod(message_path, 0o600)
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())

        command = ["commit", "-F", message_path]
        if amend:
            command.append("--amend")
        if author:
            command.extend(["--author", author])
        if selected:
            command.extend(["--", *selected])
        committed = _git(root, *command, timeout=timeout)
        if committed.returncode != 0:
            return AttributedCommitResult(
                returncode=committed.returncode,
                stdout=committed.stdout,
                stderr=committed.stderr,
            )
        resolved = _git(root, "rev-parse", "HEAD", timeout=min(timeout, 10))
        sha = resolved.stdout.strip() if resolved.returncode == 0 else ""
        return AttributedCommitResult(
            returncode=0,
            stdout=committed.stdout,
            stderr=committed.stderr,
            sha=sha,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return AttributedCommitResult(returncode=2, stderr=str(exc))
    finally:
        if message_path:
            try:
                Path(message_path).unlink()
            except OSError:
                pass
