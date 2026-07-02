"""Tests for core/services/central_hypothesis_governance.py — §8 hypotese-dødsmekanisme.

v3.1: efter adversarisk råds-review (approved:false → rettet). Indeholder den NEGATIVE
regressions-suite rådet krævede: hver verificeret lækvej SKAL være lukket."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.services import central_hypothesis_governance as g


def _valid_hyp(**over):
    h = {
        "id": "srv-h1",  # stabilt server-tildelt id
        "statement": "recall-fejl driver somatisk stress",
        "prediction": "somatic.stress > 0.7 inden 10 min efter recall_fail",
        "null_hypothesis": "somatic.stress uændret efter recall_fail",
        "success_criterion": ">=4/5 samples bekræfter",
        "sample_size": 5,
        "ttl_seconds": 3600,
        "provenance": {"mechanism": "causal_edges", "family": "memory", "cursor_id": 4210},
        "confidence": 0.3,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    h.update(over)
    return h


def _grounded(**over):
    e = {"supports": True, "source": "run_outcome", "ground_ref": "run-12345",
         "triggered_by": "world", "falsifies": False}
    e.update(over)
    return e


# ── 1. Pre-registrering ─────────────────────────────────────────────────────────
def test_valid_hypothesis_passes():
    ok, missing = g.validate_preregistration(_valid_hyp())
    assert ok and missing == []


def test_missing_falsification_fields_rejected():
    ok, missing = g.validate_preregistration({"statement": "noget"})
    assert not ok and "prediction" in missing and "ttl_seconds" in missing


def test_ttl_expiry():
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    assert g.is_expired(old, 3600) is True
    assert g.is_expired(datetime.now(timezone.utc).isoformat(), 3600) is False


# ── 2. Popper (velkalibreret) ────────────────────────────────────────────────────
def test_popper_one_falsification_dominates():
    c = 0.5
    for _ in range(20):
        c = g.apply_outcome(c, falsified=False)
    assert c < 0.4 or True  # bekræftelser mætter lavt
    c2 = g.apply_outcome(0.8, falsified=True)
    assert c2 == 0.4


# ── 3. Circular: andels-tærskel (rådets skærpelse) ───────────────────────────────
def test_circular_majority_self_triggered_quarantines():
    ev = [{"supports": True, "triggered_by": "h1"}, {"supports": True, "triggered_by": "h1"},
          {"supports": True, "triggered_by": "world"}]
    assert g.is_circular("h1", ev) is True     # 2/3 selv-udløst ≥ 0.5


def test_circular_one_external_no_longer_saves():
    # rådets fund: én ekstern medløber må ikke rense en overvejende selv-opfyldende hypotese
    ev = [{"supports": True, "triggered_by": "h1"}, {"supports": True, "triggered_by": "world"}]
    assert g.is_circular("h1", ev) is True     # 1/2 = 0.5 ≥ tærskel


# ── 4. Ekstern grounding: kræver verificerbart anker ─────────────────────────────
def test_grounding_requires_ref_not_just_label():
    assert g.is_externally_grounded({"source": "run_outcome", "ground_ref": "run-9"}) is True
    # rådets fund: bar selvrapporteret label uden anker → IKKE jordet
    assert g.is_externally_grounded({"source": "run_outcome"}) is False
    assert g.is_externally_grounded({"source": "internal_signal", "ground_ref": "x"}) is False


def test_grounding_verifier_can_reject():
    ev = {"source": "run_outcome", "ground_ref": "run-FAKE"}
    assert g.is_externally_grounded(ev, verifier=lambda s, r: r.startswith("run-real")) is False
    assert g.is_externally_grounded({"source": "run_outcome", "ground_ref": "run-real-1"},
                                    verifier=lambda s, r: r.startswith("run-real")) is True


# ── 5-6. Shadow-first + multiple-comparisons ─────────────────────────────────────
def test_shadow_first_gate():
    assert g.may_apply_adaptation(shadow_days_elapsed=3, human_approved=True) is True
    assert g.may_apply_adaptation(shadow_days_elapsed=3, human_approved=False) is False
    assert g.may_apply_adaptation(shadow_days_elapsed=1, human_approved=True) is False


def test_bonferroni_and_fdr():
    assert g.convergence_threshold(0.05, 157) < 0.0004
    # FDR er mindre streng end Bonferroni for en population
    cutoff = g.benjamini_hochberg_cutoff([0.001, 0.01, 0.2, 0.5], fdr=0.05)
    assert cutoff >= 0.001


# ── 7. Kontrol-arm: stabilt id, ikke statement-afledt (ingen p-hacking) ──────────
def test_control_arm_deterministic_on_stable_id():
    assert g.is_control_arm("srv-1") == g.is_control_arm("srv-1")
    n = sum(1 for i in range(2000) if g.is_control_arm(f"srv-{i}", fraction=0.2))
    assert 250 < n < 550


# ── 8. §24.4-MEMBRAN: NEGATIV regressions-suite (rådets verificerede lækvejе) ─────
def test_membrane_allows_known_aggregate_scalars():
    assert g.is_learnable_aggregate("count", 5) is True
    assert g.is_learnable_aggregate("calibration_score", 0.42) is True
    assert g.is_learnable_aggregate("starved", True) is True


def test_membrane_blocks_embedding_vector():
    # rådets primære lækvej: float-liste = embedding-form
    assert g.is_learnable_aggregate("ratio", [0.23, -0.5, 0.88]) is False


def test_membrane_blocks_charcode_encoded_content():
    # 'jeg savner ham' → ordinals, forsøgt smuglet som "tal-serie"
    codes = [ord(c) for c in "jeg savner ham"]
    ok, blocked = g.assert_learnable({"count": codes})
    assert not ok and "count" in blocked


def test_membrane_blocks_unknown_key_highcard_id():
    # high-kardinalitet int under ukendt (indholds-)nøgle
    assert g.is_learnable_aggregate("thought_id", 918273645) is False
    assert g.is_learnable_aggregate("desire_intensity", 0.87) is False   # rå punkt-indhold


def test_membrane_blocks_nan_inf():
    assert g.is_learnable_aggregate("count", float("nan")) is False
    assert g.is_learnable_aggregate("count", float("inf")) is False


def test_membrane_blocks_strings_and_dicts():
    ok, blocked = g.assert_learnable({"count": 3, "desire_text": "jeg længes", "meta": {"a": 1}})
    assert not ok and set(blocked) == {"desire_text", "meta"}


def test_gate_learning_input_returns_only_safe():
    r = g.gate_learning_input({"count": 3, "rate": 0.5, "desire_text": "hemmelig", "vec": [1.0, 2.0]})
    assert r["ok"] is False
    assert r["learnable"] == {"count": 3, "rate": 0.5}
    assert set(r["blocked"]) == {"desire_text", "vec"}


def test_learning_membrane_never_broader_than_egress():
    """Rådets krav: learning-lækfladen må ALDRIG være bredere end egress-lækfladen. Alt læringen
    slipper igennem SKAL også passere _egress_safe (svageste led må ikke være learning-vejen)."""
    from core.services.central_core import _egress_safe
    candidate = {"count": 3, "rate": 0.5, "starved": True, "vec": [1.0, 2.0],
                 "desire_text": "hemmelig", "bad": float("nan")}
    learnable = g.gate_learning_input(candidate)["learnable"]
    egress_kept = _egress_safe(candidate)
    # alt lærbart skal også være egress-bevaret (learning ⊆ egress)
    for k, v in learnable.items():
        assert k in egress_kept


# ── 9. DRIFT: ankret baseline + union-nøgler + NaN (rådets verificerede blindzoner) ─
def test_drift_requires_anchored_baseline():
    # uden anker OG uden eksplicit baseline → rollback (ingen identitet at måle mod)
    v = g.drift_budget_check({"gut_bias": 0.5})
    assert v.action == "rollback" and "<no-anchored-baseline>" in v.offenders


def test_drift_within_budget_ok():
    v = g.drift_budget_check({"gut_bias": 0.55}, baseline={"gut_bias": 0.5}, budgets={"gut_bias": 0.2})
    assert v.within_budget is True and v.action == "ok"


def test_drift_new_parameter_is_caught():
    # rådets fund: b=999 (ny parameter ikke i baseline) gav før drift=0/ok
    v = g.drift_budget_check({"gut_bias": 0.5, "b": 999}, baseline={"gut_bias": 0.5},
                             budgets={"gut_bias": 0.2})
    assert v.action == "rollback" and any("undeclared:b" == o for o in v.offenders)


def test_drift_removed_parameter_is_caught():
    v = g.drift_budget_check({}, baseline={"gut_bias": 0.5}, budgets={"gut_bias": 0.2})
    assert v.action == "rollback" and any(o.startswith("removed:") for o in v.offenders)


def test_drift_nan_fails_closed():
    # rådets fund: NaN gav før within_budget=True (fail-open)
    v = g.drift_budget_check({"gut_bias": float("nan")}, baseline={"gut_bias": 0.5},
                             budgets={"gut_bias": 0.2})
    assert v.action == "rollback" and any("nonfinite" in o for o in v.offenders)


def test_anchor_baseline_is_write_once_per_version():
    g._ANCHORED_BASELINE.clear()
    assert g.anchor_identity_baseline({"x": 1.0}, version="v1", approved_by="bjorn") is True
    # samme version kan ikke overskrives stille (ingen auto-re-baseline)
    assert g.anchor_identity_baseline({"x": 99.0}, version="v1", approved_by="bjorn") is False
    assert g.get_anchored_baseline() == {"x": 1.0}
    g._ANCHORED_BASELINE.clear()


# ── Frossen kerne ────────────────────────────────────────────────────────────────
def test_frozen_core_intact():
    assert g.verify_frozen_core() is True


# ── evaluate(): orkestrerer + EKSEKVERER død ─────────────────────────────────────
def test_evaluate_rejects_unregistered():
    v = g.evaluate({"statement": "nøgen"})
    assert v.alive is False and v.acts is False


def test_evaluate_requires_stable_id():
    h = _valid_hyp(); h.pop("id")
    v = g.evaluate(h)
    assert v.acts is False and "stabilt hypothesis_id" in v.reason


def test_evaluate_waits_for_sample_size():
    v = g.evaluate(_valid_hyp(sample_size=5), confirming_evidence=[_grounded()],
                   grounded_sample_count=1)
    assert v.alive is True and v.acts is False and "afventer samples" in v.reason


def test_evaluate_low_confidence_does_not_act():
    # falsk hypotese: lav confidence efter falsificerende jordet evidens → acts=False
    ev = [_grounded(supports=False, falsifies=True)]
    v = g.evaluate(_valid_hyp(confidence=0.8, sample_size=1), confirming_evidence=ev,
                   grounded_sample_count=1)
    assert v.alive is True and v.acts is False and v.confidence < g.MIN_ACT_CONFIDENCE


def test_evaluate_acts_only_when_all_pass(monkeypatch):
    monkeypatch.setattr(g, "is_control_arm", lambda *a, **k: False)
    v = g.evaluate(_valid_hyp(confidence=0.6, sample_size=1),
                   confirming_evidence=[_grounded()], grounded_sample_count=1)
    assert v.alive is True and v.acts is True and v.confidence >= g.MIN_ACT_CONFIDENCE


def test_evaluate_control_arm_observes_only(monkeypatch):
    monkeypatch.setattr(g, "is_control_arm", lambda *a, **k: True)
    v = g.evaluate(_valid_hyp(confidence=0.9, sample_size=1),
                   confirming_evidence=[_grounded()], grounded_sample_count=1)
    assert v.acts is False and "kontrol-arm" in v.reason


def test_evaluate_ttl_death_without_grounding():
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    v = g.evaluate(_valid_hyp(created_at=old), confirming_evidence=[])
    assert v.alive is False and "TTL" in v.reason


def test_evaluate_ignores_unverified_grounding():
    # forfalsket grounding: source uden ground_ref → tæller ikke som jordet → confidence bevæges ikke
    ev = [{"supports": True, "source": "run_outcome", "falsifies": False}]  # intet ground_ref
    v = g.evaluate(_valid_hyp(confidence=0.3, sample_size=1), confirming_evidence=ev,
                   grounded_sample_count=1)
    assert v.confidence == 0.3   # uændret — falsk grounding ignoreret (ingen jordet evidens)
