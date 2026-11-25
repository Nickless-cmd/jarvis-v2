"""Investigation 12: the path from retention to the forecast, and how much is structure.

The experiment's value rests on five properties that can each be lost silently:

1. **The identity must hold.** ``error == |sum w a|`` is arithmetic. If it breaks,
   the ensemble is no longer the weighted mean of its members and every number in
   the report is about a different object.
2. **The verdict must be reachable.** Condition 1 was first written as a fault
   condition among four success conditions, so ``all()`` could never be true and
   the verdict fell through to "a control failed" while every condition was met.
   The test pins the reachable verdict string so a future rename cannot silently
   disable it again.
3. **The constructed MAE must not be read as a forecast.** It is monotone in
   ``gap`` by construction in every group; the true error only by chance. Both
   shares are asserted so the two quantities cannot merge a second time.
4. **The concentration effect must survive dropping its most reactive set.** The
   largest error changes cluster in ``long_memory``.
5. **The retention effect must not be reported by its mean.** The median change is
   -0.005 and the mean -0.690; the sign is counted, and 34 of 60 is not a sign.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RUN = (
    Path(__file__).resolve().parents[1]
    / "artifacts/exp_012_forecast_path/run_20261125_v3/results.json"
)


@pytest.fixture(scope="module")
def results() -> dict:
    if not RUN.exists():
        pytest.skip(f"preserved run not present: {RUN}")
    return json.loads(RUN.read_text(encoding="utf-8"))


def test_kontrollerne_bestaar(results: dict) -> None:
    """No number may carry a verdict unless every control passed."""
    controls = results["controls"]
    assert controls["identity_holds"] is True, controls
    assert controls["identity_worst_residual"] == 0.0, controls
    assert controls["constructed_mae_monotone_in_gap"] is True, controls
    assert controls["true_error_groups"] == 20, controls


def test_verdict_er_det_naaede_og_ikke_en_fejlende_kontrol(results: dict) -> None:
    """Condition 1 was a fault condition among success conditions, so `all()` never held.

    Measured 2026-11-25: all five conditions were met while the verdict said
    "a control failed". The string is pinned here so the naming cannot silently
    turn the logic off again.
    """
    conditions = results["conditions_fired"]
    assert all(conditions.values()), conditions
    assert results["verdict"] == "error_is_data_retention_path_is_concentration_without_sign"
    assert "control_failed" not in results["verdict"]
    assert "1_identity_does_not_hold" not in conditions
    assert conditions["1_identity_holds"] is True


def test_identiteten_holder_paa_hver_maalt_celle(results: dict) -> None:
    """``error == |sum_e w_e a_e|`` — the only channel retention can take."""
    assert results["controls"]["identity_worst_residual"] == 0.0
    # The identity is the reason the path is closed: `orders` does not depend on
    # retention and `a` is data, so `w` is the only route to the forecast.
    assert results["controls"]["identity_holds"] is True


def test_fejlen_er_data_ikke_struktur(results: dict) -> None:
    """The finding: the oracle error explains the level, the top weight does not."""
    variance = results["variance"]
    assert variance["r2_oracle"] > 0.90, variance["r2_oracle"]
    assert variance["r2_top_weight"] < 0.05, variance["r2_top_weight"]
    eta = variance["eta_squared"]
    # Source (which data) dominates; retention is negligible as a main effect.
    assert eta["source"] > 0.70, eta
    assert eta["retention"] < 0.01, eta
    assert eta["source"] > 100 * eta["retention"], eta


def test_den_konstruerede_mae_er_ikke_en_prognose(results: dict) -> None:
    """Monotone by construction in every group; the true error only by chance."""
    controls = results["controls"]
    assert controls["constructed_mae_monotone_in_gap"] is True
    share = controls["true_error_monotone_share"]
    chance = controls["chance_monotone_share_with_three_gaps"]
    assert share < chance, (share, chance)
    assert share < 0.25, share


def test_retention_har_ikke_et_paalideligt_fortegn(results: dict) -> None:
    """34 of 60 is not a sign, and the median is half a percent of the error level."""
    effect = results["retention_effect"]
    assert effect["pairs"] == 60
    fall = effect["pairs_where_error_falls"]
    assert 20 < fall < 40, fall
    # The mean is carried by a handful of large cases; the median is not.
    assert abs(effect["median_d_err"]) < 0.05, effect["median_d_err"]
    assert abs(effect["mean_d_err"]) > 10 * abs(effect["median_d_err"]), effect


def test_koncentrationseffekten_overlever_uden_peak_saettet(results: dict) -> None:
    """The largest changes cluster in long_memory, so the effect is re-measured without it."""
    effect = results["retention_effect"]
    assert effect["corr_d_top_weight_d_err"] < -0.30, effect
    assert effect["corr_without_peak_set"] < -0.25, effect
    # Direction survives; strength falls. That is the honest statement.
    assert abs(effect["r2_without_peak_set"]) < abs(effect["r2_d_top_weight_d_err"]), effect
    assert effect["r2_without_peak_set"] > 0.10, effect


def test_ensemblet_er_ringere_end_den_bedste_enkeltekspert(results: dict) -> None:
    """The gap retention closes a little: the ensemble averages a good expert away."""
    effect = results["retention_effect"]
    short = effect["median_ratio_error_over_oracle_short"]
    long = effect["median_ratio_error_over_oracle_long"]
    assert short > 1.0, short
    assert long < short, (long, short)
    # Concentration tracks the gap to the oracle — the one structural handle there is.
    assert effect["r2_top_weight_vs_ratio"] > 0.15, effect["r2_top_weight_vs_ratio"]


def test_akkumulationen_kan_ikke_laese_udfaldet_ud_af_fejlen() -> None:
    """Code-level guard: the ensemble error is the members' spread, not the imposed gap.

    If someone later replaced ``real`` with the constructed predictions, the
    "true error" would become a function of the imposed gap and this test's
    premise would be false. The first row has uniform weights (``retained`` starts
    at zero for every expert), so the error there must not move when the gap does.

    Constructed with ``a = 0, 3, 6`` deliberately — an earlier version used
    ``(index - 1) * 3``, which sums to zero for three experts and made the error
    0.0 for the wrong reason.
    """
    from feltteori_research.experiment_009_expert_set import EXPERT_SETS
    from feltteori_research.experiment_012_forecast_path import _accumulate
    from feltteori_research.experiment_010_rank_drift import _orders

    experts = EXPERT_SETS["original"]
    assert len(experts) == 3, experts
    prepared = [
        {
            "date": "2026-01-01",
            "period": "evaluation",
            "outcome": 10.0,
            "real": {e: 10.0 + index * 3.0 for index, e in enumerate(experts)},
            "losses": {e: 0.1 * index for index, e in enumerate(experts)},
            "l_best": 0.0,
            "scale": 11.0,
            "sign": {e: 1.0 for e in experts},
        }
    ]
    orders = _orders(prepared, experts, "fixed")

    errors = []
    for gap in (0.05, 0.2, 0.8):
        point = _accumulate(prepared, orders, experts, 0.9, gap)[0]
        recomposed = abs(sum(point["w"][e] * point["a"][e] for e in experts))
        assert point["err"] == pytest.approx(recomposed, abs=1e-12)
        # a = 0, 3, 6 with uniform weights 1/3 -> the error is exactly 3.0.
        assert point["err"] == pytest.approx(3.0, abs=1e-9)
        assert point["oracle"] == pytest.approx(0.0, abs=1e-12)
        errors.append(point["err"])

    # Uniform weights on the first row: the gap cannot reach the error there.
    assert errors[0] == pytest.approx(errors[1], abs=1e-12)
    assert errors[1] == pytest.approx(errors[2], abs=1e-12)
