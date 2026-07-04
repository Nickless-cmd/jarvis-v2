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


# ── §7.2: egress-frit Central-observe af gate-beslutningen ───────────────
import core.services.verification_gate as _vg_mod


def _capture_observe(monkeypatch):
    """Fang record_private-kald via central_private_observe (som gaten importerer lokalt)."""
    calls: list[dict] = []
    import core.services.central_private_observe as cpo

    def _fake(cluster, nerve, *, value=1.0, meta=None, reason=""):
        calls.append({"cluster": cluster, "nerve": nerve, "value": value,
                      "meta": meta or {}, "reason": reason})
        return True

    monkeypatch.setattr(cpo, "record_private", _fake)
    return calls


def test_section_observes_pass_when_clean(monkeypatch):
    calls = _capture_observe(monkeypatch)
    with patch("core.services.verification_gate._recent_events", return_value=[]):
        assert verification_gate_section() is None
    assert len(calls) == 1
    c = calls[0]
    assert c["cluster"] == "review"
    assert c["nerve"] == "verification_gate"
    assert c["value"] == 1.0
    assert c["meta"]["decision"] == "pass"


def test_section_observes_surface_when_unverified(monkeypatch):
    calls = _capture_observe(monkeypatch)
    events = [_evt("write_file"), _evt("write_file"), _evt("write_file")]
    with patch("core.services.verification_gate._recent_events", return_value=events):
        section = verification_gate_section()
    assert section is not None
    assert len(calls) == 1
    c = calls[0]
    assert c["value"] == 0.0
    assert c["meta"]["decision"] == "surface"
    assert c["meta"]["unverified"] == 3


def test_observe_never_touches_eventbus(monkeypatch):
    # Egress-frit: gate-observe må ALDRIG nå eventbus (§24.4).
    published: list = []
    import core.eventbus.bus as bus
    monkeypatch.setattr(bus.event_bus, "publish", lambda *a, **k: published.append((a, k)))
    with patch("core.services.verification_gate._recent_events", return_value=[]):
        verification_gate_section()
    assert published == []


def test_observe_failure_does_not_break_gate(monkeypatch):
    # Self-safe: observe-fejl må aldrig ændre gate-beslutningen.
    import core.services.central_private_observe as cpo
    monkeypatch.setattr(cpo, "record_private",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with patch("core.services.verification_gate._recent_events", return_value=[]):
        assert verification_gate_section() is None  # gaten fungerer stadig
