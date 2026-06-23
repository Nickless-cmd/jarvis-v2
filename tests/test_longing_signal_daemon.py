"""Tests for longing_signal_daemon — Central-observe wiring + killswitch."""
from __future__ import annotations

from core.services import longing_signal_daemon as lsd


def test_disabled_killswitch_noop(monkeypatch):
    class _S:
        generative_autonomy_enabled = False
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())
    out = lsd.run_longing_signal_daemon_tick()
    assert out["status"] == "disabled"


def test_emit_observes_to_central(monkeypatch):
    class _S:
        generative_autonomy_enabled = True
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())
    monkeypatch.setattr(lsd, "compute_longing_intensity",
                        lambda: {"salience": 0.7, "context": {"hours_since_last_user_message": 3.0}})
    monkeypatch.setattr("core.services.signal_pressure_accumulator.ingest_signal",
                        lambda fam, sig: None)
    seen = {}
    class _C:
        def observe(self, ev): seen.update(ev)
    monkeypatch.setattr("core.services.central_core.central", lambda: _C())
    out = lsd.run_longing_signal_daemon_tick()
    assert out["emitted"] is True
    assert seen.get("cluster") == "proactivity" and seen.get("nerve") == "longing_signal"
    assert seen.get("intensity") == 0.7
