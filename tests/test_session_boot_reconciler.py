from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta


def _fresh_modules():
    runs = importlib.reload(importlib.import_module("core.services.in_flight_runs"))
    importlib.reload(importlib.import_module("core.services.session_persistence_flag"))
    rec = importlib.reload(importlib.import_module("core.services.session_boot_reconciler"))
    return runs, rec


def _seed(runs, *, status="running", age_s=1000, run_id="run-z", kind="visible"):
    started = (datetime.now(UTC) - timedelta(seconds=age_s)).isoformat()
    records = runs._load()
    records[run_id] = {
        "run_id": run_id, "session_id": "s1", "status": status,
        "kind": kind, "provider": "", "model": "",
        "excerpt": "arbejde", "started_at": started, "last_tool": "",
    }
    runs._save(records)


def _enable(on: bool):
    from core.runtime.db import set_runtime_state_value
    set_runtime_state_value("session_persistence", "on" if on else "off")


def test_flag_default_off(isolated_runtime):
    _, rec = _fresh_modules()
    from core.services.session_persistence_flag import session_persistence_enabled
    assert session_persistence_enabled() is False


def test_enabled_zombie_marked_interrupted_and_nerve_fired(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="running", age_s=1000, run_id="run-z")

    observed = []
    monkeypatch.setattr(rec, "_observe", lambda payload: observed.append(payload))

    summary = rec.reconcile_on_boot()

    assert runs._load()["run-z"]["status"] == "interrupted"
    assert runs._load()["run-z"]["interruption_reason"] == "afbrudt af container-genstart"
    assert summary["count"] == 1
    assert summary["enforced"] is True
    assert observed and observed[0]["count"] == 1
    assert observed[0]["enforced"] is True
    assert "visible" in observed[0]["kinds"]


def test_fresh_running_untouched(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="running", age_s=5, run_id="run-fresh")
    monkeypatch.setattr(rec, "_observe", lambda payload: None)

    summary = rec.reconcile_on_boot()

    assert runs._load()["run-fresh"]["status"] == "running"
    assert summary["count"] == 0


def test_already_interrupted_untouched(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="interrupted", age_s=1000, run_id="run-i")
    monkeypatch.setattr(rec, "_observe", lambda payload: None)

    summary = rec.reconcile_on_boot()

    assert runs._load()["run-i"]["status"] == "interrupted"
    assert summary["count"] == 0


def test_disabled_observe_only_no_writes(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(False)
    _seed(runs, status="running", age_s=1000, run_id="run-z")

    observed = []
    monkeypatch.setattr(rec, "_observe", lambda payload: observed.append(payload))

    summary = rec.reconcile_on_boot()

    # Nothing written: still 'running'.
    assert runs._load()["run-z"]["status"] == "running"
    # But we counted what WOULD happen.
    assert summary["count"] == 1
    assert summary["enforced"] is False
    assert observed and observed[0]["count"] == 1
    assert observed[0]["enforced"] is False


def test_idempotent_second_run_finds_nothing(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="running", age_s=1000, run_id="run-z")
    monkeypatch.setattr(rec, "_observe", lambda payload: None)

    first = rec.reconcile_on_boot()
    second = rec.reconcile_on_boot()

    assert first["count"] == 1
    assert second["count"] == 0
    assert runs._load()["run-z"]["status"] == "interrupted"


def test_reconciler_swallows_exceptions(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)

    def _boom(_):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(rec.in_flight_runs, "list_running_orphans", _boom)

    # Must not raise; returns a safe empty-ish summary.
    summary = rec.reconcile_on_boot()
    assert summary["count"] == 0
    assert summary.get("error") is True


def test_kinds_aggregated_across_orphans(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="running", age_s=1000, run_id="run-v", kind="visible")
    _seed(runs, status="running", age_s=1000, run_id="run-a", kind="autonomous")

    observed = []
    monkeypatch.setattr(rec, "_observe", lambda payload: observed.append(payload))

    summary = rec.reconcile_on_boot()

    assert summary["count"] == 2
    assert set(observed[0]["kinds"]) == {"visible", "autonomous"}
