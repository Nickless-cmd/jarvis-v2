"""Unit tests for verification_gate (R2 of reasoning-layer rollout)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.verification_gate import (
    _scan,
    evaluate_verification_gate,
    verification_gate_section,
)


def _evt(tool: str, status: str = "ok", minutes_ago: float = 1.0, kind: str = "tool.completed", extra_payload: dict | None = None) -> dict:
    payload = {"tool": tool, "status": status}
    if extra_payload:
        payload.update(extra_payload)
    return {
        "kind": kind,
        "created_at": (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat(),
        "payload": payload,
    }


def test_scan_classifies_mutations_and_verifies():
    events = [
        _evt("write_file", "ok"),
        _evt("verify_file_contains", "ok"),
        _evt("read_file", "ok"),  # neither mutation nor verify
    ]
    s = _scan(events)
    assert len(s["mutations"]) == 1
    assert len(s["verifies"]) == 1
    assert len(s["failed_verifies"]) == 0


def test_failed_verify_counted():
    events = [
        _evt("verify_file_contains", "failed"),
    ]
    s = _scan(events)
    assert len(s["failed_verifies"]) == 1


def test_evaluate_returns_zero_on_empty():
    with patch("core.services.verification_gate._recent_events", return_value=[]):
        result = evaluate_verification_gate()
    assert result["mutation_count"] == 0
    assert result["verify_count"] == 0
    assert result["unverified_count"] == 0


def test_evaluate_unverified_signal():
    events = [_evt("write_file"), _evt("write_file"), _evt("edit_file")]
    with patch("core.services.verification_gate._recent_events", return_value=events):
        result = evaluate_verification_gate()
    assert result["mutation_count"] == 3
    assert result["unverified_count"] == 3
    assert result["suggestions"]
    assert any("verify_file_contains" in s for s in result["suggestions"])


def test_evaluate_balanced_no_warning():
    events = [_evt("write_file"), _evt("verify_file_contains")]
    with patch("core.services.verification_gate._recent_events", return_value=events):
        result = evaluate_verification_gate()
    assert result["mutation_count"] == 1
    assert result["verify_count"] == 1
    assert result["unverified_count"] == 0


def test_section_returns_none_when_clean():
    with patch("core.services.verification_gate._recent_events", return_value=[]):
        assert verification_gate_section() is None


def test_section_surfaces_failed_verify():
    events = [_evt("verify_file_contains", "failed")]
    with patch("core.services.verification_gate._recent_events", return_value=events):
        section = verification_gate_section()
    assert section is not None
    assert "fejlede" in section.lower() or "failed" in section.lower()


def test_section_surfaces_unverified():
    events = [_evt("write_file"), _evt("write_file"), _evt("write_file")]
    with patch("core.services.verification_gate._recent_events", return_value=events):
        section = verification_gate_section()
    assert section is not None
    assert "verify_file_contains" in section


def test_tool_exec_wrapper():
    from core.services.verification_gate import _exec_verification_status
    with patch("core.services.verification_gate._recent_events", return_value=[]):
        result = _exec_verification_status({"minutes": 5})
    assert result["status"] == "ok"
    assert result["window_minutes"] == 5


def test_tool_exec_clamps_minutes():
    from core.services.verification_gate import _exec_verification_status
    with patch("core.services.verification_gate._recent_events", return_value=[]):
        result = _exec_verification_status({"minutes": 9999})
    assert result["window_minutes"] == 120


# ── R2 noise-reduktion: shell-kommando-klassifikator (2026-06-13) ────────
import pytest
from core.services.verification_gate import shell_command_is_mutating, _scan


@pytest.mark.parametrize("cmd", [
    "grep -rn foo bar/", "cat file.py", "ls -la", "git status",
    "git log --oneline -5", "git diff", "systemctl status jarvis-api",
    "ps aux | grep python", "wc -l *.py", 'find . -name "*.py"', "echo hej",
    'sed -n "1,5p" f.py', "journalctl -u x", "ollama list", "head -40 x.md",
])
def test_readonly_shell_not_mutating(cmd):
    assert shell_command_is_mutating(cmd) is False


@pytest.mark.parametrize("cmd", [
    "rm -rf /tmp/x", "git commit -m x", "git push origin main",
    "sed -i s/a/b/ f", "echo x > file", "cat a >> b",
    "systemctl restart jarvis-api", "mv a b", "dpkg -i x.deb",
    "pip install foo", "python script.py", "sudo systemctl restart x",
    "mkdir newdir", "touch f", "curl -X POST url",
])
def test_mutating_shell_is_mutating(cmd):
    assert shell_command_is_mutating(cmd) is True


def test_empty_command_not_mutating():
    assert shell_command_is_mutating("") is False
    assert shell_command_is_mutating("   ") is False


def test_scan_skips_readonly_bash():
    # En read-only bash (mutating=False) tæller IKKE som mutation.
    events = [
        {"kind": "tool.completed", "created_at": "2026-06-13T00:00:00+00:00",
         "payload": {"tool": "bash", "status": "ok", "mutating": False}},
        {"kind": "tool.completed", "created_at": "2026-06-13T00:00:01+00:00",
         "payload": {"tool": "bash", "status": "ok", "mutating": True}},
    ]
    scan = _scan(events)
    assert len(scan["mutations"]) == 1  # kun den mutating bash


def test_scan_legacy_bash_without_flag_counts():
    # Gamle events uden "mutating"-flag → default True (sikkerhed/back-compat).
    events = [
        {"kind": "tool.completed", "created_at": "2026-06-13T00:00:00+00:00",
         "payload": {"tool": "bash", "status": "ok"}},
    ]
    assert len(_scan(events)["mutations"]) == 1
