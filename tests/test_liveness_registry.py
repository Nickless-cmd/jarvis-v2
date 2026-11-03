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


def test_en_post_der_paastaar_ingen_skrivesti_skal_vaere_sand():
    """3/11-2026: `composer_jarvis_forslag`, `session_write_leases` og
    `user_flags` stod alle som orphaned med «INGEN skrivesti i kilden» — og
    alle tre havde en skriver, koblet paa efter 25/9-auditen. Klassifikationen
    var foraeldet, og intet fangede det, fordi registret er statisk.

    ⚠️ Graensen er vigtig: `orphaned` betyder IKKE «ingen skriver». Det betyder
    «skriveren findes, men har ingen live-kalder» — saa en INSERT i kilden er
    forventet og beviser intet. Det der kan afgoeres statisk er den haardeste
    form: en post der paastaar at der slet ikke findes en skrivefunktion.
    """
    import pathlib
    import re

    from core.services.liveness_registry import _REGISTRY

    rod = pathlib.Path(__file__).resolve().parent.parent
    insert_pat = re.compile(r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+([^\s(]+)", re.I)
    konst_pat = re.compile(
        r"^\s*([A-Z_][A-Z0-9_]*)\s*(?::\s*str\s*)?=\s*[\"']([a-z][a-z0-9_]*)[\"']",
        re.M,
    )

    # Tabeller skrives ofte gennem en konstant: `_TABEL = "x"` og derefter
    # `INSERT INTO {_TABEL}`. Den første version af denne vagt samlede hele
    # core/ til ÉN tekst og sammenlignede rå fund — saa den fandt `{_TABEL}`
    # og var blind for præcis den fil der startede undersøgelsen,
    # `db_composer_jarvis.py` (målt 3/11-2026). En vagt der ikke kan se den
    # fejl den blev bygget til at fange, er dokumentation forklædt som værn.
    inserts: set[str] = set()
    for p in (rod / "core").rglob("*.py"):
        if p.name == "liveness_registry.py":
            continue
        fil_tekst = p.read_text(encoding="utf-8", errors="ignore")
        konstanter = dict(konst_pat.findall(fil_tekst))
        for m in insert_pat.finditer(fil_tekst):
            navn = m.group(1).strip("`\"'")
            navn = re.sub(
                r"^\{(\w+)\}$",
                lambda x: konstanter.get(x.group(1), x.group(0)),
                navn,
            )
            inserts.add(navn)

    for bord, post in _REGISTRY.items():
        if "INGEN skrivesti" not in str(post.get("producer") or ""):
            continue
        ramte = [t for t in inserts if bord in t]
        assert not ramte, (
            f"{bord} staar som «INGEN skrivesti», men der findes en INSERT mod "
            f"{ramte}. Klassifikationen er foraeldet — find skriveren og dens "
            "kaldere, og afgoer om den er live, betinget eller reelt doed."
        )
