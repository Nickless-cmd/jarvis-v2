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


# ---------------------------------------------------------------------------
# Registreringen (7/9-2026)
#
# `open_ui_panel` svarede `status: ok` og gjorde INGENTING. To moduler
# registrerede navnet; app_control-udgaven blev spredt sidst i simple_tools og
# vandt derfor dict'et — men den returnerer kun en `panel_request`-markør som
# intet modul læser. Desk-appen pollede en tom kø.
#
# 6/9 blev dubletten "løst" i definitions-arrayet ved at fjerne den ANDEN
# definition. Det fjernede symptomet (modellen så to signaturer) og lod
# årsagen stå: den overlevende handler var den inerte.
# ---------------------------------------------------------------------------

def test_open_ui_panel_peger_paa_handleren_der_faktisk_skriver():
    import core.tools.app_control_tool as A
    import core.tools.ui_panel_tools as U
    from core.tools.simple_tools import _TOOL_HANDLERS

    h = _TOOL_HANDLERS["open_ui_panel"]
    assert h is U._exec_open_ui_panel, "den inerte udgave har vundet igen"
    assert h is not A._exec_open_ui_panel


def test_kun_EEN_definition_og_den_kender_scope():
    """Definitionen skal blive ved at være supersættet (den med `scope`)."""
    from core.tools.simple_tools import TOOL_DEFINITIONS

    d = [x for x in TOOL_DEFINITIONS
         if (x.get("function") or {}).get("name") == "open_ui_panel"]
    assert len(d) == 1
    assert "scope" in (d[0]["function"]["parameters"]["properties"])


def test_scope_naar_faktisk_frem_til_store(monkeypatch):
    """Handleren ignorerede `scope` — så 'workstation' blev stille til 'repo'."""
    import core.tools.ui_panel_tools as U

    set_ = {}

    def falsk_request_panel(panel, *, detail="", scope="repo", session_id=""):
        set_.update(panel=panel, detail=detail, scope=scope)
        return {"id": "panel-prøve"}

    monkeypatch.setattr(U, "request_panel", falsk_request_panel)
    monkeypatch.setattr(U, "get_request_status", lambda rid: "opened")

    U._exec_open_ui_panel({"panel": "file_tree", "detail": "a/b.py",
                           "scope": "workstation"})
    assert set_["scope"] == "workstation"


def test_ukendt_scope_afvises():
    import core.tools.ui_panel_tools as U

    r = U._exec_open_ui_panel({"panel": "preview", "scope": "månen"})
    assert r["status"] == "error" and "scope" in r["error"]
