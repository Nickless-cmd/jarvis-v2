"""Tests for app_control_tool (spec 2026-06-15, opdateret 2026-06-16 med scope)."""
from __future__ import annotations

from core.tools.app_control_tool import (
    APP_CONTROL_TOOL_DEFINITIONS,
    VALID_APP_ACTIONS,
    VALID_PANELS,
    VALID_SCOPES,
    _exec_open_ui_panel,
    _exec_request_app_action,
    build_app_action_event,
)


def test_valid_action_returns_marker() -> None:
    r = _exec_request_app_action({"action": "switch_to_code_mode", "reason": "kræver filer"})
    # Ærlig kvittering: PENDING (afventer klik), ikke falsk "ok"/success.
    assert r["status"] == "pending" and r["confirmed"] is False and r["awaiting_approval"] is True
    assert r["app_action"] == {"action": "switch_to_code_mode", "reason": "kræver filer"}
    assert r["text"] and r["dispatched"] is True


def test_invalid_action_returns_error() -> None:
    r = _exec_request_app_action({"action": "foobar"})
    assert r["status"] == "error"


def test_build_app_action_event_missing_result() -> None:
    assert build_app_action_event(None, user_message="hej", session_id="s1") is None


def test_build_app_action_event_no_marker() -> None:
    assert build_app_action_event({"status": "ok"}, user_message="hej", session_id="s1") is None


def test_build_app_action_event_with_marker() -> None:
    ev = build_app_action_event(
        {"app_action": {"action": "switch_to_code_mode", "reason": "test"}},
        user_message="skift til code mode",
        session_id="s-test",
    )
    assert ev is not None
    assert ev["type"] == "app_action_request"
    assert ev["action"] == "switch_to_code_mode"
    assert ev["original_message"] == "skift til code mode"
    assert ev["session_id"] == "s-test"


# ─── open_ui_panel tests ──────────────────────────────────────────────────────


def test_open_ui_panel_default_action() -> None:
    """Action default er 'open'."""
    r = _exec_open_ui_panel({"panel": "file_tree", "detail": "core/tools/app_control_tool.py"})
    assert r["status"] == "ok"
    assert r["panel_request"]["action"] == "open"
    assert r["panel_request"]["panel"] == "file_tree"
    assert r["panel_request"]["detail"] == "core/tools/app_control_tool.py"
    assert r["panel_request"]["scope"] == "repo"


def test_open_ui_panel_workstation_scope() -> None:
    """scope='workstation' accepteres og gemmes i panel_request."""
    r = _exec_open_ui_panel({
        "panel": "file_tree",
        "detail": "src/main.rs",
        "scope": "workstation",
    })
    assert r["status"] == "ok"
    assert r["panel_request"]["scope"] == "workstation"
    assert r["panel_request"]["detail"] == "src/main.rs"


def test_open_ui_panel_close() -> None:
    r = _exec_open_ui_panel({"action": "close"})
    assert r["status"] == "ok"
    assert r["panel_request"]["action"] == "close"


def test_open_ui_panel_invalid_panel() -> None:
    r = _exec_open_ui_panel({"panel": "nonexistent"})
    assert r["status"] == "error"


def test_open_ui_panel_missing_panel_on_open() -> None:
    r = _exec_open_ui_panel({"action": "open"})
    assert r["status"] == "error"


def test_open_ui_panel_invalid_scope() -> None:
    r = _exec_open_ui_panel({"panel": "file_tree", "scope": "cloud"})
    assert r["status"] == "error"


def test_open_ui_panel_all_valid_panels() -> None:
    for panel in sorted(VALID_PANELS):
        r = _exec_open_ui_panel({"panel": panel, "detail": "test"})
        assert r["status"] == "ok", f"panel={panel} fejlede"
        assert r["panel_request"]["panel"] == panel


def test_open_ui_panel_all_valid_scopes() -> None:
    for scope in sorted(VALID_SCOPES):
        r = _exec_open_ui_panel({"panel": "file_tree", "detail": "x", "scope": scope})
        assert r["status"] == "ok", f"scope={scope} fejlede"
        assert r["panel_request"]["scope"] == scope


def test_invalid_action_returns_error_for_open_ui() -> None:
    r = _exec_open_ui_panel({"action": "fly", "panel": "file_tree"})
    assert r["status"] == "error"


def test_tool_definition_shape() -> None:
    d = APP_CONTROL_TOOL_DEFINITIONS[0]
    assert d["function"]["name"] == "request_app_action"
    assert set(d["function"]["parameters"]["properties"]) == {"action", "reason"}
    assert d["function"]["parameters"]["properties"]["action"]["enum"] == list(VALID_APP_ACTIONS)


def test_open_ui_tool_definition_shape() -> None:
    d = APP_CONTROL_TOOL_DEFINITIONS[1]
    assert d["function"]["name"] == "open_ui_panel"
    props = d["function"]["parameters"]["properties"]
    assert "panel" in props
    assert "detail" in props
    assert "scope" in props
    assert props["scope"]["enum"] == list(VALID_SCOPES)


def test_open_ui_tool_default_scope_in_enum() -> None:
    """repo er med i enum."""
    d = APP_CONTROL_TOOL_DEFINITIONS[1]
    assert "repo" in d["function"]["parameters"]["properties"]["scope"]["enum"]


def test_tool_registered_in_simple_tools() -> None:
    from core.tools.simple_tools import _TOOL_HANDLERS, TOOL_DEFINITIONS

    assert "request_app_action" in _TOOL_HANDLERS
    assert "open_ui_panel" in _TOOL_HANDLERS
    assert any(d.get("function", {}).get("name") == "request_app_action" for d in TOOL_DEFINITIONS)
    assert any(d.get("function", {}).get("name") == "open_ui_panel" for d in TOOL_DEFINITIONS)
