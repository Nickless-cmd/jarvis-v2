"""Is the roving collapse threshold a free parameter or a function of the rank drift?

Investigation 8 prescribed the expert loss gap directly and found, in ``fixed``
assignment, a threshold near ``1 - r`` on both sources. Investigation 9 varied
the expert set across five sets and the ``fixed`` threshold did not move — which
is a tautology: in ``fixed`` the deltas are pinned to the tuple order, so the
mean rank positions are always ``0, 1/(N-1), ..., 1`` and there is nothing for
the data to move.

The data dependence lives in ``roving``, where the delta is assigned by the real
ranking each month. There the threshold ranged from 0.01 to 0.8 across cells.
This module asks whether that range is explained by the **spread of the mean
rank positions** ``m_max - m_min``:

    gap_threshold = u_crit(N) * (1-r) / (LR * (m_max - m_min))

with ``u_crit(N)`` the softmax argument spread at which the effective expert
count falls below half of ``N`` — a pure function of ``N``, solved numerically.
There is no ``(N-1)`` factor: the delta for rank ``i`` is ``gap * i/(N-1)``, so
``i/(N-1)`` spans ``[0, 1]`` and the delta *range* is ``gap`` for every ``N``.
The first run of this experiment carried that factor and was stopped by its own
control; see the amendment in the protocol.

Part A validates the formula where the rank drift is *controlled* (synthetic
order sequences where the tuple order is drawn with a prescribed probability).
Part B applies it to the two preserved sources.

The protocol is frozen in ``experiments/exp_010_rank_drift/PROTOCOL.md`` and was
committed before any measurement was computed.

The one thing that must not drift silently is the mechanism itself. This module
prepares the per-row real losses once and passes an explicit rank order into the
evaluation, where Investigation 9 recomputed them per call and derived the order
inside. Control 1 proves the two paths agree on the original set before any
other row is allowed to carry a verdict.
"""

from __future__ import annotations

import csv
import json
import math
import platform
import random
from datetime import datetime, timezone
from pathlib import Path

from feltteori_research.experiment_005_learning import (
    LEARNING_RATE,
    RETENTIONS,
    _normalized_loss,
    colon_sha256,
    parse_silso_monthly,
)
from feltteori_research.experiment_006_order import parse_noaa_monthly
from feltteori_research.experiment_009_expert_set import (
    CONTROL_EXPECTED_THRESHOLDS,
    EXPERT_SETS,
    GAPS,
    THRESHOLD_FRACTION,
    _adaptive_evaluation,
    _expert_rows_for,
)

METHOD_VERSION = "exp010.rankdrift.2"

# Frozen in the protocol. Factor 1.15 makes a threshold known to within ~1.07,
# which is what lets the invariant be tested at all: Investigation 9's factor-2
# grid could not tell a predicted 0.0157 from a measured 0.02.
GRID_RATIO = 1.15
GRID_LOW = 0.0005
GRID_HIGH = 1.0

# Part A: ``q`` is the probability that a month's rank order is the tuple order.
# ``q = 1`` is exactly `fixed`; ``q = 0`` is exactly a uniform permutation. Both
# ends are anchors, which is why the first generator — which shuffled the
# non-designated experts and so only approximated `fixed` — was replaced.
SYNTHETIC_PROBABILITIES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
SYNTHETIC_RETENTIONS = {"short_continuity": 0.9, "long_continuity": 0.99}
SYNTHETIC_SEED = 20261125

# Falsification thresholds, copied verbatim from the frozen protocol.
THRESHOLD_FACTOR = 2.0
CALIBRATION_TOLERANCE = 1e-9
UNIFORM_TOLERANCE = 1e-9
IDENTITY_TOLERANCE = 1e-12

ASSIGNMENTS = ("fixed", "roving")


def _fine_grid() -> tuple[float, ...]:
    """Geometric gap grid, ascending, from GRID_LOW to GRID_HIGH."""
    gaps: list[float] = []
    gap = GRID_LOW
    while gap <= GRID_HIGH * (1.0 + 1e-12):
        gaps.append(round(gap, 12))
        gap *= GRID_RATIO
    return tuple(gaps)


FINE_GAPS = _fine_grid()


