"""The expert loss gap as an input, not an output.

Investigation 7 tried to grade expert disagreement by blending real predictions
toward each other and measuring whatever gap resulted. That failed for a
specific reason: the blend changed the predictions and the gap together, so the
gap was not monotone in the blend, and the two sources' gap ranges never
overlapped (sunspots 0.11-2.10, CO2 0.003-0.055). Investigation 6's open
question — do the sources agree at a matched gap? — could therefore never be
asked.

This module inverts the loss function instead. ``_normalized_loss`` is
``|p - y| / (1 + |y|)``, so a prescribed normalized loss ``l`` is produced
exactly by ``p = y + s * l * (1 + |y|)``. The gap becomes the input.

Two assignments are run, because which expert is *systematically* best is a
separate variable from how large the gap is (Investigation 7's own open
question): ``fixed`` gives one expert the best loss every month, ``roving``
lets the real series decide who is best while keeping the gap the same size.

The protocol is frozen in ``experiments/exp_008_direct_gap/PROTOCOL.md``,
including the addendum that introduces the assignment axis, and was committed
before any measurement here was computed. Constants and the weighting rule are
imported from ``experiment_005_learning`` so the runs cannot silently diverge.
"""

from __future__ import annotations

import csv
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from feltteori_research.experiment_005_learning import (
    EXPERTS,
    RETENTIONS,
    _normalized_loss,
    _weights,
    colon_sha256,
    parse_silso_monthly,
)
from feltteori_research.experiment_006_order import parse_noaa_monthly
from feltteori_research.experiment_007_gradient import _expert_rows

METHOD_VERSION = "exp008.directgap.1"

# Frozen in the protocol. The gaps span the range the two preserved sources
# actually occupy (CO2 0.003-0.055, sunspots 0.11-2.10) so the question can be
# asked at a gap both sources can be held at.
GAPS = (0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8)
ASSIGNMENTS = ("fixed", "roving")

# Control: at gap 0 all three constructed experts have identical losses, so the
# softmax is uniform and the effective count is exactly 3. This is an analytic
# prediction, not a figure lifted from an earlier run.
CONTROL_TOLERANCE = 1e-9
CONTROL_EXPECTED = 3.0

# Calibration: the gap measured back off the constructed predictions must equal
# the prescribed gap. Floating-point exact, so the tolerance is tight.
CALIBRATION_TOLERANCE = 1e-9

# Falsification thresholds, copied verbatim from the frozen protocol.
THRESHOLD_HIGH = 2.0
THRESHOLD_LOW = 1.5
THRESHOLD_FACTOR = 3.0
SOURCE_DISAGREEMENT = 0.25


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


def _constructed_predictions(
    row: dict[str, object], gap: float, assignment: str
) -> tuple[dict[str, float], float]:
    """Three predictions whose normalized losses differ by a prescribed amount.

    ``l_best`` is measured on the real experts at this month, so the difficulty
    of the month is anchored in the observation rather than invented. The sign
    keeps the real over/under direction.
    """
    outcome = float(row["outcome"])
    real = {expert: float(row[f"prediction_{expert}"]) for expert in EXPERTS}
    real_losses = {expert: _normalized_loss(real[expert], outcome) for expert in EXPERTS}
    l_best = min(real_losses.values())
    scale = 1.0 + abs(outcome)

    if assignment == "fixed":
        order = list(EXPERTS)
    elif assignment == "roving":
        order = sorted(EXPERTS, key=lambda expert: real_losses[expert])
    else:
        raise ValueError(f"unknown assignment: {assignment}")

    deltas = {order[0]: 0.0, order[1]: gap / 2.0, order[2]: gap}

    predictions: dict[str, float] = {}
    for expert in EXPERTS:
        sign = 1.0 if real[expert] >= outcome else -1.0
        predictions[expert] = outcome + sign * (l_best + deltas[expert]) * scale
    return predictions, outcome


def _adaptive_evaluation(
    rows: list[dict[str, object]],
    retention: float,
    gap: float,
    assignment: str,
) -> dict[str, object]:
    """Run one adaptive mechanism over predictions with a prescribed gap."""
    retained = {expert: 0.0 for expert in EXPERTS}
    evaluation: list[dict[str, object]] = []
    for row in rows:
        predictions, outcome = _constructed_predictions(row, gap, assignment)
        weights = _weights(retained)
        prediction = sum(predictions[expert] * weights[expert] for expert in EXPERTS)
        losses = {
            expert: _normalized_loss(predictions[expert], outcome) for expert in EXPERTS
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
            expert: retention * retained[expert] + losses[expert] for expert in EXPERTS
        }
    return _aggregate(evaluation, gap)


