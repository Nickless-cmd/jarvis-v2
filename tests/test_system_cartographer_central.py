"""Tests for kartograf→Central-meldingen (system_cartographer._observe_to_central).

Verificerer at systemkortet meldes til Centralen med de rigtige felter, at det er self-safe,
og at system-cluster-nerverne er registreret. (Den fulde build_system_cartographer_surface
testes andetsteds; her dækker vi observe-broen til Centralen.)
"""
from __future__ import annotations

from core.services import system_cartographer as sc


def test_observe_to_central_emits_map(monkeypatch):
    captured = {}

    class _Central:
        def observe(self, event):
            captured.update(event)

    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: _Central())

    surface = {
        "summary": {"services": 230, "daemons": 30, "dark_edges": 12,
                    "low_coverage_services": 8, "theater_high_risk": 1, "tools": 434},
        "systemHealth": {"state": "needs-witness"},
        "autoTask": {"status": "enqueued", "task_id": "t123"},
        "recommendedObservabilityTask": {"title": "Expose foo in Mission Control"},
    }
    sc._observe_to_central(surface)
    assert captured["cluster"] == "system" and captured["nerve"] == "cartographer"
    assert captured["services"] == 230
    assert captured["dark_edges"] == 12
    assert captured["health_state"] == "needs-witness"
    assert captured["auto_task_status"] == "enqueued"
    assert captured["recommended_next"] == "Expose foo in Mission Control"


def test_observe_to_central_self_safe_on_garbage():
    # må aldrig kaste, selv på tomt/uventet input
    sc._observe_to_central({})
    sc._observe_to_central({"summary": None})


def test_system_cluster_in_catalog():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "system" in cc.clusters()
    names = [n.name for n in cc.by_cluster("system")]
    assert "cartographer" in names
