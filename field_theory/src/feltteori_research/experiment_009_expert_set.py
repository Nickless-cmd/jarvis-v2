"""Does the collapse threshold depend on the expert set, or on the mechanism?

Investigation 8 constructed the expert loss gap directly and found the collapse
threshold near ``1 - r`` on two sources, two assignment modes and four
retention conditions — but on a single expert set (``previous_month``,
``trailing_12_mean``, ``cycle_lag_132``). That set is a modelling choice.

This experiment varies the set and the number of experts while holding the
mechanism fixed, and asks whether ``1 - r`` survives. The protocol is frozen in
``experiments/exp_009_expert_set/PROTOCOL.md`` and was committed before any
measurement was computed.

The one thing that must not drift silently is the weight function: the local
version takes the expert set as a parameter, where ``experiment_005``'s reads a
module constant. Control 2 proves the two agree bit-for-bit on the original set
before any other row is allowed to carry a verdict.
"""

from __future__ import annotations

import csv
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path

from feltteori_research.experiment_005_learning import (
    EXPERTS,
    LEARNING_RATE,
    RETENTIONS,
    WARMUP_MONTHS,
    _normalized_loss,
    _weights,
    colon_sha256,
    parse_silso_monthly,
)
from feltteori_research.experiment_006_order import parse_noaa_monthly
from feltteori_research.experiment_007_gradient import _expert_rows, _period

METHOD_VERSION = "exp009.expertset.1"

# Frozen in the protocol. The original set is the control: it must reproduce
# Investigation 8 exactly.
EXPERT_SETS: dict[str, tuple[str, ...]] = {
    "original": ("previous_month", "trailing_12_mean", "cycle_lag_132"),
    "short_memory": ("trailing_3_mean", "trailing_6_mean", "seasonal_naive_12"),
    "long_memory": ("trailing_24_mean", "cycle_lag_66", "cycle_lag_132"),
    "two_experts": ("previous_month", "trailing_12_mean"),
    "four_experts": (
        "previous_month",
        "trailing_3_mean",
        "trailing_12_mean",
        "cycle_lag_132",
    ),
}

# The gaps, retentions and assignments are copied from Investigation 8 unchanged
# so the two experiments answer the same question at the same points.
GAPS = (0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8)
ASSIGNMENTS = ("fixed", "roving")

# Investigation 8's absolute floor was 1.5 with three experts, i.e. exactly half
# the available experts. Expressing it as a fraction is what makes sets of two
# and four comparable; for the original set the value is unchanged.
THRESHOLD_FRACTION = 0.5

# Falsification thresholds, copied verbatim from the frozen protocol.
THRESHOLD_FACTOR = 3.0

CALIBRATION_TOLERANCE = 1e-9
WEIGHT_IDENTITY_TOLERANCE = 0.0  # bit-identical, so the tolerance is exact
UNIFORM_TOLERANCE = 1e-9

# Investigation 8's measured thresholds for the original set, read from
# artifacts/exp_008_direct_gap/run_20261125_v2/. Used by control 1.
CONTROL_EXPECTED_THRESHOLDS = {
    ("sunspots", "fixed", "one_encounter"): None,
    ("sunspots", "fixed", "short_continuity"): 0.2,
    ("sunspots", "fixed", "long_continuity"): 0.02,
    ("sunspots", "fixed", "cumulative_continuity"): 0.002,
    ("co2", "fixed", "one_encounter"): None,
    ("co2", "fixed", "short_continuity"): 0.2,
    ("co2", "fixed", "long_continuity"): 0.02,
    ("co2", "fixed", "cumulative_continuity"): 0.005,
}


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("refusing to write an empty table")
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _weights_for(
    retained_losses: dict[str, float], experts: tuple[str, ...]
) -> dict[str, float]:
    """Softmax over accumulated loss, for an arbitrary expert set.

    Mathematically identical to ``experiment_005_learning._weights``, which
    reads the module constant ``EXPERTS`` instead. Control 2 proves the
    identity rather than trusting this comment.
    """
    minimum = min(retained_losses.values())
    unscaled = {
        expert: math.exp(-LEARNING_RATE * (retained_losses[expert] - minimum))
        for expert in experts
    }
    total = sum(unscaled.values())
    return {expert: unscaled[expert] / total for expert in experts}


