"""Tests for core/services/central_causal_quality.py — causal tier-fordeling + precision (Fase 1d)."""
from __future__ import annotations

import pytest

from core.services import central_causal_quality as cq
from core.services import central_timeseries


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


def _seed_graph(isolated_runtime):
    """Byg en lille causal-graf: events + edges med kendte tiers/kinds."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        # events: id 1=tool.invoked, 2=tool.completed, 3=inner_voice.signal, 4=dream.x
        for eid, kind in [(1, "tool.invoked"), (2, "tool.completed"),
                          (3, "inner_voice.signal"), (4, "dream.x")]:
            c.execute("INSERT INTO events (id, kind, payload_json, created_at) VALUES (?,?,?,?)",
                      (eid, kind, "{}", "2026-07-02T00:00:00Z"))
        # Tier-1: tool.completed → tool.invoked (findes som _KIND_RULES-par)
        c.execute("INSERT INTO causal_edges (child_event_id,parent_event_id,edge_kind,confidence,source,created_at) "
                  "VALUES (2,1,'triggered',0.9,'inferred-kind','2026-07-02T00:00:00Z')")
        # Tier-3 A: tool.completed → tool.invoked (KORROBORERET af tier-1-reglen)
        c.execute("INSERT INTO causal_edges (child_event_id,parent_event_id,edge_kind,confidence,source,created_at) "
                  "VALUES (2,1,'caused',0.4,'inferred-temporal','2026-07-02T00:00:00Z')")
        # Tier-3 B: dream.x → inner_voice.signal (UKORROBORERET = ren co-occurrence)
        c.execute("INSERT INTO causal_edges (child_event_id,parent_event_id,edge_kind,confidence,source,created_at) "
                  "VALUES (4,3,'caused',0.4,'inferred-temporal','2026-07-02T00:00:00Z')")
        c.commit()


def test_tier_distribution(isolated_runtime):
    _seed_graph(isolated_runtime)
    m = cq.measure_edge_tiers()
    assert m["total"] == 3
    assert m["tier1"] == 1 and m["tier3"] == 2
    # meningsfuldt = kun tier-1 → 1/3
    assert m["meaningful_ratio"] == round(1 / 3, 4)
    assert m["tier3_ratio"] == round(2 / 3, 4)


def test_tier3_precision_corroboration(isolated_runtime):
    _seed_graph(isolated_runtime)
    p = cq.estimate_tier3_precision()
    # 2 tier-3-kanter: A korroboreret (kind-par findes som tier-1-regel), B ikke → 1/2
    assert p["sampled"] == 2
    assert p["corroborated"] == 1
    assert p["tier3_precision"] == 0.5


def test_record_writes_timeseries(isolated_runtime):
    _seed_graph(isolated_runtime)
    cq.record_causal_quality()
    assert central_timeseries.recent("system", "causal_edges_total")
    assert central_timeseries.recent("system", "causal_tier3_ratio")
    assert central_timeseries.recent("system", "causal_tier3_precision")


def test_empty_graph_no_crash(isolated_runtime):
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.commit()
    m = cq.measure()
    assert m["total"] == 0
    assert m["tier3_ratio"] is None and m["tier3_precision"] is None
    res = cq.run_causal_quality_tick()
    assert res["status"] == "ok"
