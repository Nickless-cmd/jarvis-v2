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
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", lambda sid, rid="": 2)
    assert vrse.kaede_nr_eller_loft("s1") == 2


def test_et_fejlende_opslag_giver_LOFTET_ikke_nul(monkeypatch, caplog):
    def sprang(_sid, _rid=""):
        raise OSError("journalen kunne ikke laeses")
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", sprang)
    with caplog.at_level(logging.WARNING):
        assert vrse.kaede_nr_eller_loft("s1") == vrse.GENOPTAGELSES_LOFT
    # Og den er ikke tavs: et opslag der fejler systematisk maa ikke ligne en
    # almindelig afslutning i loggen.
    assert "genoptagelses-kaeden" in caplog.text
    assert "s1" in caplog.text


def test_et_negativt_tal_bliver_ikke_negativt(monkeypatch):
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", lambda sid, rid="": -5)
    assert vrse.kaede_nr_eller_loft("s1") == 0


# ── Fejl-retningen skal faktisk STANDSE turen ───────────────────────────────

def test_fallbacken_naar_loftet_saa_politikken_stopper(monkeypatch):
    """Kernen, og grunden til at loftet sendes MED til afregningen: fallbacken
    og graensen maa ikke kunne drive fra hinanden."""
    fanget: dict = {}
    monkeypatch.setattr(vrse, "settle_segment_exit",
                        lambda **kw: fanget.update(kw) or "udfald")
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr",
                        lambda sid, rid="": (_ for _ in ()).throw(OSError("nede")))
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
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", lambda sid, rid="": 1)
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


# ── Kaeden skal faktisk FODRES, ikke bare have en kolonne ───────────────────
#
# `stamp_recovery_chain` skrev tre kolonner, men kaldestedet sendte kun
# `recovery_attempt`. `recovery_task_id` og `recovery_wake_kind` stod derfor
# tomme i alle 28.456 raekker: de saa ud som om de maalte noget (25/11-2026).
# Kolonner der aldrig fodres er den samme fejlform som et vaern uden kalder.

def _stempling_fanget(monkeypatch, post: dict | None):
    """Fang hvad der sendes til stemplingen, med en givet journalpost."""
    from core.runtime import db_visible
    fanget: dict = {}
    monkeypatch.setattr("core.services.in_flight_runs.get_record",
                        lambda ident: post)
    monkeypatch.setattr(db_visible, "stamp_recovery_chain",
                        lambda rid, **kw: fanget.update({"run_id": rid, **kw}) or True)
    monkeypatch.setattr(vrse, "settle_segment_exit", lambda **kw: "udfald")
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", lambda sid, rid="": 1)
    return fanget


def test_agent_vaekning_stempler_hvad_der_vaekkede(monkeypatch):
    """Uden `wake_kind` kunne ni ture ikke skelnes fra ni almindelige ture —
    det var praecis spoergsmaalet der ikke kunne besvares."""
    fanget = _stempling_fanget(monkeypatch, {
        "task_id": "agentwake-k1", "run_id": "r-nyt",
        "wake_kind": "agent_wait",
    })
    vrse.afgoer_segment_udfald(
        run_id="r-nyt", session_id="s1", exit_reason="completed")
    assert fanget["wake_kind"] == "agent_wait"
    # Leddet arvede en anden opgave end sin egen — det ER en kaede.
    assert fanget["recovery_task_id"] == "agentwake-k1"


def test_eget_task_id_beviser_ingen_kaede(monkeypatch):
    """En post hvis `task_id` er koerslens eget id er ikke et fortsat led.
    Skrev vi den ind, ville hver eneste almindelige koersel se ud som en
    genoptagelse."""
    fanget = _stempling_fanget(monkeypatch, {
        "task_id": "r-selv", "run_id": "r-selv", "wake_kind": "",
    })
    vrse.afgoer_segment_udfald(
        run_id="r-selv", session_id="s1", exit_reason="completed")
    assert fanget["recovery_task_id"] == ""
    assert fanget["wake_kind"] == ""


def test_ulaeselig_journal_giver_tomme_felter_ikke_gaet(monkeypatch, caplog):
    """En gaettet kaede er vaerre end ingen: den ville se ud som en maalt
    sammenhaeng. Og opslaget maa ikke vaeltе turen."""
    from core.runtime import db_visible
    fanget: dict = {}

    def sprang(_ident):
        raise OSError("journalen kunne ikke laeses")

    monkeypatch.setattr("core.services.in_flight_runs.get_record", sprang)
    monkeypatch.setattr(db_visible, "stamp_recovery_chain",
                        lambda rid, **kw: fanget.update(kw) or True)
    monkeypatch.setattr(vrse, "settle_segment_exit", lambda **kw: "udfald")
    monkeypatch.setattr("core.services.auto_continuation.kaede_nr", lambda sid, rid="": 1)
    with caplog.at_level(logging.WARNING):
        vrse.afgoer_segment_udfald(
            run_id="r9", session_id="s9", exit_reason="completed")
    assert fanget["recovery_task_id"] == ""
    assert fanget["wake_kind"] == ""
    # Turen blev stadig afregnet — og fejlen er ikke tavs.
    assert "journalposten" in caplog.text
