"""Relational recurrence and expectation over deployed observation blocks."""

from __future__ import annotations

import csv
import json
import math
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Hashable

from .live_visible_runs import load_verified_observations
from .metrics import entropy, mutual_information

METHOD_VERSION = "exp004.live.continuity.1"
STATUSES = ("cancelled", "completed", "failed", "interrupted")
REPRESENTATIONS = (
    "state_transition",
    "operational_relation",
    "calendar_relation",
    "model_composition",
)


@dataclass(frozen=True)
class Experiment004Config:
    block_rows: int = 1000
    sensitivity_block_rows: tuple[int, ...] = (500, 2000)
    smoothing_alpha: float = 0.5


OUTPUTS = (
    "exp004_live_results.json",
    "exp004_live_blocks.csv",
    "exp004_live_similarity.csv",
    "exp004_live_expectations.csv",
    "exp004_live_sensitivity.csv",
    "exp004_live_recurrence.svg",
    "exp004_live_summary.md",
)


def _revision_colon_hex(repo_root: Path) -> str:
    revision = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return bytes.fromhex(revision).hex(":")


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path.name}")
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _partition(
    rows: list[dict[str, str]], block_rows: int
) -> list[list[dict[str, str]]]:
    return [
        rows[start : start + block_rows]
        for start in range(0, len(rows), block_rows)
        if len(rows[start : start + block_rows]) == block_rows
    ]


def _proportions(
    values: list[Hashable], categories: tuple[Hashable, ...]
) -> list[float]:
    counts = Counter(values)
    total = len(values)
    return [counts[category] / total for category in categories]


def _transition_vector(statuses: list[str]) -> list[float]:
    transitions = Counter(zip(statuses[:-1], statuses[1:], strict=True))
    total = max(1, len(statuses) - 1)
    return [
        transitions[(left, right)] / total for left in STATUSES for right in STATUSES
    ]


def _model_distribution(block: list[dict[str, str]]) -> dict[str, float]:
    counts = Counter(row["model"] for row in block)
    total = len(block)
    return {key: count / total for key, count in counts.items()}


def _block_state(block: list[dict[str, str]], index: int) -> dict[str, object]:
    statuses = [row["status"] for row in block]
    models = [row["model"] for row in block]
    weekdays = [row["weekday_utc"] for row in block]
    status_props = _proportions(statuses, STATUSES)
    non_completed = [status for status in statuses if status != "completed"]
    non_completed_total = len(non_completed)
    non_completed_mix = [
        (
            sum(status == category for status in non_completed) / non_completed_total
            if non_completed_total
            else 0.0
        )
        for category in ("cancelled", "failed", "interrupted")
    ]
    model_mi = mutual_information(models, statuses)
    weekday_mi = mutual_information(weekdays, statuses)
    joint_mi = mutual_information(list(zip(models, weekdays, strict=True)), statuses)
    adjacent_mi = mutual_information(statuses[:-1], statuses[1:])
    state_transition = status_props + _transition_vector(statuses)
    operational_relation = state_transition + [
        entropy(statuses) / 2,
        model_mi / 2,
        adjacent_mi / 2,
        non_completed_total / len(statuses),
        *non_completed_mix,
    ]
    calendar_relation = operational_relation + [
        weekday_mi / 2,
        (joint_mi - model_mi) / 2,
    ]
    return {
        "block": index + 1,
        "start_offset": index * len(block),
        "end_offset_exclusive": (index + 1) * len(block),
        "first_source_row_id": int(block[0]["source_row_id"]),
        "last_source_row_id": int(block[-1]["source_row_id"]),
        "first_observed_at_utc": block[0]["observed_at_utc"],
        "last_observed_at_utc": block[-1]["observed_at_utc"],
        "status_entropy_bits": entropy(statuses),
        "non_completed_fraction": non_completed_total / len(statuses),
        "cancelled_fraction": status_props[0],
        "completed_fraction": status_props[1],
        "failed_fraction": status_props[2],
        "interrupted_fraction": status_props[3],
        "model_count": len(set(models)),
        "model_status_mi_bits": model_mi,
        "weekday_status_mi_bits": weekday_mi,
        "model_weekday_status_mi_bits": joint_mi,
        "incremental_weekday_given_model_bits": joint_mi - model_mi,
        "adjacent_status_mi_bits": adjacent_mi,
        "state_transition_vector": state_transition,
        "operational_relation_vector": operational_relation,
        "calendar_relation_vector": calendar_relation,
        "model_distribution": _model_distribution(block),
    }


def _rms_distance(left: list[float], right: list[float]) -> float:
    return math.sqrt(
        sum((a - b) ** 2 for a, b in zip(left, right, strict=True)) / len(left)
    )


