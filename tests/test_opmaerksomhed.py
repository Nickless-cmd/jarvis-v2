"""Tilstands-hjernen — core.runtime.opmaerksomhed."""
from __future__ import annotations

import time

import pytest

from core.runtime import opmaerksomhed as om


@pytest.fixture
def miljoe(monkeypatch):
    lager: dict = {}
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value", lambda k, d=None: lager.get(k, d))
    monkeypatch.setattr("core.runtime.db_core.set_runtime_state_value", lambda k, v: lager.__setitem__(k, v))
    ejere = {"s-a": "rum-a", "s-a2": "rum-a", "s-b": "rum-b"}
    monkeypatch.setattr(om, "rum_for_session", lambda sid: ejere.get(sid, "rum-a"))
    monkeypatch.setattr(om, "_titel", lambda sid: f"titel {sid}")
    monkeypatch.setattr(om, "_baggrund", lambda: 0)
    state = {"live": [], "koe": []}
    monkeypatch.setattr("core.services.run_event_log.live_run_ids", lambda: [r for r, _ in state["live"]])
    monkeypatch.setattr("core.services.run_event_log.session_for_run", lambda rid: dict(state["live"]).get(rid))
    monkeypatch.setattr("core.services.cowork_feed.build_queue", lambda **kw: list(state["koe"]))
    return lager, state


def test_intet_er_idle(miljoe):
    t = om.tilstand_for(rum="rum-a")
    assert t["tilstand"] == "idle" and t["fokus"] is None and t["etiket"] == "Intet kræver dig"


def test_codex_prioritet_venter_slaar_alt(miljoe):
    _, state = miljoe
    om._noter(session_id="s-a", run_id="r1", tilstand="failed", tekst="boom")
    om._noter(session_id="s-a2", run_id="r2", tilstand="review", tekst="svar")
    state["live"] = [("r3", "s-a")]
    # s-a kører igen → dens «fejlede» er ikke længere nyheden
    t = om.tilstand_for(rum="rum-a")
    assert t["tilstand"] == "review"
    assert t["antal"] == {"waiting": 0, "failed": 0, "review": 1, "running": 1}
    state["koe"] = [{"id": "ap-1", "title": "Må jeg køre rm?", "kind": "exec", "source": "capability"}]
    t = om.tilstand_for(rum="rum-a")
    assert t["tilstand"] == "waiting" and t["fokus"]["titel"] == "Må jeg køre rm?"


def test_fejlede_slaar_faerdig(miljoe):
    om._noter(session_id="s-a2", run_id="r2", tilstand="review", tekst="svar")
    om._noter(session_id="s-a", run_id="r1", tilstand="failed", tekst="boom")
    assert om.tilstand_for(rum="rum-a")["tilstand"] == "failed"


def test_arbejdsrum_er_adskilt(miljoe):
    _, state = miljoe
    om._noter(session_id="s-b", run_id="r1", tilstand="review", tekst="andens svar")
    state["live"] = [("r9", "s-b")]
    assert om.tilstand_for(rum="rum-a")["tilstand"] == "idle"
    assert om.tilstand_for(rum="rum-b")["tilstand"] == "running"


def test_set_og_ny_tur_fjerner_punktet(miljoe):
    om._noter(session_id="s-a", run_id="r1", tilstand="review", tekst="svar")
    assert om.set("s-a") is True
    assert om.tilstand_for(rum="rum-a")["tilstand"] == "idle"
    om._noter(session_id="s-a", run_id="r2", tilstand="failed", tekst="x")
    om.glem_session("s-a")
    assert om.tilstand_for(rum="rum-a")["tilstand"] == "idle"


