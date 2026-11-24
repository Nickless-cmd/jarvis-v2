"""Tests for relevans-gaten paa beslutninger (23/11-2026).

Gaten erstattede `ORDER BY priority DESC` som udvaelgelse af hvilke beslutninger
der injiceres i prompten. Maalt foer: med 138 aktive beslutninger vandt de fem
hoejeste prioriteter ALTID, uanset turen — beslutningen om forventning-og-
modbevisning (priority 90) laa nr. 5 og blev aldrig injiceret.

Testene maaler tre ting, og den tredje er den vigtigste:

1. At en relevant beslutning SLAAR en med hoejere priority.
2. At gaten kan AFVISE — returnere faerre end max_items eller slet ingen.
3. At den ikke vinder paa et enkelt almindeligt ord (ordopslag er ikke vurdering).
"""
from __future__ import annotations

import json

import pytest


def _beslutning(decision_id: str, directive: str, *, priority: int = 50, cue: str = "") -> dict:
    return {
        "decision_id": decision_id,
        "directive": directive,
        "trigger_cue": cue,
        "priority": priority,
        "status": "active",
        "adherence_score": None,
    }


@pytest.fixture()
def fake_beslutninger(monkeypatch):
    """Isoleret beslutnings-population — ingen DB, ingen netvaerk."""
    from core.services import behavioral_decisions as bd

    def _install(rows: list[dict]) -> None:
        monkeypatch.setattr(bd, "_db_list", lambda **kw: [dict(r) for r in rows])

    return _install


def test_relevant_beslutning_slaar_hoejere_priority(fake_beslutninger) -> None:
    """Kernen i gaten: relevans gaar forud for priority.

    Uden dette er gaten bare priority-loftet med et nyt navn.
    """
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning(
            "dec_hoej",
            "Undgaa altid at skrive til produktion uden backup",
            priority=99,
            cue="Naar jeg overvejer en destruktiv kommando",
        ),
        _beslutning(
            "dec_relevant",
            "Verificer at prompt-sektionen ikke bliver klippet af budgettet",
            priority=40,
            cue="Naar en prompt-sektion forsvinder eller bliver klippet",
        ),
    ])

    valgte = bd.select_relevant_decisions(
        max_items=1,
        context_text="min prompt-sektion bliver klippet af budgettet",
    )

    assert len(valgte) == 1
    assert valgte[0]["decision_id"] == "dec_relevant", (
        "den relevante beslutning skal slaa den med priority 99"
    )
    assert valgte[0]["_selection_basis"] == "relevance"


def test_gaten_kan_afvise_alt(fake_beslutninger) -> None:
    """En hilsen maa ikke vaeckke beslutninger.

    Maalt 23/11-2026 vakte «hej Bjorn hvordan gaar det» fire beslutninger, fordi
    «hvordan» stod i 4 af 138 og derfor fik hoej IDF. Spoergeord er nu stopord.
    """
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning("dec_a", "Verificer altid at mekanismen bliver kaldt", priority=90),
        _beslutning("dec_b", "Maal om betingelsen kan opfyldes", priority=85),
    ])

    valgte = bd.select_relevant_decisions(
        max_items=5, context_text="hej Bjorn hvordan gaar det"
    )

    assert valgte == [], "en hilsen skal give nul beslutninger, ikke fyldte pladser"


def test_enkelt_almindeligt_ord_er_ikke_nok(fake_beslutninger) -> None:
    """Et ordopslag er ikke en vurdering.

    Maalt: 11 af 138 beslutninger vandt paa ordet «tilstand» alene. Der kraeves
    nu to uafhaengige ord, medmindre det ene er saa sjaeldent at det identificerer
    sagen (IDF over _ENKELTORD_IDF).
    """
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning("dec_tilstand", "Rapporter tilstand korrekt", priority=90),
        _beslutning("dec_andet", "Noget helt andet om filer", priority=50),
    ])

    valgte = bd.select_relevant_decisions(
        max_items=5, context_text="hvad er din tilstand"
    )

    ids = [d["decision_id"] for d in valgte]
    assert "dec_tilstand" not in ids, (
        "ét almindeligt ord maa ikke baere en beslutning alene"
    )


