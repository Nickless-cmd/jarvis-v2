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


# ── semantisk dedup (31/10-2026) ──────────────────────────────────────────
#
# MAALT paa den levende `forgetting_curve.json` (500 poster): fem grupper
# delte ORDRET samme `content_preview` under forskellige noegler. Noeglen er
# `sha256(focus|summary)`, saa samme udtraek med en anden `focus` fik en ny
# noegle — og dermed frisk `decay_score`. Emnet kunne strukturelt ikke falme.
#
# HVORFOR DEDUP ER EKSAKT OG IKKE EN LIGHEDS-TAERSKEL: Jaccard over ord blev
# maalt paa samme fil. Inden for ét emne (42 poster om «den afbrudte koersel»)
# topper parrene paa 0,667. Paa tvaers naar tilfaeldige par 1,000, fordi
# «somatisk tilstand: cpu 4% · 47°C · 11.2GB fri» og «… cpu 8% · 49°C · 12.2GB
# fri» er samme skabelon med andre tal. Ved taerskel 0,50 fanges 13 aegte
# emne-par — men ogsaa 92 tvaers-par: syv falske for hver aegte. En taerskel
# der matcher alt er lige saa ubrugelig som ingen dedup.

def test_samme_tanke_i_nye_ord_giver_EEN_post():
    """KERNEN. To registreringer af samme udtraek maa ikke give to poster.

    Fejler paa koden foer 31/10-2026: `register_memory` skrev altid en ny post,
    saa emnet fik frisk henfald hver gang det blev formuleret igen.
    """
    F.register_memory(memory_key="noegle-a", content_preview="Den afbrudte kørsel hænger stadig")
    F.register_memory(memory_key="noegle-b", content_preview="den afbrudte kørsel hænger stadig!")

    reg = state_store.load_json("forgetting_curve", {})
    assert len(reg) == 1, f"to poster om samme udtræk: {list(reg)}"
    post = next(iter(reg.values()))
    assert post["reinforcement_count"] >= 1, "den gensete post skal være forstærket"


def test_forskellige_emner_smelter_IKKE_sammen():
    """Den modsatte vej. En dedup der matcher alt gør kurven til én klump.

    De to tekster deler skabelonen «somatisk tilstand: cpu N% · N°C · N.NGB
    fri» — præcis den form der gav Jaccard 1,0 på tværs i den levende fil. De
    er alligevel to forskellige målinger og skal blive to poster.
    """
    F.register_memory(memory_key="s1", content_preview="somatisk tilstand: cpu 4% · 47°C · 11.2GB fri")
    F.register_memory(memory_key="s2", content_preview="somatisk tilstand: cpu 8% · 49°C · 12.2GB fri")

    reg = state_store.load_json("forgetting_curve", {})
    assert len(reg) == 2, f"to målinger blev smeltet sammen: {list(reg)}"


def test_tikket_deduplikerer_ogsaa(monkeypatch):
    """`tick()` har sin EGEN registrering — fixet skal ramme den vej der kører.

    Samme udtraek med to forskellige `focus` giver to noegler. Uden dedup i
    tikket blev det andet talt som nyt, og det er præcis den vej produktionen
    bruger (hjerteslaget), ikke `register_memory`.
    """
    _hjerne(monkeypatch, [{"focus": "tankestrøm", "summary": "jeg tæller kolonner og værdier"},
                          {"focus": "oplevelse", "summary": "jeg tæller kolonner og værdier"}])
    ud = F.tick(30.0)
    assert ud["registreret"] == 1, f"samme udtræk blev talt som nyt: {ud}"
    assert ud["forstaerket"] == 1
    assert state_store.load_json("forgetting_curve", {}).__len__() == 1


