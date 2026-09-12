"""Router-projektionen — fase 11, punkt 4, første af de tre der manglede.

Kriteriet er det samme som for `chat_messages`: kan rækkerne IKKE genskabes
fra en tom projektion, er hovedbogen ikke sandheden, og så skal ingen session
flyttes.

To ting er nye her og har derfor hver sin prøve:

* Tabellen har ingen naturlig nøgle, kun `id INTEGER PRIMARY KEY`. Uden et
  udledt `decision_id` ville en genfoldning lægge rækkerne ved siden af de
  gamle i stedet for at opdatere dem.
* Det gamle skrivested brugte `datetime('now')` — naiv tid med mellemrum.
  Projektionen skriver ISO. Samme øjeblik i to formater må ikke tælle som
  uenighed, men et ÆGTE tidsspring skal.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import projection_drift as D
from core.services import projection_runtime as P
from core.services import projection_tool_router as T


@pytest.fixture(autouse=True)
def _rent_register():
    P._unregister_all_for_tests()
    T.register()
    yield
    P._unregister_all_for_tests()


@pytest.fixture
def sid(isolated_runtime):
    s = "tr-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, "2026-09-09T09:00:00+00:00",
                                            "2026-09-09T09:00:00+00:00"))
    return s


def _beslutning(eid: str, lane: str = "primary", **ekstra):
    p = {
        "lane": lane,
        "selected_names": ["read_file", "grep"],
        "always_core": ["bash"],
        "confidence": 0.82,
        "threshold": 0.55,
        "created_at": "2026-09-09T10:00:00+00:00",
    }
    p.update(ekstra)
    return {"event_id": eid, "kind": T.KIND, "payload": p}


def _skriv(sid: str, *events):
    t = L.acquire_write_lease(sid, owner="test")
    L.append_session_events(sid, owner="test", token=t, events=list(events))
    L.release_write_lease(sid, owner="test", token=t)


def _raekker(sid: str):
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT decision_id, lane, selected_names_json, always_core_names_json, "
            "confidence, threshold, fallback_used, created_at "
            "FROM tool_router_decisions WHERE session_id = ? ORDER BY id", (sid,))]


# ── genskabelse ──────────────────────────────────────────────────────────

def test_raekkerne_genskabes_fra_en_TOM_projektion(sid):
    _skriv(sid, _beslutning("e1"), _beslutning("e2", lane="cheap"))
    r = T.rebuild(sid)
    assert r["state"]["skrevet"] == 2
    assert [x["lane"] for x in _raekker(sid)] == ["primary", "cheap"]


def test_alle_felter_overlever_turen(sid):
    _skriv(sid, _beslutning("e1", fallback_used=True, fallback_reason="tom pulje",
                            elapsed_ms=42, tokens_saved_estimate=1234))
    T.rebuild(sid)
    r = _raekker(sid)[0]
    assert r["lane"] == "primary"
    assert "read_file" in r["selected_names_json"]
    assert "bash" in r["always_core_names_json"]
    assert r["confidence"] == pytest.approx(0.82)
    assert r["fallback_used"] == 1
    assert r["created_at"] == "2026-09-09T10:00:00+00:00"


def test_en_genfoldning_opdaterer_i_stedet_for_at_dublere(sid):
    """Uden det udledte `decision_id` ville tabellen have to svar paa hvad
    routeren besluttede — tabellen har ingen naturlig noegle."""
    _skriv(sid, _beslutning("e1"), _beslutning("e2"))
    T.rebuild(sid)
    foerste = _raekker(sid)
    T.rebuild(sid)
    assert len(_raekker(sid)) == len(foerste) == 2
    assert [x["decision_id"] for x in _raekker(sid)] == [x["decision_id"] for x in foerste]


def test_tiden_kommer_fra_HAENDELSEN_ikke_fra_now(sid):
    _skriv(sid, _beslutning("e1"))
    T.rebuild(sid)
    foer = _raekker(sid)[0]["created_at"]
    T.rebuild(sid)
    assert _raekker(sid)[0]["created_at"] == foer == "2026-09-09T10:00:00+00:00"


# ── validering ───────────────────────────────────────────────────────────

def test_en_beslutning_uden_lane_afvises_men_spaerrer_ikke_resten(sid):
    daarlig = _beslutning("e1")
    daarlig["payload"]["lane"] = ""
    _skriv(sid, daarlig, _beslutning("e2", lane="cheap"))
    r = T.rebuild(sid)
    assert r["state"]["skrevet"] == 1
    assert len(r["state"]["afviste"]) == 1
    assert [x["lane"] for x in _raekker(sid)] == ["cheap"]


def test_en_tom_vaerktoejsliste_er_ingen_beslutning(sid):
    tom = _beslutning("e1")
    tom["payload"]["selected_names"] = []
    _skriv(sid, tom)
    assert T.rebuild(sid)["state"]["skrevet"] == 0


# ── drift, generaliseret ─────────────────────────────────────────────────

def test_drift_sammenligner_router_tabellen_ikke_chat_messages(sid):
    _skriv(sid, _beslutning("e1"))
    T.rebuild(sid)
    r = D.compare(sid, "tool_router_decisions")
    assert r["projektion"] == "tool_router_decisions"
    assert r["bevis"] == "verificeret" and r["enige"] is True


def test_samme_oejeblik_i_to_formater_er_IKKE_uenighed():
    """`datetime('now')` gav `2026-09-11 19:38:09` — uden zone, med mellemrum.
    Uden denne normalisering ville HVER raekke se ud som en afvigelse."""
    assert D._samme_tid("2026-09-11 19:38:09", "2026-09-11T19:38:09+00:00") is True


def test_men_et_AEGTE_tidsspring_er_stadig_uenighed():
    """Normaliseringen maa ikke sloere en forskel, kun en formforskel."""
    assert D._samme_tid("2026-09-11 19:38:09", "2026-09-11T21:38:09+00:00") is False


def test_en_ukendt_projektion_er_en_fejl_ikke_et_tomt_svar(sid):
    """Et tomt svar ville melde «enige» om noget der ikke findes."""
    with pytest.raises(ValueError):
        D.compare(sid, "findes-ikke")


# ── vagten paa det direkte skrivested ────────────────────────────────────
#
# En udskiftning bestaar af TO dele. Projektionen ovenfor folder; vagten her
# naegter det direkte skrivested naar sessionen er skiftet. Uden den anden
# halvdel ville et skifte fordoble sandheden i stedet for at flytte den.

def _beslut(sid: str):
    """Koer routerens egen persist-vej — ikke en efterligning af den."""
    from core.services.tool_router import ToolSelection, _persist
    sel = ToolSelection(
        selected_names=["read_file"], always_core=["bash"], embedding_picks=[],
        confidence=0.9, threshold=0.5, fallback_used=False, fallback_reason="",
        elapsed_ms=3,
    )
    _persist(sel, "hej", sid, "primary", "run-1")


def _antal(sid: str) -> int:
    with connect() as c:
        return c.execute(
            "SELECT COUNT(*) FROM tool_router_decisions WHERE session_id = ?",
            (sid,)).fetchone()[0]


def test_legacy_session_skriver_direkte_som_foer(sid):
    """Kontrolarm. Uden den beviser proeven nedenfor ingenting."""
    _beslut(sid)
    assert _antal(sid) == 1


def test_ledger_session_faar_INGEN_direkte_raekke(sid):
    """Ellers ville tabellen have to raekker pr. beslutning: projektionens
    med udledt `decision_id` og skrivestedets med NULL, som det fulde unikke
    indeks netop tillader."""
    L.advance_storage_mode(sid, to="shadow")
    L.advance_storage_mode(sid, to="ledger")
    _beslut(sid)
    assert _antal(sid) == 0


def test_shadow_session_skriver_stadig_direkte(sid):
    """I skygge skrives der BEGGE steder — det er hele pointen med skyggen.
    En vagt der ogsaa spaerrede her ville goere sammenligningen umulig."""
    L.advance_storage_mode(sid, to="shadow")
    _beslut(sid)
    assert _antal(sid) == 1


def test_vagten_afviser_hoejlydt_ikke_tavst(sid):
    """Beskeden skal sige hvad man skal goere i stedet."""
    from core.services.projection_tool_router import (
        DirekteSkrivningAfvist, guard_direct_write)
    L.advance_storage_mode(sid, to="shadow")
    L.advance_storage_mode(sid, to="ledger")
    with connect() as c:
        with pytest.raises(DirekteSkrivningAfvist) as ei:
            guard_direct_write(sid, conn=c)
    assert "tool_router_decisions" in str(ei.value)
    assert "hovedbogen" in str(ei.value)