def test_et_punkt_pr_samtale_og_levetid(miljoe, monkeypatch):
    om._noter(session_id="s-a", run_id="r1", tilstand="failed", tekst="x")
    om._noter(session_id="s-a", run_id="r2", tilstand="review", tekst="y")
    t = om.tilstand_for(rum="rum-a")
    assert t["tilstand"] == "review" and t["antal"]["failed"] == 0
    nu = time.time()
    monkeypatch.setattr(om.time, "time", lambda: nu + om._LEVETID_S + 1)
    assert om.tilstand_for(rum="rum-a")["tilstand"] == "idle"


@pytest.mark.parametrize("status,forventet", [
    ("completed", "review"), ("failed", "failed"), ("interrupted", "failed"),
    ("cancelled", "idle"), ("recovering", "idle"),
])
def test_udfald_afgoer_tilstanden(miljoe, monkeypatch, status, forventet):
    class _C:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a):
            class R:
                def fetchone(_): return (status, "")
            return R()
    monkeypatch.setattr("core.runtime.db.connect", lambda: _C())
    monkeypatch.setattr("core.services.run_event_log.was_consumed_or_active", lambda rid: False)
    monkeypatch.setattr("core.services.push_dispatcher._last_assistant_preview", lambda sid: "svaret")
    om._vurder_afsluttet("log-1", "visible-1", "s-a")
    assert om.tilstand_for(rum="rum-a")["tilstand"] == forventet


def test_set_live_giver_intet_at_gennemgaa(miljoe, monkeypatch):
    monkeypatch.setattr("core.services.run_event_log.was_consumed_or_active", lambda rid: True)
    om._vurder_afsluttet("log-1", "visible-1", "s-a")
    assert om.tilstand_for(rum="rum-a")["tilstand"] == "idle"


def test_detached_run_kalder_hjernen():
    """AST-vagt: begge kroge sidder i detached_run (ellers bygget men ikke forbundet)."""
    import ast
    import inspect
    from core.services.visible_runs_sections import detached_run
    navne = {n.name for n in ast.walk(ast.parse(inspect.getsource(detached_run)))
             if isinstance(n, ast.alias)}
    assert {"noter_afsluttet", "glem_session"} <= navne


def test_forslag_er_indbakke_ikke_venter(miljoe):
    """Maalt 19/9: 20 forslag + 4 initiativer, 0 blokerende. De maa ikke holde
    tilstanden paa «Venter paa dig» — saa betyder den intet."""
    _, state = miljoe
    state["koe"] = ([{"id": f"p{i}", "title": "Forslag", "source": "proposal"} for i in range(20)]
                    + [{"id": f"i{i}", "title": "Initiativ", "source": "initiative"} for i in range(4)])
    t = om.tilstand_for(rum="rum-a")
    assert t["tilstand"] == "idle" and t["indbakke"] == 24 and t["antal"]["waiting"] == 0


def _f(d: dict) -> str:
    import json
    return f"event: {d['type']}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n"


def test_aktivitet_viser_jarvis_egen_beskrivelse_af_vaerktoejet():
    frames = [
        _f({"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": ""}}),
        _f({"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "t", "name": "operator_bash", "input": {}}}),
        _f({"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta",
            "partial_json": '{"command": "git status", "description": "Tjekker om træet er rent"}'}}),
        _f({"type": "content_block_stop", "index": 1}),
    ]
    assert om.aktivitet(frames) == "Tjekker om træet er rent"


def test_aktivitet_uden_beskrivelse_falder_tilbage_til_kommandoen():
    frames = [
        _f({"type": "content_block_start", "index": 3, "content_block": {"type": "tool_use", "id": "t", "name": "operator_bash", "input": {}}}),
        _f({"type": "content_block_delta", "index": 3, "delta": {"type": "input_json_delta", "partial_json": '{"command": "ls -la"}'}}),
    ]
    assert om.aktivitet(frames) == "Bash: ls -la"


def test_aktivitet_taenker_og_skriver():
    t = _f({"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": ""}})
    x = _f({"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}})
    assert om.aktivitet([t]) == "Tænker…"
    assert om.aktivitet([t, x]) == "Skriver svaret…"
    assert om.aktivitet([]) == ""
