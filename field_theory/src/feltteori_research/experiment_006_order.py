"""Transfer test: does the retention→adaptation relation survive a new source?

Investigation 5 measured, on monthly sunspot number, that greater retention of
accumulated loss did not increase continuing adaptation. This module applies
the *same* mechanism, expert set, learning rate and evaluation rule to a
physically unrelated series (NOAA Mauna Loa CO2) and asks whether the relation
transfers.

The protocol is frozen in ``experiments/exp_006_order/PROTOCOL.md`` and was
committed before the source was parsed. Nothing here is tuned to the new
source: the constants are imported from ``experiment_005_learning`` so the two
runs cannot silently diverge.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from feltteori_research.experiment_005_learning import (
    EVALUATION_START,
    EXPERTS,
    LEARNING_RATE,
    RETENTIONS,
    WARMUP_MONTHS,
    colon_sha256,
)

METHOD_VERSION = "exp006.order.1"
SOURCE_URL = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv"
SOURCE_INFO = "https://gml.noaa.gov/ccgg/trends/data.html"

# Falsification thresholds, copied verbatim from the frozen protocol.
FALSIFY_MIN_EFFECTIVE_EXPERTS = 1.5
FALSIFY_MIN_WEIGHT_CHANGE = 0.05
FALSIFY_MAX_MAE_GAP_FRACTION = 0.005


@dataclass(frozen=True)
class MonthlyObservation:
    year: int
    month: int
    decimal_date: float
    value: float

    @property
    def date(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("no rows")
    # Field names are the union across rows: fixed traces carry no weight
    # columns, adaptive traces do. Taking the first row's keys silently drops
    # the rest (measured 2026-10-30: ValueError on weight_previous_month).
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fetch_source(destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    request = urllib.request.Request(
        SOURCE_URL, headers={"User-Agent": "jarvis-field-theory/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())


def parse_noaa_monthly(path: Path) -> tuple[list[MonthlyObservation], dict[str, int]]:
    """Parse NOAA's commented CSV. ``-1`` in the average column marks missing."""
    observations: list[MonthlyObservation] = []
    excluded = {"missing": 0, "malformed": 0}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            parts = [p.strip() for p in line.strip().split(",")]
            if not parts or parts[0] == "year":
                continue
            if len(parts) < 4:
                excluded["malformed"] += 1
                continue
            try:
                year = int(parts[0])
                month = int(parts[1])
                decimal_date = float(parts[2])
                value = float(parts[3])
            except ValueError:
                excluded["malformed"] += 1
                continue
            if value < 0:
                excluded["missing"] += 1
                continue
            observations.append(
                MonthlyObservation(
                    year=year,
                    month=month,
                    decimal_date=decimal_date,
                    value=value,
                )
            )
    observations.sort(key=lambda row: (row.year, row.month))
    return observations, excluded


def _expert_predictions(
    observations: list[MonthlyObservation], index: int
) -> dict[str, float]:
    return {
        "previous_month": observations[index - 1].value,
        "trailing_12_mean": sum(
            row.value for row in observations[index - 12 : index]
        )
        / 12,
        "cycle_lag_132": observations[index - 132].value,
    }


def _normalized_loss(prediction: float, outcome: float) -> float:
    return abs(prediction - outcome) / (1.0 + abs(outcome))


def _weights(retained_losses: dict[str, float]) -> dict[str, float]:
    minimum = min(retained_losses.values())
    unscaled = {
        expert: math.exp(-LEARNING_RATE * (loss - minimum))
        for expert, loss in retained_losses.items()
    }
    total = sum(unscaled.values())
    return {expert: unscaled[expert] / total for expert in EXPERTS}


def _weighted_prediction(
    predictions: dict[str, float], weights: dict[str, float]
) -> float:
    return sum(predictions[expert] * weights[expert] for expert in EXPERTS)


def _period(observation: MonthlyObservation) -> str:
    return (
        "evaluation"
        if (observation.year, observation.month) >= EVALUATION_START
        else "development"
    )