def _critical_argument(experts: int, floor_fraction: float) -> float:
    """Softmax argument spread at which the effective count hits the floor.

    With rank positions ``i/(N-1)`` and argument spread ``u``, the weights are
    ``exp(-u * i/(N-1))`` and the effective count is ``1 / sum(w^2)``. Bisection
    on ``u``. A set of two experts has floor 1.0, which the effective count only
    approaches asymptotically, so the search saturates at the upper bound — that
    saturation is the prediction "unreachable", not a numerical accident.
    """
    positions = [index / (experts - 1) for index in range(experts)]
    target = floor_fraction * experts

    def effective(u: float) -> float:
        weights = [math.exp(-u * position) for position in positions]
        total = sum(weights)
        normalised = [weight / total for weight in weights]
        return 1.0 / sum(weight * weight for weight in normalised)

    low, high = 0.0, 50.0
    for _ in range(200):
        middle = (low + high) / 2.0
        if effective(middle) > target:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def _prepare(rows: list[dict[str, object]], experts: tuple[str, ...]) -> list[dict[str, object]]:
    """Per-row quantities that do not depend on gap, assignment or retention."""
    prepared: list[dict[str, object]] = []
    for row in rows:
        outcome = float(row["outcome"])
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


def _orders(
    prepared: list[dict[str, object]], experts: tuple[str, ...], assignment: str
) -> list[list[str]]:
    """Rank order per row: fixed is the tuple order, roving is the real ranking."""
    if assignment == "fixed":
        return [list(experts) for _ in prepared]
    if assignment == "roving":
        return [
            sorted(experts, key=lambda expert: row["losses"][expert])  # type: ignore[arg-type]
            for row in prepared
        ]
    raise ValueError(f"unknown assignment: {assignment}")


def _synthetic_orders(
    count: int, experts: tuple[str, ...], tuple_order_probability: float, seed: int
) -> list[list[str]]:
    """Rank orders where the tuple order is drawn with a prescribed probability.

    With probability ``q`` the order is the tuple order; otherwise it is a
    uniformly drawn permutation. ``q = 1`` therefore reproduces `fixed` exactly
    and ``q = 0`` reproduces a uniform ranking exactly — the two anchors the
    first generator only approximated, because it shuffled the non-designated
    experts and so never reached a spread of 1.0.
    """
    generator = random.Random(seed)
    base = list(experts)
    orders: list[list[str]] = []
    for _ in range(count):
        if generator.random() < tuple_order_probability:
            orders.append(list(base))
        else:
            permutation = list(base)
            generator.shuffle(permutation)
            orders.append(permutation)
    return orders


def _evaluate(
    prepared: list[dict[str, object]],
    retention: float,
    gap: float,
    orders: list[list[str]],
    experts: tuple[str, ...],
) -> dict[str, object]:
    """Run the adaptive mechanism with an explicit rank order per row.

    Two different quantities are reported and they are not interchangeable:

    ``duty_cycle`` is the fraction of evaluation months whose effective expert
    count lies below the floor. It is in ``[0, 1]`` and measures *occupancy*.

    ``mean_over_min`` is the mean effective count divided by the minimum. It is
    ``>= 1`` and measures *fluctuation*. Exactly 1.000 means the count never
    moved — but it cannot say whether it sat above the floor throughout (duty 0)
    or below it throughout (duty 1). Measured 2026-11-25 on the preserved
    sources: both give ``mean_over_min`` 1.0000 while their duty cycles are
    0.0000 and 1.0000.

    Investigation 10's first report used one name, "duty cycle", for both. That
    is the same class of error the investigation is about — an instrument that
    does not measure what its label says.
    """
    span = len(experts) - 1
    retained = {expert: 0.0 for expert in experts}
    floor = THRESHOLD_FRACTION * len(experts)
    effective_sum = 0.0
    effective_min = math.inf
    effective_max = 0.0
    below_floor = 0
    error_sum = 0.0
    count = 0
    worst_gap_error = 0.0

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

        prediction = sum(predictions[expert] * weights[expert] for expert in experts)
        losses = {
            expert: _normalized_loss(predictions[expert], outcome) for expert in experts
        }

        if row["period"] == "evaluation":
            effective = 1.0 / sum(weight * weight for weight in weights.values())
            effective_sum += effective
            effective_min = min(effective_min, effective)
            effective_max = max(effective_max, effective)
            if effective < floor:
                below_floor += 1
            error_sum += abs(prediction - outcome)
            count += 1
            measured_gap = max(losses.values()) - min(losses.values())
            worst_gap_error = max(worst_gap_error, abs(measured_gap - gap))

        retained = {
            expert: retention * retained[expert] + losses[expert] for expert in experts
        }

    if count == 0:
        raise ValueError("no evaluation rows")
    mean_effective = effective_sum / count
    return {
        "rows": count,
        "mae": error_sum / count,
        "mean_effective_experts": mean_effective,
        "min_effective_experts": effective_min,
        "max_effective_experts": effective_max,
        "duty_cycle": below_floor / count,
        "mean_over_min": mean_effective / effective_min,
        "max_gap_error": worst_gap_error,
    }


