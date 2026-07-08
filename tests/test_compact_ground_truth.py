"""Tests for compact_ground_truth KEY_FILES honesty.

KEY_FILES lists files that compaction LLMs frequently mis-claim as "missing".
The list is only useful if every entry actually exists — a stale entry (a file
that was deleted) would make the ground-truth check itself lie. This guards
against that regression."""
from pathlib import Path

from core.context.compact_ground_truth import KEY_FILES, REPO_DIR


def test_all_key_files_exist():
    missing = [f for f in KEY_FILES if not (REPO_DIR / f).exists()]
    assert missing == [], f"KEY_FILES contains non-existent paths: {missing}"


def test_deleted_run_compact_not_in_key_files():
    # run_compact.py was removed in harness Part B (dead code); it must not
    # linger in KEY_FILES or the existence check would flag a false "missing".
    assert "core/context/run_compact.py" not in KEY_FILES


def test_key_files_are_relative_repo_paths():
    for f in KEY_FILES:
        assert not Path(f).is_absolute(), f"KEY_FILES entry must be repo-relative: {f}"
