"""Test workspace health guard — stub detection and shrinkage alarm."""
import pytest
from pathlib import Path
from core.identity.workspace_bootstrap import _check_workspace_file_health


def test_healthy_file_no_warnings(tmp_path: Path) -> None:
    """A healthy file above minimum size produces no warnings."""
    f = tmp_path / "SOUL.md"
    f.write_text("x" * 5000)
    warnings = _check_workspace_file_health(tmp_path, "SOUL.md", {"SOUL.md": 5000})
    assert warnings == []


def test_stub_file_warns(tmp_path: Path) -> None:
    """A file below 500B triggers minimum-size warning."""
    f = tmp_path / "SOUL.md"
    f.write_text("stub")
    warnings = _check_workspace_file_health(tmp_path, "SOUL.md", {"SOUL.md": 5000})
    assert len(warnings) == 2  # both min-size and shrinkage
    assert "below minimum" in warnings[0]


def test_shrinkage_alarm(tmp_path: Path) -> None:
    """A file that shrank >50% triggers alarm."""
    f = tmp_path / "USER.md"
    f.write_text("x" * 100)
    warnings = _check_workspace_file_health(tmp_path, "USER.md", {"USER.md": 5000})
    assert any("shrank" in w for w in warnings)


def test_non_identity_file_no_min_check(tmp_path: Path) -> None:
    """Non-critical files don't trigger min-size warning."""
    f = tmp_path / "HEARTBEAT.md"
    f.write_text("tiny")
    warnings = _check_workspace_file_health(tmp_path, "HEARTBEAT.md", {})
    assert warnings == []  # not identity-critical, no known size


def test_missing_file_no_warnings(tmp_path: Path) -> None:
    """Missing files produce no warnings (handled elsewhere)."""
    warnings = _check_workspace_file_health(tmp_path, "SOUL.md", {"SOUL.md": 5000})
    assert warnings == []