def _mean_positions(
    orders: list[list[str]], retention: float, experts: tuple[str, ...]
) -> dict[str, float]:
    """Mean rank position per expert, weighted ``r^(t-s)``.

    The accumulated loss at the end of the window weights a month by
    ``r^(t-s)``, so the drift that actually built it is the same weighted mean.
    At ``r = 1`` that is the plain mean over all rows.
    """
    span = len(experts) - 1
    count = len(orders)
    totals = {expert: 0.0 for expert in experts}
    weight_sum = 0.0
    for index, order in enumerate(orders):
        weight = (
            1.0 if retention >= 1.0 else (1.0 - retention) * retention ** (count - 1 - index)
        )
        weight_sum += weight
        for rank, expert in enumerate(order):
            totals[expert] += weight * rank / span
    return {expert: value / weight_sum for expert, value in totals.items()}


def _predicted_threshold(
    experts: tuple[str, ...], retention: float, spread: float
) -> float | None:
    """``u_crit(N)(1-r) / (LR * spread)``, or None where the formula has no domain."""
    if retention >= 1.0:
        # No steady state: the accumulated loss is an undecayed sum, so (1-r) = 0
        # and the invariant diverges. Declared out of scope in the protocol.
        return None
    if spread <= UNIFORM_TOLERANCE:
        return None
    if THRESHOLD_FRACTION * len(experts) <= 1.0:
        # The floor equals the minimum attainable effective count (a single
        # expert), so the mechanism can approach it but never cross it. Two
        # experts are the only case. Bisection saturates here and would otherwise
        # return a finite number that reads like a prediction.
        return None
    return (
        _critical_argument(len(experts), THRESHOLD_FRACTION)
        * (1.0 - retention)
        / (LEARNING_RATE * spread)
    )


def _invariant(
    experts: tuple[str, ...], retention: float, spread: float, measured: float | None
) -> float | None:
    """``Q = gap * spread * LR / (1-r)`` — must equal ``u_crit(N)``."""
    if measured is None or retention >= 1.0 or spread <= UNIFORM_TOLERANCE:
        return None
    if THRESHOLD_FRACTION * len(experts) <= 1.0:
        return None
    return measured * spread * LEARNING_RATE / (1.0 - retention)


def _scan(
    prepared: list[dict[str, object]],
    retention: float,
    orders: list[list[str]],
    experts: tuple[str, ...],
    floor: float,
) -> dict[str, object]:
    """Smallest fine-grid gap at which the effective count falls below the floor.

    The scan stops at the first crossing, so ``cells`` only holds the gaps that
    were actually evaluated. Unreached cells are scanned to the top of the grid.
    """
    series: list[dict[str, object]] = []
    crossed: float | None = None
    previous: float | None = None
    for gap in FINE_GAPS:
        result = _evaluate(prepared, retention, gap, orders, experts)
        series.append({"gap": gap, **result})
        if float(result["mean_effective_experts"]) < floor:
            crossed = gap
            break
        previous = gap
    return {"measured_threshold": crossed, "lower_bound": previous, "series": series}


def _control_order_identity(observations: dict[str, list[object]]) -> dict[str, object]:
    """The prepared/ordered path must reproduce Investigation 9's evaluation."""
    experts = EXPERT_SETS["original"]
    worst = 0.0
    for source, series in observations.items():
        rows = _expert_rows_for(series, experts)
        prepared = _prepare(rows, experts)
        for assignment in ASSIGNMENTS:
            orders = _orders(prepared, experts, assignment)
            for retention in (0.9, 1.0):
                for gap in (0.02, 0.2):
                    mine = _evaluate(prepared, retention, gap, orders, experts)
                    theirs = _adaptive_evaluation(
                        rows, retention, gap, assignment, experts
                    )
                    worst = max(
                        worst,
                        abs(
                            float(mine["mean_effective_experts"])
                            - float(theirs["mean_effective_experts"])
                        ),
                        abs(float(mine["mae"]) - float(theirs["mae"])),
                    )
    return {"passed": worst <= IDENTITY_TOLERANCE, "worst_difference": worst}


