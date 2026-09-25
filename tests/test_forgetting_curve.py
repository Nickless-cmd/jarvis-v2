"""Glemselskurven skal have noget at glemme — og overleve en genstart.

Maalt 25/9-2026: `_DECAY_REGISTRY` var en modul-global dict uden persistering,
og `register_memory` havde INGEN kalder i produktion. Henfaldet kunne koere;
der var bare aldrig noget at lade henfalde. Overfladen sagde «No memories
tracked yet» og ville have sagt det for altid.

`apply_decay_tick` kaldes kun naar beslutnings-motoren vaelger handlingen
`decay_forgotten_signals` — altsaa naar han BESLUTTER at glemme. Den sti er
bevaret; `tick()` er den loebende.
"""
from __future__ import annotations

import importlib
import json

import core.services.forgetting_curve as F
from core.runtime import state_store
import pytest


@pytest.fixture(autouse=True)
def _tom_tilstand():
    """Hver test starter paa en tom fil.

    Isolationen kom foer fra at hver test patchede `_storage_path` til sin egen
    `tmp_path`. Med `state_store` er stien skaermet af conftest' autouse-fixture
    `_guard_prod_state_dir` — men den mappe er SESSIONS-bred, saa tilstand
    laekker mellem tests i samme fil hvis ingen rydder op. Det var netop den
    skaerm der manglede for `shared_dir()`: uden den skrev disse tests i den
    aegte `~/.jarvis-v2/shared/runtime/`.
    """
    state_store.save_json("forgetting_curve", {})
    yield




def _hjerne(monkeypatch, udtraek):
    monkeypatch.setattr(
        "core.services.session_distillation.build_private_brain_context",
        lambda **kw: {"active": True, "excerpts": udtraek})


def test_kurven_overlever_en_genstart():
    """KERNEN. En modul-global dict doede med processen."""
    F.register_memory(memory_key="m1", content_preview="noget vigtigt")

    F2 = importlib.reload(F)          # ny proces
    assert F2.build_forgetting_curve_surface()["total_tracked"] == 1


def test_tikket_registrerer_arbejdssaettet(monkeypatch):
    """`register_memory` havde ingen kalder — nu laeser tikket hvad der er i sind."""
    _hjerne(monkeypatch, [{"focus": "a", "summary": "foerste"},
                          {"focus": "b", "summary": "anden"}])
    ud = F.tick(30.0)
    assert ud["registreret"] == 2 and ud["sporet"] == 2


def test_det_der_ses_igen_forstaerkes_og_falmer_langsommere(monkeypatch, tmp_path):
    """Hele kurven: genbesoeg nulstiller henfaldet og bremser det naeste gang."""
    _hjerne(monkeypatch, [{"focus": "a", "summary": "foerste"}])
    F.tick(30.0)
    ud = F.tick(30.0)
    assert ud["registreret"] == 0 and ud["forstaerket"] == 1

    post = next(iter(state_store.load_json("forgetting_curve", {}).values()))
    assert post["reinforcement_count"] == 1
    # forstaerket -> henfaldet er halveret (increment / (1*0.5 + 1))
    assert 0 < post["decay_score"] < 0.01


def test_det_der_holder_op_med_at_blive_set_falmer(monkeypatch):
    _hjerne(monkeypatch, [{"focus": "a", "summary": "foerste"}])
    F.tick(30.0)
    _hjerne(monkeypatch, [])                      # ikke i sind laengere
    for _ in range(95):
        F.tick(30.0)
    assert F.build_forgetting_curve_surface()["faded_memories"] == 1


def test_en_falmet_erindring_SLETTES_ikke():
    """«Removed from active prompt injection but archived for possible revival»
    — den maa aldrig blive til ingenting."""
    F.register_memory(memory_key="m1", content_preview="gammel", initial_decay=0.95)
    assert F.get_active_memories() == []
    faldne = F.get_faded_memories()
    assert len(faldne) == 1 and faldne[0]["content_preview"] == "gammel"


def test_noeglen_er_stabil_paa_tvaers_af_processer():
    """Udtraek baerer intet id. Var noeglen ustabil, ville alt se nyt ud hver gang."""
    a = F.noegle_for("fokus", "en opsummering")
    b = F.noegle_for(" fokus ", "en opsummering ")
    assert a == b
    assert a != F.noegle_for("fokus", "en ANDEN opsummering")


def test_tikket_skriver_filen_ÉN_gang(monkeypatch):
    """Foerste udgave kaldte register/reinforce per udtraek — tolv fulde
    laes+skriv-cyklusser — og talte dubletter som nye (maalt: «10» mens der
    stod 6)."""
    skrivninger = []
    aegte = F._save
    monkeypatch.setattr(F, "_save", lambda reg: skrivninger.append(1) or aegte(reg))
    _hjerne(monkeypatch, [{"focus": "a", "summary": f"nr {i}"} for i in range(12)])
    ud = F.tick(30.0)
    # én fra selve tikket + én fra apply_decay_tick
    assert len(skrivninger) == 2, f"{len(skrivninger)} skrivninger"
    assert ud["registreret"] == 12 == ud["sporet"]


def test_arbejdssaettet_er_afgraenset(tmp_path):
    """Og de mest faldne ryddes foerst — de er alligevel ude af injektionen."""
    for i in range(F._MAX_SPOR + 40):
        F.register_memory(memory_key=f"m{i}", initial_decay=(i % 100) / 100)
    reg = state_store.load_json("forgetting_curve", {})
    assert len(reg) == F._MAX_SPOR
    assert max(float(v["decay_score"]) for v in reg.values()) < 0.99


def test_en_hjerne_der_ikke_kan_laeses_vaelter_ikke_tikket(monkeypatch):
    monkeypatch.setattr(
        "core.services.session_distillation.build_private_brain_context",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("ingen hjerne")))
    assert F.tick(30.0)["registreret"] == 0


@pytest.mark.timeout(15)
def test_tikket_laaser_sig_ikke_selv_fast(monkeypatch):
    """`tick()` og `apply_decay_tick()` tager BEGGE `med_laas` paa samme noegle.

    `flock` er knyttet til den aabne fil-beskrivelse, og `med_laas` aabner en
    ny hver gang — to laase paa samme noegle i samme proces er derfor ikke
    re-entrante. Var kaldet indlejret, ville tikket vente paa sig selv for
    altid; her slippes laasen foer `apply_decay_tick` kaldes.

    Testen faar en timeout frem for en assertion, fordi en deadlock ikke
    fejler — den haenger.
    """
    _hjerne(monkeypatch, [{"focus": "a", "summary": "noget"}])
    ud = F.tick(30.0)
    assert ud["registreret"] == 1
