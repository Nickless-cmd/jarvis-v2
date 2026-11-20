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


# ── En konstant er ikke en svaghed (20/11-2026) ───────────────────────────────


def test_frosne_domaener_bliver_ikke_laeringsmaal(isolated_runtime):
    """`face recognition` stod på 0,35 i alle 1.011 vektorer — og var et mål.

    Målt 20/11-2026: 689 domæner har nogensinde stået i vektoren, 509 af dem
    har ALDRIG ændret værdi. `face recognition` er en af dem: 0,35 i hver
    eneste version, og der findes ingen ansigtsgenkendelse i kodebasen —
    strengen findes kun som fixture i denne fil. Navnet blev opfundet af
    modellen i `confidence_by_domain`, og intet har rørt tallet siden.

    Fordi 0,35 sorterer nederst, lå den altid blandt de tre første, og
    curriculum'et gjorde den til et læringsmål: «Bliv bedre til face
    recognition — confidence er kun 35 %». Et mål der ikke kan arbejdes med og
    ikke kan lukkes.

    Testen kræver to vektorer: med én kan konstant og måling ikke skelnes, og
    så skal planen sige det højt i stedet for at gætte.
    """
    import core.services.self_experiments as SE

    # Cachen lever mellem tests i samme proces; nøglen er vektor-rækken, men vi
    # rydder den alligevel så testen ikke arver en anden bases svar.
    getattr(SE, "_MAALTE_CACHE", {}).update({"noegle": None, "domaener": None})

    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({
            "face recognition": 0.35,          # konstant
            "desk render capabilities": 0.45,  # målt
        }),
        recurring_mistakes=json.dumps([]),
    )
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({
            "face recognition": 0.35,          # stadig 0,35 — aldrig rørt
            "desk render capabilities": 0.38,  # har flyttet sig
        }),
        recurring_mistakes=json.dumps([]),
    )
    # To skift, ikke ét: et domæne der kun har flyttet sig én gang er en
    # selvrapport der skiftede mening — se `test_et_enkelt_skift_er_ikke_en_maaling`.
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({
            "face recognition": 0.35,
            "desk render capabilities": 0.32,
        }),
        recurring_mistakes=json.dumps([]),
    )

    plan = SE.generate_learning_curriculum()
    pulje = list(plan.get("candidates") or plan.get("curriculum") or [])
    domaener = {str(c.get("domain")) for c in pulje if c.get("type") == "weakness"}

    assert "face recognition" not in domaener, (
        "en domæne der aldrig har ændret værdi blev gjort til læringsmål"
    )
    assert "desk render capabilities" in domaener, (
        "en domæne der FAKTISK har flyttet sig faldt ud — filteret er for hårdt"
    )
    assert int(plan.get("unmeasured_weak_domains") or 0) == 1
    assert "aldrig maalt" in str(plan.get("summary") or "")


def test_uden_historik_gaetter_planen_ikke(isolated_runtime):
    """Én vektor = ingen historik. Så må planen ikke lade som om den filtrerer.

    Alternativet — at behandle alt som målt — ville være den samme tavshed der
    gjorde konstanterne til mål i 1.011 vektorer.
    """
    import core.services.self_experiments as SE

    getattr(SE, "_MAALTE_CACHE", {}).update({"noegle": None, "domaener": None})

    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({"face recognition": 0.35}),
        recurring_mistakes=json.dumps([]),
    )

    plan = SE.generate_learning_curriculum()

    assert "domain_history" in list(plan.get("kilde_fejl") or []), (
        "planen kunne ikke skelne, men sagde det ikke"
    )