def _control_reproduction(thresholds: list[dict[str, object]]) -> dict[str, object]:
    """Fixed-mode thresholds must fall inside Investigation 9's measured bracket.

    Restricted to three-expert sets: Investigation 8's expected thresholds are
    defined for the original three-expert set, and Investigation 9 measured the
    same numbers for every three-expert set. Sets of two and four have a
    different floor and are not described by those numbers — applying them there
    was the first run's control defect.
    """
    grid = list(GAPS)
    checked: list[dict[str, object]] = []
    for cell in thresholds:
        if cell["assignment"] != "fixed":
            continue
        if int(cell["experts"]) != 3:
            continue
        key = (cell["source"], cell["assignment"], cell["retention_condition"])
        if key not in CONTROL_EXPECTED_THRESHOLDS:
            continue
        expected = CONTROL_EXPECTED_THRESHOLDS[key]
        measured = cell["measured_threshold"]
        if expected is None:
            ok = measured is None
            bracket = (grid[-1], None)
        else:
            index = grid.index(float(expected))
            lower = grid[index - 1]
            ok = measured is not None and lower <= float(measured) <= float(expected)
            bracket = (lower, float(expected))
        checked.append(
            {
                "expert_set": cell["expert_set"],
                "source": cell["source"],
                "retention_condition": cell["retention_condition"],
                "expected": expected,
                "measured": measured,
                "bracket": bracket,
                "ok": ok,
            }
        )
    return {"passed": all(item["ok"] for item in checked), "checked": checked}


def _control_calibration(cells: list[dict[str, object]]) -> dict[str, object]:
    worst = max((float(cell["max_gap_error"]) for cell in cells), default=0.0)
    return {"passed": worst <= CALIBRATION_TOLERANCE, "worst_gap_error": worst}


def _condition_invariant(thresholds: list[dict[str, object]]) -> dict[str, object]:
    """Q must be constant across cells with the same N and r < 1."""
    groups: dict[int, list[dict[str, object]]] = {}
    for cell in thresholds:
        q = cell["invariant"]
        if q is None:
            continue
        groups.setdefault(int(cell["experts"]), []).append(cell)

    report: dict[str, object] = {}
    worst_ratio = 0.0
    fired = False
    for experts, items in sorted(groups.items()):
        values = [float(item["invariant"]) for item in items]
        ratio = max(values) / min(values) if min(values) > 0 else math.inf
        worst_ratio = max(worst_ratio, ratio)
        if ratio > THRESHOLD_FACTOR:
            fired = True
        report[str(experts)] = {
            "cells": len(items),
            "invariant_min": min(values),
            "invariant_max": max(values),
            "ratio": ratio,
            "u_crit": _critical_argument(experts, THRESHOLD_FRACTION),
        }
    return {"fired": fired, "worst_ratio": worst_ratio, "per_expert_count": report}


def _diagnostic_invariant_by_assignment(
    thresholds: list[dict[str, object]]
) -> dict[str, object]:
    """Post-hoc diagnostic, not a condition: does the invariant hold within `fixed`?

    Condition 1 spans every cell with the same ``N``, as the protocol froze it.
    This split was added after the first run, so it carries no verdict — it
    answers a narrower question: whether the drift formula is exact where the
    drift is deterministic, which is what separates a wrong formula from a
    formula that is right about one route to collapse and silent about another.
    """
    report: dict[str, object] = {}
    for assignment in ASSIGNMENTS:
        per_count: dict[str, object] = {}
        for experts in (2, 3, 4):
            values = [
                float(cell["invariant"])
                for cell in thresholds
                if cell["assignment"] == assignment
                and int(cell["experts"]) == experts
                and cell["invariant"] is not None
            ]
            if not values:
                per_count[str(experts)] = {"cells": 0}
                continue
            per_count[str(experts)] = {
                "cells": len(values),
                "invariant_min": min(values),
                "invariant_max": max(values),
                "ratio": max(values) / min(values) if min(values) > 0 else None,
                "u_crit": _critical_argument(experts, THRESHOLD_FRACTION),
            }
        report[assignment] = per_count
    return report


