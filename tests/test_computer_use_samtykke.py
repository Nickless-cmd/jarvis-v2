"""Mus og tastatur kræver samtykke — skærmbilledet gør ikke.

Bjørn 21/9-2026 bad om ægte computer-use «som i cc desktop». Målt samme dag:
de 55 operator-værktøjer FANDTES, men nut.js var aldrig installeret, så hvert
kald døde med «Cannot find module '@nut-tree-fork/nut-js'» — mens værktøjerne
blev tilbudt til modellen alligevel.

Sikkerheden så jeg efter i Claude Desktops egen kode, som han foreslog. Deres
`cowork-vm-service` vælger bwrap → KVM → host-uden-isolation som SIDSTE udvej,
binder /usr og /etc read-only og giver en TOM hjemmemappe. Claude Desktop
giver altså aldrig agenten brugerens rigtige mus og tastatur. Det Bjørn beder
om er en stærkere rettighed, og den skal have sin egen port.

Hans valg, ordret: «godkendelse første gang pr. session».
"""
from __future__ import annotations

import pytest

from core.services import computer_use_samtykke as cs
from core.tools.simple_tools import _TOOL_HANDLERS


@pytest.fixture(autouse=True)
def _rent_samtykke():
    cs.traek_tilbage()
    yield
    cs.traek_tilbage()


def _kald(navn, **ekstra):
    return _TOOL_HANDLERS[navn]({"_runtime_session_id": "s1", **ekstra})


def test_foerste_klik_i_en_samtale_beder_om_lov():
    svar = _kald("operator_mouse_click", x=100, y=200)
    assert svar["status"] == "approval_needed"
    assert "mus og dit tastatur" in svar["message"]


def test_efter_ja_er_resten_af_samtalen_fri():
    """Ellers koster én opgave hundredvis af kort, og så bruges det ikke."""
    cs.giv_samtykke("s1")
    svar = _kald("operator_mouse_click", x=1, y=1)
    assert svar["status"] != "approval_needed"


def test_godkendelsen_kommer_tilbage_med_trust_flaget_og_noteres():
    """Samme vej som phone_adb: kortet besvares, kaldet køres igen med flaget."""
    assert not cs.har_samtykke("s1")
    _kald("operator_mouse_click", x=1, y=1, _runtime_trust_all=True)
    assert cs.har_samtykke("s1"), "samtykket blev ikke husket"


def test_samtykke_gaelder_KUN_den_ene_samtale():
    cs.giv_samtykke("s1")
    svar = _TOOL_HANDLERS["operator_mouse_click"]({"_runtime_session_id": "en-anden"})
    assert svar["status"] == "approval_needed"


@pytest.mark.parametrize("navn", sorted(cs.LAESENDE & set(_TOOL_HANDLERS)))
def test_at_LAESE_er_frit(navn):
    """Modellen skal kunne se skærmen for at pege — og et kig ændrer intet."""
    assert not cs.kraever_samtykke(navn)


@pytest.mark.parametrize("navn", sorted(cs.HANDLENDE & set(_TOOL_HANDLERS)))
def test_alle_handlende_vaerktoejer_er_faktisk_pakket_ind(navn):
    """Porten sidder i dispatch-tabellen, så nummer ti ikke kan smutte forbi."""
    svar = _TOOL_HANDLERS[navn]({"_runtime_session_id": "s-ny"})
    assert svar["status"] == "approval_needed", f"{navn} slap forbi porten"


def test_noedbremsen_lukker_alt():
    cs.giv_samtykke("s1")
    cs.giv_samtykke("s2")
    cs.traek_tilbage()
    assert cs.aktive_samtaler() == []


def test_en_fejl_i_porten_slipper_IKKE_kaldet_igennem(monkeypatch):
    """Fail-safe retning: kan samtykket ikke afgøres, sker der ingenting."""
    import core.tools.simple_tools as st
    monkeypatch.setattr(cs, "har_samtykke",
                        lambda sid: (_ for _ in ()).throw(RuntimeError("nede")))
    svar = _TOOL_HANDLERS["operator_mouse_click"]({"_runtime_session_id": "s1"})
    assert svar["status"] == "error"
    assert "samtykke" in svar["error"]
