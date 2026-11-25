"""Investigation 13: the regime where retention has a reliable sign.

The experiment's value rests on six properties that can each be lost silently:

1. **The identity must hold.** ``error == |sum w a|``, recomposed from the stored
   weight vector and error directions. An earlier draft compared ``err`` with
   ``|err|`` — zero by construction, a control that cannot fail.
2. **The retraction must stay measured.** Investigation 12 claimed the ensemble
   never beats the oracle "as the arithmetic of a convex combination requires".
   That was wrong: the correct inequality is ``|sum w a| <= sum w |a|``, an upper
   bound with no lower bound. The test asserts the ensemble *does* beat the oracle
   in some months, so the retraction cannot quietly revert to the old claim.
3. **The cross share must have a positive denominator.** An earlier probe divided
   by ``(sum w a)^2``, which can be near zero, and produced -972 570. The test
   pins the decomposition arithmetic against a hand-built row.
4. **The regime must not be regression to the mean.** Split-half across months
   that share nothing is compared with the same-half correlation. If the effect
   were mean reversion, the same-half number would be the larger one.
5. **The ex ante answer must stay negative.** The best predictor available before
   the outcome explains less than the ex post one — otherwise the headline is
   wrong, not merely weak.
6. **The failed hold-out must stay in the result.** It failed for top-expert
   stability; a report that drops it is not this experiment.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

RUN = (
    Path(__file__).resolve().parents[1]
    / "artifacts/exp_013_retention_sign/run_20261125_v2/results.json"
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
    assert controls["cells_total"] == 60, controls
    assert controls["months_total"] > 0, controls


def test_verdict_er_det_naaede_og_ikke_en_fejlende_kontrol(results: dict) -> None:
    """Every condition is phrased as the property that must hold.

    Investigation 12 lost a verdict to a negatively phrased condition among
    success conditions. The string and the polarity are pinned here.
    """
    conditions = results["conditions_fired"]
    assert all(conditions.values()), conditions
    assert results["verdict"] == "regime_exists_but_requires_the_outcome"
    assert "control_failed" not in results["verdict"]
    assert conditions["6_no_ex_ante_regime"] is True


def test_ensemblet_KAN_slaa_oracle(results: dict) -> None:
    """The retraction, kept measured rather than merely stated.

    ``|sum w a| <= sum w |a|`` is an upper bound. It gives no lower bound, so an
    ensemble can beat every member when the errors point in opposite directions.
    """
    controls = results["controls"]
    assert controls["months_ensemble_beats_oracle"] > 0, controls
    assert controls["months_total"] == 19170, controls
    # And when it loses, it can lose badly — the bound is one-sided.
    assert controls["worst_error_over_oracle"] > 100.0, controls


def test_eksperterne_forstaerker_hinanden(results: dict) -> None:
    """The measured reason the ensemble rarely wins: a positive cross term."""
    controls = results["controls"]
    assert controls["cross_share_median"] > 0.0, controls
    assert controls["cells_where_experts_amplify"] >= 54, controls
    assert controls["amplify_share"] >= results["thresholds"]["amplify_share"], controls


def test_krydsleddet_er_aritmetisk_korrekt() -> None:
    """``(sum w a)^2 == sum w^2 a^2 + 2 sum_{i<j} w_i w_j a_i a_j``.

    Built by hand so the identity is checked against arithmetic and not against
    another copy of the implementation. The denominator is the diagonal term,
    which is strictly positive — dividing by ``(sum w a)^2`` is what produced
    -972 570 in an earlier probe.
    """
    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    errors = {"a": 2.0, "b": -3.0, "c": 5.0}
    signed = sum(weights[k] * errors[k] for k in weights)
    diagonal = sum(weights[k] ** 2 * errors[k] ** 2 for k in weights)
    cross = 2.0 * (
        weights["a"] * weights["b"] * errors["a"] * errors["b"]
        + weights["a"] * weights["c"] * errors["a"] * errors["c"]
        + weights["b"] * weights["c"] * errors["b"] * errors["c"]
    )
    assert math.isclose(signed**2, diagonal + cross, rel_tol=1e-12, abs_tol=1e-12)
    # Here the errors point in different directions and the cross term is
    # negative — the case that lets an ensemble beat its best member.
    assert cross < 0.0
    assert abs(signed) < min(abs(v) for v in errors.values())


def test_regimet_er_ikke_regression_mod_middel(results: dict) -> None:
    """Split-half across months that share nothing beats the same-half number."""
    controls = results["controls"]
    same_half = controls["same_half_r2"]
    split_a = controls["split_half_r2_a"]
    split_b = controls["split_half_r2_b"]
    assert same_half is not None and split_a is not None and split_b is not None
    assert split_a >= results["thresholds"]["split_half_r2"], (split_a, controls)
    # If the effect were mean reversion inside one measurement, the same-half
    # correlation would be the larger one. It is not.
    assert split_a > same_half, (split_a, same_half)
    # And the effect is specific to the distance from the oracle, not to the
    # error level: the plain error correlation is markedly weaker.
    corr_ratio = results["regime"]["corr_ratio_d_err"]
    corr_level = controls["corr_error_level_d_err"]
    assert abs(corr_ratio) > abs(corr_level), (corr_ratio, corr_level)


def test_der_findes_ikke_et_ex_ante_regime(results: dict) -> None:
    """The operational answer is negative, and it is the headline."""
    regime = results["regime"]
    best = regime["best_ex_ante_r2"]
    ex_post = regime["r2_ratio_d_err"]
    assert best is not None and ex_post is not None
    assert best < results["thresholds"]["ex_ante_r2"], regime["ex_ante_r2"]
    assert ex_post > best, (ex_post, best)
    # The intuitive candidate — expert disagreement — is the emptiest of them.
    spread = regime["ex_ante_r2"]["exante_spread"]
    assert spread is not None and spread < 0.05, regime["ex_ante_r2"]


def test_det_fejlende_hold_out_staar_i_resultatet(results: dict) -> None:
    """Top-expert stability flips sign between the two sources. That failure is part of the result."""
    hold_out = results["controls"]["hold_out"]
    assert hold_out["sunspots_to_co2_top_stable"]["sign_preserved"] is False
    assert hold_out["co2_to_sunspots_top_stable"]["sign_preserved"] is False
    # The one candidate that does preserve sign is carried by three cells on one
    # side, which is not evidence of a regime.
    assert hold_out["sunspots_to_co2_top_shifts"]["test_n"] == 3


def test_retentionseffekten_rapporteres_ikke_ved_sit_middel(results: dict) -> None:
    """Median and mean disagree by two orders of magnitude; the count carries the sign."""
    regime = results["regime"]
    assert abs(regime["mean_d_err_all"]) > abs(regime["median_d_err_all"]) * 10
    assert 0 < regime["pairs_where_error_falls"] < regime["cells"]


# --- Code tests: these call the module, so a mutation in the arithmetic fails ---
#
# The tests above read a frozen artifact. Measured 2026-11-25: changing the cross
# share's denominator to ``(sum w a)^2`` — the exact error an earlier probe made —
# changed the module's verdict but every artifact test still passed, because they
# read a file rather than the code. These two close that hole.

import sys  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from feltteori_research.experiment_009_expert_set import EXPERT_SETS  # noqa: E402
from feltteori_research.experiment_010_rank_drift import _orders  # noqa: E402
from feltteori_research.experiment_013_retention_sign import (  # noqa: E402
    _accumulate,
)


def _hand_built_rows(experts: tuple[str, ...], retention: float = 0.9) -> list[dict]:
    """One evaluation month whose errors point in different directions.

    The offsets are chosen so the best single expert has a non-zero error — with
    symmetric offsets the middle expert lands on zero, ``oracle`` becomes 0 and
    the comparison "ensemble beats the oracle" is between two zeros and proves
    nothing. Here the errors are -4, +1, +4: the best expert is off by 1, the
    uniform ensemble is off by 1/3.
    """
    offsets = (-4.0, 1.0, 4.0)
    assert len(experts) == len(offsets), (experts, offsets)
    prepared = [
        {
            "date": "2026-01-01",
            "period": "evaluation",
            "outcome": 10.0,
            "real": {
                expert: 10.0 + offsets[index] for index, expert in enumerate(experts)
            },
            "losses": {expert: 0.1 * index for index, expert in enumerate(experts)},
            "l_best": 0.0,
            "scale": 11.0,
            "sign": {
                expert: (1.0 if index >= 1 else -1.0)
                for index, expert in enumerate(experts)
            },
        }
    ]
    orders = _orders(prepared, experts, "fixed")
    return _accumulate(prepared, orders, experts, retention, 0.2)


def test_krydsleds_andelen_bruger_diagonalen_som_naevner() -> None:
    """``cross_share == cross / diag``, computed independently.

    Dividing by ``(sum w a)^2`` instead makes the share explode whenever the
    ensemble error is near zero. That is division by nothing, and it is the one
    mistake that already cost a measurement in this investigation.
    """
    experts = EXPERT_SETS["original"]
    point = _hand_built_rows(experts)[0]
    assert point["diag"] > 0.0, point
    assert math.isclose(
        point["cross_share"], point["cross"] / point["diag"], rel_tol=1e-12
    ), point
    # The wrong denominator is a different number, so this assertion has teeth.
    if abs(point["signed"]) > 1e-9:
        wrong = point["cross"] / point["signed"] ** 2
        assert not math.isclose(point["cross_share"], wrong, rel_tol=1e-6)


def test_identiteten_binder_fejlen_til_de_aegte_praediktioner() -> None:
    """``err`` must come from ``real``, not from the constructed predictions.

    Investigation 12 showed the constructed prediction is ``outcome + imposed gap``,
    so reading the error from it measures the gap and not predictive skill. Here
    the decomposition ties ``signed`` to ``diag`` and ``cross`` independently, so
    a fault in any of them shows up. Measured 2026-11-25: sourcing ``signed`` from
    the constructed predictions instead of ``real`` fails this test.

    A redundant ``recomposed`` (a copy of ``err``) would *not* fail — both routes
    are arithmetically identical, so the identity cannot detect its own
    redundancy. That is a limit of the check, not a hole in the result.
    """
    experts = EXPERT_SETS["original"]
    point = _hand_built_rows(experts)[0]
    assert math.isclose(point["err"], abs(point["signed"]), rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(
        point["recomposed"], abs(point["signed"]), rel_tol=1e-12, abs_tol=1e-12
    )
    assert math.isclose(
        point["signed"] ** 2, point["diag"] + point["cross"], rel_tol=1e-12, abs_tol=1e-12
    )
    # The error directions really do disagree here, so the cross term is negative
    # and the ensemble beats the best single expert — the case Investigation 12
    # claimed was impossible.
    assert point["cross"] < 0.0
    assert point["err"] < point["oracle"]

