"""Tests for core/services/central_hypothesis_generator.py — Lag 3 governed generator (observe-only)."""
from __future__ import annotations

import pytest

from core.services import central_hypothesis_generator as gen


def _seed_edges(isolated_runtime, pairs):
    """pairs: list of (parent_kind, child_kind, count, source)."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    eid = 1
    with connect() as c:
        _ensure_causal_edges_table(c)
        gen.ensure_schema()
        for pk, ck, count, source in pairs:
            for _ in range(count):
                p, ch = eid, eid + 1
                eid += 2
                c.execute("INSERT INTO events (id, kind, payload_json, created_at) VALUES (?,?,?,?)",
                          (p, pk, "{}", "2026-07-02T00:00:00Z"))
                c.execute("INSERT INTO events (id, kind, payload_json, created_at) VALUES (?,?,?,?)",
                          (ch, ck, "{}", "2026-07-02T00:00:00Z"))
                c.execute("INSERT INTO causal_edges (child_event_id,parent_event_id,edge_kind,"
                          "confidence,source,created_at) VALUES (?,?,'caused',0.9,?,?)",
                          (ch, p, source, "2026-07-02T00:00:00Z"))
        c.commit()


def test_detect_recurring_meaningful_pairs(isolated_runtime):
    _seed_edges(isolated_runtime, [
        ("memory.recall_fail", "somatic.stress", 4, "inferred-kind"),   # meningsfuld, ≥3
        ("tool.invoked", "tool.completed", 2, "inferred-id"),           # under tærskel
        ("noise.a", "noise.b", 5, "inferred-temporal"),                 # Tier-3 = ignoreres
    ])
    cands = gen.detect_causal_convergence_candidates(min_recurrence=3)
    fams = {(c["parent_family"], c["child_family"]) for c in cands}
    assert ("memory", "somatic") in fams
    assert ("tool", "tool") not in fams        # samme familie filtreres + under tærskel
    assert ("noise", "noise") not in fams      # Tier-3 udelukket


def test_formulate_is_preregistered(isolated_runtime):
    cand = {"parent_family": "memory", "child_family": "somatic", "count": 4, "cursor": 42}
    hyp = gen.formulate_correlation_hypothesis(cand)
    from core.services import central_hypothesis_governance as gov
    ok, missing = gov.validate_preregistration(hyp)
    assert ok and missing == []
    assert hyp["provenance"]["family"] == "memory->somatic"


def test_register_rejects_unpreregistered(isolated_runtime):
    res = gen.register_governed_hypothesis({"statement": "nøgen", "provenance": {}})
    assert res["status"] == "rejected"


def test_full_generation_tick_registers(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    res = gen.run_hypothesis_generation_tick()
    assert res["status"] == "ok" and res["registered"] == 1
    active = gen.list_active_hypotheses()
    assert active and "memory" in active[0]["statement"]
    # idempotent: anden tick registrerer ikke dubletten
    res2 = gen.run_hypothesis_generation_tick()
    assert res2["registered"] == 0 and res2["duplicate"] >= 1


def test_grounded_samples_resolve_hypothesis(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    hyp_id = gen.list_active_hypotheses()[0]["hyp_id"]
    # 5 jordede støttende samples (sample_size=5) → resolve supported
    out = None
    for i in range(5):
        out = gen.record_governed_sample(hyp_id, supports=True, falsifies=False,
                                         source="run_outcome", ground_ref=f"run-{i}",
                                         triggered_by="world")
    assert out["hyp_status"] == "resolved" and out["outcome"] == "supported"


def test_unverified_grounding_does_not_resolve(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    hyp_id = gen.list_active_hypotheses()[0]["hyp_id"]
    # samples uden ground_ref → tæller ikke som jordede → forbliver aktiv (afventer)
    for i in range(6):
        out = gen.record_governed_sample(hyp_id, supports=True, source="run_outcome")
    assert out["hyp_status"] == "active"


def test_self_triggered_confirmation_quarantined(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    hyp_id = gen.list_active_hypotheses()[0]["hyp_id"]
    # bekræftelse hvor triggered_by == hyp_id (selv-opfyldende) → karantæne
    out = gen.record_governed_sample(hyp_id, supports=True, source="run_outcome",
                                     ground_ref="run-x", triggered_by=hyp_id)
    assert out["hyp_status"] == "quarantined"
