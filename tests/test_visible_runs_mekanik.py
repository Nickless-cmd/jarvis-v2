"""Mekanik-tests for continuation vs. promise-registrering (side-02afb491ea).

Rodårsag 2+3 testet ved mekanismens søm:
- 23/6-guarden: et spørgsmål spawner ALDRIG en continuation (regression).
- Et ægte pause-løfte spawner stadig continuation (guard-stien er ikke død).
- _record_promise_from_run er koblet FRA _maybe_trigger_continuation: et
  løfte registreres selv når continuation er blokeret (spørgsmål/cooldown),
  og continuation-stien skriver ikke længere til promise-ledger.
- Registreringen bruger detect_promise_intent — spørgsmåls-guarden gælder
  kun for continuation, ikke for registrering.
"""

from __future__ import annotations

import threading
import time

import pytest

import core.services.promise_ledger as pl
import core.services.unfinished_intent as ui
import core.services.visible_runs_memory as vrm


def _mem_store(monkeypatch):
    """In-memory erstatning for runtime_state (ingen DB i unit-test)."""
    store: dict = {}
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "get_runtime_state_value", lambda k, d=None: store.get(k, d))

    def _set(k, v, **kw):
        store[k] = v

    monkeypatch.setattr(dbc, "set_runtime_state_value", _set)
    return store


class _Run:
    """Minimal VisibleRun-fake: kun felterne mekanikken læser."""

    def __init__(self) -> None:
        self.session_id = "sess-mekanik-test"
        self.run_id = "run-mekanik-test"
        self.autonomous = False


def _vent_paa_continuation_traade() -> None:
    """Vent til eventuelle continuation-tråde er færdige (delay er 0.01 s)."""
    for _ in range(500):
        alive = [
            t
            for t in threading.enumerate()
            if t.name.startswith("continuation-") and t.is_alive()
        ]
        if not alive:
            return
        time.sleep(0.01)


@pytest.fixture(autouse=True)
def _ren_mekanik(monkeypatch):
    """Uafhængige tests: ingen cooldown-arv, ingen DB, ingen ægte
    aktiv-run-abort, og 0.01 s delay så vent-lokket rammer."""
    ui.reset_cooldown_for_tests()
    monkeypatch.setattr(vrm, "_CONTINUATION_DELAY_SECONDS", 0.01)
    # _delayed_spawn importerer symbolet ved hvert kald — patch på modulet
    # der ejer det (core.services.visible_runs), ikke på vrm.
    monkeypatch.setattr(
        "core.services.visible_runs._get_active_visible_run_state", lambda: None
    )
    yield
    ui.reset_cooldown_for_tests()


def test_sporgsmaal_spawner_ikke_continuation(monkeypatch):
    """23/6-guarden: spørgsmål i slutningen må aldrig spawn en continuation."""
    kaldt = []
    monkeypatch.setattr(
        vrm._vr, "start_autonomous_run", lambda *a, **k: kaldt.append("spawn")
    )
    vrm._maybe_trigger_continuation(
        _Run(), "Skal jeg genstarte tjenesten, eller vil du selv gøre det?"
    )
    _vent_paa_continuation_traade()
    assert kaldt == []


def test_aegte_pause_spawner_continuation(monkeypatch):
    kaldt = []
    monkeypatch.setattr(
        vrm._vr, "start_autonomous_run", lambda *a, **k: kaldt.append("spawn")
    )
    vrm._maybe_trigger_continuation(
        _Run(),
        "Jeg fikser nu deploymenten, men der er stadig problemer i logs"
        " som jeg kigger på senere...",
    )
    _vent_paa_continuation_traade()
    assert kaldt == ["spawn"]


def test_continuation_stien_skriver_ikke_ledger(monkeypatch):
    """Rodårsag 3: ledger-skrivning er udkoblet. Genindsættes koblingen
    (record_promise inde i continuation-stien) bliver denne test rød."""
    store = _mem_store(monkeypatch)
    kaldt = []
    monkeypatch.setattr(
        vrm._vr, "start_autonomous_run", lambda *a, **k: kaldt.append("spawn")
    )
    vrm._maybe_trigger_continuation(
        _Run(), "Jeg opretter lige nu den nye række i tabellen og vender tilbage."
    )
    _vent_paa_continuation_traade()
    assert kaldt == ["spawn"]
    assert store == {}


def test_lofte_registreres_selv_om_continuation_blokeres(monkeypatch):
    """Rodårsag 2+3 samlet: løftet i en tekst der slutter med et spørgsmål
    registreres — continuation-guarden gælder kun for continuation."""
    _mem_store(monkeypatch)
    kaldt = []
    monkeypatch.setattr(
        vrm._vr, "start_autonomous_run", lambda *a, **k: kaldt.append("spawn")
    )
    run = _Run()
    t = (
        "Jeg tjekker lige at nøglerne er væk og vender tilbage med svar."
        " Skal jeg gemme dem i arkivet igen?"
    )
    vrm._record_promise_from_run(run, t)
    assert kaldt == []  # registreringen spawner aldrig continuation
    pend = pl.pending_promises(run.session_id)
    assert len(pend) == 1
    assert "tjekker lige" in pend[0]["text"]


def test_registrering_ignorerer_ikke_lofter(monkeypatch):
    store = _mem_store(monkeypatch)
    vrm._record_promise_from_run(_Run(), "Her er status på det hele:")
    assert store == {}


def test_autonome_runs_registrerer_ikke(monkeypatch):
    store = _mem_store(monkeypatch)
    run = _Run()
    run.autonomous = True
    vrm._record_promise_from_run(run, "Jeg tjekker lige at nøglerne er væk.")
    assert store == {}


def test_cooldown_sperrer_ikke_registrering(monkeypatch):
    """Cooldown gælder continuation — ikke om et løfte huskes."""
    _mem_store(monkeypatch)
    kaldt = []
    monkeypatch.setattr(
        vrm._vr, "start_autonomous_run", lambda *a, **k: kaldt.append("spawn")
    )
    run = _Run()
    ui.mark_triggered(run.session_id)
    vrm._maybe_trigger_continuation(
        run,
        "Jeg fikser nu deploymenten, men der er stadig problemer i logs"
        " som jeg kigger på senere...",
    )
    _vent_paa_continuation_traade()
    assert kaldt == []  # continuation spærret af cooldown
    vrm._record_promise_from_run(run, "Jeg tjekker lige at nøglerne er væk.")
    assert len(pl.pending_promises(run.session_id)) == 1
