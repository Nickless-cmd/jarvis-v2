"""Four measures instead of one threshold statistic.

Investigation 10 closed with its own instrument as the open problem: a single
number, ``mean_effective_experts < 0.5*N``, measures an *equilibrium* in
``fixed`` assignment and an *occupancy* in ``roving``, and the two cannot be
compared. This module replaces it with four:

``occupancy``           fraction of evaluation months below the floor
``persistence``         mean length of a collapse run, in months
``recovery``            mean length of a healthy run, in months
``identity_stability``  fraction of months the dominant expert is unchanged

The protocol (``experiments/exp_011_four_measures/PROTOCOL.md``) was committed
before this module existed, so ``git log`` proves the ordering.

**The prediction the protocol is built to break.** The first three are not
independent. By construction ``O*T = K*P`` and ``(1-O)*T = K'*R``, so

    P/(P+R) = O*K' / (O*K' + (1-O)*K)

and because collapse and healthy runs alternate, ``|K-K'| <= 1``. Hence on every
cell with ``K = K'`` the identity ``O = P/(P+R)`` holds exactly, and the first
three measures span two degrees of freedom rather than three. That is written
into the protocol as a prediction, not discovered here.

The consequence is the real question: if three collapse to two, is the fourth an
independent axis at all? Condition 3 answers that by looking for a pair of cells
with the same occupancy and different identity stability.

Only the per-month series is new. The mechanism — ``_prepare``, ``_orders``,
``_evaluate`` — is Investigation 10's, imported unchanged, and two controls prove
the new series reproduces the aggregate it replaces.
"""

from __future__ import annotations

import csv
import json
import math
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from feltteori_research.experiment_005_learning import (
    LEARNING_RATE,
    _normalized_loss,
    colon_sha256,
    parse_silso_monthly,
)
from feltteori_research.experiment_006_order import parse_noaa_monthly
from feltteori_research.experiment_009_expert_set import (
    EXPERT_SETS,
    THRESHOLD_FRACTION,
    _expert_rows_for,
)
from feltteori_research.experiment_010_rank_drift import (
    ASSIGNMENTS,
    SYNTHETIC_SEED,
    _evaluate,
    _orders,
    _prepare,
    _synthetic_orders,
)

METHOD_VERSION = "exp011.fourmeasures.1"

# Frozen in the protocol. Three gaps spanning below, at and above the measured
# fixed thresholds (0.02 at r=0.99, 0.2 at r=0.9) so every cell is not simply
# "collapsed" or "not collapsed" for the same reason as its neighbours.
GAPS_MEASURED = (0.05, 0.2, 0.8)
RETENTIONS_MEASURED = (0.9, 0.99)
SYNTHETIC_COUNT = 400

# Frozen tolerances.
IDENTITY_TOLERANCE = 1e-12
SERIES_TOLERANCE = 1e-9
OCCUPANCY_PAIR_TOLERANCE = 0.05
IDENTITY_PAIR_THRESHOLD = 0.30


