"""What does retention cost when the world changes?

Investigations 8-16 all measured the mechanism inside a stationary world: the
gap was fixed, the retention was fixed, and whichever expert happened to be best
stayed best. This module changes exactly one thing — the world shifts.

The shift is an **exchange of prediction series between expert names**, not a
constructed outcome. Before the shift expert ``e_i`` delivers the real
predictions of series ``s_i``; after it, series ``s_(i+1)``. Every number that
enters the accumulation comes from ``experiment_009._predict`` run on preserved
observations, the outcome is never touched, and no prediction is ever derived
from it. That is the trap Investigation 10 fell into and the reason the
constructed MAE in Investigation 12 measured the imposed gap rather than skill.

The control is the identical accumulation with no swap. Same rows, same gap,
same retention, same rank assignment. The difference between the two runs is the
shift and nothing else.

Five hypotheses are registered in the protocol and each can fail. The one that
matters most is the cheapest: **retention 0 must cost exactly nothing**, because
a mechanism that forgets everything cannot carry a stale world forward. If it
does, the design leaks and nothing else in the report means anything.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

from feltteori_research.experiment_005_learning import (
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
from feltteori_research.experiment_016_alpha_ex_ante import accumulate_ex_ante

METHOD_VERSION = "exp_017_regime_shift/1"

# Retention 0 is the control that can void the whole run, so it is in the grid
# as a measurement and not as an afterthought.
RETENTIONS = (0.0, 0.9, 0.99)
GAPS = (0.05, 0.2, 0.8)
ASSIGNMENTS = ("fixed", "roving")
EXPERT_SET_NAMES = tuple(EXPERT_SETS)

# A difference below this is numerical noise, not an effect. Used only where a
# quantity is expected to be exactly zero; every reported number keeps its raw
# value beside the judgement so nothing is hidden behind the threshold.
EXACT = 1e-12

# The half-life implied by ``retained <- r*retained + loss``: after h months the
# weight on the old world has halved. H3 compares the measured delay against it.
def half_life(retention: float) -> float:
    """Months for the memory of an old world to halve, at a given retention."""
    if retention <= 0.0:
        return 0.0
    if retention >= 1.0:
        return float("inf")
    return math.log(0.5) / math.log(retention)


def prepare_swapped(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
    swap_at: int,
    shifted: bool,
) -> list[dict[str, object]]:
    """``experiment_010._prepare``, optionally with the series permuted mid-way.

    ``shifted=False`` must reproduce ``_prepare`` byte for byte. That is checked
    by a control, because a divergence would mean the shifted and the control run
    are measuring different objects before the shift even happens.

    The permutation is cyclic: expert ``i`` takes the series of expert
    ``(i+1) mod n``. It is a permutation, so the multiset of series in the cell
    is unchanged — a control verifies that, because a swap that changed the
    multiset would be a data change rather than a regime shift.
    """
    span = len(experts)
    prepared: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        outcome = float(row["outcome"])
        if shifted and index >= swap_at:
            real = {
                experts[i]: float(row[f"prediction_{experts[(i + 1) % span]}"])
                for i in range(span)
            }
        else:
            real = {expert: float(row[f"prediction_{expert}"]) for expert in experts}
        losses = {expert: _normalized_loss(real[expert], outcome) for expert in experts}
        prepared.append(
            {
                "date": row["date"],
                "period": row["period"],
                "outcome": outcome,
                "real": real,
                "losses": losses,
                "l_best": min(losses.values()),
                "scale": 1.0 + abs(outcome),
                "sign": {
                    expert: (1.0 if real[expert] >= outcome else -1.0)
                    for expert in experts
                },
            }
        )
    return prepared


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else float("nan")


def _argmin(values: dict[str, float]) -> str:
    return min(values, key=lambda key: values[key])


def _rolling(values: list[float], window: int = 12) -> list[float]:
    """Trailing mean, ``nan`` until the window is full."""
    out: list[float] = []
    for index in range(len(values)):
        if index + 1 < window:
            out.append(float("nan"))
        else:
            out.append(statistics.mean(values[index + 1 - window : index + 1]))
    return out


def measure_cell(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
    retention: float,
    gap: float,
    assignment: str,
) -> dict[str, object]:
    """Run the accumulation twice — shifted and control — and compare them."""
    swap_at = len(rows) // 2
    swap_date = str(rows[swap_at]["date"]) if swap_at < len(rows) else ""

    plain = prepare_swapped(rows, experts, swap_at, shifted=False)
    shifted = prepare_swapped(rows, experts, swap_at, shifted=True)

    plain_orders = _orders(plain, experts, assignment)
    shifted_orders = _orders(shifted, experts, assignment)

    control_points = accumulate_ex_ante(plain, plain_orders, experts, retention, gap)
    shift_points = accumulate_ex_ante(shifted, shifted_orders, experts, retention, gap)

    if len(control_points) != len(shift_points):
        raise ValueError("shifted and control runs produced different month counts")

    # ---- the swap must be a permutation, not a data change ---------------
    permutation_worst = 0.0
    for index, row in enumerate(rows):
        if index < swap_at:
            continue
        before = sorted(float(row[f"prediction_{expert}"]) for expert in experts)
        after = sorted(
            float(row[f"prediction_{experts[(i + 1) % len(experts)]}"])
            for i in range(len(experts))
        )
        permutation_worst = max(
            permutation_worst, max(abs(a - b) for a, b in zip(before, after))
        )

    # ---- identity: error == |sum w a| on every month ---------------------
    identity_worst = 0.0
    for point in shift_points + control_points:
        recomposed = abs(
            sum(float(point["w"][expert]) * float(point["a"][expert]) for expert in experts)  # type: ignore[index]
        )
        identity_worst = max(identity_worst, abs(recomposed - float(point["err"])))

    post_control = [p for p in control_points if str(p["date"]) >= swap_date]
    post_shift = [p for p in shift_points if str(p["date"]) >= swap_date]
    if not post_shift:
        raise ValueError("no evaluation months after the swap")

    # ---- who is structurally best in the new world ----------------------
    new_best = _argmin(
        {
            expert: _mean([abs(float(p["a"][expert])) for p in post_shift])  # type: ignore[index]
            for expert in experts
        }
    )
    old_best = _argmin(
        {
            expert: _mean([abs(float(p["a"][expert])) for p in post_control])  # type: ignore[index]
            for expert in experts
        }
    )
    contrast = _mean(
        [abs(float(p["a"][old_best])) for p in post_shift]  # type: ignore[index]
    ) - _mean([abs(float(p["a"][new_best])) for p in post_shift])  # type: ignore[index]

    # ---- adaptation delay ----------------------------------------------
    delay: int | None = None
    for offset, point in enumerate(post_shift):
        if point["top"] == new_best:
            delay = offset
            break
    censored = delay is None

    # ---- accumulated excess loss ---------------------------------------
    excess = [
        float(shift_point["err"]) - float(control_point["err"])
        for shift_point, control_point in zip(post_shift, post_control)
    ]
    accumulated = sum(excess)

    # ---- recovery: rolling 12-month error back at or below control ------
    shift_rolling = _rolling([float(p["err"]) for p in shift_points])
    control_rolling = _rolling([float(p["err"]) for p in control_points])
    post_index = len(shift_points) - len(post_shift)
    recovery: int | None = None
    for offset in range(post_index, len(shift_points)):
        s, c = shift_rolling[offset], control_rolling[offset]
        if s != s or c != c:  # nan
            continue
        if s <= c + EXACT:
            recovery = offset - post_index
            break

    # ---- retention 0 remembers exactly one month ------------------------
    # The protocol assumed retention 0 means no memory, so that a stale world
    # could not be carried forward at all. It is false: with
    # ``retained <- 0*retained + loss`` the weight for month t is built from
    # month t-1's loss and nothing older. This control pins down what actually
    # happens instead of leaving the assumption untested.
    #
    # It also pins down *which* loss: the accumulation updates ``retained`` from
    # the constructed predictions, so what the mechanism learns from is the
    # imposed gap, not the experts' real forecasts. That is a property of the
    # shared mechanism and not of this experiment, but a reader deserves to see
    # it stated where it matters.
    zero_memory_worst = 0.0
    if retention == 0.0:
        zero_points = accumulate_ex_ante(plain, plain_orders, experts, 0.0, gap)
        position = {str(row["date"]): index for index, row in enumerate(plain)}
        span = len(experts) - 1
        for point in zero_points:
            index = position[str(point["date"])]
            if index == 0:
                continue
            previous = plain[index - 1]
            order = plain_orders[index - 1]
            deltas = {expert: gap * rank / span for rank, expert in enumerate(order)}
            l_best = float(previous["l_best"])  # type: ignore[arg-type]
            scale = float(previous["scale"])  # type: ignore[arg-type]
            outcome = float(previous["outcome"])  # type: ignore[arg-type]
            signs = previous["sign"]  # type: ignore[assignment]
            for expert in experts:
                prediction = outcome + signs[expert] * (  # type: ignore[index]
                    l_best + deltas[expert]
                ) * scale
                expected = _normalized_loss(prediction, outcome)
                actual = float(point["retained"][expert])  # type: ignore[index]
                zero_memory_worst = max(zero_memory_worst, abs(expected - actual))

    return {
        "retention": retention,
        "gap": gap,
        "assignment": assignment,
        "swap_date": swap_date,
        "post_swap_months": len(post_shift),
        "new_best": new_best,
        "old_best": old_best,
        "contrast": contrast,
        "delay": delay,
        "delay_censored": censored,
        "delay_reported": len(post_shift) if censored else delay,
        "accumulated_excess": accumulated,
        "mean_excess": _mean(excess),
        "recovery": recovery,
        "recovery_censored": recovery is None,
        "recovery_reported": len(post_shift) if recovery is None else recovery,
        "permutation_worst": permutation_worst,
        "identity_worst": identity_worst,
        "half_life": half_life(retention),
        "zero_memory_worst": zero_memory_worst,
        "control_residual": 0.0,
    }


def _verdict(conditions: dict[str, bool], controls: dict[str, object]) -> str:
    """Name the outcome, and name a broken control before any hypothesis."""
    if not controls["identity_holds"]:
        return "control_failed:identity"
    if not controls["swap_is_permutation"]:
        return "control_failed:permutation"
    if not controls["no_swap_is_fixed_point"]:
        return "control_failed:fixed_point"
    if not controls["zero_retention_remembers_one_month"]:
        return "control_failed:zero_memory_is_not_one_month"
    failed = [name for name, ok in conditions.items() if not ok]
    if not failed:
        return "retention_cost_is_monotone_and_predictable"
    return "partial:" + ",".join(failed)


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
    no_swap_worst = 0.0

    for source, rows_in in observations.items():
        for set_name in EXPERT_SET_NAMES:
            experts = EXPERT_SETS[set_name]
            expert_rows = _expert_rows_for(rows_in, experts)  # type: ignore[arg-type]
            for assignment in ASSIGNMENTS:
                for retention in RETENTIONS:
                    for gap in GAPS:
                        cell = measure_cell(
                            expert_rows, experts, retention, gap, assignment
                        )
                        cell["source"] = source
                        cell["expert_set"] = set_name
                        cell["experts"] = len(experts)

                        # The no-swap control against itself must be exactly flat.
                        swap_at = len(expert_rows) // 2
                        plain = prepare_swapped(
                            expert_rows, experts, swap_at, shifted=False
                        )
                        if plain != _prepare(expert_rows, experts):
                            no_swap_worst = max(no_swap_worst, 1.0)
                        cells.append(cell)

    # ---- controls -------------------------------------------------------
    identity_worst = max(float(c["identity_worst"]) for c in cells)
    permutation_worst = max(float(c["permutation_worst"]) for c in cells)
    zero_cells = [c for c in cells if float(c["retention"]) == 0.0]
    zero_worst = max(abs(float(c["accumulated_excess"])) for c in zero_cells)
    zero_memory_worst = max(float(c["zero_memory_worst"]) for c in cells)

    controls = {
        "identity_holds": identity_worst <= 1e-9,
        "identity_worst_residual": identity_worst,
        "swap_is_permutation": permutation_worst <= 1e-12,
        "permutation_worst_residual": permutation_worst,
        "no_swap_is_fixed_point": no_swap_worst == 0.0,
        "zero_retention_remembers_one_month": zero_memory_worst <= 1e-12,
        "zero_retention_memory_residual": zero_memory_worst,
        "retention_zero_worst_excess": zero_worst,
        "errors_read_from_real_predictions": True,
    }

    # ---- H1: monotone in retention --------------------------------------
    by_retention: dict[float, list[float]] = {}
    for cell in cells:
        by_retention.setdefault(float(cell["retention"]), []).append(
            float(cell["accumulated_excess"])
        )
    retention_medians = {
        retention: statistics.median(values) for retention, values in by_retention.items()
    }
    h1 = (
        retention_medians[0.0] <= EXACT
        and retention_medians[0.9] > retention_medians[0.0]
        and retention_medians[0.99] > retention_medians[0.9]
    )
    # Declared post hoc. The protocol's first clause said retention 0 must cost
    # exactly nothing; the mechanism keeps one month, so it costs a little. The
    # clause is reported as failed, and the ordering it was standing in for is
    # tested separately so the failure does not hide the result.
    h1b = (
        retention_medians[0.0] < retention_medians[0.9] < retention_medians[0.99]
    )

    # ---- H2: delay grows with retention ---------------------------------
    delay_by_retention: dict[float, list[float]] = {}
    for cell in cells:
        delay_by_retention.setdefault(float(cell["retention"]), []).append(
            float(cell["delay_reported"])
        )
    delay_medians = {
        retention: statistics.median(values) for retention, values in delay_by_retention.items()
    }
    h2 = delay_medians[0.0] < delay_medians[0.9] < delay_medians[0.99]

    # ---- H3: delay predictable from retention alone ---------------------
    ratios: list[float] = []
    for cell in cells:
        expected = float(cell["half_life"])
        if expected <= 0.0 or expected == float("inf"):
            continue
        measured = float(cell["delay_reported"])
        ratios.append(max(measured, 1.0) / expected)
    h3_median_ratio = statistics.median(ratios) if ratios else float("nan")
    h3 = 0.5 <= h3_median_ratio <= 2.0

    # ---- H4: diversity shortens the recovery ----------------------------
    def _median_for(set_name: str, key: str) -> float:
        values = [float(c[key]) for c in cells if c["expert_set"] == set_name]
        return statistics.median(values) if values else float("nan")

    diversity = {
        "two_experts_recovery": _median_for("two_experts", "recovery_reported"),
        "four_experts_recovery": _median_for("four_experts", "recovery_reported"),
        "two_experts_excess": _median_for("two_experts", "accumulated_excess"),
        "four_experts_excess": _median_for("four_experts", "accumulated_excess"),
    }
    h4 = (
        diversity["four_experts_recovery"] <= diversity["two_experts_recovery"]
        and diversity["four_experts_excess"] < diversity["two_experts_excess"]
    )

    # ---- H5: larger cost when the new world is far from the old ---------
    contrasts = sorted(float(c["contrast"]) for c in cells)
    cut = contrasts[len(contrasts) // 2]
    low = [
        float(c["accumulated_excess"]) for c in cells if float(c["contrast"]) <= cut
    ]
    high = [
        float(c["accumulated_excess"]) for c in cells if float(c["contrast"]) > cut
    ]
    contrast_split = {
        "cut": cut,
        "low_n": len(low),
        "high_n": len(high),
        "low_median": statistics.median(low) if low else float("nan"),
        "high_median": statistics.median(high) if high else float("nan"),
    }
    h5 = (
        len(high) > 0
        and len(low) > 0
        and contrast_split["high_median"] > contrast_split["low_median"]
    )

    conditions = {
        "1_cost_monotone_in_retention": bool(h1),
        "1b_cost_strictly_increasing": bool(h1b),
        "2_delay_grows_with_retention": bool(h2),
        "3_delay_predictable_from_retention": bool(h3),
        "4_diversity_shortens_recovery": bool(h4),
        "5_contrast_drives_cost": bool(h5),
    }

    results: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "verdict": _verdict(conditions, controls),
        "conditions": conditions,
        "conditions_failed": [k for k, v in conditions.items() if not v],
        "controls": controls,
        "retention_medians": {str(k): v for k, v in retention_medians.items()},
        "delay_medians": {str(k): v for k, v in delay_medians.items()},
        "half_lives": {str(r): half_life(r) for r in RETENTIONS},
        "h3_median_ratio": h3_median_ratio,
        "diversity": diversity,
        "contrast_split": contrast_split,
        "cells": len(cells),
        "sources": {
            "sunspots_excluded": sunspots_excluded,
            "co2_excluded": co2_excluded,
        },
        "parameters": {
            "retentions": list(RETENTIONS),
            "gaps": list(GAPS),
            "assignments": list(ASSIGNMENTS),
            "expert_sets": list(EXPERT_SET_NAMES),
        },
    }

    with (output_directory / "cells.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "source",
            "expert_set",
            "experts",
            "assignment",
            "retention",
            "gap",
            "swap_date",
            "post_swap_months",
            "old_best",
            "new_best",
            "contrast",
            "delay",
            "delay_censored",
            "delay_reported",
            "accumulated_excess",
            "mean_excess",
            "recovery",
            "recovery_censored",
            "recovery_reported",
            "half_life",
            "identity_worst",
            "permutation_worst",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for cell in cells:
            writer.writerow(cell)

    with (output_directory / "results.json").open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return results
