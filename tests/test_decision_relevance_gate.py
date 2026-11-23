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
