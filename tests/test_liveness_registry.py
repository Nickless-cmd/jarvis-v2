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


# ── Jarvis' audit er lukket (25/9-2026) ─────────────────────────────────────


def _auditens_borde() -> set[str]:
    """Tabelnavnene fra `docs/audits/2026-09-25-tomme-tabeller.md`.

    Læst fra dokumentet frem for kopieret ind: en kopi er et sted mere at
    glemme, og netop den dublet kostede tre røde tests i `test_cluster_infra`
    samme dag — anden gang samme fil blev ramt af den.
    """
    import pathlib
    import re

    tekst = pathlib.Path(
        "docs/audits/2026-09-25-tomme-tabeller.md").read_text(encoding="utf-8")
    navne = set()
    for linje in tekst.split("\n"):
        if not linje.startswith("|"):
            continue
        felter = [f.strip().strip("`") for f in linje.split("|")[1:-1]]
        if len(felter) < 2:
            continue
        # Auditens rækker har formen `| tabel | fil.py:linje |` (eller
        # «INGEN»). Uden det krav talte parseren også ordene fra den
        # opsummerings-tabel jeg selv skrev i bunden — `orphaned`, `wired`,
        # `manual_only` ligner alle et tabelnavn. Den fælde fandt sin egen
        # test med det samme; det er formen der skal måles, ikke kolonne ét.
        if not re.fullmatch(r"[a-z][a-z0-9_]{3,}", felter[0] or ""):
            continue
        andet = felter[1].strip("*` ")
        if not (re.search(r"\.py:\d+", andet) or andet == "INGEN"):
            continue
        navne.add(felter[0])
    return navne


def test_hvert_bord_i_auditen_er_klassificeret():
    """27 tomme borde. Et uklassificeret bord er et spørgsmål ingen har stillet."""
    from core.services.liveness_registry import _REGISTRY

    navne = _auditens_borde()
    assert len(navne) == 27, f"auditen har {len(navne)} borde — er den ændret?"
    mangler = sorted(navne - set(_REGISTRY))
    assert not mangler, f"uklassificerede: {mangler}"


def test_de_tre_slags_tomhed_holdes_adskilt():
    """«Tom» er tre forskellige ting, og kun den ene er en fejl."""
    from core.services.liveness_registry import classify_table

    # Ingen vej til en række: nøglen læses ét sted og skrives kun af en test.
    assert classify_table("cheap_lane_quota_observations")["status"] == "orphaned"
    # Kun en bevidst handling: `record_rca` investigerer med vilje ikke selv.
    assert classify_table("central_rca")["status"] == "manual_only"
    # Live vej, begivenheden er ikke sket: kræver en aktiv research-kørsel.
    assert classify_table("research_sources")["status"] == "wired"


def test_et_manual_only_bord_er_LEVENDE():
    """En knap ingen har trykket på er ikke en død tabel."""
    from core.services.liveness_registry import is_alive

    for bord in ("central_rca", "message_feedback", "cheap_lane_audit"):
        assert is_alive(bord) is True, bord


def test_et_orphaned_bord_er_DOEDT():
    from core.services.liveness_registry import is_alive

    for bord in ("cadence_idempotency_keys", "runtime_world_facts",
                 "cognitive_epistemic_claims", "cheap_lane_quota_observations"):
        assert is_alive(bord) is False, bord


