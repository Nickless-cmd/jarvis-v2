"""C5 — durable event-trigger SHADOW telemetry tests.

The shadow tick records to `central_timeseries`, which is IN-MEMORY (wiped on
every restart). After a night of restarts that leaves ZERO calibration samples.
These tests prove the DURABLE ring-buffer (runtime-state `event_trigger_shadow_log`)
that survives restart, so a stable 24h window actually accumulates θ-data:

  * a tick appends a sample to the durable log; recent_shadow_samples() returns it;
  * the samples survive a simulated restart (read-cache cleared → re-read from DB);
  * the log is capped (>500 appends → keeps the newest ~500);
  * a persist error never breaks the tick (self-safe).

The existing central_timeseries.record is kept (live view) — durable persist is
ADDED alongside it.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def wired(monkeypatch):
    """Neutralise the LLM/council seams + make signal_delta_trigger + guards
    deterministic. central_timeseries.record is captured (must still be called)."""
    from core.services import central_timeseries as ts
    import core.services.signal_delta_trigger as sdt
    import core.services.dispatch_guards as dg
    import core.services.autonomous_lease as al
    import core.services.central_convene_judge as cj

    records: list[dict] = []

    def _rec(cluster, nerve, value=None, *, meta=None):
        records.append({"cluster": cluster, "nerve": nerve, "value": value, "meta": dict(meta or {})})

    monkeypatch.setattr(ts, "record", _rec)
    monkeypatch.setattr(cj, "current_mode", lambda: "shadow")
    monkeypatch.setattr(
        sdt, "evaluate",
        lambda signals: {
            "crossed": ["autonomy_pressure"],
            "movements": {"autonomy_pressure": 0.4},
            "reason": "signal-delta dispatch",
        },
    )
    monkeypatch.setattr(dg, "budget_allows", lambda *a, **k: True)
    monkeypatch.setattr(dg, "is_tripped", lambda *a, **k: False)
    monkeypatch.setattr(al, "visible_active", lambda *a, **k: False)
    return {"records": records}


def _load():
    import importlib

    return importlib.import_module("core.services.event_trigger_shadow")


def test_tick_appends_durable_sample(isolated_runtime, wired):
    mod = _load()

    before = mod.recent_shadow_samples()
    assert before == []

    out = mod.tick_event_trigger_shadow(signals={"autonomy_pressure": 0.7}, now="2026-07-13T10:00:00+00:00")
    assert out["recorded"] is True

    # central_timeseries.record still fired (live view kept).
    assert len(wired["records"]) == 1

    samples = mod.recent_shadow_samples()
    assert len(samples) == 1
    s = samples[0]
    assert s["ts"] == "2026-07-13T10:00:00+00:00"
    assert s["would_dispatch"] is True
    assert s["crossed"] == ["autonomy_pressure"]
    assert s["movement"] == pytest.approx(0.4)
    assert s["budget_ok"] is True
    assert s["breaker_tripped"] is False
    assert s["visible_active"] is False
    assert s["signals"] == {"autonomy_pressure": 0.7}
    assert s["movements"] == {"autonomy_pressure": 0.4}


def test_samples_survive_simulated_restart(isolated_runtime, wired):
    mod = _load()
    from core.runtime import db_core

    mod.tick_event_trigger_shadow(signals={"autonomy_pressure": 0.7}, now="2026-07-13T10:00:00+00:00")

    # Simulate a restart: central_timeseries is in-memory and would be wiped, and
    # the runtime-state read-cache is cold. Clear the read-cache → force a fresh
    # DB read. The durable log (sqlite runtime_state_kv) must still be there.
    db_core.clear_runtime_state_cache()

    samples = mod.recent_shadow_samples()
    assert len(samples) == 1
    assert samples[0]["ts"] == "2026-07-13T10:00:00+00:00"
    assert samples[0]["would_dispatch"] is True


def test_durable_log_is_capped(isolated_runtime, wired):
    mod = _load()

    # Append well over the cap; oldest must drop, newest survive.
    total = mod._DURABLE_CAP + 40
    for i in range(total):
        mod.tick_event_trigger_shadow(
            signals={"autonomy_pressure": 0.7}, now=f"2026-07-13T10:00:{i:02d}+00:00",
        )

    samples = mod.recent_shadow_samples(limit=10_000)
    assert len(samples) == mod._DURABLE_CAP
    # newest kept (last appended), oldest dropped.
    assert samples[-1]["ts"] == f"2026-07-13T10:00:{total - 1:02d}+00:00"
    # the very first sample must have aged out.
    kept_ts = {s["ts"] for s in samples}
    assert "2026-07-13T10:00:00+00:00" not in kept_ts


def test_persist_error_does_not_break_tick(isolated_runtime, wired, monkeypatch):
    mod = _load()

    def _boom(*a, **k):
        raise RuntimeError("durable store unavailable")

    # Break the durable persist path — the tick must still record + return normally.
    monkeypatch.setattr(mod, "_persist_durable", _boom)

    out = mod.tick_event_trigger_shadow(signals={"autonomy_pressure": 0.7})
    assert out["recorded"] is True
    assert out["would_dispatch"] is True
    # live-view record still fired despite the durable failure.
    assert len(wired["records"]) == 1
