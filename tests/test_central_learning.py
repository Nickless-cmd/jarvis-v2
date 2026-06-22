"""Tests for #4 adaptiv læring (central_learning) — deterministisk pr. cluster fra incidents."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import central_learning as cl


def _inc(cluster, nerve, *, severity="error", kind="", age_hours=1):
    ts = (datetime.now(UTC) - timedelta(hours=age_hours)).isoformat()
    return {"cluster": cluster, "nerve": nerve, "severity": severity, "kind": kind, "ts": ts}


def test_cluster_health_counts_window():
    inc = [_inc("auth", "tool_access", severity="severe", age_hours=1),
           _inc("auth", "tool_access", age_hours=2),
           _inc("loop", "loop_control", age_hours=100)]  # uden for 24t
    h = cl.cluster_health(hours=24, incidents=inc)
    assert h["auth"]["total"] == 2 and h["auth"]["severe"] == 1
    assert "loop" not in h


def test_degrading_detects_recent_spike():
    # 5 incidents i sidste time, ingen ældre baseline → recent-rate >> baseline → degraderende
    inc = [_inc("stream", "provider_call", age_hours=0.2) for _ in range(5)]
    deg = cl.degrading(recent_hours=6, baseline_hours=48, incidents=inc)
    assert any(d["cluster"] == "stream" and d["nerve"] == "provider_call" for d in deg)


def test_no_degrading_when_below_min():
    inc = [_inc("loop", "x", age_hours=0.5)]  # kun 1 < _DEGRADE_MIN_RECENT
    assert cl.degrading(incidents=inc) == []


def test_autonomous_reliability_from_supervision():
    inc = [_inc("autonomous", "supervision", kind="lied", age_hours=1),
           _inc("autonomous", "supervision", kind="connection_error", age_hours=2),
           _inc("auth", "tool_access", age_hours=1)]  # ikke supervision
    rel = cl.autonomous_reliability(hours=24, incidents=inc)
    assert rel["lied"] == 1 and rel["connection_error"] == 1 and rel["flagged_runs"] == 2


def test_assess_autonomy_lie_disqualifies():
    inc = [_inc("autonomous", "supervision", kind="lied", age_hours=1)]
    a = cl.assess_autonomy(incidents=inc)
    assert a["verdict"] == "ikke_moden" and a["dishonest"] is True


def test_assess_autonomy_clean_is_mature():
    a = cl.assess_autonomy(incidents=[])  # ingen flag → moden
    assert a["verdict"] == "moden"


def test_connection_flakiness_not_disqualifying():
    inc = [_inc("autonomous", "supervision", kind="connection_error", age_hours=1) for _ in range(3)]
    a = cl.assess_autonomy(incidents=inc)
    assert a["dishonest"] is False  # netværks-flakiness ≠ ustabil/uærlig


def test_catalog_has_learning():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "learning" in [n.name for n in cc.by_cluster("system")]
