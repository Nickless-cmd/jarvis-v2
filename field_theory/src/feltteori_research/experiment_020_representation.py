"""Experiment 020 — can a different representation separate what the data holds?

Investigation 19 found that 29 of 40 cell-windows fail the C3 identity control,
and that the identity rate and the error rate are largely the same property
measured twice: *a cell where the fingerprint cannot tell the series apart is a
cell where the match is wrong.* It named the cause — the representation is not
discriminative — and did not test it.

This module tests it by holding every input fixed and changing only the function
that maps data to a vector. The question is not whether the detector can be made
better; it is whether the information was in the data all along.

The protocol is frozen in ``experiments/exp_020_representation/protocol.md`` and
was committed alone as ``127fff270``, before this file existed.

Design notes that matter for reading the numbers:

* ``experiment_018b_lag_fingerprint`` is **not modified**. Its building blocks are
  imported so the baseline is reproducible by construction.
* Every representation sees exactly two inputs: the prediction streams and the
  outcome series. No month is added and no series is extended.
* C3 is not redefined here. The threshold 0.9 and the control itself come from
  ``exp_018b``, because a control chosen by the experiment it judges can be tuned.
* X1 exists so the result can be thrown away. Adding dimensions separates nearest
  neighbours with no information at all, and that is the most likely way to get a
  false positive out of this design.
"""

from __future__ import annotations

import random
import statistics
from pathlib import Path
from typing import Callable

from .experiment_005_learning import parse_silso_monthly
from .experiment_006_order import parse_noaa_monthly
from .experiment_009_expert_set import EXPERT_SETS, _expert_rows_for
from .experiment_017_regime_shift import prepare_swapped
from .experiment_018_detect_shift import (
    _evaluation_indices,
    apply_stats,
    assign,
    feature_stats,
    identity,
    true_permutation,
)
from .experiment_018b_lag_fingerprint import _corr

METHOD_VERSION = "exp_020_representation/1"

#: The baseline's eight lags, unchanged from 18b.
LAGS = (1, 2, 3, 6, 12, 24, 66, 132)
#: Every lag the data supports, for B1.
ALL_LAGS = tuple(range(1, 133))
WINDOWS = (24, 36, 60, 120)
#: Inherited from 18b. Not re-chosen here.
C3_THRESHOLD = 0.9
SEED = 20261125
#: How many irrelevant features X1 adds, so it matches B1's dimensionality.
IRRELEVANT_FEATURES = 124

#: A representation maps the two fixed inputs to a feature vector per expert.
Representation = Callable[
    [list[dict[str, float]], list[float], tuple[str, ...], int],
    "dict[str, dict[str, float]] | None",
]


# ---------------------------------------------------------------------------
# small helpers the representations share
# ---------------------------------------------------------------------------


