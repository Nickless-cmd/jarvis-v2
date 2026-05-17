"""Diagnostic-coverage for "silent stale state" bug (2026-05-17).

Symptom: `_prepare_scheduler_startup` logs `recovery_status=...-cleared`
men persisted DB-rækken er uændret. Næste tick fyrer aldrig fordi
schedule_state forbliver "ticking" og blokerer 9+ downstream daemons.

Disse tests verificerer at vi opfanger drift mellem intended overrides
og hvad der faktisk landede i DB — så næste incident producerer en
diagnostisk log + event, ikke stille tavshed.
"""
from __future__ import annotations

import pytest

from core.services import heartbeat_runtime as hb


def _stale_state() -> dict[str, object]:
    return {
        "state_id": "default",
        "last_tick_id": "",
        "last_tick_at": "",
        "next_tick_at": "",
        "schedule_state": "ticking",
        "due": False,
        "last_decision_type": "",
        "last_result": "",
        "blocked_reason": "already-ticking",
        "currently_ticking": True,  # bug-style: stuck ticking
        "last_trigger_source": "",
        "scheduler_active": False,
        "scheduler_started_at": "",
        "scheduler_stopped_at": "2026-05-17T10:35:15+00:00",
        "scheduler_health": "stopped",
        "recovery_status": "",
        "last_recovery_at": "",
        "provider": "",
        "model": "",
        "lane": "",
        "model_source": "",
        "resolution_status": "",
        "fallback_used": False,
        "execution_status": "",
        "parse_status": "",
        "budget_status": "ok",
        "last_ping_eligible": False,
        "last_ping_result": "",
        "last_successful_ping_at": "",
        "last_action_type": "",
        "last_action_status": "",
        "last_action_summary": "",
        "last_action_artifact": "",
        "updated_at": "2026-05-17T10:35:15+00:00",  # frozen
    }


def _policy_stub(*, name: str) -> dict[str, object]:
    return {
        "enabled": True,
        "kill_switch": "enabled",
        "budget_status": "ok",
    }


def test_prepare_scheduler_startup_detects_silent_write_drift(
    monkeypatch, caplog
) -> None:
    """Når _persist_runtime_state returnerer stale data (write landede ikke
    i DB), skal _prepare_scheduler_startup publishe heartbeat.scheduler_startup_drift
    med diagnostisk kontekst — ikke stille fortsætte som om alt er fint."""
    monkeypatch.setattr(hb, "get_heartbeat_runtime_state", lambda: _stale_state())
    monkeypatch.setattr(hb, "load_heartbeat_policy", _policy_stub)

    # Simuler "silent write": upsert returnerer stadig den gamle row
    stale = _stale_state()
    monkeypatch.setattr(hb, "_persist_runtime_state", lambda **_: stale)

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        hb.event_bus, "publish", lambda name, payload: events.append((name, payload))
    )

    hb._prepare_scheduler_startup(name="default")

    drift = [e for e in events if e[0] == "heartbeat.scheduler_startup_drift"]
    assert drift, f"forventede drift-event, fik events={[e[0] for e in events]}"
    payload = drift[0][1]
    assert "mismatches" in payload
    assert "scheduler_health" in payload["mismatches"]
    assert payload["mismatches"]["scheduler_health"]["expected"] == "active"
    assert payload["mismatches"]["scheduler_health"]["actual"] == "stopped"
    assert "pid" in payload and isinstance(payload["pid"], int)
    assert "db_path" in payload


def test_prepare_scheduler_startup_no_drift_when_write_succeeded(monkeypatch) -> None:
    """Happy-path: upsert returnerer faktisk-skrevet state — ingen drift-event."""
    monkeypatch.setattr(hb, "get_heartbeat_runtime_state", lambda: _stale_state())
    monkeypatch.setattr(hb, "load_heartbeat_policy", _policy_stub)

    def _truthful_persist(**kwargs):
        overrides = kwargs["overrides"]
        merged = _stale_state()
        merged.update(overrides)
        return merged

    monkeypatch.setattr(hb, "_persist_runtime_state", _truthful_persist)

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        hb.event_bus, "publish", lambda name, payload: events.append((name, payload))
    )

    hb._prepare_scheduler_startup(name="default")

    drift = [e for e in events if e[0] == "heartbeat.scheduler_startup_drift"]
    assert not drift, f"happy-path skulle ikke publishe drift, fik {drift}"


def test_prepare_scheduler_startup_reraises_on_persist_exception(
    monkeypatch, caplog
) -> None:
    """Hvis _persist_runtime_state kaster (fx DB locked), skal vi re-raise
    med stack trace i log — ikke sluge exception og lade startup fortsætte."""
    monkeypatch.setattr(hb, "get_heartbeat_runtime_state", lambda: _stale_state())
    monkeypatch.setattr(hb, "load_heartbeat_policy", _policy_stub)

    def _boom(**_):
        raise RuntimeError("simulated DB write failure")

    monkeypatch.setattr(hb, "_persist_runtime_state", _boom)

    with caplog.at_level("ERROR"):
        with pytest.raises(RuntimeError, match="simulated DB write failure"):
            hb._prepare_scheduler_startup(name="default")

    assert any(
        "HEARTBEAT-STATE-PERSIST-FAILED" in r.message
        for r in caplog.records
    ), "forventede logger.exception med stack trace + HEARTBEAT-STATE- prefix"
