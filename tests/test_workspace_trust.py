"""Tests for workspace_trust (trusted-folder gate)."""
from core.services import workspace_trust as wt


def test_untrusted_by_default():
    assert wt.is_trusted("u1", "container", "core") is False


def test_set_and_clear_trust():
    wt.set_trusted("u1", "container", "core", True)
    assert wt.is_trusted("u1", "container", "core") is True
    wt.set_trusted("u1", "container", "core", False)
    assert wt.is_trusted("u1", "container", "core") is False


def test_trust_is_per_user_and_root():
    wt.set_trusted("u1", "container", "apps", True)
    assert wt.is_trusted("u1", "container", "apps") is True
    assert wt.is_trusted("u2", "container", "apps") is False
    assert wt.is_trusted("u1", "container", "core") is False


def test_guard_allows_non_write_tools():
    wt.set_trust_context(kind="container", root="core", trusted=False)
    try:
        assert wt.guard_code_write("read_file") is None
        assert wt.guard_code_write("operator_read_file") is None
    finally:
        wt.clear_trust_context()


def test_guard_blocks_write_in_untrusted_workspace():
    wt.set_trust_context(kind="container", root="core", trusted=False)
    try:
        msg = wt.guard_code_write("write_file")
        assert msg is not None and "ikke betroet" in msg
        assert wt.guard_code_write("operator_bash") is not None
    finally:
        wt.clear_trust_context()


def test_guard_allows_write_in_trusted_workspace():
    wt.set_trust_context(kind="container", root="core", trusted=True)
    try:
        assert wt.guard_code_write("write_file") is None
        assert wt.guard_code_write("bash") is None
    finally:
        wt.clear_trust_context()


def test_guard_noop_without_context():
    wt.clear_trust_context()
    assert wt.guard_code_write("write_file") is None
