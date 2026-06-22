"""Test for #10 Phase A — autonome runs synlige i Centralen (_observe_autonomous_run)."""
from __future__ import annotations


def test_observe_autonomous_run_emits(monkeypatch):
    events = []

    class _Central:
        def observe(self, event):
            events.append(dict(event))

    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: _Central())
    # supervise() kaldes også nu (#3) — neutralisér dens incident-skrivning
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: None)

    from core.services.visible_runs import _observe_autonomous_run

    class _Run:
        run_id = "r1"; provider = "deepseek"; model = "v4"

    _observe_autonomous_run(run=_Run(), session_id="s1", outcome="failed",
                            frames=3, error="loopede")
    # autonomous_run-observen skal være blandt de emitterede (supervision kommer også)
    run_ev = next(e for e in events if e.get("nerve") == "autonomous_run")
    assert run_ev["cluster"] == "autonomous"
    assert run_ev["outcome"] == "failed" and run_ev["frames"] == 3
    assert run_ev["provider"] == "deepseek"


def test_observe_autonomous_self_safe():
    # må aldrig kaste selv på garbage-run
    from core.services.visible_runs import _observe_autonomous_run
    _observe_autonomous_run(run=object(), session_id="", outcome="completed")


def test_autonomous_cluster_in_catalog():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "autonomous" in cc.clusters()
