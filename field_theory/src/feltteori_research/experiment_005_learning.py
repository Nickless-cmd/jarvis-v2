"""Independent-source experiment for error, learning, and continuity."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import shutil
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

METHOD_VERSION = "exp005.learning.1"
SOURCE_URL = "https://www.sidc.be/SILSO/INFO/snmtotcsv.php"
SOURCE_PAGE = "https://www.sidc.be/SILSO/datafiles"
SOURCE_INFO = "https://www.sidc.be/SILSO/infosnmtot"
EXPERTS = ("previous_month", "trailing_12_mean", "cycle_lag_132")
RETENTIONS = {
    "one_encounter": 0.0,
    "short_continuity": 0.9,
    "long_continuity": 0.99,
    "cumulative_continuity": 1.0,
}
LEARNING_RATE = 2.0
WARMUP_MONTHS = 132
EVALUATION_START = (2000, 1)


@dataclass(frozen=True)
class SunspotObservation:
    year: int
    month: int
    decimal_date: float
    value: float
    standard_deviation: float
    observation_count: int
    definitive: bool

    @property
    def date(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


def colon_sha256(path: Path) -> str:
    return bytes.fromhex(hashlib.sha256(path.read_bytes()).hexdigest()).hex(":")


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _fetch_source(source: str, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(
            source,
            headers={"User-Agent": "feltteori-research/0.1 (noncommercial research)"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            with destination.open("xb") as output:
                shutil.copyfileobj(response, output)
        return
    with Path(source).open("rb") as input_handle:
        with destination.open("xb") as output:
            shutil.copyfileobj(input_handle, output)


def parse_silso_monthly(path: Path) -> tuple[list[SunspotObservation], dict[str, int]]:
    """Parse definitive, non-missing rows from the official semicolon CSV."""
    observations: list[SunspotObservation] = []
    excluded = {"provisional": 0, "missing": 0}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for line_number, fields in enumerate(
            csv.reader(handle, delimiter=";"), start=1
        ):
            if not fields or all(not field.strip() for field in fields):
                continue
            if len(fields) != 7:
                raise ValueError(f"source line {line_number} has {len(fields)} fields")
            year, month = int(fields[0]), int(fields[1])
            value = float(fields[3])
            definitive = fields[6].strip() == "1"
            if value == -1:
                excluded["missing"] += 1
                continue
            if not definitive:
                excluded["provisional"] += 1
                continue
            observation = SunspotObservation(
                year=year,
                month=month,
                decimal_date=float(fields[2]),
                value=value,
                standard_deviation=float(fields[4]),
                observation_count=int(fields[5]),
                definitive=True,
            )
            if not 1 <= month <= 12:
                raise ValueError(f"invalid month on source line {line_number}")
            if observations and (year, month) <= (
                observations[-1].year,
                observations[-1].month,
            ):
                raise ValueError("source months are duplicated or not increasing")
            observations.append(observation)
    if len(observations) <= WARMUP_MONTHS:
        raise ValueError("source does not contain enough definitive observations")
    if not any((row.year, row.month) >= EVALUATION_START for row in observations):
        raise ValueError("source has no definitive evaluation observations")
    return observations, excluded


def _expert_predictions(
    observations: list[SunspotObservation], index: int
) -> dict[str, float]:
    return {
        "previous_month": observations[index - 1].value,
        "trailing_12_mean": sum(row.value for row in observations[index - 12 : index])
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


def _period(observation: SunspotObservation) -> str:
    return (
        "evaluation"
        if (observation.year, observation.month) >= EVALUATION_START
        else "development"
    )


def _adaptive_trace(
    observations: list[SunspotObservation],
    expert_rows: list[dict[str, object]],
    name: str,
    retention: float,
    history: str,
) -> list[dict[str, object]]:
    retained = {expert: 0.0 for expert in EXPERTS}
    rows: list[dict[str, object]] = []
    previous_weights: dict[str, float] | None = None
    for source_row in expert_rows:
        observation = observations[int(source_row["source_index"])]
        if history == "reset" and observation.date == "2000-01":
            retained = {expert: 0.0 for expert in EXPERTS}
        weights = _weights(retained)
        predictions = {
            expert: float(source_row[f"prediction_{expert}"]) for expert in EXPERTS
        }
        prediction = _weighted_prediction(predictions, weights)
        outcome = observation.value
        expert_losses = {
            expert: float(source_row[f"normalized_loss_{expert}"]) for expert in EXPERTS
        }
        retained_after = {
            expert: retention * retained[expert] + expert_losses[expert]
            for expert in EXPERTS
        }
        weight_change = (
            0.0
            if previous_weights is None
            else sum(abs(weights[e] - previous_weights[e]) for e in EXPERTS)
        )
        rows.append(
            {
                "date": observation.date,
                "period": _period(observation),
                "mechanism": f"adaptive_{name}_{history}",
                "retention": retention,
                "outcome": outcome,
                "prediction": prediction,
                "absolute_error": abs(prediction - outcome),
                "normalized_absolute_error": _normalized_loss(prediction, outcome),
                "weight_change_l1": weight_change,
                "effective_expert_count": 1.0
                / sum(weight * weight for weight in weights.values()),
                **{f"weight_{expert}": weights[expert] for expert in EXPERTS},
                **{
                    f"retained_loss_after_{expert}": retained_after[expert]
                    for expert in EXPERTS
                },
            }
        )
        retained = retained_after
        previous_weights = weights
    return rows


def _fixed_trace(
    observations: list[SunspotObservation],
    expert_rows: list[dict[str, object]],
    selected_expert: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    ledger = {expert: 0.0 for expert in EXPERTS}
    for source_row in expert_rows:
        observation = observations[int(source_row["source_index"])]
        predictions = {
            expert: float(source_row[f"prediction_{expert}"]) for expert in EXPERTS
        }
        losses = {
            expert: float(source_row[f"normalized_loss_{expert}"]) for expert in EXPERTS
        }
        ledger = {expert: ledger[expert] + losses[expert] for expert in EXPERTS}
        for mechanism, weights in (
            ("fixed_uniform", {expert: 1 / 3 for expert in EXPERTS}),
            (
                "fixed_selected_expert",
                {expert: float(expert == selected_expert) for expert in EXPERTS},
            ),
        ):
            prediction = _weighted_prediction(predictions, weights)
            rows.append(
                {
                    "date": observation.date,
                    "period": _period(observation),
                    "mechanism": mechanism,
                    "retention": "not_applicable",
                    "outcome": observation.value,
                    "prediction": prediction,
                    "absolute_error": abs(prediction - observation.value),
                    "normalized_absolute_error": _normalized_loss(
                        prediction, observation.value
                    ),
                    "weight_change_l1": 0.0,
                    "effective_expert_count": (
                        3.0 if mechanism == "fixed_uniform" else 1.0
                    ),
                    **{f"weight_{expert}": weights[expert] for expert in EXPERTS},
                    **{
                        f"retained_loss_after_{expert}": ledger[expert]
                        for expert in EXPERTS
                    },
                }
            )
    return rows


def _summaries(trace: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in trace:
        grouped[(str(row["mechanism"]), str(row["period"]))].append(row)
    summaries: list[dict[str, object]] = []
    for (mechanism, period), rows in sorted(grouped.items()):
        count = len(rows)
        summaries.append(
            {
                "mechanism": mechanism,
                "period": period,
                "rows": count,
                "mean_absolute_error": sum(float(r["absolute_error"]) for r in rows)
                / count,
                "root_mean_squared_error": math.sqrt(
                    sum(float(r["absolute_error"]) ** 2 for r in rows) / count
                ),
                "mean_normalized_absolute_error": sum(
                    float(r["normalized_absolute_error"]) for r in rows
                )
                / count,
                "mean_weight_change_l1": sum(float(r["weight_change_l1"]) for r in rows)
                / count,
                "mean_effective_expert_count": sum(
                    float(r["effective_expert_count"]) for r in rows
                )
                / count,
            }
        )
    return summaries


def _history_comparisons(trace: list[dict[str, object]]) -> list[dict[str, object]]:
    by_mechanism = {
        mechanism: {
            str(row["date"]): float(row["prediction"])
            for row in trace
            if row["mechanism"] == mechanism and row["period"] == "evaluation"
        }
        for mechanism in {str(row["mechanism"]) for row in trace}
    }
    output: list[dict[str, object]] = []
    for name in RETENTIONS:
        continued = by_mechanism[f"adaptive_{name}_continued"]
        reset = by_mechanism[f"adaptive_{name}_reset"]
        dates = sorted(continued)
        differences = [abs(continued[date] - reset[date]) for date in dates]
        output.append(
            {
                "retention_condition": name,
                "evaluation_rows": len(dates),
                "different_prediction_rows": sum(
                    value > 1e-12 for value in differences
                ),
                "mean_absolute_prediction_difference": sum(differences)
                / len(differences),
                "last_different_date": max(
                    (
                        date
                        for date, value in zip(dates, differences, strict=True)
                        if value > 1e-12
                    ),
                    default=None,
                ),
            }
        )
    return output


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _polyline(
    values: list[float],
    left: float,
    top: float,
    width: float,
    height: float,
    minimum: float,
    maximum: float,
) -> str:
    span = maximum - minimum or 1.0
    count = max(1, len(values) - 1)
    return " ".join(
        f"{left + width * index / count:.2f},{top + height * (maximum - value) / span:.2f}"
        for index, value in enumerate(values)
    )


def _write_svg(path: Path, trace: list[dict[str, object]]) -> None:
    evaluation = [row for row in trace if row["period"] == "evaluation"]
    mechanisms = {
        name: [row for row in evaluation if row["mechanism"] == name]
        for name in (
            "fixed_uniform",
            "fixed_selected_expert",
            "adaptive_short_continuity_continued",
            "adaptive_cumulative_continuity_continued",
        )
    }
    observed = [float(row["outcome"]) for row in mechanisms["fixed_uniform"]]
    maximum = max(
        observed
        + [float(r["prediction"]) for rows in mechanisms.values() for r in rows]
    )
    colors = {
        "observed": "#111827",
        "fixed_uniform": "#9ca3af",
        "fixed_selected_expert": "#2563eb",
        "adaptive_short_continuity_continued": "#d97706",
        "adaptive_cumulative_continuity_continued": "#7c3aed",
    }
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720">',
        '<rect width="1200" height="720" fill="#ffffff"/>',
        '<text x="70" y="35" font-family="sans-serif" font-size="20">Investigation 5: evaluation observations and constructed expectations</text>',
        '<text x="70" y="60" font-family="sans-serif" font-size="12" fill="#4b5563">WDC-SILSO definitive monthly means; evaluation begins 2000-01</text>',
    ]
    for y in range(5):
        py = 90 + y * 100
        value = maximum * (4 - y) / 4
        lines.append(f'<line x1="70" y1="{py}" x2="1160" y2="{py}" stroke="#e5e7eb"/>')
        lines.append(
            f'<text x="15" y="{py + 4}" font-family="sans-serif" font-size="11">{value:.0f}</text>'
        )
    lines.append(
        f'<polyline fill="none" stroke="{colors["observed"]}" stroke-width="1.6" points="{_polyline(observed, 70, 90, 1090, 400, 0, maximum)}"/>'
    )
    for mechanism, rows in mechanisms.items():
        values = [float(row["prediction"]) for row in rows]
        lines.append(
            f'<polyline fill="none" stroke="{colors[mechanism]}" stroke-width="1.1" opacity="0.85" points="{_polyline(values, 70, 90, 1090, 400, 0, maximum)}"/>'
        )
    short = mechanisms["adaptive_short_continuity_continued"]
    for index, expert in enumerate(EXPERTS):
        weights = [float(row[f"weight_{expert}"]) for row in short]
        lines.append(
            f'<polyline fill="none" stroke="{("#059669", "#dc2626", "#0284c7")[index]}" stroke-width="1.2" points="{_polyline(weights, 70, 550, 1090, 100, 0, 1)}"/>'
        )
    lines.extend(
        [
            '<text x="70" y="535" font-family="sans-serif" font-size="13">Short-continuity expert weights (0 to 1)</text>',
            '<text x="70" y="685" font-family="sans-serif" font-size="11" fill="#374151">Black observed; blue selected fixed expert; gray uniform; orange short continuity; purple cumulative. Weights: green previous, red trailing-12, cyan lag-132.</text>',
            "</svg>",
        ]
    )
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def run_investigation(source: str, output_directory: Path) -> dict[str, object]:
    """Fetch, preserve, and analyze one independent source snapshot."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)
    source_path = output_directory / "silso_monthly_total_v2.csv"
    _fetch_source(source, source_path)
    observations, excluded = parse_silso_monthly(source_path)
    expert_rows: list[dict[str, object]] = []
    for index in range(WARMUP_MONTHS, len(observations)):
        observation = observations[index]
        predictions = _expert_predictions(observations, index)
        expert_rows.append(
            {
                "source_index": index,
                "date": observation.date,
                "period": _period(observation),
                "outcome": observation.value,
                **{f"prediction_{name}": predictions[name] for name in EXPERTS},
                **{
                    f"absolute_error_{name}": abs(predictions[name] - observation.value)
                    for name in EXPERTS
                },
                **{
                    f"normalized_loss_{name}": _normalized_loss(
                        predictions[name], observation.value
                    )
                    for name in EXPERTS
                },
            }
        )
    development = [row for row in expert_rows if row["period"] == "development"]
    selected_expert = min(
        EXPERTS,
        key=lambda name: (
            sum(float(row[f"absolute_error_{name}"]) for row in development)
            / len(development)
        ),
    )
    trace = _fixed_trace(observations, expert_rows, selected_expert)
    for name, retention in RETENTIONS.items():
        for history in ("continued", "reset"):
            trace.extend(
                _adaptive_trace(observations, expert_rows, name, retention, history)
            )
    trace.sort(key=lambda row: (str(row["date"]), str(row["mechanism"])))
    summaries = _summaries(trace)
    history = _history_comparisons(trace)
    expert_summary = []
    for expert in EXPERTS:
        for period in ("development", "evaluation"):
            rows = [row for row in expert_rows if row["period"] == period]
            expert_summary.append(
                {
                    "expert": expert,
                    "period": period,
                    "rows": len(rows),
                    "mean_absolute_error": sum(
                        float(row[f"absolute_error_{expert}"]) for row in rows
                    )
                    / len(rows),
                    "mean_normalized_absolute_error": sum(
                        float(row[f"normalized_loss_{expert}"]) for row in rows
                    )
                    / len(rows),
                }
            )
    manifest = {
        "method_version": METHOD_VERSION,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "requested_location": source,
            "canonical_url": SOURCE_URL,
            "information_page": SOURCE_INFO,
            "publisher_page": SOURCE_PAGE,
            "publisher": "WDC-SILSO, Royal Observatory of Belgium, Brussels",
            "doi": "10.24414/qnza-ac80",
            "license": "CC BY-NC 4.0",
            "sha256_colon_hex": colon_sha256(source_path),
        },
        "observations": {
            "definitive_non_missing_rows": len(observations),
            "first_month": observations[0].date,
            "last_month": observations[-1].date,
            "excluded": excluded,
        },
        "parameters": {
            "experts": list(EXPERTS),
            "warmup_months": WARMUP_MONTHS,
            "evaluation_start": "2000-01",
            "learning_rate": LEARNING_RATE,
            "retentions": RETENTIONS,
            "loss": "absolute_error / (1 + absolute_outcome)",
        },
        "runtime": {"python": platform.python_version()},
    }
    results = {
        "method_version": METHOD_VERSION,
        "source_sha256_colon_hex": manifest["source"]["sha256_colon_hex"],
        "selected_fixed_expert_from_development_mae": selected_expert,
        "expert_summaries": expert_summary,
        "mechanism_summaries": summaries,
        "continued_vs_reset": history,
        "constructed": {
            "adaptive_rules": "declared exponential expert weighting",
            "fixed_uniform_error_ledger": "retained consequence without changed weights",
        },
    }
    _write_csv(output_directory / "exp005_expert_trace.csv", expert_rows)
    _write_csv(output_directory / "exp005_mechanism_trace.csv", trace)
    _write_json(output_directory / "manifest.json", manifest)
    _write_json(output_directory / "exp005_results.json", results)
    _write_svg(output_directory / "exp005_learning_continuity.svg", trace)
    return results
