"""Et nyt godkendelses-vaerktoej maa ikke rulles ud foer broen baerer — K4.

«approval-required tools cannot enter rollout until the invocation-bound
atomic approval bridge is active.»

At annoncere et vaerktoej til modellen ER dets udrulning. De nitten der
allerede lever paa den gamle inline-sti staar navngivet — at tage `bash` og
`write_file` fra ham ville vaere langt vaerre end den gaeld de udgoer.

Den vigtigste test er `test_gaten_fjerner_intet_i_dag`: en vagt der ved et
uheld skjuler vaerktoejer er en langt stoerre skade end den forebygger.
"""
from __future__ import annotations

import logging

import pytest

from core.tools import approval_rollout_gate as G
from core.tools import tool_definition_v2 as V


@pytest.fixture(autouse=True)
def _rene():
    V._nulstil_for_tests()
    yield
    V._nulstil_for_tests()


# ── den vigtigste: gaten maa ikke tage noget fra ham ─────────────────────

def test_gaten_fjerner_intet_i_dag(isolated_runtime):
    assert G.blocked() == []


def test_bash_og_write_file_annonceres_stadig(isolated_runtime):
    """De to er hans vej udenom systemet og hans mest brugte skrivning."""
    from core.tools.simple_tools import get_tool_definitions
    navne = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
    for n in ("bash", "write_file", "edit_file", "operator_bash"):
        assert n in navne, n


def test_gaten_aendrer_ikke_antallet(isolated_runtime, monkeypatch):
    """Sammenlign MED og UDEN gaten — ikke bare 'ser rigtigt ud'."""
    from core.tools.simple_tools import get_tool_definitions
    med = len(get_tool_definitions(role="owner", scope=""))
    monkeypatch.setattr(G, "may_advertise", lambda n: (True, ""))
    uden = len(get_tool_definitions(role="owner", scope=""))
    assert med == uden


# ── og den den findes for ────────────────────────────────────────────────

def test_et_NYT_godkendelses_vaerktoej_holdes_tilbage(isolated_runtime, monkeypatch):
    """Hele pointen. `stripe_create_issuing_card` staar paa listen; fjern den
    derfra, og den maa ikke annonceres saa laenge broen er i skygge."""
    monkeypatch.setattr(G, "GRANDFATHERED",
                        G.GRANDFATHERED - {"stripe_create_issuing_card"})
    ok, grund = G.may_advertise("stripe_create_issuing_card")
    assert ok is False and "ikke aktiv" in grund
    assert G.blocked() == ["stripe_create_issuing_card"]


def test_naar_broen_er_aktiv_maa_det_rulles_ud(isolated_runtime, monkeypatch):
    monkeypatch.setattr(G, "GRANDFATHERED",
                        G.GRANDFATHERED - {"stripe_create_issuing_card"})
    monkeypatch.setattr(G, "bridge_active", lambda: True)
    ok, grund = G.may_advertise("stripe_create_issuing_card")
    assert ok is True and grund == "broen er aktiv"


def test_et_vaerktoej_uden_godkendelse_roeres_ikke(isolated_runtime):
    assert G.may_advertise("read_file") == (True, "")


def test_et_ukendt_navn_roeres_ikke(isolated_runtime):
    assert G.may_advertise("findes_ikke")[0] is True


# ── afbryderen ───────────────────────────────────────────────────────────

def test_broen_er_i_SKYGGE_som_standard(isolated_runtime):
    assert G.bridge_active() is False


@pytest.mark.parametrize("v", [None, {}, {"enabled": False}, "sludder", True])
def test_kun_et_eksplicit_true_siger_at_broen_baerer(monkeypatch, v):
    import core.services.central_switches as CS
    monkeypatch.setattr(CS.shared_cache, "get", lambda *a, **k: v)
    assert G.bridge_active() is False


def test_skygge_afbryderen_er_IKKE_haandhaevelses_afbryderen(isolated_runtime,
                                                             monkeypatch):
    """`approval/bridge_shadow` er taendt i produktion. Den maa ikke faa gaten
    til at tro at broen baerer."""
    import core.services.central_switches as CS
    from core.services.central_switches import _key
    kun_skygge = {_key("approval", "bridge_shadow"): {"enabled": True}}
    monkeypatch.setattr(CS.shared_cache, "get", lambda k, *a, **kw: kun_skygge.get(k))
    assert G.bridge_active() is False


# ── fail-open, men ikke tavst ────────────────────────────────────────────

def test_en_kollapset_gate_annoncerer_frem_for_at_skjule(isolated_runtime,
                                                         monkeypatch, caplog):
    monkeypatch.setattr(V, "describe",
                        lambda n: (_ for _ in ()).throw(RuntimeError("i stykker")))
    with caplog.at_level(logging.WARNING):
        ok, grund = G.may_advertise("write_file")
    assert ok is True
    assert "kunne ikke afgoere" in grund and "approval_rollout_gate" in caplog.text


def test_en_kollapset_gate_i_annonceringen_giver_hele_listen(isolated_runtime,
                                                             monkeypatch):
    from core.tools.simple_tools import get_tool_definitions
    import core.tools.approval_rollout_gate as GG
    monkeypatch.setattr(GG, "may_advertise",
                        lambda n: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert len(get_tool_definitions(role="owner", scope="")) > 400


# ── gaelden skal kunne taelles ───────────────────────────────────────────

def test_gaelden_er_et_TAL_ikke_en_fornemmelse(isolated_runtime):
    d = G.debt()
    assert len(d) == 19
    assert "bash" in d and "operator_write_file" in d


def test_listen_raadner_ikke(isolated_runtime):
    """Et navn paa listen der ikke laengere findes, skjuler at gaelden er
    betalt — eller at vaerktoejet er vaek."""
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    kendte = {d["function"]["name"] for d in TOOL_DEFINITIONS}
    ukendte = sorted(G.GRANDFATHERED - kendte)
    assert ukendte == [], f"staar paa listen, findes ikke: {ukendte}"


def test_alle_paa_listen_kraever_faktisk_godkendelse(isolated_runtime):
    """Et navn der IKKE kraever godkendelse har ingen grund til at staa der."""
    unoedige = sorted(n for n in G.GRANDFATHERED
                      if (V.describe(n) or None) is not None
                      and V.describe(n).approval_requirement != V.APPROVAL_ASK)
    assert unoedige == [], f"unoedige paa listen: {unoedige}"
