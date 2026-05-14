"""Tests for read_before_write_guard — cross-worker + bash overwrite detection."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.services import read_before_write_guard as rbw
from core.services import shared_cache as sc


@pytest.fixture(autouse=True)
def _clean_state():
    sc.invalidate_prefix(rbw._CACHE_KEY_PREFIX)
    yield
    sc.invalidate_prefix(rbw._CACHE_KEY_PREFIX)


@pytest.fixture
def protected_file(tmp_path):
    """Create a SOUL.md file with content to be protected."""
    f = tmp_path / "SOUL.md"
    f.write_text("# SOUL\n\noriginal content\n", encoding="utf-8")
    return f


# ── write_file guard ─────────────────────────────────────────


def test_write_unprotected_file_always_allowed(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello", encoding="utf-8")
    allowed, reason = rbw.check_read_before_write(str(f), session_id="s1")
    assert allowed is True
    assert reason is None


def test_write_new_protected_file_allowed(tmp_path):
    """If the protected file doesn't exist yet, allow — no data to lose."""
    target = tmp_path / "SOUL.md"
    allowed, reason = rbw.check_read_before_write(str(target), session_id="s1")
    assert allowed is True


def test_write_existing_protected_without_read_blocked(protected_file):
    allowed, reason = rbw.check_read_before_write(str(protected_file), session_id="s1")
    assert allowed is False
    assert "READ-BEFORE-WRITE GUARD" in reason
    assert "SOUL.md" in reason


def test_write_after_read_allowed(protected_file):
    rbw.record_read(str(protected_file), session_id="s1")
    allowed, reason = rbw.check_read_before_write(str(protected_file), session_id="s1")
    assert allowed is True


def test_read_in_other_session_does_not_help(protected_file):
    rbw.record_read(str(protected_file), session_id="s2")
    allowed, _ = rbw.check_read_before_write(str(protected_file), session_id="s1")
    assert allowed is False


def test_default_session_read_satisfies_any_session(protected_file):
    """Many callers pass session_id='default'. A read under 'default' should
    also satisfy a write check from any session — fallback path."""
    rbw.record_read(str(protected_file), session_id="default")
    allowed, _ = rbw.check_read_before_write(str(protected_file), session_id="custom")
    assert allowed is True


# ── bash command guard ──────────────────────────────────────


def test_bash_safe_command_allowed():
    allowed, _ = rbw.check_bash_command_safe("ls -la /tmp")
    assert allowed is True


def test_bash_safe_grep_with_filename_in_match_allowed():
    """grep'ing for a string that contains 'SOUL.md' should NOT trigger the
    overwrite-pattern detector — only cp/mv/>/tee/sed do."""
    allowed, _ = rbw.check_bash_command_safe("grep SOUL.md /some/file.txt")
    assert allowed is True


def test_bash_cp_to_protected_file_blocked(protected_file, tmp_path):
    """cp source.txt SOUL.md without prior read → block."""
    src = tmp_path / "new.md"
    src.write_text("new", encoding="utf-8")
    cmd = f"cp {src} {protected_file}"
    allowed, reason = rbw.check_bash_command_safe(cmd)
    assert allowed is False
    assert "SOUL.md" in reason


def test_bash_cp_to_protected_file_allowed_after_read(protected_file, tmp_path):
    src = tmp_path / "new.md"
    src.write_text("new", encoding="utf-8")
    rbw.record_read(str(protected_file))
    cmd = f"cp {src} {protected_file}"
    allowed, _ = rbw.check_bash_command_safe(cmd)
    assert allowed is True


def test_bash_cp_to_directory_containing_protected_blocked(protected_file, tmp_path):
    """cp source.md /target/dir/ where dir contains SOUL.md → block."""
    src = tmp_path / "new_SOUL.md"
    src.write_text("new soul", encoding="utf-8")
    target_dir = protected_file.parent
    # Simulate Jarvis' bug: cp src/SOUL.md /target/dir/  → lands as dir/SOUL.md
    src.rename(target_dir.parent / "src_SOUL.md")
    src = target_dir.parent / "src_SOUL.md"
    cmd = f"cp {src.parent}/SOUL.md {target_dir}/"
    allowed, reason = rbw.check_bash_command_safe(cmd)
    # The detector should flag protected_file as target. SOUL.md is in cmd
    # and protected_file exists in target_dir.
    assert allowed is False
    assert "SOUL.md" in reason


def test_bash_redirect_to_protected_blocked(protected_file):
    cmd = f"echo 'new content' > {protected_file}"
    allowed, reason = rbw.check_bash_command_safe(cmd)
    assert allowed is False


def test_bash_append_redirect_to_protected_blocked(protected_file):
    cmd = f"echo 'append' >> {protected_file}"
    allowed, reason = rbw.check_bash_command_safe(cmd)
    assert allowed is False


def test_bash_tee_to_protected_blocked(protected_file):
    cmd = f"echo 'new' | tee {protected_file}"
    allowed, reason = rbw.check_bash_command_safe(cmd)
    assert allowed is False


def test_bash_mv_to_protected_blocked(protected_file, tmp_path):
    src = tmp_path / "new.md"
    src.write_text("new", encoding="utf-8")
    cmd = f"mv {src} {protected_file}"
    allowed, reason = rbw.check_bash_command_safe(cmd)
    assert allowed is False


def test_bash_command_without_protected_pathname_allowed():
    cmd = "cp /tmp/foo.txt /tmp/bar.txt"
    allowed, _ = rbw.check_bash_command_safe(cmd)
    assert allowed is True


def test_record_read_persists_to_shared_cache(protected_file):
    rbw.record_read(str(protected_file), session_id="test-session")
    reads = rbw.get_session_reads("test-session")
    assert str(protected_file.resolve()) in reads


def test_clear_session(protected_file):
    rbw.record_read(str(protected_file), session_id="to-clear")
    assert len(rbw.get_session_reads("to-clear")) > 0
    rbw.clear_session("to-clear")
    assert rbw.get_session_reads("to-clear") == set()


def test_is_protected():
    assert rbw.is_protected("/path/SOUL.md") is True
    assert rbw.is_protected("/path/IDENTITY.md") is True
    assert rbw.is_protected("/path/random.md") is False
    assert rbw.is_protected("/path/SOUL.md.bak") is False