def _measure_series(
    prepared: list[dict[str, object]],
    retention: float,
    gap: float,
    orders: list[list[str]],
    experts: tuple[str, ...],
) -> dict[str, object]:
    """Per-month effective count and dominant expert over the evaluation window.

    The accumulation is Investigation 10's ``_evaluate`` verbatim, including the
    order of operations: the weights for month ``t`` are built from ``retained``
    *before* that month's losses are added, so the dominant expert recorded here
    is the one that governed the month, not the one that governs the month after.

    Ties in the dominant expert are broken by the tuple order, so the measure is
    deterministic and does not depend on dict iteration order.
    """
    span = len(experts) - 1
    floor = THRESHOLD_FRACTION * len(experts)
    retained = {expert: 0.0 for expert in experts}
    effective_series: list[float] = []
    dominant_series: list[str] = []
    top_weight_series: list[float] = []
    top_margin_series: list[float] = []

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
            effective_series.append(
                1.0 / sum(weight * weight for weight in weights.values())
            )
            # The weight is exp(-LR * (retained - min)), so the expert that
            # governs the month is the one with the LOWEST accumulated loss.
            # Taking the maximum here measures the least influential expert
            # instead — measured 2026-11-25 on the SILSO source: argmax(retained)
            # agreed with argmax(weight) in 1 of 3198 months, argmin in 3198.
            # Tuple order breaks ties.
            dominant_series.append(
                min(experts, key=lambda expert: (retained[expert], experts.index(expert)))
            )
            # ``dominance_share`` and ``identity_stability`` are both derived from
            # *who* holds the top rank, never from *how much* power the top rank
            # carries. Two systems with constant weights 34/33/33 and 60/20/20
            # give identical dominance_share (1.000), identity_stability (1.000)
            # and distinct_dominants (1) while their power distribution is not
            # comparable. These two series carry the continuous distribution the
            # rank-based measures discard.
            ranked_weights = sorted(weights.values(), reverse=True)
            top_weight_series.append(ranked_weights[0])
            top_margin_series.append(
                ranked_weights[0] - ranked_weights[1] if len(ranked_weights) > 1 else 0.0
            )

        losses = {
            expert: _normalized_loss(predictions[expert], outcome) for expert in experts
        }
        retained = {
            expert: retention * retained[expert] + losses[expert] for expert in experts
        }

    if not effective_series:
        raise ValueError("no evaluation rows")
    return {
        "effective": effective_series,
        "dominant": dominant_series,
        "top_weight": top_weight_series,
        "top_margin": top_margin_series,
        "floor": floor,
        "rows": len(effective_series),
    }


def _runs(flags: list[bool]) -> list[tuple[bool, int]]:
    """Maximal contiguous runs as ``(value, length)``, in order."""
    if not flags:
        return []
    runs: list[tuple[bool, int]] = []
    current = flags[0]
    length = 1
    for flag in flags[1:]:
        if flag == current:
            length += 1
        else:
            runs.append((current, length))
            current = flag
            length = 1
    runs.append((current, length))
    return runs


def _four_measures(series: dict[str, object]) -> dict[str, object]:
    """Occupancy, persistence, recovery and identity stability from one series.

    Undefined is reported as ``None``, never as zero: a cell that never collapses
    has no persistence, and a cell that never recovers has no recovery. Reporting
    either as 0.0 is the exact conflation Investigation 10 had to correct.
    """
    effective = list(series["effective"])  # type: ignore[arg-type]
    dominant = list(series["dominant"])  # type: ignore[arg-type]
    top_weight = list(series["top_weight"])  # type: ignore[arg-type]
    top_margin = list(series["top_margin"])  # type: ignore[arg-type]
    floor = float(series["floor"])  # type: ignore[arg-type]
    count = len(effective)

    collapsed = [value < floor for value in effective]
    runs = _runs(collapsed)
    collapse_runs = [length for value, length in runs if value]
    healthy_runs = [length for value, length in runs if not value]

    below = sum(collapse_runs)
    occupancy = below / count
    run_count = len(collapse_runs)
    healthy_run_count = len(healthy_runs)

    persistence = below / run_count if run_count else None
    recovery = (
        (count - below) / healthy_run_count if healthy_run_count else None
    )

    switches = sum(
        1 for index in range(1, count) if dominant[index] != dominant[index - 1]
    )
    identity_stability = 1.0 - switches / (count - 1) if count > 1 else None

    # ``identity_stability`` alone turned out to be a grab-bag, the same way
    # "duty cycle" was in Investigation 10: it measures the *frequency* of
    # transitions and nothing about how the dominance is distributed. Measured
    # 2026-11-25 on the preserved sources: one cell has ~51 switches but a single
    # expert holding 72.6% of the window, while another has zero switches and one
    # expert holding 100%. ``dominance_share`` and ``switches_per_month`` separate
    # what ``identity_stability`` merged, and they are reported alongside it
    # rather than replacing it — the frozen condition was tested on the original
    # definition and stays tested on it.
    dominance = Counter(dominant)
    dominance_share = max(dominance.values()) / count if count else None
    switches_per_month = switches / (count - 1) if count > 1 else None

    residual = None
    if run_count and run_count == healthy_run_count:
        residual = abs(occupancy - persistence / (persistence + recovery))  # type: ignore[operator]

    return {
        "rows": count,
        "floor": floor,
        "occupancy": occupancy,
        "persistence": persistence,
        "recovery": recovery,
        "identity_stability": identity_stability,
        "dominance_share": dominance_share,
        "switches_per_month": switches_per_month,
        "distinct_dominants": len(set(dominant)),
        "collapse_runs": run_count,
        "healthy_runs": healthy_run_count,
        "longest_collapse": max(collapse_runs) if collapse_runs else None,
        "longest_healthy": max(healthy_runs) if healthy_runs else None,
        "identity_residual": residual,
        "mean_effective_experts": sum(effective) / count,
        "min_effective_experts": min(effective),
        "max_effective_experts": max(effective),
        "mean_top_weight": sum(top_weight) / count,
        "mean_top_margin": sum(top_margin) / count,
        "min_top_weight": min(top_weight),
        "max_top_weight": max(top_weight),
    }