def test_sjaeldent_fagord_kan_baere_alene(fake_beslutninger) -> None:
    """Den anden side: et ord der kun staar i én beslutning ER identificerende."""
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning(
            "dec_sjaelden",
            "Undersoeg hvorfor klippeloftet ikke fanger snittet",
            priority=40,
            cue="Naar klippeloftet fejler",
        ),
        _beslutning("dec_x", "Andet om filer og mapper", priority=90),
        _beslutning("dec_y", "Tredje om netvaerk og porte", priority=85),
    ])

    valgte = bd.select_relevant_decisions(
        max_items=5, context_text="klippeloftet fanger ikke"
    )

    ids = [d["decision_id"] for d in valgte]
    assert "dec_sjaelden" in ids, "et sjaeldent fagord skal kunne baere alene"


def test_uden_kontekst_falder_den_aabent_tilbage(fake_beslutninger) -> None:
    """Tom kontekst maa ikke forveksles med en vurdering.

    Gaten skal stadig virke i et heartbeat uden tur-signaler — men den skal SIGE
    at den faldt tilbage, saa en tom kontekst ikke laeses som «intet er relevant».
    """
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning("dec_hoej", "Hoej prioritet", priority=99),
        _beslutning("dec_lav", "Lav prioritet", priority=10),
    ])

    valgte = bd.select_relevant_decisions(max_items=5, context_text="")

    assert len(valgte) == 2
    assert all(d["_selection_basis"] == "priority-fallback-no-context" for d in valgte)
    assert valgte[0]["decision_id"] == "dec_hoej"


def test_hver_vurdering_baerer_sin_begrundelse(fake_beslutninger) -> None:
    """Valget skal kunne efterproeves, ikke troes."""
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning(
            "dec_a",
            "Verificer at prompt-sektionen ikke klippes",
            priority=50,
            cue="Naar prompt-sektionen klippes",
        ),
    ])

    valgte = bd.select_relevant_decisions(
        max_items=5, context_text="prompt-sektionen klippes igen"
    )

    assert valgte, "beslutningen burde vaere valgt"
    v = valgte[0]["_relevans"]
    assert v["hvorfor"], "en vurdering uden begrundelse kan ikke efterproeves"
    assert v["score"] > 0
    assert v["cue_hit"] or v["dir_hit"] or v["tool_hit"]


def test_maskinel_kontekst_uden_fagsignal_afvises(fake_beslutninger) -> None:
    """«Ingen kontekst» og «kontekst uden fagsignal» er TO forskellige svar.

    Heartbeat scorer ikke mod en brugerbesked, men mod `tool_intent` og
    `loop_runtime` — korte, maskinelle strenge som «idle active 2». Efter
    stopord-filteret staar der intet tilbage. Den gamle gren faldt dermed tilbage
    til priority og fyldte fem pladser — maalt de SAMME fem hver tick, hvilket er
    praecis den adfaerd gaten skulle afskaffe.
    """
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning(
            "dec_hoej",
            "Undgaa at skrive til produktion uden backup",
            priority=94,
            cue="Naar jeg overvejer en destruktiv kommando",
        ),
        _beslutning(
            "dec_ny",
            "Skriv regressionstesten foer fixet",
            priority=50,
            cue="Naar en fejl er rettet",
        ),
    ])

    uden = bd.select_relevant_decisions(max_items=5)
    assert len(uden) == 2
    assert uden[0]["_selection_basis"] == "priority-fallback-no-context"

    med = bd.select_relevant_decisions(max_items=5, context_text="idle active 2")
    assert med == [], "maskinel stoej uden fagsignal maa ikke fylde pladser via priority"


