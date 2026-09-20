"""Bjørns valg i komponisten: tog han forslaget, eller skrev han selv?

Bjørn 20/9-2026: «vi skal gemme brugerens valg, dvs. om de brugte den
suggested (tab) i composer eller skrev der egen besked så næste forslag bliver
mere mig/målrettet».

Det farlige her er ikke et tabt tal — det er at hans egen beskedtekst skulle
snige sig med. Derfor står den test først.
"""
from __future__ import annotations

import pytest

from core.runtime import db_composer_choice as dc


def _vis(fid: str = "cs-1", sid: str = "s1", tekst: str = "Ret det og kør testene igen"):
    return dc.noter_vist(forslag_id=fid, session_id=sid, forslag=tekst,
                         kilde_besked_id="message-7")


def test_HANS_egen_tekst_kan_ikke_havne_her(isolated_runtime):
    """Skriver han sin egen besked, gemmes ét bit — ikke hvad han skrev.

    Et signal om hvad der IKKE virkede kræver ingen kopi af hvad han sagde i
    stedet. Kolonnerne er derfor talt op med vilje: kommer der en til, skal
    nogen tage stilling til hvad der står i den."""
    _vis()
    dc.noter_valg(forslag_id="cs-1", valg="eget")
    raekke = dc.seneste_valg()[0]
    assert set(raekke) == {
        "forslag_id", "session_id", "forslag", "kilde_besked_id",
        "valg", "vist_at", "valgt_at",
    }
    # Forslaget er serverens egne ord. Alt andet tekstligt er id'er.
    assert raekke["forslag"] == "Ret det og kør testene igen"
    assert raekke["valg"] == "eget"


def test_vist_opretter_raekken_og_valget_afslutter_den(isolated_runtime):
    _vis()
    assert dc.seneste_valg()[0]["valg"] == "vist"
    assert dc.noter_valg(forslag_id="cs-1", valg="accepteret") is True
    raekke = dc.seneste_valg()[0]
    assert raekke["valg"] == "accepteret"
    assert raekke["valgt_at"]
    assert raekke["kilde_besked_id"] == "message-7", \
        "uden beskeden det kom af, er valget ubrugeligt"


def test_et_forslag_der_ALDRIG_blev_vist_findes_ikke(isolated_runtime):
    """Krav 11. Blev forslaget hentet men kasseret — feltet var ikke tomt,
    svaret streamede, sessionen skiftede — ringer klienten aldrig. Talte vi
    dem med, ville afvisnings-raten måle hans skrivetempo frem for forslaget."""
    dc.noter_valg(forslag_id="cs-aldrig-vist", valg="afvist")
    assert dc.seneste_valg() == []


def test_det_FOERSTE_terminale_valg_vinder(isolated_runtime):
    """Tager han forslaget med Tab og retter i det, er svaret stadig at han
    tog det. En senere afsendelse må ikke skrive «accepteret» om til «eget»."""
    _vis()
    dc.noter_valg(forslag_id="cs-1", valg="accepteret")
    dc.noter_valg(forslag_id="cs-1", valg="eget")
    assert dc.seneste_valg()[0]["valg"] == "accepteret"


def test_samme_forslag_vist_TO_gange_er_ét_forslag(isolated_runtime):
    """En genrender eller en dobbelt-effekt må ikke tælle som to tilbud."""
    _vis()
    _vis()
    assert len(dc.seneste_valg()) == 1


def test_et_UKENDT_valg_afvises(isolated_runtime):
    _vis()
    assert dc.noter_valg(forslag_id="cs-1", valg="måske") is False
    assert dc.noter_valg(forslag_id="cs-1", valg="vist") is False, \
        "«vist» er ikke et terminalt valg"
    assert dc.seneste_valg()[0]["valg"] == "vist"


def test_et_tomt_kald_skriver_ikke(isolated_runtime):
    assert dc.noter_vist(forslag_id="", session_id="s1", forslag="x") is False
    assert dc.noter_vist(forslag_id="cs-2", session_id="", forslag="x") is False
    assert dc.noter_vist(forslag_id="cs-3", session_id="s1", forslag="   ") is False
    assert dc.seneste_valg() == []


def test_optaelling_er_grundlaget_for_virker_det(isolated_runtime):
    for i, valg in enumerate(("accepteret", "eget", "afvist", "accepteret")):
        _vis(fid=f"cs-{i}")
        dc.noter_valg(forslag_id=f"cs-{i}", valg=valg)
    _vis(fid="cs-staar-aabent")
    assert dc.optaelling() == {"vist": 1, "accepteret": 2, "afvist": 1, "eget": 1}


def test_valgene_kan_hentes_pr_SESSION(isolated_runtime):
    _vis(fid="cs-a", sid="s1")
    _vis(fid="cs-b", sid="s2")
    assert [r["forslag_id"] for r in dc.seneste_valg(session_id="s2")] == ["cs-b"]
