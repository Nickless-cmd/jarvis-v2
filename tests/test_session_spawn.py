"""Tests for session_spawn — start_session.

Dækker de tre session-veje, rate-guarden, og de to validerings-edge-cases
(tom prompt, prompt over loftet). ``start_autonomous_run`` monkeypatches, så
ingen tråd startes: testen måler BESLUTNINGEN, ikke runnet.
"""
from __future__ import annotations

import pytest

import core.services.session_spawn as sp


@pytest.fixture(autouse=True)
def _ren_guard(monkeypatch):
    """Hver test starter med et tomt rate-vindue."""
    monkeypatch.setattr(sp, "_SPAWN_TIMES", [])


def _fang_run(monkeypatch):
    """Erstat start_autonomous_run; returnér listen af kald."""
    kald: list[dict] = []

    def _falsk(message, session_id=None, follow=False, origin=None):
        kald.append(
            {"message": message, "session_id": session_id, "origin": origin}
        )

    import core.services.visible_runs as vr

    monkeypatch.setattr(vr, "start_autonomous_run", _falsk)
    return kald


# ── de tre session-veje ───────────────────────────────────────────────


def test_uden_session_og_titel_lader_rotatoren_vaelge(monkeypatch):
    kald = _fang_run(monkeypatch)
    r = sp.start_session("undersøg X")
    assert r["status"] == "ok"
    assert r["session_id"] is None  # None → rotatoren i start_autonomous_run
    assert r["oprettet"] is False
    assert kald[0]["session_id"] is None
    assert kald[0]["message"] == "undersøg X"


def test_eksplicit_session_id_vinder(monkeypatch):
    kald = _fang_run(monkeypatch)
    r = sp.start_session("arbejd videre", session_id="chat-abc123")
    assert r["status"] == "ok"
    assert r["session_id"] == "chat-abc123"
    assert r["oprettet"] is False
    assert kald[0]["session_id"] == "chat-abc123"


def test_titel_opretter_ny_session(monkeypatch):
    kald = _fang_run(monkeypatch)
    oprettede: list[str] = []

    import core.services.chat_sessions as cs

    def _falsk_opret(*, title="New chat", **_):
        oprettede.append(title)
        return {"id": "chat-ny123"}

    monkeypatch.setattr(cs, "create_chat_session", _falsk_opret)

    r = sp.start_session("skriv rapporten", title="Rapport-gennemgang")
    assert r["status"] == "ok"
    assert r["session_id"] == "chat-ny123"
    assert r["oprettet"] is True
    assert oprettede == ["Rapport-gennemgang"]
    assert kald[0]["session_id"] == "chat-ny123"


def test_titel_trunkerer_ved_120_tegn(monkeypatch):
    _fang_run(monkeypatch)
    oprettede: list[str] = []

    import core.services.chat_sessions as cs

    def _opret(*, title="", **_):
        oprettede.append(title)
        return {"id": "chat-x"}

    monkeypatch.setattr(cs, "create_chat_session", _opret)
    sp.start_session("noget", title="T" * 400)
    assert len(oprettede[0]) == 120


# ── edge cases ────────────────────────────────────────────────────────


def test_tom_prompt_afvises_og_starter_intet(monkeypatch):
    kald = _fang_run(monkeypatch)
    r = sp.start_session("   ")
    assert r["status"] == "error"
    assert "tom prompt" in r["error"]
    assert kald == []  # intet run startet


def test_prompt_over_loftet_afvises(monkeypatch):
    kald = _fang_run(monkeypatch)
    r = sp.start_session("x" * (sp._MAX_PROMPT_CHARS + 1))
    assert r["status"] == "error"
    assert "tegn" in r["error"]
    assert kald == []


def test_netop_paa_loftet_slipper_igennem(monkeypatch):
    kald = _fang_run(monkeypatch)
    r = sp.start_session("x" * sp._MAX_PROMPT_CHARS)
    assert r["status"] == "ok"
    assert len(kald) == 1


def test_run_fejl_giver_error_og_taeller_ikke(monkeypatch):
    import core.services.visible_runs as vr

    def _boom(*a, **k):
        raise RuntimeError("tråd kunne ikke startes")

    monkeypatch.setattr(vr, "start_autonomous_run", _boom)
    r = sp.start_session("noget")
    assert r["status"] == "error"
    assert "tråd kunne ikke startes" in r["error"]
    # Et run der ikke kom op, må ikke æde af kvoten.
    assert sp.antal_sidste_time() == 0


def test_session_oprettelse_fejler_giver_error(monkeypatch):
    _fang_run(monkeypatch)
    import core.services.chat_sessions as cs

    def _boom(*, title="", **_):
        raise RuntimeError("db låst")

    monkeypatch.setattr(cs, "create_chat_session", _boom)
    r = sp.start_session("noget", title="T")
    assert r["status"] == "error"
    assert "db låst" in r["error"]


# ── rate-guard ────────────────────────────────────────────────────────


def test_rate_guard_lofter_ved_ti(monkeypatch):
    kald = _fang_run(monkeypatch)
    for i in range(sp._MAX_PER_HOUR):
        assert sp.start_session(f"opgave {i}")["status"] == "ok"
    r = sp.start_session("en for meget")
    assert r["status"] == "error"
    assert "rate-guard" in r["error"]
    assert len(kald) == sp._MAX_PER_HOUR  # det ellevte startede intet


def test_rate_guard_vinduet_ruller(monkeypatch):
    """Et tidsstempel ældre end en time skal falde ud af vinduet."""
    kald = _fang_run(monkeypatch)
    import time as _t

    nu = _t.time()
    monkeypatch.setattr(sp, "_SPAWN_TIMES", [nu - 3601.0] * sp._MAX_PER_HOUR)
    r = sp.start_session("efter vinduet")
    assert r["status"] == "ok"
    assert len(kald) == 1


def test_antal_sidste_time_rydder_gamle(monkeypatch):
    import time as _t

    nu = _t.time()
    monkeypatch.setattr(sp, "_SPAWN_TIMES", [nu - 7200.0, nu - 10.0])
    assert sp.antal_sidste_time() == 1


# ── skema + eksekutor ─────────────────────────────────────────────────


def test_skemaet_er_velformet():
    d = sp.SESSION_TOOL_DEFINITIONS
    assert len(d) == 1
    fn = d[0]["function"]
    assert fn["name"] == "start_session"
    assert fn["parameters"]["required"] == ["prompt"]
    assert set(fn["parameters"]["properties"]) == {
        "prompt", "session_id", "title", "origin",
    }


def test_eksekutor_videresender_og_stripper(monkeypatch):
    kald = _fang_run(monkeypatch)
    r = sp._exec_start_session(
        {"prompt": "  opgave  ", "session_id": "  chat-1  ", "origin": "  self  "}
    )
    assert r["status"] == "ok"
    assert kald[0]["message"] == "opgave"
    assert kald[0]["session_id"] == "chat-1"
    assert kald[0]["origin"] == "self"


def test_eksekutor_tom_session_id_bliver_none(monkeypatch):
    kald = _fang_run(monkeypatch)
    r = sp._exec_start_session({"prompt": "x", "session_id": "   "})
    assert r["status"] == "ok"
    assert kald[0]["session_id"] is None