def _js_distance(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    midpoint = {key: (left.get(key, 0.0) + right.get(key, 0.0)) / 2 for key in keys}

    def divergence(source: dict[str, float]) -> float:
        return sum(
            probability * math.log2(probability / midpoint[key])
            for key, probability in source.items()
            if probability
        )

    return (divergence(left) + divergence(right)) / 2


def _distance(
    left: dict[str, object], right: dict[str, object], representation: str
) -> float:
    if representation == "model_composition":
        return _js_distance(
            left["model_distribution"],
            right["model_distribution"],  # type: ignore[arg-type]
        )
    key = f"{representation}_vector"
    return _rms_distance(left[key], right[key])  # type: ignore[arg-type]


def _similarity_rows(states: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for state_index, state in enumerate(states):
        adjacent = [
            index
            for index in (state_index - 1, state_index + 1)
            if 0 <= index < len(states)
        ]
        non_adjacent = [
            index for index in range(len(states)) if abs(index - state_index) > 1
        ]
        for representation in REPRESENTATIONS:
            adjacent_index = min(
                adjacent,
                key=lambda other: _distance(state, states[other], representation),
            )
            nearest_index = min(
                non_adjacent,
                key=lambda other: _distance(state, states[other], representation),
            )
            adjacent_distance = _distance(state, states[adjacent_index], representation)
            nearest_distance = _distance(state, states[nearest_index], representation)
            result.append(
                {
                    "block": state_index + 1,
                    "representation": representation,
                    "closest_adjacent_block": adjacent_index + 1,
                    "closest_adjacent_distance": adjacent_distance,
                    "closest_nonadjacent_block": nearest_index + 1,
                    "closest_nonadjacent_distance": nearest_distance,
                    "nonadjacent_gap_blocks": abs(nearest_index - state_index),
                    "nonadjacent_is_closer": int(nearest_distance < adjacent_distance),
                }
            )
    return result


def _smoothed_distribution(statuses: list[str], alpha: float) -> dict[str, float]:
    counts = Counter(statuses)
    total = len(statuses) + alpha * len(STATUSES)
    return {status: (counts[status] + alpha) / total for status in STATUSES}


def _scores(statuses: list[str], distribution: dict[str, float]) -> tuple[float, float]:
    log_loss = -sum(math.log2(distribution[status]) for status in statuses) / len(
        statuses
    )
    brier = sum(
        sum(
            (distribution[category] - float(status == category)) ** 2
            for category in STATUSES
        )
        for status in statuses
    ) / len(statuses)
    return log_loss, brier


def _historical_expectations(
    blocks: list[list[dict[str, str]]],
    states: list[dict[str, object]],
    alpha: float,
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for target_index in range(3, len(blocks)):
        current_state_index = target_index - 1
        target_statuses = [row["status"] for row in blocks[target_index]]
        expanding_statuses = [
            row["status"] for block in blocks[:target_index] for row in block
        ]
        previous_statuses = [row["status"] for row in blocks[current_state_index]]
        predictions: dict[str, tuple[dict[str, float], int | None, float | None]] = {
            "expanding_prevalence": (
                _smoothed_distribution(expanding_statuses, alpha),
                None,
                None,
            ),
            "previous_block": (
                _smoothed_distribution(previous_statuses, alpha),
                current_state_index,
                0.0,
            ),
        }
        eligible = range(0, current_state_index - 1)
        for representation in REPRESENTATIONS:
            analog_index = min(
                eligible,
                key=lambda index: _distance(
                    states[current_state_index], states[index], representation
                ),
            )
            following_statuses = [row["status"] for row in blocks[analog_index + 1]]
            predictions[f"recurrence_{representation}"] = (
                _smoothed_distribution(following_statuses, alpha),
                analog_index,
                _distance(
                    states[current_state_index], states[analog_index], representation
                ),
            )
        for predictor, (distribution, analog_index, distance) in predictions.items():
            log_loss, brier = _scores(target_statuses, distribution)
            result.append(
                {
                    "target_block": target_index + 1,
                    "current_state_block": current_state_index + 1,
                    "predictor": predictor,
                    "analog_state_block": (
                        analog_index + 1 if analog_index is not None else ""
                    ),
                    "analog_following_block": (
                        analog_index + 2
                        if analog_index is not None
                        and predictor.startswith("recurrence_")
                        else ""
                    ),
                    "analog_distance": distance if distance is not None else "",
                    "target_first_observed_at_utc": blocks[target_index][0][
                        "observed_at_utc"
                    ],
                    "target_last_observed_at_utc": blocks[target_index][-1][
                        "observed_at_utc"
                    ],
                    "log_loss_bits": log_loss,
                    "brier_score": brier,
                    **{f"expected_{key}": value for key, value in distribution.items()},
                }
            )
    return result


def _aggregate_expectations(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["predictor"]), []).append(row)
    previous_by_target = {
        int(row["target_block"]): row for row in grouped["previous_block"]
    }
    result: list[dict[str, object]] = []
    for predictor, measured in grouped.items():
        losses = [float(row["log_loss_bits"]) for row in measured]
        briers = [float(row["brier_score"]) for row in measured]
        result.append(
            {
                "predictor": predictor,
                "targets": len(measured),
                "mean_log_loss_bits": sum(losses) / len(losses),
                "mean_brier_score": sum(briers) / len(briers),
                "log_loss_wins_vs_previous_block": sum(
                    float(row["log_loss_bits"])
                    < float(
                        previous_by_target[int(row["target_block"])]["log_loss_bits"]
                    )
                    for row in measured
                ),
                "brier_wins_vs_previous_block": sum(
                    float(row["brier_score"])
                    < float(previous_by_target[int(row["target_block"])]["brier_score"])
                    for row in measured
                ),
            }
        )
    return sorted(result, key=lambda row: str(row["predictor"]))


def _sensitivity(
    rows: list[dict[str, str]], block_sizes: tuple[int, ...]
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for block_rows in block_sizes:
        blocks = _partition(rows, block_rows)
        states = [_block_state(block, index) for index, block in enumerate(blocks)]
        similarity = _similarity_rows(states)
        for representation in REPRESENTATIONS:
            selected = [
                row for row in similarity if row["representation"] == representation
            ]
            result.append(
                {
                    "block_rows": block_rows,
                    "blocks": len(blocks),
                    "representation": representation,
                    "nonadjacent_closer_count": sum(
                        int(row["nonadjacent_is_closer"]) for row in selected
                    ),
                    "nonadjacent_closer_fraction": sum(
                        int(row["nonadjacent_is_closer"]) for row in selected
                    )
                    / len(selected),
                    "mean_nonadjacent_gap_blocks": sum(
                        int(row["nonadjacent_gap_blocks"]) for row in selected
                    )
                    / len(selected),
                }
            )
    return result


def analyze_experiment_004(
    run_directory: Path,
    output_directory: Path,
    repo_root: Path,
    config: Experiment004Config,
) -> dict[str, object]:
    """Run the declared retrospective continuity analysis."""
    if config.block_rows < 20 or config.smoothing_alpha <= 0:
        raise ValueError("non-degenerate block size and positive smoothing required")
    output_directory.mkdir(parents=True, exist_ok=True)
    existing = [name for name in OUTPUTS if (output_directory / name).exists()]
    if existing:
        raise FileExistsError(f"Investigation 4 outputs already exist: {existing}")
    manifest, rows = load_verified_observations(run_directory)
    blocks = _partition(rows, config.block_rows)
    if len(blocks) < 6:
        raise ValueError("at least six complete blocks are required")
    states = [_block_state(block, index) for index, block in enumerate(blocks)]
    similarity = _similarity_rows(states)
    historical = _historical_expectations(blocks, states, config.smoothing_alpha)
    aggregates = _aggregate_expectations(historical)
    sensitivity = _sensitivity(rows, config.sensitivity_block_rows)
    public_states = [
        {
            key: value
            for key, value in state.items()
            if not key.endswith("_vector") and key != "model_distribution"
        }
        for state in states
    ]
    result: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "evidence_status": "retrospective exploratory analysis of previously inspected observations",
        "deployed_analysis_revision_colon_hex": _revision_colon_hex(repo_root),
        "observations_sha256_colon_hex": manifest["observations"]["sha256_colon_hex"],
        "source": manifest["source"],
        "parameters": {
            "block_rows": config.block_rows,
            "sensitivity_block_rows": list(config.sensitivity_block_rows),
            "smoothing_alpha": config.smoothing_alpha,
        },
        "representations": {
            "state_transition": "status proportions and adjacent-status transition matrix",
            "operational_relation": "state/transition plus entropy, model/status MI, adjacent MI, and non-completed composition",
            "calendar_relation": "operational relation plus weekday MI and incremental model-weekday MI",
            "model_composition": "Jensen-Shannon divergence over labeled model populations",
        },
        "blocks": public_states,
        "similarity": similarity,
        "historical_expectations": historical,
        "expectation_aggregates": aggregates,
        "sensitivity": sensitivity,
    }
    _write_json(output_directory / OUTPUTS[0], result)
    _write_csv(output_directory / OUTPUTS[1], public_states)
    _write_csv(output_directory / OUTPUTS[2], similarity)
    _write_csv(output_directory / OUTPUTS[3], historical)
    _write_csv(output_directory / OUTPUTS[4], sensitivity)
    _write_svg(output_directory / OUTPUTS[5], states, similarity)
    _write_summary(output_directory / OUTPUTS[6], result)
    return result


def _write_summary(path: Path, result: dict[str, object]) -> None:
    aggregates = result["expectation_aggregates"]
    assert isinstance(aggregates, list)
    lines = [
        "# Live Investigation 4: measured summary",
        "",
        "**Evidence status:** retrospective exploration; not independent confirmation.",
        "",
        "| Predictor | Mean log loss | Mean Brier | Log-loss wins vs previous |",
        "|---|---:|---:|---:|",
    ]
    for row in aggregates:
        lines.append(
            f"| `{row['predictor']}` | {row['mean_log_loss_bits']:.6f} "
            f"| {row['mean_brier_score']:.6f} "
            f"| {row['log_loss_wins_vs_previous_block']}/{row['targets']} |"
        )
    lines.extend(
        [
            "",
            "Separate representations are not a universal continuity scale.",
            "Any prospective candidate must be frozen before rows above high-water ID 46095 are read.",
        ]
    )
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _write_svg(
    path: Path,
    states: list[dict[str, object]],
    similarity: list[dict[str, object]],
) -> None:
    width, height = 1160, 650
    left, right, top, panel_height = 90, 1110, 84, 205
    plot_width = right - left

    def x(index: int) -> float:
        return left + plot_width * index / max(1, len(states) - 1)

    max_entropy = max(float(state["status_entropy_bits"]) for state in states)
    max_mi = max(float(state["model_weekday_status_mi_bits"]) for state in states)

    def y(value: float, maximum: float, panel_top: float) -> float:
        if maximum <= 0:
            return panel_top + panel_height
        return panel_top + panel_height * (1 - value / maximum)

    entropy_points = " ".join(
        f"{x(index):.1f},{y(float(state['status_entropy_bits']), max_entropy, top):.1f}"
        for index, state in enumerate(states)
    )
    mi_points = " ".join(
        f"{x(index):.1f},{y(float(state['model_weekday_status_mi_bits']), max_mi, top):.1f}"
        for index, state in enumerate(states)
    )
    second_top = 390
    selected = [
        row for row in similarity if row["representation"] == "operational_relation"
    ]
    max_distance = max(
        max(
            float(row["closest_adjacent_distance"]),
            float(row["closest_nonadjacent_distance"]),
        )
        for row in selected
    )
    adjacent_points = " ".join(
        f"{x(index):.1f},{y(float(row['closest_adjacent_distance']), max_distance, second_top):.1f}"
        for index, row in enumerate(selected)
    )
    recurrent_points = " ".join(
        f"{x(index):.1f},{y(float(row['closest_nonadjacent_distance']), max_distance, second_top):.1f}"
        for index, row in enumerate(selected)
    )
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf6"/>',
        "<style>text{font-family:system-ui,sans-serif;fill:#20242b}.title{font-size:21px;font-weight:700}.label{font-size:13px}.small{font-size:11px}</style>",
        '<text x="28" y="32" class="title">Investigation 4 — adjacency and relational recurrence</text>',
        '<text x="28" y="53" class="small">1,000-row database-ordered states; retrospective exploratory views</text>',
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{panel_height}" fill="none" stroke="#bbb7ae"/>',
        f'<polyline points="{entropy_points}" fill="none" stroke="#0f766e" stroke-width="2.5"/>',
        f'<polyline points="{mi_points}" fill="none" stroke="#6d28d9" stroke-width="2.5"/>',
        f'<text x="{left}" y="{top - 10}" class="label">Status entropy (teal) and model×weekday MI (purple), independently scaled</text>',
        f'<rect x="{left}" y="{second_top}" width="{plot_width}" height="{panel_height}" fill="none" stroke="#bbb7ae"/>',
        f'<polyline points="{adjacent_points}" fill="none" stroke="#2563eb" stroke-width="2.5"/>',
        f'<polyline points="{recurrent_points}" fill="none" stroke="#d97706" stroke-width="2.5"/>',
        f'<text x="{left}" y="{second_top - 10}" class="label">Operational-relation distance: closest adjacent (blue), closest non-adjacent (orange)</text>',
    ]
    for index in (0, len(states) // 2, len(states) - 1):
        label = str(states[index]["first_observed_at_utc"])[:10]
        position = x(index)
        svg.append(
            f'<text x="{position:.1f}" y="{height - 20}" class="small" text-anchor="middle">{label}</text>'
        )
    svg.append("</svg>")
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(svg) + "\n")
