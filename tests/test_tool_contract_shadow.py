"""Skyggen for skema-kontrakten — Fase 3, K2.

Den maa maale alt og afgoere intet, indtil nogen bevidst taender for
haandhaevelsen. De to afbrydere er adskilt med vilje: maalingen skal kunne
koere i dagevis uden at haandhaeve, og haandhaevelsen skal kunne slaas fra
uden at maalingen stopper.
"""
from __future__ import annotations

import logging

import pytest

from core.services import tool_contract_shadow as S
from core.tools import tool_schema_contract as K


@pytest.fixture(autouse=True)
def _rene(isolated_runtime):
    S._nulstil_for_tests()
    K._nulstil_for_tests()
    yield
    S._nulstil_for_tests()
    K._nulstil_for_tests()


@pytest.fixture
def taendt(monkeypatch):
    monkeypatch.setattr(S, "live", lambda: True)


# ── afbryderne ───────────────────────────────────────────────────────────

def test_slukket_som_standard():
    assert S.live() is False and S.haandhaever() is False


def test_slukket_maaler_ingenting():
    S.observe("write_memory_topic", {"slug": "x"})
    assert S.taellere()["maalt"] == 0


@pytest.mark.parametrize("v", [None, {}, {"enabled": False}, "sludder", True])
def test_kun_et_eksplicit_true_taender(monkeypatch, v):
    """Husets `is_enabled` er fail-open og ville taende en maaling ingen har
    besluttet."""
    import core.services.central_switches as CS
    monkeypatch.setattr(CS.shared_cache, "get", lambda *a, **k: v)
    assert S.live() is False and S.haandhaever() is False


def test_de_to_afbrydere_er_uafhaengige(monkeypatch):
    import core.services.central_switches as CS
    from core.services.central_switches import _key
    taendte = {_key("tools", "contract_shadow"): {"enabled": True}}
    monkeypatch.setattr(CS.shared_cache, "get", lambda k, *a, **kw: taendte.get(k))
    assert S.live() is True and S.haandhaever() is False


# ── maalingen ────────────────────────────────────────────────────────────

def test_et_rent_kald_taelles_som_rent(taendt):
    S.observe("write_file", {"path": "/a", "content": "x"})
    assert S.taellere()["rene"] == 1 and S.taellere()["haarde"] == 0


def test_et_manglende_paakraevet_felt_er_HAARDT(taendt, caplog):
    with caplog.at_level(logging.WARNING):
        brud = S.observe("write_memory_topic", {"slug": "x", "content": "# hej"})
    assert S.taellere()["haarde"] == 1
    assert [b.haard for b in brud] == [True, True]
    # BEGGE sider i loggen: hvad manglede, OG hvad kaldet havde med.
    assert "title" in caplog.text and "slug" in caplog.text


def test_en_enum_udenfor_listen_er_BLOED(taendt):
    brud = S.observe("recall_memories", {"query": "x", "modalities": ["somatic"]})
    assert S.taellere()["bloede"] == 1 and S.taellere()["haarde"] == 0
    assert not any(b.haard for b in brud)


def test_ukendt_vaerktoej_taelles_for_sig(taendt):
    S.observe("findes_ikke", {"x": 1})
    assert S.taellere()["ukendt_vaerktoej"] == 1


def test_tael_pr_vaerktoej_saa_moensteret_kan_ses(taendt):
    for _ in range(3):
        S.observe("write_memory_topic", {"slug": "x"})
    assert S.pr_vaerktoej()["write_memory_topic/haard"] == 3


# ── den maa aldrig vaelte kaldet den maaler ──────────────────────────────

def test_en_maaling_der_kaster_giver_tom_liste(taendt, monkeypatch, caplog):
    monkeypatch.setattr(K, "violations",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("i stykker")))
    with caplog.at_level(logging.WARNING):
        assert S.observe("write_file", {"path": "/a", "content": "x"}) == []
    assert S.taellere()["fejl"] == 1


