"""Investigation 14: why weighting loses, and why the quoted number moves.

The experiment's value rests on four properties that can each be lost silently:

1. **The identity must hold.** ``err == |sum w a|`` recomposed from the stored
   weight vector and error directions. Residual 0.0. A tautological check
   (``err == |err|``) would be zero by construction and is not used.

2. **The error must be read from the real predictions.** If ``a`` comes from the
   constructed predictions, the outcome cancels out and the error measures the
   imposed gap instead. Investigation 12 established this; a mutation restores
   the bug and must be caught.

3. **The hard argmax must reproduce ``err_selected`` exactly.** A finite alpha
   only approaches it — checking at alpha = 50 fails for arithmetic reasons and
   would tell us nothing about whether the reading is right.

4. **The falsified sub-prediction stays in the result.** The registered
   prediction was that the month-level median would be *lower* than the
   cell-level median. It is higher. That is part of the answer, not a number to
   be quietly dropped, and the verdict must name it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from feltteori_research.experiment_014_weight_penalty import (
    METHOD_VERSION,
    _argmax_weights,
    _sharpen,
    accumulate,
)

ARTIFACT = (
    Path(__file__).resolve().parents[1]
    / "artifacts/exp_014_weight_penalty/run_20261125_v2/results.json"
)


@pytest.fixture(scope="module")
def results() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_identiteten_holder(results: dict) -> None:
    """``err`` and ``recomposed`` are two routes to the same number."""
    assert results["controls"]["identity_holds"] is True
    assert results["controls"]["identity_worst_residual"] == 0.0


def test_den_haarde_argmax_giver_praecis_valget(results: dict) -> None:
    """The alpha -> infinity limit is selection, and it must be exact."""
    assert results["controls"]["alpha_converges_to_selection"] is True
    assert results["controls"]["alpha_worst_gap"] == 0.0


def test_argumentet_i_protokollen_er_ikke_tautologisk() -> None:
    """A hand-built row where the answer is known, so the identity can fail.

    Three experts with errors -3, 0, +3 around the outcome. Uniform weights give
    a weighted sum of exactly 0, which is NOT the same as the oracle's 0 — the
    oracle here is the middle expert. A reading of ``a`` from the constructed
    predictions would give a gap-driven number instead.
    """
    experts = ("a", "b", "c")
    prepared = [
        {
            "date": "2026-01-01",
            "period": "evaluation",
            "outcome": 10.0,
            "real": {"a": 7.0, "b": 10.0, "c": 13.0},
            "losses": {"a": 0.1, "b": 0.2, "c": 0.3},
            "l_best": 0.0,
            "scale": 11.0,
            "sign": {"a": 1.0, "b": 1.0, "c": 1.0},
        }
    ]
    orders = [["a", "b", "c"]]
    points = accumulate(prepared, orders, experts, 0.9, 0.5)
    point = points[0]

    assert point["err"] == point["recomposed"]
    assert point["err_oracle"] == pytest.approx(0.0)
    # The weights are uniform on the first month, so the errors cancel exactly.
    assert point["err"] == pytest.approx(0.0)
    # And the terms really do point in opposite directions.
    assert point["rest_same_sign"] is False


def test_den_haarde_argmax_laegger_al_masse_paa_en() -> None:
    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    hard = _argmax_weights(weights)
    assert hard == {"a": 1.0, "b": 0.0, "c": 0.0}


def test_skarpning_bevarer_summen() -> None:
    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    for alpha in (1.0, 2.0, 5.0):
        sharp = _sharpen(weights, alpha)
        assert sum(sharp.values()) == pytest.approx(1.0)
        assert sharp["a"] >= sharp["b"] >= sharp["c"]


def test_tabet_er_monotont_i_koncentrationen(results: dict) -> None:
    """The whole point: a concentrated weight costs almost nothing."""
    concentration = results["concentration"]
    ratios = [entry["median_ratio"] for entry in concentration]
    assert ratios == sorted(ratios, reverse=True), ratios
    assert concentration[-1]["median_ratio"] < 1.01
    assert concentration[0]["median_ratio"] > 2.0


def test_restmassen_baerer_tabet(results: dict) -> None:
    """Same-sign months carry the loss; opposite-sign months cancel it."""
    residual = results["residual"]
    assert residual["same_sign_share"] > 0.70
    assert residual["same_sign_median"] > residual["opposite_sign_median"] + 0.10
    assert residual["opposite_sign_median"] == pytest.approx(1.0)


def test_det_er_ikke_opvarmning(results: dict) -> None:
    assert results["warm_up_spread"] < 0.15
    ratios = [band["median_ratio"] for band in results["warm_up"]]
    assert min(ratios) > 1.15, ratios


def test_middelet_har_et_indre_minimum(results: dict) -> None:
    """A sharpened weight beats both the learned weight and pure selection."""
    curve = results["alpha_curve"]
    means = {entry["alpha"]: entry["mean_ratio"] for entry in curve}
    best = min(means, key=lambda alpha: means[alpha])
    assert 1.0 < best < 50.0, best
    assert means[best] < means[1.0]
    assert means[best] < results["selection_mean_ratio"]
    # The median, by contrast, falls monotonically toward 1.00.
    medians = [entry["median_ratio"] for entry in curve]
    assert medians == sorted(medians, reverse=True), medians


def test_den_falsificerede_delforudsigelse_staar_i_resultatet(results: dict) -> None:
    """The registered prediction about the aggregate fell, and the verdict says so."""
    aggregate = results["aggregate"]
    # The prediction was month_median < cell_median. It is the other way round.
    assert aggregate["month_median"] > aggregate["cell_median"]
    assert results["conditions"]["1_aggregate_matters"] is False
    assert results["conditions_failed"] == ["1_aggregate_matters"]
    # The real aggregate effect is mean against median, not cell against month.
    assert aggregate["month_mean"] > 5.0 * aggregate["month_median"]
    assert results["verdict"] == "allocation_holds_aggregate_prediction_fell"


def test_metodeversionen_er_sat(results: dict) -> None:
    assert results["method_version"] == METHOD_VERSION


def test_err_selected_laeses_fra_vaegtens_egen_top() -> None:
    """``err_selected`` is the error of the expert the WEIGHT prefers.

    The frozen artifact cannot catch a code mutation, so this test calls
    ``accumulate`` directly on a row where the weight's top expert is neither the
    best nor the worst: reading ``min`` or ``max`` instead of ``top`` changes the
    answer. First month, uniform weights, so ``top`` is the first expert.
    """
    experts = ("a", "b", "c")
    prepared = [
        {
            "date": "2026-01-01",
            "period": "evaluation",
            "outcome": 10.0,
            "real": {"a": 15.0, "b": 20.0, "c": 9.0},
            "losses": {"a": 0.1, "b": 0.2, "c": 0.3},
            "l_best": 0.0,
            "scale": 11.0,
            "sign": {"a": 1.0, "b": 1.0, "c": 1.0},
        }
    ]
    point = accumulate(prepared, [["a", "b", "c"]], experts, 0.9, 0.5)[0]

    # Errors are +5, +10, -1; the uniform weight's top is "a".
    assert point["top"] == "a"
    assert point["err_selected"] == pytest.approx(5.0)
    assert point["err_selected"] != pytest.approx(10.0)  # not the worst
    assert point["err_selected"] != pytest.approx(1.0)  # not the best
    assert point["err_oracle"] == pytest.approx(1.0)