def test_strukturelt_token_er_ikke_et_fagsignal(fake_beslutninger) -> None:
    """«active» er et strukturelt token, ikke en sag.

    Maalt 24/11-2026 i heartbeat-stien: `active` stod i 1 af 138 beslutninger og
    fik derfor IDF 4,24 — nok til at passere enkeltords-reglen. Resultatet var at
    de samme to beslutninger (`active_dreams`, `bgActive`) blev valgt paa hver
    eneste kontekst. Samme fejlklasse som «hvordan» i en hilsen: sjaelden OG
    betydningsloes.
    """
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning(
            "dec_dream",
            "Vaelg aldrig et dream_id uden at tjekke active_dreams",
            priority=80,
        ),
        _beslutning("dec_irrelevant", "Ryd op i gamle logfiler", priority=40),
    ])

    valgte = bd.select_relevant_decisions(max_items=5, context_text="active 2")
    assert valgte == [], "et strukturelt token maa ikke baere en beslutning alene"


def test_sporet_baerer_hvilke_beslutninger_der_blev_valgt(fake_beslutninger, tmp_path, monkeypatch) -> None:
    """«valgt=4» er ikke efterproveligt — sporet skal baere HVILKE fire.

    Maalt 24/11-2026: foerste version af spoeret gemte kun antallet. En linje som
    `basis=relevance, valgt=4` kunne ikke afgoere om de fire var de rigtige, eller
    hvorfor de vandt. Uden id og score er spoeret et tælleapparat, ikke et bevis.
    """
    from core.services import behavioral_decisions as bd

    spor = tmp_path / "relevans_gate.jsonl"
    monkeypatch.setattr(bd, "_GATE_SPOR", spor)

    fake_beslutninger([
        _beslutning("dec_prompt", "Verificer at prompt-sektionen ikke klippes", priority=50,
                    cue="Naar prompt-sektionen klippes"),
        _beslutning("dec_irrelevant", "Ryd op i gamle logfiler", priority=90),
    ])

    valgte = bd.select_relevant_decisions(max_items=5, context_text="prompt-sektionen klippes igen")
    assert valgte, "beslutningen burde vaere valgt"

    linjer = [json.loads(ln) for ln in spor.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert linjer, "sporet skal skrive en linje"
    post = linjer[-1]
    assert post["basis"] == "relevance"
    assert post["valgte"], "sporet skal navngive de valgte beslutninger"
    ids = [v["id"] for v in post["valgte"]]
    assert "dec_prompt" in ids, f"den valgte beslutning mangler i spoeret: {ids}"
    assert all("score" in v and "hvorfor" in v for v in post["valgte"])


def test_telemetri_fejl_skrives_til_egen_fil(fake_beslutninger, tmp_path, monkeypatch) -> None:
    """En tavs telemetri-fejl maa ikke vaere uskelnelig fra «gaten blev ikke kaldt».

    Maalt 23/11-2026: fejlgrenen skrev til `logger.debug`, men `jarvis-runtime`
    skrev nul INFO-linjer til journalen overhovedet. En fejlende filskrivning
    forsvandt dermed sporloest. Nu skrives fejlen til sin egen fil, hvis
    eksistens ER svaret paa spoergsmaalet.
    """
    from core.services import behavioral_decisions as bd

    fejlfil = tmp_path / "relevans_gate_fejl.jsonl"
    # En sti der ikke kan aabnes som fil: en mappe.
    umulig = tmp_path / "er_en_mappe"
    umulig.mkdir()
    monkeypatch.setattr(bd, "_GATE_SPOR", umulig)
    monkeypatch.setattr(bd, "_GATE_SPOR_FEJL", fejlfil)

    fake_beslutninger([_beslutning("dec_a", "Verificer prompt-sektionen", priority=50)])

    bd.select_relevant_decisions(max_items=5, context_text="prompt-sektionen klippes")

    assert fejlfil.exists(), "en fejlet telemetri-skrivning skal efterlade et spor"
    post = json.loads(fejlfil.read_text(encoding="utf-8").splitlines()[-1])
    assert post["fejl"], "fejlposten skal navngive fejlen"


def test_priority_fallback_er_synlig_i_prompt_teksten(fake_beslutninger) -> None:
    """Fallback maa ikke ligne en relevansvurdering i den tekst modellen laeser.

    `_selection_basis` blev sat paa dict'en, men naaede aldrig prompt-linjen.
    Modellen kunne derfor ikke se forskel paa «valgt fordi den passede til turen»
    og «valgt fordi den var hoejest prioriteret».
    """
    from core.services import behavioral_decisions as bd

    fake_beslutninger([_beslutning("dec_hoej", "Hoej prioritet uden kontekst", priority=94)])

    linje = bd.format_active_decisions_for_heartbeat(max_items=5, context_text="")
    assert "priority" in linje.lower(), f"fallback skal meldes i teksten: {linje[:120]}"

    med_kontekst = bd.format_active_decisions_for_heartbeat(
        max_items=5, context_text="prompt-sektionen klippes"
    )
    if med_kontekst:
        assert "valgt paa priority" not in med_kontekst, "en relevansvurdering maa ikke meldes som fallback"


def test_en_filsti_er_ikke_et_fagsignal(fake_beslutninger) -> None:
    """Stier i konteksten maa ikke baere et valg — maalt i DRIFT, ikke i en test.

    Den foerste produktionslinje (21:17:39) valgte 5 af 137 paa ord fra
    `/tmp/pytest-of-bs/pytest-419/test_approved_sudo_exec_become0/workspaces/default/to`:
    9 af 15 tokens kom fra stien alene. Det er samme fejlklasse som «active» —
    et token der ikke baerer en sag, men som IDF'en alligevel giver vaegt fordi
    det er sjaeldent i beslutningspopulationen.

    Konteksten her er ordret den streng der stod i `relevans_gate.jsonl`.
    """
    from core.services.behavioral_decisions import _relevans_ord

    drift_ctx = (
        "sudo-exec-completed Approved bounded sudo exec blev udført for sudo "
        "chmod 600 /tmp/pytest-of-bs/pytest-419/test_approved_sudo_exec_become0/"
        "workspaces/default/to"
    )
    ord_ = _relevans_ord(drift_ctx)

    for stoej in ("pytest-of-bs", "become0", "workspaces", "default", "pytest-419"):
        assert stoej not in ord_, f"«{stoej}» er en del af en sti, ikke et signal: {sorted(ord_)}"

    # Ord uden for stien skal stadig vaere der — ellers fjerner vi signal med stoej.
    assert "chmod" in ord_ and "sudo" in ord_, f"aegte ord forsvandt: {sorted(ord_)}"


def test_en_beslutning_kan_ikke_vinde_paa_en_sti(fake_beslutninger) -> None:
    """Negativ gren paa stoej: en beslutning hvis ENESTE overlap er en stidel vinder ikke."""
    from core.services import behavioral_decisions as bd

    fake_beslutninger(
        [
            _beslutning(
                "dec_sti",
                "Koer pytest-of-bs i workspaces/default",
                priority=99,
                cue="Naar pytest-of-bs bliver oprettet",
            ),
            _beslutning(
                "dec_rigtig",
                "Verificer exec_command mod dens allowlist foer den koeres",
                priority=60,
                cue="Naar exec_command bliver koert",
            ),
        ]
    )

    valgte = bd.select_relevant_decisions(
        max_items=5,
        context_text="sudo chmod 600 /tmp/pytest-of-bs/pytest-419/workspaces/default/to",
    )
    ids = [d["decision_id"] for d in valgte]
    assert "dec_sti" not in ids, f"en sti maatte ikke baere et valg: {ids}"


def test_foraeldet_kontekst_er_ikke_en_relevansvurdering(fake_beslutninger) -> None:
    """En kontekst fra maj maa ikke rangere beslutninger som om den var nutid.

    MAALT I DRIFT 24/11-2026 over 74 ticks: `tool_intent.last_action_at` stod paa
    2026-05-15 — seks maaneder gammel — men kaldestedet sendte den ind som
    «turens kontekst». Gaten scorede derfor korrekt paa en situation der ikke
    laengere fandtes, og valgte de SAMME fem beslutninger med de SAMME scorer i
    hver tick (10:20, 10:35, 10:54, 11:11 — identiske). Det er praecis den adfaerd
    gaten skulle afskaffe, blot med en anden aarsag end priority.

    Gaten kan ikke selv vide hvor gammel en streng er — alderen skal FOELGE MED.
    """
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning("dec_hoej", "Hoej prioritet uden relation til turen", priority=94),
        _beslutning(
            "dec_relevant",
            "Verificer at prompt-sektionen ikke klippes",
            priority=40,
            cue="Naar prompt-sektionen klippes",
        ),
    ])

    seks_maaneder = 15_768_000

    foraeldet = bd.select_relevant_decisions(
        max_items=5,
        context_text="prompt-sektionen klippes",
        context_age_seconds=seks_maaneder,
    )
    assert foraeldet, "en foraeldet kontekst falder tilbage — den giver stadig beslutninger"
    assert all(d["_selection_basis"] == "priority-fallback-stale-context" for d in foraeldet), (
        "foraeldet kontekst skal meldes som fallback, ikke som relevans"
    )
    assert foraeldet[0]["decision_id"] == "dec_hoej", (
        "en foraeldet kontekst maa ikke rangere — den beskriver ikke turen"
    )

    linje = bd.format_active_decisions_for_heartbeat(
        max_items=5,
        context_text="prompt-sektionen klippes",
        context_age_seconds=seks_maaneder,
    )
    assert "foraeldet" in linje, f"prompten skal melde foraeldelsen: {linje[:160]}"
    assert "262800 min" in linje, f"alderen skal staa i klartekst: {linje[:160]}"

    frisk = bd.select_relevant_decisions(
        max_items=5,
        context_text="prompt-sektionen klippes",
        context_age_seconds=30,
    )
    assert frisk and frisk[0]["decision_id"] == "dec_relevant", (
        "en frisk kontekst skal stadig vurdere relevans"
    )
    assert frisk[0]["_selection_basis"] == "relevance"


