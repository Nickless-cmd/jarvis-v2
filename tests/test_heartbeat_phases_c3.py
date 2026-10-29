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


# ── Grenen skal ligge hvor betingelsen OPSTÅR ──────────────────────────────
#
# MÅLT 29/10-2026, efter at målene blev synlige for sansningen: `productive_idle`
# fyrede 3-4 gange i timen i et helt døgn og stoppede HELT kl. 19 — samme time
# som fixet trådte i kraft. Årsagen er strukturel: `active_goals` er nu altid
# ikke-tom, så `_identify_priorities` tilføjer `advance_goals` hver gang, og
# `if priorities:` i `act_phase` vinder altid over `productive_idle`.
#
# C3-grenen lå i `productive_idle` og var derfor uopnåelig — samme fejlform som
# den oprindeligt havde. Den ligger nu i `advance_goals`-vejen.


def _stille_omgivelser():
    """Ingen streaming, ingen aktiv bruger — så `act_phase` dispatcher ticken."""
    return (
        patch("core.services.visible_stream_gate.visible_streaming", return_value=False),
        patch("core.services.heartbeat_phases._user_active_recently", return_value=False),
        patch("core.services.heartbeat_phases._inner_tick_during_chat_enabled", return_value=True),
    )


def test_c3_kaldes_i_advance_goals_grenen():
    """Prioriteten `advance_goals` er den vej der FAKTISK tages — grenen skal ligge der."""
    from core.services.heartbeat_phases import act_phase

    a, b, c = _stille_omgivelser()
    with a, b, c, patch(
        "core.services.heartbeat_phases._propose_skill_chains_in_idle"
    ) as forslag, patch(
        "core.services.heartbeat_runtime.run_heartbeat_tick"
    ) as tick:
        tick.return_value = type("R", (), {"status": "ok"})()
        resultat = act_phase(
            signals={"active_goals": [MAAL]},
            reflection={"activity_level": "normal", "priorities": ["advance_goals"]},
        )

    assert forslag.call_count == 1, (
        "C3 kaldes ikke i advance_goals-vejen — så er grenen død igen, fordi "
        "productive_idle aldrig indtræffer når der findes et aktivt mål"
    )
    assert resultat.get("kind") == "tick_dispatched"


def test_c3_kaldes_ikke_uden_advance_goals():
    """En prioritet uden aktive mål skal ikke trække et LLM-kald ind i ticken."""
    from core.services.heartbeat_phases import act_phase

    a, b, c = _stille_omgivelser()
    with a, b, c, patch(
        "core.services.heartbeat_phases._propose_skill_chains_in_idle"
    ) as forslag, patch(
        "core.services.heartbeat_runtime.run_heartbeat_tick"
    ) as tick:
        tick.return_value = type("R", (), {"status": "ok"})()
        act_phase(
            signals={},
            reflection={"activity_level": "normal", "priorities": ["compact_context"]},
        )

    assert forslag.call_count == 0
