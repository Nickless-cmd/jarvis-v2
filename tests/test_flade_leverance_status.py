"""`leverance-status` — katalogets første skabelon (14/11-2026).

Testen måler DEGRADERINGEN, ikke udseendet. Det er hele pointen med typen:
én dårlig egenskab må ødelægge ét element, ikke fladen. Erklærer guarden en
korrekt skrevet flade «død», erstattes den af en grå linje OG der fyrer et
helt modelkald for at «rette» den — den fejlform opgaven blev skrevet for at
undgå.
"""
from __future__ import annotations

from core.services.jarvis_ui_guard import _diagnosticér


def _flade(**kw):
    data = {"type": "leverance-status", "title": "Leverance"}
    data.update(kw)
    return data


def test_fuld_flade_er_ok():
    niveau, fejl = _diagnosticér(_flade(items=[
        {"label": "Evaluator", "status": "leveret", "bevis": "commit 8ee7403b5"},
        {"label": "Streaming", "status": "leveret", "bevis": "commit 7776c7b1d"},
        {"label": "Handlende flader", "status": "igang", "bevis": "denne tur"},
    ]))
    assert niveau == "ok"
    assert fejl == []


def test_ukendt_status_degraderer_men_draber_ikke():
    """Parseren falder tilbage til `naeste`. Guarden må ikke sige «død»."""
    niveau, fejl = _diagnosticér(_flade(items=[
        {"label": "A", "status": "faerdig", "bevis": "x"},
    ]))
    assert niveau == "delvis", "en tastefejl i ét felt må ikke koste hele fladen"
    assert any("ukendt status" in f for f in fejl)


def test_manglende_bevis_degraderer_men_draber_ikke():
    niveau, fejl = _diagnosticér(_flade(items=[
        {"label": "A", "status": "leveret"},
    ]))
    assert niveau == "delvis"
    assert any("bevis" in f for f in fejl)


def test_ingen_brugbare_items_er_doed():
    """Uden en enkelt post er der intet at vise — først HER er «død» rigtigt."""
    niveau, fejl = _diagnosticér(_flade(items=[{"status": "leveret"}]))
    assert niveau == "død"
    assert fejl


def test_loftet_over_tolv_er_delvis():
    items = [{"label": f"Punkt {i}", "status": "leveret", "bevis": "x"} for i in range(14)]
    niveau, fejl = _diagnosticér(_flade(items=items))
    assert niveau == "delvis"
    assert any("kun 12 vises" in f for f in fejl)
