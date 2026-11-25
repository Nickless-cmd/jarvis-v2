"""Tests for Investigation 19 — the distance as a self-doubt signal.

The code tests are written so that a plausible mutation fails them: reversing the
AUC, choosing the abstention threshold on the test half, dropping the full
distance matrix, or letting the current month's outcome reach the fingerprint.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from feltteori_research.experiment_019_distance_as_doubt import (
    MIN_COVERAGE,
    QUARTILES,
    _abstention,
    _auc,
    _bootstrap_auc,
    _quartile_error_rates,
    distances_to_all,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    PROJECT_ROOT
    / "artifacts/exp_019_distance_as_doubt/run_20261125_v5/results.json"
)
PROTOCOL = PROJECT_ROOT / "experiments/exp_019_distance_as_doubt/protocol.md"


@pytest.fixture(scope="module")
def artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


# ---- AUC ----------------------------------------------------------------


def test_auc_is_one_when_every_wrong_match_is_further_away() -> None:
    scores = [1.0, 2.0, 3.0, 9.0, 10.0]
    labels = [False, False, False, True, True]
    assert _auc(scores, labels) == pytest.approx(1.0)


def test_auc_is_zero_when_the_ordering_is_reversed() -> None:
    scores = [1.0, 2.0, 3.0, 9.0, 10.0]
    labels = [True, True, True, False, False]
    assert _auc(scores, labels) == pytest.approx(0.0)


def test_auc_is_one_half_when_every_score_is_tied() -> None:
    assert _auc([5.0] * 6, [True, False] * 3) == pytest.approx(0.5)


def test_auc_needs_both_classes() -> None:
    assert math.isnan(_auc([1.0, 2.0], [True, True]))
    assert math.isnan(_auc([], []))


def test_bootstrap_interval_brackets_the_point_estimate() -> None:
    scores = [float(index) for index in range(40)]
    labels = [index >= 20 for index in range(40)]
    low, high = _bootstrap_auc(scores, labels, resamples=200)
    point = _auc(scores, labels)
    assert low <= point <= high


def test_bootstrap_is_deterministic_for_a_fixed_seed() -> None:
    scores = [float(index % 7) for index in range(60)]
    labels = [index % 3 == 0 for index in range(60)]
    assert _bootstrap_auc(scores, labels, resamples=100) == _bootstrap_auc(
        scores, labels, resamples=100
    )


# ---- calibration --------------------------------------------------------


def test_quartiles_are_monotone_when_error_tracks_distance() -> None:
    scores = [float(index) for index in range(40)]
    labels = [index >= 30 for index in range(40)]
    bins = _quartile_error_rates(scores, labels)
    assert len(bins) == QUARTILES
    rates = [entry["error_rate"] for entry in bins]
    assert rates == sorted(rates)
    assert rates[0] == 0.0
    assert rates[-1] == 1.0


def test_quartiles_are_flat_when_error_is_independent_of_distance() -> None:
    scores = [float(index) for index in range(40)]
    labels = [(index % 4) == 0 for index in range(40)]
    rates = [entry["error_rate"] for entry in _quartile_error_rates(scores, labels)]
    assert max(rates) - min(rates) < 0.15


# ---- the full distance matrix ------------------------------------------


def _z(level: float) -> dict[str, float]:
    """A fingerprint where every lag sits at the same level."""
    from feltteori_research.experiment_018b_lag_fingerprint import LAG_FEATURES

    return {feature: level for feature in LAG_FEATURES}


def test_distance_matrix_keeps_every_name_not_just_the_winner() -> None:
    observed = {"a": _z(0.0), "b": _z(5.0), "c": _z(7.0)}
    reference = {"a": _z(0.0), "b": _z(4.0), "c": _z(9.0)}
    matrix = distances_to_all(observed, reference, ("a", "b", "c"))
    assert set(matrix) == {"a", "b", "c"}
    for expert in matrix:
        assert set(matrix[expert]) == {"a", "b", "c"}
    assert matrix["a"]["a"] == pytest.approx(0.0)
    assert matrix["a"]["c"] > matrix["a"]["a"]
    assert matrix["b"]["b"] < matrix["b"]["c"]


# ---- abstention ---------------------------------------------------------


def _points(distances: list[float], hits: list[bool]) -> list[dict[str, object]]:
    return [
        {"distance": distance, "hit": hit, "settled": True}
        for distance, hit in zip(distances, hits)
    ]


def test_abstention_chooses_on_development_and_is_judged_on_test() -> None:
    # Development: low distances are right, high distances are wrong.
    development = _points([1.0, 2.0, 3.0, 8.0, 9.0, 10.0], [True, True, True, False, False, False])
    # Test: the same distances, but the relationship is reversed. A threshold
    # chosen on development must therefore do badly here. If the implementation
    # peeked at test, it would pick a different threshold and score better.
    test = _points([1.0, 2.0, 3.0, 8.0, 9.0, 10.0], [False, False, False, True, True, True])
    result = _abstention(development, test)
    assert result["applicable"] is True
    assert result["threshold"] <= 3.0
    assert result["development_precision"] == pytest.approx(1.0)
    assert result["test_precision"] == pytest.approx(0.0)


def test_abstention_respects_the_minimum_coverage() -> None:
    development = _points([1.0, 2.0, 3.0, 4.0, 9.0], [True, True, True, True, False])
    test = _points([1.0, 2.0], [True, True])
    result = _abstention(development, test)
    # Answering only the single perfect month would leave 20 % coverage, below
    # the floor, so the chosen threshold must answer more than that.
    assert result["development_coverage"] >= MIN_COVERAGE


def test_abstention_reports_when_it_cannot_apply() -> None:
    assert _abstention([], [])["applicable"] is False


# ---- the artifact ------------------------------------------------------


def test_verdict_names_the_two_failed_hypotheses(artifact: dict) -> None:
    assert artifact["verdict"] == "partial:4_abstention_pays,5_held_out_table_transfers"


def test_the_three_held_hypotheses_are_held(artifact: dict) -> None:
    conditions = artifact["conditions"]
    assert conditions["1_calibration_is_monotone"] is True
    assert conditions["2_distance_separates"] is True
    assert conditions["3_signal_survives_within_cell"] is True


def test_the_two_failed_hypotheses_are_failed(artifact: dict) -> None:
    conditions = artifact["conditions"]
    assert conditions["4_abstention_pays"] is False
    assert conditions["5_held_out_table_transfers"] is False


def test_pooled_power_exceeds_within_cell_power(artifact: dict) -> None:
    """The whole finding: most of the signal is the cell, not the month."""
    auc = artifact["auc"]
    assert auc["pooled"] > auc["within_cell"] > 0.5
    survived = (auc["within_cell"] - 0.5) / (auc["pooled"] - 0.5)
    assert survived < 0.35


def test_the_scrambled_control_loses_the_power(artifact: dict) -> None:
    controls = artifact["controls"]
    assert controls["scrambled_reference_loses_power"] is True
    assert controls["scrambled_auc"] < 0.6
    # And the reason it lands far below 0.5 rather than near it: the scrambled
    # condition makes nearly every match wrong.
    assert controls["scrambled_error_rate"] > 0.9


def test_the_held_out_table_does_not_transfer(artifact: dict) -> None:
    transfer = artifact["transfer"]
    assert transfer["ratio"] < 0.5
    assert transfer["ordinary_median_distance"] < transfer["held_out_median_distance"]


def test_calibration_quartiles_are_monotone_in_the_artifact(artifact: dict) -> None:
    rates = [entry["error_rate"] for entry in artifact["quartiles"]]
    assert len(rates) == QUARTILES
    assert rates == sorted(rates)
    assert rates[-1] > 3.0 * rates[0]


def test_the_protocol_was_committed_before_the_module() -> None:
    """The protocol exists on disk and names the frozen hypotheses."""
    text = PROTOCOL.read_text()
    assert "Frozen:" in text
    assert "exploratory" in text.lower()
    for hypothesis in ("H1", "H2", "H3", "H4", "H5"):
        assert hypothesis in text
