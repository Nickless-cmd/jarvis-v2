"""Tests for core/services/central_adaptation.py — Lag 4 c→d-lukning (shadow-first, reversibel)."""
from __future__ import annotations

import pytest

from core.services import central_adaptation as ad
from core.services import central_hypothesis_governance as gov


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    gov._ANCHORED_BASELINE.clear()
    ad._kv_set(ad._BIAS_KEY, 0.0)
    ad._kv_set(ad._LIVE_FLAG, False)
    ad._kv_set(ad._PAUSE_KEY, False)
    yield


def _seed_resolved(supported: int, contradicted: int):
    from core.services import central_hypothesis_generator as gen
    from core.runtime.db import connect
    gen.ensure_schema()
    with connect() as c:
        i = 0
        for outcome, n in (("supported", supported), ("contradicted", contradicted)):
            for _ in range(n):
                i += 1
                c.execute(
                    "INSERT INTO central_hypotheses (hyp_id, source, statement, prediction, "
                    "null_hypothesis, success_criterion, sample_size, ttl_seconds, provenance_json, "
                    "confidence, status, outcome, grounded_samples, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?, 'resolved', ?, 5, '2026-07-02T00:00:00Z')",
                    (f"h{i}", "causal_convergence", "s", "p", "n", "sc", 5, 3600, "{}", 0.5, outcome))
        c.commit()


def test_shadow_never_applies_without_live_flag():
    _seed_resolved(supported=8, contradicted=2)   # accuracy 0.8 → foreslå +bias
    res = ad.run_adaptation_tick()
    assert res["mode"] == "shadow"
    assert res["applied"] is False
    assert res["proposed_bias"] > 0            # DER ER et forslag
    assert ad.get_gut_bias() == 0.0            # men INTET ændret (shadow)


def test_too_few_resolved_proposes_zero():
    _seed_resolved(supported=2, contradicted=1)   # < _MIN_RESOLVED
    p = ad.compute_proposed_bias()
    assert p["enough"] is False and p["proposed"] == 0.0


def test_live_flag_applies_bounded_bias():
    _seed_resolved(supported=8, contradicted=2)   # accuracy 0.8 → (0.8-0.5)*0.5 = 0.15
    ad._kv_set(ad._LIVE_FLAG, True)
    res = ad.run_adaptation_tick()
    assert res["mode"] == "live" and res["applied"] is True
    assert ad.get_gut_bias() == 0.15
    # snapshot til rollback gemt
    assert float(ad._kv_get(ad._PREV_KEY, None)) == 0.0


def test_low_accuracy_gives_caution_bias():
    _seed_resolved(supported=1, contradicted=9)   # accuracy 0.1 → (0.1-0.5)*0.5 = -0.2
    ad._kv_set(ad._LIVE_FLAG, True)
    ad.run_adaptation_tick()
    assert ad.get_gut_bias() == -0.2


def test_drift_over_budget_rolls_back_and_pauses(monkeypatch):
    # tving et forslag der overskrider drift-budgettet → rollback + pause
    monkeypatch.setattr(ad, "compute_proposed_bias",
                        lambda: {"proposed": 0.9, "accuracy": 1.0, "resolved": 10, "enough": True})
    ad._kv_set(ad._BIAS_KEY, 0.1)
    ad._kv_set(ad._LIVE_FLAG, True)
    res = ad.run_adaptation_tick()
    assert res["gate"] == "rollback"
    assert ad.is_paused() is True              # kill-switch slået til
    assert ad.get_gut_bias() == 0.0            # gendannet til forrige (prev default 0.0)


def test_paused_blocks_live_apply():
    _seed_resolved(supported=8, contradicted=2)
    ad._kv_set(ad._LIVE_FLAG, True)
    ad._kv_set(ad._PAUSE_KEY, True)            # paused
    res = ad.run_adaptation_tick()
    assert res["mode"] == "shadow"             # paused → ikke live
    assert res["applied"] is False and ad.get_gut_bias() == 0.0


def test_gut_engine_reads_bias_default_zero_no_change():
    # med bias=0 (shadow) ændrer gut_engine sig ikke
    from core.services.gut_engine import derive_gut_signal
    out = derive_gut_signal(task_description="x", confidence=0.8, recent_success_count=6)
    assert out["hunch"] == "proceed" and 0.0 <= float(out["confidence"]) <= 1.0