def _cell(
    measures: dict[str, object], label: dict[str, object], aggregate: dict[str, object]
) -> dict[str, object]:
    """One row of the results table, with the control differences attached."""
    return {
        **label,
        **measures,
        "duty_cycle_investigation_10": aggregate["duty_cycle"],
        "occupancy_difference": abs(
            float(measures["occupancy"]) - float(aggregate["duty_cycle"])
        ),
        "mean_difference": abs(
            float(measures["mean_effective_experts"])
            - float(aggregate["mean_effective_experts"])
        ),
        "min_difference": abs(
            float(measures["min_effective_experts"])
            - float(aggregate["min_effective_experts"])
        ),
    }


def _control_occupancy(cells: list[dict[str, object]]) -> dict[str, object]:
    """Occupancy must equal Investigation 10's ``duty_cycle`` on every cell."""
    worst = max((float(cell["occupancy_difference"]) for cell in cells), default=0.0)
    offenders = [
        {key: cell[key] for key in ("source", "expert_set", "assignment", "gap", "retention")}
        for cell in cells
        if float(cell["occupancy_difference"]) > IDENTITY_TOLERANCE
    ]
    return {"passed": worst <= IDENTITY_TOLERANCE, "worst_difference": worst, "offenders": offenders}


def _control_series_reconstructs(cells: list[dict[str, object]]) -> dict[str, object]:
    """The per-month series must reproduce the aggregate it replaces."""
    worst = max(
        (
            max(float(cell["mean_difference"]), float(cell["min_difference"]))
            for cell in cells
        ),
        default=0.0,
    )
    return {"passed": worst <= SERIES_TOLERANCE, "worst_difference": worst}


def _control_runs_maximal(cells: list[dict[str, object]]) -> dict[str, object]:
    """Run counting must be consistent with the occupancy it produced.

    ``K`` and ``K'`` differ by at most one because the two kinds alternate. A
    counting bug — an off-by-one at the boundary, or a run merged across a
    transition — shows up here before it reaches a verdict.
    """
    offenders: list[dict[str, object]] = []
    for cell in cells:
        runs = int(cell["collapse_runs"])
        healthy = int(cell["healthy_runs"])
        if abs(runs - healthy) > 1:
            offenders.append(
                {
                    "source": cell["source"],
                    "expert_set": cell["expert_set"],
                    "assignment": cell["assignment"],
                    "gap": cell["gap"],
                    "retention": cell["retention"],
                    "collapse_runs": runs,
                    "healthy_runs": healthy,
                }
            )
    return {"passed": not offenders, "offenders": offenders}


def _condition_identity(cells: list[dict[str, object]]) -> dict[str, object]:
    """Condition 1: ``O = P/(P+R)`` must hold exactly where ``K = K'``."""
    checked = [
        cell
        for cell in cells
        if cell["identity_residual"] is not None
    ]
    worst = max((float(cell["identity_residual"]) for cell in checked), default=0.0)
    offenders = [
        {
            "source": cell["source"],
            "expert_set": cell["expert_set"],
            "assignment": cell["assignment"],
            "gap": cell["gap"],
            "retention": cell["retention"],
            "occupancy": cell["occupancy"],
            "residual": cell["identity_residual"],
        }
        for cell in checked
        if float(cell["identity_residual"]) > IDENTITY_TOLERANCE
    ]
    return {
        "fired": bool(offenders),
        "cells_checked": len(checked),
        "cells_excluded_unequal_runs": len(cells) - len(checked),
        "worst_residual": worst,
        "offenders": offenders,
    }


