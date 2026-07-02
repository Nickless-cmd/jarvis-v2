"""Tests for core/services/central_model_meta.py — Tråd 1: Centralen kender sit eget hardware."""
from __future__ import annotations

import pytest

from core.services import central_model_meta as mm


def _seed_runs(rows):
    """rows: (run_id, provider, model, status, started, finished)."""
    from core.runtime.db import connect
    with connect() as c:
        for rid, prov, model, status, st, fi in rows:
            c.execute(
                "INSERT INTO visible_runs (run_id, lane, provider, model, status, started_at, "
                "finished_at) VALUES (?,?,?,?,?,?,?)",
                (rid, "visible", prov, model, status, st, fi))
        c.commit()


def _fast_slow(isolated_runtime, n=20):
    """Model A (fast/dsk) ~1s runs; Model B (slow/glm) ~3s runs — ægte latency-kontrast."""
    rows = []
    for i in range(n):
        rows.append((f"a{i}", "dsk", "flash", "completed",
                     "2026-07-02T10:00:00+00:00", "2026-07-02T10:00:01+00:00"))
        rows.append((f"b{i}", "glm", "big", "completed",
                     "2026-07-02T10:00:00+00:00", "2026-07-02T10:00:03+00:00"))
    _seed_runs(rows)


def test_aggregate_computes_latency_and_success(isolated_runtime):
    _fast_slow(isolated_runtime, n=20)
    agg = mm.aggregate_model_outcomes()
    assert agg["dsk/flash"]["latency_ms"] == pytest.approx(1000.0)
    assert agg["glm/big"]["latency_ms"] == pytest.approx(3000.0)
    assert agg["dsk/flash"]["success_rate"] == 1.0


def test_observe_writes_timeseries(isolated_runtime):
    _fast_slow(isolated_runtime, n=16)
    n = mm.observe_model_outcomes()
    assert n >= 2
    from core.services import central_timeseries as ts
    samples = ts.recent("system", "model_outcome:dsk/flash", limit=5)
    assert samples and samples[-1].meta.get("duration_ms") == pytest.approx(1000.0)


def test_detect_latency_contrast(isolated_runtime):
    _fast_slow(isolated_runtime, n=20)
    cands = mm.detect_model_meta_candidates()
    lat = [c for c in cands if c["metric"] == "latency"]
    assert lat and lat[0]["winner"] == "dsk/flash" and lat[0]["loser"] == "glm/big"


def test_no_contrast_below_min_samples(isolated_runtime):
    _fast_slow(isolated_runtime, n=5)   # 5 < _MIN_SAMPLES
    assert mm.detect_model_meta_candidates() == []


def test_tick_registers_governed_hypothesis(isolated_runtime):
    _fast_slow(isolated_runtime, n=20)
    res = mm.run_model_meta_tick()
    assert res["models_observed"] >= 2 and res["hypotheses_registered"] >= 1
    from core.services import central_hypothesis_generator as gen
    stmts = " ".join(h["statement"] for h in gen.list_active_hypotheses(limit=10))
    assert "dsk/flash" in stmts and "bedre end" in stmts


def test_persistence_test_holds_then_falsifies(isolated_runtime):
    _fast_slow(isolated_runtime, n=20)
    fam = "latency:dsk/flash>glm/big"
    res = mm.test_model_meta_persistence(fam)
    assert res and res["supports"] is True
    # nu vender billedet: glm bliver lynhurtig (0ms) i volumen → dominansen kollapser → falsifies
    _seed_runs([(f"c{i}", "glm", "big", "completed",
                 "2026-07-02T11:00:00+00:00", "2026-07-02T11:00:00+00:00") for i in range(60)])
    res2 = mm.test_model_meta_persistence(fam)
    assert res2 and res2["falsifies"] is True


def test_sampler_routes_model_meta(isolated_runtime):
    """§8.4: sampleren finder test-stien for en registreret model_meta-hypotese og jorder et sample."""
    _fast_slow(isolated_runtime, n=20)
    mm.run_model_meta_tick()
    from core.services import central_hypothesis_sampler as smp
    out = smp.run_hypothesis_sampler_tick()
    assert out["tested"] >= 1


def test_surface_lists_known_models(isolated_runtime):
    _fast_slow(isolated_runtime, n=16)
    surf = mm.build_model_meta_surface()
    assert surf["active"] is True and surf["models_known"] >= 2


def test_self_safe_on_empty(isolated_runtime):
    assert mm.aggregate_model_outcomes() == {}
    assert mm.observe_model_outcomes() == 0
    assert mm.detect_model_meta_candidates() == []
    assert mm.run_model_meta_tick()["status"] == "ok"
