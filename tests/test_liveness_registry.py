from core.services.liveness_registry import (
    classify_table,
    is_alive,
    liveness_summary,
)


def test_orphaned_classified_with_replacement():
    e = classify_table("cognitive_missions")
    assert e["status"] == "orphaned"
    assert "agent_dispatch" in e["replacement"]


def test_replaced_points_to_active_table():
    e = classify_table("cognitive_dream_hypotheses")
    assert e["status"] == "replaced"
    assert e["replacement"] == "runtime_dream_hypothesis_signals"


def test_wired_is_alive():
    assert classify_table("cognitive_gut_state")["status"] == "wired"
    assert is_alive("cognitive_gut_state") is True


def test_orphaned_is_not_alive():
    assert is_alive("cognitive_trade_outcomes") is False


def test_active_and_manual_and_replaced_count_as_alive():
    assert is_alive("private_brain_records") is True       # active
    assert is_alive("meta_learning_hypotheses") is True    # manual_only
    assert is_alive("cognitive_dream_hypotheses") is True  # replaced (ikke død)


def test_unknown_table_is_unclassified_not_dead():
    e = classify_table("some_random_table")
    assert e["status"] == "unclassified"
    assert is_alive("some_random_table") is False  # ukendt ≠ levende, men heller ikke "død"


def test_summary_has_orphaned_and_replaced():
    s = liveness_summary()
    assert "cognitive_epistemic_claims" in s["orphaned"]
    assert s["replaced"]["cognitive_dream_hypotheses"] == "runtime_dream_hypothesis_signals"
    assert s["counts"]["orphaned"] >= 4


# ── Moduler uden bord (25/9-2026) ────────────────────────────────────────
#
# Registret daekkede kun tabeller. Jarvis' audit fandt 27 borde uden raekker;
# en parallel gennemgang fandt 11 MODULER uden bord — moduler der gemmer i en
# modul-global liste der doer ved genstart og er usynlig for den proces der
# bygger fladen. Samme sag set fra hver sin ende.

def test_et_modul_der_kaldes_men_ikke_gemmer_er_IKKE_levende():
    """`uden_bord` er den status der manglede. Uden den ville de elleve se ud
    som «unclassified», altsaa som et spoergsmaal ingen har stillet.

    `continuity_kernel` stod her indtil den fik sit bord 25/9-2026. Testen
    pinner nu VOKABULARET frem for et bestemt modul: at status'en findes og
    betyder «gemmer ikke» — ellers ville den doe naar den sidste post rykker
    til `bygget`, og det er praecis naar den skal blive staaende.
    """
    from core.services.liveness_registry import _MODUL_LEVENDE, module_persists

    assert "uden_bord" not in _MODUL_LEVENDE
    assert module_persists("et-modul-der-ikke-findes") is False


def test_de_ti_byggede_er_markeret_som_byggede():
    from core.services.liveness_registry import module_persists
    for m in (
        "body_memory",
        "forgetting_curve",
        "decision_ghosts",
        "memory_tattoos",
        "ghost_networks",
        "text_resonance",
        "continuity_kernel",
        "initiative_accumulator",
        "boredom_curiosity_bridge",
    ):
        assert module_persists(m) is True, m


def test_en_projektion_gemmer_intet_men_er_ikke_doed():
    """`cognitive_core_experiments` samler fem andres flader og har ingen egen
    tilstand. «Gemmer ikke» er kun en mangel naar modulet HAR noget at miste."""
    from core.services.liveness_registry import (
        classify_module,
        module_is_alive,
        module_persists,
    )

    assert classify_module("cognitive_core_experiments")["status"] == "projektion"
    assert module_persists("cognitive_core_experiments") is False
    assert module_is_alive("cognitive_core_experiments") is True


def test_continuity_kernel_er_IKKE_afloest_af_continuity():
    """Jeg var ved at klassificere den som afloest. Den goer noget andet:
    eksistens-FOELELSEN mellem tik, ikke tilstands-TRANSPORT mellem sessioner.

    Testen laeser de to moduler frem for at stole paa noten — en note kan
    blive forkert uden at nogen opdager det.
    """
    import ast
    import pathlib

    def api(m):
        t = ast.parse(pathlib.Path(f"core/services/{m}.py").read_text(encoding="utf-8"))
        return {n.name for n in t.body
                if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")}

    assert not (api("continuity_kernel") & api("continuity")), (
        "de to deler nu funktioner — saa kan «ikke afloest» vaere blevet forkert")
    assert not (api("initiative_accumulator") & api("initiative_queue"))


def test_et_ukendt_modul_er_unclassified_ikke_doedt():
    """Registrets hele formaal: «STOPPE konfabulation om at hans systemer er
    doede». Et modul der ikke staar her er et spoergsmaal, ikke en dom."""
    from core.services.liveness_registry import classify_module
    assert classify_module("noget_der_ikke_findes")["status"] == "unclassified"