def _predict(observations: list[object], index: int, name: str) -> float:
    """One expert's prediction at ``index``, from the preserved observations."""
    if name == "previous_month":
        return float(getattr(observations[index - 1], "value"))
    if name == "seasonal_naive_12":
        return float(getattr(observations[index - 12], "value"))
    if name.startswith("trailing_"):
        window = int(name.removeprefix("trailing_").removesuffix("_mean"))
        values = [
            float(getattr(row, "value")) for row in observations[index - window : index]
        ]
        return sum(values) / len(values)
    if name.startswith("cycle_lag_"):
        lag = int(name.removeprefix("cycle_lag_"))
        return float(getattr(observations[index - lag], "value"))
    raise ValueError(f"unknown expert: {name}")


def _expert_rows_for(
    observations: list[object], experts: tuple[str, ...]
) -> list[dict[str, object]]:
    """Per-month predictions for an arbitrary expert set, in exp_005's row form."""
    longest_lookback = 0
    for name in experts:
        if name == "seasonal_naive_12":
            longest_lookback = max(longest_lookback, 12)
        elif name.startswith("trailing_"):
            window = int(name.removeprefix("trailing_").removesuffix("_mean"))
            longest_lookback = max(longest_lookback, window)
        elif name.startswith("cycle_lag_"):
            lag = int(name.removeprefix("cycle_lag_"))
            longest_lookback = max(longest_lookback, lag)
        elif name != "previous_month":
            raise ValueError(f"unknown expert: {name}")
    if longest_lookback > WARMUP_MONTHS:
        raise ValueError(
            f"expert set needs {longest_lookback} months of history, "
            f"warmup only provides {WARMUP_MONTHS}"
        )

    rows: list[dict[str, object]] = []
    for index in range(WARMUP_MONTHS, len(observations)):
        observation = observations[index]
        year = int(getattr(observation, "year"))
        month = int(getattr(observation, "month"))
        rows.append(
            {
                "date": f"{year:04d}-{month:02d}",
                "period": _period(year, month),
                "outcome": float(getattr(observation, "value")),
                **{
                    f"prediction_{name}": _predict(observations, index, name)
                    for name in experts
                },
            }
        )
    return rows


def _constructed_predictions(
    row: dict[str, object],
    gap: float,
    assignment: str,
    experts: tuple[str, ...],
) -> tuple[dict[str, float], float]:
    """Predictions whose normalized losses differ by exactly ``gap``.

    ``l_best`` is measured on the real experts at this month so the difficulty
    of the month stays anchored in the observation, and the over/under sign is
    kept from the real experts. This is Investigation 8's construction with the
    expert set passed in instead of read from a constant.
    """
    outcome = float(row["outcome"])
    real = {expert: float(row[f"prediction_{expert}"]) for expert in experts}
    real_losses = {expert: _normalized_loss(real[expert], outcome) for expert in experts}
    l_best = min(real_losses.values())
    scale = 1.0 + abs(outcome)

    if assignment == "fixed":
        order = list(experts)
    elif assignment == "roving":
        order = sorted(experts, key=lambda expert: real_losses[expert])
    else:
        raise ValueError(f"unknown assignment: {assignment}")

    deltas: dict[str, float] = {}
    for rank, expert in enumerate(order):
        if len(experts) == 2:
            deltas[expert] = gap * rank
        else:
            # Investigation 8's spacing: best at 0, worst at gap, the middle at
            # gap/2. For four experts the remaining ones are spread evenly.
            deltas[expert] = gap * rank / (len(order) - 1)

    predictions: dict[str, float] = {}
    for expert in experts:
        sign = 1.0 if real[expert] >= outcome else -1.0
        predictions[expert] = outcome + sign * (l_best + deltas[expert]) * scale
    return predictions, outcome


