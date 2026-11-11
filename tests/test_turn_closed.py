"""Turen skal være HELT afsluttet før et wakeup kan begynde (11/11-2026).

Bjørn: «en tur skal afsluttes helt før et wakeup kan begyndes».

Hullet var tidsbaseret: vagten gav op efter 120 sekunder, og
`unregister_visible_run` rydder aktiv-slot'en før det sidste frame er nået
klienten. Nu spørges den DELTE journal i stedet for et ur.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import in_flight_runs as ifr
from core.services.visible_runs_sections import run_control_state as rcs


@pytest.fixture(autouse=True)
def _isoleret_lager(tmp_path, monkeypatch):
    lager: dict = {}
    monkeypatch.setattr(ifr, "_load", lambda: lager)
    monkeypatch.setattr(ifr, "_save", lambda d: lager.update(d))
    # Kvitteringen lever i runtime-state (DB). Uden denne isolering læser testen
    # en kvittering en TIDLIGERE kørsel har efterladt for samme session-id, og
    # så maaler den sin egen historik i stedet for koden.
    kvitteringer: dict = {}
    monkeypatch.setattr(rcs, "set_runtime_state_value",
                        lambda k, v: kvitteringer.__setitem__(k, v))
    monkeypatch.setattr(rcs, "get_runtime_state_value",
                        lambda k, default=None: kvitteringer.get(k, default))
    return lager


def _post(lager, rid, sid, *, alder_s=0.0):
    t = (datetime.now(UTC) - timedelta(seconds=alder_s)).isoformat()
    lager[rid] = {
        "run_id": rid, "session_id": sid, "status": "running",
        "started_at": t, "last_progress_at": t, "owner_proc": "",
    }


def test_en_koerende_tur_holder_wakeup_tilbage(_isoleret_lager):
    _post(_isoleret_lager, "r1", "s1")
    assert rcs.turn_is_open("s1") is True


def test_et_gammelt_men_koerende_run_er_STADIG_aabent(_isoleret_lager):
    """Kernen i Bjørns krav: alderen må ikke afgøre det. Et run der venter på
    et godkendelses-kort kan stå i minutter uden at være færdigt — den gamle
    vagt gav op efter 120 s og startede et wakeup oveni."""
    _post(_isoleret_lager, "r1", "s1", alder_s=3600)
    assert rcs.turn_is_open("s1") is True


def test_en_lukket_tur_aabner_for_wakeup(_isoleret_lager):
    assert rcs.turn_is_open("s1") is False


def test_kvitteringen_skrives_pr_session(monkeypatch):
    skrevet: dict = {}
    monkeypatch.setattr(rcs, "set_runtime_state_value",
                        lambda k, v: skrevet.__setitem__(k, v))
    rcs.mark_turn_closed("s1", "r1")
    assert "visible_runs.turn_closed.s1" in skrevet
    assert skrevet["visible_runs.turn_closed.s1"]["run_id"] == "r1"


def test_tom_session_kvitteres_ikke(monkeypatch):
    skrevet: dict = {}
    monkeypatch.setattr(rcs, "set_runtime_state_value",
                        lambda k, v: skrevet.__setitem__(k, v))
    rcs.mark_turn_closed("", "r1")
    assert skrevet == {}


def test_kvitteringen_SLAAR_de_andre_kilder(_isoleret_lager, monkeypatch):
    """Målt 11/11-2026: kvitteringen blev skrevet, men `turn_is_open` læste den
    aldrig — så den var død kode på den vej Bjørn faktisk ser. Her står der et
    levende run i journalen SAMTIDIG med at turen er kvitteret lukket: den
    situation opstår i vinduet hvor det sidste frame er sendt men
    `mark_completed` endnu ikke har ryddet posten. Kvitteringen skal vinde."""
    _post(_isoleret_lager, "r1", "s1")
    assert rcs.turn_is_open("s1") is True
    rcs.mark_turn_closed("s1", "r1")
    assert rcs.turn_is_open("s1") is False


def test_en_ukvitteret_session_falder_tilbage_til_journalen(_isoleret_lager):
    """Uden kvittering må svaret ikke blive «lukket» — så ville vagten lukke
    wakeups ind i en tur der stadig kører."""
    _post(_isoleret_lager, "r1", "s1")
    assert rcs.turn_closed_at("s1") == ""
    assert rcs.turn_is_open("s1") is True