def _condition_identity_axis(cells: list[dict[str, object]]) -> dict[str, object]:
    """Condition 3: is identity stability an axis independent of occupancy?

    Looks for a pair of cells with essentially the same occupancy and materially
    different identity stability. If no such pair exists, the fourth measure adds
    nothing the first three did not already carry.
    """
    usable = [
        cell
        for cell in cells
        if cell["identity_stability"] is not None and cell["persistence"] is not None
    ]
    best: dict[str, object] | None = None
    for first in range(len(usable)):
        for second in range(first + 1, len(usable)):
            a, b = usable[first], usable[second]
            occupancy_gap = abs(float(a["occupancy"]) - float(b["occupancy"]))
            if occupancy_gap > OCCUPANCY_PAIR_TOLERANCE:
                continue
            identity_gap = abs(
                float(a["identity_stability"]) - float(b["identity_stability"])
            )
            if best is None or identity_gap > float(best["identity_gap"]):
                best = {
                    "occupancy_gap": occupancy_gap,
                    "identity_gap": identity_gap,
                    "a": {
                        key: a[key]
                        for key in (
                            "source",
                            "expert_set",
                            "assignment",
                            "gap",
                            "retention",
                            "occupancy",
                            "identity_stability",
                            "distinct_dominants",
                        )
                    },
                    "b": {
                        key: b[key]
                        for key in (
                            "source",
                            "expert_set",
                            "assignment",
                            "gap",
                            "retention",
                            "occupancy",
                            "identity_stability",
                            "distinct_dominants",
                        )
                    },
                }
    return {
        "fired": best is None or float(best["identity_gap"]) < IDENTITY_PAIR_THRESHOLD,
        "best_pair": best,
        "cells_usable": len(usable),
    }


def _condition_fixed_stable(cells: list[dict[str, object]]) -> dict[str, object]:
    """Condition 4: in ``fixed`` the dominant expert should not change hands."""
    fixed_cells = [
        cell
        for cell in cells
        if cell["assignment"] == "fixed" and cell["identity_stability"] is not None
    ]
    unstable = [
        {
            "source": cell["source"],
            "expert_set": cell["expert_set"],
            "gap": cell["gap"],
            "retention": cell["retention"],
            "identity_stability": cell["identity_stability"],
            "distinct_dominants": cell["distinct_dominants"],
        }
        for cell in fixed_cells
        if float(cell["identity_stability"]) < 1.0
    ]
    return {
        "fired": bool(unstable),
        "cells_checked": len(fixed_cells),
        "unstable": unstable,
    }


def _condition_undefined(cells: list[dict[str, object]]) -> dict[str, object]:
    """Condition 5: an undefined measure must never be reported as zero."""
    offenders: list[dict[str, object]] = []
    for cell in cells:
        occupancy = float(cell["occupancy"])
        if occupancy == 0.0 and cell["persistence"] is not None:
            offenders.append(
                {
                    "reason": "persistence reported where nothing collapsed",
                    "source": cell["source"],
                    "expert_set": cell["expert_set"],
                    "assignment": cell["assignment"],
                    "gap": cell["gap"],
                    "retention": cell["retention"],
                    "persistence": cell["persistence"],
                }
            )
        if occupancy == 1.0 and cell["recovery"] is not None:
            offenders.append(
                {
                    "reason": "recovery reported where diversity never returned",
                    "source": cell["source"],
                    "expert_set": cell["expert_set"],
                    "assignment": cell["assignment"],
                    "gap": cell["gap"],
                    "retention": cell["retention"],
                    "recovery": cell["recovery"],
                }
            )
    return {"fired": bool(offenders), "offenders": offenders}