def _condition_synthetic(synthetic: list[dict[str, object]]) -> dict[str, object]:
    """The threshold must fall monotonically as the drift strengthens."""
    unreachable = float("inf")
    report: dict[str, object] = {}
    fired = False
    for retention_condition, items in _group_by(synthetic, "retention_condition").items():
        ordered = sorted(items, key=lambda item: float(item["tuple_order_probability"]))
        sequence = [
            unreachable if item["measured_threshold"] is None else float(item["measured_threshold"])
            for item in ordered
        ]
        decreasing = all(
            sequence[index] >= sequence[index + 1] for index in range(len(sequence) - 1)
        )
        if not decreasing:
            fired = True
        report[str(retention_condition)] = {
            "tuple_order_probabilities": [item["tuple_order_probability"] for item in ordered],
            "measured": [item["measured_threshold"] for item in ordered],
            "predicted": [item["predicted_threshold"] for item in ordered],
            "spread": [item["spread"] for item in ordered],
            "monotone_decreasing": decreasing,
        }

    uniform = [
        item
        for item in synthetic
        if abs(float(item["tuple_order_probability"])) < 1e-12
    ]
    uniform_unreachable = all(item["measured_threshold"] is None for item in uniform)
    if not uniform_unreachable:
        fired = True
    report["uniform_is_unreachable"] = uniform_unreachable

    return {"fired": fired, "per_retention": report}


def _condition_uniform_declared(thresholds: list[dict[str, object]]) -> dict[str, object]:
    """A zero-drift cell must be reported unreachable, never as a threshold."""
    offenders = [
        cell
        for cell in thresholds
        if float(cell["spread"]) <= UNIFORM_TOLERANCE
        and cell["measured_threshold"] is not None
    ]
    return {"fired": bool(offenders), "offenders": offenders}