def test_et_enkelt_skift_er_ikke_en_maaling(isolated_runtime):
    """`souls-build analyse`: 0,45 i 10 vektorer, 0,38 i de næste 205.

    Præcis ÉN ændring — og den faldt lige efter domænets fødsel. Reglen «to
    forskellige værdier» gjorde den derfor til en MÅLT svaghed, og den blev et
    læringsmål: «Bliv bedre til souls-build analyse — confidence er kun 38 %».

    Der findes ikke én linje kode med det navn. Der findes til gengæld rigtige
    tråde om «souls-appen» — så navnet er ikke grebet ud af luften: et PROJEKT
    blev skrevet ind som en KOMPETENCE. Et tal der kun har flyttet sig én gang
    er en mening der skiftede, ikke en måling.

    Målt 20/11-2026 i den levende base: 177 svage domæner, 24 med mindst ét
    skift, kun 7 med to eller flere.
    """
    import core.services.self_experiments as SE

    getattr(SE, "_MAALTE_CACHE", {}).update({"noegle": None, "domaener": None})

    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({"souls-build analyse": 0.45}),
        recurring_mistakes=json.dumps([]),
    )
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({"souls-build analyse": 0.38}),
        recurring_mistakes=json.dumps([]),
    )
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({"souls-build analyse": 0.38}),
        recurring_mistakes=json.dumps([]),
    )

    plan = SE.generate_learning_curriculum()
    pulje = list(plan.get("candidates") or plan.get("curriculum") or [])
    domaener = {str(c.get("domain")) for c in pulje if c.get("type") == "weakness"}

    assert "souls-build analyse" not in domaener, (
        "et domæne der kun har skiftet mening én gang blev gjort til et læringsmål"
    )
    assert int(plan.get("unmeasured_weak_domains") or 0) == 1



def test_konklusion_fra_eksperiment_klippes_ved_ordgraense(monkeypatch):
    """`exp.get("hypothesis", "")[:60]` var den sidste rå klipning i planen.

    Samme fejlklasse som `mistake[:60]` — men den overlevede den første
    rettelse, fordi den ligger i en anden gren af samme funktion. Et
    læringsmål der ender i «...ud fra proce» kan ikke arbejdes med.
    """
    import json

    import core.services.self_experiments as SE

    hypotese = ("Konkluderer at processerne 'kører som det skal' ud fra "
                "proces-tilstedeværelse alene — uden at måle arbejdet i de "
                "to ender, og uden at verificere starttid mod commit-tid")
    assert len(hypotese) > 60

    monkeypatch.setattr(
        SE, "list_cognitive_experiments",
        lambda **_: [{
            "hypothesis": hypotese,
            "result": json.dumps({"best_cohort": "kort", "significant": True,
                                  "difference": 0.22}),
        }],
    )
    monkeypatch.setattr(
        "core.runtime.db.get_latest_cognitive_personality_vector",
        lambda: {"confidence_by_domain": json.dumps({}),
                 "recurring_mistakes": json.dumps([])},
    )

    flade = SE.generate_learning_curriculum()
    konklusioner = [c for c in flade["curriculum"]
                    if c["type"] == "experiment_conclusion"]
    assert konklusioner, "eksperiment-konklusionen mangler i planen"

    fokus = str(konklusioner[0]["focus"])
    assert fokus in hypotese, "klippet er ikke et forstykke af originalen"
    rester = hypotese[len(fokus):]
    assert rester == "" or rester.startswith(" "), (
        f"klippet rammer midt i et ord: «{fokus[-12:]}»"
    )



# ── Curriculum-scope er en stabil domænenøgle, ikke en rå fejlsætning ────────


def test_to_formuleringer_af_samme_fejltype_rammer_samme_noegle():
    from core.services.self_experiments import normaliser_fejl_til_domaene as n

    a = n("Afbrød sit eget svar midt i sætningen ('og den skal lukkes m")
    b = n("Holder op midt i en sætning ('jeg skal vide om det er fronte")
    assert a == b == "afbryder-midt-i-saetning"
    c = n("Konkluderer at processerne 'kører som det skal' ud fra proce")
    assert c == "konkluderer-uden-bevis" and c != a


def test_ukendt_fejlformulering_giver_eksplicit_noegle():
    from core.services.self_experiments import (
        UKENDT_FEJL_DOMAENE,
        normaliser_fejl_til_domaene as n,
    )

    for tekst in ("noget helt andet og nyt", "", "   "):
        ud = n(tekst)
        assert ud == UKENDT_FEJL_DOMAENE == "ukendt-fejl"


def test_materialiseret_scope_er_kategori_ikke_raa_saetning(isolated_runtime):
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({"desk render capabilities": 0.9}),
        recurring_mistakes=json.dumps([
            "Afbrød sit eget svar midt i sætningen ('og den skal lukkes m",
            "Holder op midt i en sætning ('jeg skal vide om det er fronte",
        ]),
    )
    from core.services.self_experiments import materialize_learning_curriculum_tasks

    ud = materialize_learning_curriculum_tasks(limit=3)
    scopes = [str(isolated_runtime.db.get_runtime_task(t)["scope"]) for t in ud["task_ids"]]
    assert scopes == ["afbryder-midt-i-saetning"]  # to sætninger → ét domæne, dedupet


