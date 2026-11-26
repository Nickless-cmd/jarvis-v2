"""Tests for Investigation 20 — can a different representation separate the series?

The tests are written so that a plausible mutation fails them: letting a
representation name the expert it describes, letting ``_features_of`` read one
expert's keys and fail somewhere else, letting R0 drift away from the 018b
fingerprint it is supposed to reproduce, or breaking B3's residual arithmetic.
"""

from __future__ import annotations

import statistics

import pytest

from feltteori_research.experiment_009_expert_set import EXPERT_SETS
from feltteori_research.experiment_018b_lag_fingerprint import lag_fingerprint
from feltteori_research.experiment_020_representation import (
    LAGS,
    REPRESENTATIONS,
    _features_of,
    rep_pairwise,
    rep_shared_removed,
)

EXPERTS = EXPERT_SETS["original"]
WINDOW = 24
N_ROWS = 300


def _rows(experts: tuple[str, ...] = EXPERTS) -> list[dict[str, float]]:
    return [
        {expert: float((index * (position + 3)) % 19) for position, expert in enumerate(experts)}
        for index in range(N_ROWS)
    ]


def _outcomes() -> list[float]:
    return [float((index * 7) % 13) for index in range(N_ROWS)]


# ---- B2 must not name the expert it describes ---------------------------


def test_b2_features_do_not_name_any_expert() -> None:
    """B2 may not carry the expert's own name in its coordinate system.

    Measured 26/11-2026: a ``pair_<expert>`` design puts a constant 1.0 at each
    expert's own position, and that constant does *not* vanish under z-scoring —
    it becomes a near one-hot identity code with spread 2.21-2.31 against ~2.0
    for the lag features. ``assign`` weights every feature equally, so the
    detector could read the answer off the coordinate system instead of off the
    series. That is the exact failure mode the experiment exists to separate.
    """
    fingerprint = rep_pairwise(_rows(), _outcomes(), EXPERTS, WINDOW)
    assert fingerprint is not None
    for feature in _features_of(fingerprint, EXPERTS):
        for expert in EXPERTS:
            assert expert not in feature, (
                f"feature {feature!r} names expert {expert!r}: the detector can "
                "read the identity off the coordinate system"
            )


def test_b2_carries_one_relation_feature_per_other_expert() -> None:
    """The relational profile keeps every relation, only drops the self-reference."""
    fingerprint = rep_pairwise(_rows(), _outcomes(), EXPERTS, WINDOW)
    assert fingerprint is not None
    relation_features = [name for name in _features_of(fingerprint, EXPERTS) if name.startswith("rel_")]
    assert len(relation_features) == len(EXPERTS) - 1


def test_b2_relations_are_sorted_descending() -> None:
    """A fixed order is what makes the profile name-free; unsorted it would leak."""
    fingerprint = rep_pairwise(_rows(), _outcomes(), EXPERTS, WINDOW)
    assert fingerprint is not None
    for expert in EXPERTS:
        values = [
            fingerprint[expert][name]
            for name in sorted(_features_of(fingerprint, EXPERTS))
            if name.startswith("rel_")
        ]
        assert values == sorted(values, reverse=True)


# ---- _features_of must fail loudly on an asymmetric representation ------


def test_features_of_rejects_a_representation_that_is_not_name_symmetric() -> None:
    """Reading one expert's keys and failing three frames later cost the first run."""
    asymmetric = {
        EXPERTS[0]: {"lag1": 0.1, "own_marker": 1.0},
        EXPERTS[1]: {"lag1": 0.2},
        EXPERTS[2]: {"lag1": 0.3},
    }
    with pytest.raises(ValueError, match="not name-symmetric"):
        _features_of(asymmetric, EXPERTS)


def test_every_registered_representation_is_name_symmetric() -> None:
    """A representation that gives each expert different keys cannot be measured."""
    for name, representation in REPRESENTATIONS.items():
        fingerprint = representation(_rows(), _outcomes(), EXPERTS, WINDOW)
        assert fingerprint is not None, name
        _features_of(fingerprint, EXPERTS)  # raises ValueError if asymmetric


# ---- R0 must reproduce the fingerprint Investigation 19 was built on ----


