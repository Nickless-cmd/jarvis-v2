"""Investigation 10: the roving threshold is not a function of the rank drift alone.

The experiment's value rests on three properties that can each be lost silently:

1. **The mechanism must not diverge.** This module prepares the per-row real
   losses once and passes an explicit rank order into the evaluation, where
   Investigation 9 recomputed them per call and derived the order inside. If the
   two paths disagree, every threshold below is a number about a different
   mechanism. Measured: bit-identical, difference 0.0.

2. **The formula must not carry a factor that only the grid can hide.** The first
   run of this experiment carried a spurious ``(N-1)`` in the threshold formula.
   The ``fixed`` cells sat at exactly half the predicted value on every source and
   every set — which is what exposed it. The tests below pin the formula at its
   measured value so that factor cannot come back unnoticed.

3. **The two-expert set must not be read as agreement.** Its floor is
   ``0.5 * 2 = 1.0``, the minimum attainable effective count, so the mechanism
   approaches it and never crosses it. Bisection saturates there and would
   otherwise return a finite number that reads like a prediction.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RUN = (
    Path(__file__).resolve().parents[1]
    / "artifacts/exp_010_rank_drift/run_20261125_v2/results.json"
)


@pytest.fixture(scope="module")
def results() -> dict:
    if not RUN.exists():
        pytest.skip(f"preserved run not present: {RUN}")
    return json.loads(RUN.read_text(encoding="utf-8"))


def test_kontrollerne_bestaar(results: dict) -> None:
    """No threshold may carry a verdict unless every control passed."""
    assert results["controls_passed"] is True, results["control"]
    assert results["control"]["order_identity"]["worst_difference"] == 0.0
    assert results["control"]["calibration"]["worst_gap_error"] <= 1e-9
    assert results["control"]["reproduction"]["passed"] is True


def test_formlen_har_ikke_en_falsk_n_minus_en_faktor() -> None:
    """The threshold is u_crit(1-r)/(LR*spread) — the delta range is `gap` for any N."""
    from feltteori_research.experiment_010_rank_drift import (
        _critical_argument,
        _predicted_threshold,
    )

    experts = ("a", "b", "c")
    predicted = _predicted_threshold(experts, 0.9, 1.0)
    assert predicted == pytest.approx(_critical_argument(3, 0.5) * 0.1 / 2.0)
    # The value the first, faulty run produced was exactly twice this.
    assert predicted == pytest.approx(0.1567, abs=5e-4)


def test_invarianten_er_den_omvendte_af_formlen() -> None:
    from feltteori_research.experiment_010_rank_drift import (
        _critical_argument,
        _invariant,
        _predicted_threshold,
    )

    experts = ("a", "b", "c")
    predicted = _predicted_threshold(experts, 0.99, 0.4)
    assert predicted is not None
    assert _invariant(experts, 0.99, 0.4, predicted) == pytest.approx(
        _critical_argument(3, 0.5)
    )


def test_to_eksperter_er_strukturelt_uopnaaelige() -> None:
    """Floor 1.0 equals the minimum attainable effective count, so there is no threshold."""
    from feltteori_research.experiment_010_rank_drift import _predicted_threshold

    assert _predicted_threshold(("a", "b"), 0.9, 1.0) is None
    assert _predicted_threshold(("a", "b"), 0.99, 1.0) is None


def test_syntetisk_q_et_er_praecis_den_faste_orden() -> None:
    from feltteori_research.experiment_010_rank_drift import _synthetic_orders

    experts = ("a", "b", "c")
    orders = _synthetic_orders(50, experts, 1.0, 20261125)
    assert all(order == list(experts) for order in orders)


def test_syntetisk_q_nul_er_ikke_den_faste_orden() -> None:
    from feltteori_research.experiment_010_rank_drift import _synthetic_orders

    experts = ("a", "b", "c")
    orders = _synthetic_orders(50, experts, 0.0, 20261125)
    assert not all(order == list(experts) for order in orders)
    # Every month is still a permutation of the same three experts.
    assert all(sorted(order) == sorted(experts) for order in orders)


def test_middelpositioner_for_fast_orden_er_praecis() -> None:
    """In `fixed` the positions are 0, 1/(N-1), ..., 1, so the spread is exactly 1."""
    from feltteori_research.experiment_010_rank_drift import _mean_positions

    experts = ("a", "b", "c", "d")
    orders = [list(experts) for _ in range(10)]
    positions = _mean_positions(orders, 0.9, experts)
    assert positions["a"] == pytest.approx(0.0)
    assert positions["d"] == pytest.approx(1.0)
    assert max(positions.values()) - min(positions.values()) == pytest.approx(1.0)


def test_invarianten_holder_i_fixed_og_gør_ikke_i_roving(results: dict) -> None:
    """The finding itself: the drift formula is exact for deterministic drift only."""
    diagnostic = results["diagnostic_invariant_by_assignment"]
    fixed = diagnostic["fixed"]["3"]
    roving = diagnostic["roving"]["3"]
    assert fixed["cells"] > 0 and roving["cells"] > 0
    # Fixed: inside the grid factor of u_crit on every cell.
    assert fixed["ratio"] <= 1.15
    assert fixed["invariant_min"] == pytest.approx(fixed["u_crit"], rel=0.15)
    # Roving: it is not.
    assert roving["ratio"] > 3.0


def test_dommen_er_falsificeret_og_uniform_blev_ikke_uopnaaelig(results: dict) -> None:
    """Condition 2's unreachability claim failed, and that failure is a result."""
    assert results["verdict"] == "falsified"
    fired = results["conditions_fired"]
    assert fired["1_invariant_not_constant"] is True
    assert fired["4_control_failed"] is False
    assert fired["5_calibration_failed"] is False
    synthetic = results["condition_2_synthetic"]["per_retention"]
    assert synthetic["uniform_is_unreachable"] is False
    # The scaling half of condition 2 did hold: stronger drift, lower threshold.
    for condition in ("short_continuity", "long_continuity"):
        assert synthetic[condition]["monotone_decreasing"] is True


def test_q_et_er_praecis_den_faste_orden_ved_r_et() -> None:
    """A synthetic q=1 cell must reproduce the fixed threshold, not approximate it."""
    from feltteori_research.experiment_010_rank_drift import (
        _predicted_threshold,
        _synthetic_orders,
        _mean_positions,
    )

    experts = ("a", "b", "c")
    orders = _synthetic_orders(100, experts, 1.0, 20261125)
    positions = _mean_positions(orders, 0.9, experts)
    spread = max(positions.values()) - min(positions.values())
    assert spread == pytest.approx(1.0)
    assert _predicted_threshold(experts, 0.9, spread) == pytest.approx(0.1567, abs=5e-4)
