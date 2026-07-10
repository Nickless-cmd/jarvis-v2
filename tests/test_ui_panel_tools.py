from __future__ import annotations


def test_definitions_expose_open_ui_panel() -> None:
    from core.tools.ui_panel_tools import UI_PANEL_TOOL_DEFINITIONS, UI_PANEL_TOOL_HANDLERS

    names = {d["function"]["name"] for d in UI_PANEL_TOOL_DEFINITIONS}
    assert "open_ui_panel" in names
    assert "open_ui_panel" in UI_PANEL_TOOL_HANDLERS


def test_handler_records_pending(isolated_runtime, monkeypatch) -> None:
    from core.tools import ui_panel_tools as u
    from core.services.ui_panel_store import list_pending

    monkeypatch.setattr(u, "get_request_status", lambda rid: "opened")
    res = u._exec_open_ui_panel({"panel": "right", "detail": "vis dette"})
    assert res["status"] == "ok" and res["panel"] == "right"
    pend = list_pending()
    assert len(pend) == 1 and pend[0]["panel"] == "right"


def test_handler_rejects_unknown_panel(isolated_runtime) -> None:
    from core.tools.ui_panel_tools import _exec_open_ui_panel

    res = _exec_open_ui_panel({"panel": "rm-rf"})
    assert res["status"] == "error"


def test_registered_in_global_catalog(isolated_runtime) -> None:
    from core.services.tool_catalog import get_tool_definitions
    names = {d["function"]["name"] for d in get_tool_definitions() if "function" in d}
    assert "open_ui_panel" in names


def test_close_action_valid() -> None:
    from core.tools.ui_panel_tools import _exec_open_ui_panel
    r = _exec_open_ui_panel({"action": "close"})
    assert r["status"] == "ok"
    assert r["action"] == "close"


def test_open_is_default_action(isolated_runtime, monkeypatch) -> None:
    from core.tools import ui_panel_tools as u
    # Request→ACK-kontrakt: simulér at desk kvitterer (status 'opened').
    monkeypatch.setattr(u, "get_request_status", lambda rid: "opened")
    r = u._exec_open_ui_panel({"panel": "preview"})
    assert r["status"] == "ok"
    assert r.get("action", "open") == "open"


def test_file_tree_panel_with_highlight_path(isolated_runtime, monkeypatch) -> None:
    # Jarvis-styret highlight: panel="file_tree" + detail=sti registreres.
    from core.tools import ui_panel_tools as u
    from core.services.ui_panel_store import list_pending

    monkeypatch.setattr(u, "get_request_status", lambda rid: "opened")
    r = u._exec_open_ui_panel({"panel": "file_tree", "detail": "core/tools/ui_panel_tools.py"})
    assert r["status"] == "ok" and r["panel"] == "file_tree"
    pend = [p for p in list_pending() if p["panel"] == "file_tree"]
    assert pend and pend[-1]["detail"] == "core/tools/ui_panel_tools.py"
