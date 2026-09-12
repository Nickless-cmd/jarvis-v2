"""Bevis er ikke det samme som enighed — Fase 11.

MAALT 10/9-2026: kanariefuglen sad paa TO sessioner der havde vaeret doede i
20 timer (sidste haendelse 9/9 kl. 16:32), mens dagens trafik loeb i en tredje
session som slet ikke var i ledgeren. Timepulsen meldte «ledger enige, +0»
hver time.

Det lyder som loebende verifikation. Det er tavshed. Og et skifte — fase 11's
hele formaal — maa aldrig hvile paa tavshed.

`enige` er sandt naar der ingen uenigheder er, ogsaa naar der ingenting er at
vaere uenig om. Derfor staar dommen nu for sig i `bevis`.
"""
from __future__ import annotations

import core.services.projection_drift as pd


def _stub(monkeypatch, ledger, tabel):
    # Signaturen tager nu ogsaa projektions-modulet: sammenligneren slaar
    # tabelnavn, haendelsestype og kolonner op i stedet for at kende dem.
    monkeypatch.setattr(pd, "_fra_ledger", lambda sid, m: ledger)
    monkeypatch.setattr(pd, "_fra_tabellen", lambda sid, m: tabel)


def _besked(mid, tekst, tid="2026-09-10T10:00:00"):
    return {"message_id": mid, "role": "user", "content": tekst,
            "created_at": tid}


def test_to_tomme_sider_er_IKKE_bevis(monkeypatch):
    """Kernen. Foer var dette udfald ikke til at skelne fra en verificeret
    session — og det var praecis den tilstand kanariefuglen stod i."""
    _stub(monkeypatch, [], [])
    d = pd.compare("s")
    assert d["enige"] is True, "der ER ingen uenigheder — det er stadig sandt"
    assert d["bevis"] == "intet-bevis", (
        "to tomme sider blev regnet som verificeret enighed")


def test_ens_indhold_er_verificeret(monkeypatch):
    m = [_besked("m1", "hej"), _besked("m2", "hej igen")]
    _stub(monkeypatch, list(m), list(m))
    d = pd.compare("s")
    assert d["enige"] is True
    assert d["bevis"] == "verificeret"


def test_forskel_er_uenig(monkeypatch):
    _stub(monkeypatch, [_besked("m1", "hej")], [_besked("m1", "noget andet")])
    d = pd.compare("s")
    assert d["enige"] is False
    assert d["bevis"] == "uenig"
    assert d["uenigheder"]


def test_tidsstemplerne_afsloerer_en_doed_kanariefugl(monkeypatch):
    """En laeser skal kunne se om «enige» hviler paa noget fra i dag eller fra
    i forgaars. Uden det ser en doed session ud som en sund."""
    gammel = [_besked("m1", "hej", "2026-09-09T16:32:18")]
    _stub(monkeypatch, list(gammel), list(gammel))
    d = pd.compare("s")
    assert d["nyeste_ledger"] == "2026-09-09T16:32:18"
    assert d["nyeste_tabel"] == "2026-09-09T16:32:18"


def test_en_tom_side_mod_en_fuld_er_uenig_ikke_intet_bevis(monkeypatch):
    """Den farligste forveksling: ledgeren tom, tabellen fuld. Det er ikke
    «intet bevis» — det er den vaerste slags uenighed, og et skifte dér ville
    goere en samtale til ingenting."""
    _stub(monkeypatch, [], [_besked("m1", "hej")])
    d = pd.compare("s")
    assert d["bevis"] == "uenig"
    assert d["enige"] is False
