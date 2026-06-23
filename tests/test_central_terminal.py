"""Tests for central_terminal — owner-command-line ind i Centralen (Bjørn 2026-06-23)."""
from __future__ import annotations

from core.services.central_terminal import run_command


def test_help_lists_commands():
    r = run_command("help")
    assert r["ok"] and any("status" in ln for ln in r["lines"])


def test_empty_line_is_noop():
    r = run_command("   ")
    assert r["ok"] and r["lines"] == []


def test_unknown_command_is_error_not_throw():
    r = run_command("frobnicate")
    assert r["ok"] is False and "ukendt kommando" in r["lines"][0]


def test_status_renders_coverage(monkeypatch):
    import core.services.central_terminal as ct
    monkeypatch.setattr(ct, "_q", lambda action, **k: {
        "status": "ok", "action": "status",
        "data": {"status": "green", "coverage": {"nerves": 116, "clusters": 21},
                 "open_breakers": 0, "unresolved_incidents": 2, "clusters": {"truth": "green"}},
        "error": None, "meta": {},
    })
    r = run_command("status")
    assert r["ok"] and "nerver=116" in r["lines"][0] and "GREEN" in r["lines"][0]


def test_toggle_requires_on_off():
    r = run_command("toggle some_nerve")
    assert r["ok"] is False and "on|off" in r["lines"][0]


def test_toggle_security_nerve_refused():
    # tool_access er sikkerheds-nerve → central_query afviser → terminalen viser fejl-linjen
    r = run_command("toggle tool_access off")
    assert r["ok"] is False and "sikkerheds-nerve" in r["lines"][0]


def test_nerve_requires_name():
    r = run_command("nerve")
    assert r["ok"] is False and "nerve <navn>" in r["lines"][0]
