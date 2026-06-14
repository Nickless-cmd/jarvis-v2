from __future__ import annotations


def test_definitions_expose_open_ui_panel() -> None:
    from core.tools.ui_panel_tools import UI_PANEL_TOOL_DEFINITIONS, UI_PANEL_TOOL_HANDLERS

    names = {d["function"]["name"] for d in UI_PANEL_TOOL_DEFINITIONS}
    assert "open_ui_panel" in names
    assert "open_ui_panel" in UI_PANEL_TOOL_HANDLERS


def test_handler_records_pending(isolated_runtime) -> None:
    from core.tools.ui_panel_tools import _exec_open_ui_panel
    from core.services.ui_panel_store import list_pending

    res = _exec_open_ui_panel({"panel": "right", "detail": "vis dette"})
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
