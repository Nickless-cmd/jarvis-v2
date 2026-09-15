"""En invokering uden run-id kan ikke skelnes fra en test.

## Målt 15/9-2026

Spørgsmålet «bliver skills faktisk brugt» kunne ikke besvares. Der stod tre
`cognitive_state.skill_invoked` i basen — men lasten var kun:

    {"name": "git-advanced"}

Ingen run-id, ingen session. Så en ægte invokering kunne ikke skelnes fra en
test der skriver i den levende DB. Codex' analyse konkluderede «ingen rigtig
skill_invoke siden 4. september»; jeg kunne hverken bekræfte eller afkræfte det.

## Mekanismen fandtes allerede

`aktivt_run_id()` blev bygget 12/9 efter to hændelser (8839 og 6798) der begge
stod med tomt run_id og derfor ikke kunne efterforskes. Kommentaren dér siger
det selv: «Feltet fandtes i record_central_incident; kalderen sendte det bare
ikke.» Samme mønster her.

## Kæden i ét event

`surfaced` siger om runtimen havde foreslået skillet, eller han fandt det selv.
Uden det kan matched → surfaced → invoked ikke lægges sammen bagefter.
"""
from __future__ import annotations

import pytest

from core.tools import skill_engine_tools as st
from core.services import skill_relevance_surface as srs


@pytest.fixture
def udgivne(monkeypatch):
    ude: list[tuple[str, dict]] = []
    from core.eventbus import bus
    monkeypatch.setattr(bus.event_bus, "publish",
                        lambda kind, payload=None, **k: ude.append((kind, dict(payload or {}))))
    monkeypatch.setattr(st.skill_engine, "get_skill_instructions",
                        lambda navn: {"status": "ok", "instructions": "x", "name": navn})
    monkeypatch.setattr(st.skill_engine, "record_skill_usage", lambda *a, **k: None)
    return ude


def _invokering(ude):
    return next(p for k, p in ude if k == "cognitive_state.skill_invoked")


def test_invokeringen_baerer_run_id(udgivne, monkeypatch):
    from core.services import session_context_resolve as scr
    monkeypatch.setattr(scr, "aktivt_run_id", lambda standard="": "visible-abc123")
    monkeypatch.setattr(scr, "aktiv_session_id", lambda standard="": "chat-xyz")
    st._exec_skill_invoke({"name": "pdf"})
    p = _invokering(udgivne)
    assert p["run_id"] == "visible-abc123"
    assert p["session_id"] == "chat-xyz"


def test_uden_et_run_staar_feltet_TOMT_ikke_forkert(udgivne, monkeypatch):
    """Et gæt ville være værre end ingenting — så ville sporet lyve."""
    from core.services import session_context_resolve as scr
    monkeypatch.setattr(scr, "aktivt_run_id", lambda standard="": "")
    monkeypatch.setattr(scr, "aktiv_session_id", lambda standard="": "")
    st._exec_skill_invoke({"name": "pdf"})
    assert _invokering(udgivne)["run_id"] == ""


def test_navnet_er_der_stadig(udgivne):
    """Dead-skill-detektionen læser `name`. En ny nøgle må ikke fortrænge den."""
    st._exec_skill_invoke({"name": "pdf"})
    assert _invokering(udgivne)["name"] == "pdf"


def test_sporet_siger_om_runtimen_FORESLOG_det(udgivne, monkeypatch):
    monkeypatch.setattr(srs, "_SIDSTE", ("noget", ["pdf", "excel-automation"]))
    st._exec_skill_invoke({"name": "pdf"})
    assert _invokering(udgivne)["surfaced"] is True


def test_sporet_siger_ogsaa_naar_han_fandt_det_SELV(udgivne, monkeypatch):
    """Det er hele pointen med feltet: at kunne skelne de to."""
    monkeypatch.setattr(srs, "_SIDSTE", ("noget", ["excel-automation"]))
    st._exec_skill_invoke({"name": "pdf"})
    assert _invokering(udgivne)["surfaced"] is False


def test_en_fejl_i_sporet_vaelter_ikke_invokeringen(udgivne, monkeypatch):
    """Telemetri må aldrig kunne ødelægge det den observerer."""
    from core.services import session_context_resolve as scr
    monkeypatch.setattr(scr, "aktivt_run_id",
                        lambda standard="": (_ for _ in ()).throw(RuntimeError("i stykker")))
    ud = st._exec_skill_invoke({"name": "pdf"})
    assert ud.get("status") != "error", ud
    assert _invokering(udgivne)["name"] == "pdf"
