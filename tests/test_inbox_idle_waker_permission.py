"""Vækkerens kald skal passe til starterens signatur — og bære tilladelsen.

12/11-2026: `inbox_idle_waker._start_run` sendte `permission_session=` til
`start_autonomous_run`, som ikke havde parameteren. Hvert eneste
indbakke-vækning kastede derfor `TypeError`, blev fanget som «kunne ikke
starte run», og posten blev rullet tilbage og ventede for evigt — hele
vækningsvejen var død i to dage uden at en enkelt test så det.

Hvorfor testene ikke så det: `tests/test_inbox_idle_waker.py` patcher
`_start_run` SELV i hver eneste test, så det indre kald aldrig blev prøvet.
En mock på den brækkede søm kan ikke se fejlen.

Disse tests binder producentens faktiske argumenter mod forbrugerens
virkelige signatur — og kræver at tilladelsen følger med hele vejen.
"""
from __future__ import annotations

import inspect
from contextlib import contextmanager
from types import SimpleNamespace

import pytest


def _recorder(spor: dict):
    """Starter-attrap der fanger argumenterne i stedet for at starte et run."""

    def _start(*args, **kwargs):
        spor["args"] = args
        spor["kwargs"] = kwargs
        return True

    return _start


@contextmanager
def _reservation(session_id: str):
    yield SimpleNamespace(acquired=True, reason="")


@pytest.fixture
def vaekker(monkeypatch):
    """Vækkeren med en attrap for starteren og for reservationen."""
    from core.services import inbox_idle_waker as w
    from core.services import visible_autonomous_run as var

    spor: dict = {}
    original = var.start_autonomous_run
    monkeypatch.setattr(var, "start_autonomous_run", _recorder(spor))
    monkeypatch.setattr(
        "core.services.background_start_reservation.reserve_background_start",
        _reservation,
    )
    return w, original, spor


def test_vaekkerens_kald_passer_til_starterens_signatur(vaekker):
    """Den præcise fejlform: et ukendt nøgleord kaster TypeError ved kaldet.

    Testen kalder den RIGTIGE `_start_run`, fanger hvad den sender, og binder
    det mod den RIGTIGE signatur. Det er bindingen der fejlede i drift.
    """
    w, original, spor = vaekker

    assert w._start_run(
        "GØR DET",
        session_id="chat-1",
        user_id="",
        task_id="",
        permission_session="chat-1",
        origin="inbox",
    ) is True

    # Ingen TypeError → argumenterne binder. Det er hele pointen.
    sig = inspect.signature(original)
    sig.bind(*spor["args"], **spor["kwargs"])

    # BEVIS FOR AT TESTEN BIDER: fjernes parameteren igen (som den var i drift
    # indtil i dag), SKAL bindingen kaste. Ellers måler testen ingenting.
    uden = sig.replace(
        parameters=[p for p in sig.parameters.values() if p.name != "permission_session"]
    )
    with pytest.raises(TypeError):
        uden.bind(*spor["args"], **spor["kwargs"])


def test_tilladelsessamtalen_naar_starteren(vaekker):
    """Postens `permission_session` må ikke tabe på vejen.

    Tabte den, faldt runnet tilbage til silo-niveauet og rejste et
    godkendelses-kort midt i et run brugeren havde sat til fuld adgang.
    """
    w, _original, spor = vaekker

    w._start_run(
        "GØR DET",
        session_id="auto-inbox-20261112",
        user_id="",
        permission_session="chat-1",
        origin="inbox",
    )

    assert spor["kwargs"]["permission_session"] == "chat-1"
    assert spor["kwargs"]["session_id"] == "auto-inbox-20261112"


def test_continuation_baerer_samtalens_tilladelse(monkeypatch):
    """Continuation er en fortsættelse af brugerens egen tur.

    Uden `permission_session` læste runnet et silo-niveau i stedet for det
    niveau samtalen faktisk stod på.
    """
    from core.services import visible_runs_memory as vrm
    from core.services import visible_autonomous_run as var

    spor: dict = {}
    monkeypatch.setattr(var, "start_autonomous_run", _recorder(spor))
    monkeypatch.setattr(vrm, "_CONTINUATION_DELAY_SECONDS", 0.0)

    # Ingen cooldown fra en tidligere test i samme proces.
    cooldown = getattr(vrm, "_LAST_CONTINUATION", None)
    if isinstance(cooldown, dict):
        cooldown.clear()

    monkeypatch.setattr(
        "core.services.unfinished_intent.detect_unfinished_intent",
        lambda _tekst: SimpleNamespace(pattern="jeg-laeser", matched_text="Jeg læser"),
    )
    monkeypatch.setattr(
        "core.services.visible_runs._get_active_visible_run_state",
        lambda: None,
    )

    # Threaden startes straks i stedet for i baggrunden, så testen er deterministisk.
    class _StraksThread:
        def __init__(self, target=None, name="", daemon=False):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr("threading.Thread", _StraksThread)

    run = SimpleNamespace(
        autonomous=False,
        session_id="chat-1",
        run_id="visible-test123",
        user_id="",
    )
    vrm._maybe_trigger_continuation(run, "Jeg læser filen nu og retter den.")

    assert spor.get("kwargs"), "continuation startede intet run"
    assert spor["kwargs"]["permission_session"] == "chat-1"
    assert spor["kwargs"]["origin"] == "continuation"