def _rank(values: list[float]) -> list[float]:
    """Average ranks, ties shared — the standard Spearman handling."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        average = (position + end) / 2.0 + 1.0
        for slot in range(position, end + 1):
            ranks[order[slot]] = average
        position = end + 1
    return ranks


def _spearman(left: list[float], right: list[float]) -> float:
    """Rank correlation; zero when either side is constant."""
    return _corr(_rank(left), _rank(right))


def _window_indices(n: int, window: int, lookback: int) -> list[int] | None:
    """Trailing window, or ``None`` when the history cannot support it."""
    if window < 4 or n < window + lookback:
        return None
    return list(range(n - window, n))


# ---------------------------------------------------------------------------
# the representations
# ---------------------------------------------------------------------------


def rep_baseline(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
) -> dict[str, dict[str, float]] | None:
    """R0 — 18b's lag fingerprint, reproduced exactly.

    Eight Pearson correlations between one expert's prediction stream and the
    outcome at a lag. This is the object whose failure Investigation 19 reported.
    """
    n = len(real_rows)
    indices = _window_indices(n, window, max(LAGS))
    if indices is None:
        return None
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        prediction = [float(real_rows[i][expert]) for i in indices]
        features: dict[str, float] = {}
        for lag in LAGS:
            paired_outcome = [float(outcomes[i - lag]) for i in indices]
            features[f"lag{lag}"] = _corr(prediction, paired_outcome)
        out[expert] = features
    return out


def rep_first_difference(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
) -> dict[str, dict[str, float]] | None:
    """A1 — correlate the *change* in prediction against the *change* in outcome.

    Differencing is invertible given one starting value, so the series carries the
    same information. What changes is that a shared level or slow trend no longer
    dominates the correlation. If the series differ only in their month-to-month
    motion, this is the representation that can see it.
    """
    n = len(real_rows)
    indices = _window_indices(n, window, max(LAGS) + 1)
    if indices is None:
        return None
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        delta_prediction = [
            float(real_rows[i][expert]) - float(real_rows[i - 1][expert])
            for i in indices
        ]
        features: dict[str, float] = {}
        for lag in LAGS:
            delta_outcome = [
                float(outcomes[i - lag]) - float(outcomes[i - lag - 1])
                for i in indices
            ]
            features[f"dlag{lag}"] = _corr(delta_prediction, delta_outcome)
        out[expert] = features
    return out


def rep_annual_difference(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
) -> dict[str, dict[str, float]] | None:
    """D12 — the same eight lags, taken on the year-over-year change.

    Added 26/11-2026 as a falsification control, after the protocol was frozen.
    A1 and B3 both passed 21/40 and both are differences, so the run could not say
    whether "difference" was the mechanism or whether each removed a specific
    component. D12 is a third difference of the same data. If "difference" is what
    helps, D12 should help too. Measured in run_v4 (26/11-2026): 2/40, median C3
    0.225 — chance level for a four-expert set, against A1's and B3's 21/40.
    It removes variation that is shared across *time* rather than across *experts*,
    and it takes the signal with it.
    """
    n = len(real_rows)
    indices = _window_indices(n, window, max(LAGS) + 1)
    if indices is None:
        return None
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        delta_prediction = [
            float(real_rows[i][expert]) - float(real_rows[i - 12][expert])
            for i in indices
        ]
        features: dict[str, float] = {}
        for lag in LAGS:
            delta_outcome = [
                float(outcomes[i - lag]) - float(outcomes[i - lag - 12])
                for i in indices
            ]
            features[f"ylag{lag}"] = _corr(delta_prediction, delta_outcome)
        out[expert] = features
    return out


def rep_rank(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
) -> dict[str, dict[str, float]] | None:
    """A2 — Spearman at the same eight lags.

    Declared weaker than the baseline in the protocol: ranks discard magnitude, so
    this holds *less* information. It isolates one failure mode — sensitivity to a
    few extreme months — and a gain here would mean the discarded part was noise.
    """
    n = len(real_rows)
    indices = _window_indices(n, window, max(LAGS))
    if indices is None:
        return None
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        prediction = [float(real_rows[i][expert]) for i in indices]
        features: dict[str, float] = {}
        for lag in LAGS:
            paired_outcome = [float(outcomes[i - lag]) for i in indices]
            features[f"lag{lag}"] = _spearman(prediction, paired_outcome)
        out[expert] = features
    return out


def rep_full_lag(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
) -> dict[str, dict[str, float]] | None:
    """B1 — all 132 lags instead of the eight the baseline selected.

    No new data; the baseline's choice of eight was itself a compression. Included
    in the protocol as the representation that should be beaten, because a higher
    dimension separates nearest neighbours more easily regardless of content.
    """
    n = len(real_rows)
    indices = _window_indices(n, window, max(ALL_LAGS))
    if indices is None:
        return None
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        prediction = [float(real_rows[i][expert]) for i in indices]
        features: dict[str, float] = {}
        for lag in ALL_LAGS:
            paired_outcome = [float(outcomes[i - lag]) for i in indices]
            features[f"lag{lag}"] = _corr(prediction, paired_outcome)
        out[expert] = features
    return out


def rep_pairwise(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
) -> dict[str, dict[str, float]] | None:
    """B2 — the baseline features plus each expert's relational profile.

    Two series that are near-copies of each other are declared near-copies here
    instead of being inferred from matching fingerprints. The relation is computed
    from the same two inputs; it was simply not expressed before.

    The profile is *sorted* and names nobody: ``rel_1`` is the strongest relation
    this series has to any other series, whoever that turns out to be. An earlier
    design used ``pair_<expert>`` and put a constant 1.0 at each expert's own
    position. Measured 26/11-2026 that constant does **not** vanish under
    z-scoring: it becomes a near one-hot identity code with spread 2.21-2.31
    against ~2.0 for the lag features, and ``assign`` weights every feature
    equally. The detector could then read the answer off the coordinate system
    instead of off the series. Sorting removes the self-reference and keeps the
    relation.
    """
    n = len(real_rows)
    indices = _window_indices(n, window, max(LAGS))
    if indices is None:
        return None
    streams = {
        expert: [float(real_rows[i][expert]) for i in indices] for expert in experts
    }
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        features: dict[str, float] = {}
        for lag in LAGS:
            paired_outcome = [float(outcomes[i - lag]) for i in indices]
            features[f"lag{lag}"] = _corr(streams[expert], paired_outcome)
        relations = sorted(
            (
                _corr(streams[expert], streams[other])
                for other in experts
                if other != expert
            ),
            reverse=True,
        )
        for position, value in enumerate(relations, start=1):
            features[f"rel_{position}"] = value
        out[expert] = features
    return out


def rep_shared_removed(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
) -> dict[str, dict[str, float]] | None:
    """B3 — subtract the cross-expert mean series before correlating.

    In a periodic world the common cycle is exactly the component that makes every
    fingerprint look alike. Removing it leaves what distinguishes the series. A
    linear transformation of the same series, and the second half of H3's
    prediction.
    """
    n = len(real_rows)
    indices = _window_indices(n, window, max(LAGS))
    if indices is None:
        return None
    span = len(experts)
    common = [
        sum(float(real_rows[i][expert]) for expert in experts) / span for i in indices
    ]
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        residual = [float(real_rows[i][expert]) - common[offset] for offset, i in enumerate(indices)]
        features: dict[str, float] = {}
        for lag in LAGS:
            paired_outcome = [float(outcomes[i - lag]) for i in indices]
            features[f"lag{lag}"] = _corr(residual, paired_outcome)
        out[expert] = features
    return out


def rep_irrelevant(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
) -> dict[str, dict[str, float]] | None:
    """X1 — the control that must NOT help.

    The baseline's eight features plus ``IRRELEVANT_FEATURES`` correlations against
    a fixed pseudo-random series at varying shifts. It adds dimensions and no
    information about the world, so any identity-rate gain it produces is the
    dimension artefact C5 is designed to catch.
    """
    n = len(real_rows)
    indices = _window_indices(n, window, max(LAGS) + 64)
    if indices is None:
        return None
    rng = random.Random(SEED)
    noise = [rng.gauss(0.0, 1.0) for _ in range(n)]
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        prediction = [float(real_rows[i][expert]) for i in indices]
        features: dict[str, float] = {}
        for lag in LAGS:
            paired_outcome = [float(outcomes[i - lag]) for i in indices]
            features[f"lag{lag}"] = _corr(prediction, paired_outcome)
        for slot in range(IRRELEVANT_FEATURES):
            shift = slot % 64
            features[f"noise{slot}"] = _corr(
                prediction, [noise[i - shift] for i in indices]
            )
        out[expert] = features
    return out


REPRESENTATIONS: dict[str, Representation] = {
    "R0_baseline": rep_baseline,
    "A1_first_difference": rep_first_difference,
    "A2_rank": rep_rank,
    "B1_full_lag": rep_full_lag,
    "B2_pairwise": rep_pairwise,
    "B3_shared_removed": rep_shared_removed,
    "X1_irrelevant": rep_irrelevant,
    "D12_annual_difference": rep_annual_difference,
}

#: The five the protocol registers as candidates. X1 is a control, not a candidate.
#: D12 is a second control, added after the protocol was frozen to falsify the
#: "both winners are differences, so difference is the mechanism" reading.
CANDIDATES = ("A1_first_difference", "A2_rank", "B1_full_lag", "B2_pairwise", "B3_shared_removed")


# ---------------------------------------------------------------------------
# measuring one cell under one representation
# ---------------------------------------------------------------------------


def _features_of(
    fingerprint: dict[str, dict[str, float]], experts: tuple[str, ...]
) -> tuple[str, ...]:
    """The feature names a representation produced, in a stable order.

    Every expert must carry the same names, or ``feature_stats`` cannot express
    them in one coordinate system. Reading the first expert's keys and letting a
    later lookup fail gave a ``KeyError`` three frames deep with no hint of which
    representation was at fault (measured 25/11-2026, cost the first full run).
    """
    first = set(fingerprint[experts[0]].keys())
    for expert in experts[1:]:
        if set(fingerprint[expert].keys()) != first:
            raise ValueError(
                f"representation is not name-symmetric: {expert!r} carries "
                f"{sorted(set(fingerprint[expert].keys()) - first)} more and "
                f"{sorted(first - set(fingerprint[expert].keys()))} less than "
                f"{experts[0]!r}"
            )
    return tuple(sorted(first))


def measure_cell_for(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
    source: str,
    set_name: str,
    rep_name: str,
    representation: Representation,
) -> dict[str, object]:
    """C3 identity rate and post-swap accuracy for one cell, one representation.

    The structure mirrors ``experiment_018b.measure_cell`` deliberately, so the
    baseline number can be compared to Investigation 19's without re-deriving it.
    """
    evaluation = _evaluation_indices(rows)
    if len(evaluation) < 40:
        raise ValueError("too few evaluation months to split")
    swap_position = len(evaluation) // 2
    swap_at = evaluation[swap_position]

    plain = prepare_swapped(rows, experts, swap_at, shifted=False)
    shifted = prepare_swapped(rows, experts, swap_at, shifted=True)

    control_real = [point["real"] for point in plain]
    shift_real = [point["real"] for point in shifted]
    outcomes = [float(row["outcome"]) for row in rows]  # type: ignore[arg-type]

    permutation = true_permutation(experts)
    identity_mapping = identity(experts)

    windows: dict[str, object] = {}
    for window in WINDOWS:
        reference = representation(shift_real[:swap_at], outcomes[:swap_at], experts, window)
        if reference is None:
            windows[str(window)] = {"skipped": "reference window too short"}
            continue
        features = _features_of(reference, experts)
        stats = feature_stats(reference, experts, features)
        reference_z = apply_stats(reference, stats, experts, features)

        # ---- C3: the reference must identify a name against itself ------
        half = swap_at // 2
        first = representation(shift_real[:half], outcomes[:half], experts, window)
        second = representation(
            shift_real[half:swap_at], outcomes[half:swap_at], experts, window
        )
        reference_is_stable = False
        if first is not None and second is not None:
            stats_second = feature_stats(second, experts, features)
            self_mapping, _ = assign(
                apply_stats(first, stats_second, experts, features),
                apply_stats(second, stats_second, experts, features),
                experts,
                features=features,
            )
            reference_is_stable = self_mapping == identity_mapping

        # ---- accuracy after the swap -----------------------------------
        hits: list[bool] = []
        for offset in range(swap_position, len(evaluation)):
            row_index = evaluation[offset]
            observed = representation(
                shift_real[: row_index + 1], outcomes[: row_index + 1], experts, window
            )
            if observed is None:
                continue
            observed_z = apply_stats(observed, stats, experts, features)
            mapping, _ = assign(observed_z, reference_z, experts, features=features)
            hits.append(mapping == permutation)
        scored = [hit for index, hit in enumerate(hits) if index + 1 >= window]
        accuracy = sum(scored) / len(scored) if scored else 0.0

        # ---- C3 as registered: identity on the unshifted control -------
        control_identity = 0
        control_total = 0
        for offset in range(swap_position, len(evaluation)):
            row_index = evaluation[offset]
            observed = representation(
                control_real[: row_index + 1], outcomes[: row_index + 1], experts, window
            )
            if observed is None:
                continue
            observed_z = apply_stats(observed, stats, experts, features)
            mapping, _ = assign(observed_z, reference_z, experts, features=features)
            control_total += 1
            if mapping == identity_mapping:
                control_identity += 1
        control_identity_rate = (
            control_identity / control_total if control_total else 0.0
        )

        windows[str(window)] = {
            "control_identity_rate": control_identity_rate,
            "accuracy": accuracy,
            "reference_is_stable": reference_is_stable,
            "feature_count": len(features),
            "scored_months": len(scored),
        }

    return {
        "source": source,
        "expert_set": set_name,
        "experts": list(experts),
        "representation": rep_name,
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# controls
# ---------------------------------------------------------------------------


def control_no_look_ahead(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
    rep_name: str,
    representation: Representation,
    window: int = 60,
) -> float:
    """C1 — mutate every outcome at and after a probe month; the answer must not move.

    A1 is the representation that needs this most, since differencing changes which
    outcome values are read. The residual is the largest disagreement found.
    """
    evaluation = _evaluation_indices(rows)
    probe = evaluation[len(evaluation) // 2]
    plain = prepare_swapped(rows, experts, probe, shifted=False)
    real = [point["real"] for point in plain]
    outcomes = [float(row["outcome"]) for row in rows]

    def mapping_for(outcome_series: list[float]) -> dict[str, str] | None:
        reference = representation(real[:probe], outcome_series[:probe], experts, window)
        if reference is None:
            return None
        features = _features_of(reference, experts)
        stats = feature_stats(reference, experts, features)
        reference_z = apply_stats(reference, stats, experts, features)
        observed = representation(real[: probe + 1], outcome_series[: probe + 1], experts, window)
        if observed is None:
            return None
        observed_z = apply_stats(observed, stats, experts, features)
        chosen, _ = assign(observed_z, reference_z, experts, features=features)
        return chosen

    baseline = mapping_for(outcomes)
    mutated = list(outcomes)
    for index in range(probe, len(mutated)):
        mutated[index] = mutated[index] * 3.0 + 17.0
    after = mapping_for(mutated)
    if baseline is None or after is None:
        return 0.0
    return 0.0 if baseline == after else 1.0


def control_label_permutation(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
    representation: Representation,
    window: int = 60,
) -> float:
    """C2 — rename the reference names at random; accuracy must collapse toward chance."""
    evaluation = _evaluation_indices(rows)
    swap_position = len(evaluation) // 2
    swap_at = evaluation[swap_position]
    shifted = prepare_swapped(rows, experts, swap_at, shifted=True)
    shift_real = [point["real"] for point in shifted]
    outcomes = [float(row["outcome"]) for row in rows]

    reference = representation(shift_real[:swap_at], outcomes[:swap_at], experts, window)
    if reference is None:
        return 0.0
    features = _features_of(reference, experts)
    stats = feature_stats(reference, experts, features)
    reference_z = apply_stats(reference, stats, experts, features)

    rng = random.Random(SEED)
    shuffled = list(experts)
    rng.shuffle(shuffled)
    rename = {expert: shuffled[index] for index, expert in enumerate(experts)}
    scrambled_z = {rename[expert]: reference_z[expert] for expert in experts}

    permutation = true_permutation(experts)
    hits: list[bool] = []
    for offset in range(swap_position, len(evaluation)):
        row_index = evaluation[offset]
        observed = representation(
            shift_real[: row_index + 1], outcomes[: row_index + 1], experts, window
        )
        if observed is None:
            continue
        observed_z = apply_stats(observed, stats, experts, features)
        mapping, _ = assign(observed_z, scrambled_z, experts, features=features)
        hits.append(mapping == permutation)
    scored = [hit for index, hit in enumerate(hits) if index + 1 >= window]
    return sum(scored) / len(scored) if scored else 0.0


def control_swap_preserves_multiset(
    rows: list[dict[str, object]], experts: tuple[str, ...]
) -> bool:
    """C6 — the cyclic permutation must not change the set of series in a cell.

    B2 and B3 read across experts, so a swap that altered the multiset would be a
    data change rather than a regime shift.
    """
    evaluation = _evaluation_indices(rows)
    swap_at = evaluation[len(evaluation) // 2]
    shifted = prepare_swapped(rows, experts, swap_at, shifted=True)
    original = prepare_swapped(rows, experts, swap_at, shifted=False)
    for index in range(swap_at, len(rows)):
        before = sorted(round(shifted[index]["real"][expert], 12) for expert in experts)
        after = sorted(round(original[index]["real"][expert], 12) for expert in experts)
        if before != after:
            return False
    return True


# ---------------------------------------------------------------------------
# the investigation
# ---------------------------------------------------------------------------


def run_investigation(
    silso_path: Path,
    noaa_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Measure the four registered hypotheses across seven representations."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspots, _ = parse_silso_monthly(silso_path)
    co2, _ = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspots, "co2": co2}

    cells: list[dict[str, object]] = []
    excluded_cells: list[dict[str, object]] = []
    for source, rows_in in observations.items():
        for set_name in EXPERT_SETS:
            experts = EXPERT_SETS[set_name]
            expert_rows = _expert_rows_for(rows_in, experts)  # type: ignore[arg-type]
            for rep_name, representation in REPRESENTATIONS.items():
                try:
                    cell = measure_cell_for(
                        expert_rows, experts, source, set_name, rep_name, representation
                    )
                except ValueError as error:
                    excluded_cells.append(
                        {
                            "source": source,
                            "expert_set": set_name,
                            "representation": rep_name,
                            "reason": str(error),
                        }
                    )
                    continue
                cells.append(cell)

    # ---- per representation: how many cell-windows clear C3? -----------
    summary: dict[str, dict[str, object]] = {}
    for rep_name in REPRESENTATIONS:
        entries = [
            (cell, entry)
            for cell in cells
            if cell["representation"] == rep_name
            for entry in (cell["windows"] or {}).values()  # type: ignore[union-attr]
            if isinstance(entry, dict) and "control_identity_rate" in entry
        ]
        passing = [pair for pair in entries if pair[1]["control_identity_rate"] >= C3_THRESHOLD]
        accuracies = [pair[1]["accuracy"] for pair in passing]
        summary[rep_name] = {
            "cell_windows": len(entries),
            "passing_c3": len(passing),
            "passing_share": len(passing) / len(entries) if entries else 0.0,
            "median_identity_rate": (
                statistics.median(pair[1]["control_identity_rate"] for pair in entries)
                if entries
                else 0.0
            ),
            "mean_accuracy_in_passing": (
                statistics.mean(accuracies) if accuracies else 0.0
            ),
            "feature_count": entries[0][1]["feature_count"] if entries else 0,
        }

    baseline_count = int(summary["R0_baseline"]["passing_c3"])  # type: ignore[arg-type]
    best_name = max(CANDIDATES, key=lambda name: int(summary[name]["passing_c3"]))  # type: ignore[arg-type]
    best_count = int(summary[best_name]["passing_c3"])  # type: ignore[arg-type]
    irrelevant_count = int(summary["X1_irrelevant"]["passing_c3"])  # type: ignore[arg-type]

    # ---- the four registered hypotheses --------------------------------
    h1 = best_count >= 12
    h2 = best_count > irrelevant_count
    h3 = (
        int(summary["A1_first_difference"]["passing_c3"]) > int(summary["B1_full_lag"]["passing_c3"])  # type: ignore[arg-type]
        or int(summary["B3_shared_removed"]["passing_c3"]) > int(summary["B1_full_lag"]["passing_c3"])  # type: ignore[arg-type]
    )
    # H4: cells that newly pass under the best representation must be at least as
    # accurate as the baseline's passing cells.
    baseline_passing = [
        entry
        for cell in cells
        if cell["representation"] == "R0_baseline"
        for entry in (cell["windows"] or {}).values()  # type: ignore[union-attr]
        if isinstance(entry, dict)
        and entry.get("control_identity_rate", 0.0) >= C3_THRESHOLD
    ]
    best_passing = [
        entry
        for cell in cells
        if cell["representation"] == best_name
        for entry in (cell["windows"] or {}).values()  # type: ignore[union-attr]
        if isinstance(entry, dict)
        and entry.get("control_identity_rate", 0.0) >= C3_THRESHOLD
    ]
    baseline_accuracy = (
        statistics.mean(entry["accuracy"] for entry in baseline_passing)
        if baseline_passing
        else 0.0
    )
    best_accuracy = (
        statistics.mean(entry["accuracy"] for entry in best_passing)
        if best_passing
        else 0.0
    )
    h4 = best_accuracy >= baseline_accuracy - 0.05

    # ---- controls ------------------------------------------------------
    sample_rows = None
    sample_experts: tuple[str, ...] = ()
    for source, rows_in in observations.items():
        for set_name, experts in EXPERT_SETS.items():
            sample_rows = _expert_rows_for(rows_in, experts)  # type: ignore[arg-type]
            sample_experts = experts
            break
        break
    no_look_ahead = {}
    label_permutation = {}
    if sample_rows is not None:
        for rep_name, representation in REPRESENTATIONS.items():
            no_look_ahead[rep_name] = control_no_look_ahead(
                sample_rows, sample_experts, rep_name, representation
            )
            label_permutation[rep_name] = control_label_permutation(
                sample_rows, sample_experts, representation
            )

    multiset_ok = bool(
        sample_rows is not None
        and control_swap_preserves_multiset(sample_rows, sample_experts)
    )
    c0_reproduces = baseline_count == 11
    c1_ok = all(value == 0.0 for value in no_look_ahead.values())
    best_scrambled = label_permutation.get(best_name, 0.0)

    if not c0_reproduces or not c1_ok or not multiset_ok:
        verdict = "control_failed"
    elif not h2:
        verdict = "dimension_artefact"
    elif h1 and h3 and h4:
        verdict = "representation_matters"
    else:
        verdict = f"partial:{'+'.join(name for name, held in (('H1', h1), ('H3', h3), ('H4', h4)) if not held)}"

    result: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "verdict": verdict,
        "hypotheses": {"1_representation_matters": h1, "2_not_dimensionality": h2,
                       "3_shared_component_mechanism": h3, "4_rescued_cells_are_real": h4},
        "summary": summary,
        "baseline_passing": baseline_count,
        "best_representation": best_name,
        "best_passing": best_count,
        "irrelevant_passing": irrelevant_count,
        "accuracy": {"baseline_passing_mean": baseline_accuracy,
                     "best_passing_mean": best_accuracy},
        "controls": {
            "C0_reproduces_11": c0_reproduces,
            "C1_no_look_ahead": no_look_ahead,
            "C2_label_permutation": label_permutation,
            "C2_best_scrambled": best_scrambled,
            "C6_multiset_preserved": multiset_ok,
        },
        "cells": cells,
        "excluded_cells": excluded_cells,
    }

    import json

    (output_directory / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    return result
