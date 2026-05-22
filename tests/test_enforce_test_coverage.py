"""Tests for scripts/enforce_test_coverage.py — the pre-commit hook."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

ENFORCE_SCRIPT = REPO_ROOT / "scripts" / "enforce_test_coverage.py"


@pytest.fixture
def empty_git_worktree(tmp_path: Path) -> Path:
    """Create a temporary git repo with core/ and tests/ dirs."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, capture_output=True,
    )
    (repo / "core").mkdir()
    (repo / "tests").mkdir()
    return repo


def _run_enforce(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Run the enforce script against a temp repo with --repo-root."""
    cmd = [sys.executable, str(ENFORCE_SCRIPT), "--repo-root", str(repo), *args]
    return subprocess.run(cmd, cwd=repo, capture_output=True, text=True)


class TestEnforceTestCoverage:
    """Tests for the pre-commit enforcement script."""

    def test_blocks_commit_when_test_missing(self, empty_git_worktree: Path):
        """A core file without a matching test file should be blocked."""
        repo = empty_git_worktree
        core_file = repo / "core" / "foo.py"
        core_file.write_text("# foo module")
        subprocess.run(["git", "add", str(core_file)], cwd=repo, capture_output=True)

        result = _run_enforce(repo)

        assert result.returncode != 0, "Should have blocked commit"
        assert "MISSING" in result.stderr or "blocked" in result.stderr

    def test_allows_commit_when_test_exists(self, empty_git_worktree: Path):
        """A core file WITH a matching test file should pass."""
        repo = empty_git_worktree
        core_file = repo / "core" / "bar.py"
        test_file = repo / "tests" / "test_bar.py"
        core_file.write_text("# bar module")
        test_file.write_text("# test bar")
        subprocess.run(["git", "add", str(core_file)], cwd=repo, capture_output=True)
        subprocess.run(["git", "add", str(test_file)], cwd=repo, capture_output=True)

        result = _run_enforce(repo)

        assert result.returncode == 0, "Should have allowed commit"

    def test_ignores_init_py(self, empty_git_worktree: Path):
        """__init__.py files should not require test files."""
        repo = empty_git_worktree
        core_file = repo / "core" / "__init__.py"
        core_file.write_text("# init")
        subprocess.run(["git", "add", str(core_file)], cwd=repo, capture_output=True)

        result = _run_enforce(repo)

        assert result.returncode == 0, "__init__.py should be skipped"

    def test_skips_non_core_files(self, empty_git_worktree: Path):
        """Files outside core/ should not be checked."""
        repo = empty_git_worktree
        scripts_dir = repo / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        scripts_file = scripts_dir / "some_tool.py"
        scripts_file.write_text("# script")
        subprocess.run(["git", "add", str(scripts_file)], cwd=repo, capture_output=True)

        result = _run_enforce(repo)

        assert result.returncode == 0, "scripts/ files should be skipped"

    def test_no_staged_files_passes(self, empty_git_worktree: Path):
        """No staged files should pass cleanly."""
        repo = empty_git_worktree

        result = _run_enforce(repo)

        assert result.returncode == 0, "No staged files = should pass"

    def test_multiple_files_reports_all_missing(self, empty_git_worktree: Path):
        """Multiple missing test files should all be reported."""
        repo = empty_git_worktree
        for name in ("alpha.py", "beta.py", "gamma.py"):
            f = repo / "core" / name
            f.write_text(f"# {name}")
            subprocess.run(["git", "add", str(f)], cwd=repo, capture_output=True)

        result = _run_enforce(repo)

        assert result.returncode != 0
        assert "test_alpha.py" in result.stderr
        assert "test_beta.py" in result.stderr
        assert "test_gamma.py" in result.stderr