def _adaptive_evaluation(
    rows: list[dict[str, object]],
    retention: float,
    gap: float,
    assignment: str,
    experts: tuple[str, ...],
) -> dict[str, object]:
    """Run one adaptive mechanism over predictions with a prescribed gap."""
    retained = {expert: 0.0 for expert in experts}
    evaluation: list[dict[str, object]] = []
    for row in rows:
        predictions, outcome = _constructed_predictions(row, gap, assignment, experts)
        weights = _weights_for(retained, experts)
        prediction = sum(predictions[expert] * weights[expert] for expert in experts)
        losses = {
            expert: _normalized_loss(predictions[expert], outcome) for expert in experts
        }
        if row["period"] == "evaluation":
            evaluation.append(
                {
                    "prediction": prediction,
                    "absolute_error": abs(prediction - outcome),
                    "effective_experts": 1.0
                    / sum(weight * weight for weight in weights.values()),
                    "weights": dict(weights),
                    "measured_gap": max(losses.values()) - min(losses.values()),
                }
            )
        retained = {
            expert: retention * retained[expert] + losses[expert] for expert in experts
        }
    return _aggregate(evaluation, gap)


def _aggregate(
    evaluation: list[dict[str, object]], prescribed_gap: float
) -> dict[str, object]:
    count = len(evaluation)
    return {
        "rows": count,
        "mae": sum(float(r["absolute_error"]) for r in evaluation) / count,
        "mean_effective_experts": sum(
            float(r["effective_experts"]) for r in evaluation
        )
        / count,
        "min_effective_experts": min(
            float(r["effective_experts"]) for r in evaluation
        ),
        "mean_measured_gap": sum(float(r["measured_gap"]) for r in evaluation) / count,
        "max_gap_error": max(
            abs(float(r["measured_gap"]) - prescribed_gap) for r in evaluation
        ),
    }


def _control_weight_identity() -> dict[str, object]:
    """The local weight function must equal exp_005's on the original set.

    Compared on a fixed grid of loss vectors that spans the shapes the mechanism
    actually produces, not just one vector.
    """
    grids = [
        {"previous_month": 0.0, "trailing_12_mean": 0.0, "cycle_lag_132": 0.0},
        {"previous_month": 0.0, "trailing_12_mean": 0.01, "cycle_lag_132": 0.02},
        {"previous_month": 0.5, "trailing_12_mean": 0.0, "cycle_lag_132": 0.1},
        {"previous_month": 12.5, "trailing_12_mean": 12.51, "cycle_lag_132": 12.52},
        {"previous_month": 0.0001, "trailing_12_mean": 2.0, "cycle_lag_132": 0.0001},
    ]
    worst = 0.0
    for grid in grids:
        local = _weights_for(grid, EXPERTS)
        original = _weights(grid)
        for expert in EXPERTS:
            worst = max(worst, abs(local[expert] - original[expert]))
    return {"worst_absolute_difference": worst, "passed": worst <= WEIGHT_IDENTITY_TOLERANCE}