def test_ord_i_directive_kan_ikke_baere_beslutningen_alene(fake_beslutninger) -> None:
    """Et ord i det lange `directive` er ikke en situationsbeskrivelse.

    MAALT I DRIFT: `dec_8e5784fcde71` slap igennem med score 0,10 udelukkende
    fordi «output» stod i dens directive — mens turens «output» var review af en
    sudo-kommando. `trigger_cue` er beslutningens SITUATION; `directive` er dens
    handling. Et ord der kun rammer handlingen maa ikke baere beslutningen alene.

    Populationen er med vilje stor nok til at ordet faar IDF over
    `_ENKELTORD_IDF` — saa den GAMLE regel faktisk ville have sluppet den igennem.
    Uden det ville testen vaere groen af den forkerte grund.
    """
    from core.services import behavioral_decisions as bd

    rows = [
        _beslutning(
            "dec_kun_directive",
            "Undersoeg effekt af formlen i regnearket",
            priority=99,
            cue="Naar jeg regner paa tal",
        )
    ]
    for i in range(60):
        rows.append(_beslutning(f"dec_fyld_{i}", f"Fyldebeslutning {i} om emne{i}x", priority=10))

    fake_beslutninger(rows)

    valgte = bd.select_relevant_decisions(
        max_items=5,
        context_text="review af effekt foer mutation",
    )

    ids = [d["decision_id"] for d in valgte]
    assert "dec_kun_directive" not in ids, (
        f"et ord der kun staar i directive maa ikke baere beslutningen: {ids}"
    )