def test_taellerne_kan_laeses_fra_en_anden_proces(taendt):
    """En log alene raekker ikke: api og runtime er to processer, og den ene
    kan ikke se den andens hukommelse."""
    S.observe("write_memory_topic", {"slug": "x"})
    fra_cache = S.taellere_fra_cache()
    assert fra_cache and fra_cache["haarde"] == 1
    assert fra_cache["_top"]["write_memory_topic/haard"] == 1


# ── koblingen i chokepunktet ─────────────────────────────────────────────

@pytest.fixture
def _dispatch(monkeypatch):
    """Erstat den ægte dispatch, saa testen maaler KOBLINGEN og ikke 466
    vaerktoejer."""
    import core.tools.simple_tools as ST
    kaldt = []
    monkeypatch.setattr(ST, "_execute_tool_impl",
                        lambda n, a: kaldt.append((n, a)) or {"status": "ok"})
    monkeypatch.setattr("core.tools.tool_call_observation.observe_tool_call",
                        lambda *a: None)
    return kaldt


def test_skyggen_maaler_men_afviser_ikke(isolated_runtime, monkeypatch, _dispatch):
    """Hele grunden til at der er to afbrydere: maalingen skal kunne koere
    laenge uden at aendre noget."""
    import core.tools.simple_tools as ST
    monkeypatch.setattr(S, "live", lambda: True)
    monkeypatch.setattr(S, "haandhaever", lambda: False)

    r = ST.execute_tool("write_memory_topic", {"slug": "x", "content": "# hej"})
    assert r == {"status": "ok"}
    assert len(_dispatch) == 1
    assert S.taellere()["haarde"] == 1


def test_haandhaevelsen_afviser_FOER_afsendelsen(isolated_runtime, monkeypatch,
                                                 _dispatch):
    """Det er hele pointen: det ufuldstaendige kald maa ikke naa vaerktoejet.
    Det var dét der skrev 14 tomme filer og meldte dem gemt."""
    import core.tools.simple_tools as ST
    monkeypatch.setattr(S, "live", lambda: True)
    monkeypatch.setattr(S, "haandhaever", lambda: True)

    r = ST.execute_tool("write_memory_topic", {"slug": "x", "content": "# hej"})
    assert r["status"] == "error"
    assert "title" in r["error"] and "body" in r["error"]
    assert r["schema_version"].startswith("sha256:")
    assert _dispatch == []


def test_haandhaevelsen_afviser_ALDRIG_et_bloedt_brud(isolated_runtime,
                                                      monkeypatch, _dispatch):
    """`recall_memories` med modalities=['somatic'] gav 10 rigtige resultater.
    Skemaet var for snaevert. Det kald skal stadig koere."""
    import core.tools.simple_tools as ST
    monkeypatch.setattr(S, "live", lambda: True)
    monkeypatch.setattr(S, "haandhaever", lambda: True)

    r = ST.execute_tool("recall_memories", {"query": "x", "modalities": ["somatic"]})
    assert r == {"status": "ok"}
    assert len(_dispatch) == 1
    assert S.taellere()["bloede"] == 1


def test_et_rent_kald_gaar_uroert_igennem(isolated_runtime, monkeypatch, _dispatch):
    import core.tools.simple_tools as ST
    monkeypatch.setattr(S, "live", lambda: True)
    monkeypatch.setattr(S, "haandhaever", lambda: True)

    assert ST.execute_tool("write_file", {"path": "/a", "content": "x"}) == {"status": "ok"}
    assert len(_dispatch) == 1


def test_en_kollapset_kontrakt_lader_kaldet_koere(isolated_runtime, monkeypatch,
                                                  _dispatch):
    """En maaling der kan vaelte kaldet den maaler, er ikke en maaling —
    den er en ny fejlkilde."""
    import core.tools.simple_tools as ST
    monkeypatch.setattr(S, "observe",
                        lambda *a: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert ST.execute_tool("write_file", {"path": "/a", "content": "x"}) == {"status": "ok"}
    assert len(_dispatch) == 1
