"""`remember_this` venter ikke på kant-udledningen.

Bjørn 17/9-2026: «hans remember_this tool er historisk langsomt». Målt på
ct105: 9.705 aktive poster er kandidater hver gang, hver kandidats markdown-fil
læses fra disken, og entity-overlappet regnes ud — **~12 sekunder** pr. note.
Selve skrivningen er hurtig; det var efterarbejdet der stod i vejen for svaret.

En afgrænsning af kandidaterne blev prøvet først og målt: tærsklen er 0,4, og
entity + kæde kan alene give 0,35, så den eksakte øvre grænse udelukkede 0 af
9.705. Afgrænsning ville derfor ikke være en optimering, men en ændring af
hvilke kanter der findes.

Derfor: skriv posten, svar, og udled kanterne bagefter. Går tråden tabt, tager
`b4_catchup_infer_once` posten — den er bygget til præcis `skip_temporal`.
"""
from __future__ import annotations

import time

from core.services import brain_edge_worker as w


def test_koesaet_blokerer_ikke_paa_udledningen(monkeypatch):
    """Selve pointen: værktøjet må ikke vente på 12 sekunders efterarbejde."""
    startet = []

    def _langsom(entry_id, now=None):
        startet.append(entry_id)
        time.sleep(0.4)
        return 3

    monkeypatch.setattr("core.services.jarvis_brain.infer_temporal_edges", _langsom)
    t0 = time.monotonic()
    assert w.koesaet("brain-1") is True
    assert time.monotonic() - t0 < 0.1, "koesaet ventede paa udledningen"
    # Og arbejdet sker faktisk — en kø der taber alt ville vaere vaerre.
    for _ in range(40):
        if startet:
            break
        time.sleep(0.05)
    assert startet == ["brain-1"]


def test_en_fejlet_udledning_vaelter_ikke_arbejderen(monkeypatch):
    """Time-passet tager posten. En tabt udledning er en forsinkelse, ikke et
    tab — derfor må den heller ikke slå tråden ihjel for de næste."""
    kaldt = []

    def _skiftevis(entry_id, now=None):
        kaldt.append(entry_id)
        if entry_id == "daarlig":
            raise RuntimeError("disken er fuld")
        return 1

    monkeypatch.setattr("core.services.jarvis_brain.infer_temporal_edges", _skiftevis)
    w.koesaet("daarlig")
    w.koesaet("god")
    for _ in range(40):
        if "god" in kaldt:
            break
        time.sleep(0.05)
    assert kaldt == ["daarlig", "god"]


def test_et_tomt_id_koesaettes_ikke():
    assert w.koesaet("") is False


def test_vaerktoejet_springer_kant_udledningen_over():
    """Kilde-vagt: skrev `remember_this` stadig synkront, ville alt ovenfor
    være ligegyldigt — køen ville bare stå tom bag en tolv-sekunders ventetid."""
    import inspect
    from core.tools import jarvis_brain_tools
    kilde = inspect.getsource(jarvis_brain_tools.remember_this)
    assert "skip_temporal=True" in kilde
    assert "koesaet" in kilde
    assert kilde.index("skip_temporal=True") < kilde.index("koesaet("), \
        "koeen skal fyldes EFTER skrivningen"


def test_time_passet_findes_stadig():
    """Baggrunden er kun sikker fordi opsamlingen findes. Forsvinder den, er
    en tabt tråd et tabt kantsæt — og så holder den beslutning ikke."""
    from core.services.jarvis_brain_daemon import b4_catchup_infer_once
    assert callable(b4_catchup_infer_once)