def _control_expert_rows_identity(
    sunspot_observations: list[object], co2_observations: list[object]
) -> dict[str, object]:
    """The parameterised row builder must reproduce exp_007's on the original set."""
    checks: list[dict[str, object]] = []
    for name, observations in (
        ("sunspots", sunspot_observations),
        ("co2", co2_observations),
    ):
        parameterised = _expert_rows_for(observations, EXPERTS)
        reference = _expert_rows(observations)
        identical = len(parameterised) == len(reference)
        worst = 0.0
        if identical:
            for a, b in zip(parameterised, reference, strict=True):
                if a["date"] != b["date"] or a["period"] != b["period"]:
                    identical = False
                    break
                for expert in EXPERTS:
                    worst = max(
                        worst,
                        abs(float(a[f"prediction_{expert}"]) - float(b[f"prediction_{expert}"])),
                    )
                worst = max(worst, abs(float(a["outcome"]) - float(b["outcome"])))
        checks.append(
            {
                "source": name,
                "rows": len(parameterised),
                "same_structure": identical,
                "worst_absolute_difference": worst,
                "ok": identical and worst <= 0.0,
            }
        )
    return {"checks": checks, "passed": all(bool(c["ok"]) for c in checks)}


def _control_uniform(cells: list[dict[str, object]]) -> dict[str, object]:
    """At gap 0 the softmax is uniform, so the effective count must be exactly N."""
    checks: list[dict[str, object]] = []
    for cell in cells:
        if cell["gap"] != 0.0:
            continue
        measured = float(cell["mean_effective_experts"])
        expected = float(len(EXPERT_SETS[str(cell["expert_set"])]))
        checks.append(
            {
                "expert_set": cell["expert_set"],
                "source": cell["source"],
                "assignment": cell["assignment"],
                "retention_condition": cell["retention_condition"],
                "measured": measured,
                "expected": expected,
                "ok": abs(measured - expected) <= UNIFORM_TOLERANCE,
            }
        )
    return {"checks": checks, "passed": all(bool(c["ok"]) for c in checks)}


def _control_calibration(cells: list[dict[str, object]]) -> dict[str, object]:
    """The gap measured off the constructed predictions must be the prescribed one."""
    worst = max(float(cell["max_gap_error"]) for cell in cells)
    return {"worst_absolute_gap_error": worst, "passed": worst <= CALIBRATION_TOLERANCE}


def _control_reproduction(thresholds: dict[str, object]) -> dict[str, object]:
    """The original set must reproduce Investigation 8's measured thresholds."""
    checks: list[dict[str, object]] = []
    for cell in thresholds["per_cell"]:  # type: ignore[index]
        if cell["expert_set"] != "original" or cell["assignment"] != "fixed":
            continue
        key = (cell["source"], cell["assignment"], cell["retention_condition"])
        if key not in CONTROL_EXPECTED_THRESHOLDS:
            continue
        expected = CONTROL_EXPECTED_THRESHOLDS[key]
        measured = cell["measured_threshold"]
        if expected is None:
            ok = measured is None
        else:
            ok = measured is not None and abs(float(measured) - float(expected)) <= 1e-12
        checks.append(
            {
                "source": key[0],
                "retention_condition": key[2],
                "expected": expected,
                "measured": measured,
                "ok": ok,
            }
        )
    return {"checks": checks, "passed": all(bool(c["ok"]) for c in checks)}


def _thresholds(cells: list[dict[str, object]]) -> dict[str, object]:
    """Smallest gap at which the mechanism is no longer responsive, per cell."""
    per_cell: list[dict[str, object]] = []
    for expert_set, experts in EXPERT_SETS.items():
        floor = THRESHOLD_FRACTION * len(experts)
        for source in ("sunspots", "co2"):
            for assignment in ASSIGNMENTS:
                for retention_condition, retention in RETENTIONS.items():
                    series = _series(cells, expert_set, source, assignment, retention_condition)
                    crossed = next(
                        (
                            row
                            for row in series
                            if float(row["mean_effective_experts"]) < floor
                        ),
                        None,
                    )
                    per_cell.append(
                        {
                            "expert_set": expert_set,
                            "experts": len(experts),
                            "source": source,
                            "assignment": assignment,
                            "retention_condition": retention_condition,
                            "retention": retention,
                            "floor": floor,
                            "expected_threshold": 1.0 - retention,
                            "measured_threshold": crossed["gap"] if crossed is not None else None,
                            "series": series,
                        }
                    )
    return {"per_cell": per_cell}


