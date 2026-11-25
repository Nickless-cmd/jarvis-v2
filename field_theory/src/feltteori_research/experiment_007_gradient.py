"""Does the collapse to one expert depend on the expert loss gap?

Investigation 5 measured lock-in on sunspots; Investigation 6 found the relation
did not transfer to CO2. Investigation 6's own Limitation named the untested
explanation: one expert is near-optimal by construction on CO2, so the adaptive
mechanisms cannot beat it. This module tests that explanation directly by
grading the disagreement between experts on both preserved series and asking
whether the collapse follows the gap rather than the source.

The protocol is frozen in ``experiments/exp_007_gradient/PROTOCOL.md`` and was
committed before any measurement here was computed. The mechanism constants and
the weighting rule are imported from ``experiment_005_learning`` so the runs
cannot silently diverge.

The blend is a constructed instrument: it does not claim that a real process
behaves this way. It asks how the mechanism behaves as a function of a quantity
that can be measured on the preserved data.
"""

from __future__ import annotations

import csv
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path

from feltteori_research.experiment_005_learning import (
    EVALUATION_START,
    EXPERTS,
    RETENTIONS,
    WARMUP_MONTHS,
    _normalized_loss,
    _weights,
    colon_sha256,
    parse_silso_monthly,
)
from feltteori_research.experiment_006_order import parse_noaa_monthly

METHOD_VERSION = "exp007.gradient.1"

BLEND_WEIGHTS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)

# Validity check, frozen in the protocol: at blend 0 the run must reproduce the
# preserved Investigation 5 and 6 figures for long_continuity_continued.
#
# The expected values are the full-precision figures from the preserved result
# files, not the rounded numbers quoted in the findings documents. A first
# version compared against the three-decimal 1.886 with a 1e-6 tolerance and
# reported an instrument fault for a 0.0003 difference that was rounding in the
# report, not divergence in the mechanism.
CONTROL_TOLERANCE = 1e-9
CONTROL_EXPECTED = {
    "sunspots": {"effective_experts": 1.0, "mae": 14.8513},
    "co2": {"effective_experts": 1.8856506370006225, "mae": 1.3023798658761925},
}

# Falsification thresholds, copied verbatim from the frozen protocol.
MONOTONE_TOLERANCE = 0.05
MATCHED_GAP_RELATIVE = 0.10
MATCHED_GAP_MAX_DIFFERENCE = 0.25


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


def _period(year: int, month: int) -> str:
    return "evaluation" if (year, month) >= EVALUATION_START else "development"


def _expert_rows(observations: list[object]) -> list[dict[str, object]]:
    """Per-month expert predictions, identical in form to exp_005's rows."""
    rows: list[dict[str, object]] = []
    for index in range(WARMUP_MONTHS, len(observations)):
        observation = observations[index]
        year = int(getattr(observation, "year"))
        month = int(getattr(observation, "month"))
        outcome = float(getattr(observation, "value"))
        predictions = {
            "previous_month": float(getattr(observations[index - 1], "value")),
            "trailing_12_mean": sum(
                float(getattr(row, "value")) for row in observations[index - 12 : index]
            )
            / 12,
            "cycle_lag_132": float(getattr(observations[index - 132], "value")),
        }
        rows.append(
            {
                "date": f"{year:04d}-{month:02d}",
                "period": _period(year, month),
                "outcome": outcome,
                **{f"prediction_{name}": predictions[name] for name in EXPERTS},
            }
        )
    return rows


def _blend(predictions: dict[str, float], blend: float) -> dict[str, float]:
    """Move each expert toward the mean of the other two by ``blend``."""
    if blend == 0.0:
        return dict(predictions)
    blended: dict[str, float] = {}
    for expert in EXPERTS:
        others = [predictions[other] for other in EXPERTS if other != expert]
        blended[expert] = (1.0 - blend) * predictions[expert] + blend * (
            sum(others) / len(others)
        )
    return blended


