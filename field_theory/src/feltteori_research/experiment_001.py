"""Reproducible first exploration of perspective-dependent observability."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .metrics import entropy, perspective_metrics

METHOD_VERSION = "exp001.1"
PERSPECTIVES = ("outcome_only", "cue_access", "cue_context_access")


@dataclass(frozen=True)
class RunConfig:
    rows_per_source: int = 2048
    seed: int = 20261030
    context_block_size: int = 32
    relation_noise: float = 0.10
    permutations: int = 500

    def validate(self) -> None:
        if self.rows_per_source < 2:
            raise ValueError("rows_per_source must be at least 2")
        if self.context_block_size < 1:
            raise ValueError("context_block_size must be positive")
        if not 0.0 <= self.relation_noise <= 1.0:
            raise ValueError("relation_noise must be between 0 and 1")
        if self.permutations < 1:
            raise ValueError("permutations must be positive")


def _generate_rows(config: RunConfig) -> list[dict[str, int | str]]:
    generator = random.Random(config.seed)
    rows: list[dict[str, int | str]] = []
    for source in ("iid_control", "context_relation"):
        for index in range(config.rows_per_source):
            cue = generator.randrange(2)
            context = (index // config.context_block_size) % 2
            if source == "iid_control":
                outcome = generator.randrange(2)
            else:
                outcome = cue ^ context
                if generator.random() < config.relation_noise:
                    outcome ^= 1
            rows.append(
                {
                    "observation_id": f"{source}:{index:06d}",
                    "source": source,
                    "index": index,
                    "cue": cue,
                    "context": context,
                    "outcome": outcome,
                }
            )
    return rows


def _write_observations(path: Path, rows: list[dict[str, int | str]]) -> None:
    fieldnames = ["observation_id", "source", "index", "cue", "context", "outcome"]
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    # Colon-separated hex remains lossless while being visibly a checksum,
    # rather than an opaque token that generic secret scanners misclassify.
    return digest.digest().hex(":")


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _summarize_null(values: list[float], observed: float) -> dict[str, float]:
    return {
        "minimum": min(values),
        "q05": _quantile(values, 0.05),
        "median": _quantile(values, 0.5),
        "q95": _quantile(values, 0.95),
        "maximum": max(values),
        "fraction_at_least_observed": sum(value >= observed for value in values)
        / len(values),
    }


def _analyze(
    rows: list[dict[str, int | str]], config: RunConfig
) -> tuple[dict[str, Any], list[dict[str, int | float | str]]]:
    results: dict[str, Any] = {"method_version": METHOD_VERSION, "sources": {}}
    permutation_rows: list[dict[str, int | float | str]] = []
    for source_index, source in enumerate(("iid_control", "context_relation")):
        source_rows = [row for row in rows if row["source"] == source]
        outcomes = [int(row["outcome"]) for row in source_rows]
        observed = perspective_metrics(source_rows)
        null_values = {name: [] for name in PERSPECTIVES}
        permutation_rng = random.Random(config.seed + 1009 * (source_index + 1))
        for permutation in range(config.permutations):
            shuffled = outcomes.copy()
            permutation_rng.shuffle(shuffled)
            permuted_rows = [
                dict(row, outcome=shuffled[i]) for i, row in enumerate(source_rows)
            ]
            measured = perspective_metrics(permuted_rows)
            for perspective, value in measured.items():
                null_values[perspective].append(value)
                permutation_rows.append(
                    {
                        "source": source,
                        "permutation": permutation,
                        "perspective": perspective,
                        "mutual_information_bits": value,
                    }
                )
        results["sources"][source] = {
            "descriptive": {
                "rows": len(source_rows),
                "outcome_one_fraction": sum(outcomes) / len(outcomes),
                "outcome_entropy_bits": entropy(outcomes),
            },
            "perspectives": {
                name: {
                    "observed_mutual_information_bits": observed[name],
                    "permuted_outcome_null": _summarize_null(
                        null_values[name], observed[name]
                    ),
                }
                for name in PERSPECTIVES
            },
        }
    return results, permutation_rows


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_permutations(path: Path, rows: list[dict[str, int | float | str]]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source",
                "permutation",
                "perspective",
                "mutual_information_bits",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Experiment 001 measured summary",
        "",
        "These are measurements, not an interpretation of Feltteori. Mutual",
        "information and null summaries are defined in the protocol.",
        "",
    ]
    for source, source_result in results["sources"].items():
        descriptive = source_result["descriptive"]
        lines.extend(
            [
                f"## {source}",
                "",
                f"- Rows: {descriptive['rows']}",
                f"- Outcome-one fraction: {descriptive['outcome_one_fraction']:.6f}",
                f"- Outcome entropy: {descriptive['outcome_entropy_bits']:.6f} bits",
                "",
                "| Accessible relation | Observed MI (bits) | Null median | Null 5–95% | Null fraction ≥ observed |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for perspective in PERSPECTIVES:
            measured = source_result["perspectives"][perspective]
            null = measured["permuted_outcome_null"]
            lines.append(
                f"| {perspective} | {measured['observed_mutual_information_bits']:.6f} "
                f"| {null['median']:.6f} | {null['q05']:.6f}–{null['q95']:.6f} "
                f"| {null['fraction_at_least_observed']:.6f} |"
            )
        lines.append("")
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _write_svg(path: Path, results: dict[str, Any]) -> None:
    width, height = 900, 430
    left, plot_width = 250, 580
    max_value = max(
        measured["observed_mutual_information_bits"]
        for source in results["sources"].values()
        for measured in source["perspectives"].values()
    )
    scale_max = max(0.01, max_value * 1.12)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf6"/>',
        "<style>text{font-family:system-ui,sans-serif;fill:#20242b}.title{font-size:20px;font-weight:700}.small{font-size:12px}.label{font-size:13px}.source{font-size:15px;font-weight:700}</style>",
        '<text x="30" y="32" class="title">Perspective comparison — observed MI and permuted null</text>',
        '<text x="30" y="52" class="small">Bars: observed mutual information. Lines: 5–95% of outcome-permutation null; dots: null median.</text>',
    ]
    row_y = 92
    colors = {"iid_control": "#3b82f6", "context_relation": "#d97706"}
    for source_name, source in results["sources"].items():
        svg.append(f'<text x="30" y="{row_y}" class="source">{source_name}</text>')
        row_y += 24
        for perspective in PERSPECTIVES:
            measured = source["perspectives"][perspective]
            observed = measured["observed_mutual_information_bits"]
            null = measured["permuted_outcome_null"]
            x_observed = left + plot_width * observed / scale_max
            x_q05 = left + plot_width * null["q05"] / scale_max
            x_q95 = left + plot_width * null["q95"] / scale_max
            x_median = left + plot_width * null["median"] / scale_max
            svg.extend(
                [
                    f'<text x="45" y="{row_y + 4}" class="label">{perspective}</text>',
                    f'<line x1="{left}" y1="{row_y}" x2="{left + plot_width}" y2="{row_y}" stroke="#e1ded5"/>',
                    f'<rect x="{left}" y="{row_y - 6}" width="{max(1, x_observed - left):.2f}" height="12" fill="{colors[source_name]}" opacity="0.72"/>',
                    f'<line x1="{x_q05:.2f}" y1="{row_y}" x2="{x_q95:.2f}" y2="{row_y}" stroke="#111827" stroke-width="2"/>',
                    f'<circle cx="{x_median:.2f}" cy="{row_y}" r="3" fill="#111827"/>',
                    f'<text x="{left + plot_width + 10}" y="{row_y + 4}" class="small">{observed:.4f}</text>',
                ]
            )
            row_y += 30
        row_y += 22
    for tick in range(6):
        value = scale_max * tick / 5
        x = left + plot_width * tick / 5
        svg.extend(
            [
                f'<line x1="{x:.2f}" y1="68" x2="{x:.2f}" y2="{height - 36}" stroke="#c9c5bb" stroke-dasharray="2 4"/>',
                f'<text x="{x:.2f}" y="{height - 16}" class="small" text-anchor="middle">{value:.2f}</text>',
            ]
        )
    svg.append("</svg>")
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(svg) + "\n")


def run_experiment(output: Path, config: RunConfig) -> dict[str, Any]:
    """Create one immutable run directory and return its derived results."""
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    observations_path = output / "observations.csv"
    rows = _generate_rows(config)
    _write_observations(observations_path, rows)
    raw_digest = _sha256(observations_path)
    manifest = {
        "experiment": "exp_001_perspective",
        "method_version": METHOD_VERSION,
        "parameters": asdict(config),
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "prng": "random.Random (Mersenne Twister)",
        },
        "raw_observations": {
            "path": "observations.csv",
            "sha256_colon_hex": raw_digest,
            "rows": len(rows),
        },
    }
    _write_json(output / "manifest.json", manifest)
    results, permutations = _analyze(rows, config)
    results["raw_observations_sha256_colon_hex"] = raw_digest
    _write_json(output / "results.json", results)
    _write_permutations(output / "permutations.csv", permutations)
    _write_summary(output / "summary.md", results)
    _write_svg(output / "perspective_comparison.svg", results)
    return results
