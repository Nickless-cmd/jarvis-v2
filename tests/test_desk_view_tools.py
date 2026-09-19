"""Jarvis' tre desk-værktøjer — Claude Desktops ccd_view (19/9-2026)."""
from __future__ import annotations

import threading

import pytest

import core.runtime.db_view_requests as vr
import core.tools.desk_view_tools as dv


@pytest.fixture
def kv(monkeypatch):
    lager: dict[str, str] = {}
    monkeypatch.setattr(vr, "get_runtime_state_value", lambda k: lager.get(k))
    monkeypatch.setattr(vr, "set_runtime_state_value", lambda k, v: lager.__setitem__(k, v))
    monkeypatch.setattr(dv, "FRIST_S", 1.5)
    return lager


def _desk_svarer(resultat):
    """En «desk» der svarer på den første forespørgsel den ser."""
    def løb():
        import time
        for _ in range(40):
            v = vr.ventende()
            if v:
                vr.svar(v[0]["id"], resultat(v[0]))
                return
            time.sleep(0.02)
    t = threading.Thread(target=løb, daemon=True)
    t.start()
    return t


def test_show_pane_diff_naar_desk_og_giver_svaret_tilbage(kv):
    set_: list = []
    _desk_svarer(lambda r: set_.append(r) or {"open_panes": ["diff"]})
    ud = dv._exec_show_pane({"pane": "diff", "path": "core/login.py", "_runtime_session_id": "s1"})
    assert ud == {"status": "ok", "open_panes": ["diff"]}
    assert set_[0]["op"] == "show_pane" and set_[0]["session_id"] == "s1"
    assert set_[0]["args"] == {"pane": "diff", "path": "core/login.py"}


def test_desks_fejltekst_videregives(kv):
    _desk_svarer(lambda r: {"error": "Terminalen findes kun i kode-tilstand."})
    ud = dv._exec_show_pane({"pane": "terminal", "_runtime_session_id": "s1"})
    assert ud == {"status": "error", "error": "Terminalen findes kun i kode-tilstand."}


def test_get_layout_baerer_samtalens_id(kv):
    """Fanget af testen nedenfor: get_layout sendte `{}` og tabte samtalens id."""
    set_: list = []
    _desk_svarer(lambda r: set_.append(r) or {"views": [{"placement": "primary"}], "open_panes": []})
    assert dv._exec_get_layout({"_runtime_session_id": "s9"})["views"] == [{"placement": "primary"}]
    assert set_[0]["session_id"] == "s9"


def test_uden_desk_er_svaret_aerligt(kv, monkeypatch):
    monkeypatch.setattr(dv, "FRIST_S", 0.3)
    ud = dv._exec_get_layout({"_runtime_session_id": "s1"})
    assert ud["status"] == "unconfirmed" and "ikke åben" in ud["note"]


def test_file_kraever_path_som_hos_cc(kv):
    ud = dv._exec_show_pane({"pane": "file", "_runtime_session_id": "s1"})
    assert ud["status"] == "error" and "`path`" in ud["error"]
    assert vr.ventende() == []


def test_ukendt_panel_og_ingen_samtale(kv, monkeypatch):
    assert dv._exec_close_pane({"pane": "vinduet", "_runtime_session_id": "s1"})["status"] == "error"
    monkeypatch.setattr(dv, "_session", lambda: "")
    assert "Ingen samtale" in dv._exec_get_layout({})["error"]


def test_vaerktoejerne_er_registreret_og_i_chat_scopet():
    from core.tools import simple_tools as st
    from core.tools.tool_scoping import CHAT_MODE_TOOLS_BASE, CODE_MODE_TOOLS_BASE
    for n in ("desk_get_layout", "desk_show_pane", "desk_close_pane"):
        assert n in st._TOOL_HANDLERS
        # Begge scopes: kode-tilstand har sin EGEN smalle liste.
        assert n in CHAT_MODE_TOOLS_BASE and n in CODE_MODE_TOOLS_BASE