def _aggregate(evaluation: list[dict[str, object]], prescribed_gap: float) -> dict[str, object]:
    count = len(evaluation)
    weight_changes: list[float] = []
    previous: dict[str, float] | None = None
    for row in evaluation:
        weights = row["weights"]
        assert isinstance(weights, dict)
        if previous is not None:
            weight_changes.append(sum(abs(weights[e] - previous[e]) for e in EXPERTS))
        previous = weights
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
        "mean_weight_change_l1": (
            sum(weight_changes) / len(weight_changes) if weight_changes else 0.0
        ),
        "mean_measured_gap": sum(float(r["measured_gap"]) for r in evaluation) / count,
        "max_gap_error": max(
            abs(float(r["measured_gap"]) - prescribed_gap) for r in evaluation
        ),
    }


def _control_check(cells: list[dict[str, object]]) -> dict[str, object]:
    """At gap 0 the softmax is uniform, so effective experts must be exactly 3."""
    checks: list[dict[str, object]] = []
    for cell in cells:
        if cell["gap"] != 0.0:
            continue
        measured = float(cell["mean_effective_experts"])
        checks.append(
            {
                "source": cell["source"],
                "assignment": cell["assignment"],
                "retention_condition": cell["retention_condition"],
                "measured_effective_experts": measured,
                "expected_effective_experts": CONTROL_EXPECTED,
                "ok": abs(measured - CONTROL_EXPECTED) <= CONTROL_TOLERANCE,
            }
        )
    return {"checks": checks, "passed": all(bool(c["ok"]) for c in checks)}


def _calibration_check(cells: list[dict[str, object]]) -> dict[str, object]:
    """The gap measured off the constructed predictions must be the prescribed one."""
    worst = max(float(cell["max_gap_error"]) for cell in cells)
    return {
        "worst_absolute_gap_error": worst,
        "tolerance": CALIBRATION_TOLERANCE,
        "passed": worst <= CALIBRATION_TOLERANCE,
    }


def _series(
    cells: list[dict[str, object]], source: str, assignment: str, retention_condition: str
) -> list[dict[str, object]]:
    rows = [
        {"gap": c["gap"], "mean_effective_experts": c["mean_effective_experts"]}
        for c in cells
        if c["source"] == source
        and c["assignment"] == assignment
        and c["retention_condition"] == retention_condition
    ]
    rows.sort(key=lambda row: float(row["gap"]))
    return rows


def _thresholds(cells: list[dict[str, object]]) -> dict[str, object]:
    """Smallest gap at which the mechanism is no longer responsive."""
    per_cell: list[dict[str, object]] = []
    for source in ("sunspots", "co2"):
        for assignment in ASSIGNMENTS:
            for retention_condition, retention in RETENTIONS.items():
                series = _series(cells, source, assignment, retention_condition)
                crossed = next(
                    (
                        row
                        for row in series
                        if float(row["mean_effective_experts"]) < THRESHOLD_LOW
                    ),
                    None,
                )
                per_cell.append(
                    {
                        "source": source,
                        "assignment": assignment,
                        "retention_condition": retention_condition,
                        "retention": retention,
                        "expected_threshold": 1.0 - retention,
                        "measured_threshold": (
                            crossed["gap"] if crossed is not None else None
                        ),
                        "series": series,
                    }
                )
    return {"per_cell": per_cell}


def _condition_1_no_threshold(thresholds: dict[str, object]) -> dict[str, object]:
    """Count retentions with r<1 that never fall from above 2.0 to below 1.5."""
    per_cell = thresholds["per_cell"]
    assert isinstance(per_cell, list)
    by_key: dict[tuple[str, str, str], dict[str, object]] = {}
    for cell in per_cell:
        if float(cell["retention"]) >= 1.0:
            continue
        key = (cell["source"], cell["assignment"], cell["retention_condition"])
        by_key[key] = cell
    never_crossed = [
        {
            "source": key[0],
            "assignment": key[1],
            "retention_condition": key[2],
            "peak": max(float(r["mean_effective_experts"]) for r in cell["series"]),
        }
        for key, cell in by_key.items()
        if cell["measured_threshold"] is None
    ]
    # The protocol counts retentions, not cells: a retention fires the condition
    # only if it fails on both sources and both assignments.
    failing_retentions = {
        cell["retention_condition"]
        for cell in never_crossed
        if sum(
            1
            for other in never_crossed
            if other["retention_condition"] == cell["retention_condition"]
        )
        >= 2
    }
    return {
        "never_crossed": never_crossed,
        "failing_retentions": sorted(failing_retentions),
        "fired": len(failing_retentions) >= 2,
    }