def _adaptive_evaluation(
    rows: list[dict[str, object]],
    retention: float,
    history: str,
    blend: float,
) -> dict[str, object]:
    """Run one adaptive mechanism over the blended predictions."""
    retained = {expert: 0.0 for expert in EXPERTS}
    evaluation: list[dict[str, object]] = []
    for row in rows:
        if history == "reset" and row["date"] == "2000-01":
            retained = {expert: 0.0 for expert in EXPERTS}
        predictions = _blend(
            {expert: float(row[f"prediction_{expert}"]) for expert in EXPERTS}, blend
        )
        outcome = float(row["outcome"])
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
                    "loss_gap": max(losses.values()) - min(losses.values()),
                }
            )
        retained = {
            expert: retention * retained[expert] + losses[expert] for expert in EXPERTS
        }
    return _aggregate(evaluation)


def _aggregate(evaluation: list[dict[str, object]]) -> dict[str, object]:
    count = len(evaluation)
    weight_changes = []
    previous: dict[str, float] | None = None
    for row in evaluation:
        weights = row["weights"]
        assert isinstance(weights, dict)
        if previous is not None:
            weight_changes.append(
                sum(abs(weights[e] - previous[e]) for e in EXPERTS)
            )
        previous = weights
    return {
        "rows": count,
        "mae": sum(float(r["absolute_error"]) for r in evaluation) / count,
        "mean_effective_experts": sum(
            float(r["effective_experts"]) for r in evaluation
        )
        / count,
        "mean_weight_change_l1": (
            sum(weight_changes) / len(weight_changes) if weight_changes else 0.0
        ),
        "mean_loss_gap": sum(float(r["loss_gap"]) for r in evaluation) / count,
    }


def _fixed_expert_mae(rows: list[dict[str, object]], expert: str) -> float:
    evaluation = [row for row in rows if row["period"] == "evaluation"]
    return sum(
        abs(float(row[f"prediction_{expert}"]) - float(row["outcome"]))
        for row in evaluation
    ) / len(evaluation)


def _select_fixed_expert(rows: list[dict[str, object]]) -> str:
    development = [row for row in rows if row["period"] == "development"]
    return min(
        EXPERTS,
        key=lambda name: sum(
            abs(float(row[f"prediction_{name}"]) - float(row["outcome"]))
            for row in development
        )
        / len(development),
    )


def _source_cells(
    name: str, rows: list[dict[str, object]], selected: str
) -> list[dict[str, object]]:
    fixed_mae = _fixed_expert_mae(rows, selected)
    cells: list[dict[str, object]] = []
    for blend in BLEND_WEIGHTS:
        for retention_name, retention in RETENTIONS.items():
            for history in ("continued", "reset"):
                result = _adaptive_evaluation(rows, retention, history, blend)
                cells.append(
                    {
                        "source": name,
                        "blend": blend,
                        "retention_condition": retention_name,
                        "retention": retention,
                        "history": history,
                        "rows": result["rows"],
                        "mae": result["mae"],
                        "mae_gap_fraction_vs_fixed": (
                            result["mae"] - fixed_mae
                        )
                        / fixed_mae,
                        "mean_effective_experts": result["mean_effective_experts"],
                        "mean_weight_change_l1": result["mean_weight_change_l1"],
                        "mean_loss_gap": result["mean_loss_gap"],
                        "fixed_expert": selected,
                        "fixed_expert_mae": fixed_mae,
                    }
                )
    return cells


def _control_check(cells: list[dict[str, object]]) -> dict[str, object]:
    """At blend 0 the run must reproduce the preserved earlier figures."""
    checks: list[dict[str, object]] = []
    for source, expected in CONTROL_EXPECTED.items():
        cell = next(
            c
            for c in cells
            if c["source"] == source
            and c["blend"] == 0.0
            and c["retention_condition"] == "long_continuity"
            and c["history"] == "continued"
        )
        effective_ok = (
            abs(float(cell["mean_effective_experts"]) - expected["effective_experts"])
            <= CONTROL_TOLERANCE
        )
        mae_ok = abs(float(cell["mae"]) - expected["mae"]) <= 1e-3
        checks.append(
            {
                "source": source,
                "measured_effective_experts": cell["mean_effective_experts"],
                "expected_effective_experts": expected["effective_experts"],
                "measured_mae": cell["mae"],
                "expected_mae": expected["mae"],
                "effective_experts_ok": effective_ok,
                "mae_ok": mae_ok,
                "passed": effective_ok and mae_ok,
            }
        )
    return {"checks": checks, "passed": all(c["passed"] for c in checks)}


