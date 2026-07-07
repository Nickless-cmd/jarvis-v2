from __future__ import annotations

import pytest


def _req(panel="preview"):
    from core.services.ui_panel_store import request_panel
    return request_panel(panel=panel, session_id="s1", detail="vis fil")


def test_request_and_list(isolated_runtime) -> None:
    from core.services.ui_panel_store import list_pending

    r1 = _req("preview")
    r2 = _req("right")
    pend = list_pending()
    assert {p["id"] for p in pend} == {r1["id"], r2["id"]}
    assert {p["panel"] for p in pend} == {"preview", "right"}


def test_unknown_panel_raises(isolated_runtime) -> None:
    # Runtime now rejects unknown panels with ValueError instead of clamping
    # to preview (ui_panel_store.request_panel validates against VALID_PANELS).
    from core.services.ui_panel_store import request_panel, list_pending

    with pytest.raises(ValueError):
        request_panel(panel="evil-panel", session_id="s1")
    assert list_pending() == []


def test_ack_removes_from_pending(isolated_runtime) -> None:
    from core.services.ui_panel_store import ack_panel, list_pending

    rec = _req()
    assert ack_panel(rec["id"]) is True
    assert list_pending() == []


def test_ack_unknown_false(isolated_runtime) -> None:
    from core.services.ui_panel_store import ack_panel

    assert ack_panel("nope") is False


def test_tool_registered_and_callable(isolated_runtime) -> None:
    # open_ui_panel skal være i tool-registry + handleren virke.
    from core.services.tool_catalog import get_tool_definitions
    names = {d["function"]["name"] for d in get_tool_definitions() if "function" in d}
    assert "open_ui_panel" in names

    from core.tools.ui_panel_tools import _exec_open_ui_panel
    res = _exec_open_ui_panel({"panel": "preview", "detail": "x"})
    assert res["status"] == "ok" and res["panel"] == "preview"


def test_request_panel_records_scope(isolated_runtime) -> None:
    from core.services.ui_panel_store import request_panel, list_pending
    rec = request_panel(panel="preview", session_id="s", detail="", scope="workstation")
    assert rec["scope"] == "workstation"
    assert any(r["id"] == rec["id"] and r.get("scope") == "workstation"
               for r in list_pending())


def test_request_panel_defaults_scope_repo(isolated_runtime) -> None:
    from core.services.ui_panel_store import request_panel
    rec = request_panel(panel="preview", session_id="s", detail="")
    assert rec["scope"] == "repo"
