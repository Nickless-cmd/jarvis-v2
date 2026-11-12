"""Continuation må ikke starte oven i et run der allerede kører.

12/11-2026: Bjørn målte to ture der startede lige efter hinanden, og den
anden arvede ikke samtalens fulde adgang. Årsagen var `_maybe_trigger_continuation`:
den startede et nyt run uden at gå gennem `reserve_background_start`, så intet
værn så at den forrige kørsel lige var slut — og intet samlede dem.

Testen rammer den ÆGTE søm: den kalder `_maybe_trigger_continuation` med en
tekst der matcher continuation-mønstret, og observerer om
`start_autonomous_run` bliver kaldt når reservationen afviser.
"""
from __future__ import annotations

import time

import pytest


@pytest.fixture
def continuation_setup(monkeypatch):
    """Byg et run + en tekst der udløser continuation, uden at starte noget."""
    from core.services import visible_runs_memory as vrm

    startet: list[dict] = []

    class _Run:
        autonomous = False
        session_id = "chat-test-continuation"
        run_id = "visible-testcontinuation"

    # Cooldown og intent-detektion er ikke det vi måler — de skal bare slippe.
    import core.services.unfinished_intent as ui

    monkeypatch.setattr(ui, "is_in_cooldown", lambda _sid: False)
    monkeypatch.setattr(ui, "mark_triggered", lambda _sid: None)

    class _Intent:
        pattern = "jeg-læser"
        matched_text = "Jeg læser filen"

    monkeypatch.setattr(ui, "detect_unfinished_intent", lambda _t: _Intent())

    # Ingen aktiv kørsel i samtalen — ellers afbryder den tidlige guard.
    import core.services.visible_runs as vr

    monkeypatch.setattr(
        vr, "_get_active_visible_run_state", lambda: None
    )

    # Fang starteren i stedet for at starte et rigtigt run.
    monkeypatch.setattr(
        vrm._vr,
        "start_autonomous_run",
        lambda message, **kw: startet.append({"message": message, **kw}) or True,
    )

    # Ingen 5-sekunders ventetid i testen.
    monkeypatch.setattr(vrm, "_CONTINUATION_DELAY_SECONDS", 0)

    return vrm, _Run(), startet


def _kør_og_vent(vrm, run, tekst: str) -> None:
    vrm._maybe_trigger_continuation(run, tekst)
    # _delayed_spawn kører i en daemon-tråd; vent til den har haft tid.
    for _ in range(50):
        time.sleep(0.01)


def test_continuation_afvises_naar_et_run_er_aktivt(continuation_setup, monkeypatch):
    """Reservationen afviser → continuation må IKKE starte et run."""
    vrm, run, startet = continuation_setup

    import core.services.background_start_reservation as bsr

    class _Afvist:
        acquired = False
        reason = "shared-active:visible-abc"

    from contextlib import contextmanager

    @contextmanager
    def _reserver(_sid):
        yield _Afvist()

    monkeypatch.setattr(bsr, "reserve_background_start", _reserver)

    _kør_og_vent(vrm, run, "Jeg læser filen nu og vender tilbage.")

    assert startet == [], (
        "continuation startede et run selv om reservationen afviste — "
        "så lander to ture oven i hinanden igen"
    )


def test_continuation_koerer_naar_reservationen_er_ledig(continuation_setup, monkeypatch):
    """Reservationen giver grønt → continuation skal starte, med tilladelsen med."""
    vrm, run, startet = continuation_setup

    import core.services.background_start_reservation as bsr

    class _Ledig:
        acquired = True
        reason = ""

    from contextlib import contextmanager

    @contextmanager
    def _reserver(_sid):
        yield _Ledig()

    monkeypatch.setattr(bsr, "reserve_background_start", _reserver)

    _kør_og_vent(vrm, run, "Jeg læser filen nu og vender tilbage.")

    assert len(startet) == 1, "continuation startede ikke trods ledig reservation"
    assert startet[0]["session_id"] == run.session_id
    assert startet[0]["origin"] == "continuation"
    # Tilladelsen skal følge samtalen — ellers rejser runnet godkendelseskort
    # midt i en tur brugeren har sat til fuld adgang.
    assert startet[0]["permission_session"] == run.session_id


def test_reservationen_bruges_overhovedet(continuation_setup, monkeypatch):
    """Sensitivitet: kaldes reserve_background_start overhovedet?

    Uden denne kan de to tests ovenfor bestå af den forkerte grund — fx hvis
    continuation aldrig nåede frem til starteren.
    """
    vrm, run, startet = continuation_setup

    import core.services.background_start_reservation as bsr

    kaldt: list[str] = []

    class _Ledig:
        acquired = True
        reason = ""

    from contextlib import contextmanager

    @contextmanager
    def _reserver(sid):
        kaldt.append(sid)
        yield _Ledig()

    monkeypatch.setattr(bsr, "reserve_background_start", _reserver)

    _kør_og_vent(vrm, run, "Jeg læser filen nu og vender tilbage.")

    assert kaldt == [run.session_id], (
        "continuation gik uden om reserve_background_start — "
        "så er overlap-værnet ikke koblet på"
    )
