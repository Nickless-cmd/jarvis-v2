"""Declared post-hoc audit for Investigation 5's lock-in and metric conflict."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from .experiment_005_learning import EXPERTS

AUDIT_METHOD_VERSION = "exp005.posthoc.lock_in.1"
AUDITED_MECHANISMS = (
    "fixed_selected_expert",
    "adaptive_short_continuity_continued",
    "adaptive_long_continuity_continued",
    "adaptive_long_continuity_reset",
    "adaptive_cumulative_continuity_continued",
    "adaptive_cumulative_continuity_reset",
)


def _colon_sha256(path: Path) -> str:
    return bytes.fromhex(hashlib.sha256(path.read_bytes()).hexdigest()).hex(":")


def _quantile(sorted_values: list[float], fraction: float) -> float:
    position = fraction * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _bin_name(value: float, boundaries: tuple[float, float, float]) -> str:
    if value <= boundaries[0]:
        return "q1_lowest_observed_values"
    if value <= boundaries[1]:
        return "q2"
    if value <= boundaries[2]:
        return "q3"
    return "q4_highest_observed_values"


def audit_investigation(run_directory: Path) -> dict[str, object]:
    """Explain inspected lock-in and loss disagreement without changing results."""
    output_path = run_directory / "exp005_posthoc_audit.json"
    csv_path = run_directory / "exp005_posthoc_value_ranges.csv"
    if output_path.exists() or csv_path.exists():
        raise FileExistsError(output_path if output_path.exists() else csv_path)
    trace_path = run_directory / "exp005_mechanism_trace.csv"
    source_path = run_directory / "silso_monthly_total_v2.csv"
    manifest = json.loads((run_directory / "manifest.json").read_text(encoding="utf-8"))
    if _colon_sha256(source_path) != manifest["source"]["sha256_colon_hex"]:
        raise ValueError("source digest no longer matches manifest")
    with trace_path.open(newline="", encoding="utf-8") as handle:
        trace = [row for row in csv.DictReader(handle) if row["period"] == "evaluation"]
    fixed = [row for row in trace if row["mechanism"] == "fixed_selected_expert"]
    values = sorted(float(row["outcome"]) for row in fixed)
    boundaries = (
        _quantile(values, 0.25),
        _quantile(values, 0.50),
        _quantile(values, 0.75),
    )
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in trace:
        if row["mechanism"] in AUDITED_MECHANISMS:
            grouped[
                (row["mechanism"], _bin_name(float(row["outcome"]), boundaries))
            ].append(row)
    range_rows: list[dict[str, object]] = []
    for (mechanism, value_range), rows in sorted(grouped.items()):
        range_rows.append(
            {
                "mechanism": mechanism,
                "posthoc_value_range": value_range,
                "rows": len(rows),
                "minimum_outcome": min(float(row["outcome"]) for row in rows),
                "maximum_outcome": max(float(row["outcome"]) for row in rows),
                "mean_absolute_error": sum(float(row["absolute_error"]) for row in rows)
                / len(rows),
                "mean_normalized_absolute_error": sum(
                    float(row["normalized_absolute_error"]) for row in rows
                )
                / len(rows),
            }
        )
    with csv_path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(range_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(range_rows)

    lock_in = []
    for mechanism in AUDITED_MECHANISMS:
        if not mechanism.startswith("adaptive_"):
            continue
        rows = [row for row in trace if row["mechanism"] == mechanism]
        dominant = Counter(
            max(EXPERTS, key=lambda expert: float(row[f"weight_{expert}"]))
            for row in rows
        )
        lock_in.append(
            {
                "mechanism": mechanism,
                "rows": len(rows),
                "dominant_expert_counts": dict(sorted(dominant.items())),
                "near_one_hot_rows": sum(
                    max(float(row[f"weight_{expert}"]) for expert in EXPERTS)
                    >= 0.999999
                    for row in rows
                ),
                "first_weights": {
                    expert: float(rows[0][f"weight_{expert}"]) for expert in EXPERTS
                },
                "final_weights": {
                    expert: float(rows[-1][f"weight_{expert}"]) for expert in EXPERTS
                },
                "mean_weights": {
                    expert: sum(float(row[f"weight_{expert}"]) for row in rows)
                    / len(rows)
                    for expert in EXPERTS
                },
            }
        )

    by_mechanism_date = {
        mechanism: {row["date"]: row for row in trace if row["mechanism"] == mechanism}
        for mechanism in AUDITED_MECHANISMS
    }
    fixed_by_date = by_mechanism_date["fixed_selected_expert"]
    short_by_date = by_mechanism_date["adaptive_short_continuity_continued"]
    differences = []
    for date in sorted(fixed_by_date):
        fixed_row = fixed_by_date[date]
        short_row = short_by_date[date]
        differences.append(
            {
                "date": date,
                "outcome": float(fixed_row["outcome"]),
                "short_minus_fixed_absolute_error": float(short_row["absolute_error"])
                - float(fixed_row["absolute_error"]),
                "short_minus_fixed_normalized_error": float(
                    short_row["normalized_absolute_error"]
                )
                - float(fixed_row["normalized_absolute_error"]),
            }
        )
    result = {
        "method_version": AUDIT_METHOD_VERSION,
        "evidence_status": "post-hoc after primary result inspection",
        "prompt": "Locate the observed lock-in and disagreement between absolute and normalized error without changing the primary method.",
        "source_sha256_colon_hex": manifest["source"]["sha256_colon_hex"],
        "primary_trace_sha256_colon_hex": _colon_sha256(trace_path),
        "posthoc_outcome_quartile_boundaries": list(boundaries),
        "lock_in": lock_in,
        "short_continuity_extreme_differences": {
            "largest_absolute_error_improvements": sorted(
                differences, key=lambda row: row["short_minus_fixed_absolute_error"]
            )[:10],
            "largest_absolute_error_harms": sorted(
                differences,
                key=lambda row: row["short_minus_fixed_absolute_error"],
                reverse=True,
            )[:10],
        },
        "limits": [
            "Value ranges and extreme months were selected after primary inspection.",
            "The audit explains arithmetic behavior of constructed mechanisms, not solar causality.",
            "It does not replace or retune the preserved primary summaries.",
        ],
    }
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result
