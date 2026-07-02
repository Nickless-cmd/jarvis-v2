"""Tests for core/services/central_hypothesis_governance.py — §8 hypotese-dødsmekanisme.

Dette er de ufravigelige værn FØR Lag 3. Testes hårdt: uden dem er Lag 3+4 en
confirmation-bias-maskine (rådets kerne-frygt)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.services import central_hypothesis_governance as g


def _valid_hyp(**over):
    h = {
        "id": "h1",
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


# ── 1. Pre-registrering ─────────────────────────────────────────────────────────
def test_valid_hypothesis_passes():
    ok, missing = g.validate_preregistration(_valid_hyp())
    assert ok and missing == []


def test_missing_falsification_fields_rejected():
    ok, missing = g.validate_preregistration({"statement": "noget"})
    assert not ok
    assert "prediction" in missing and "null_hypothesis" in missing and "ttl_seconds" in missing


def test_bad_sample_size_and_provenance_rejected():
    ok, missing = g.validate_preregistration(_valid_hyp(sample_size=0, provenance={"mechanism": "x"}))
    assert not ok and "sample_size" in missing and "provenance" in missing


def test_ttl_expiry():
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    assert g.is_expired(old, 3600) is True
    fresh = datetime.now(timezone.utc).isoformat()
    assert g.is_expired(fresh, 3600) is False


# ── 2. Popper-asymmetri ─────────────────────────────────────────────────────────
def test_popper_falsification_is_aggressive():
    assert g.apply_outcome(0.8, falsified=True) == 0.4          # halveret (down_rate 0.5)


def test_popper_confirmation_is_slow_and_saturating():
    up = g.apply_outcome(0.8, falsified=False)
    assert 0.8 < up < 0.82                                       # kun lille løft
    # aldrig til 1.0 uanset hvor mange bekræftelser
    c = 0.5
    for _ in range(1000):
        c = g.apply_outcome(c, falsified=False)
    assert c < 1.0


def test_one_falsification_undoes_many_confirmations():
    c = 0.5
    for _ in range(10):
        c = g.apply_outcome(c, falsified=False)
    before = c
    c = g.apply_outcome(c, falsified=True)
    assert c < before * 0.6                                      # én modsigelse dominerer


# ── 3. Circular-karantæne ───────────────────────────────────────────────────────
def test_self_triggered_confirmation_is_circular():
    ev = [{"supports": True, "triggered_by": "h1"}, {"supports": True, "triggered_by": "h1"}]
    assert g.is_circular("h1", ev) is True


def test_externally_triggered_confirmation_not_circular():
    ev = [{"supports": True, "triggered_by": "h1"}, {"supports": True, "triggered_by": "world"}]
    assert g.is_circular("h1", ev) is False


# ── 4. Ekstern grounding ────────────────────────────────────────────────────────
def test_grounding_gate():
    assert g.is_externally_grounded({"source": "run_outcome"}) is True
    assert g.is_externally_grounded({"source": "internal_signal"}) is False


# ── 5. Shadow-first ─────────────────────────────────────────────────────────────
def test_shadow_first_gate():
    assert g.may_apply_adaptation(shadow_days_elapsed=3, human_approved=True) is True
    assert g.may_apply_adaptation(shadow_days_elapsed=3, human_approved=False) is False   # ingen godkendelse
    assert g.may_apply_adaptation(shadow_days_elapsed=1, human_approved=True) is False    # for kort skygge


# ── 6. Multiple-comparisons ─────────────────────────────────────────────────────
def test_bonferroni_tightens_threshold():
    assert g.convergence_threshold(0.05, 1) == 0.05
    assert g.convergence_threshold(0.05, 157) < 0.0004


# ── 7. Kontrol-arm ──────────────────────────────────────────────────────────────
def test_control_arm_is_deterministic_and_partial():
    # deterministisk: samme id → samme svar
    assert g.is_control_arm("h1") == g.is_control_arm("h1")
    # ~fraction af mange id'er havner i kontrol-armen
    n = sum(1 for i in range(2000) if g.is_control_arm(f"h{i}", fraction=0.2))
    assert 250 < n < 550                                        # ~20% ± tolerance


# ── Samlet dom ──────────────────────────────────────────────────────────────────
def test_evaluate_rejects_unregistered():
    v = g.evaluate({"statement": "nøgen hypotese"})
    assert v.alive is False and v.acts is False and "ikke-preregistreret" in v.reason


def test_evaluate_dead_on_ttl_without_grounding():
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    v = g.evaluate(_valid_hyp(created_at=old), confirming_evidence=[])
    assert v.alive is False and "TTL" in v.reason


def test_evaluate_quarantines_circular():
    ev = [{"supports": True, "triggered_by": "h1", "source": "run_outcome"}]
    v = g.evaluate(_valid_hyp(), confirming_evidence=ev)
    assert v.quarantined is True and v.acts is False


def test_evaluate_only_grounded_evidence_moves_confidence():
    ev = [
        {"supports": True, "source": "internal_signal", "triggered_by": "world"},  # ignoreres
        {"supports": True, "source": "run_outcome", "triggered_by": "world", "falsifies": False},
    ]
    v = g.evaluate(_valid_hyp(confidence=0.3), confirming_evidence=ev)
    assert v.alive is True
    # kun det jordede sample løftede confidence en smule over 0.3
    assert 0.3 < v.confidence < 0.35


def test_evaluate_falsifying_evidence_kills_confidence():
    ev = [{"supports": False, "source": "run_outcome", "triggered_by": "world", "falsifies": True}]
    v = g.evaluate(_valid_hyp(confidence=0.8), confirming_evidence=ev)
    assert v.confidence <= 0.4