def _kald_grafen(rod) -> dict[str, set[str]]:
    """funktionsnavn -> de funktioner den kalder. Bygget med AST.

    15/11-2026: forgængeren til denne vagt ledte efter en tekststreng og døde,
    da rettelsen fjernede netop den streng. En tekstsoegning efter «kaldes
    denne funktion?» er ogsaa strukturelt forkert: den tæller docstrings og
    kommentarer med. Maalt samme dag fandt en saadan soegning `reconcile_claim`
    i epistemics.py:21 — som er en DOCSTRING der fortæller at funktionen netop
    ikke har kaldere. Vagten ville have rapporteret det stik modsatte af
    sandheden. Kun et `ast.Call`-knudepunkt er et kald.

    Hver konklusion er krydset med en soegning i kilden, saa de to metoder
    ikke kan tage fejl af det samme: `_with_quota_observation` har 8
    kaldesteder, kalder `observe_provider_quota`, som kalder
    `record_quota_observation` (cheap_lane_quotas.py:38).
    """
    import ast
    import pathlib

    kald: dict[str, set[str]] = {}
    for p in (rod / "core").rglob("*.py"):
        if p.name == "liveness_registry.py":
            continue
        try:
            trae = ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for knude in ast.walk(trae):
            if not isinstance(knude, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            kalder = kald.setdefault(knude.name, set())
            for under in ast.walk(knude):
                if not isinstance(under, ast.Call):
                    continue
                f = under.func
                navn = (
                    f.id if isinstance(f, ast.Name)
                    else f.attr if isinstance(f, ast.Attribute)
                    else None
                )
                if navn:
                    kalder.add(navn)
    return kald


def _kaldes_af(kald: dict[str, set[str]], producent: str) -> list[str]:
    """Hvilke funktioner kalder `producent`?"""
    return sorted(f for f, kaldte in kald.items() if producent in kaldte)


def test_en_orphaned_post_skal_kunne_begrunde_at_den_er_naabar():
    """`orphaned` paastaar «ingen vej til en raekke». Paastanden skal maales.

    Vagtens input er HELE registrets orphaned-poster — ikke en tekststreng.
    Forgængeren filtrerede paa «INGEN skrivesti» i `producer` og matchede 0 af
    41 poster efter 3/11-rettelserne: dens loekkekrop koerte aldrig, og
    `17 passed` beviste intet om det den blev bygget til at fange. Her maales
    derimod det paastanden handler om: kan producent-funktionen kaldes?

    Undtagelsen er eksplicit og maalt, ikke gaettet: en post hvis kaede ER live,
    men hvor ingen raekke kan opstaa fordi indgangsbetingelsen aldrig opfyldes,
    saetter `path_reachable: True`. Feltet findes for at de to slags tomhed
    ikke blandes sammen — praecis den fejl 25/9-auditen advarede imod.
    """
    import pathlib
    import re

    from core.services.liveness_registry import _REGISTRY

    rod = pathlib.Path(__file__).resolve().parent.parent
    kald = _kald_grafen(rod)

    orphaned = {
        bord: post for bord, post in _REGISTRY.items()
        if post.get("status") == "orphaned"
    }
    # En vagt der maaler nul poster er dokumentation. Tallet skal staa her,
    # saa naeste aendring i registret ikke kan goere den tavst tom igen.
    assert len(orphaned) >= 8, (
        f"vagten maaler {len(orphaned)} orphaned-poster — registret er aendret, "
        "og en tom vagt beviser intet"
    )

    maalt, naabare = 0, []
    for bord, post in orphaned.items():
        m = re.match(r"([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)",
                     str(post.get("producer") or "").strip())
        if not m:
            continue  # posten navngiver ingen funktion; intet at maale
        maalt += 1
        producent = m.group(2)
        kaldes_af = _kaldes_af(kald, producent)
        if not kaldes_af:
            continue  # ingen kalder den: paastanden holder
        if post.get("path_reachable"):
            continue  # vejen er kendt naabar, og posten siger det
        naabare.append((bord, producent, kaldes_af))

    assert maalt >= 8, f"kun {maalt} orphaned-producere kunne maales"
    assert not naabare, (
        "disse poster staar som «ingen vej til en raekke», men deres producent "
        f"KALDES: {naabare}. Enten er klassifikationen foraeldet — eller vejen "
        "er naabar og posten skal saette `path_reachable: True` med en note der "
        "forklarer hvorfor der ikke desto mindre aldrig opstaar raekker."
    )


def test_naabarhedsvagten_KAN_fejle():
    """Mutationstest: en vagt der ikke kan fejle er dokumentation.

    Der indsaettes en post der paastaar `orphaned` om en funktion som
    beviseligt kaldes, og det verificeres at samme logik som ovenfor ville
    fange den. Uden dette trin er det en antagelse at vagten virker — og
    forgængeren var netop groen uden at maale noget.
    """
    import pathlib
    import re

    rod = pathlib.Path(__file__).resolve().parent.parent
    kald = _kald_grafen(rod)

    producent = "record_quota_observation"
    kaldes_af = _kaldes_af(kald, producent)
    assert kaldes_af, (
        f"{producent} kaldes ikke laengere — mutationstesten maa ikke bygge paa "
        "en kant der er forsvundet"
    )

    # Samme beslutning som vagten traeffer, paa en post UDEN undtagelsesflaget.
    falsk_post = {"status": "orphaned", "producer": f"x.{producent}"}
    m = re.match(r"([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)", falsk_post["producer"])
    assert m
    doemt = bool(_kaldes_af(kald, m.group(2))) and not falsk_post.get(
        "path_reachable")
    assert doemt, "mutationstesten fanger ikke en post der beviseligt er naabar"