def test_r0_reproduces_the_018b_lag_fingerprint() -> None:
    """If R0 drifts, every comparison to Investigation 19's numbers is meaningless."""
    rows = _rows()
    outcomes = _outcomes()
    ours = REPRESENTATIONS["R0_baseline"](rows, outcomes, EXPERTS, WINDOW)
    theirs = lag_fingerprint(rows, outcomes, EXPERTS, WINDOW)
    assert ours is not None and theirs is not None
    assert set(ours) == set(theirs)
    for expert in EXPERTS:
        assert set(ours[expert]) == set(theirs[expert])
        for feature in theirs[expert]:
            assert ours[expert][feature] == pytest.approx(theirs[expert][feature], abs=1e-12)


def test_r0_feature_names_are_exactly_the_lags() -> None:
    fingerprint = REPRESENTATIONS["R0_baseline"](_rows(), _outcomes(), EXPERTS, WINDOW)
    assert fingerprint is not None
    assert _features_of(fingerprint, EXPERTS) == tuple(sorted(f"lag{lag}" for lag in LAGS))


# ---- B3 must be the residual of the same series, nothing more -----------


def test_b3_residual_is_series_minus_cross_expert_mean() -> None:
    """B3 is a linear transform of the same inputs — it may not invent data."""
    rows = _rows()
    outcomes = _outcomes()
    fingerprint = rep_shared_removed(rows, outcomes, EXPERTS, WINDOW)
    assert fingerprint is not None

    # Recompute the trailing window's residual independently. ``_window_indices``
    # returns ``range(n - window, n)``, not the first window.
    indices = list(range(N_ROWS - WINDOW, N_ROWS))
    common = [statistics.mean(rows[i][expert] for expert in EXPERTS) for i in indices]
    residual = [rows[i][EXPERTS[0]] - common[offset] for offset, i in enumerate(indices)]
    paired = [outcomes[i - LAGS[0]] for i in indices]
    expected = _corr(residual, paired)
    assert fingerprint[EXPERTS[0]]["lag1"] == pytest.approx(expected, abs=1e-12)


def test_b3_residuals_sum_to_zero_across_experts() -> None:
    """The common component really is removed — otherwise B3 is just a rescaling."""
    rows = _rows()
    start = max(LAGS)
    indices = list(range(start, N_ROWS))[:WINDOW]
    residuals = {
        expert: [
            rows[i][expert] - statistics.mean(rows[i][other] for other in EXPERTS)
            for i in indices
        ]
        for expert in EXPERTS
    }
    for offset in range(len(indices)):
        total = sum(residuals[expert][offset] for expert in EXPERTS)
        assert abs(total) < 1e-12


# ---- D12 is a control, and it is not A1 --------------------------------


def test_d12_is_registered_as_a_control_not_a_candidate() -> None:
    """D12 was added after the protocol was frozen to falsify "difference works".

    It must be measured (so it lives in ``REPRESENTATIONS``) but it may never be
    counted as a candidate — otherwise a failed control could be read as a winner.
    """
    from feltteori_research.experiment_020_representation import CANDIDATES

    assert "D12_annual_difference" in REPRESENTATIONS
    assert "D12_annual_difference" not in CANDIDATES


def test_d12_differences_over_twelve_months_not_one() -> None:
    """D12 must subtract ``x[t-12]``; subtracting ``x[t-1]`` would make it A1."""
    from feltteori_research.experiment_020_representation import rep_annual_difference

    rows = _rows()
    outcomes = _outcomes()
    fingerprint = rep_annual_difference(rows, outcomes, EXPERTS, WINDOW)
    assert fingerprint is not None
    # Recompute the first expert's first-lag feature by hand, with a 12-month lag.
    n = len(rows)
    indices = list(range(n - WINDOW, n))
    delta_prediction = [rows[i][EXPERTS[0]] - rows[i - 12][EXPERTS[0]] for i in indices]
    lag = LAGS[0]
    delta_outcome = [outcomes[i - lag] - outcomes[i - lag - 12] for i in indices]
    expected = _corr(delta_prediction, delta_outcome)
    assert fingerprint[EXPERTS[0]][f"ylag{lag}"] == pytest.approx(expected)


def _corr(left: list[float], right: list[float]) -> float:
    """Pearson correlation, matching the module's own helper."""
    mean_left = statistics.mean(left)
    mean_right = statistics.mean(right)
    numerator = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right, strict=True))
    left_spread = statistics.pstdev(left)
    right_spread = statistics.pstdev(right)
    if left_spread == 0.0 or right_spread == 0.0:
        return 0.0
    return numerator / (len(left) * left_spread * right_spread)


