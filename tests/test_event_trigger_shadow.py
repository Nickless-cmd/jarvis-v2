"""event_trigger_shadow — heartbeat-path self-cadence gate (2026-07-14).

The θ-meter is called from TWO heartbeat paths (priorities via run_heartbeat_tick,
idle via productive_idle). To keep the 500-sample durable ring covering a full ~25h
θ-window, the heartbeat path (signals=None) self-throttles to ~3 min. Injected signals
(test / explicit caller) are NEVER throttled — so the durable tests keep asserting a
sample per call.
"""
from __future__ import annotations

import importlib

import pytest


def _load():
    return importlib.import_module("core.services.event_trigger_shadow")


@pytest.fixture()
def neutralized(monkeypatch):
    mod = _load()
    import core.services.signal_delta_trigger as sdt
    from core.services import central_timeseries as ts

    monkeypatch.setattr(ts, "record", lambda *a, **k: None)
    monkeypatch.setattr(mod, "_gather_signals", lambda: {"autonomy_pressure": 0.7})
    monkeypatch.setattr(sdt, "evaluate", lambda s: {"crossed": [], "movements": {}, "reason": "flat"})
    monkeypatch.setattr(
        mod, "_consult_guards",
        lambda: {"budget_ok": True, "breaker_tripped": False, "visible_active": False},
    )
    mod._last_tick_at = None
    return mod


def test_heartbeat_path_records_then_throttles(isolated_runtime, neutralized):
    mod = neutralized
    out1 = mod.tick_event_trigger_shadow()  # no signals = heartbeat path
    assert out1["recorded"] is True
    out2 = mod.tick_event_trigger_shadow()  # immediate re-call throttled
    assert out2["recorded"] is False
    assert out2["skipped"] == "cadence"


def test_injected_signals_never_throttle(isolated_runtime, neutralized):
    mod = neutralized
    # a heartbeat-path call arms the throttle...
    assert mod.tick_event_trigger_shadow()["recorded"] is True
    # ...but an explicit signals= call still records (test/durable path unaffected).
    assert mod.tick_event_trigger_shadow(signals={"autonomy_pressure": 0.9})["recorded"] is True


def test_cadence_elapsed_allows_next_heartbeat_tick(isolated_runtime, neutralized):
    mod = neutralized
    assert mod.tick_event_trigger_shadow()["recorded"] is True
    # backdate past the cadence window → next heartbeat tick fires again.
    mod._last_tick_at = mod._last_tick_at - (mod._CADENCE_SECONDS + 1.0)
    assert mod.tick_event_trigger_shadow()["recorded"] is True
