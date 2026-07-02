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


def test_detect_outcome_divergence(isolated_runtime):
    """Rådets dybeste: samme årsag → modsatte udfald = divergens (konflikt-trigger)."""
    _seed_edges(isolated_runtime, [
        ("decision.created", "behavioral_decision_review.kept", 3, "inferred-kind"),
        ("decision.created", "behavioral_decision_review.broken", 2, "inferred-kind"),
        ("tool.invoked", "tool.completed", 4, "inferred-id"),   # kun én side → ikke divergens
    ])
    cands = gen.detect_outcome_divergence_candidates(min_each=2)
    fams = {c["parent_family"] for c in cands}
    assert "decision" in fams            # fører til BEGGE kept+broken
    assert "tool" not in fams            # kun completed, ingen error → ingen divergens
    hyp = gen.formulate_divergence_hypothesis(cands[0])
    from core.services import central_hypothesis_governance as gov
    ok, _ = gov.validate_preregistration(hyp)
    assert ok and hyp["source"] == "causal_divergence"
    assert "skjult" in hyp["statement"]


def test_tick_registers_both_convergence_and_divergence(isolated_runtime):
    _seed_edges(isolated_runtime, [
        ("memory.recall_fail", "somatic.stress", 4, "inferred-kind"),                  # konvergens
        ("decision.created", "behavioral_decision_review.kept", 3, "inferred-kind"),   # divergens (kept
        ("decision.created", "behavioral_decision_review.broken", 3, "inferred-kind"), #  + broken)
    ])
    res = gen.run_hypothesis_generation_tick()
    assert res["status"] == "ok"
    assert res["divergence"] >= 1 and res["registered"] >= 2
    statements = " ".join(h["statement"] for h in gen.list_active_hypotheses(limit=10))
    assert "skjult" in statements       # divergens-hypotesen er registreret


def test_stance_divergence_becomes_hypothesis(isolated_runtime, monkeypatch):
    """Lag 3 v3: gentagen tvær-modal uenighed → governed divergens-hypotese."""
    monkeypatch.setattr(gen, "detect_causal_convergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_outcome_divergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_stance_divergence_candidates",
                        lambda **k: [{"key": "gut:proceed|somatic:stress",
                                      "count": 5, "desc": "gut vil frem, men kroppen bremser"}])
    res = gen.run_hypothesis_generation_tick()
    assert res["divergence"] >= 1 and res["registered"] >= 1
    stmts = " ".join(h["statement"] for h in gen.list_active_hypotheses(limit=10))
    assert "UENIGE" in stmts and "kroppen bremser" in stmts


def test_prediction_error_surprise_becomes_hypothesis(isolated_runtime, monkeypatch):
    """Tråd 4-bro (§6): en overraskelse fra sekvens-modellen → governed prediction_error-hypotese,
    fuldt pre-registreret + notation via lexicon (runtime→cost er bundne familier)."""
    monkeypatch.setattr(gen, "detect_causal_convergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_outcome_divergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_stance_divergence_candidates", lambda **k: [])
    monkeypatch.setattr(gen, "detect_prediction_error_candidates",
                        lambda: [{"from_family": "memory", "to_family": "somatic",
                                  "prob": 0.01, "from_total": 101, "cursor": 42}])
    res = gen.run_hypothesis_generation_tick()
    assert res["registered"] >= 1
    active = gen.list_active_hypotheses(limit=10)
    perr = [h for h in active if "overrasket" in h["statement"]]
    assert perr, "prediction_error-hypotese blev ikke registreret"
    # provenance-mekanisme + notation sat korrekt → sampleren kan finde test-stien
    import json as _json
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute("SELECT source, provenance_json, notation_il FROM central_hypotheses "
                        "WHERE source='prediction_error'").fetchone()
    prov = _json.loads(row["provenance_json"] or "{}")
    assert prov.get("mechanism") == "prediction_error" and prov.get("family") == "memory->somatic"
    # memory→somatic er bundne (kontinuitet, krop) → rendret via lexicon med stød-operatoren
    assert row["notation_il"] and "!" in row["notation_il"]


def test_awareness_surface_shows_generated_hypotheses(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    txt = gen.format_governed_hypotheses_for_awareness()
    assert txt and "memory" in txt and "jordede samples" in txt
    # tom tilstand → None (ingen støj i prompten)
    from core.runtime.db import connect
    with connect() as c:
        c.execute("DELETE FROM central_hypotheses")
        c.commit()
    assert gen.format_governed_hypotheses_for_awareness() is None


def test_self_triggered_confirmation_quarantined(isolated_runtime):
    _seed_edges(isolated_runtime, [("memory.recall_fail", "somatic.stress", 4, "inferred-kind")])
    gen.run_hypothesis_generation_tick()
    hyp_id = gen.list_active_hypotheses()[0]["hyp_id"]
    # bekræftelse hvor triggered_by == hyp_id (selv-opfyldende) → karantæne
    out = gen.record_governed_sample(hyp_id, supports=True, source="run_outcome",
                                     ground_ref="run-x", triggered_by=hyp_id)
    assert out["hyp_status"] == "quarantined"
