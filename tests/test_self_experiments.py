"""Laeringsplanen skal kunne blive til opgaver.

15/9-2026: `create_task(run_id=)` blev omdoebt til `origin_ref` i 4b53916a3.
`materialize_learning_curriculum_tasks` sendte stadig `run_id`, fik TypeError
hver gang, og hjerteslagets `except: pass` slugte den. To doegn uden en
eneste curriculum-opgave. Testen kalder den RIGTIGE create_task.
"""
from __future__ import annotations

import json


def test_laeringsplanen_bliver_til_en_opgave_med_ophav(isolated_runtime):
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({"repo_reasoning": 0.2, "planning": 0.35}),
        recurring_mistakes=json.dumps(["Svar bliver for lange i simple repo-opgaver"]),
    )
    from core.services.self_experiments import materialize_learning_curriculum_tasks

    ud = materialize_learning_curriculum_tasks(
        limit=3, origin="heartbeat:curriculum", owner="heartbeat-runtime",
        run_id="heartbeat-tick:abc",
    )

    assert int(ud["created"]) >= 1
    opgave = isolated_runtime.db.get_runtime_task(str(ud["task_ids"][0]))
    assert opgave["kind"] == "curriculum-focus"
    # Tick-id'et er OPHAV, ikke en koersel — derfor origin_ref.
    assert opgave.get("origin_ref") == "heartbeat-tick:abc"


# ── Læringsplanen sagde ikke hvorfor den var tom (25/9-2026) ────────────────


def test_en_tom_plan_er_LEVENDE_ikke_doed():
    """`active` stod som `bool(curriculum)`.

    `cognitive_architecture_surface` læser nøglen som «systemet lever», så en
    plan uden materiale meldte sig død — samme fejlklasse som de otte andre
    flader samme dag.
    """
    from core.services.self_experiments import generate_learning_curriculum

    flade = generate_learning_curriculum()
    assert flade["active"] is True


def test_en_tom_plan_siger_HVORFOR_den_er_tom():
    """«No curriculum generated yet» sagde intet om årsagen.

    Målt på CT105: planen læser `confidence_by_domain` og `recurring_mistakes`
    fra personlighedsvektoren, og de er ikke-tomme i 1 og 0 af 1007 versioner.
    `learned_preferences` — samme skrivevej — er fyldt i 728.
    """
    from core.services.self_experiments import _curriculum_summary

    tekst = _curriculum_summary([], [])
    assert "Ingen plan" in tekst
    assert "svage domaener" in tekst and "afsluttede eksperimenter" in tekst


def test_en_BRAEKKET_kilde_ser_ikke_ud_som_en_tom():
    """De tre `except: pass` gjorde de to tilstande umulige at skelne."""
    from core.services.self_experiments import _curriculum_summary

    tekst = _curriculum_summary([], ["confidence_by_domain"])
    assert "kilderne fejlede" in tekst
    assert "confidence_by_domain" in tekst


def test_en_kilde_der_kaster_taelles_frem_for_at_blive_slugt(monkeypatch):
    import core.services.self_experiments as SE

    def _knaek():
        raise RuntimeError("vektoren er væk")

    monkeypatch.setattr("core.runtime.db.get_latest_cognitive_personality_vector",
                        _knaek)
    flade = SE.generate_learning_curriculum()

    assert "confidence_by_domain" in flade["kilde_fejl"]
    assert "kilderne fejlede" in flade["summary"]
    assert flade["active"] is True, "en brækket kilde er ikke et dødt modul"
