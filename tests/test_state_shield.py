"""Ingen test må skrive i den ægte ~/.jarvis-v2/state/*.json.

Databasen har haft sit værn længe. JSON-state havde intet, og det blev dyrt
17/9-2026: `in_flight_runs.json` i produktionen stod fuld af test-fikstur
(`visible-cap-*`, `session-smoke`, `visible-loop-not-blocked`), fordi enhver
test der kaldte `mark_started` skrev direkte i den ægte fil.

Så længe journalen kun blev LÆST var det rod. Med den varige genoptagelse er
den en KØ: dispatcheren tog to fikstur-poster ved næste genstart og kørte dem
som ægte synlige ture med beskeden «hej» — den ene på den betalte lane.
Testdata blev til rigtige kald.

Testen her er derfor ikke en stil-regel. Den er værnet mod at det sker igen.
"""
from __future__ import annotations

from pathlib import Path

from core.runtime import state_store
from core.services import in_flight_runs


def _aegte_state() -> Path:
    from core.runtime.config import STATE_DIR
    return Path(STATE_DIR)


def test_state_store_peger_IKKE_paa_den_aegte_mappe():
    assert Path(state_store._STATE_DIR) != _aegte_state()


def test_en_journal_post_lander_i_skjoldet_og_ikke_i_produktionen():
    """Den konkrete vej fikstur-posterne kom ind ad."""
    in_flight_runs.mark_started(run_id="visible-shield-proeve", session_id="s-shield",
                                user_message="hej")
    skrevet = Path(state_store._STATE_DIR) / "in_flight_runs.json"
    assert skrevet.is_file(), "posten blev slet ikke skrevet"
    assert "visible-shield-proeve" in skrevet.read_text(encoding="utf-8")

    aegte = _aegte_state() / "in_flight_runs.json"
    if aegte.is_file():
        assert "visible-shield-proeve" not in aegte.read_text(encoding="utf-8")