def test_sporet_kan_genskabe_sit_eget_valg(fake_beslutninger, tmp_path, monkeypatch) -> None:
    """Et spor der ikke kan reproducere sit eget valg er ikke et spor.

    Maalt 24/11-2026 (tredje gang samme fejlform): spoerets `ctx` blev klippet
    til 160, saa 400 tegn — og begge gange forsvandt praecis de ord der afgjorde
    valget. `loop_runtime.items[].title` ligger SIDST i heartbeat-konteksten, saa
    et snit fjernede de aabne loops der bar valget. Resultatet var en driftslinje
    hvis `hvorfor`-strenge pegede paa ord der ikke fandtes i dens egen `ctx`.
    """
    from core.services import behavioral_decisions as bd

    spor = tmp_path / "relevans_gate.jsonl"
    monkeypatch.setattr(bd, "_GATE_SPOR", spor)

    fake_beslutninger([
        _beslutning("dec_prompt", "Verificer at prompt-sektionen ikke klippes", priority=50,
                    cue="Naar prompt-sektionen klippes"),
        _beslutning("dec_loop", "Folg signalet hele vejen i den koerende proces", priority=40,
                    cue="Naar jeg skal afgoere om en koerende proces har aendringen inde"),
    ])

    # Loop-titlen ligger EFTER tegn 400 — praecis som i den aegte heartbeat-kontekst.
    ctx = ("inspect-working-tree main " + ("udfyldning " * 40)
           + "Folg signalet hele vejen ind i prompten i den koerende proces")
    assert len(ctx) > 400, "testen skal bruge en kontekst der er laengere end det gamle snit"

    foerste = bd.select_relevant_decisions(max_items=5, context_text=ctx)
    post = json.loads(spor.read_text(encoding="utf-8").splitlines()[-1])

    assert post["ctx_len"] == len(ctx), (
        f"ctx_len skal vaere den fulde laengde ({len(ctx)}), var {post['ctx_len']}"
    )
    assert post["ctx"] == ctx, "spoeret maa ikke klippe konteksten"

    # Det afgoerende: valget skal kunne genskabes UDELUKKENDE fra den loggede linje.
    genskabt = bd.select_relevant_decisions(max_items=5, context_text=post["ctx"])
    assert [d.get("decision_id") for d in foerste] == [d.get("decision_id") for d in genskabt], (
        "valget kan ikke genskabes fra spoeret — saa er spoeret ikke et bevis"
    )


