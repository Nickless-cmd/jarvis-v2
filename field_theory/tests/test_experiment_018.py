"""Tests for Investigations 18 and 18b — detection of a regime shift ex ante.

The tests that matter here are the ones that would fail if the detector started
reading the outcome, or if the symmetric-statistics boundary were wrong. A test
that merely re-runs the module and compares to the artifact would pass on a
contaminated detector, so most of these are property tests on small synthetic
data.
"""

from __future__ import annotations

import math

import pytest

from feltteori_research.experiment_018_detect_shift import (
    FEATURES,
    apply_stats,
    assign,
    feature_stats,
    fingerprint,
    identity,
    symmetric_statistics,
    true_permutation,
)
from feltteori_research.experiment_018b_lag_fingerprint import (
    _corr,
    lag_fingerprint,
    no_look_ahead,
)

EXPERTS3 = ("a", "b", "c")
EXPERTS2 = ("a", "b")


# ---------------------------------------------------------------------------
# the ex ante boundary — the test that matters most
# ---------------------------------------------------------------------------


def _synthetic_outcomes(n: int) -> list[float]:
    return [10.0 + 3.0 * math.sin(index / 3.0) + 0.2 * index for index in range(n)]


def _lagged_rows(outcomes: list[float], lag: int, experts: tuple[str, ...]) -> list[dict[str, float]]:
    """Each expert delivers the observation ``lag`` months back."""
    rows: list[dict[str, float]] = []
    for index in range(len(outcomes)):
        source = max(index - lag, 0)
        rows.append({expert: float(outcomes[source]) for expert in experts})
    return rows


def test_lag_fingerprint_peaks_at_the_true_lag() -> None:
    outcomes = _synthetic_outcomes(80)
    rows = _lagged_rows(outcomes, 6, EXPERTS2)
    features = lag_fingerprint(rows, outcomes, EXPERTS2, 40, lags=(1, 2, 3, 6, 12))
    assert features is not None
    for expert in EXPERTS2:
        assert features[expert]["lag6"] == pytest.approx(1.0, abs=1e-6)
        assert features[expert]["lag1"] < 0.999


def test_lag_fingerprint_never_reads_the_current_outcome() -> None:
    """Mutating the outcome at the final index must not move the fingerprint.

    A detector that used lag 0 — the current month's outcome — would change here.
    """
    outcomes = _synthetic_outcomes(80)
    rows = _lagged_rows(outcomes, 3, EXPERTS2)
    clean = lag_fingerprint(rows, outcomes, EXPERTS2, 40, lags=(1, 2, 3, 6))
    mutated_outcomes = list(outcomes)
    mutated_outcomes[-1] = mutated_outcomes[-1] * 1.7 + 3.0
    dirty = lag_fingerprint(rows, mutated_outcomes, EXPERTS2, 40, lags=(1, 2, 3, 6))
    assert clean is not None and dirty is not None
    for expert in EXPERTS2:
        for feature in clean[expert]:
            assert clean[expert][feature] == dirty[expert][feature]


def test_no_look_ahead_holds_on_synthetic_rows() -> None:
    """The full control on synthetic rows: mutating future outcomes changes nothing."""
    n = 400
    outcomes = _synthetic_outcomes(n)
    rows: list[dict[str, object]] = []
    for index in range(n):
        rows.append(
            {
                "date": f"{1900 + index // 12:04d}-{index % 12 + 1:02d}",
                "period": "evaluation" if index >= 150 else "development",
                "outcome": outcomes[index],
                "prediction_a": outcomes[max(index - 1, 0)],
                "prediction_b": (
                    sum(outcomes[max(index - 12, 0) : index]) / max(min(index, 12), 1)
                ),
            }
        )
    worst = no_look_ahead(rows, EXPERTS2, probes=3)
    assert worst == 0.0


def test_corr_is_zero_for_a_constant_series() -> None:
    assert _corr([1.0, 1.0, 1.0, 1.0], [1.0, 2.0, 3.0, 4.0]) == 0.0


def test_corr_is_one_for_a_shifted_copy() -> None:
    values = [1.0, 4.0, 2.0, 9.0, 3.0]
    assert _corr(values, values) == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# the symmetric class must be exactly invariant