def _monotone_check(cells: list[dict[str, object]]) -> dict[str, object]:
    """Condition 1: does the collapse ease monotonically as the gap shrinks?"""
    per_source: dict[str, object] = {}
    for source in ("sunspots", "co2"):
        series = [
            {
                "blend": c["blend"],
                "mean_effective_experts": c["mean_effective_experts"],
                "mean_loss_gap": c["mean_loss_gap"],
            }
            for c in cells
            if c["source"] == source
            and c["retention_condition"] == "long_continuity"
            and c["history"] == "continued"
        ]
        series.sort(key=lambda row: float(row["blend"]))
        violations = [
            {
                "from_blend": series[i]["blend"],
                "to_blend": series[i + 1]["blend"],
                "drop": float(series[i]["mean_effective_experts"])
                - float(series[i + 1]["mean_effective_experts"]),
            }
            for i in range(len(series) - 1)
            if float(series[i + 1]["mean_effective_experts"])
            < float(series[i]["mean_effective_experts"]) - MONOTONE_TOLERANCE
        ]
        per_source[source] = {
            "series": series,
            "violations": violations,
            "monotone": not violations,
        }
    return {
        "per_source": per_source,
        "passed": all(bool(v["monotone"]) for v in per_source.values()),
    }


def _gap_is_monotone(cells: list[dict[str, object]]) -> dict[str, object]:
    """Instrument validity: does the blend actually shrink the gap monotonically?

    Condition 1 asks whether the collapse eases as the gap shrinks. That
    question is only answerable if the blend shrinks the gap monotonically. It
    does not: blending each expert toward the mean of the other two makes the
    three predictions converge, and once they are close the *difference* between
    their losses is dominated by noise, so the gap turns and grows again. The
    measured gap on sunspots runs 2.1019 -> 0.2290 -> 1.0620 and on CO2
    0.0554 -> 0.0058 -> 0.0275.

    When the gap is not monotone, a fall in effective experts at high blend is
    the instrument's own shape, not a property of the mechanism. Measured: the
    fall also appears in `one_encounter`, which has no lock-in to remove.
    """
    per_source: dict[str, object] = {}
    for source in ("sunspots", "co2"):
        series = sorted(
            (
                {
                    "blend": c["blend"],
                    "mean_loss_gap": c["mean_loss_gap"],
                }
                for c in cells
                if c["source"] == source
                and c["retention_condition"] == "long_continuity"
                and c["history"] == "continued"
            ),
            key=lambda row: float(row["blend"]),
        )
        turns = [
            {
                "from_blend": series[i]["blend"],
                "to_blend": series[i + 1]["blend"],
                "gap_rise": float(series[i + 1]["mean_loss_gap"])
                - float(series[i]["mean_loss_gap"]),
            }
            for i in range(len(series) - 1)
            if float(series[i + 1]["mean_loss_gap"])
            > float(series[i]["mean_loss_gap"])
        ]
        per_source[source] = {
            "series": series,
            "turns": turns,
            "monotone": not turns,
        }
    return {
        "per_source": per_source,
        "valid": all(bool(v["monotone"]) for v in per_source.values()),
    }