def _condition_2_threshold_off(thresholds: dict[str, object]) -> dict[str, object]:
    """Does the measured threshold sit within a factor of 3 of (1 - r)?"""
    per_cell = thresholds["per_cell"]
    assert isinstance(per_cell, list)
    off: list[dict[str, object]] = []
    for cell in per_cell:
        retention = float(cell["retention"])
        measured = cell["measured_threshold"]
        if retention >= 1.0 or measured is None:
            continue
        expected = 1.0 - retention
        if expected <= 0:
            continue
        ratio = max(float(measured), expected) / min(float(measured), expected)
        if ratio > THRESHOLD_FACTOR:
            off.append(
                {
                    "source": cell["source"],
                    "assignment": cell["assignment"],
                    "retention_condition": cell["retention_condition"],
                    "expected_threshold": expected,
                    "measured_threshold": measured,
                    "ratio": ratio,
                }
            )
    off_retentions = {entry["retention_condition"] for entry in off}
    return {
        "off": off,
        "off_retentions": sorted(off_retentions),
        "fired": len(off_retentions) >= 2,
    }


def _condition_3_source_matters(cells: list[dict[str, object]]) -> dict[str, object]:
    """At identical gap and retention, do the two sources disagree?"""
    disagreements: list[dict[str, object]] = []
    for assignment in ASSIGNMENTS:
        for retention_condition in RETENTIONS:
            for gap in GAPS:
                pair = {
                    c["source"]: c
                    for c in cells
                    if c["assignment"] == assignment
                    and c["retention_condition"] == retention_condition
                    and c["gap"] == gap
                }
                if set(pair) != {"sunspots", "co2"}:
                    continue
                difference = abs(
                    float(pair["sunspots"]["mean_effective_experts"])
                    - float(pair["co2"]["mean_effective_experts"])
                )
                if difference > SOURCE_DISAGREEMENT:
                    disagreements.append(
                        {
                            "assignment": assignment,
                            "retention_condition": retention_condition,
                            "gap": gap,
                            "sunspots_effective": pair["sunspots"][
                                "mean_effective_experts"
                            ],
                            "co2_effective": pair["co2"]["mean_effective_experts"],
                            "difference": difference,
                        }
                    )
    # The protocol's addendum requires this condition to be read within each
    # assignment mode separately, so a difference between modes cannot be
    # mistaken for a difference between sources. Reporting only the pooled
    # count hides exactly that: the first run pooled both modes and returned
    # `falsified`, while the fixed mode — the one where the gap is the only
    # variable — disagreed in 1 of 40 cells and the roving mode in 11 of 40.
    per_assignment: dict[str, object] = {}
    for assignment in ASSIGNMENTS:
        subset = [d for d in disagreements if d["assignment"] == assignment]
        cells_in_mode = len(RETENTIONS) * len(GAPS)
        per_assignment[assignment] = {
            "disagreements": subset,
            "count": len(subset),
            "cells": cells_in_mode,
            "fired": bool(subset),
        }
    return {
        "disagreements": disagreements,
        "count": len(disagreements),
        "per_assignment": per_assignment,
        "fired": bool(disagreements),
    }


