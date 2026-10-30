"""Blind-by-construction candidate discovery for Investigation 2."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .metrics import entropy, mutual_information

METHOD_VERSION = "exp002.discover.1"
BASE_VARIABLES = ("v0", "v1", "v2", "v3", "context")


@dataclass(frozen=True)
class DiscoveryConfig:
    permutations: int = 250
    maximum_lag: int = 12
    permutation_seed: int = 202610303

    def validate(self) -> None:
        if self.permutations < 1:
            raise ValueError("permutations must be positive")
        if self.maximum_lag < 1:
            raise ValueError("maximum_lag must be positive")


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    variables: tuple[str, ...] = ()
    lag: int = 0


def candidate_catalog(maximum_lag: int) -> list[Candidate]:
    candidates = [
        Candidate(f"value({name})", "single", (name,)) for name in BASE_VARIABLES
    ]
    candidates.extend(
        Candidate(f"joint({','.join(names)})", "joint", names)
        for names in itertools.combinations(BASE_VARIABLES, 2)
    )
    candidates.extend(
        Candidate(f"xor({','.join(names)})", "xor", names)
        for size in (2, 3, 4)
        for names in itertools.combinations(BASE_VARIABLES, size)
    )
    candidates.extend(
        Candidate(f"outcome_lag({lag})", "lag", lag=lag)
        for lag in range(1, maximum_lag + 1)
    )
    return candidates


def _candidate_values(
    rows: list[dict[str, int | str]], candidate: Candidate, outcomes: list[int]
) -> tuple[list[object], list[int]]:
    if candidate.family == "lag":
        return outcomes[: -candidate.lag], outcomes[candidate.lag :]
    if candidate.family == "single":
        return [int(row[candidate.variables[0]]) for row in rows], outcomes
    if candidate.family == "joint":
        return [
            tuple(int(row[name]) for name in candidate.variables) for row in rows
        ], outcomes
    if candidate.family == "xor":
        return [
            sum(int(row[name]) for name in candidate.variables) % 2 for row in rows
        ], outcomes
    raise ValueError(f"unknown candidate family: {candidate.family}")


def score_candidate(
    rows: list[dict[str, int | str]], candidate: Candidate, outcomes: list[int]
) -> float:
    values, aligned_outcomes = _candidate_values(rows, candidate, outcomes)
    return mutual_information(values, aligned_outcomes)


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _null_summary(values: list[float], observed: float) -> dict[str, float | int]:
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


def _colon_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).digest().hex(":")


def _load_rows(path: Path) -> list[dict[str, int | str]]:
    integer_fields = {"index", "v0", "v1", "v2", "v3", "context", "outcome"}
    with path.open(newline="", encoding="utf-8") as handle:
        rows: list[dict[str, int | str]] = []
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    key: int(value) if key in integer_fields else value
                    for key, value in raw.items()
                }
            )
    return rows


def _stable_permutation_seed(seed: int, source_id: str, partition: str) -> int:
    material = f"{seed}|{source_id}|{partition}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_null_rows(path: Path, rows: list[dict[str, int | float | str]]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_id",
                "partition",
                "permutation",
                "null_kind",
                "score_bits",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _analyze_source(
    source_id: str,
    source_rows: list[dict[str, int | str]],
    candidates: list[Candidate],
    config: DiscoveryConfig,
) -> tuple[dict[str, Any], list[dict[str, int | float | str]]]:
    discovery = [row for row in source_rows if row["partition"] == "discovery"]
    confirmation = [row for row in source_rows if row["partition"] == "confirmation"]
    discovery_outcomes = [int(row["outcome"]) for row in discovery]
    confirmation_outcomes = [int(row["outcome"]) for row in confirmation]
    discovery_scores = {
        candidate.name: score_candidate(discovery, candidate, discovery_outcomes)
        for candidate in candidates
    }
    ordered = sorted(
        candidates, key=lambda item: (-discovery_scores[item.name], item.name)
    )
    selected = ordered[0]
    selected_discovery_score = discovery_scores[selected.name]
    top_candidates = [
        {
            "rank": rank,
            "name": candidate.name,
            "family": candidate.family,
            "variables": list(candidate.variables),
            "lag": candidate.lag or None,
            "discovery_mi_bits": discovery_scores[candidate.name],
            "confirmation_mi_bits": score_candidate(
                confirmation, candidate, confirmation_outcomes
            ),
        }
        for rank, candidate in enumerate(ordered[:5], start=1)
    ]

    discovery_max_null: list[float] = []
    discovery_selected_null: list[float] = []
    confirmation_selected_null: list[float] = []
    null_rows: list[dict[str, int | float | str]] = []
    discovery_rng = random.Random(
        _stable_permutation_seed(config.permutation_seed, source_id, "discovery")
    )
    confirmation_rng = random.Random(
        _stable_permutation_seed(config.permutation_seed, source_id, "confirmation")
    )
    for permutation in range(config.permutations):
        shuffled_discovery = discovery_outcomes.copy()
        discovery_rng.shuffle(shuffled_discovery)
        all_null_scores = [
            score_candidate(discovery, candidate, shuffled_discovery)
            for candidate in candidates
        ]
        maximum = max(all_null_scores)
        selected_null = score_candidate(discovery, selected, shuffled_discovery)
        discovery_max_null.append(maximum)
        discovery_selected_null.append(selected_null)
        shuffled_confirmation = confirmation_outcomes.copy()
        confirmation_rng.shuffle(shuffled_confirmation)
        confirmation_null = score_candidate(
            confirmation, selected, shuffled_confirmation
        )
        confirmation_selected_null.append(confirmation_null)
        null_rows.extend(
            [
                {
                    "source_id": source_id,
                    "partition": "discovery",
                    "permutation": permutation,
                    "null_kind": "search_wide_maximum",
                    "score_bits": maximum,
                },
                {
                    "source_id": source_id,
                    "partition": "discovery",
                    "permutation": permutation,
                    "null_kind": "selected_candidate",
                    "score_bits": selected_null,
                },
                {
                    "source_id": source_id,
                    "partition": "confirmation",
                    "permutation": permutation,
                    "null_kind": "selected_candidate",
                    "score_bits": confirmation_null,
                },
            ]
        )
    confirmation_score = top_candidates[0]["confirmation_mi_bits"]
    return (
        {
            "descriptive": {
                "discovery_rows": len(discovery),
                "confirmation_rows": len(confirmation),
                "discovery_outcome_entropy_bits": entropy(discovery_outcomes),
                "confirmation_outcome_entropy_bits": entropy(confirmation_outcomes),
            },
            "candidate_count": len(candidates),
            "selected_candidate": top_candidates[0],
            "top_discovery_candidates": top_candidates,
            "discovery_search_wide_null": _null_summary(
                discovery_max_null, selected_discovery_score
            ),
            "discovery_selected_candidate_null": _null_summary(
                discovery_selected_null, selected_discovery_score
            ),
            "confirmation_selected_candidate_null": _null_summary(
                confirmation_selected_null, confirmation_score
            ),
        },
        null_rows,
    )


def _write_summary(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Investigation 2: opaque measured summary",
        "",
        "Source meanings were not available to the analyzer. Scores are plug-in",
        "mutual information; calibration measures are descriptive, not universal thresholds.",
        "",
        "| Source | Selected discovery perspective | Discovery MI | Search-null q95 | Confirmation MI | Confirmation-null q95 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for source_id, source in results["sources"].items():
        selected = source["selected_candidate"]
        lines.append(
            f"| {source_id} | `{selected['name']}` | {selected['discovery_mi_bits']:.6f} "
            f"| {source['discovery_search_wide_null']['q95']:.6f} "
            f"| {selected['confirmation_mi_bits']:.6f} "
            f"| {source['confirmation_selected_candidate_null']['q95']:.6f} |"
        )
    lines.extend(
        [
            "",
            "The search-null comparison accounts for selecting the largest score from the",
            "declared catalog. Confirmation evaluates that selected perspective without reselection.",
        ]
    )
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _log_x(value: float, left: float, width: float) -> float:
    clipped = max(1e-6, min(1.0, value))
    return left + width * (math.log10(clipped) + 6) / 6


def _write_svg(path: Path, results: dict[str, Any]) -> None:
    width, height = 980, 510
    left, plot_width = 270, 620
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf6"/>',
        "<style>text{font-family:system-ui,sans-serif;fill:#20242b}.title{font-size:20px;font-weight:700}.small{font-size:12px}.label{font-size:13px}.source{font-size:14px;font-weight:700}</style>",
        '<text x="28" y="30" class="title">Investigation 2 — selected perspectives before source reveal</text>',
        '<text x="28" y="50" class="small">Log scale. Orange: discovery selection; blue: fixed-candidate confirmation; lines: corresponding null 5–95%.</text>',
    ]
    for tick_power in range(-6, 1):
        value = 10**tick_power
        x = _log_x(value, left, plot_width)
        svg.extend(
            [
                f'<line x1="{x:.2f}" y1="68" x2="{x:.2f}" y2="{height - 38}" stroke="#d8d4ca" stroke-dasharray="2 4"/>',
                f'<text x="{x:.2f}" y="{height - 16}" class="small" text-anchor="middle">10^{tick_power}</text>',
            ]
        )
    y = 92
    for source_id, source in results["sources"].items():
        selected = source["selected_candidate"]
        discovery_null = source["discovery_search_wide_null"]
        confirmation_null = source["confirmation_selected_candidate_null"]
        svg.extend(
            [
                f'<text x="28" y="{y}" class="source">{source_id}</text>',
                f'<text x="82" y="{y}" class="label">{selected["name"]}</text>',
            ]
        )
        for offset, score, null, color, label in (
            (-7, selected["discovery_mi_bits"], discovery_null, "#d97706", "D"),
            (9, selected["confirmation_mi_bits"], confirmation_null, "#2563eb", "C"),
        ):
            line_y = y + offset
            x05 = _log_x(null["q05"], left, plot_width)
            x95 = _log_x(null["q95"], left, plot_width)
            point_x = _log_x(score, left, plot_width)
            svg.extend(
                [
                    f'<line x1="{x05:.2f}" y1="{line_y}" x2="{x95:.2f}" y2="{line_y}" stroke="#4b5563" stroke-width="2"/>',
                    f'<circle cx="{point_x:.2f}" cy="{line_y}" r="5" fill="{color}"/>',
                    f'<text x="{left - 12}" y="{line_y + 4}" class="small" text-anchor="end">{label}</text>',
                    f'<text x="{left + plot_width + 10}" y="{line_y + 4}" class="small">{score:.5f}</text>',
                ]
            )
        y += 78
    svg.append("</svg>")
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(svg) + "\n")


def analyze_dataset(run_directory: Path, config: DiscoveryConfig) -> dict[str, Any]:
    """Analyze opaque observations without reading the source key."""
    config.validate()
    results_path = run_directory / "results.json"
    if results_path.exists():
        raise FileExistsError(results_path)
    manifest = json.loads(
        (run_directory / "generation_manifest.json").read_text(encoding="utf-8")
    )
    observations = run_directory / manifest["raw_observations"]["path"]
    digest = _colon_sha256(observations)
    if digest != manifest["raw_observations"]["sha256_colon_hex"]:
        raise ValueError("raw observation digest does not match generation manifest")
    rows = _load_rows(observations)
    candidates = candidate_catalog(config.maximum_lag)
    source_ids = sorted({str(row["source_id"]) for row in rows})
    results: dict[str, Any] = {
        "method_version": METHOD_VERSION,
        "parameters": {
            "permutations": config.permutations,
            "maximum_lag": config.maximum_lag,
            "permutation_seed": config.permutation_seed,
        },
        "raw_observations_sha256_colon_hex": digest,
        "candidate_catalog": [
            {
                "name": item.name,
                "family": item.family,
                "variables": list(item.variables),
                "lag": item.lag or None,
            }
            for item in candidates
        ],
        "sources": {},
    }
    null_rows: list[dict[str, int | float | str]] = []
    for source_id in source_ids:
        measured, source_null_rows = _analyze_source(
            source_id,
            [row for row in rows if row["source_id"] == source_id],
            candidates,
            config,
        )
        results["sources"][source_id] = measured
        null_rows.extend(source_null_rows)
    _write_json(results_path, results)
    _write_null_rows(run_directory / "null_measurements.csv", null_rows)
    _write_summary(run_directory / "opaque_summary.md", results)
    _write_svg(run_directory / "selected_perspectives.svg", results)
    return results


def reveal_sources(run_directory: Path) -> None:
    """Write a post-analysis mapping and observation table; never alter results."""
    output = run_directory / "revealed_summary.md"
    if output.exists():
        raise FileExistsError(output)
    results = json.loads((run_directory / "results.json").read_text(encoding="utf-8"))
    source_key = json.loads(
        (run_directory / "source_key.json").read_text(encoding="utf-8")
    )
    lines = [
        "# Investigation 2: source reveal",
        "",
        "This mapping was applied after opaque `results.json` had been written.",
        "Generator intent is provenance, not ground truth about every observed pattern.",
        "",
        "| Source | Generator | Selected perspective | Discovery MI | Confirmation MI | Search exceedances | Confirmation exceedances |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for source_id, measured in results["sources"].items():
        key = source_key["sources"][source_id]
        selected = measured["selected_candidate"]
        search_null = measured["discovery_search_wide_null"]
        confirmation_null = measured["confirmation_selected_candidate_null"]
        lines.append(
            f"| {source_id} | `{key['generator']}` | `{selected['name']}` "
            f"| {selected['discovery_mi_bits']:.6f} | {selected['confirmation_mi_bits']:.6f} "
            f"| {search_null['exceedance_count']}/{search_null['permutations']} "
            f"| {confirmation_null['exceedance_count']}/{confirmation_null['permutations']} |"
        )
    lines.extend(
        [
            "",
            "Descriptions and intended contrasts are preserved in `source_key.json`.",
            "Interpretation and limitations belong in the living research notebook.",
        ]
    )
    with output.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
