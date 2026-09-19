"""Visnings-forespørgsler: spørg, svar, vent (Claude Desktops view-request)."""
from __future__ import annotations

import threading
import time

import pytest

import core.runtime.db_view_requests as vr


@pytest.fixture
def kv(monkeypatch):
    lager: dict[str, str] = {}
    monkeypatch.setattr(vr, "get_runtime_state_value", lambda k: lager.get(k))
    monkeypatch.setattr(vr, "set_runtime_state_value", lambda k, v: lager.__setitem__(k, v))
    return lager


def test_spoerg_og_svar(kv):
    r = vr.opret("show_pane", {"pane": "diff"}, session_id="s1")
    assert [x["id"] for x in vr.ventende()] == [r["id"]]
    assert vr.svar(r["id"], {"open_panes": ["diff"]}) is True
    assert vr.ventende() == []
    assert vr.vent_paa_svar(r["id"], frist_s=0.1) == {"open_panes": ["diff"]}


def test_kun_foerste_svar_taeller(kv):
    r = vr.opret("get_layout", {}, session_id="s1")
    assert vr.svar(r["id"], {"views": [{"placement": "primary"}]})
    assert vr.svar(r["id"], {"views": []}) is False
    assert vr.vent_paa_svar(r["id"], frist_s=0.1)["views"] == [{"placement": "primary"}]


def test_uden_svar_giver_vent_none(kv):
    r = vr.opret("get_layout", {}, session_id="s1")
    assert vr.vent_paa_svar(r["id"], frist_s=0.3, interval_s=0.05) is None


def test_foraeldede_forespoergsler_udfoeres_ikke(kv, monkeypatch):
    r = vr.opret("show_pane", {"pane": "diff"}, session_id="s1")
    nu = time.time()
    monkeypatch.setattr(vr.time, "time", lambda: nu + vr.FORAELDET_S + 1)
    assert vr.ventende() == []
    assert r["id"]


def test_ukendt_operation(kv):
    with pytest.raises(ValueError):
        vr.opret("delete_everything", {}, session_id="s1")


def test_svar_fra_en_anden_traad_naar_frem(kv):
    """Værktøjet i runtime venter; desk svarer via api — her en tråd."""
    r = vr.opret("get_layout", {}, session_id="s1")
    threading.Timer(0.15, lambda: vr.svar(r["id"], {"views": []})).start()
    assert vr.vent_paa_svar(r["id"], frist_s=2, interval_s=0.05) == {"views": []}
