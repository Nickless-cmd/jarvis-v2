"""Can a regime shift be detected before the outcome?

Investigations 8-17 all grade the mechanism against an outcome that has already
happened. This one asks the operational question: before this month's outcome is
known, can the mechanism tell that the world has changed?

The shift is Investigation 17's — a cyclic exchange of prediction series between
expert names — but placed at the **evaluation midpoint** instead of in the
warmup. Investigation 17's placement put the shift 1281 months before the first
evaluated month, so its delay was not measured from the shift. That is corrected
here and recorded in the protocol.

The structural point the module is built around: the shift is a *permutation* of
the prediction columns. Any statistic symmetric in the expert names is therefore
exactly invariant and has zero power. Only a name-aware statistic can see the
shift, and the one registered here is a fingerprint of the shape of each name's
prediction stream.
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

from .experiment_005_learning import parse_silso_monthly
from .experiment_006_order import parse_noaa_monthly
from .experiment_009_expert_set import EXPERT_SETS, _expert_rows_for
from .experiment_010_rank_drift import _orders, _prepare
from .experiment_016_alpha_ex_ante import accumulate_ex_ante
from .experiment_017_regime_shift import prepare_swapped

METHOD_VERSION = "exp_018_detect_shift/1"

WINDOWS = (6, 12, 24, 36)
ASSIGNMENT = "roving"
# The fingerprint reads the prediction streams, which do not depend on the memory
# knobs. One retention and one gap are enough to materialise the rows; that
# independence is itself part of the result.
RETENTION = 0.5
GAP = 0.2

FEATURES = ("f_step", "f_ac1", "f_tie")

EXACT = 1e-12
EPS = 1e-9
# A detection counts only when it is right and stays right: at least this share
# of the remaining months must also be right. One lucky month is not a detection.
STABLE_SHARE = 0.9


# ---------------------------------------------------------------------------
# fingerprint
# ---------------------------------------------------------------------------


def _ac1(values: list[float]) -> float:
    """Lag-1 autocorrelation of a short series. Scale-free by construction."""
    n = len(values)
    if n < 3:
        return 0.0
    mean = statistics.mean(values)
    numerator = sum((values[i] - mean) * (values[i - 1] - mean) for i in range(1, n))
    denominator = sum((value - mean) ** 2 for value in values)
    return numerator / denominator if denominator > 0.0 else 0.0


def fingerprint(
    history: list[dict[str, float]],
    experts: tuple[str, ...],
    window: int,
) -> dict[str, dict[str, float]] | None:
    """Shape of each name's prediction stream over the trailing ``window``.

    ``history`` is a list of ``real`` dicts in date order. Only predictions are
    read — never an outcome, never ``scale`` — so the features are computable at
    month ``t`` from data the mechanism actually holds.
    """
    if len(history) < window or window < 3:
        return None
    tail = history[-window:]
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        values = [float(point[expert]) for point in tail]
        steps = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
        median = statistics.median(values)
        spread = statistics.mean([abs(value - median) for value in values])
        ties = sum(1 for i in range(1, len(values)) if values[i] == values[i - 1])
        out[expert] = {
            "f_step": statistics.mean(steps) / (spread + EPS),
            "f_ac1": _ac1(values),
            "f_tie": ties / max(len(values) - 1, 1),
        }
    return out


def feature_stats(
    reference: dict[str, dict[str, float]],
    experts: tuple[str, ...],
    features: tuple[str, ...] = FEATURES,
) -> dict[str, tuple[float, float]]:
    """Mean and spread per feature across the reference names.

    These are the coordinates the observation is later expressed in. Measuring a
    distance in the observation's *own* coordinates would compare two different
    spaces and mean nothing.
    """
    stats: dict[str, tuple[float, float]] = {}
    for feature in features:
        values = [reference[expert][feature] for expert in experts]
        spread = statistics.pstdev(values)
        stats[feature] = (statistics.mean(values), spread if spread > 0.0 else 1.0)
    return stats


def apply_stats(
    values: dict[str, dict[str, float]],
    stats: dict[str, tuple[float, float]],
    experts: tuple[str, ...],
    features: tuple[str, ...] = FEATURES,
) -> dict[str, dict[str, float]]:
    """Express ``values`` in the reference's coordinates."""
    return {
        expert: {
            feature: (values[expert][feature] - stats[feature][0]) / stats[feature][1]
            for feature in features
        }
        for expert in experts
    }