# ── Curriculum paa fast kadence, uafhaengigt af action-vaelgeren (20/11-2026) ──


def test_ukendt_fejl_bliver_ikke_til_en_task(isolated_runtime):
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({"planning": 0.35}),
        recurring_mistakes=json.dumps(["uforstaaeligt a", "uforstaaeligt b"]),
    )
    from core.services.self_experiments import materialize_learning_curriculum_tasks

    ud = materialize_learning_curriculum_tasks(limit=5)
    scopes = [isolated_runtime.db.get_runtime_task(t)["scope"] for t in ud["task_ids"]]
    assert "ukendt-fejl" not in scopes
    assert "planning" in scopes


# ── Selvrapporteret er ikke målt (20/11-2026) ────────────────────────────────

def _nulstil_cache() -> None:
    import core.services.self_experiments as SE

    SE._MAALTE_CACHE.clear()
    SE._MAALTE_CACHE.update(
        {"noegle": None, "domaener": None, "mekanisk_noegle": None, "mekaniske": None}
    )


def test_selvrapporteret_svaghed_bliver_ikke_kaldt_maalt(isolated_runtime):
    """Et domaene med kun smaa selvrapporterede skridt maa ikke kaldes maalt.

    Maalt 20/11-2026: 23 af 24 domaener der slap gennem «to skift»-reglen
    havde udelukkende skridt paa 0,01-0,04. Planen skrev «confidence er kun
    38 %» som om tallet var maalt — og sendte mig ud efter en svaghed der
    ikke findes.
    """
    import json

    from core.runtime.db import upsert_cognitive_personality_vector

    _nulstil_cache()
    # app: 0,44 -> 0,42 -> 0,40 — to skift, men ingen mekaniske (0,02).
    # kadence: 0,42 -> 0,40 -> 0,45 — det SIDSTE skridt er mekanisk (+0,05).
    # (20/11-2026: kravet er det sidste skridt, ikke et hvilket som helst —
    # se test_mekanisk_skridt_der_er_overskrevet_gor_tallet_umalt.)
    historik = [
        {"app reverse engineering": 0.44, "kadence-maaling i drift": 0.42},
        {"app reverse engineering": 0.42, "kadence-maaling i drift": 0.40},
        {"app reverse engineering": 0.40, "kadence-maaling i drift": 0.45},
    ]
    for vektor in historik:
        upsert_cognitive_personality_vector(
            confidence_by_domain=json.dumps(vektor)
        )

    # «kadence» bliver kun målt fordi den staar i MÅLINGSSPORET — ikke fordi
    # dens sidste skridt tilfaeldigt er +0,05. (Ændret 20/11-2026: spooret er
    # autoriteten, se test_skridtstoerrelse_er_ikke_et_bevis.)
    from core.services import capability_measurement as cm

    cm.set_domain_confidence(
        "kadence-maaling i drift", 0.45, evidence="test: maalt i spooret"
    )
    _nulstil_cache()

    import core.services.self_experiments as SE

    plan = SE.generate_learning_curriculum()
    poster = {
        str(c.get("domain") or ""): c for c in plan.get("curriculum") or []
    }

    selvrap = poster.get("app reverse engineering")
    assert selvrap is not None, "selvrapporteret domaene faldt helt ud af planen"
    assert selvrap["measured"] is False
    tekst = str(selvrap.get("suggestion") or "")
    assert "confidence er kun" not in tekst, (
        f"selvrapporteret tal blev kaldt en maaling: {tekst!r}"
    )
    assert "uden en maaling bag" in tekst

    # 20/11-2026: DENNE KONTRAKT BLEV VENDT. Den kraevede foer at et +0,05-skridt
    # blev kaldt «maalt». Men skridtet blev skrevet af `_confidence_delta` paa
    # «completed + did_work», og `did_work` betoed «runnet kaldte et vaerktoej».
    # Engagement, ikke maaling. Testen var dermed selv med til at goere et
    # spoegelse til en maalt svaghed.
    kadence = poster.get("kadence-maaling i drift")
    assert kadence is not None, "domaenet faldt helt ud af planen"
    assert kadence["measured"] is False, (
        "et +0,05-skridt fra den fjernede lofts-mekanisme blev kaldt maalt"
    )
    assert "uden en maaling bag" in str(kadence.get("suggestion") or "")


