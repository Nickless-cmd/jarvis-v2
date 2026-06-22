"""Test for #10 Phase A — autonome runs synlige i Centralen (_observe_autonomous_run)."""
from __future__ import annotations


def test_observe_autonomous_run_emits(monkeypatch):
    captured = {}

    class _Central:
        def observe(self, event):
            captured.update(event)

    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: _Central())

    from core.services.visible_runs import _observe_autonomous_run

    class _Run:
        run_id = "r1"; provider = "deepseek"; model = "v4"

    _observe_autonomous_run(run=_Run(), session_id="s1", outcome="failed",
                            frames=3, error="loopede")
    assert captured["cluster"] == "autonomous" and captured["nerve"] == "autonomous_run"
    assert captured["outcome"] == "failed" and captured["frames"] == 3
    assert captured["provider"] == "deepseek"


def test_observe_autonomous_self_safe():
    # må aldrig kaste selv på garbage-run
    from core.services.visible_runs import _observe_autonomous_run
    _observe_autonomous_run(run=object(), session_id="", outcome="completed")


def test_autonomous_cluster_in_catalog():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "autonomous" in cc.clusters()
