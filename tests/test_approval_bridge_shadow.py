"""Skyggen for godkendelses-broen — ville den sige det samme?

Det her er den vej hvert eneste godkendte værktøjskald går igennem. En fejl
betyder enten at en godkendt handling ikke sker, eller — værre — at en handling
sker som ingen godkendte. Derfor kører broen ved siden af og afgør ingenting.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest

from core.runtime import db_approval_bridge as B
from core.services import approval_bridge_shadow as S


@pytest.fixture(autouse=True)
def _rene(isolated_runtime):
    S._nulstil_for_tests()
    yield
    S._nulstil_for_tests()


@pytest.fixture
def taendt(monkeypatch):
    monkeypatch.setattr(S, "live", lambda: True)


@pytest.fixture
def aid():
    return "appr-" + datetime.now(UTC).strftime("%H%M%S%f")


ARGS = {"command": "rm -rf /tmp/x"}


# ── afbryderen ───────────────────────────────────────────────────────────

def test_slukket_som_standard():
    assert S.live() is False


def test_slukket_roerer_ingenting(aid):
    S.note_requested(aid, tool_name="bash", arguments=ARGS)
    assert B.state(aid) is None
    assert S.taellere()["sprunget_over"] == 1


@pytest.mark.parametrize("v", [None, {}, {"enabled": False}, "sludder"])
def test_kun_et_eksplicit_true_taender(monkeypatch, v):
    import core.services.central_switches as CS
    monkeypatch.setattr(CS.shared_cache, "get", lambda *a, **k: v)
    assert S.live() is False


# ── den fulde vej ────────────────────────────────────────────────────────

def test_hele_forloebet_registreres(taendt, aid):
    S.note_requested(aid, tool_name="bash", arguments=ARGS, run_id="r1")
    assert B.state(aid)["state"] == B.PENDING
    S.note_decided(aid, approved=True)
    assert B.state(aid)["state"] == B.APPROVED
    S.note_claim(aid, tool_name="bash", arguments=ARGS, legacy_allowed=True)
    assert B.state(aid)["state"] == B.DISPATCHING
    assert S.taellere()["enige"] == 1


def test_et_NEJ_foelges_ogsaa(taendt, aid):
    S.note_requested(aid, tool_name="bash", arguments=ARGS)
    S.note_decided(aid, approved=False)
    assert B.state(aid)["state"] == B.DENIED


# ── uenighed ─────────────────────────────────────────────────────────────

def test_uenighed_naar_argumenterne_er_ANDRE(taendt, aid, caplog):
    """Den fejl broen findes for: man sagde ja til ét kald og der køres et andet.
    Den kørende kode tillader det; broen ville ikke."""
    S.note_requested(aid, tool_name="bash", arguments={"command": "rm -rf /tmp/x"})
    S.note_decided(aid, approved=True)
    with caplog.at_level(logging.WARNING):
        S.note_claim(aid, tool_name="bash", arguments={"command": "rm -rf /"},
                     legacy_allowed=True)
    assert S.taellere()["uenige"] == 1
    assert "UENIGE" in caplog.text and "ANDET kald" in caplog.text


def test_loggen_baerer_begge_sider(taendt, aid, caplog):
    S.note_requested(aid, tool_name="bash", arguments={"command": "a"})
    S.note_decided(aid, approved=True)
    with caplog.at_level(logging.WARNING):
        S.note_claim(aid, tool_name="bash", arguments={"command": "b"},
                     legacy_allowed=True)
    t = caplog.text
    assert "gammel=True" in t and "bro=False" in t and aid in t


def test_enighed_naar_begge_afviser(taendt, aid):
    S.note_requested(aid, tool_name="bash", arguments=ARGS)
    # ingen beslutning → broen afviser; den koerende kode gjorde ogsaa
    S.note_claim(aid, tool_name="bash", arguments=ARGS, legacy_allowed=False)
    assert S.taellere()["enige"] == 1


# ── den må ALDRIG kunne vælte en godkendelse ─────────────────────────────

def test_en_doed_bro_kaster_ikke(taendt, aid, monkeypatch):
    monkeypatch.setattr(B, "request",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    S.note_requested(aid, tool_name="bash", arguments=ARGS)   # kaster ikke
    assert S.taellere()["fejl"] == 1


def test_en_doed_bro_vaelter_ikke_overtagelsen(taendt, aid, monkeypatch):
    # godkendelsen SKAL findes, ellers springer skyggen over foer den naar claim
    S.note_requested(aid, tool_name="bash", arguments=ARGS)
    monkeypatch.setattr(B, "claim",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    S.note_claim(aid, tool_name="bash", arguments=ARGS, legacy_allowed=True)
    assert S.taellere()["fejl"] == 1


def test_ingen_af_kaldene_returnerer_noget_nogen_kan_handle_paa(taendt, aid):
    assert S.note_requested(aid, tool_name="bash", arguments=ARGS) is None
    assert S.note_decided(aid, approved=True) is None
    assert S.note_claim(aid, tool_name="bash", arguments=ARGS,
                        legacy_allowed=True) is None


# ── tællerne er aflæselige udefra ────────────────────────────────────────

def test_taellerne_kan_laeses_fra_en_anden_proces(taendt, aid):
    S.note_requested(aid, tool_name="bash", arguments=ARGS)
    assert (S.taellere_fra_cache() or {}).get("registreret") == 1


def test_en_godkendelse_fra_FOER_taendingen_er_ikke_en_uenighed(taendt, aid):
    """De første målinger efter en tænding ville ellers være lutter falske
    uenigheder — og så lærer man at ignorere signalet præcis når det begynder
    at virke."""
    # ingen note_requested: godkendelsen blev oprettet foer skyggen var taendt
    S.note_claim(aid, tool_name="bash", arguments=ARGS, legacy_allowed=True)
    t = S.taellere()
    assert t["uenige"] == 0 and t["sprunget_over"] == 1


def test_en_KENDT_godkendelse_maales_stadig(taendt, aid):
    S.note_requested(aid, tool_name="bash", arguments=ARGS)
    S.note_decided(aid, approved=True)
    S.note_claim(aid, tool_name="bash", arguments=ARGS, legacy_allowed=True)
    assert S.taellere()["enige"] == 1


# ── posten skyggen selv aabnede, skal ogsaa lukkes ───────────────────────

def test_note_settled_lukker_en_overtagelse(taendt, aid):
    """Set paa CT105: seks overtagelser stod som `dispatching` og blev aldrig
    lukket. `dispatching` BETYDER «udfaldet er ukendt», og `expire_stale`
    roerer den aldrig netop derfor — saa hver maaling saa ud som et nedbrud."""
    from core.runtime import db_approval_bridge as B
    from core.services.approval_bridge_shadow import (
        note_claim, note_decided, note_requested, note_settled,
    )
    a, args = aid, {"command": "ls"}
    note_requested(a, tool_name="bash", arguments=args)
    note_decided(a, approved=True)
    note_claim(a, tool_name="bash", arguments=args, legacy_allowed=True)
    assert B.state(a)["state"] == B.DISPATCHING

    note_settled(a, ok=True)
    assert B.state(a)["state"] == B.COMPLETED


def test_note_settled_paa_en_ukendt_er_stille(taendt):
    """En godkendelse fra foer taendingen har ingen post. At lukke den er ikke
    en fejl — der er bare intet at lukke."""
    from core.services.approval_bridge_shadow import note_settled, taellere
    foer = taellere()["fejl"]
    note_settled("approval-findes-ikke", ok=True)
    assert taellere()["fejl"] == foer
