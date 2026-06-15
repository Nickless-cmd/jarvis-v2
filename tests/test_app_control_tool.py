"""Tests for app_control_tool (spec 2026-06-15)."""
from __future__ import annotations

from core.tools.app_control_tool import (
    APP_CONTROL_TOOL_DEFINITIONS,
    VALID_APP_ACTIONS,
    _exec_request_app_action,
    build_app_action_event,
)


def test_valid_action_returns_marker() -> None:
    r = _exec_request_app_action({"action": "switch_to_code_mode", "reason": "kræver filer"})
    assert r["status"] == "ok"
    assert r["app_action"] == {"action": "switch_to_code_mode", "reason": "kræver filer"}
    assert r["text"]  # menneskelig note som modellen ser


def test_request_full_access_valid() -> None:
    r = _exec_request_app_action({"action": "request_full_access"})
    assert r["status"] == "ok"
    assert r["app_action"]["action"] == "request_full_access"


def test_unknown_action_errors() -> None:
    r = _exec_request_app_action({"action": "delete_everything"})
    assert r["status"] == "error"
    assert "ukendt action" in r["error"]


def test_build_event_from_marker() -> None:
    result = {"status": "ok", "app_action": {"action": "switch_to_code_mode", "reason": "x"}}
    ev = build_app_action_event(result, user_message="ret bug", session_id="s1")
    assert ev == {
        "type": "app_action_request",
        "action": "switch_to_code_mode",
        "reason": "x",
        "original_message": "ret bug",
        "session_id": "s1",
    }


def test_build_event_none_without_marker() -> None:
    assert build_app_action_event({"status": "ok"}, user_message="x", session_id="s") is None
    assert build_app_action_event(None, user_message="x", session_id="s") is None


def test_build_event_rejects_bad_action() -> None:
    result = {"app_action": {"action": "nope"}}
    assert build_app_action_event(result, user_message="x", session_id="s") is None


def test_tool_definition_shape() -> None:
    d = APP_CONTROL_TOOL_DEFINITIONS[0]
    assert d["function"]["name"] == "request_app_action"
    assert set(d["function"]["parameters"]["properties"]) == {"action", "reason"}
    assert d["function"]["parameters"]["properties"]["action"]["enum"] == list(VALID_APP_ACTIONS)
