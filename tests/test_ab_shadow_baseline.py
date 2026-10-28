"""Shadow-baseline for A/B-armen (28/10-2026).

BAGGRUND. `record_trial` startede med `if not is_explore_live(): return`. Det var
korrekt som værn mod forurening — shadow udelader intet, så der findes ingen ABSENT-data
— men det betød også at PRESENT-armen, den arm der FAKTISK sker, aldrig blev målt.
Resultatet var et forsøg der stod i Mission Control som "kørende" med `present_total: 0`
i månedsvis, uden nogen baseline at holde et fremtidigt ABSENT-resultat op imod.

RETTELSEN ER ASYMMETRISK, og det er hele pointen:
  * PRESENT tæller ALTID — sektionen var med, intet blev udeladt, nul risiko for turen.
  * ABSENT tæller ALDRIG i shadow — shadow udelader intet, så en "absent"-tælling ville
    være en løgn om hvad der skete med turen.

Disse tests værner begge sider. Fjernes den ene, bliver enten armen død igen (ingen
baseline) eller uærlig (ABSENT-data der ikke fandtes).
"""
from __future__ import annotations

import pytest

from core.services import central_prompt_explore as cpe


@pytest.fixture()
def kv(monkeypatch):
    """Isoleret KV-lager — rører ikke den levende runtime-state."""
    lager: dict = {}
    monkeypatch.setattr(cpe, "_kv_get", lambda k, d=None: lager.get(k, d))
    monkeypatch.setattr(cpe, "_kv_set", lambda k, v: lager.__setitem__(k, v))
    return lager


def _start(tt: str = "opgave", sec: str = "kerne-selv (Centralens midte)") -> dict:
    st = cpe._new_state(tt, sec)
    cpe._kv_set(cpe._STATE_KEY, st)
    return st


# ── 1. Shadow: PRESENT tæller ────────────────────────────────────────────────────────
def test_shadow_taeller_present_armen(kv) -> None:
    """Den arm der faktisk sker, skal måles — ogsaa naar flaget er slukket."""
    _start()
    assert cpe.is_explore_live() is False
    cpe.record_trial("opgave", ["kerne-selv (Centralens midte)"], "completed")
    st = cpe._kv_get(cpe._STATE_KEY)
    assert st["present_total"] == 1
    assert st["present_good"] == 1


def test_shadow_taeller_fejlet_udfald_som_ikke_god(kv) -> None:
    _start()
    cpe.record_trial("opgave", ["kerne-selv (Centralens midte)"], "failed")
    st = cpe._kv_get(cpe._STATE_KEY)
    assert st["present_total"] == 1
    assert st["present_good"] == 0


# ── 2. MODPRØVE: ABSENT maa ALDRIG tælle i shadow ────────────────────────────────────
def test_shadow_taeller_aldrig_absent(kv) -> None:
    """Shadow udelader intet. En ABSENT-tælling her ville være data om noget der ikke skete."""
    st = cpe._new_state("opgave", "kerne-selv (Centralens midte)")
    st["arm"] = "absent"          # tvinges, som en gammel state kunne stå
    cpe._kv_set(cpe._STATE_KEY, st)
    cpe.record_trial("opgave", [], "completed")   # sektionen var IKKE med
    st = cpe._kv_get(cpe._STATE_KEY)
    assert st["absent_total"] == 0, "shadow målte en ABSENT-tur der aldrig blev udeladt"
    assert st["present_total"] == 0


# ── 3. Live: begge arme tæller som før ───────────────────────────────────────────────
def test_live_taeller_absent_naar_sektionen_er_vaek(kv) -> None:
    kv[cpe._EXPLORE_FLAG] = True
    st = cpe._new_state("opgave", "kerne-selv (Centralens midte)")
    assert st["arm"] == "absent", "live skal starte paa ABSENT-armen"
    cpe._kv_set(cpe._STATE_KEY, st)
    cpe.record_trial("opgave", [], "completed")
    st = cpe._kv_get(cpe._STATE_KEY)
    assert st["absent_total"] == 1
    assert st["absent_good"] == 1


def test_live_afviser_forurenet_absent(kv) -> None:
    """Sektionen VAR med i en absent-tur → tælles ikke (forurener ikke data)."""
    kv[cpe._EXPLORE_FLAG] = True
    _start()
    cpe.record_trial("opgave", ["kerne-selv (Centralens midte)"], "completed")
    st = cpe._kv_get(cpe._STATE_KEY)
    assert st["absent_total"] == 0


# ── 4. Shadow-forsøget maa ikke afsluttes paa halvt grundlag ─────────────────────────
def test_shadow_afslutter_ikke_forsoeg_uden_absent_data(kv) -> None:
    """15 PRESENT-ture i shadow → armen er fuld, men der er intet at sammenligne med.
    Staten skal BEHOLDES (baseline akkumulerer), ikke ryddes."""
    _start()
    for _ in range(cpe._TRIALS_PER_ARM):
        cpe.record_trial("opgave", ["kerne-selv (Centralens midte)"], "completed")
    st = cpe._kv_get(cpe._STATE_KEY)
    assert st, "shadow ryddede forsøget og dermed den eneste baseline"
    assert st["present_total"] == cpe._TRIALS_PER_ARM
    assert st["arm"] == "present"
    assert st["left"] == cpe._TRIALS_PER_ARM, "tælleren skal nulstilles saa den kan fortsætte"


def test_shadow_baseline_kan_ikke_blive_dispensable(kv) -> None:
    """Uden ABSENT-data kan dommen aldrig sige 'undværlig' — uanset baseline-rate."""
    st = cpe._new_state("opgave", "kerne-selv (Centralens midte)")
    st["present_good"], st["present_total"] = 15, 15
    dom = cpe.evaluate_ablation(st)
    assert dom["dispensable"] is False


# ── 5. Manglende kontekst er kun en fejl naar forsøget kører live ────────────────────
def test_manglende_kontekst_taelles_ikke_i_shadow(kv) -> None:
    kv[cpe._EXPLORE_FLAG] = False
    cpe.record_turn_outcome("completed")
    assert cpe._kv_get(cpe._MISSING_KEY, 0) == 0


def test_manglende_kontekst_taelles_naar_live(kv) -> None:
    """Et forsøg der ikke kan maale, skal sige det — ikke tie."""
    kv[cpe._EXPLORE_FLAG] = True
    cpe.record_turn_outcome("completed")
    assert cpe._kv_get(cpe._MISSING_KEY, 0) == 1


# ── 6. Hele kæden i shadow: komposition → udfald → baseline ─────────────────────────
def test_kaeden_ender_i_baseline_uden_live_flag(kv) -> None:
    _start()
    cpe.note_composition("opgave", ["kerne-selv (Centralens midte)"])
    cpe.record_turn_outcome("completed")
    st = cpe._kv_get(cpe._STATE_KEY)
    assert st["present_total"] == 1, "kæden nåede ikke frem til armen i shadow"
    overflade = cpe.build_prompt_explore_surface()
    assert overflade["baseline"]["present_total"] == 1
    assert overflade["baseline"]["present_rate"] == 1.0
    assert overflade["missing_context"] == 0