def _group_by(items: list[dict[str, object]], key: str) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in items:
        grouped.setdefault(str(item[key]), []).append(item)
    return grouped


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("refusing to write an empty table")
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_investigation(
    silso_path: Path, noaa_path: Path, output_directory: Path
) -> dict[str, object]:
    """Measure the rank drift, predict the roving threshold, and test the invariant."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspot_observations, sunspot_excluded = parse_silso_monthly(silso_path)
    co2_observations, co2_excluded = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspot_observations, "co2": co2_observations}

    identity = _control_order_identity(observations)
    if not identity["passed"]:
        raise SystemExit(
            "control failed before any cell was run: the prepared/ordered path does "
            f"not reproduce Investigation 9's evaluation. {identity}"
        )

    # ---- Part B: the preserved sources ----
    cells: list[dict[str, object]] = []
    thresholds: list[dict[str, object]] = []
    for expert_set, experts in EXPERT_SETS.items():
        floor = THRESHOLD_FRACTION * len(experts)
        for source, series in observations.items():
            rows = _expert_rows_for(series, experts)
            prepared = _prepare(rows, experts)
            for assignment in ASSIGNMENTS:
                orders = _orders(prepared, experts, assignment)
                for retention_condition, retention in RETENTIONS.items():
                    positions = _mean_positions(orders, retention, experts)
                    spread = max(positions.values()) - min(positions.values())
                    predicted = _predicted_threshold(experts, retention, spread)
                    scan = _scan(prepared, retention, orders, experts, floor)
                    measured = scan["measured_threshold"]
                    for row in scan["series"]:  # type: ignore[union-attr]
                        cells.append(
                            {
                                "expert_set": expert_set,
                                "experts": len(experts),
                                "source": source,
                                "assignment": assignment,
                                "retention_condition": retention_condition,
                                "retention": retention,
                                "floor": floor,
                                **row,  # type: ignore[arg-type]
                            }
                        )
                    thresholds.append(
                        {
                            "expert_set": expert_set,
                            "experts": len(experts),
                            "source": source,
                            "assignment": assignment,
                            "retention_condition": retention_condition,
                            "retention": retention,
                            "floor": floor,
                            "spread": spread,
                            "mean_positions": json.dumps(positions, sort_keys=True),
                            "predicted_threshold": predicted,
                            "measured_threshold": measured,
                            "lower_bound": scan["lower_bound"],
                            "invariant": _invariant(experts, retention, spread, measured),
                            "unreachable_declared": (
                                measured is None
                                and (
                                    retention >= 1.0
                                    or spread <= UNIFORM_TOLERANCE
                                    or (predicted is not None and predicted > GRID_HIGH)
                                )
                            ),
                        }
                    )

    # ---- Part A: controlled rank drift ----
    synthetic: list[dict[str, object]] = []
    synthetic_experts = EXPERT_SETS["original"]
    synthetic_prepared = _prepare(
        _expert_rows_for(sunspot_observations, synthetic_experts), synthetic_experts
    )
    for tuple_order_probability in SYNTHETIC_PROBABILITIES:
        orders = _synthetic_orders(
            len(synthetic_prepared),
            synthetic_experts,
            tuple_order_probability,
            SYNTHETIC_SEED,
        )
        for retention_condition, retention in SYNTHETIC_RETENTIONS.items():
            positions = _mean_positions(orders, retention, synthetic_experts)
            spread = max(positions.values()) - min(positions.values())
            predicted = _predicted_threshold(synthetic_experts, retention, spread)
            scan = _scan(
                synthetic_prepared,
                retention,
                orders,
                synthetic_experts,
                THRESHOLD_FRACTION * len(synthetic_experts),
            )
            synthetic.append(
                {
                    "tuple_order_probability": tuple_order_probability,
                    "retention_condition": retention_condition,
                    "retention": retention,
                    "spread": spread,
                    "predicted_threshold": predicted,
                    "measured_threshold": scan["measured_threshold"],
                    "lower_bound": scan["lower_bound"],
                    "invariant": _invariant(
                        synthetic_experts, retention, spread, scan["measured_threshold"]
                    ),
                }
            )

    control = {
        "order_identity": identity,
        "calibration": _control_calibration(cells),
        "reproduction": _control_reproduction(thresholds),
    }
    controls_passed = all(bool(value["passed"]) for value in control.values())

    condition_1 = _condition_invariant(thresholds)
    condition_2 = _condition_synthetic(synthetic)
    condition_3 = _condition_uniform_declared(thresholds)

    conditions = {
        "1_invariant_not_constant": bool(condition_1["fired"]),
        "2_synthetic_scaling_absent": bool(condition_2["fired"]),
        "3_uniform_is_unreachable": bool(condition_3["fired"]),
        "4_control_failed": not controls_passed,
        "5_calibration_failed": not bool(control["calibration"]["passed"]),
    }

    if conditions["4_control_failed"] or conditions["5_calibration_failed"]:
        verdict = "instrument_fault"
    elif conditions["1_invariant_not_constant"] or conditions["2_synthetic_scaling_absent"]:
        verdict = "falsified"
    elif conditions["3_uniform_is_unreachable"]:
        verdict = "falsified_unreachable_reported_as_threshold"
    else:
        verdict = "not_falsified"

    results = {
        "method_version": METHOD_VERSION,
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "conditions_fired": conditions,
        "controls_passed": controls_passed,
        "control": control,
        "condition_1_invariant": condition_1,
        "condition_2_synthetic": condition_2,
        "condition_3_uniform": condition_3,
        "diagnostic_invariant_by_assignment": _diagnostic_invariant_by_assignment(thresholds),
        "grid": {"ratio": GRID_RATIO, "low": GRID_LOW, "high": GRID_HIGH, "points": len(FINE_GAPS)},
        "parameters": {
            "threshold_fraction": THRESHOLD_FRACTION,
            "learning_rate": LEARNING_RATE,
            "expert_sets": {name: list(experts) for name, experts in EXPERT_SETS.items()},
            "retentions": RETENTIONS,
            "synthetic_probabilities": list(SYNTHETIC_PROBABILITIES),
            "synthetic_retentions": SYNTHETIC_RETENTIONS,
            "synthetic_seed": SYNTHETIC_SEED,
            "u_crit": {
                str(count): _critical_argument(count, THRESHOLD_FRACTION)
                for count in (2, 3, 4)
            },
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
        "thresholds": thresholds,
        "synthetic": synthetic,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }

    _write_json(output_directory / "results.json", results)
    _write_csv(output_directory / "cells.csv", cells)
    _write_csv(
        output_directory / "thresholds.csv",
        [
            {
                key: value
                for key, value in cell.items()
                if key != "mean_positions"
            }
            for cell in thresholds
        ],
    )
    _write_csv(output_directory / "synthetic.csv", synthetic)
    _write_json(
        output_directory / "manifest.json",
        {
            "method_version": METHOD_VERSION,
            "verdict": verdict,
            "grid_points": len(FINE_GAPS),
            "cells": len(cells),
            "threshold_cells": len(thresholds),
            "synthetic_cells": len(synthetic),
        },
    )
    return results