def _condition_share_axis(cells: list[dict[str, object]]) -> dict[str, object]:
    """Condition 6 (supplementary): is ``dominance_share`` independent of occupancy?

    Added after the first run, and recorded as an addition rather than a
    replacement. Condition 3 tested the frozen definition of identity stability
    and fired; this asks whether the *reason* it fired was that the definition
    merged two different properties. ``dominance_share`` is the fraction of the
    window held by the single most dominant expert, which is what "continuity of
    the dominant component" actually means — ``identity_stability`` divides by
    the window length and so shrinks any difference as the window grows.

    If a pair of cells exists with near-identical occupancy and materially
    different dominance share, the fourth measure does carry an axis the first
    three do not, and condition 3's firing is a defect of the definition rather
    than an absence of information.
    """
    usable = [
        cell
        for cell in cells
        if cell["dominance_share"] is not None and cell["persistence"] is not None
    ]
    best: dict[str, object] | None = None
    for first in range(len(usable)):
        for second in range(first + 1, len(usable)):
            a, b = usable[first], usable[second]
            occupancy_gap = abs(float(a["occupancy"]) - float(b["occupancy"]))
            if occupancy_gap > OCCUPANCY_PAIR_TOLERANCE:
                continue
            share_gap = abs(float(a["dominance_share"]) - float(b["dominance_share"]))
            if best is None or share_gap > float(best["share_gap"]):
                best = {
                    "occupancy_gap": occupancy_gap,
                    "share_gap": share_gap,
                    "a": {
                        key: a[key]
                        for key in (
                            "source",
                            "expert_set",
                            "assignment",
                            "gap",
                            "retention",
                            "occupancy",
                            "dominance_share",
                            "identity_stability",
                            "distinct_dominants",
                        )
                    },
                    "b": {
                        key: b[key]
                        for key in (
                            "source",
                            "expert_set",
                            "assignment",
                            "gap",
                            "retention",
                            "occupancy",
                            "dominance_share",
                            "identity_stability",
                            "distinct_dominants",
                        )
                    },
                }
    return {
        "fired": best is None or float(best["share_gap"]) < IDENTITY_PAIR_THRESHOLD,
        "best_pair": best,
        "cells_usable": len(usable),
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (
                        ""
                        if row[key] is None
                        else json.dumps(row[key])
                        if isinstance(row[key], (dict, list))
                        else row[key]
                    )
                    for key in fieldnames
                }
            )


