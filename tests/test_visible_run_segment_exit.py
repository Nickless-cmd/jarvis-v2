"""Kan vi ikke taelle kaeden, skal segmentet STANDSE — ikke fortsaette i blinde.

Opslaget af genoptagelses-kaeden laa foer inde i `visible_runs` med en tavs
`except Exception: _recovery_attempt = 0`. Nul betyder «foerste forsoeg», saa et
opslag der fejlede systematisk gav en tur der aldrig kunne naa sit loft. Og
fordi undtagelsen ikke blev logget, lignede det en helt almindelig afslutning.

Retningen er ikke en smagssag: at standse for tidligt giver et aerligt varsel
om at checkpointet er bevaret, og mennesket kan sige fortsaet. En uendelig
loekke koster penge og kan ikke opdages indefra.
"""
from __future__ import annotations

import logging

import pytest

from core.services import visible_run_segment_exit as vrse
from core.services.visible_terminal_policy import (
    TerminalEvidence,
    TerminalState,
    classify_terminal,
)


# ── Taelleren og dens fejl-retning ──────────────────────────────────────────

def test_taelleren_laeses_normalt(monkeypatch):
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", lambda sid: 2)
    assert vrse.kaede_nr_eller_loft("s1") == 2


def test_et_fejlende_opslag_giver_LOFTET_ikke_nul(monkeypatch, caplog):
    def sprang(_sid):
        raise OSError("journalen kunne ikke laeses")
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", sprang)
    with caplog.at_level(logging.WARNING):
        assert vrse.kaede_nr_eller_loft("s1") == vrse.GENOPTAGELSES_LOFT
    # Og den er ikke tavs: et opslag der fejler systematisk maa ikke ligne en
    # almindelig afslutning i loggen.
    assert "genoptagelses-kaeden" in caplog.text
    assert "s1" in caplog.text


def test_et_negativt_tal_bliver_ikke_negativt(monkeypatch):
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", lambda sid: -5)
    assert vrse.kaede_nr_eller_loft("s1") == 0


# ── Fejl-retningen skal faktisk STANDSE turen ───────────────────────────────

def test_fallbacken_naar_loftet_saa_politikken_stopper(monkeypatch):
    """Kernen, og grunden til at loftet sendes MED til afregningen: fallbacken
    og graensen maa ikke kunne drive fra hinanden."""
    fanget: dict = {}
    monkeypatch.setattr(vrse, "settle_segment_exit",
                        lambda **kw: fanget.update(kw) or "udfald")
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr",
                        lambda sid: (_ for _ in ()).throw(OSError("nede")))
    vrse.afgoer_segment_udfald(
        run_id="r1", session_id="s1", exit_reason="completed",
        forced_finalize=True)
    assert fanget["recovery_attempt"] == fanget["recovery_limit"]

    # Og med de tal faelder politikken faktisk dommen «stop».
    dom = classify_terminal(TerminalEvidence(
        exit_reason="completed", forced_finalize=True, incompletion_evidence=True,
        recovery_attempt=fanget["recovery_attempt"],
        recovery_limit=fanget["recovery_limit"]))
    assert dom.state is TerminalState.FAILED_TERMINAL
    assert dom.should_continue is False


# ── Exit-grunden maa ikke lyve ──────────────────────────────────────────────

@pytest.mark.parametrize("grund,afkortet,forventet", [
    ("completed", True, "completed-truncated"),
    ("completed", False, "completed"),
    ("budget-opbrugt", True, "budget-opbrugt"),
    ("", True, ""),
])
def test_afkortet_svar_retter_grunden(monkeypatch, grund, afkortet, forventet):
    fanget: dict = {}
    monkeypatch.setattr(vrse, "settle_segment_exit",
                        lambda **kw: fanget.update(kw) or "udfald")
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", lambda sid: 0)
    vrse.afgoer_segment_udfald(run_id="r1", session_id="s1",
                               exit_reason=grund, truncated=afkortet)
    assert fanget["exit_reason"] == forventet
    # Resumeet skal baere den RETTEDE grund, ikke den der loej.
    assert fanget["summary"] == forventet


def test_alle_felter_naar_frem_til_afregningen(monkeypatch):
    fanget: dict = {}
    monkeypatch.setattr(vrse, "settle_segment_exit",
                        lambda **kw: fanget.update(kw) or "udfald")
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", lambda sid: 1)
    vrse.afgoer_segment_udfald(
        run_id="r7", session_id="s7", exit_reason="completed",
        final_text="svaret", finish_reason="length",
        forced_finalize=True, pending_tool_intent=True, truncated=False)
    assert fanget["run_id"] == "r7"
    assert fanget["session_id"] == "s7"
    assert fanget["final_text"] == "svaret"
    assert fanget["finish_reason"] == "length"
    assert fanget["forced_finalize"] is True
    assert fanget["pending_tool_intent"] is True
    assert fanget["recovery_attempt"] == 1
