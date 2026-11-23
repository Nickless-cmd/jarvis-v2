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