def run_investigation(
    silso_path: Path, noaa_path: Path, output_directory: Path
) -> dict[str, object]:
    """Measure the four properties on both parts and test the conditions."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspot_observations, sunspot_excluded = parse_silso_monthly(silso_path)
    co2_observations, co2_excluded = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspot_observations, "co2": co2_observations}

    # ---- Part B: the preserved sources ----
    cells: list[dict[str, object]] = []
    for expert_set, experts in EXPERT_SETS.items():
        if THRESHOLD_FRACTION * len(experts) <= 1.0:
            # Floor equals the minimum attainable effective count: collapse is
            # approached, never crossed. Reported as unreachable, not as a
            # measurement of zero occupancy.
            continue
        for source, series in observations.items():
            rows = _expert_rows_for(series, experts)
            prepared = _prepare(rows, experts)
            for assignment in ASSIGNMENTS:
                orders = _orders(prepared, experts, assignment)
                for retention in RETENTIONS_MEASURED:
                    for gap in GAPS_MEASURED:
                        measured = _measure_series(
                            prepared, retention, gap, orders, experts
                        )
                        aggregate = _evaluate(prepared, retention, gap, orders, experts)
                        cells.append(
                            _cell(
                                _four_measures(measured),
                                {
                                    "part": "B_sources",
                                    "source": source,
                                    "expert_set": expert_set,
                                    "experts": len(experts),
                                    "assignment": assignment,
                                    "retention": retention,
                                    "gap": gap,
                                },
                                aggregate,
                            )
                        )

    # ---- Part A: synthetic rank sequences, independent of both sources ----
    synthetic_experts = EXPERT_SETS["original"]
    synthetic_prepared = _prepare(
        _expert_rows_for(sunspot_observations, synthetic_experts), synthetic_experts
    )
    synthetic_cells: list[dict[str, object]] = []
    for tuple_order_probability in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        orders = _synthetic_orders(
            len(synthetic_prepared), synthetic_experts, tuple_order_probability, SYNTHETIC_SEED
        )
        for retention in RETENTIONS_MEASURED:
            for gap in GAPS_MEASURED:
                measured = _measure_series(
                    synthetic_prepared, retention, gap, orders, synthetic_experts
                )
                aggregate = _evaluate(
                    synthetic_prepared, retention, gap, orders, synthetic_experts
                )
                synthetic_cells.append(
                    _cell(
                        _four_measures(measured),
                        {
                            "part": "A_synthetic",
                            "source": "synthetic",
                            "expert_set": "original",
                            "experts": len(synthetic_experts),
                            "assignment": f"q={tuple_order_probability}",
                            "tuple_order_probability": tuple_order_probability,
                            "retention": retention,
                            "gap": gap,
                        },
                        aggregate,
                    )
                )

    all_cells = cells + synthetic_cells

    control = {
        "occupancy": _control_occupancy(all_cells),
        "series_reconstructs": _control_series_reconstructs(all_cells),
        "runs_maximal": _control_runs_maximal(all_cells),
    }
    controls_passed = all(bool(value["passed"]) for value in control.values())

    condition_1 = _condition_identity(all_cells)
    condition_2 = _condition_identity_axis(all_cells)
    condition_3 = _condition_fixed_stable(all_cells)
    condition_4 = _condition_undefined(all_cells)
    condition_5 = _condition_share_axis(all_cells)

    conditions = {
        "1_identity_does_not_hold": bool(condition_1["fired"]),
        "2_occupancy_disagrees_with_investigation_10": not bool(
            control["occupancy"]["passed"]
        ),
        "3_identity_is_a_function_of_occupancy": bool(condition_2["fired"]),
        "4_fixed_is_identity_stable": bool(condition_3["fired"]),
        "5_no_collapse_is_unmeasurable": bool(condition_4["fired"]),
        "6_dominance_share_is_a_function_of_occupancy": bool(condition_5["fired"]),
    }

    if conditions["2_occupancy_disagrees_with_investigation_10"] or not controls_passed:
        verdict = "instrument_fault"
    elif conditions["1_identity_does_not_hold"]:
        verdict = "falsified_algebra"
    elif conditions["3_identity_is_a_function_of_occupancy"] and conditions[
        "6_dominance_share_is_a_function_of_occupancy"
    ]:
        verdict = "falsified_four_measures_three_degrees_of_freedom"
    elif conditions["3_identity_is_a_function_of_occupancy"]:
        # Neutral label. It names which pre-registered criterion was not met, not
        # a reading of what that means. "The criterion was not observed inside
        # this design" and "a dependence was demonstrated" are different claims.
        verdict = "preregistered_identity_criterion_not_met_dominance_axis_independent"
    else:
        verdict = "not_falsified"

    results = {
        "method_version": METHOD_VERSION,
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_committed_before_this_module": "2d9cc7d3c",
        "verdict": verdict,
        "conditions_fired": conditions,
        "controls_passed": controls_passed,
        "control": control,
        "condition_1_identity": condition_1,
        "condition_3_identity_axis": condition_2,
        "condition_4_fixed_stability": condition_3,
        "condition_5_undefined": condition_4,
        "condition_6_dominance_share": condition_5,
        "parameters": {
            "threshold_fraction": THRESHOLD_FRACTION,
            "learning_rate": LEARNING_RATE,
            "gaps": list(GAPS_MEASURED),
            "retentions": list(RETENTIONS_MEASURED),
            "expert_sets": {name: list(experts) for name, experts in EXPERT_SETS.items()},
            "synthetic_seed": SYNTHETIC_SEED,
            "synthetic_count": SYNTHETIC_COUNT,
            "occupancy_pair_tolerance": OCCUPANCY_PAIR_TOLERANCE,
            "identity_pair_threshold": IDENTITY_PAIR_THRESHOLD,
        },
        "sources": {
            "sunspots": {
                "path": str(silso_path),
                "sha256_colon_hex": colon_sha256(silso_path),
                "observations": len(sunspot_observations),
                "excluded": sunspot_excluded,
            },
            "co2": {
                "path": str(noaa_path),
                "sha256_colon_hex": colon_sha256(noaa_path),
                "observations": len(co2_observations),
                "excluded": co2_excluded,
            },
        },
        "cells": all_cells,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }

    _write_json(output_directory / "results.json", results)
    _write_csv(output_directory / "cells.csv", all_cells)
    _write_json(
        output_directory / "manifest.json",
        {
            "method_version": METHOD_VERSION,
            "verdict": verdict,
            "cells": len(all_cells),
            "sources": ["sunspots", "co2", "synthetic"],
        },
    )
    return results
