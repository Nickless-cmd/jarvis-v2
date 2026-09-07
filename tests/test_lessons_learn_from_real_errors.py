"""Læringen skal fange ægte fejl — ikke at Bjørn trykkede stop.

Målt 7/9-2026: `lessons` havde **4 rækker efter 17.609 runs**, og
`evidence_count` stod på 1 for alle fire. Upserten er korrekt (den lægger til
ved match), og `record_episode` i samme funktion havde kørt 1.936 gange — så
funktionen kørte fint. Betingelsen var bare aldrig sand.

To ting var galt:

1. `error_text` kom fra `_final_run_error`, som kun sættes ved
   brugerafbrydelse og interruption. Afbrydelser er langt de hyppigste, så
   læringen så stort set kun «brugeren stoppede».
2. De 250 runs der faktisk FEJLEDE satte deres fejl på visible_runs.py:5617 —
   **efter** læringskaldet på 5045. De nåede den aldrig.
"""

from __future__ import annotations

import pytest

from core.services.visible_runs_learning_signals import er_brugerafbrydelse


@pytest.mark.parametrize("tekst", [
    "user-cancelled-during-agentic-loop",
    "USER-CANCELLED",
    "cancelled-by-user",
    "run-abandoned-before-finalization:CancelledError",
    "client-disconnected",
])
def test_afbrydelser_er_ikke_lektier(tekst):
    """Der er intet at lære af at han trykkede stop.

    Og de druknede den håndfuld ægte fejl der var noget værd: den ENE
    tool_error-lektie der fandtes var en provider-timeout, og den stod som
    `rejected`.
    """
    assert er_brugerafbrydelse(tekst) is True


@pytest.mark.parametrize("tekst", [
    "provider-round-timeout: timed out waiting for provider stream item",
    "KeyError: 'session_id'",
    "bridge_not_connected",
    "unexpected-run-error",
])
def test_aegte_fejl_taeller(tekst):
    assert er_brugerafbrydelse(tekst) is False


def test_tom_fejl_er_ikke_en_afbrydelse():
    """Tom betyder «ingen fejl», ikke «afbrudt» — og skal ikke skjule noget."""
    assert er_brugerafbrydelse("") is False
    assert er_brugerafbrydelse(None) is False


def test_writeren_springer_afbrydelser_over(monkeypatch):
    """Selve koblingen, ikke bare hjælperen."""
    import core.services.visible_runs_learning_signals as LS

    skrevet: list[str] = []
    monkeypatch.setattr(
        "core.services.lessons.record_tool_error",
        lambda **kw: skrevet.append(kw.get("error_text", "")),
    )
    monkeypatch.setattr(LS, "record_episode", lambda **kw: None, raising=False)

    class _Run:
        run_id = "r1"
        session_id = "s1"
        user_message = "hej"

    LS.record_visible_run_learning_signals(
        run_ref=_Run(), collected_native_tool_calls=[{"name": "bash"}],
        outcome_status="interrupted",
        outcome_error="user-cancelled-during-agentic-loop",
        followup_text="", output_tokens=0,
    )
    assert skrevet == [], "en brugerafbrydelse blev til en lektie"


def test_den_ydre_fejlhandler_laerer_af_run_fejl():
    """De 250 «failed»-runs skal naa laeringen.

    De saetter deres fejl EFTER laeringskaldet, saa der er nu et kald i den
    ydre fejlhandler. Testen laeser kilden, fordi stien kun rammes af en
    uhaandteret undtagelse midt i et rigtigt run.
    """
    import pathlib

    kilde = (pathlib.Path(__file__).resolve().parents[1]
             / "core" / "services" / "visible_runs.py").read_text(encoding="utf-8")
    i = kilde.index('set_last_visible_run_outcome(run, status="failed", error=_outer_error)')
    vindue = kilde[i:i + 900]
    assert "record_tool_error" in vindue, "den ydre fejlhandler laerer ikke af fejlen"
    assert "er_brugerafbrydelse" in vindue, "den filtrerer ikke afbrydelser fra"