def _series(
    cells: list[dict[str, object]],
    expert_set: str,
    source: str,
    assignment: str,
    retention_condition: str,
) -> list[dict[str, object]]:
    subset = [
        c
        for c in cells
        if c["expert_set"] == expert_set
        and c["source"] == source
        and c["assignment"] == assignment
        and c["retention_condition"] == retention_condition
    ]
    return sorted(subset, key=lambda c: float(c["gap"]))


def _condition_1_set_dependence(thresholds: dict[str, object]) -> dict[str, object]:
    """Does 1-r survive the expert set? Evaluated on fixed assignment only."""
    rows: list[dict[str, object]] = []
    for cell in thresholds["per_cell"]:  # type: ignore[index]
        if cell["assignment"] != "fixed":
            continue
        if cell["expert_set"] == "original":
            continue
        measured = cell["measured_threshold"]
        expected = float(cell["expected_threshold"])
        if measured is None or expected <= 0.0:
            continue
        ratio = float(measured) / expected
        rows.append(
            {
                "expert_set": cell["expert_set"],
                "source": cell["source"],
                "retention_condition": cell["retention_condition"],
                "measured": measured,
                "expected": expected,
                "ratio": ratio,
                "within_factor": (1.0 / THRESHOLD_FACTOR) <= ratio <= THRESHOLD_FACTOR,
            }
        )
    failing = [row for row in rows if not bool(row["within_factor"])]
    # The condition is stated on both sources: a set that only breaks on one
    # source is a source effect, not an expert-set effect.
    sources_by_set: dict[str, set[str]] = {}
    for row in failing:
        sources_by_set.setdefault(str(row["expert_set"]), set()).add(str(row["source"]))
    fired_on_both = sorted(
        name for name, sources in sources_by_set.items() if len(sources) == 2
    )
    return {
        "rows": rows,
        "failing_rows": failing,
        "sets_failing_on_both_sources": fired_on_both,
        "fired": bool(fired_on_both),
    }


def _condition_2_count_matters(thresholds: dict[str, object]) -> dict[str, object]:
    """Does the number of experts move the threshold by more than a factor?"""
    index = {
        (c["expert_set"], c["source"], c["assignment"], c["retention_condition"]): c
        for c in thresholds["per_cell"]  # type: ignore[index]
    }
    rows: list[dict[str, object]] = []
    for other in ("two_experts", "four_experts"):
        for source in ("sunspots", "co2"):
            for assignment in ASSIGNMENTS:
                for retention_condition in RETENTIONS:
                    key_other = (other, source, assignment, retention_condition)
                    key_original = ("original", source, assignment, retention_condition)
                    a = index.get(key_other)
                    b = index.get(key_original)
                    if a is None or b is None:
                        continue
                    measured_other = a["measured_threshold"]
                    measured_original = b["measured_threshold"]
                    if measured_other is None or measured_original is None:
                        ratio = None
                        within = True
                    else:
                        ratio = float(measured_other) / float(measured_original)
                        within = (1.0 / THRESHOLD_FACTOR) <= ratio <= THRESHOLD_FACTOR
                    rows.append(
                        {
                            "expert_set": other,
                            "source": source,
                            "assignment": assignment,
                            "retention_condition": retention_condition,
                            "measured_other": measured_other,
                            "measured_original": measured_original,
                            "ratio": ratio,
                            "within_factor": within,
                        }
                    )
    failing = [row for row in rows if not bool(row["within_factor"])]
    return {"rows": rows, "failing_rows": failing, "fired": bool(failing)}


