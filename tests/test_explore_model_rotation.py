"""Rotationen skal faktisk SKIFTE model — Fase-uafhaengigt, maalt 10/9-2026.

Jarvis koerte explore tre gange mod Bjoerns maskine. Alle tre runder ramte
samme provider og samme model, selvom `egnede_modeller(undtagen=...)` korrekt
udelukkede den.

AARSAGEN, maalt hele vejen ned:

    rotationens valg : mistral/ministral-3b-latest   capability 0,28
    vagten           : 0,28 < 0,6 -> kasser valget
    routeren svarer  : nvidia-nim/nemotron-3-ultra-550b-a55b
                       (0 vaerktoejskald paa 87 koersler)

Blokken fyrer KUN naar kalderen har valgt eksplicit — og den kasserer netop
det valg. Rotationen var koblet paa og uden virkning, og vagten der skal undgaa
svage modeller rutede TIL den model der fabrikerer.
"""
from __future__ import annotations

import inspect


def test_et_eksplicit_valg_respekteres():
    from core.services import agent_runtime_spawn as sp

    par = inspect.signature(sp.spawn_agent_task).parameters
    assert "respekter_model" in par
    kilde = inspect.getsource(sp.spawn_agent_task)
    assert "and not respekter_model:" in kilde, (
        "capability-vagten kasserer stadig et eksplicit valg")


def test_explore_beder_om_at_faa_sit_valg_respekteret():
    from core.tools import simple_tools_explore as e

    kilde = inspect.getsource(e._explore_spawn)
    assert "respekter_model=bool(provider and model)" in kilde, (
        "explores rotation faar stadig sit valg kasseret nedenstroems")


def test_en_omrutning_maa_ikke_lande_paa_en_der_FABRIKERER():
    """Selv naar vagten omruter: erstatningen skal kunne kalde vaerktoejer. En
    vagt der bytter en svag model for en der fabrikerer, goer det vaerre."""
    from core.services import agent_runtime_spawn as sp

    kilde = inspect.getsource(sp.spawn_agent_task)
    assert "kan_kalde_vaerktoejer(_rp, _rm)" in kilde
    assert "_duer" in kilde


def test_rotationen_vaelger_faktisk_noget_ANDET(isolated_runtime, monkeypatch):
    """Selve rotationen — at `undtagen` bider — er uroert og skal blive ved
    med at virke."""
    from core.services import agent_model_fitness as f

    poster = [
        {"provider": "p1", "model": "m1", "enabled": True, "probe_score": 100,
         "probe_detail": {"follows": True}, "kvalitets_score": 90},
        {"provider": "p2", "model": "m2", "enabled": True, "probe_score": 100,
         "probe_detail": {"follows": True}, "kvalitets_score": 80},
    ]
    monkeypatch.setattr(f, "_registret", lambda: poster)
    alle = f.egnede_modeller(maks=4)
    assert ("p1", "m1") in alle
    uden = f.egnede_modeller(undtagen=frozenset({("p1", "m1")}), maks=4)
    assert ("p1", "m1") not in uden, "undtagen-filteret bider ikke"
    assert ("p2", "m2") in uden
