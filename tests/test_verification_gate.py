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