def _adaptive_trace(
    observations: list[MonthlyObservation],
    retention: float,
    *,
    reset_at_evaluation: bool,
) -> list[dict[str, object]]:
    retained = {expert: 0.0 for expert in EXPERTS}
    trace: list[dict[str, object]] = []
    # The reset must fire exactly once, at the FIRST evaluation observation.
    # Measured 2026-10-30 (method deviation, see research/notebook.md): the
    # first version tested `not trace`, but `trace` is already filled by the
    # development period when the boundary is reached — so the condition was
    # never true and reset never ran. `continued` and `reset` then traced the
    # identical computation, which was reported as an empirical finding about
    # continuity. It was an instrument fault. A pending flag cannot be
    # satisfied by a non-empty history.
    reset_pending = reset_at_evaluation
    for index in range(WARMUP_MONTHS, len(observations)):
        observation = observations[index]
        period = _period(observation)
        if reset_pending and period == "evaluation":
            retained = {expert: 0.0 for expert in EXPERTS}
            reset_pending = False
        predictions = _expert_predictions(observations, index)
        weights = _weights(retained)
        prediction = _weighted_prediction(predictions, weights)
        losses = {
            expert: _normalized_loss(predictions[expert], observation.value)
            for expert in EXPERTS
        }
        trace.append(
            {
                "date": observation.date,
                "period": period,
                "outcome": observation.value,
                "prediction": prediction,
                "absolute_error": abs(prediction - observation.value),
                "normalized_error": _normalized_loss(prediction, observation.value),
                "effective_experts": 1.0
                / sum(weight * weight for weight in weights.values()),
                "weight_change": 0.0,
                **{f"weight_{expert}": weights[expert] for expert in EXPERTS},
            }
        )
        previous = weights
        for expert in EXPERTS:
            retained[expert] = retention * retained[expert] + losses[expert]
        updated = _weights(retained)
        trace[-1]["weight_change"] = sum(
            abs(updated[expert] - previous[expert]) for expert in EXPERTS
        ) / 2.0
    return trace


def _fixed_trace(
    observations: list[MonthlyObservation], expert: str
) -> list[dict[str, object]]:
    trace: list[dict[str, object]] = []
    for index in range(WARMUP_MONTHS, len(observations)):
        observation = observations[index]
        predictions = _expert_predictions(observations, index)
        prediction = predictions[expert]
        trace.append(
            {
                "date": observation.date,
                "period": _period(observation),
                "outcome": observation.value,
                "prediction": prediction,
                "absolute_error": abs(prediction - observation.value),
                "normalized_error": _normalized_loss(prediction, observation.value),
                "effective_experts": 1.0,
                "weight_change": 0.0,
            }
        )
    return trace


def _summaries(trace: list[dict[str, object]], name: str) -> dict[str, object]:
    evaluation = [row for row in trace if row["period"] == "evaluation"]
    if not evaluation:
        raise ValueError(f"{name}: no evaluation rows")
    count = len(evaluation)
    return {
        "mechanism": name,
        "evaluation_months": count,
        "mae": sum(float(row["absolute_error"]) for row in evaluation) / count,
        "rmse": math.sqrt(
            sum(float(row["absolute_error"]) ** 2 for row in evaluation) / count
        ),
        "normalized_absolute_error": sum(
            float(row["normalized_error"]) for row in evaluation
        )
        / count,
        "mean_effective_experts": sum(
            float(row["effective_experts"]) for row in evaluation
        )
        / count,
        "mean_weight_change": sum(
            float(row["weight_change"]) for row in evaluation
        )
        / count,
    }


def _judge(summaries: list[dict[str, object]], fixed_mae: float) -> dict[str, object]:
    """Apply the three falsification conditions frozen in the protocol."""
    by_name = {str(row["mechanism"]): row for row in summaries}
    verdicts: dict[str, object] = {}
    for name in ("long_continuity_continued", "cumulative_continuity_continued"):
        row = by_name[name]
        effective = float(row["mean_effective_experts"])
        change = float(row["mean_weight_change"])
        mae = float(row["mae"])
        gap = abs(mae - fixed_mae) / fixed_mae
        conditions = {
            "effective_experts_above_threshold": effective
            > FALSIFY_MIN_EFFECTIVE_EXPERTS,
            "weight_change_above_threshold": change > FALSIFY_MIN_WEIGHT_CHANGE,
            "mae_gap_above_threshold": gap > FALSIFY_MAX_MAE_GAP_FRACTION,
        }
        verdicts[name] = {
            "mean_effective_experts": effective,
            "mean_weight_change": change,
            "mae": mae,
            "mae_gap_fraction_vs_fixed": gap,
            "conditions": conditions,
            "falsifies_transfer": any(conditions.values()),
        }
    return verdicts