def run_investigation(
    silso_path: Path, noaa_path: Path, output_directory: Path
) -> dict[str, object]:
    """Run the mechanism at a prescribed gap across several expert sets."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspot_observations, sunspot_excluded = parse_silso_monthly(silso_path)
    co2_observations, co2_excluded = parse_noaa_monthly(noaa_path)

    observations = {"sunspots": sunspot_observations, "co2": co2_observations}

    control_rows = _control_expert_rows_identity(sunspot_observations, co2_observations)
    control_weights = _control_weight_identity()
    if not control_rows["passed"] or not control_weights["passed"]:
        raise SystemExit(
            "control failed before any cell was run: the parameterised builders do "
            f"not reproduce the originals. rows={control_rows} weights={control_weights}"
        )

    sources = {
        f"{name}::{expert_set}": _expert_rows_for(series, experts)
        for name, series in observations.items()
        for expert_set, experts in EXPERT_SETS.items()
    }

    cells: list[dict[str, object]] = []
    for key, rows in sources.items():
        source, expert_set = key.split("::")
        experts = EXPERT_SETS[expert_set]
        for gap in GAPS:
            for assignment in ASSIGNMENTS:
                for retention_condition, retention in RETENTIONS.items():
                    result = _adaptive_evaluation(rows, retention, gap, assignment, experts)
                    cells.append(
                        {
                            "expert_set": expert_set,
                            "experts": len(experts),
                            "source": source,
                            "assignment": assignment,
                            "retention_condition": retention_condition,
                            "retention": retention,
                            "gap": gap,
                            **result,
                        }
                    )

    thresholds = _thresholds(cells)

    control = {
        "expert_rows_identity": control_rows,
        "weight_identity": control_weights,
        "uniform": _control_uniform(cells),
        "calibration": _control_calibration(cells),
        "reproduction": _control_reproduction(thresholds),
    }
    controls_passed = all(bool(v["passed"]) for v in control.values())

    condition_1 = _condition_1_set_dependence(thresholds)
    condition_2 = _condition_2_count_matters(thresholds)

    conditions = {
        "1_set_dependence": bool(condition_1["fired"]),
        "2_count_matters": bool(condition_2["fired"]),
        "3_control_failed": not controls_passed,
    }

    if conditions["3_control_failed"]:
        verdict = "instrument_fault"
    elif conditions["1_set_dependence"] or conditions["2_count_matters"]:
        verdict = "falsified"
    else:
        verdict = "not_falsified"

    results = {
        "method_version": METHOD_VERSION,
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
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
        "parameters": {
            "expert_sets": {name: list(experts) for name, experts in EXPERT_SETS.items()},
            "gaps": list(GAPS),
            "retentions": RETENTIONS,
            "assignments": list(ASSIGNMENTS),
            "learning_rate": LEARNING_RATE,
            "warmup_months": WARMUP_MONTHS,
            "evaluation_start": "2000-01",
            "threshold_fraction": THRESHOLD_FRACTION,
            "threshold_factor": THRESHOLD_FACTOR,
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "control": control,
        "controls_passed": controls_passed,
        "thresholds": thresholds,
        "condition_1_set_dependence": condition_1,
        "condition_2_count_matters": condition_2,
        "conditions_fired": conditions,
        "verdict": verdict,
    }

    _write_json(output_directory / "results.json", results)
    _write_csv(
        output_directory / "cells.csv",
        [
            {
                key: cell[key]
                for key in (
                    "expert_set",
                    "experts",
                    "source",
                    "assignment",
                    "retention_condition",
                    "retention",
                    "gap",
                    "rows",
                    "mae",
                    "mean_effective_experts",
                    "min_effective_experts",
                    "mean_measured_gap",
                    "max_gap_error",
                )
            }
            for cell in cells
        ],
    )
    _write_csv(
        output_directory / "thresholds.csv",
        [
            {
                key: cell[key]
                for key in (
                    "expert_set",
                    "experts",
                    "source",
                    "assignment",
                    "retention_condition",
                    "retention",
                    "floor",
                    "expected_threshold",
                    "measured_threshold",
                )
            }
            for cell in thresholds["per_cell"]  # type: ignore[index]
        ],
    )
    return results
