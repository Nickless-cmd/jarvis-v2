"""Can the detector's distance be used as self-doubt?

Investigation 18's H5 reported that the distance to the nearest reference grows
when the true name is removed from the pool. That table compares two constructed
conditions the operator never chooses between, and its per-cell sample is three
experts. This module asks the operational question instead: month by month, in
ordinary operation with a complete reference, does the distance to the chosen
name predict whether that choice is correct?

Nothing about the fingerprint, the reference, the windows or the swap changes.
``experiment_018b_lag_fingerprint._match`` already computes the distance for
every name and discards it; this module keeps it and pairs it with the outcome
of the match.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

from .experiment_005_learning import parse_silso_monthly
from .experiment_006_order import parse_noaa_monthly
from .experiment_009_expert_set import EXPERT_SETS, _expert_rows_for
from .experiment_017_regime_shift import prepare_swapped
from .experiment_018_detect_shift import (
    _distance,
    _evaluation_indices,
    apply_stats,
    assign,
    feature_stats,
    identity,
    true_permutation,
)
from .experiment_018b_lag_fingerprint import (
    LAG_FEATURES,
    WINDOWS,
    _reference,
    lag_fingerprint,
)

METHOD_VERSION = "exp_019_distance_as_doubt/1"

BOOTSTRAP = 1000
SEED = 20261125
MIN_SCORED = 40
MIN_COVERAGE = 0.25
QUARTILES = 4
# The protocol's C3 says the unshifted control must return the identity mapping
# but does not name a rate. 0.9 is Investigation 18b's threshold for its own H4.
C3_THRESHOLD = 0.9


def _auc(scores: list[float], labels: list[bool]) -> float:
    """Area under the ROC curve with ``True`` as the positive class.

    Computed directly as the Mann-Whitney statistic so no external dependency
    is involved and ties are handled explicitly.
    """
    positive = [score for score, label in zip(scores, labels) if label]
    negative = [score for score, label in zip(scores, labels) if not label]
    if not positive or not negative:
        return float("nan")
    wins = 0.0
    for pos in positive:
        for neg in negative:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / (len(positive) * len(negative))


def _bootstrap_auc(
    scores: list[float], labels: list[bool], resamples: int = BOOTSTRAP
) -> tuple[float, float]:
    """Percentile interval for the AUC, resampling paired observations."""
    size = len(scores)
    if size < 10:
        return (float("nan"), float("nan"))
    rng = random.Random(SEED)
    values: list[float] = []
    for _ in range(resamples):
        picks = [rng.randrange(size) for _ in range(size)]
        value = _auc([scores[i] for i in picks], [labels[i] for i in picks])
        if value == value:
            values.append(value)
    if not values:
        return (float("nan"), float("nan"))
    values.sort()
    low = values[int(0.025 * (len(values) - 1))]
    high = values[int(0.975 * (len(values) - 1))]
    return (low, high)


def distances_to_all(
    observed_z: dict[str, dict[str, float]],
    reference_z: dict[str, dict[str, float]],
    experts: tuple[str, ...],
) -> dict[str, dict[str, float]]:
    """Every observed name against every reference name.

    ``assign`` only returns the winner; the full matrix is what makes the
    second-nearest name and the margin available, and the margin is a different
    quantity from the distance even though both come from the same row.
    """
    return {
        expert: {
            name: _distance(observed_z[expert], reference_z[name], LAG_FEATURES)
            for name in experts
        }
        for expert in experts
    }


def trace_cell(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
    source: str,
    set_name: str,
) -> dict[str, object]:
    """Per-month distance and correctness after the swap, per window.

    The reference is built from the world before the swap, exactly as in
    Investigation 18b. Every evaluated month after the swap then yields one
    observation: the distance to the chosen name and whether the chosen mapping
    was the true permutation.
    """
    evaluation = _evaluation_indices(rows)
    if len(evaluation) < 40:
        raise ValueError("too few evaluation months to split")
    swap_position = len(evaluation) // 2
    swap_at = evaluation[swap_position]

    shifted = prepare_swapped(rows, experts, swap_at, shifted=True)
    plain = prepare_swapped(rows, experts, swap_at, shifted=False)
    shift_real = [point["real"] for point in shifted]
    control_real = [point["real"] for point in plain]
    outcomes = [float(row["outcome"]) for row in rows]  # type: ignore[arg-type]

    permutation = true_permutation(experts)
    identity_mapping = identity(experts)

    windows: dict[str, object] = {}
    for window in WINDOWS:
        pack = _reference(shift_real, outcomes, experts, window, swap_at)
        if pack is None:
            windows[str(window)] = {"skipped": "reference window too short"}
            continue
        reference, stats = pack
        reference_z = apply_stats(reference, stats, experts, LAG_FEATURES)

        # ---- C4: inherited unchanged from 18b --------------------------
        half = swap_at // 2
        first = lag_fingerprint(shift_real[:half], outcomes[:half], experts, window)
        second = lag_fingerprint(
            shift_real[half:swap_at], outcomes[half:swap_at], experts, window
        )
        reference_is_stable = False
        if first is not None and second is not None:
            stats_second = feature_stats(second, experts, LAG_FEATURES)
            self_mapping, _ = assign(
                apply_stats(first, stats_second, experts, LAG_FEATURES),
                apply_stats(second, stats_second, experts, LAG_FEATURES),
                experts,
                features=LAG_FEATURES,
            )
            reference_is_stable = self_mapping == identity_mapping

        # ---- C2: a reference with its names scrambled must carry no signal
        rng = random.Random(SEED)
        shuffled = list(experts)
        rng.shuffle(shuffled)
        rename = dict(zip(experts, shuffled))
        scrambled_z = {
            rename[name]: values for name, values in reference_z.items()
        }

        observations: list[dict[str, object]] = []
        scrambled_observations: list[dict[str, object]] = []
        for offset in range(swap_position, len(evaluation)):
            row_index = evaluation[offset]
            observed = lag_fingerprint(
                shift_real[: row_index + 1], outcomes[: row_index + 1], experts, window
            )
            if observed is None:
                continue
            observed_z = apply_stats(observed, stats, experts, LAG_FEATURES)
            matrix = distances_to_all(observed_z, reference_z, experts)
            chosen = {
                expert: min(matrix[expert], key=lambda name: matrix[expert][name])
                for expert in experts
            }
            distances = [matrix[expert][chosen[expert]] for expert in experts]
            second_best = []
            for expert in experts:
                ordered = sorted(matrix[expert].values())
                second_best.append(ordered[1] if len(ordered) > 1 else ordered[0])

            observations.append(
                {
                    "offset": offset - swap_position,
                    "distance": statistics.median(distances),
                    "margin": statistics.median(
                        [s - d for s, d in zip(second_best, distances)]
                    ),
                    "hit": chosen == permutation,
                    "settled": (offset - swap_position) + 1 >= window,
                }
            )

            # C2 uses the same observation against a reference whose names are
            # scrambled. The true mapping is unchanged, so a detector with real
            # information must lose its power here.
            scrambled_matrix = distances_to_all(observed_z, scrambled_z, experts)
            scrambled_chosen = {
                expert: min(
                    scrambled_matrix[expert],
                    key=lambda name: scrambled_matrix[expert][name],
                )
                for expert in experts
            }
            scrambled_distances = [
                scrambled_matrix[expert][scrambled_chosen[expert]]
                for expert in experts
            ]
            scrambled_observations.append(
                {
                    "distance": statistics.median(scrambled_distances),
                    "hit": scrambled_chosen == permutation,
                    "settled": (offset - swap_position) + 1 >= window,
                }
            )

        scored = [entry for entry in observations if entry["settled"]]
        if len(scored) < MIN_SCORED:
            windows[str(window)] = {"skipped": "too few settled months"}
            continue

        # ---- H4 needs a split, and it must be in time, not in identity --
        cut = len(scored) // 2
        development = scored[:cut]
        test = scored[cut:]

        # ---- H5: the ordinary distance against 18b's held-out distance --
        settled = lag_fingerprint(shift_real, outcomes, experts, window)
        held_distances: list[float] = []
        if settled is not None:
            settled_z = apply_stats(settled, stats, experts, LAG_FEATURES)
            for expert in experts:
                _, held = assign(
                    settled_z,
                    reference_z,
                    experts,
                    excluded=permutation[expert],
                    features=LAG_FEATURES,
                )
                held_distances.append(held[expert])

        # ---- C3: the unshifted control must return the identity ---------
        # The reference is built from the shifted world, so applying it to the
        # unshifted world must give back the identity mapping. A cell where it
        # does not is not a measurement of detection, only of confusion.
        control_identity = 0
        control_total = 0
        for offset in range(swap_position, len(evaluation)):
            row_index = evaluation[offset]
            control_observed = lag_fingerprint(
                control_real[: row_index + 1],
                outcomes[: row_index + 1],
                experts,
                window,
            )
            if control_observed is None:
                continue
            control_z = apply_stats(control_observed, stats, experts, LAG_FEATURES)
            control_matrix = distances_to_all(control_z, reference_z, experts)
            control_chosen = {
                expert: min(
                    control_matrix[expert],
                    key=lambda name: control_matrix[expert][name],
                )
                for expert in experts
            }
            control_total += 1
            if control_chosen == identity_mapping:
                control_identity += 1
        control_identity_rate = (
            control_identity / control_total if control_total else 0.0
        )

        windows[str(window)] = {
            "reference_is_stable": reference_is_stable,
            "control_identity_rate": control_identity_rate,
            "observations": observations,
            "scrambled": scrambled_observations,
            "development_error_rate": (
                sum(1 for entry in development if not entry["hit"]) / len(development)
                if development
                else float("nan")
            ),
            "test_error_rate": (
                sum(1 for entry in test if not entry["hit"]) / len(test)
                if test
                else float("nan")
            ),
            "held_out_median_distance": (
                statistics.median(held_distances) if held_distances else float("nan")
            ),
        }

    return {
        "source": source,
        "expert_set": set_name,
        "experts": list(experts),
        "swap_date": str(rows[swap_at]["date"]),
        "evaluation_months": len(evaluation),
        "permutation": permutation,
        "windows": windows,
    }


def _quartile_error_rates(
    scores: list[float], labels: list[bool]
) -> list[dict[str, float]]:
    """Error rate per distance quartile. H1 is monotonicity across these."""
    if len(scores) < QUARTILES:
        return []
    order = sorted(range(len(scores)), key=lambda index: scores[index])
    bins: list[dict[str, float]] = []
    for quartile in range(QUARTILES):
        start = quartile * len(order) // QUARTILES
        stop = (quartile + 1) * len(order) // QUARTILES
        members = order[start:stop]
        if not members:
            continue
        errors = sum(1 for index in members if labels[index])
        bins.append(
            {
                "quartile": float(quartile + 1),
                "months": float(len(members)),
                "error_rate": errors / len(members),
                "distance_low": scores[members[0]],
                "distance_high": scores[members[-1]],
            }
        )
    return bins


def _abstention(
    development: list[dict[str, object]], test: list[dict[str, object]]
) -> dict[str, object]:
    """Pick a threshold on development, measure precision on test.

    The threshold maximises development precision subject to keeping at least
    ``MIN_COVERAGE`` of the development months. It is chosen without seeing a
    single test month.
    """
    if not development or not test:
        return {"applicable": False, "reason": "empty split"}
    thresholds = sorted({float(entry["distance"]) for entry in development})
    best: dict[str, object] = {"applicable": False, "reason": "no threshold met coverage"}
    for threshold in thresholds:
        kept = [entry for entry in development if float(entry["distance"]) <= threshold]
        coverage = len(kept) / len(development)
        if coverage < MIN_COVERAGE or not kept:
            continue
        precision = sum(1 for entry in kept if entry["hit"]) / len(kept)
        if not best.get("applicable") or precision > float(best["development_precision"]):
            best = {
                "applicable": True,
                "threshold": threshold,
                "development_precision": precision,
                "development_coverage": coverage,
            }
    if not best.get("applicable"):
        return best
    threshold = float(best["threshold"])
    answered = [entry for entry in test if float(entry["distance"]) <= threshold]
    if not answered:
        best["test_coverage"] = 0.0
        best["test_precision"] = float("nan")
        return best
    best["test_precision"] = sum(1 for entry in answered if entry["hit"]) / len(answered)
    best["test_coverage"] = len(answered) / len(test)
    best["baseline_precision"] = sum(1 for entry in test if entry["hit"]) / len(test)
    # The protocol's registered bar is the complement of the DEVELOPMENT error
    # rate, not the test baseline: the threshold was chosen on development, so
    # development is what it may claim to know. Both bars are reported because
    # the test baseline is the stricter comparison, and hiding it would flatter
    # the result.
    development_error_rate = sum(1 for entry in development if not entry["hit"]) / len(
        development
    )
    best["development_error_rate"] = development_error_rate
    best["protocol_bar"] = 1.0 - development_error_rate
    best["passes_protocol_bar"] = bool(
        float(best["test_precision"]) > float(best["protocol_bar"])
    )
    best["passes_stricter_baseline"] = bool(
        float(best["test_precision"]) > float(best["baseline_precision"])
    )
    return best


def run_investigation(
    silso_path: Path,
    noaa_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Measure the five registered hypotheses."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspots, sunspots_excluded = parse_silso_monthly(silso_path)
    co2, co2_excluded = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspots, "co2": co2}

    cells: list[dict[str, object]] = []
    excluded_cells: list[dict[str, object]] = []
    for source, rows_in in observations.items():
        for set_name in EXPERT_SETS:
            experts = EXPERT_SETS[set_name]
            expert_rows = _expert_rows_for(rows_in, experts)  # type: ignore[arg-type]
            try:
                cell = trace_cell(expert_rows, experts, source, set_name)
            except ValueError as error:
                excluded_cells.append(
                    {"source": source, "expert_set": set_name, "reason": str(error)}
                )
                continue
            cells.append(cell)

    # ---- pooled quantities over every valid cell and window ------------
    pooled_scores: list[float] = []
    pooled_labels: list[bool] = []
    within_scores: list[float] = []
    within_labels: list[bool] = []
    scrambled_scores: list[float] = []
    scrambled_labels: list[bool] = []
    ordinary_distances: list[float] = []
    held_distances: list[float] = []
    valid = 0
    unstable = 0

    for cell in cells:
        windows = cell["windows"]
        assert isinstance(windows, dict)
        for window_key, entry in windows.items():
            if not isinstance(entry, dict) or "observations" not in entry:
                continue
            if not entry.get("reference_is_stable"):
                unstable += 1
                continue
            valid += 1
            entries = [
                item for item in entry["observations"] if item["settled"]  # type: ignore[index]
            ]
            if not entries:
                continue
            mean_distance = statistics.mean(float(item["distance"]) for item in entries)
            for item in entries:
                distance = float(item["distance"])
                label = not bool(item["hit"])
                pooled_scores.append(distance)
                pooled_labels.append(label)
                within_scores.append(distance - mean_distance)
                within_labels.append(label)
            for item in entry["scrambled"]:  # type: ignore[index]
                if not item["settled"]:
                    continue
                scrambled_scores.append(float(item["distance"]))
                scrambled_labels.append(not bool(item["hit"]))
            ordinary_distances.append(
                statistics.median(float(item["distance"]) for item in entries)
            )
            held = float(entry.get("held_out_median_distance", float("nan")))
            if held == held:
                held_distances.append(held)

    # ---- H1: calibration ------------------------------------------------
    quartiles = _quartile_error_rates(pooled_scores, pooled_labels)
    h1 = (
        len(quartiles) == QUARTILES
        and all(
            quartiles[index]["error_rate"] <= quartiles[index + 1]["error_rate"]
            for index in range(len(quartiles) - 1)
        )
    )

    # ---- H2: rank power -------------------------------------------------
    auc = _auc(pooled_scores, pooled_labels)
    auc_low, auc_high = _bootstrap_auc(pooled_scores, pooled_labels)
    h2 = bool(auc == auc and auc > 0.5 and auc_low == auc_low and auc_low > 0.5)

    # ---- H3: the signal is not cell identity ----------------------------
    within_auc = _auc(within_scores, within_labels)
    within_low, within_high = _bootstrap_auc(within_scores, within_labels)
    h3 = bool(
        within_auc == within_auc
        and within_auc > 0.5
        and within_low == within_low
        and within_low > 0.5
    )

    # ---- C2: scrambled reference must lose the power --------------------
    scrambled_auc = _auc(scrambled_scores, scrambled_labels)
    c2 = bool(scrambled_auc != scrambled_auc or scrambled_auc < 0.6)

    # ---- robustness: the same measurement on the strict C3 subset -------
    # C3 is the protocol's identity control: the reference, built from the
    # shifted world, applied to the unshifted world must give back the identity.
    # The protocol did not specify a threshold; 0.9 is the value Investigation
    # 18b used for its own H4. The registered hypotheses stay on the C4 gate, and
    # this block reports what happens when the stricter one is applied, because
    # a conclusion that only survives the looser gate is a weaker claim.
    strict_scores: list[float] = []
    strict_labels: list[bool] = []
    strict_within_scores: list[float] = []
    strict_within_labels: list[bool] = []
    strict_cells = 0
    for cell in cells:
        windows = cell["windows"]
        assert isinstance(windows, dict)
        for window_key, entry in windows.items():
            if not isinstance(entry, dict) or "observations" not in entry:
                continue
            if not entry.get("reference_is_stable"):
                continue
            if float(entry.get("control_identity_rate", 0.0)) < C3_THRESHOLD:
                continue
            entries = [
                item for item in entry["observations"] if item["settled"]  # type: ignore[index]
            ]
            if not entries:
                continue
            strict_cells += 1
            mean_distance = statistics.mean(float(item["distance"]) for item in entries)
            for item in entries:
                distance = float(item["distance"])
                label = not bool(item["hit"])
                strict_scores.append(distance)
                strict_labels.append(label)
                strict_within_scores.append(distance - mean_distance)
                strict_within_labels.append(label)
    strict_auc = _auc(strict_scores, strict_labels)
    strict_low, strict_high = _bootstrap_auc(strict_scores, strict_labels)
    strict_within_auc = _auc(strict_within_scores, strict_within_labels)
    robustness = {
        "c3_threshold": C3_THRESHOLD,
        "strict_cells": strict_cells,
        "strict_months": len(strict_scores),
        "strict_pooled_auc": strict_auc,
        "strict_pooled_interval": [strict_low, strict_high],
        "strict_within_cell_auc": strict_within_auc,
        "strict_quartiles": _quartile_error_rates(strict_scores, strict_labels),
    }

    # ---- H4: abstention chosen on development, measured on test --------
    abstentions: list[dict[str, object]] = []
    for cell in cells:
        windows = cell["windows"]
        assert isinstance(windows, dict)
        for window_key, entry in windows.items():
            if not isinstance(entry, dict) or "observations" not in entry:
                continue
            if not entry.get("reference_is_stable"):
                continue
            scored = [
                item for item in entry["observations"] if item["settled"]  # type: ignore[index]
            ]
            if len(scored) < MIN_SCORED:
                continue
            cut = len(scored) // 2
            result = _abstention(scored[:cut], scored[cut:])
            if result.get("applicable"):
                result["source"] = cell["source"]
                result["expert_set"] = cell["expert_set"]
                result["window"] = int(window_key)
                abstentions.append(result)
    measurable = [
        entry
        for entry in abstentions
        if entry.get("test_precision") is not None
        and float(entry["test_precision"]) == float(entry["test_precision"])
    ]
    h4 = bool(measurable) and all(
        bool(entry["passes_protocol_bar"]) for entry in measurable
    )
    # A cell where the development months contain no error cannot be improved:
    # the protocol bar is then 1.0 and nothing can exceed it. That is a flaw in
    # the registered condition, not a result, so it is counted separately.
    no_error_to_remove = [
        entry for entry in measurable if float(entry["development_error_rate"]) == 0.0
    ]
    improvable = [
        entry
        for entry in measurable
        if float(entry["development_error_rate"]) > 0.0
    ]
    h4_improvable = bool(improvable) and all(
        bool(entry["passes_protocol_bar"]) for entry in improvable
    )

    # ---- H5: does the held-out table transfer to ordinary operation ----
    ordinary_median = (
        statistics.median(ordinary_distances) if ordinary_distances else float("nan")
    )
    held_median = statistics.median(held_distances) if held_distances else float("nan")
    ratio = (
        ordinary_median / held_median
        if held_median == held_median and held_median > 0.0
        else float("nan")
    )
    h5 = bool(ratio == ratio and ratio >= 0.5)

    conditions = {
        "1_calibration_is_monotone": h1,
        "2_distance_separates": h2,
        "3_signal_survives_within_cell": h3,
        "4_abstention_pays": h4,
        "5_held_out_table_transfers": h5,
    }
    supplementary = {
        "4b_abstention_pays_where_improvable": h4_improvable,
        "cells_with_no_development_error": len(no_error_to_remove),
        "cells_where_abstention_could_help": len(improvable),
        "abstentions_passing_stricter_baseline": sum(
            1 for entry in measurable if bool(entry["passes_stricter_baseline"])
        ),
        "abstentions_passing_protocol_bar": sum(
            1 for entry in measurable if bool(entry["passes_protocol_bar"])
        ),
    }
    controls = {
        "scrambled_reference_loses_power": c2,
        "scrambled_auc": scrambled_auc,
        # The scrambled condition makes almost every match wrong, so the
        # positive class dominates and the AUC is pushed far below 0.5 rather
        # than toward it. The control proves the signal disappears; it is a weak
        # null test, and the error rate is reported so that is visible.
        "scrambled_error_rate": (
            sum(1 for label in scrambled_labels if label) / len(scrambled_labels)
            if scrambled_labels
            else float("nan")
        ),
        "valid_cells": valid,
        "unstable_cells": unstable,
        "excluded_cells": len(excluded_cells),
    }

    failed = [name for name, ok in conditions.items() if not ok]
    if not c2:
        verdict = "control_failed:scrambled_reference_keeps_power"
    elif not failed:
        verdict = "distance_is_a_calibrated_doubt_signal"
    else:
        verdict = "partial:" + ",".join(failed)

    result: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "verdict": verdict,
        "conditions": conditions,
        "controls": controls,
        "supplementary": supplementary,
        "robustness": robustness,
        "auc": {
            "pooled": auc,
            "pooled_interval": [auc_low, auc_high],
            "within_cell": within_auc,
            "within_cell_interval": [within_low, within_high],
            "scrambled": scrambled_auc,
            "months": len(pooled_scores),
            "error_rate": (
                sum(1 for label in pooled_labels if label) / len(pooled_labels)
                if pooled_labels
                else float("nan")
            ),
        },
        "quartiles": quartiles,
        "abstentions": abstentions,
        "transfer": {
            "ordinary_median_distance": ordinary_median,
            "held_out_median_distance": held_median,
            "ratio": ratio,
        },
        "excluded_cells": excluded_cells,
        "sources": {
            "sunspots_excluded": sunspots_excluded,
            "co2_excluded": co2_excluded,
        },
        "cells": cells,
    }
    (output_directory / "results.json").write_text(json.dumps(result, indent=1))
    return result