def run_investigation(source: str, output_directory: Path) -> dict[str, object]:
    output_directory.mkdir(parents=True, exist_ok=False)
    source_path = output_directory / "noaa_co2_mm_mlo.csv"
    if source == "fetch":
        fetch_source(source_path)
    else:
        source_path.write_bytes(Path(source).read_bytes())

    observations, excluded = parse_noaa_monthly(source_path)
    if len(observations) < WARMUP_MONTHS + 24:
        raise ValueError(f"too few observations: {len(observations)}")

    development = [
        row
        for row in observations[WARMUP_MONTHS:]
        if _period(row) == "development"
    ]
    if not development:
        raise ValueError("no development rows")

    expert_development_mae: dict[str, float] = {}
    for expert in EXPERTS:
        errors = []
        for index in range(WARMUP_MONTHS, len(observations)):
            observation = observations[index]
            if _period(observation) != "development":
                continue
            predictions = _expert_predictions(observations, index)
            errors.append(abs(predictions[expert] - observation.value))
        expert_development_mae[expert] = sum(errors) / len(errors)
    selected = min(expert_development_mae, key=expert_development_mae.get)

    traces: dict[str, list[dict[str, object]]] = {}
    traces[f"fixed_{selected}"] = _fixed_trace(observations, selected)
    for label, retention in RETENTIONS.items():
        traces[f"{label}_continued"] = _adaptive_trace(
            observations, retention, reset_at_evaluation=False
        )
        traces[f"{label}_reset"] = _adaptive_trace(
            observations, retention, reset_at_evaluation=True
        )

    summaries = [_summaries(trace, name) for name, trace in traces.items()]
    fixed_mae = float(
        next(row["mae"] for row in summaries if row["mechanism"] == f"fixed_{selected}")
    )
    verdicts = _judge(summaries, fixed_mae)

    _write_csv(
        output_directory / "exp006_mechanism_summaries.csv",
        [{k: v for k, v in row.items()} for row in summaries],
    )
    _write_csv(
        output_directory / "exp006_trace.csv",
        [
            {"mechanism": name, **row}
            for name, trace in traces.items()
            for row in trace
        ],
    )

    results = {
        "method_version": METHOD_VERSION,
        "source_url": SOURCE_URL,
        "source_info": SOURCE_INFO,
        "source_sha256_colon_hex": colon_sha256(source_path),
        "observations": {
            "total": len(observations),
            "first": observations[0].date,
            "last": observations[-1].date,
            "excluded": excluded,
            "warmup_months": WARMUP_MONTHS,
        },
        "constants_inherited_from": "exp005.learning.1",
        "experts": list(EXPERTS),
        "retentions": RETENTIONS,
        "learning_rate": LEARNING_RATE,
        "evaluation_start": f"{EVALUATION_START[0]:04d}-{EVALUATION_START[1]:02d}",
        "expert_development_mae": expert_development_mae,
        "selected_fixed_expert_from_development_mae": selected,
        "mechanism_summaries": summaries,
        "falsification": {
            "thresholds": {
                "min_effective_experts": FALSIFY_MIN_EFFECTIVE_EXPERTS,
                "min_weight_change": FALSIFY_MIN_WEIGHT_CHANGE,
                "max_mae_gap_fraction": FALSIFY_MAX_MAE_GAP_FRACTION,
            },
            "verdicts": verdicts,
            "transfer_falsified": any(
                bool(v["falsifies_transfer"]) for v in verdicts.values()
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    }
    _write_json(output_directory / "exp006_results.json", results)
    return results
