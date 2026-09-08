"""Cadence-kernen: hvad Keymakeren gør hver halve time.

Fokus her er koblingen, ikke tidsstyringen. Produceren blev udvidet 8/9-2026
med adfærds-nøglen, og den slags udvidelse er præcis dér huset plejer at tabe
ting: koden skrives, og ingen kalder den.
"""

from __future__ import annotations

import inspect

import core.services.internal_cadence_core as C


def test_keymaker_produceren_optjener_BEGGE_slags_noegler():
    """Gate-nøgler måler gates; adfærds-nøglen måler ham. Uden begge kald ville
    den ene halvdel af sløjfen være bygget og aldrig kørt."""
    src = inspect.getsource(C)
    assert "evaluate_keys()" in src, "gate-nøglerne optjenes ikke"
    assert "evaluate_behaviour_key()" in src, "adfærds-nøglen optjenes ikke"


def test_udloebne_noegler_reverteres_i_samme_tick():
    """En tilladelse mistes hvis den ikke fornyes — det er hele pointen med
    at autonomi er en nøgle og ikke en kontakt."""
    assert "expire_due()" in inspect.getsource(C)


def test_keymakeren_er_registreret_som_producer():
    src = inspect.getsource(C)
    assert 'name="keymaker"' in src
    assert "cooldown_minutes=30" in src


def test_produceren_rapporterer_hans_efterlevelse():
    """Tallet skal med ud, ellers kan man ikke se hvor tæt han er på at
    fortjene nøglen uden at slå i databasen."""
    assert "adfaerd" in inspect.getsource(C)


def test_droemme_dommeren_er_registreret():
    """Uden koblingen ville dommeren være endnu et modul der er bygget og
    aldrig kaldt — det hyppigste mønster i dette hus."""
    src = inspect.getsource(C)
    assert 'name="dream_hypothesis_judge"' in src
    assert "koer_dommer" in src


def test_dommeren_koerer_én_gang_i_doegnet():
    """Kandidaterne skrives af drømme-sessionerne (3-4 om dagen). En dom pr.
    time ville bare stille samme spørgsmål til den samme markdown igen."""
    src = inspect.getsource(C)
    i = src.index('name="dream_hypothesis_judge"')
    assert "cooldown_minutes=24 * 60" in src[i:i + 400]


def test_droemme_hoesten_er_registreret():
    src = inspect.getsource(C)
    assert 'name="dream_session_lessons"' in src
    assert "koer_hoest" in src
