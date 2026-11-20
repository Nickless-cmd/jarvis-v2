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


# ── Læringsmålet klippede midt i ordet (20/11-2026) ──────────────────────────


def test_laeringsmaal_klippes_ved_ordgraense_ikke_midt_i_ordet():
    """`mistake[:60]` klippede «...ud fra proce» — netop ordene der bar meningen.

    Målt 20/11-2026: alle 5 seneste curriculum-focus-task'er i runtime_tasks
    var 60-tegns-klippede ved oprettelse. Klippet skal bære meningen,
    ikke ødelægge den.
    """
    from core.services.self_experiments import _klip_ord_graense

    maal = ("Konkluderer at processerne 'kører som det skal' ud fra "
            "proces-tilstedeværelse alene — uden at måle arbejdet")
    assert len(maal) > 60

    klippet = _klip_ord_graense(maal, loft=60)
    assert len(klippet) <= 60
    # Enten hele teksten eller resten starter med mellemrum — aldrig midt i ord.
    rester = maal[len(klippet):]
    assert rester == "" or rester.startswith(" ")


def test_curriculum_laeringsmaal_baerer_hele_meningen(monkeypatch):
    """Læringsmålet i planen skal kunne læses som en hel sætning."""
    import json

    import core.services.self_experiments as SE

    langt = ("Konkluderer at processerne 'kører som det skal' ud fra "
             "proces-tilstedeværelse alene — uden at måle arbejdet i begge "
             "ender, uden at verificere processens starttid mod kodens "
             "commit-tidspunkt og uden en omkostnings-post fra processen selv")
    assert len(langt) > 180

    monkeypatch.setattr(
        "core.runtime.db.get_latest_cognitive_personality_vector",
        lambda: {
            "confidence_by_domain": json.dumps({}),
            "recurring_mistakes": json.dumps([langt]),
        },
    )
    flade = SE.generate_learning_curriculum()
    mistak = [c for c in flade["curriculum"] if c["type"] == "mistake_pattern"]
    assert mistak, "læringsmålet mangler i planen"

    suggestion = mistak[0]["suggestion"]
    efter_undgaa = suggestion[len("Undgå: "):]
    assert efter_undgaa in langt, "klippet er ikke et forstykke af originalen"
    rester = langt[len(efter_undgaa):]
    assert rester == "" or rester.startswith(" "), (
        f"klippet rammer midt i et ord: «{efter_undgaa[-12:]}»"
    )


# ── Læringsplanen var et fast punkt (20/11-2026) ─────────────────────────────


def test_planen_gaar_videre_til_naeste_kandidat_naar_de_svageste_er_i_koeen(
    isolated_runtime,
):
    """`items[:limit]` klippede FØR frasorteringen — så de tre samme sad fast.

    Målt 20/11-2026: 175 domæner under 0,5, og sorteret stigende giver de
    altid de samme tre. Var de tre i forvejen i køen, blev de frasorteret,
    `created` var 0, og svaret var «Curriculum is current» — mens kandidat 4
    og nedefter (gentagne fejl, afsluttede eksperimenter) aldrig blev nået.
    """
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({
            "desk render capabilities": 0.32,
            "face recognition": 0.35,
            "adherence-analyse": 0.35,
            "vision capability analysis": 0.36,
            "godkendelses- og kortanalyse": 0.37,
        }),
        recurring_mistakes=json.dumps([]),
    )
    from core.services.self_experiments import materialize_learning_curriculum_tasks

    foerste = materialize_learning_curriculum_tasks(limit=3)
    assert int(foerste["created"]) == 3

    anden = materialize_learning_curriculum_tasks(limit=3)
    assert int(anden["created"]) == 2, (
        "planen nåede ikke kandidat 4 og 5 — den er stadig et fast punkt"
    )
    scopes = {
        str(isolated_runtime.db.get_runtime_task(tid)["scope"])
        for tid in anden["task_ids"]
    }
    assert scopes == {"vision capability analysis", "godkendelses- og kortanalyse"}