def _distance(
    left: dict[str, float],
    right: dict[str, float],
    features: tuple[str, ...] = FEATURES,
) -> float:
    return math.sqrt(sum((left[f] - right[f]) ** 2 for f in features))


def assign(
    observed_z: dict[str, dict[str, float]],
    reference_z: dict[str, dict[str, float]],
    experts: tuple[str, ...],
    excluded: str | None = None,
    features: tuple[str, ...] = FEATURES,
) -> tuple[dict[str, str], dict[str, float]]:
    """Nearest reference name for each observed stream, plus the distances.

    ``excluded`` removes one reference name from the pool, which is how the
    held-out case is built: the detector is asked to recognise a world it has
    no reference for, and it will answer anyway.
    """
    pool = [expert for expert in experts if expert != excluded]
    mapping: dict[str, str] = {}
    distances: dict[str, float] = {}
    for expert in experts:
        best = min(
            pool, key=lambda name: _distance(observed_z[expert], reference_z[name], features)
        )
        mapping[expert] = best
        distances[expert] = _distance(observed_z[expert], reference_z[best], features)
    return mapping, distances


def true_permutation(experts: tuple[str, ...]) -> dict[str, str]:
    """After the swap, name ``i`` delivers the series of name ``i+1``."""
    span = len(experts)
    return {experts[i]: experts[(i + 1) % span] for i in range(span)}


def identity(experts: tuple[str, ...]) -> dict[str, str]:
    return {expert: expert for expert in experts}


# ---------------------------------------------------------------------------
# name-symmetric statistics (the class with exactly zero power)
# ---------------------------------------------------------------------------


def symmetric_statistics(
    real: dict[str, float], experts: tuple[str, ...]
) -> dict[str, object]:
    """Statistics unchanged by any permutation of the expert names."""
    values = [float(real[expert]) for expert in experts]
    ordered = sorted(values)
    mean = statistics.mean(values)
    return {
        "sorted": ordered,
        "mean": mean,
        "spread": ordered[-1] - ordered[0],
        "mad": statistics.mean([abs(value - mean) for value in values]),
    }


# ---------------------------------------------------------------------------
# one cell
# ---------------------------------------------------------------------------


def _evaluation_indices(rows: list[dict[str, object]]) -> list[int]:
    return [index for index, row in enumerate(rows) if row["period"] == "evaluation"]