# ---- C1: the third route that H5's falsification clause names -----------


def test_c1_with_uniform_loadings_is_exactly_b3(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forcing the estimated direction to be uniform must reproduce B3 exactly.

    This is the invariant that makes C1 a *test* of H5 rather than a second opinion:
    the only thing separating the two representations is where the shared direction
    comes from. With ``u = 1/sqrt(k)`` the projection is the mean, the two residuals
    differ by an additive constant, and Pearson is invariant to that. If this test
    ever fails, C1 has acquired a difference of its own and can no longer be read as
    "B3 with an estimated component".
    """
    import feltteori_research.experiment_020_representation as module

    uniform = [1.0 / (len(EXPERTS) ** 0.5)] * len(EXPERTS)
    monkeypatch.setattr(module, "_pc1_direction", lambda *args, **kwargs: list(uniform))

    rows = _rows()
    outcomes = _outcomes()
    b3 = module.rep_shared_removed(rows, outcomes, EXPERTS, WINDOW)
    c1 = module.rep_shared_removed_pc1(rows, outcomes, EXPERTS, WINDOW)
    assert b3 is not None and c1 is not None
    for expert in EXPERTS:
        for feature in LAGS:
            name = f"lag{feature}"
            assert c1[expert][name] == pytest.approx(b3[expert][name], abs=1e-9), (
                f"C1 with uniform loadings differs from B3 at {expert}/{name}"
            )


def test_c1_residual_is_orthogonal_to_the_estimated_direction() -> None:
    """The removal must actually remove: the residual may not project onto PC1.

    The direction comes from a power iteration, so it is an approximation and the
    orthogonality holds to the convergence tolerance, not exactly. The check is
    therefore a cosine, not an absolute sum: measuring ``mixed == 0`` absolutely
    fails on a residual that is orthogonal to within 1e-10 relative (measured
    26/11-2026: 3.8e-06 absolute on data of order 100).
    """
    from feltteori_research.experiment_020_representation import (
        _pc1_direction,
        _window_indices,
    )

    rows = _rows()
    indices = _window_indices(len(rows), WINDOW, max(LAGS))
    assert indices is not None
    direction = _pc1_direction(rows, EXPERTS, indices)

    columns = [[rows[i][expert] for i in indices] for expert in EXPERTS]
    centred = [
        [value - sum(column) / len(indices) for value in column] for column in columns
    ]
    span = len(EXPERTS)
    for j in range(span):
        residual = [
            centred[j][t]
            - sum(direction[m] * centred[m][t] for m in range(span)) * direction[j]
            for t in range(len(indices))
        ]
        projected = [
            sum(direction[m] * centred[m][t] for m in range(span))
            for t in range(len(indices))
        ]
        residual_norm = sum(value * value for value in residual) ** 0.5
        projected_norm = sum(value * value for value in projected) ** 0.5
        assert residual_norm > 0.0, "the residual is empty, so the test proves nothing"
        assert projected_norm > 0.0, "nothing was projected out, so nothing was removed"
        cosine = sum(a * b for a, b in zip(residual, projected, strict=True)) / (
            residual_norm * projected_norm
        )
        assert abs(cosine) < 1e-8, (
            f"expert {EXPERTS[j]} still carries the shared component: cos={cosine:.2e}"
        )


def test_c1_is_registered_as_a_control_not_a_candidate() -> None:
    """C1 tests H5, which was registered after H1-H4. It may not enter H1's contest."""
    from feltteori_research.experiment_020_representation import CANDIDATES

    assert "C1_shared_removed_pc1" in REPRESENTATIONS
    assert "C1_shared_removed_pc1" not in CANDIDATES


def test_pc1_loadings_are_a_unit_vector() -> None:
    """A power iteration that did not normalise would silently rescale the removal."""
    from feltteori_research.experiment_020_representation import pc1_loadings

    loadings = pc1_loadings(_rows(), EXPERTS, WINDOW)
    assert loadings is not None
    assert len(loadings) == len(EXPERTS)
    norm = sum(value * value for value in loadings) ** 0.5
    assert norm == pytest.approx(1.0, abs=1e-9)