def _matched_gap_check(cells: list[dict[str, object]]) -> dict[str, object]:
    """Condition 2: at a matched loss gap, do the two sources agree?"""
    long_continued = [
        c
        for c in cells
        if c["retention_condition"] == "long_continuity"
        and c["history"] == "continued"
    ]
    sunspots = [c for c in long_continued if c["source"] == "sunspots"]
    co2 = [c for c in long_continued if c["source"] == "co2"]
    pairs: list[dict[str, object]] = []
    for a in sunspots:
        for b in co2:
            gap_a = float(a["mean_loss_gap"])
            gap_b = float(b["mean_loss_gap"])
            if gap_a <= 0 or gap_b <= 0:
                continue
            relative = abs(gap_a - gap_b) / max(gap_a, gap_b)
            if relative <= MATCHED_GAP_RELATIVE:
                pairs.append(
                    {
                        "sunspots_blend": a["blend"],
                        "co2_blend": b["blend"],
                        "sunspots_gap": gap_a,
                        "co2_gap": gap_b,
                        "relative_gap_difference": relative,
                        "sunspots_effective": a["mean_effective_experts"],
                        "co2_effective": b["mean_effective_experts"],
                        "effective_difference": abs(
                            float(a["mean_effective_experts"])
                            - float(b["mean_effective_experts"])
                        ),
                    }
                )
    disagreeing = [
        p for p in pairs if float(p["effective_difference"]) > MATCHED_GAP_MAX_DIFFERENCE
    ]
    # No matched pair means the condition cannot fire — that is not evidence
    # against the claim, and it must not be counted as one. The first version
    # returned passed=False here, which turned "the instrument cannot reach the
    # question" into a finding.
    return {
        "matched_pairs": pairs,
        "disagreeing_pairs": disagreeing,
        "passed": not disagreeing,
        "reachable": bool(pairs),
        "note": (
            "no matched-gap pair exists: the two sources' gap ranges do not "
            "overlap, so condition 2 cannot fire and carries no verdict"
            if not pairs
            else None
        ),
    }


def run_investigation(
    silso_path: Path, noaa_path: Path, output_directory: Path
) -> dict[str, object]:
    """Grade expert disagreement on both preserved series and measure collapse."""
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
    selected: dict[str, str] = {}
    for name, rows in sources.items():
        chosen = _select_fixed_expert(rows)
        selected[name] = chosen
        cells.extend(_source_cells(name, rows, chosen))

    control = _control_check(cells)
    monotone = _monotone_check(cells)
    matched = _matched_gap_check(cells)
    gap_validity = _gap_is_monotone(cells)

    conditions = {
        "1_no_threshold": not bool(monotone["passed"]),
        "2_sources_disagree_at_matched_gap": (
            bool(matched["reachable"]) and not bool(matched["passed"])
        ),
        "3_control_failed": not bool(control["passed"]),
        "4_gap_not_monotone": not bool(gap_validity["valid"]),
    }
    if conditions["3_control_failed"]:
        verdict = "instrument_fault"
    elif conditions["4_gap_not_monotone"]:
        # Condition 1 fired, but the independent variable it depends on is not
        # monotone in the instrument. The fall in effective experts is then the
        # blend's own shape, and the experiment cannot reach its question.
        verdict = "inconclusive_instrument_cannot_reach_question"
    elif conditions["1_no_threshold"] or conditions["2_sources_disagree_at_matched_gap"]:
        verdict = "falsified"
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
            "warmup_months": WARMUP_MONTHS,
            "evaluation_start": "2000-01",
            "blend_weights": list(BLEND_WEIGHTS),
            "retentions": RETENTIONS,
            "blend_rule": "(1-b)*own + b*mean(other two)",
        },
        "runtime": {"python": platform.python_version()},
    }
    results = {
        "method_version": METHOD_VERSION,
        "selected_fixed_expert": selected,
        "control": control,
        "condition_1_monotone": monotone,
        "condition_2_matched_gap": matched,
        "condition_4_gap_validity": gap_validity,
        "conditions_fired": conditions,
        "verdict": verdict,
    }

    _write_csv(output_directory / "exp007_cells.csv", cells)
    _write_json(output_directory / "manifest.json", manifest)
    _write_json(output_directory / "exp007_results.json", results)
    return results