def test_sporet_logger_hele_ord_saettet(fake_beslutninger, tmp_path, monkeypatch) -> None:
    """`ord` blev klippet til 12 — og de 12 var de alfabetisk foerste.

    24/11-2026 (maalt i DRIFT): heartbeat-konteksten har 82 betydningsbaerende
    ord, men spoeret skrev `[:12]`. Det var fjerde gang i samme fil inden for en
    time at et vilkaarligt snit skjulte det afgoerende — og netop det snit fik
    mig til at laese tre forskellige testkald som «gaten der afviser», fordi de
    ord der adskilte dem laa uden for snittet.
    """
    from core.services import behavioral_decisions as bd

    spor = tmp_path / "relevans_gate.jsonl"
    monkeypatch.setattr(bd, "_GATE_SPOR", spor)

    fake_beslutninger([
        _beslutning("dec_prompt", "Verificer at prompt-sektionen ikke klippes", priority=50,
                    cue="Naar prompt-sektionen klippes"),
    ])

    # Ordene spaender over hele alfabetet, saa et alfabetisk snit bliver synligt.
    ctx = " ".join(["aalborg", "betingelse", "chokolade", "dokument", "egentlig",
                    "formaal", "gaeste", "historik", "indhold", "journal",
                    "kategori", "loesning", "maaling", "nyhed", "omfang",
                    "periode", "relevans", "signal", "tilstand", "undersoeg"])

    bd.select_relevant_decisions(max_items=5, context_text=ctx)
    post = json.loads(spor.read_text(encoding="utf-8").splitlines()[-1])

    fuldt = bd._relevans_ord(ctx)
    assert post["ord_antal"] == len(fuldt), (
        f"ord_antal skal vaere det fulde saet ({len(fuldt)}), var {post['ord_antal']}"
    )
    assert set(post["ord"]) == fuldt, "spoeret maa ikke klippe ord-saettet"
    # Vagt mod netop den alfabetiske form: ord fra slutningen af alfabetet skal med.
    assert any(o.startswith("u") for o in post["ord"]), (
        "ord fra slutningen af alfabetet mangler — spoeret er klippet alfabetisk"
    )