# ── gamle poster uden `summary` (31/10-2026, anden runde) ──────────────────
#
# Foerste udgave af dedup'en skrev `summary` paa NYE poster og sammenlignede
# mod det felt. Men de 500 poster der laa i filen foer fixet har intet
# `summary`, saa deres `content_preview` — MED `focus`-praefiks — var det
# eneste at sammenligne mod. En gentagelse under et andet `focus` bar derfor
# praefikset med og kunne pr. konstruktion aldrig matche.
#
# MAALT paa de 500 levende poster: 0 af 200 gamle poster blev fanget ved
# gentagelse. Fixet virkede kun fremad.
#
# Rettelsen strikker praefikset af og klipper sammenligningen til
# `_PREVIEW_LAENGDE` i begge ender — fordi `content_preview` er TRUNKERET ved
# registrering, saa to identiske udtraek kan vaere klippet paa hver sin plads.
# Maalt efter: 197 af 197 fanget, 0 falske match.

def test_gammel_post_uden_summary_fanges_ved_gentagelse(monkeypatch):
    """KERNEN i anden runde. Posten er skrevet FOER fixet: intet `summary`."""
    state_store.save_json("forgetting_curve", {
        "gammel-noegle": {
            "decay_score": 0.4,
            "reinforcement_count": 0,
            "content_preview": "tankestrøm: jeg tæller kolonner og værdier i hver række",
            "registered_at": "2026-10-01T00:00:00Z",
            "last_referenced_at": "2026-10-01T00:00:00Z",
        }
    })
    # Samme udtraek, nu under et ANDET fokus -> ny noegle, men samme indhold.
    _hjerne(monkeypatch, [{"focus": "oplevelse",
                           "summary": "jeg tæller kolonner og værdier i hver række"}])
    ud = F.tick(30.0)

    reg = state_store.load_json("forgetting_curve", {})
    assert len(reg) == 1, f"den gamle post blev ikke genkendt: {list(reg)}"
    assert ud["registreret"] == 0, f"gentagelsen blev talt som ny: {ud}"
    assert ud["forstaerket"] == 1
    assert next(iter(reg.values()))["reinforcement_count"] == 1


def test_trunkeret_gammel_post_fanges_paa_sit_foerste_stykke(monkeypatch):
    """`content_preview` er klippet ved 100 TEGN ved registrering.

    To identiske udtraek der er klippet paa hver sin plads deler derfor kun det
    foerste stykke. Uden at klippe sammenligningen til samme laengde ville de
    aldrig matche — og det var praecis hvad de 6 resterende dublet-grupper i
    den levende fil var.
    """
    lang = "den afbrudte kørsel under værktøjsudførelsen hænger stadig som et åbent sår " * 2
    state_store.save_json("forgetting_curve", {
        "gammel": {
            "decay_score": 0.2,
            "reinforcement_count": 0,
            "content_preview": f"tankestrøm: {lang}"[:F._PREVIEW_LAENGDE],
            "registered_at": "2026-10-01T00:00:00Z",
            "last_referenced_at": "2026-10-01T00:00:00Z",
        }
    })
    _hjerne(monkeypatch, [{"focus": "oplevelse", "summary": lang}])
    ud = F.tick(30.0)
    assert ud["registreret"] == 0, f"trunkeret gentagelse blev ny post: {ud}"
    assert len(state_store.load_json("forgetting_curve", {})) == 1


def test_praefiks_strip_smelter_IKKE_korte_forskellige_tekster():
    """Den modsatte vej for anden runde.

    Rettelsen klipper til 100 tegn og sammenligner EKSAKT — bevidst ikke
    `startswith`. En kort tekst er praefiks af en laengere, og med `startswith`
    ville «jeg tæller kolonner» smelte sammen med «jeg tæller kolonner og
    værdier». Det maa ikke ske: de er to forskellige erkendelser.
    """
    F.register_memory(memory_key="kort", content_preview="jeg tæller kolonner")
    F.register_memory(memory_key="lang", content_preview="jeg tæller kolonner og værdier i hver række")
    assert len(state_store.load_json("forgetting_curve", {})) == 2