# ── Det sidste skridt ejer tallet (20/11-2026) ───────────────────────────────

def test_mekanisk_skridt_der_er_overskrevet_gor_tallet_umalt(isolated_runtime):
    """`dil_widgets animationstal`: 0,40 -> 0,36 -> 0,41 (+0,05) -> 0,36.

    Det mekaniske skridt ligger i MIDTEN. Tallet der staar nu (0,36) blev
    skrevet af modellen bagefter — og netop dette domaene blev 20/11-2026
    givet til mig som opgave med ordene «maalt confidence 36 %». Det var
    ikke maalt: det var en selvrapport der engang havde vaeret forbi en
    maaling, og som derefter var skrevet tilbage.
    """
    import json

    from core.runtime.db import upsert_cognitive_personality_vector

    _nulstil_cache()
    historik = [
        {"dil_widgets animationstal": 0.40},
        {"dil_widgets animationstal": 0.36},
        {"dil_widgets animationstal": 0.41},  # +0,05 — mekanisk
        {"dil_widgets animationstal": 0.36},  # selvrapport ovenpaa
    ]
    for vektor in historik:
        upsert_cognitive_personality_vector(confidence_by_domain=json.dumps(vektor))

    import core.services.self_experiments as SE

    post = {
        str(c.get("domain") or ""): c
        for c in SE.generate_learning_curriculum().get("curriculum") or []
    }.get("dil_widgets animationstal")
    assert post is not None, "domaenet faldt ud af planen"
    assert post["measured"] is False, (
        "et mekanisk skridt der er overskrevet af en selvrapport blev kaldt maalt"
    )
    assert "uden en maaling bag" in str(post.get("suggestion") or "")


# ── Skridtstørrelse er ikke et bevis (20/11-2026) ────────────────────────────

def test_skridtstoerrelse_er_ikke_et_bevis(isolated_runtime):
    """`souls-build analyse`: 0,45 -> 0,38 -> 0,43 (+0,05) — og IKKE målt.

    MÅLT 20/11-2026 i den levende base: domænet havde fem skift, og det sidste
    var præcis +0,05 kl. 06:48:24. Planen skrev «maalt confidence 43 %» — og
    gav mig det som dagens opgave. Men +0,05 var arbejds-løftet fra
    `record_curriculum_outcome`, som blev fjernet kl. 10:00 netop fordi arbejde
    ikke er en måling. Domænet findes ikke i målingssporet.

    Et skridt på den rigtige størrelse er derfor ikke et bevis. Sporet er.
    """
    import json

    from core.runtime.db import upsert_cognitive_personality_vector

    _nulstil_cache()
    historik = [
        {"souls-build analyse": 0.45},
        {"souls-build analyse": 0.38},
        {"souls-build analyse": 0.43},  # +0,05 — ser mekanisk ud
    ]
    for vektor in historik:
        upsert_cognitive_personality_vector(confidence_by_domain=json.dumps(vektor))

    import core.services.self_experiments as SE

    post = {
        str(c.get("domain") or ""): c
        for c in SE.generate_learning_curriculum().get("curriculum") or []
    }.get("souls-build analyse")
    assert post is not None, "domaenet faldt ud af planen"
    assert post["measured"] is False, (
        "et skridt paa +0,05 uden en maaling i sporet blev kaldt maalt"
    )
    assert "uden en maaling bag" in str(post.get("suggestion") or "")


def test_fisher_skelner_stoej_fra_effekt():
    from core.services.self_experiments import _fisher_exact_p

    # 2 af 2 mod 18 af 22 — praecis den konklusion der blev et laeringsmaal.
    assert _fisher_exact_p(2, 0, 18, 4) > 0.5
    # 18 af 20 mod 4 af 20 — en forskel der ikke kan forklares af tilfaeld.
    assert _fisher_exact_p(18, 2, 4, 16) < 0.001


def test_to_observationer_konkluderer_ikke():
    import json as _json

    from core.services.self_experiments import _evaluate_experiment

    cohorts = {
        "control": {"n": 22, "success": 18},
        "treatment": {"n": 2, "success": 2},
    }
    result_json, status = _evaluate_experiment(cohorts)
    result = _json.loads(result_json)

    assert status == "running", "2 observationer blev konkluderet"
    assert result["significant"] is False
    assert result["sample_ok"] is False
    assert "for faa observationer" in result["reason"]
    assert result["n_best"] == 2 and result["n_worst"] == 22


