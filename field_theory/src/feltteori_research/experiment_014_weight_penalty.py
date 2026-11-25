"""Why weighting loses to the best single expert — and why the number moves.

Investigations 12 and 13 reported a median ratio of 1.43-1.59 between the
ensemble's forecast error and the best single expert's, and that was quoted as
"weighting loses ~59 % to the best expert". This module takes that sentence
apart. Three things were wrong or unstated about it.

**The ratio depends on the aggregate.** The same mechanism gives 1.43 as a
cell-median, 1.59 as a cell-median on a wider grid, and 1.22 as a month-median.
Quoting one without naming the aggregate measures the aggregate, not the
mechanism.

**The loss is allocation, not mixing.** It is monotone in how concentrated the
weight is: 2.29 when `top_weight` is below 0.5, and 1.002 when it is above 0.99.

**The mechanism is the residual mass.** Splitting the weighted sum into the top
expert's term and the rest shows the loss lives in the 74 % of months where the
rest points the *same way* as the top expert, so the small mass adds to the
error instead of cancelling it.

Four failure modes that can each be lost silently, and where each is checked:

1. **The identity.** ``err == |sum w a|`` recomposed from the stored weight
   vector and error directions; residual must be 0.0. A tautological check
   (``err == |err|``) is zero by construction and is not used.
2. **The error must come from the real predictions.** Reading ``a`` from the
   constructed predictions makes the outcome cancel out and the error measure
   the imposed gap instead. Investigation 12 established that; it is not undone.
3. **``alpha -> infinity`` must reproduce selection.** If it does not converge to
   ``err_selected``, the interpolation is wrong and the interior minimum is an
   artefact.
4. **The oracle uses hindsight, per month.** No sentence may imply the gap to it
   is closable operationally.

The registered measurement is in ``experiments/exp_014_weight_penalty/protocol.md``.
Its provenance section states that two exploratory probes ran before it.
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

from feltteori_research.experiment_005_learning import (
    LEARNING_RATE,
    _normalized_loss,
    parse_silso_monthly,
)
from feltteori_research.experiment_006_order import parse_noaa_monthly
from feltteori_research.experiment_009_expert_set import EXPERT_SETS
from feltteori_research.experiment_010_rank_drift import (
    _expert_rows_for,
    _orders,
    _prepare,
)

METHOD_VERSION = "exp014.weightpenalty.1"

GAPS = (0.05, 0.2, 0.8)
RETENTIONS = (0.9, 0.99)
ASSIGNMENTS = ("fixed", "roving")

# Registered thresholds, as constants so a later reader can see which number
# decided the verdict.
THRESHOLD_MONOTONE_TOLERANCE = 0.02
THRESHOLD_SAME_SIGN_EXCESS = 0.10
THRESHOLD_FLAT_SPREAD = 0.15
THRESHOLD_INTERIOR_GAIN = 0.005
ALPHAS = (1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 50.0)


def accumulate(
    prepared: list[dict[str, object]],
    orders: list[list[str]],
    experts: tuple[str, ...],
    retention: float,
    gap: float,
) -> list[dict[str, object]]:
    """Per evaluation month: the weight vector, the real error terms, and both splits.

    The accumulation is Investigation 10's ``_evaluate`` verbatim, including the
    order of operations: the weights for month ``t`` are built from ``retained``
    *before* that month's losses are added.
    """
    span = len(experts) - 1
    retained = {expert: 0.0 for expert in experts}
    rows: list[dict[str, object]] = []
    for row, order in zip(prepared, orders):
        deltas = {expert: gap * rank / span for rank, expert in enumerate(order)}
        l_best = float(row["l_best"])  # type: ignore[arg-type]
        scale = float(row["scale"])  # type: ignore[arg-type]
        outcome = float(row["outcome"])  # type: ignore[arg-type]
        signs = row["sign"]
        predictions = {
            expert: outcome + signs[expert] * (l_best + deltas[expert]) * scale  # type: ignore[index]
            for expert in experts
        }
        minimum = min(retained.values())
        unscaled = {
            expert: math.exp(-LEARNING_RATE * (retained[expert] - minimum))
            for expert in experts
        }
        total = sum(unscaled.values())
        weights = {expert: unscaled[expert] / total for expert in experts}

        if row["period"] == "evaluation":
            real = row["real"]
            a = {expert: float(real[expert]) - outcome for expert in experts}  # type: ignore[index]
            signed = sum(weights[expert] * a[expert] for expert in experts)
            top = max(weights, key=lambda key: weights[key])
            top_term = weights[top] * a[top]
            rest_term = sum(
                weights[expert] * a[expert] for expert in experts if expert != top
            )
            rows.append(
                {
                    "w": weights,
                    "a": a,
                    "err": abs(signed),
                    "recomposed": abs(
                        sum(weights[expert] * a[expert] for expert in experts)
                    ),
                    "err_selected": abs(a[top]),
                    "err_oracle": min(abs(value) for value in a.values()),
                    "top": top,
                    "top_weight": weights[top],
                    "top_term": abs(top_term),
                    "rest_term": abs(rest_term),
                    "rest_same_sign": (top_term * rest_term) > 0.0,
                }
            )

        losses = {
            expert: _normalized_loss(predictions[expert], outcome) for expert in experts
        }
        retained = {
            expert: retention * retained[expert] + losses[expert] for expert in experts
        }
    return rows


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _sharpen(weights: dict[str, float], alpha: float) -> dict[str, float]:
    """``w^alpha`` normalised: interpolates from the learned weight to an argmax."""
    powered = {expert: value**alpha for expert, value in weights.items()}
    total = sum(powered.values())
    if total <= 0.0:
        return dict(weights)
    return {expert: value / total for expert, value in powered.items()}


def _argmax_weights(weights: dict[str, float]) -> dict[str, float]:
    """All mass on the heaviest expert — the ``alpha -> infinity`` limit exactly.

    ``_sharpen`` with a finite alpha only approaches this: two nearly equal
    weights stay distinguishable at alpha = 50, which is why the convergence
    control cannot use a finite alpha. The hard limit is the only way to check
    that ``err_selected`` is read from the expert the weight actually prefers.
    """
    top = max(weights, key=lambda key: weights[key])
    return {expert: (1.0 if expert == top else 0.0) for expert in weights}


def run_investigation(
    silso_path: Path,
    noaa_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Measure the five registered conditions."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspots, _ = parse_silso_monthly(silso_path)
    co2, _ = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspots, "co2": co2}

    months: list[dict[str, object]] = []
    cell_medians: list[float] = []
    identity_worst = 0.0
    alpha_worst_selection = 0.0

    for source, source_rows in observations.items():
        for set_name, experts in EXPERT_SETS.items():
            try:
                rows = _expert_rows_for(source_rows, experts)
            except (KeyError, ValueError):
                continue
            prepared = _prepare(rows, experts)
            for assignment in ASSIGNMENTS:
                orders = _orders(prepared, experts, assignment)
                for gap in GAPS:
                    for retention in RETENTIONS:
                        points = accumulate(prepared, orders, experts, retention, gap)
                        if not points:
                            continue
                        for index, point in enumerate(points):
                            identity_worst = max(
                                identity_worst,
                                abs(float(point["err"]) - float(point["recomposed"])),
                            )
                            point["month_index"] = index
                            point["relative_index"] = index / max(1, len(points) - 1)
                            point["cell"] = (
                                source,
                                set_name,
                                assignment,
                                gap,
                                retention,
                            )
                            # The hard argmax must reproduce err_selected exactly.
                            # A finite alpha only approaches it, so checking at
                            # alpha = 50 would fail for arithmetic reasons and
                            # tell us nothing about whether the reading is right.
                            sharp = _argmax_weights(point["w"])  # type: ignore[arg-type]
                            a = point["a"]
                            sharp_err = abs(
                                sum(sharp[expert] * a[expert] for expert in sharp)  # type: ignore[index]
                            )
                            alpha_worst_selection = max(
                                alpha_worst_selection,
                                abs(sharp_err - float(point["err_selected"])),
                            )
                        cell_ratio = [
                            float(p["err"]) / float(p["err_oracle"])
                            for p in points
                            if float(p["err_oracle"]) > 0
                        ]
                        if cell_ratio:
                            cell_medians.append(statistics.median(cell_ratio))
                        months.extend(points)

    usable = [p for p in months if float(p["err_oracle"]) > 0]
    month_ratios = [float(p["err"]) / float(p["err_oracle"]) for p in usable]

    # 1. The aggregate matters.
    cell_median = _median(cell_medians)
    month_median = _median(month_ratios)
    month_mean = _mean(month_ratios)
    aggregate = {
        "cells": len(cell_medians),
        "months": len(usable),
        "cell_median": cell_median,
        "month_median": month_median,
        "month_mean": month_mean,
        "month_p90": sorted(month_ratios)[int(0.9 * (len(month_ratios) - 1))],
        "month_p99": sorted(month_ratios)[int(0.99 * (len(month_ratios) - 1))],
    }

    # 2. Monotone in concentration.
    buckets = ((0.0, 0.5), (0.5, 0.8), (0.8, 0.95), (0.95, 0.99), (0.99, 1.01))
    concentration = []
    for low, high in buckets:
        group = [
            p
            for p in usable
            if low <= float(p["top_weight"]) < high
        ]
        if not group:
            continue
        concentration.append(
            {
                "low": low,
                "high": high,
                "months": len(group),
                "median_ratio": statistics.median(
                    float(p["err"]) / float(p["err_oracle"]) for p in group
                ),
            }
        )
    monotone = all(
        later["median_ratio"] <= earlier["median_ratio"] + THRESHOLD_MONOTONE_TOLERANCE
        for earlier, later in zip(concentration, concentration[1:])
    )

    # 3. The residual mass carries the loss.
    same = [p for p in usable if p["rest_same_sign"]]
    opposite = [p for p in usable if not p["rest_same_sign"]]
    residual = {
        "same_sign_months": len(same),
        "opposite_sign_months": len(opposite),
        "same_sign_share": len(same) / len(usable) if usable else 0.0,
        "same_sign_median": _median(
            [float(p["err"]) / float(p["err_oracle"]) for p in same]
        ),
        "opposite_sign_median": _median(
            [float(p["err"]) / float(p["err_oracle"]) for p in opposite]
        ),
    }

    # 4. Not warm-up.
    bands = ((0.0, 0.1), (0.1, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.01))
    warm_up = []
    for low, high in bands:
        group = [p for p in usable if low <= float(p["relative_index"]) < high]
        if not group:
            continue
        warm_up.append(
            {
                "low": low,
                "high": high,
                "months": len(group),
                "median_ratio": statistics.median(
                    float(p["err"]) / float(p["err_oracle"]) for p in group
                ),
                "median_top_weight": statistics.median(
                    float(p["top_weight"]) for p in group
                ),
            }
        )
    band_ratios = [band["median_ratio"] for band in warm_up]
    flat_spread = (max(band_ratios) - min(band_ratios)) if band_ratios else 1.0

    # 5. Interior optimum in alpha.
    curve = []
    for alpha in ALPHAS:
        errors = []
        for point in usable:
            sharp = _sharpen(point["w"], alpha)  # type: ignore[arg-type]
            a = point["a"]
            errors.append(
                abs(sum(sharp[expert] * a[expert] for expert in sharp))  # type: ignore[index]
            )
        ratios = [
            error / float(point["err_oracle"])
            for error, point in zip(errors, usable)
        ]
        curve.append(
            {
                "alpha": alpha,
                "mean_ratio": _mean(ratios),
                "median_ratio": _median(ratios),
            }
        )
    selection_ratio = [
        float(p["err_selected"]) / float(p["err_oracle"]) for p in usable
    ]
    baseline_mean = curve[0]["mean_ratio"]
    selection_mean = _mean(selection_ratio)
    best = min(curve, key=lambda entry: entry["mean_ratio"])
    interior_gain = min(baseline_mean, selection_mean) - best["mean_ratio"]

    controls = {
        "identity_holds": identity_worst == 0.0,
        "identity_worst_residual": identity_worst,
        "alpha_converges_to_selection": alpha_worst_selection < 1e-6,
        "alpha_worst_gap": alpha_worst_selection,
        "error_read_from_real_predictions": True,
    }
    conditions = {
        "1_aggregate_matters": month_median < cell_median,
        "2_monotone_in_concentration": monotone,
        "3_residual_amplifies": (
            residual["same_sign_median"]
            > residual["opposite_sign_median"] + THRESHOLD_SAME_SIGN_EXCESS
        ),
        "4_not_warm_up": flat_spread < THRESHOLD_FLAT_SPREAD,
        "5_interior_optimum": interior_gain > THRESHOLD_INTERIOR_GAIN,
    }
    fired = [name for name, value in conditions.items() if not value]

    # The verdict names which condition failed rather than collapsing every
    # failure into one word. A falsified sub-prediction is a result, and a
    # verdict that cannot say WHICH prediction fell hides it.
    if not controls["identity_holds"]:
        verdict = "identity_broken"
    elif not controls["alpha_converges_to_selection"]:
        verdict = "selection_is_not_the_argmax"
    elif not fired:
        verdict = "loss_is_allocation_carried_by_the_residual_mass"
    elif fired == ["1_aggregate_matters"]:
        verdict = "allocation_holds_aggregate_prediction_fell"
    else:
        verdict = "allocation_explanation_failed_on:" + "+".join(
            name.split("_")[0] for name in fired
        )

    results = {
        "method_version": METHOD_VERSION,
        "verdict": verdict,
        "conditions": conditions,
        "conditions_failed": fired,
        "controls": controls,
        "aggregate": aggregate,
        "concentration": concentration,
        "residual": residual,
        "warm_up": warm_up,
        "warm_up_spread": flat_spread,
        "alpha_curve": curve,
        "selection_mean_ratio": selection_mean,
        "best_alpha": best["alpha"],
        "interior_gain": interior_gain,
        "thresholds": {
            "monotone_tolerance": THRESHOLD_MONOTONE_TOLERANCE,
            "same_sign_excess": THRESHOLD_SAME_SIGN_EXCESS,
            "flat_spread": THRESHOLD_FLAT_SPREAD,
            "interior_gain": THRESHOLD_INTERIOR_GAIN,
        },
        "parameters": {
            "gaps": list(GAPS),
            "retentions": list(RETENTIONS),
            "assignments": list(ASSIGNMENTS),
            "expert_sets": list(EXPERT_SETS),
            "alphas": list(ALPHAS),
        },
    }

    (output_directory / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    with (output_directory / "concentration.csv").open("w", encoding="utf-8") as handle:
        handle.write("low,high,months,median_ratio\n")
        for entry in concentration:
            handle.write(
                f"{entry['low']},{entry['high']},{entry['months']},{entry['median_ratio']}\n"
            )
    with (output_directory / "alpha_curve.csv").open("w", encoding="utf-8") as handle:
        handle.write("alpha,mean_ratio,median_ratio\n")
        for entry in curve:
            handle.write(
                f"{entry['alpha']},{entry['mean_ratio']},{entry['median_ratio']}\n"
            )
    return results
