from __future__ import annotations


def _req(rid="p1", panel="preview"):
    from core.services.ui_panel_store import request_panel
    return request_panel(request_id=rid, panel=panel, session_id="s1",
                         detail="vis fil", created_at="2026-06-14T12:00:00Z")


def test_request_and_list(isolated_runtime) -> None:
    from core.services.ui_panel_store import list_pending

    _req("p1", "preview")
    _req("p2", "right")
    pend = list_pending()
    assert {p["id"] for p in pend} == {"p1", "p2"}
    assert {p["panel"] for p in pend} == {"preview", "right"}


def test_unknown_panel_clamps_to_preview(isolated_runtime) -> None:
    from core.services.ui_panel_store import list_pending

    _req("p1", "evil-panel")
    assert list_pending()[0]["panel"] == "preview"


def test_ack_removes_from_pending(isolated_runtime) -> None:
    from core.services.ui_panel_store import ack, list_pending

    _req("p1")
    assert ack("p1") is True
    assert list_pending() == []


def test_ack_unknown_false(isolated_runtime) -> None:
    from core.services.ui_panel_store import ack

    assert ack("nope") is False


def test_tool_registered_and_callable(isolated_runtime) -> None:
    # open_ui_panel skal være i tool-registry + handleren virke.
    from core.services.tool_catalog import get_tool_definitions
    names = {d["function"]["name"] for d in get_tool_definitions() if "function" in d}
    assert "open_ui_panel" in names

    from core.tools.ui_panel_tools import _exec_open_ui_panel
    res = _exec_open_ui_panel({"panel": "preview", "detail": "x"})
    assert res["status"] == "ok" and res["panel"] == "preview"


def test_request_panel_carries_action_close(isolated_runtime) -> None:
    from core.services.ui_panel_store import request_panel, list_pending
    rec = request_panel(request_id="p-close-1", panel="preview", session_id="s",
                        detail="", created_at="t", action="close")
    assert rec["action"] == "close"
    assert any(r["id"] == "p-close-1" and r.get("action") == "close" for r in list_pending())


def test_request_panel_defaults_action_open(isolated_runtime) -> None:
    from core.services.ui_panel_store import request_panel
    rec = request_panel(request_id="p-open-1", panel="preview", session_id="s",
                        detail="", created_at="t")
    assert rec["action"] == "open"