def test_straffen_for_laengde_er_sublineaer() -> None:
    """Fire gange saa mange ord maa koste 2x, ikke 4x.

    Maalt 24/11-2026 i DRIFT: med `score / maal` tabte en praecis beslutning til
    en kort, udelukkende fordi den var laengere at beskrive — `bekraeftet, file,
    main` (maal 29) slog en 4-ords match (maal 34) med 1,239 mod 0,642, selv om
    den ramte faerre ord. sqrt(maal) goer straffen sublineaer.

    Testen maaler FORHOLDET mellem to beslutninger med samme raa score, saa den
    ikke laaser sig til en bestemt population. Under lineaer normalisering er
    forholdet 4,0; under sqrt er det 2,0.
    """
    from core.services import behavioral_decisions as bd

    ctx = "relevans signal"
    kort = bd.score_decision_relevance(
        {"directive": "", "trigger_cue": "relevans signal"}, context_text=ctx
    )
    lang = bd.score_decision_relevance(
        {
            "directive": "chokolade dokument journal kategori periode omfang",
            "trigger_cue": "relevans signal",
        },
        context_text=ctx,
    )

    assert kort["raa_score"] == lang["raa_score"], (
        "forudsaetningen er at de to har SAMME raa score — ellers maaler "
        f"testen ikke normaliseringen (fik {kort['raa_score']} og {lang['raa_score']})"
    )
    forhold = kort["score"] / lang["score"]
    assert 1.9 <= forhold <= 2.1, (
        f"forventet 2,0 (sqrt-normalisering), fik {forhold:.2f} — "
        "4,0 betyder at straffen er lineaer igen, og praecise beslutninger taber"
    )


def test_gulvet_afviser_en_svag_match_paa_den_nye_skala(fake_beslutninger) -> None:
    """Den negative gren skal stadig virke efter skalaen flyttede.

    24/11-2026: normaliseringen blev sqrt(maal), saa scorerne gik fra 0,06-1,7
    til 0,3-9,3. Gulvet blev maalt frem til 0,32 for at afvise praecis det samme
    saet — men en flyttet skala kan goere gulvet tandloest uden at nogen test
    markerer det. Derfor maales der paa den nye skala, med en sag der rammer TO
    ord og derfor ville slippe gennem to-ord-reglen.
    """
    from core.services import behavioral_decisions as bd

    fyld = " ".join(f"fyldord{i}" for i in range(38))
    svag_directive = f"relevans signal {fyld}"
    fake_beslutninger([
        _beslutning("dec_svag", svag_directive),
        _beslutning("dec_staerk", "noter hvad der blev maalt", cue="relevans signal"),
    ])

    ctx = "relevans signal"
    svag = bd.score_decision_relevance(
        {"directive": svag_directive, "trigger_cue": ""}, context_text=ctx
    )
    assert len(svag["dir_hit"]) == 2, (
        "sagen skal ramme to ord — ellers afviser to-ord-reglen den, og testen "
        f"maaler ikke gulvet (fik {svag['dir_hit']})"
    )
    assert svag["score"] < bd._RELEVANS_GULV, (
        f"den svage sag skal ligge UNDER gulvet, var {svag['score']}"
    )

    valgte = bd.select_relevant_decisions(max_items=5, context_text=ctx)
    assert [d["decision_id"] for d in valgte] == ["dec_staerk"], (
        "gulvet skal afvise den svage sag og lade den staerke passere"
    )


