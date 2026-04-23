# tests/test_mc_tabs_endpoints.py
from __future__ import annotations
import pytest


def _fake_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the filesystem. Use this to inspect code.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {}, "content": {}},
                    "required": ["path", "content"],
                },
            },
        },
    ]


# ---------------------------------------------------------------------------
# /mc/skills
# ---------------------------------------------------------------------------

def test_mc_skills_structure(monkeypatch):
    import apps.api.jarvis_api.routes.mission_control as mc
    monkeypatch.setattr(mc, "_get_all_tools", lambda: _fake_tools())
    monkeypatch.setattr(mc, "_skills_recent_invocations", lambda: [
        {"capability_name": "read_file", "status": "ok", "invoked_at": "2026-04-23T10:00:00"}
    ])
    monkeypatch.setattr(mc, "_skills_calls_today", lambda: 5)

    result = mc.mc_skills()

    assert result["total"] == 2
    assert len(result["tools"]) == 2
    assert result["tools"][0]["name"] == "read_file"
    assert result["tools"][1]["required"] == ["path", "content"]
    assert result["calls_today"] == 5
    assert len(result["recent_invocations"]) == 1


def test_mc_skills_tool_fields(monkeypatch):
    import apps.api.jarvis_api.routes.mission_control as mc
    monkeypatch.setattr(mc, "_get_all_tools", lambda: _fake_tools())
    monkeypatch.setattr(mc, "_skills_recent_invocations", lambda: [])
    monkeypatch.setattr(mc, "_skills_calls_today", lambda: 0)

    result = mc.mc_skills()
    tool = result["tools"][0]

    assert "name" in tool
    assert "description" in tool
    assert "required" in tool
    assert isinstance(tool["description"], str)
    assert len(tool["description"]) <= 120


# ---------------------------------------------------------------------------
# /mc/hardening
# ---------------------------------------------------------------------------

def test_mc_hardening_structure(monkeypatch):
    import apps.api.jarvis_api.routes.mission_control as mc
    monkeypatch.setattr(mc, "_hardening_approval_counts", lambda: {"pending": 2, "approved_today": 3, "denied_today": 1})
    monkeypatch.setattr(mc, "_hardening_autonomy_level", lambda: "direct")
    monkeypatch.setattr(mc, "_hardening_integrations", lambda: {
        "telegram": True, "discord": False, "home_assistant": False, "anthropic": True
    })
    monkeypatch.setattr(mc, "_hardening_recent_approvals", lambda: [
        {"intent_type": "write_file", "intent_target": "/tmp/f", "approval_state": "approved", "requested_at": "2026-04-23T10:00:00"}
    ])

    result = mc.mc_hardening()

    assert result["pending"] == 2
    assert result["approved_today"] == 3
    assert result["denied_today"] == 1
    assert result["autonomy_level"] == "direct"
    assert result["integrations"]["telegram"] is True
    assert result["integrations"]["discord"] is False
    assert len(result["recent_approvals"]) == 1


def test_mc_hardening_integrations_keys(monkeypatch):
    import apps.api.jarvis_api.routes.mission_control as mc
    monkeypatch.setattr(mc, "_hardening_approval_counts", lambda: {"pending": 0, "approved_today": 0, "denied_today": 0})
    monkeypatch.setattr(mc, "_hardening_autonomy_level", lambda: "direct")
    monkeypatch.setattr(mc, "_hardening_integrations", lambda: {
        "telegram": False, "discord": False, "home_assistant": False, "anthropic": False
    })
    monkeypatch.setattr(mc, "_hardening_recent_approvals", lambda: [])

    result = mc.mc_hardening()
    keys = set(result["integrations"].keys())

    assert keys == {"telegram", "discord", "home_assistant", "anthropic"}


# ---------------------------------------------------------------------------
# /mc/lab
# ---------------------------------------------------------------------------

def test_mc_lab_structure(monkeypatch):
    import apps.api.jarvis_api.routes.mission_control as mc
    monkeypatch.setattr(mc, "_lab_costs_today", lambda: {
        "total_usd": 0.05, "input_tokens": 10000, "output_tokens": 2000, "calls": 8
    })
    monkeypatch.setattr(mc, "_lab_providers_today", lambda: [
        {"provider": "anthropic", "cost_usd": 0.05, "input_tokens": 10000, "output_tokens": 2000, "calls": 8}
    ])
    monkeypatch.setattr(mc, "_lab_db_stats", lambda: {
        "events": 500, "runs": 50, "sessions": 5, "approvals": 10
    })
    monkeypatch.setattr(mc, "_lab_recent_events", lambda: [
        {"id": 1, "kind": "tool.called", "family": "tool", "created_at": "2026-04-23T10:00:00"}
    ])

    result = mc.mc_lab()

    assert result["costs_today"]["total_usd"] == 0.05
    assert result["costs_today"]["calls"] == 8
    assert len(result["providers_today"]) == 1
    assert result["db_stats"]["events"] == 500
    assert len(result["recent_events"]) == 1
    assert result["recent_events"][0]["family"] == "tool"


def test_mc_lab_providers_sorted(monkeypatch):
    import apps.api.jarvis_api.routes.mission_control as mc
    monkeypatch.setattr(mc, "_lab_costs_today", lambda: {"total_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "calls": 0})
    monkeypatch.setattr(mc, "_lab_providers_today", lambda: [
        {"provider": "anthropic", "cost_usd": 0.10, "input_tokens": 1000, "output_tokens": 200, "calls": 3},
        {"provider": "ollama", "cost_usd": 0.00, "input_tokens": 500, "output_tokens": 100, "calls": 5},
    ])
    monkeypatch.setattr(mc, "_lab_db_stats", lambda: {"events": 0, "runs": 0, "sessions": 0, "approvals": 0})
    monkeypatch.setattr(mc, "_lab_recent_events", lambda: [])

    result = mc.mc_lab()
    assert result["providers_today"][0]["provider"] == "anthropic"