def _condition_5_assignment_inert(cells: list[dict[str, object]]) -> dict[str, object]:
    """Does the assignment axis change anything at all?"""
    differences: list[dict[str, object]] = []
    for source in ("sunspots", "co2"):
        for retention_condition in RETENTIONS:
            for gap in GAPS:
                fixed = next(
                    (
                        c
                        for c in cells
                        if c["source"] == source
                        and c["retention_condition"] == retention_condition
                        and c["gap"] == gap
                        and c["assignment"] == "fixed"
                    ),
                    None,
                )
                roving = next(
                    (
                        c
                        for c in cells
                        if c["source"] == source
                        and c["retention_condition"] == retention_condition
                        and c["gap"] == gap
                        and c["assignment"] == "roving"
                    ),
                    None,
                )
                if fixed is None or roving is None:
                    continue
                difference = abs(
                    float(fixed["mean_effective_experts"])
                    - float(roving["mean_effective_experts"])
                )
                if difference > SOURCE_DISAGREEMENT:
                    differences.append(
                        {
                            "source": source,
                            "retention_condition": retention_condition,
                            "gap": gap,
                            "fixed_effective": fixed["mean_effective_experts"],
                            "roving_effective": roving["mean_effective_experts"],
                            "difference": difference,
                        }
                    )
    return {
        "differences": differences,
        "count": len(differences),
        "inert": not differences,
    }


def run_investigation(
    silso_path: Path, noaa_path: Path, output_directory: Path
) -> dict[str, object]:
    """Run the mechanism at a prescribed expert loss gap on both preserved series."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspot_observations, sunspot_excluded = parse_silso_monthly(silso_path)
    co2_observations, co2_excluded = parse_noaa_monthly(noaa_path)

    sources = {
        "sunspots": _expert_rows(sunspot_observations),
        "co2": _expert_rows(co2_observations),
    }

    cells: list[dict[str, object]] = []
    for name, rows in sources.items():
        for gap in GAPS:
            for assignment in ASSIGNMENTS:
                for retention_condition, retention in RETENTIONS.items():
                    result = _adaptive_evaluation(rows, retention, gap, assignment)
                    cells.append(
                        {
                            "source": name,
                            "gap": gap,
                            "assignment": assignment,
                            "retention_condition": retention_condition,
                            "retention": retention,
                            "rows": result["rows"],
                            "mae": result["mae"],
                            "mean_effective_experts": result["mean_effective_experts"],
                            "min_effective_experts": result["min_effective_experts"],
                            "mean_weight_change_l1": result["mean_weight_change_l1"],
                            "mean_measured_gap": result["mean_measured_gap"],
                            "max_gap_error": result["max_gap_error"],
                        }
                    )

    control = _control_check(cells)
    calibration = _calibration_check(cells)
    thresholds = _thresholds(cells)
    no_threshold = _condition_1_no_threshold(thresholds)
    threshold_off = _condition_2_threshold_off(thresholds)
    source_matters = _condition_3_source_matters(cells)
    assignment_inert = _condition_5_assignment_inert(cells)

    conditions = {
        "1_no_threshold": bool(no_threshold["fired"]),
        "2_threshold_not_near_one_minus_r": bool(threshold_off["fired"]),
        "3_source_matters_at_matched_gap": bool(source_matters["fired"]),
        "4_control_failed": not bool(control["passed"]),
        "5_calibration_failed": not bool(calibration["passed"]),
    }
    if conditions["4_control_failed"] or conditions["5_calibration_failed"]:
        verdict = "instrument_fault"
    elif conditions["1_no_threshold"] or conditions["3_source_matters_at_matched_gap"]:
        verdict = "falsified"
    elif conditions["2_threshold_not_near_one_minus_r"]:
        verdict = "partially_falsified_accumulation_argument_wrong"
    else:
        verdict = "not_falsified"

    manifest = {
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
            "experts": list(EXPERTS),
            "gaps": list(GAPS),
            "assignments": list(ASSIGNMENTS),
            "retentions": RETENTIONS,
            "evaluation_start": "2000-01",
            "construction": "p = y + sign * l * (1 + |y|), l in {l_best, l_best+gap/2, l_best+gap}",
        },
        "runtime": {"python": platform.python_version()},
    }
    results = {
        "method_version": METHOD_VERSION,
        "control": control,
        "calibration": calibration,
        "thresholds": thresholds,
        "condition_1_no_threshold": no_threshold,
        "condition_2_threshold_not_near_one_minus_r": threshold_off,
        "condition_3_source_matters_at_matched_gap": source_matters,
        "condition_5_assignment_axis": assignment_inert,
        "conditions_fired": conditions,
        "verdict": verdict,
    }

    _write_csv(output_directory / "exp008_cells.csv", cells)
    _write_json(output_directory / "manifest.json", manifest)
    _write_json(output_directory / "exp008_results.json", results)
    return results