def test_strukturelle_tokens_kan_ikke_baere_beviset(fake_beslutninger) -> None:
    """To maskin-tokens er to ord men NUL signaler.

    24/11-2026 (maalt i DRIFT, 16 heartbeat-ticks): `dec_f1047a72079f` ramte
    UDELUKKENDE `file` + `memory` — fra «recent governed file writes» og
    «Memory Promotions has 1560 proposed items» — og scorede 4,31, altsaa som en
    staerk sag. Begge tokens staar i HVER heartbeat-kontekst og kan derfor ikke
    skelne en tur fra en anden. En vaegt alene kan ikke afvise dem: en ren
    strukturel match scorer 0,647 selv ved faktor 0,15, altsaa over gulvet 0,32.
    Vaernet skal derfor sidde i beviskravet.
    """
    from core.services import behavioral_decisions as bd

    fake_beslutninger([
        _beslutning("dec_kun_maskin", "file memory"),
        _beslutning("dec_fag", "noter hvad der blev maalt", cue="relevans gaten"),
    ])

    valgte = bd.select_relevant_decisions(
        max_items=5,
        context_text="recent governed file writes exist memory promotions relevans gaten",
    )
    ids = [d["decision_id"] for d in valgte]
    assert "dec_kun_maskin" not in ids, (
        "en sag hvis ENESTE hit er strukturelle tokens maa ikke vaelges — "
        "ellers er beviskravet et ordopslag"
    )
    assert ids == ["dec_fag"]


def test_strukturelt_token_vejer_mindre_end_fagord() -> None:
    """Samme form, samme kontekst — kun ordets klasse afgoer vaegten."""
    from core.services import behavioral_decisions as bd

    maskin = bd.score_decision_relevance(
        {"directive": "file", "trigger_cue": ""}, context_text="file"
    )
    fag = bd.score_decision_relevance(
        {"directive": "gaten", "trigger_cue": ""}, context_text="gaten"
    )
    # Begge rammer praecis ét ord, saa forskellen i raa_score ER vaegten:
    # det strukturelle ord bidrager med 1 x _STRUKTUREL_VAEGT, fagordet med 1 x 1.
    assert maskin["raa_score"] == round(bd._STRUKTUREL_VAEGT, 4), (
        "det strukturelle ords raa bidrag skal vaere praecis vaegten — "
        f"fik {maskin['raa_score']}"
    )
    assert fag["raa_score"] == 1.0, f"fagordet skal bidrage fuldt — fik {fag['raa_score']}"
    forhold = fag["score"] / maskin["score"]
    assert abs(forhold - 1 / bd._STRUKTUREL_VAEGT) < 0.01, (
        f"forventet forhold {1 / bd._STRUKTUREL_VAEGT:.2f}, fik {forhold:.2f} — "
        "1,0 betyder at strukturelle tokens ikke laengere vejes lavere"
    )


def test_taellere_er_strukturelle_men_tilstande_er_fagord() -> None:
    """Skellet er maalt, ikke smag: tællere og identitet vs. tilstandsbeskrivelser.

    24/11-2026: foerste version havde `signal`/`pressure`/`initiative` med, og
    det fik en eksisterende test til at fejle med rette. «private signal pressure
    is high» er INFORMATION om turen — en beslutning om signal-pres ER relevant
    naar presset er hoejt. Det er taellerne («has 1560 proposed items») og
    identiteten («main», «inspect-working-tree») der ikke baerer en sag.
    """
    from core.services import behavioral_decisions as bd

    for taeller in ("file", "memory", "main", "scheduled", "heartbeat", "proposed"):
        assert taeller in bd._STRUKTURELLE_ORD, f"{taeller} er en taeller/identitet"
    for tilstand in ("signal", "pressure", "proces", "relevans", "gaten", "prompten"):
        assert tilstand not in bd._STRUKTURELLE_ORD, (
            f"{tilstand} beskriver turen og maa ikke vaere strukturel"
        )
