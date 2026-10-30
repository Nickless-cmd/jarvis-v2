"""Fixed-perspective measurements over deployed visible-run observations."""

from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

from .live_visible_runs import load_verified_observations
from .metrics import entropy, mutual_information

METHOD_VERSION = "exp001.live.1"


@dataclass(frozen=True)
class LiveExperiment001Config:
    permutations: int = 500
    permutation_seed: int = 202610304


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _summary(values: list[float], observed: float) -> dict[str, float | int]:
    exceedances = sum(value >= observed for value in values)
    return {
        "minimum": min(values),
        "q05": _quantile(values, 0.05),
        "median": _quantile(values, 0.5),
        "q95": _quantile(values, 0.95),
        "maximum": max(values),
        "exceedance_count": exceedances,
        "permutations": len(values),
        "plus_one_rank_fraction": (exceedances + 1) / (len(values) + 1),
    }


def _measure(rows: list[dict[str, str]], outcomes: list[str]) -> dict[str, float]:
    providers = [row["provider"] for row in rows]
    provider_models = [(row["provider"], row["model"]) for row in rows]
    return {
        "outcome_ordering": mutual_information(outcomes[:-1], outcomes[1:]),
        "provider_access": mutual_information(providers, outcomes),
        "provider_model_access": mutual_information(provider_models, outcomes),
    }


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def analyze_live_experiment_001(
    run_directory: Path, config: LiveExperiment001Config
) -> dict:
    if config.permutations < 1:
        raise ValueError("permutations must be positive")
    results_path = run_directory / "exp001_live_results.json"
    if results_path.exists():
        raise FileExistsError(results_path)
    manifest, rows = load_verified_observations(run_directory)
    outcomes = [row["status"] for row in rows]
    observed = _measure(rows, outcomes)
    null_values = {name: [] for name in observed}
    null_rows: list[dict[str, int | float | str]] = []
    rng = random.Random(config.permutation_seed)
    for permutation in range(config.permutations):
        shuffled = outcomes.copy()
        rng.shuffle(shuffled)
        measured = _measure(rows, shuffled)
        for perspective, score in measured.items():
            null_values[perspective].append(score)
            null_rows.append(
                {
                    "permutation": permutation,
                    "perspective": perspective,
                    "mutual_information_bits": score,
                }
            )
    counts: dict[str, int] = {}
    for outcome in outcomes:
        counts[outcome] = counts.get(outcome, 0) + 1
    results = {
        "method_version": METHOD_VERSION,
        "live_source": manifest["source"],
        "observations_sha256_colon_hex": manifest["observations"]["sha256_colon_hex"],
        "parameters": {
            "permutations": config.permutations,
            "permutation_seed": config.permutation_seed,
        },
        "descriptive": {
            "rows": len(rows),
            "status_counts": counts,
            "status_entropy_bits": entropy(outcomes),
        },
        "perspectives": {
            name: {
                "observed_mutual_information_bits": score,
                "permuted_outcome_null": _summary(null_values[name], score),
            }
            for name, score in observed.items()
        },
    }
    _write_json(results_path, results)
    with (run_directory / "exp001_live_null.csv").open(
        "x", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["permutation", "perspective", "mutual_information_bits"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(null_rows)
    _write_summary(run_directory / "exp001_live_summary.md", results)
    return results


def _write_summary(path: Path, results: dict) -> None:
    lines = [
        "# Live Investigation 1: measured summary",
        "",
        f"Deployed host: `{results['live_source']['hostname']}`; rows: {results['descriptive']['rows']}; high-water ID: {results['live_source']['high_water_id']}.",
        "",
        "| Perspective | Observed MI | Null q05–q95 | Exceedances |",
        "|---|---:|---:|---:|",
    ]
    for name, measured in results["perspectives"].items():
        null = measured["permuted_outcome_null"]
        lines.append(
            f"| `{name}` | {measured['observed_mutual_information_bits']:.6f} "
            f"| {null['q05']:.6f}–{null['q95']:.6f} "
            f"| {null['exceedance_count']}/{null['permutations']} |"
        )
    lines.extend(
        [
            "",
            "These are observational production measurements. They do not establish causality",
            "or validate Field Theory as a whole.",
        ]
    )
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
