"""Perspective discovery across chronological deployed visible-run blocks."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

from .live_visible_runs import load_verified_observations
from .metrics import mutual_information

METHOD_VERSION = "exp002.live.1"
VARIABLES = (
    "provider",
    "model",
    "lane",
    "profile_name",
    "capability_presence",
    "hour_bin_utc",
    "weekday_utc",
)


@dataclass(frozen=True)
class LiveExperiment002Config:
    source_blocks: int = 5
    permutations: int = 250
    maximum_lag: int = 12
    permutation_seed: int = 202610305


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    variables: tuple[str, ...] = ()
    lag: int = 0


def candidate_catalog(maximum_lag: int) -> list[Candidate]:
    values = [Candidate(f"value({name})", "single", (name,)) for name in VARIABLES]
    values.extend(
        Candidate(f"joint({','.join(names)})", "joint", names)
        for names in itertools.combinations(VARIABLES, 2)
    )
    values.extend(
        Candidate(f"status_lag({lag})", "lag", lag=lag)
        for lag in range(1, maximum_lag + 1)
    )
    return values


def _score(
    rows: list[dict[str, str]], candidate: Candidate, outcomes: list[str]
) -> float:
    if candidate.family == "lag":
        return mutual_information(outcomes[: -candidate.lag], outcomes[candidate.lag :])
    if candidate.family == "single":
        values: list[object] = [row[candidate.variables[0]] for row in rows]
    else:
        values = [tuple(row[name] for name in candidate.variables) for row in rows]
    return mutual_information(values, outcomes)


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


def _source_id(digest: str, index: int) -> str:
    return "L-" + hashlib.sha256(f"{digest}|{index}".encode()).hexdigest()[:4].upper()


def _partition(rows: list[dict[str, str]], blocks: int) -> list[list[dict[str, str]]]:
    base, remainder = divmod(len(rows), blocks)
    result = []
    start = 0
    for index in range(blocks):
        size = base + int(index < remainder)
        result.append(rows[start : start + size])
        start += size
    return result


def _stable_seed(seed: int, source_id: str, partition: str) -> int:
    material = f"{seed}|{source_id}|{partition}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def analyze_live_experiment_002(
    run_directory: Path, config: LiveExperiment002Config
) -> dict:
    if config.source_blocks < 2 or config.permutations < 1 or config.maximum_lag < 1:
        raise ValueError(
            "source_blocks >= 2 and positive permutations/lags are required"
        )
    results_path = run_directory / "exp002_live_results.json"
    if results_path.exists():
        raise FileExistsError(results_path)
    manifest, rows = load_verified_observations(run_directory)
    if len(rows) < config.source_blocks * (config.maximum_lag + 4):
        raise ValueError("not enough live observations for requested blocks and lags")
    candidates = candidate_catalog(config.maximum_lag)
    digest = manifest["observations"]["sha256_colon_hex"]
    results = {
        "method_version": METHOD_VERSION,
        "live_source": manifest["source"],
        "observations_sha256_colon_hex": digest,
        "parameters": {
            "source_blocks": config.source_blocks,
            "permutations": config.permutations,
            "maximum_lag": config.maximum_lag,
            "permutation_seed": config.permutation_seed,
        },
        "candidate_count": len(candidates),
        "candidate_catalog": [candidate.name for candidate in candidates],
        "sources": {},
    }
    null_rows: list[dict[str, int | float | str]] = []
    source_key: dict[str, dict[str, object]] = {}
    for block_index, block in enumerate(_partition(rows, config.source_blocks)):
        source_id = _source_id(digest, block_index)
        midpoint = len(block) // 2
        discovery, confirmation = block[:midpoint], block[midpoint:]
        discovery_outcomes = [row["status"] for row in discovery]
        confirmation_outcomes = [row["status"] for row in confirmation]
        discovery_scores = {
            candidate.name: _score(discovery, candidate, discovery_outcomes)
            for candidate in candidates
        }
        ordered = sorted(candidates, key=lambda c: (-discovery_scores[c.name], c.name))
        selected = ordered[0]
        top = [
            {
                "rank": rank,
                "name": candidate.name,
                "family": candidate.family,
                "variables": list(candidate.variables),
                "lag": candidate.lag or None,
                "discovery_mi_bits": discovery_scores[candidate.name],
                "confirmation_mi_bits": _score(
                    confirmation, candidate, confirmation_outcomes
                ),
            }
            for rank, candidate in enumerate(ordered[:5], start=1)
        ]
        discovery_max_null: list[float] = []
        confirmation_null: list[float] = []
        discovery_rng = random.Random(
            _stable_seed(config.permutation_seed, source_id, "d")
        )
        confirmation_rng = random.Random(
            _stable_seed(config.permutation_seed, source_id, "c")
        )
        for permutation in range(config.permutations):
            shuffled_discovery = discovery_outcomes.copy()
            discovery_rng.shuffle(shuffled_discovery)
            maximum = max(
                _score(discovery, candidate, shuffled_discovery)
                for candidate in candidates
            )
            discovery_max_null.append(maximum)
            shuffled_confirmation = confirmation_outcomes.copy()
            confirmation_rng.shuffle(shuffled_confirmation)
            fixed_score = _score(confirmation, selected, shuffled_confirmation)
            confirmation_null.append(fixed_score)
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
                        "partition": "confirmation",
                        "permutation": permutation,
                        "null_kind": "selected_candidate",
                        "score_bits": fixed_score,
                    },
                ]
            )
        results["sources"][source_id] = {
            "discovery_rows": len(discovery),
            "confirmation_rows": len(confirmation),
            "selected_candidate": top[0],
            "top_discovery_candidates": top,
            "discovery_search_wide_null": _summary(
                discovery_max_null, top[0]["discovery_mi_bits"]
            ),
            "confirmation_selected_candidate_null": _summary(
                confirmation_null, top[0]["confirmation_mi_bits"]
            ),
        }
        source_key[source_id] = {
            "chronological_block": block_index + 1,
            "first_observed_at_utc": block[0]["observed_at_utc"],
            "last_observed_at_utc": block[-1]["observed_at_utc"],
            "first_source_row_id": int(block[0]["source_row_id"]),
            "last_source_row_id": int(block[-1]["source_row_id"]),
        }
    _write_json(results_path, results)
    _write_json(run_directory / "exp002_live_source_key.json", source_key)
    with (run_directory / "exp002_live_null.csv").open(
        "x", newline="", encoding="utf-8"
    ) as handle:
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
        writer.writerows(null_rows)
    _write_summaries(run_directory, results, source_key)
    _write_svg(run_directory / "exp002_live_selected.svg", results)
    return results


def _write_summaries(run_directory: Path, results: dict, source_key: dict) -> None:
    header = [
        "| Source | Selected perspective | Discovery MI | Search-null q95 | Confirmation MI | Confirmation-null q95 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    rows = []
    for source_id, measured in results["sources"].items():
        selected = measured["selected_candidate"]
        rows.append(
            f"| {source_id} | `{selected['name']}` | {selected['discovery_mi_bits']:.6f} "
            f"| {measured['discovery_search_wide_null']['q95']:.6f} "
            f"| {selected['confirmation_mi_bits']:.6f} "
            f"| {measured['confirmation_selected_candidate_null']['q95']:.6f} |"
        )
    opaque = [
        "# Live Investigation 2: opaque measured summary",
        "",
        *header,
        *rows,
        "",
        "Opaque IDs conceal chronological block order in this report only.",
    ]
    revealed = [
        "# Live Investigation 2: chronological reveal",
        "",
        "| Source | Block | Time range (UTC) |",
        "|---|---:|---|",
    ]
    for source_id, details in source_key.items():
        revealed.append(
            f"| {source_id} | {details['chronological_block']} "
            f"| {details['first_observed_at_utc']} → {details['last_observed_at_utc']} |"
        )
    revealed.extend(["", *header, *rows])
    for filename, lines in (
        ("exp002_live_opaque_summary.md", opaque),
        ("exp002_live_revealed_summary.md", revealed),
    ):
        with (run_directory / filename).open("x", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def _log_x(value: float, left: float, width: float) -> float:
    clipped = max(1e-6, min(1.0, value))
    return left + width * (math.log10(clipped) + 6) / 6


def _write_svg(path: Path, results: dict) -> None:
    width, height = 1040, 520
    left, plot_width = 340, 610
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf6"/>',
        "<style>text{font-family:system-ui,sans-serif;fill:#20242b}.title{font-size:20px;font-weight:700}.small{font-size:12px}.label{font-size:13px}.source{font-size:14px;font-weight:700}</style>",
        '<text x="28" y="30" class="title">Live Investigation 2 — selected perspectives before chronology reveal</text>',
        '<text x="28" y="50" class="small">Log scale. Orange: discovery; blue: later confirmation; lines: corresponding permutation-null 5–95%.</text>',
    ]
    for tick_power in range(-6, 1):
        x = _log_x(10**tick_power, left, plot_width)
        svg.extend(
            [
                f'<line x1="{x:.2f}" y1="68" x2="{x:.2f}" y2="{height - 38}" stroke="#d8d4ca" stroke-dasharray="2 4"/>',
                f'<text x="{x:.2f}" y="{height - 16}" class="small" text-anchor="middle">10^{tick_power}</text>',
            ]
        )
    y = 92
    for source_id, measured in results["sources"].items():
        selected = measured["selected_candidate"]
        svg.extend(
            [
                f'<text x="28" y="{y}" class="source">{source_id}</text>',
                f'<text x="82" y="{y}" class="label">{selected["name"]}</text>',
            ]
        )
        comparisons = (
            (
                -7,
                selected["discovery_mi_bits"],
                measured["discovery_search_wide_null"],
                "#d97706",
                "D",
            ),
            (
                9,
                selected["confirmation_mi_bits"],
                measured["confirmation_selected_candidate_null"],
                "#2563eb",
                "C",
            ),
        )
        for offset, score, null, color, label in comparisons:
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
        y += 80
    svg.append("</svg>")
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(svg) + "\n")
