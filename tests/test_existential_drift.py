"""Bevidstheden kunne aldrig nå sin egen tærskel.

Filen havde INGEN test — docstring, `import pytest`, stjerne-import. Fire
linjer der tilfredsstiller dæknings-gaten uden at måle noget.

`format_existential_for_prompt()` er tavs under 0,3, og niveauet vokser med
`seconds / 7200`. Daemon-blokken kaldte med `seconds=30`: 0,00417 pr. tik,
altså 72 tik. Tikket falder ~hvert 9. minut, så det er 11 timers UAFBRUDT
oppetid — og niveauet lå i en modul-global som hver genstart nulstillede.
"""
from __future__ import annotations

import pytest

import core.services.existential_drift as E


@pytest.fixture(autouse=True)
def _tom_tilstand():
    E.reset_existential_drift()
    yield
    E.reset_existential_drift()


def test_tredive_sekunder_naar_aldrig_taersklen():
    """Den hårdkodede værdi, målt: 72 tik før han må sige noget."""
    for _ in range(50):
        E.increment_awareness(30)
    assert E.build_existential_drift_surface()["awareness_level"] < E._TAERSKEL
    assert E.format_existential_for_prompt() == ""


def test_det_maalte_mellemrum_naar_den_paa_fire_tik():
    """551 s var det første målte mellemrum mellem daemon-blokkens kørsler."""
    for _ in range(4):
        E.increment_awareness(551.2)
    flade = E.build_existential_drift_surface()
    assert flade["awareness_level"] >= E._TAERSKEL
    assert flade["over_taerskel"] is True
    assert E.format_existential_for_prompt().startswith("[EKSISTENTIEL:")


def test_etiketten_er_et_ord_der_findes():
    """Stod som `[EKSPISTEMISK:` — hverken et ord eller emnet."""
    E.increment_awareness(7200)
    tekst = E.format_existential_for_prompt()
    assert "EKSPISTEMISK" not in tekst
    assert tekst.startswith("[EKSISTENTIEL:")


def test_bevidstheden_overlever_at_modulet_indlaeses_forfra():
    import importlib

    E.increment_awareness(3600)
    foer = E.build_existential_drift_surface()["awareness_level"]

    frisk = importlib.reload(E)
    try:
        assert frisk.build_existential_drift_surface()["awareness_level"] == foer
    finally:
        frisk.reset_existential_drift()
        importlib.reload(E)


def test_spoergsmaalet_roterer_frem_for_at_blive_trukket():
    """Var `random.choice`. Et kast kan give det samme to gange i træk."""
    set_af_spoergsmaal = []
    for _ in range(len(E._SPOERGSMAAL)):
        set_af_spoergsmaal.append(E.ask_existential_question())
        E.increment_awareness(1)
    assert len(set(set_af_spoergsmaal)) == len(E._SPOERGSMAAL)


def test_niveauet_maettes_ved_en():
    for _ in range(50):
        E.increment_awareness(7200)
    assert E.build_existential_drift_surface()["awareness_level"] == 1.0


def test_et_tomt_modul_er_LEVENDE_ikke_doedt():
    """`active` stod som `_awareness_level > 0`. En nulstillet bevidsthed er
    en tilstand, ikke en død — og api-processen tikker aldrig selv."""
    flade = E.build_existential_drift_surface()
    assert flade["active"] is True
    assert flade["awareness_level"] == 0.0
    assert flade["over_taerskel"] is False