def measure_cell(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
    source: str,
    set_name: str,
) -> dict[str, object]:
    """Place the shift at the evaluation midpoint and measure detection."""
    evaluation = _evaluation_indices(rows)
    if len(evaluation) < 40:
        raise ValueError("too few evaluation months to split")
    swap_position = len(evaluation) // 2
    swap_at = evaluation[swap_position]
    swap_date = str(rows[swap_at]["date"])

    plain = prepare_swapped(rows, experts, swap_at, shifted=False)
    shifted = prepare_swapped(rows, experts, swap_at, shifted=True)

    control_points = accumulate_ex_ante(
        plain, _orders(plain, experts, ASSIGNMENT), experts, RETENTION, GAP
    )
    shift_points = accumulate_ex_ante(
        shifted, _orders(shifted, experts, ASSIGNMENT), experts, RETENTION, GAP
    )

    # ---- C2: the swap is a permutation, not a data change ---------------
    permutation_worst = 0.0
    for index in range(swap_at, len(rows)):
        before = sorted(float(rows[index][f"prediction_{e}"]) for e in experts)
        after = sorted(
            float(rows[index][f"prediction_{experts[(i + 1) % len(experts)]}"])
            for i in range(len(experts))
        )
        permutation_worst = max(
            permutation_worst, max(abs(a - b) for a, b in zip(before, after))
        )

    # ---- C3: the unshifted path is `_prepare` ---------------------------
    no_swap_is_fixed_point = plain == _prepare(rows, experts)

    # ---- H1: the symmetric class is exactly invariant -------------------
    symmetric_worst = 0.0
    for control_point, shift_point in zip(control_points, shift_points):
        left = symmetric_statistics(control_point["real"], experts)  # type: ignore[arg-type]
        right = symmetric_statistics(shift_point["real"], experts)  # type: ignore[arg-type]
        symmetric_worst = max(
            symmetric_worst,
            abs(float(left["mean"]) - float(right["mean"])),
            abs(float(left["spread"]) - float(right["spread"])),
            abs(float(left["mad"]) - float(right["mad"])),
            max(
                abs(a - b)
                for a, b in zip(left["sorted"], right["sorted"])  # type: ignore[arg-type]
            ),
        )

    # ---- prediction history per run, evaluation months only -------------
    control_real = [control_point["real"] for control_point in control_points]
    shift_real = [shift_point["real"] for shift_point in shift_points]
    if len(control_real) != len(shift_real):
        raise ValueError("shifted and control runs disagree on month count")

    permutation = true_permutation(experts)
    identity_mapping = identity(experts)

    windows: dict[str, object] = {}
    for window in WINDOWS:
        if swap_position < window:
            windows[str(window)] = {"skipped": "not enough pre-shift months"}
            continue

        reference_shift = fingerprint(shift_real[:swap_position], experts, window)
        reference_control = fingerprint(control_real[:swap_position], experts, window)
        if reference_shift is None or reference_control is None:
            windows[str(window)] = {"skipped": "reference window too short"}
            continue

        stats_shift = feature_stats(reference_shift, experts)
        stats_control = feature_stats(reference_control, experts)
        reference_z = apply_stats(reference_shift, stats_shift, experts)
        reference_z_control = apply_stats(reference_control, stats_control, experts)

        # ---- C4: the reference identifies a name against itself ----------
        half = swap_position // 2
        first = fingerprint(shift_real[:half], experts, window)
        second = fingerprint(shift_real[half:swap_position], experts, window)
        if first is None or second is None:
            windows[str(window)] = {"skipped": "pre-shift halves too short"}
            continue
        stats_second = feature_stats(second, experts)
        self_mapping, _ = assign(
            apply_stats(first, stats_second, experts),
            apply_stats(second, stats_second, experts),
            experts,
        )
        reference_is_stable = self_mapping == identity_mapping

        # ---- H2/H3: detection on the shifted run ------------------------
        hits: list[bool] = []
        for offset in range(swap_position, len(shift_real)):
            observed = fingerprint(shift_real[: offset + 1], experts, window)
            if observed is None:
                hits.append(False)
                continue
            mapping, _ = assign(
                apply_stats(observed, stats_shift, experts), reference_z, experts
            )
            hits.append(mapping == permutation)

        detection_delay = len(hits)
        for index in range(len(hits)):
            remaining = hits[index:]
            if hits[index] and sum(remaining) / len(remaining) >= STABLE_SHARE:
                detection_delay = index
                break

        # Accuracy is measured only once the trailing window is entirely
        # post-shift; before that the detector is reading a mixture, and the
        # mixture is the delay rather than an error.
        scored = [hit for index, hit in enumerate(hits) if index + 1 >= window]
        accuracy = sum(scored) / len(scored) if scored else 0.0

        # ---- H4: the control run must return the identity ---------------
        control_identity = 0
        control_total = 0
        for offset in range(swap_position, len(control_real)):
            observed = fingerprint(control_real[: offset + 1], experts, window)
            if observed is None:
                continue
            mapping, _ = assign(
                apply_stats(observed, stats_control, experts),
                reference_z_control,
                experts,
            )
            control_total += 1
            if mapping == identity_mapping:
                control_identity += 1
        control_identity_rate = (
            control_identity / control_total if control_total else 0.0
        )

        # ---- H5: held-out reference, and whether the distance separates --
        settled = fingerprint(shift_real, experts, window)
        held_distances: list[float] = []
        true_distances: list[float] = []
        held_wrong = 0
        held_total = 0
        if settled is not None:
            settled_z = apply_stats(settled, stats_shift, experts)
            for expert in experts:
                excluded = permutation[expert]
                _, held = assign(settled_z, reference_z, experts, excluded=excluded)
                _, matched = assign(settled_z, reference_z, experts)
                held_distances.append(held[expert])
                true_distances.append(matched[expert])
                held_total += 1
                if held[expert] != excluded:
                    held_wrong += 1

        windows[str(window)] = {
            "accuracy": accuracy,
            "detection_delay": detection_delay,
            "post_shift_months": len(hits),
            "control_identity_rate": control_identity_rate,
            "reference_is_stable": reference_is_stable,
            "self_mapping": self_mapping,
            "held_out_median_distance": (
                statistics.median(held_distances) if held_distances else float("nan")
            ),
            "true_match_median_distance": (
                statistics.median(true_distances) if true_distances else float("nan")
            ),
            "held_out_wrong": held_wrong,
            "held_out_total": held_total,
        }

    return {
        "source": source,
        "expert_set": set_name,
        "experts": list(experts),
        "swap_date": swap_date,
        "swap_position": swap_position,
        "evaluation_months": len(evaluation),
        "pre_shift_months": swap_position,
        "post_shift_months": len(evaluation) - swap_position,
        "permutation": permutation,
        "permutation_worst": permutation_worst,
        "no_swap_is_fixed_point": no_swap_is_fixed_point,
        "symmetric_worst": symmetric_worst,
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# control that can kill the run
# ---------------------------------------------------------------------------


def outcome_is_invisible(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
) -> float:
    """C1 — mutate every outcome; the fingerprint must not move.

    A contaminated detector would read ``outcome`` or ``scale`` and would change.
    """
    evaluation = _evaluation_indices(rows)
    swap_at = evaluation[len(evaluation) // 2]
    mutated: list[dict[str, object]] = []
    for row in rows:
        copy = dict(row)
        copy["outcome"] = float(row["outcome"]) * 1.7 + 3.0  # type: ignore[arg-type]
        mutated.append(copy)

    worst = 0.0
    for window in WINDOWS:
        plain = prepare_swapped(rows, experts, swap_at, shifted=True)
        changed = prepare_swapped(mutated, experts, swap_at, shifted=True)
        real_a = [point["real"] for point in plain]
        real_b = [point["real"] for point in changed]
        left = fingerprint(real_a, experts, window)
        right = fingerprint(real_b, experts, window)
        if left is None or right is None:
            continue
        for expert in experts:
            for feature in FEATURES:
                worst = max(worst, abs(left[expert][feature] - right[expert][feature]))
    return worst


# ---------------------------------------------------------------------------
# entrypoint
# ---------------------------------------------------------------------------


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
    outcome_worst = 0.0
    for source, rows_in in observations.items():
        for set_name in EXPERT_SETS:
            experts = EXPERT_SETS[set_name]
            expert_rows = _expert_rows_for(rows_in, experts)  # type: ignore[arg-type]
            cells.append(measure_cell(expert_rows, experts, source, set_name))
            outcome_worst = max(
                outcome_worst, outcome_is_invisible(expert_rows, experts)
            )

    # ---- controls -------------------------------------------------------
    permutation_worst = max(float(cell["permutation_worst"]) for cell in cells)
    symmetric_worst = max(float(cell["symmetric_worst"]) for cell in cells)
    fixed_point = all(bool(cell["no_swap_is_fixed_point"]) for cell in cells)
    stable = all(
        bool(window.get("reference_is_stable", True))
        for cell in cells
        for window in cell["windows"].values()  # type: ignore[union-attr]
    )

    controls = {
        "detector_cannot_see_outcome": outcome_worst <= EXACT,
        "outcome_mutation_worst": outcome_worst,
        "swap_is_permutation": permutation_worst <= EXACT,
        "permutation_worst_residual": permutation_worst,
        "no_swap_is_fixed_point": fixed_point,
        "reference_is_stable": stable,
    }

    # ---- H1 -------------------------------------------------------------
    h1 = symmetric_worst <= EXACT

    # ---- per-window aggregates -----------------------------------------
    aggregates: dict[str, dict[str, float]] = {}
    for window in WINDOWS:
        key = str(window)
        entries = [
            cell["windows"][key]  # type: ignore[index]
            for cell in cells
            if key in cell["windows"]
            and "accuracy" in cell["windows"][key]  # type: ignore[index]
        ]
        if not entries:
            continue
        aggregates[key] = {
            "cells": float(len(entries)),
            "accuracy_median": statistics.median(
                float(entry["accuracy"]) for entry in entries
            ),
            "delay_median": statistics.median(
                float(entry["detection_delay"]) for entry in entries
            ),
            "control_identity_median": statistics.median(
                float(entry["control_identity_rate"]) for entry in entries
            ),
            "held_out_distance_median": statistics.median(
                float(entry["held_out_median_distance"]) for entry in entries
            ),
            "true_distance_median": statistics.median(
                float(entry["true_match_median_distance"]) for entry in entries
            ),
        }

    # ---- H2: recognition works at some window --------------------------
    h2 = any(entry["accuracy_median"] >= 0.9 for entry in aggregates.values())

    # ---- H3: shorter window detects sooner and identifies worse --------
    ordered = [aggregates[str(w)] for w in WINDOWS if str(w) in aggregates]
    h3 = (
        len(ordered) >= 2
        and all(
            ordered[i]["delay_median"] <= ordered[i + 1]["delay_median"]
            for i in range(len(ordered) - 1)
        )
        and all(
            ordered[i]["accuracy_median"] <= ordered[i + 1]["accuracy_median"]
            for i in range(len(ordered) - 1)
        )
    )

    # ---- H4: the control returns the identity --------------------------
    h4 = bool(aggregates) and all(
        entry["control_identity_median"] >= 0.9 for entry in aggregates.values()
    )

    # ---- H5: held-out distances separate from true-match distances -----
    h5 = bool(aggregates) and all(
        entry["held_out_distance_median"] > entry["true_distance_median"]
        for entry in aggregates.values()
    )

    conditions = {
        "1_symmetric_class_has_zero_power": bool(h1),
        "2_recognition_works": bool(h2),
        "3_frontier_is_monotone": bool(h3),
        "4_control_returns_identity": bool(h4),
        "5_held_out_distance_separates": bool(h5),
    }

    failed = [name for name, ok in conditions.items() if not ok]
    if not controls["detector_cannot_see_outcome"]:
        verdict = "control_failed:detector_sees_outcome"
    elif not controls["swap_is_permutation"]:
        verdict = "control_failed:swap_is_not_a_permutation"
    elif not controls["no_swap_is_fixed_point"]:
        verdict = "control_failed:fixed_point"
    elif not controls["reference_is_stable"]:
        verdict = "control_failed:reference_unstable"
    elif not failed:
        verdict = "shift_is_detectable_before_the_outcome"
    else:
        verdict = "partial:" + ",".join(failed)

    results: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "verdict": verdict,
        "conditions": conditions,
        "conditions_failed": failed,
        "controls": controls,
        "symmetric_worst_residual": symmetric_worst,
        "windows": {str(w): aggregates.get(str(w), {}) for w in WINDOWS},
        "parameters": {
            "windows": list(WINDOWS),
            "assignment": ASSIGNMENT,
            "retention": RETENTION,
            "gap": GAP,
            "features": list(FEATURES),
            "stable_share": STABLE_SHARE,
        },
        "excluded": {"sunspots": sunspots_excluded, "co2": co2_excluded},
        "cells": cells,
    }

    (output_directory / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True), encoding="utf-8"
    )
    return results