def test_reelt_sample_konkluderer():
    import json as _json

    from core.services.self_experiments import _evaluate_experiment

    cohorts = {
        "control": {"n": 20, "success": 4},
        "treatment": {"n": 20, "success": 18},
    }
    result_json, status = _evaluate_experiment(cohorts)
    result = _json.loads(result_json)

    assert status == "concluded"
    assert result["significant"] is True
    assert result["best_cohort"] == "treatment"
    assert result["p_value"] < 0.001


def test_tom_kohorte_er_ikke_nul_procent_succes():
    from core.services.self_experiments import _evaluate_experiment

    # Foer: success/max(n,1) gjorde en uberoert kohorte til 0 % succes, saa
    # den kunne tabe til en anden kohorte uden at nogen havde betraadt den.
    cohorts = {
        "control": {"n": 40, "success": 30},
        "treatment": {"n": 0, "success": 0},
    }
    result_json, status = _evaluate_experiment(cohorts)

    assert result_json == "{}" and status == "running"


def test_correction_rate_er_ikke_laengere_en_tautologi():
    from core.services.self_experiments import _success_for_visible_run

    eksp = {"metric": "correction_rate"}
    kort = {"status": "completed", "text_preview": "kort svar her"}
    langt = {"status": "completed", "text_preview": "ord " * 60}

    # Foer gav begge et udfald bestemt af kohorte-reglen selv: kort -> True,
    # langt -> False, uanset om nogen faktisk rettede svaret.
    assert _success_for_visible_run(experiment=eksp, run=kort) is None
    assert _success_for_visible_run(experiment=eksp, run=langt) is None


def test_konklusionens_tekst_baerer_samplet():
    from core.services.self_experiments import _eksperiment_forslag
    tekst = _eksperiment_forslag(
        "treatment",
        {"difference": 0.18, "n_best": 2, "n_worst": 22, "p_value": 1.0},
    )
    assert "n=2 mod 22" in tekst, "samplet mangler i laeringsmaalet"
    assert "p=" in tekst, "p-vaerdien mangler i laeringsmaalet"


# ── Sporet er den eneste kilde til ordet «målt» (20/11-2026) ──────────────────

def test_kun_sporet_kan_kalde_et_tal_maalt(isolated_runtime):
    """To domaener med IDENTISK historik — kun spoeret afgoer.

    Begge slutter med et spring paa praecis +0,05, som er den form den
    fjernede proxy tog fejl af. Forskellen er ikke skridtets stoerrelse, men
    hvem der skrev det: en maaling eller en rettelse.
    """
    import json

    from core.runtime.db import upsert_cognitive_personality_vector
    from core.services import capability_measurement as cm

    # Sporet maa ALDRIG pege paa produktionsfilen i en test.
    assert "pytest" in str(cm._ledger_path()) or "/tmp/" in str(cm._ledger_path()), (
        f"testen ville skrive i den aegte spoer-fil: {cm._ledger_path()}"
    )

    _nulstil_cache()
    for vaerdi in (0.40, 0.45):
        upsert_cognitive_personality_vector(
            confidence_by_domain=json.dumps(
                {"maalte-evne": vaerdi, "kun-rettet": vaerdi}
            )
        )

    sti = cm._ledger_path()
    sti.parent.mkdir(parents=True, exist_ok=True)
    sti.write_text(
        json.dumps(
            {
                "domain": "maalte-evne",
                "value": 0.45,
                "evidence": "målt: 5/5 runder mod grundsandhed",
                "kind": "measurement",
            }
        )
        + "\n"
        + json.dumps(
            {
                "domain": "kun-rettet",
                "value": 0.45,
                "evidence": "tilbagerullet et forkert løft",
                "kind": "correction",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    import core.services.self_experiments as SE

    poster = {
        str(c.get("domain") or ""): c
        for c in SE.generate_learning_curriculum().get("curriculum") or []
    }
    assert "maalte-evne" in poster, "det maalte domaene faldt ud af planen"
    assert poster["maalte-evne"]["measured"] is True
    assert "maalt confidence" in str(poster["maalte-evne"].get("suggestion") or "")
    assert "kun-rettet" in poster, "det rettede domaene faldt ud af planen"
    assert poster["kun-rettet"]["measured"] is False, (
        "en rettelse i spoeret blev laest som en maaling"
    )
    assert "uden en maaling bag" in str(poster["kun-rettet"].get("suggestion") or "")
