"""Tests for self-tools handlers in simple_tools."""
from __future__ import annotations

import json
from unittest.mock import patch


def _call_handler(name: str, args: dict):
    """Call a tool handler by name via _TOOL_HANDLERS."""
    from core.tools import simple_tools
    handler = simple_tools._TOOL_HANDLERS[name]
    return handler(args)


# ── daemon_status ──────────────────────────────────────────────────────

def test_daemon_status_returns_all_daemons():
    result = _call_handler("daemon_status", {})
    assert "daemons" in result
    assert len(result["daemons"]) == 21
    names = {d["name"] for d in result["daemons"]}
    assert "curiosity" in names
    assert "desire" in names


# ── control_daemon ─────────────────────────────────────────────────────

def test_control_daemon_enable():
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "control_daemon") as mock_ctrl:
        mock_ctrl.return_value = {"ok": True, "name": "curiosity", "action": "enable"}
        result = _call_handler("control_daemon", {"name": "curiosity", "action": "enable"})
    assert result["ok"] is True
    mock_ctrl.assert_called_once_with("curiosity", "enable", interval_minutes=None)


def test_control_daemon_unknown_returns_error():
    result = _call_handler("control_daemon", {"name": "ghost", "action": "enable"})
    assert "error" in result
    assert "valid" in result


def test_control_daemon_set_interval():
    from apps.api.jarvis_api.services import daemon_manager
    with patch.object(daemon_manager, "control_daemon") as mock_ctrl:
        mock_ctrl.return_value = {"ok": True, "name": "curiosity", "action": "set_interval"}
        result = _call_handler("control_daemon", {
            "name": "curiosity",
            "action": "set_interval",
            "interval_minutes": 20,
        })
    assert result["ok"] is True
    mock_ctrl.assert_called_once_with("curiosity", "set_interval", interval_minutes=20)


# ── list_signal_surfaces ───────────────────────────────────────────────

def test_list_signal_surfaces_returns_dict():
    result = _call_handler("list_signal_surfaces", {})
    assert isinstance(result, dict)
    assert "surfaces" in result
    assert len(result["surfaces"]) > 10


# ── read_signal_surface ────────────────────────────────────────────────

def test_read_signal_surface_known_name():
    result = _call_handler("read_signal_surface", {"name": "autonomy_pressure"})
    assert isinstance(result, dict)
    assert "error" not in result


def test_read_signal_surface_unknown_name():
    result = _call_handler("read_signal_surface", {"name": "not_real"})
    assert "error" in result
    assert "valid" in result


# ── eventbus_recent ────────────────────────────────────────────────────

def test_eventbus_recent_returns_list():
    result = _call_handler("eventbus_recent", {})
    assert "events" in result
    assert isinstance(result["events"], list)


def test_eventbus_recent_respects_limit():
    from core.eventbus.bus import event_bus
    event_bus.publish("heartbeat.test", {"source": "test"})
    result = _call_handler("eventbus_recent", {"limit": 1})
    assert len(result["events"]) <= 1


def test_eventbus_recent_filters_by_kind():
    from core.eventbus.bus import event_bus
    event_bus.publish("heartbeat.test_filter", {"source": "filter_test"})
    result = _call_handler("eventbus_recent", {"kind": "heartbeat", "limit": 50})
    for event in result["events"]:
        assert event["kind"].startswith("heartbeat")


# ── update_setting ─────────────────────────────────────────────────────

def test_update_setting_non_sensitive_returns_old_and_new(tmp_path):
    import core.runtime.config as _cfg

    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"relevance_model_name": "llama3.1:8b"}))
    with patch.object(_cfg, "SETTINGS_FILE", settings_file):
        result = _call_handler("update_setting", {
            "key": "relevance_model_name",
            "value": "llama3.1:70b",
        })
    assert result["key"] == "relevance_model_name"
    assert result["old"] == "llama3.1:8b"
    assert result["new"] == "llama3.1:70b"


def test_update_setting_sensitive_key_triggers_approval():
    result = _call_handler("update_setting", {
        "key": "visible_auth_profile",
        "value": "new-profile",
    })
    assert result.get("requires_approval") is True
    assert "key" in result


def test_update_setting_unknown_key_returns_error():
    result = _call_handler("update_setting", {"key": "not_a_real_key", "value": "x"})
    assert "error" in result
    assert "valid_keys" in result
