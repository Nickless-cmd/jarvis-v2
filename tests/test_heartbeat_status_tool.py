"""Værktøjet der svarer på «lever heartbeat?» må ikke svare om sin EGEN proces.

Målt 11/11-2026: API-processen (8080, `JARVIS_ENABLE_RUNTIME_SERVICES=0`)
starter aldrig scheduleren, så dens modul-globale `_THREAD`/`_ITERATION` er
altid tomme. Schedulerens tråd lever i runtime-processen (8011). Værktøjet
hentede `active`/`health` fra den DELTE tilstand, men tråden fra sin egen
tomme kopi — og svarede derfor `DEGRADED` permanent, mens journalen viste
`HEARTBEAT-LOOP iteration=8`.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from core.services import heartbeat_scheduler as sched


@pytest.fixture(autouse=True)
def _rene():
    sched._STOP.set()
    sched._THREAD = None
    sched._ITERATION = 0
    yield
    sched._STOP.set()
    sched._THREAD = None


def _iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def _write_state(tmp_path, monkeypatch, *, next_tick_minutes_ago, active=1, health="active"):
    now = datetime.now(UTC)
    state = {
        "scheduler_active": active,
        "scheduler_health": health,
        "last_tick_at": _iso(now - timedelta(minutes=next_tick_minutes_ago + 15)),
        "next_tick_at": _iso(now - timedelta(minutes=next_tick_minutes_ago)),
        "interval_minutes": 15,
    }
    path = tmp_path / "HEARTBEAT_STATE.json"
    path.write_text(json.dumps({
        "state": state,
        "recent_ticks": [],
    }), encoding="utf-8")
    import core.runtime.workspace_paths as wp
    from core.runtime import db_heartbeat

    monkeypatch.setattr(wp, "heartbeat_state_path", lambda: path)
    monkeypatch.setattr(db_heartbeat, "get_heartbeat_runtime_state", lambda: state)


def _fresh_tick(monkeypatch):
    from core.runtime import db_heartbeat

    now = datetime.now(UTC)
    monkeypatch.setattr(
        db_heartbeat,
        "recent_heartbeat_runtime_ticks",
        lambda *, limit: [{"started_at": _iso(now - timedelta(seconds=30))}],
    )


def test_status_bruger_delt_fremdrift_naar_observatoerprocessen_ikke_ejer_traaden(
    tmp_path, monkeypatch
):
    """API-processens tomme modul-globaler må ikke beskrive runtime-tråden."""
    from core.tools.simple_tools_native import _exec_heartbeat_status

    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "0")
    _write_state(tmp_path, monkeypatch, next_tick_minutes_ago=-10)
    _fresh_tick(monkeypatch)

    assert sched.is_running() is False
    assert sched.iterations() == 0
    out = _exec_heartbeat_status({})
    assert out["scheduler"]["verdict"] == "ACTIVE"
    assert "flag_active_but_thread_not_running" not in out["scheduler"]["mismatch"]
    assert out["scheduler"]["thread_observation"] == "not_observed_in_this_process"
    assert "not observed in this process" in out["text"]


def test_ejerprocessen_fanger_stadig_en_aegte_stilstand(tmp_path, monkeypatch):
    """Fixet må ikke gøre dommen tandløs.

    Kun observatørprocessen må melde «ikke observeret». I EJERprocessen, hvor
    `_THREAD` og `_ITERATION` faktisk beskriver schedulerens tråd, skal en død
    tråd stadig give mismatch — ellers har vi byttet en falsk alarm ud med en
    vagt der aldrig ringer.
    """
    from core.tools.simple_tools_native import _exec_heartbeat_status

    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")
    _write_state(tmp_path, monkeypatch, next_tick_minutes_ago=-10)
    _fresh_tick(monkeypatch)

    assert sched.is_running() is False
    out = _exec_heartbeat_status({})
    assert out["scheduler"]["observer_process"] == "runtime"
    assert out["scheduler"]["thread_observation"] == "not_running"
    assert "flag_active_but_thread_not_running" in out["scheduler"]["mismatch"]
    assert out["scheduler"]["verdict"] == "DEGRADED"


def test_db_fejl_bliver_logget_og_ikke_tavst_nul(tmp_path, monkeypatch, caplog):
    """En DB-fejl må ikke se ud som «ingen ticks»."""
    from core.runtime import db_heartbeat
    from core.tools.simple_tools_native import _exec_heartbeat_status

    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "0")
    _write_state(tmp_path, monkeypatch, next_tick_minutes_ago=-10)

    def _boom(*, limit):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(db_heartbeat, "recent_heartbeat_runtime_ticks", _boom)

    with caplog.at_level("WARNING"):
        out = _exec_heartbeat_status({})
    assert out["status"] == "ok"
    assert "database is locked" in caplog.text