# ---------------------------------------------------------------------------


def test_symmetric_statistics_are_invariant_under_permutation() -> None:
    real = {"a": 3.0, "b": -1.0, "c": 7.5}
    permuted = {"a": 7.5, "b": 3.0, "c": -1.0}
    left = symmetric_statistics(real, EXPERTS3)
    right = symmetric_statistics(permuted, EXPERTS3)
    for key in ("sorted", "mean", "spread", "mad"):
        assert left[key] == right[key], key


def test_symmetric_statistics_do_move_when_a_value_changes() -> None:
    """The invariance above must come from permutation, not from the statistic
    ignoring its input."""
    left = symmetric_statistics({"a": 3.0, "b": -1.0, "c": 7.5}, EXPERTS3)
    right = symmetric_statistics({"a": 3.0, "b": -1.0, "c": 8.5}, EXPERTS3)
    assert left["spread"] != right["spread"]


# ---------------------------------------------------------------------------
# the shape fingerprint
# ---------------------------------------------------------------------------


def test_jagged_series_scores_higher_on_step_than_a_smooth_one() -> None:
    smooth = [{"a": float(10 + index // 10)} for index in range(30)]
    jagged = [{"a": float(10 + (index % 2) * 5)} for index in range(30)]
    smooth_features = fingerprint(smooth, ("a",), 24)
    jagged_features = fingerprint(jagged, ("a",), 24)
    assert smooth_features is not None and jagged_features is not None
    assert jagged_features["a"]["f_step"] > smooth_features["a"]["f_step"]


def test_fingerprint_returns_none_when_the_window_does_not_fit() -> None:
    assert fingerprint([{"a": 1.0}] * 3, ("a",), 12) is None


# ---------------------------------------------------------------------------
# matching
# ---------------------------------------------------------------------------


def test_true_permutation_is_cyclic() -> None:
    assert true_permutation(EXPERTS3) == {"a": "b", "b": "c", "c": "a"}


def test_identity_maps_every_name_to_itself() -> None:
    assert identity(EXPERTS3) == {"a": "a", "b": "b", "c": "c"}


def _reference() -> dict[str, dict[str, float]]:
    return {
        "a": {"f_step": 0.0, "f_ac1": 0.0, "f_tie": 0.0},
        "b": {"f_step": 5.0, "f_ac1": 5.0, "f_tie": 5.0},
        "c": {"f_step": 10.0, "f_ac1": 10.0, "f_tie": 10.0},
    }


def test_assign_recovers_the_identity_when_observation_matches_reference() -> None:
    reference = _reference()
    stats = feature_stats(reference, EXPERTS3)
    z = apply_stats(reference, stats, EXPERTS3)
    mapping, _ = assign(z, z, EXPERTS3)
    assert mapping == identity(EXPERTS3)


def test_assign_never_returns_an_excluded_name() -> None:
    reference = _reference()
    stats = feature_stats(reference, EXPERTS3)
    z = apply_stats(reference, stats, EXPERTS3)
    mapping, distances = assign(z, z, EXPERTS3, excluded="b")
    assert "b" not in mapping.values()
    assert set(distances) == set(EXPERTS3)


def test_assign_maps_a_swapped_observation_to_the_other_name() -> None:
    reference = _reference()
    stats = feature_stats(reference, EXPERTS3)
    z = apply_stats(reference, stats, EXPERTS3)
    # Name a now carries what b carried.
    observed = {"a": z["b"], "b": z["c"], "c": z["a"]}
    mapping, _ = assign(observed, z, EXPERTS3)
    assert mapping == {"a": "b", "b": "c", "c": "a"}


def test_feature_stats_and_apply_stats_round_trip_to_zero_mean() -> None:
    reference = _reference()
    stats = feature_stats(reference, EXPERTS3)
    z = apply_stats(reference, stats, EXPERTS3)
    for feature in FEATURES:
        assert sum(z[expert][feature] for expert in EXPERTS3) / 3 == pytest.approx(
            0.0, abs=1e-9
        )
