"""C3-grenen: forslag skal bygge på de mål der FAKTISK er aktive — og kun én gang.

MÅLT 29/10-2026: `_collect_active_goals` læste kun `autonomous_goals`, hvor 3.691
mål står `pending` og nul er `active`. Grenen kunne derfor ALDRIG fyre — samme
fejlform som sansningen havde, og som `_aktive_maal` blev skrevet for at lukke.

Da grenen blev koblet til den levende butik uden en gate, kaldte
`productive_idle` en LLM ved HVERT ledigt tick (2 mål × forslag, hvert 15.
minut = op til 192 kald i døgnet). Dedup'en i `_propose_skill_chains_in_idle`
sker EFTER kaldet, så den sparer lagring — ikke penge.

Gaten er derfor: et mål der allerede har et forslag bliver ikke foreslået igen.
Det gør omkostningen «ét kald pr. nyt aktivt mål» i stedet for «to kald hvert
kvarter i al evighed».
"""
from __future__ import annotations

from unittest.mock import patch

from core.services.heartbeat_phases import (
    _collect_active_goals,
    _propose_skill_chains_in_idle,
    clear_chain_proposals,
    get_chain_proposals,
)

MAAL = {"goal_id": "goal_test_1", "title": "Bevis pålidelighed over tid — gør mig til nogen"}


def setup_function() -> None:
    clear_chain_proposals()


def teardown_function() -> None:
    clear_chain_proposals()


def _tom_forslagsliste():
    return patch(
        "core.tools.skill_chain_propose_tool._exec_propose_skill_chain",
        return_value={
            "status": "ok",
            "plan": ["search_memory", "read_file"],
            "rationale": "test",
            "confidence": 0.8,
        },
    )


def test_collect_active_goals_laeser_langhorisont_butikken():
    """Det aktive mål bor i long_horizon_goals — grenen skal finde det der."""
    with patch(
        "core.services.autonomous_goals.list_goals", return_value=[]
    ), patch(
        "core.services.long_horizon_goals.list_active_goals", return_value=[MAAL]
    ):
        maal = _collect_active_goals()

    titler = [m.get("title") for m in maal]
    assert MAAL["title"] in titler, (
        "C3 læste ikke den butik der har aktive mål — grenen er død igen"
    )


def test_c3_foreslaar_for_maal_uden_forslag():
    """Første gang: der er et aktivt mål uden forslag, så LLM'en må kaldes."""
    with patch(
        "core.services.heartbeat_phases._collect_active_goals", return_value=[MAAL]
    ), _tom_forslagsliste() as fake:
        forslag = _propose_skill_chains_in_idle(max_goals=2)

    assert fake.call_count == 1
    assert len(forslag) == 1
    assert forslag[0]["goal_id"] == "goal_test_1"


def test_c3_kalder_ikke_igen_for_samme_maal():
    """Anden gang: målet har allerede et forslag — intet nyt LLM-kald.

    Det er hele omkostningsgaten. Uden den ville hvert ledigt tick kalde LLM'en
    igen for det samme mål, fordi dedup'en først sker bagefter.
    """
    with patch(
        "core.services.heartbeat_phases._collect_active_goals", return_value=[MAAL]
    ), _tom_forslagsliste() as fake:
        foerste = _propose_skill_chains_in_idle(max_goals=2)
        andet = _propose_skill_chains_in_idle(max_goals=2)

    assert len(foerste) == 1
    assert fake.call_count == 1, (
        f"LLM'en blev kaldt {fake.call_count} gange for det SAMME mål — "
        "gaten holder ikke, og hvert idle-tick koster penge"
    )
    assert andet == [], "andet kald skal være tomt: målet har allerede et forslag"
    assert len(get_chain_proposals()) == 1


def test_c3_foreslaar_for_nyt_maal_naar_det_dukker_op():
    """Gaten må ikke gøre grenen død: et NYT aktivt mål skal stadig foreslås."""
    nyt = {"goal_id": "goal_test_2", "title": "Et helt andet mål der også er aktivt"}

    with patch(
        "core.services.heartbeat_phases._collect_active_goals", return_value=[MAAL]
    ), _tom_forslagsliste() as fake:
        _propose_skill_chains_in_idle(max_goals=2)
        assert fake.call_count == 1

        with patch(
            "core.services.heartbeat_phases._collect_active_goals",
            return_value=[MAAL, nyt],
        ):
            forslag = _propose_skill_chains_in_idle(max_goals=2)

    assert fake.call_count == 2, "det nye mål skal have sit eget kald"
    assert [f["goal_id"] for f in forslag] == ["goal_test_2"]
