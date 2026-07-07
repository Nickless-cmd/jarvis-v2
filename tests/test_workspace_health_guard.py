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
    """A file below 500B triggers minimum-size warning — begge er CRITICAL (ægte stub-kollaps)."""
    f = tmp_path / "SOUL.md"
    f.write_text("stub")
    warnings = _check_workspace_file_health(tmp_path, "SOUL.md", {"SOUL.md": 5000})
    assert len(warnings) == 2  # both min-size and shrinkage
    assert warnings[0][0] == "critical" and "under minimum" in warnings[0][1]
    # shrinkage under minimum → OGSÅ critical
    assert all(lvl == "critical" for lvl, _ in warnings)


def test_shrinkage_alarm_below_min_is_critical(tmp_path: Path) -> None:
    """En fil der skrumper <50% OG er under minimum → CRITICAL (stub-kollaps)."""
    f = tmp_path / "USER.md"
    f.write_text("x" * 100)   # 100B < 500B min
    warnings = _check_workspace_file_health(tmp_path, "USER.md", {"USER.md": 5000})
    shrink = [(lvl, w) for lvl, w in warnings if "shrank" in w]
    assert shrink and shrink[0][0] == "critical"


def test_substantial_shrinkage_is_only_warning(tmp_path: Path) -> None:
    """KERNE-FIX: en LEGITIM kuratering (140KB→4KB, stadig substantiel ≥500B) → WARNING, ikke
    CRITICAL → farver ikke Centralen rød."""
    f = tmp_path / "MEMORY.md"
    f.write_text("x" * 4392)   # 4KB > 500B min
    warnings = _check_workspace_file_health(tmp_path, "MEMORY.md", {"MEMORY.md": 139827})
    shrink = [(lvl, w) for lvl, w in warnings if "shrank" in w]
    assert shrink and shrink[0][0] == "warning"   # IKKE critical


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
