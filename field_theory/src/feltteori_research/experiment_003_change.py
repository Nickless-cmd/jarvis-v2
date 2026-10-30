"""Retrospective analysis of change in deployed observable relationships."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import socket
import sqlite3
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Hashable

from .live_visible_runs import load_verified_observations
from .metrics import entropy, mutual_information

METHOD_VERSION = "exp003.live.change.1"
CONTEXT_METHOD_VERSION = "exp003.live.context.1"


@dataclass(frozen=True)
class Experiment003Config:
    window_rows: int = 2000
    step_rows: int = 500
    permutations: int = 200
    permutation_seed: int = 202610306
    sensitivity_window_rows: tuple[int, ...] = (1000, 4000)
    discontinuity_block_rows: int = 1000
    transport_blocks: int = 5
    smoothing_alpha: float = 0.5


@dataclass(frozen=True)
class OperationalContextConfig:
    db_path: Path = Path("/home/bs/.jarvis-v2/state/jarvis.db")
    expected_host: str = "Jarvis"


OUTPUTS = (
    "exp003_live_results.json",
    "exp003_live_rolling.csv",
    "exp003_live_sensitivity.csv",
    "exp003_live_discontinuities.csv",
    "exp003_live_transfers.csv",
    "exp003_live_evolution.svg",
    "exp003_live_summary.md",
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


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _stable_seed(seed: int, *parts: object) -> int:
    material = "|".join(str(part) for part in (seed, *parts)).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _windows(
    rows: list[dict[str, str]], size: int, step: int
) -> list[tuple[int, list[dict[str, str]]]]:
    if size > len(rows):
        return []
    return [
        (start, rows[start : start + size])
        for start in range(0, len(rows) - size + 1, step)
    ]


def _month(row: dict[str, str]) -> str:
    return row["observed_at_utc"][:7]


def _conditional_weekday_shuffle(
    rows: list[dict[str, str]], rng: random.Random
) -> tuple[list[str], float]:
    weekdays = [row["weekday_utc"] for row in rows]
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[(row["model"], _month(row))].append(index)
    movable = 0
    for indices in groups.values():
        values = [weekdays[index] for index in indices]
        if len(set(values)) > 1:
            movable += len(indices)
        rng.shuffle(values)
        for index, value in zip(indices, values, strict=True):
            weekdays[index] = value
    return weekdays, movable / len(rows)


def _window_metrics(
    block: list[dict[str, str]],
    start: int,
    config: Experiment003Config,
    with_nulls: bool,
) -> dict[str, object]:
    statuses = [row["status"] for row in block]
    models = [row["model"] for row in block]
    weekdays = [row["weekday_utc"] for row in block]
    joint = list(zip(models, weekdays, strict=True))
    status_entropy = entropy(statuses)
    model_mi = mutual_information(models, statuses)
    weekday_mi = mutual_information(weekdays, statuses)
    joint_mi = mutual_information(joint, statuses)
    joint_counts = Counter(joint)
    result: dict[str, object] = {
        "start_offset": start,
        "end_offset_exclusive": start + len(block),
        "first_source_row_id": int(block[0]["source_row_id"]),
        "last_source_row_id": int(block[-1]["source_row_id"]),
        "first_observed_at_utc": block[0]["observed_at_utc"],
        "last_observed_at_utc": block[-1]["observed_at_utc"],
        "rows": len(block),
        "status_entropy_bits": status_entropy,
        "non_completed_fraction": sum(value != "completed" for value in statuses)
        / len(statuses),
        "status_count": len(set(statuses)),
        "model_count": len(set(models)),
        "model_weekday_state_count": len(joint_counts),
        "rare_joint_row_fraction_lt5": sum(
            count for count in joint_counts.values() if count < 5
        )
        / len(block),
        "model_mi_bits": model_mi,
        "weekday_mi_bits": weekday_mi,
        "model_weekday_mi_bits": joint_mi,
        "incremental_weekday_given_model_bits": joint_mi - model_mi,
        "normalized_joint_by_status_entropy": (
            joint_mi / status_entropy if status_entropy else None
        ),
    }
    if not with_nulls:
        return result
    conditional_values: list[float] = []
    global_values: list[float] = []
    movable_fractions: list[float] = []
    rng = random.Random(_stable_seed(config.permutation_seed, start, len(block)))
    for _ in range(config.permutations):
        permuted_weekdays, movable = _conditional_weekday_shuffle(block, rng)
        permuted_joint = list(zip(models, permuted_weekdays, strict=True))
        conditional_values.append(
            mutual_information(permuted_joint, statuses) - model_mi
        )
        shuffled_statuses = statuses.copy()
        rng.shuffle(shuffled_statuses)
        global_values.append(mutual_information(joint, shuffled_statuses))
        movable_fractions.append(movable)
    observed_increment = joint_mi - model_mi
    conditional_mean = sum(conditional_values) / len(conditional_values)
    result.update(
        {
            "conditional_null_mean_bits": conditional_mean,
            "conditional_null_q05_bits": _quantile(conditional_values, 0.05),
            "conditional_null_q95_bits": _quantile(conditional_values, 0.95),
            "conditional_null_exceedances": sum(
                value >= observed_increment for value in conditional_values
            ),
            "bias_reference_adjusted_increment_bits": observed_increment
            - conditional_mean,
            "conditional_null_movable_row_fraction": sum(movable_fractions)
            / len(movable_fractions),
            "global_outcome_null_mean_joint_bits": sum(global_values)
            / len(global_values),
            "global_outcome_null_q95_joint_bits": _quantile(global_values, 0.95),
        }
    )
    return result


def _distribution(values: list[Hashable]) -> dict[Hashable, float]:
    counts = Counter(values)
    return {key: count / len(values) for key, count in counts.items()}


def _jensen_shannon(left: list[Hashable], right: list[Hashable]) -> float:
    p, q = _distribution(left), _distribution(right)
    keys = set(p) | set(q)
    midpoint = {key: (p.get(key, 0.0) + q.get(key, 0.0)) / 2 for key in keys}

    def divergence(source: dict[Hashable, float]) -> float:
        return sum(
            probability * math.log2(probability / midpoint[key])
            for key, probability in source.items()
            if probability
        )

    return (divergence(p) + divergence(q)) / 2


def _partition(rows: list[dict[str, str]], blocks: int) -> list[list[dict[str, str]]]:
    base, remainder = divmod(len(rows), blocks)
    result: list[list[dict[str, str]]] = []
    start = 0
    for index in range(blocks):
        size = base + int(index < remainder)
        result.append(rows[start : start + size])
        start += size
    return result


def _discontinuities(
    rows: list[dict[str, str]], block_rows: int
) -> list[dict[str, object]]:
    blocks = [
        rows[index : index + block_rows] for index in range(0, len(rows), block_rows)
    ]
    blocks = [block for block in blocks if len(block) == block_rows]
    result: list[dict[str, object]] = []
    for index, (left, right) in enumerate(
        zip(blocks, blocks[1:], strict=False), start=1
    ):
        left_status = [row["status"] for row in left]
        right_status = [row["status"] for row in right]
        left_models = [row["model"] for row in left]
        right_models = [row["model"] for row in right]
        result.append(
            {
                "boundary_after_block": index,
                "left_last_source_row_id": int(left[-1]["source_row_id"]),
                "right_first_source_row_id": int(right[0]["source_row_id"]),
                "left_last_observed_at_utc": left[-1]["observed_at_utc"],
                "right_first_observed_at_utc": right[0]["observed_at_utc"],
                "status_js_divergence_bits": _jensen_shannon(left_status, right_status),
                "model_js_divergence_bits": _jensen_shannon(left_models, right_models),
                "non_completed_fraction_change": (
                    sum(value != "completed" for value in right_status)
                    - sum(value != "completed" for value in left_status)
                )
                / block_rows,
                "models_entered": len(set(right_models) - set(left_models)),
                "models_left": len(set(left_models) - set(right_models)),
            }
        )
    return result


def _probability_model(
    rows: list[dict[str, str]],
    feature_names: tuple[str, ...],
    statuses: tuple[str, ...],
    alpha: float,
) -> tuple[dict[tuple[str, ...], dict[str, float]], dict[str, float]]:
    overall = Counter(row["status"] for row in rows)
    denominator = len(rows) + alpha * len(statuses)
    fallback = {status: (overall[status] + alpha) / denominator for status in statuses}
    grouped: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    for row in rows:
        grouped[tuple(row[name] for name in feature_names)][row["status"]] += 1
    probabilities: dict[tuple[str, ...], dict[str, float]] = {}
    for key, counts in grouped.items():
        total = sum(counts.values()) + alpha * len(statuses)
        probabilities[key] = {
            status: (counts[status] + alpha) / total for status in statuses
        }
    return probabilities, fallback


def _log_loss(
    rows: list[dict[str, str]],
    features: tuple[str, ...],
    probabilities: dict[tuple[str, ...], dict[str, float]],
    fallback: dict[str, float],
    model_backoff: tuple[dict[tuple[str, ...], dict[str, float]], dict[str, float]]
    | None = None,
) -> tuple[float, float]:
    loss = 0.0
    exact = 0
    for row in rows:
        key = tuple(row[name] for name in features)
        distribution = probabilities.get(key)
        if distribution is not None:
            exact += 1
        elif model_backoff is not None:
            distribution = model_backoff[0].get((row["model"],), model_backoff[1])
        else:
            distribution = fallback
        loss -= math.log2(distribution[row["status"]])
    return loss / len(rows), exact / len(rows)


def _transfers(
    rows: list[dict[str, str]], config: Experiment003Config
) -> list[dict[str, object]]:
    blocks = _partition(rows, config.transport_blocks)
    statuses = tuple(sorted({row["status"] for row in rows}))
    result: list[dict[str, object]] = []
    for index, (training, evaluation) in enumerate(
        zip(blocks, blocks[1:], strict=False), start=1
    ):
        base_model, base_fallback = _probability_model(
            training, (), statuses, config.smoothing_alpha
        )
        model_model, model_fallback = _probability_model(
            training, ("model",), statuses, config.smoothing_alpha
        )
        joint_model, joint_fallback = _probability_model(
            training, ("model", "weekday_utc"), statuses, config.smoothing_alpha
        )
        base_loss, _ = _log_loss(evaluation, (), base_model, base_fallback)
        model_loss, model_coverage = _log_loss(
            evaluation, ("model",), model_model, model_fallback
        )
        joint_loss, joint_coverage = _log_loss(
            evaluation,
            ("model", "weekday_utc"),
            joint_model,
            joint_fallback,
            (model_model, model_fallback),
        )
        result.append(
            {
                "training_block": index,
                "evaluation_block": index + 1,
                "training_first_observed_at_utc": training[0]["observed_at_utc"],
                "training_last_observed_at_utc": training[-1]["observed_at_utc"],
                "evaluation_first_observed_at_utc": evaluation[0]["observed_at_utc"],
                "evaluation_last_observed_at_utc": evaluation[-1]["observed_at_utc"],
                "base_log_loss_bits": base_loss,
                "model_log_loss_bits": model_loss,
                "model_weekday_log_loss_bits": joint_loss,
                "model_gain_vs_base_bits": base_loss - model_loss,
                "weekday_gain_vs_model_bits": model_loss - joint_loss,
                "model_exact_state_coverage": model_coverage,
                "model_weekday_exact_state_coverage": joint_coverage,
            }
        )
    return result


def _full_snapshot(rows: list[dict[str, str]]) -> dict[str, object]:
    statuses = [row["status"] for row in rows]
    models = [row["model"] for row in rows]
    weekdays = [row["weekday_utc"] for row in rows]
    joint = list(zip(models, weekdays, strict=True))
    status_entropy = entropy(statuses)
    model_mi = mutual_information(models, statuses)
    joint_mi = mutual_information(joint, statuses)
    return {
        "rows": len(rows),
        "status_entropy_bits": status_entropy,
        "model_count": len(set(models)),
        "model_weekday_state_count": len(set(joint)),
        "model_mi_bits": model_mi,
        "weekday_mi_bits": mutual_information(weekdays, statuses),
        "model_weekday_mi_bits": joint_mi,
        "incremental_weekday_given_model_bits": joint_mi - model_mi,
        "normalized_joint_by_status_entropy": joint_mi / status_entropy,
    }


def analyze_experiment_003(
    run_directory: Path,
    output_directory: Path,
    repo_root: Path,
    config: Experiment003Config,
) -> dict[str, object]:
    """Run the recorded retrospective analysis without changing observations."""
    if (
        config.window_rows < 2
        or config.step_rows < 1
        or config.permutations < 1
        or config.discontinuity_block_rows < 2
        or config.transport_blocks < 2
        or config.smoothing_alpha <= 0
    ):
        raise ValueError("positive, non-degenerate analysis parameters are required")
    output_directory.mkdir(parents=True, exist_ok=True)
    existing = [name for name in OUTPUTS if (output_directory / name).exists()]
    if existing:
        raise FileExistsError(f"Investigation 3 outputs already exist: {existing}")
    manifest, rows = load_verified_observations(run_directory)
    rolling = [
        _window_metrics(block, start, config, with_nulls=True)
        for start, block in _windows(rows, config.window_rows, config.step_rows)
    ]
    sensitivity: list[dict[str, object]] = []
    for size in config.sensitivity_window_rows:
        step = max(1, size // 4)
        for start, block in _windows(rows, size, step):
            measured = _window_metrics(block, start, config, with_nulls=False)
            measured["sensitivity_window_rows"] = size
            sensitivity.append(measured)
    discontinuities = _discontinuities(rows, config.discontinuity_block_rows)
    transfers = _transfers(rows, config)
    context_path = output_directory / "exp003_operational_context.json"
    context_status: dict[str, object]
    if context_path.exists():
        context = json.loads(context_path.read_text(encoding="utf-8"))
        if (
            context["observations_sha256_colon_hex"]
            != manifest["observations"]["sha256_colon_hex"]
        ):
            raise ValueError(
                "operational context references a different observation snapshot"
            )
        context_status = {
            "path": context_path.name,
            "method_version": context["method_version"],
        }
    else:
        context_status = {"path": None, "status": "not collected"}
    result: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "evidence_status": "retrospective exploratory analysis of previously inspected observations",
        "deployed_analysis_revision_colon_hex": _revision_colon_hex(repo_root),
        "observations_sha256_colon_hex": manifest["observations"]["sha256_colon_hex"],
        "source": manifest["source"],
        "parameters": {
            "window_rows": config.window_rows,
            "step_rows": config.step_rows,
            "permutations": config.permutations,
            "permutation_seed": config.permutation_seed,
            "sensitivity_window_rows": list(config.sensitivity_window_rows),
            "discontinuity_block_rows": config.discontinuity_block_rows,
            "transport_blocks": config.transport_blocks,
            "smoothing_alpha": config.smoothing_alpha,
        },
        "null_models": {
            "global_outcome_shuffle": "destroys chronology and all context/status alignment",
            "conditional_calendar_shuffle": "shuffles weekday within model x calendar-month while preserving outcomes and row order",
        },
        "operational_context": context_status,
        "full_snapshot": _full_snapshot(rows),
        "rolling_windows": rolling,
        "sensitivity_windows": sensitivity,
        "discontinuities": discontinuities,
        "transfers": transfers,
    }
    _write_json(output_directory / OUTPUTS[0], result)
    _write_csv(output_directory / OUTPUTS[1], rolling)
    _write_csv(output_directory / OUTPUTS[2], sensitivity)
    _write_csv(output_directory / OUTPUTS[3], discontinuities)
    _write_csv(output_directory / OUTPUTS[4], transfers)
    _write_svg(output_directory / OUTPUTS[5], rolling)
    _write_summary(output_directory / OUTPUTS[6], result)
    return result


def collect_operational_context(
    run_directory: Path,
    output_directory: Path,
    repo_root: Path,
    config: OperationalContextConfig,
) -> dict[str, object]:
    """Collect aggregate context without reading text, identity, or payload fields."""
    hostname = socket.gethostname()
    if hostname != config.expected_host:
        raise RuntimeError(
            f"operational context collection requires host {config.expected_host!r}; got {hostname!r}"
        )
    manifest, _ = load_verified_observations(run_directory)
    first = manifest["source"]["first_observed_at_utc"]
    cutoff = manifest["source"]["last_observed_at_utc"]
    uri = f"file:{config.db_path}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        epoch_rows = connection.execute(
            """
            SELECT substr(first_seen_at, 1, 7) AS month,
                   COUNT(*) AS epochs,
                   COALESCE(SUM(observation_count), 0) AS observations,
                   COALESCE(SUM(CASE WHEN mismatch THEN 1 ELSE 0 END), 0) AS mismatches,
                   COUNT(DISTINCT provider) AS providers,
                   COUNT(DISTINCT observed_model) AS observed_models
            FROM provider_model_epochs
            WHERE last_seen_at <= ?
            GROUP BY month ORDER BY month
            """,
            (cutoff,),
        ).fetchall()
        epoch_coverage = connection.execute(
            """SELECT COUNT(*), MIN(first_seen_at), MAX(last_seen_at)
               FROM provider_model_epochs WHERE last_seen_at <= ?""",
            (cutoff,),
        ).fetchone()
        incident_rows = connection.execute(
            """
            SELECT substr(ts, 1, 7) AS month, COUNT(*) AS incidents,
                   COUNT(DISTINCT kind) AS kinds, COUNT(DISTINCT cluster) AS clusters,
                   COALESCE(SUM(CASE WHEN resolved THEN 1 ELSE 0 END), 0) AS resolved
            FROM central_incidents
            WHERE ts <= ?
            GROUP BY month ORDER BY month
            """,
            (cutoff,),
        ).fetchall()
        incident_coverage = connection.execute(
            """SELECT COUNT(*), MIN(ts), MAX(ts)
               FROM central_incidents WHERE ts <= ?""",
            (cutoff,),
        ).fetchone()
        connection.commit()
    finally:
        connection.close()
    commit_dates = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "log",
            "--all",
            "--format=%aI",
            f"--since={first}",
            f"--until={cutoff}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    commits_by_month = Counter(value[:7] for value in commit_dates if value)
    result: dict[str, object] = {
        "method_version": CONTEXT_METHOD_VERSION,
        "evidence_status": "aggregate operational context; not deployment or causal evidence",
        "deployed_collection_revision_colon_hex": _revision_colon_hex(repo_root),
        "observations_sha256_colon_hex": manifest["observations"]["sha256_colon_hex"],
        "observation_range": {"first": first, "cutoff": cutoff},
        "source": {
            "hostname": hostname,
            "database_path": str(config.db_path),
            "sqlite_mode": "mode=ro; PRAGMA query_only=ON",
        },
        "privacy_boundary": {
            "included": "monthly aggregate counts and coverage timestamps only",
            "excluded": [
                "message and incident text",
                "payloads",
                "run and session identifiers",
                "user and workspace identifiers",
                "secrets",
            ],
        },
        "provider_model_epochs": {
            "coverage": {
                "rows": epoch_coverage[0],
                "first": epoch_coverage[1],
                "last": epoch_coverage[2],
            },
            "monthly": [
                dict(
                    zip(
                        (
                            "month",
                            "epochs",
                            "observations",
                            "mismatches",
                            "providers",
                            "observed_models",
                        ),
                        row,
                        strict=True,
                    )
                )
                for row in epoch_rows
            ],
            "limitation": "coverage begins after the observation series; epochs are not deployment records",
        },
        "central_incidents": {
            "coverage": {
                "rows": incident_coverage[0],
                "first": incident_coverage[1],
                "last": incident_coverage[2],
            },
            "monthly": [
                dict(
                    zip(
                        ("month", "incidents", "kinds", "clusters", "resolved"),
                        row,
                        strict=True,
                    )
                )
                for row in incident_rows
            ],
            "limitation": "incident categories are aggregate operational records, not verified visible-run causes",
        },
        "git_author_dates": {
            "monthly": [
                {"month": month, "commits": commits_by_month[month]}
                for month in sorted(commits_by_month)
            ],
            "limitation": "author date measures repository history, not what revision was deployed when",
        },
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    _write_json(output_directory / "exp003_operational_context.json", result)
    return result


def audit_peak_cells(
    run_directory: Path, output_directory: Path, repo_root: Path
) -> dict[str, object]:
    """Preserve categorical cells selected after inspecting the primary result."""
    csv_path = output_directory / "exp003_live_peak_cells.csv"
    manifest_path = output_directory / "exp003_live_peak_cells_manifest.json"
    if csv_path.exists() or manifest_path.exists():
        raise FileExistsError("Investigation 3 peak audit already exists")
    source_manifest, rows = load_verified_observations(run_directory)
    primary = json.loads(
        (output_directory / "exp003_live_results.json").read_text(encoding="utf-8")
    )
    digest = source_manifest["observations"]["sha256_colon_hex"]
    if primary["observations_sha256_colon_hex"] != digest:
        raise ValueError("primary result references a different observation snapshot")
    peak = max(primary["rolling_windows"], key=lambda row: row["model_weekday_mi_bits"])
    start = int(peak["start_offset"])
    end = int(peak["end_offset_exclusive"])
    size = end - start
    periods = (
        ("preceding", max(0, start - size), start),
        ("selected_peak", start, end),
        ("following", end, min(len(rows), end + size)),
    )
    audit_rows: list[dict[str, object]] = []
    for period, period_start, period_end in periods:
        block = rows[period_start:period_end]
        grouped: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        for row in block:
            grouped[(row["model"], row["weekday_utc"])][row["status"]] += 1
        for (model, weekday), counts in sorted(grouped.items()):
            total = sum(counts.values())
            known = sum(
                counts[name]
                for name in ("completed", "interrupted", "failed", "cancelled")
            )
            audit_rows.append(
                {
                    "period": period,
                    "period_start_offset": period_start,
                    "period_end_offset_exclusive": period_end,
                    "first_observed_at_utc": block[0]["observed_at_utc"],
                    "last_observed_at_utc": block[-1]["observed_at_utc"],
                    "model": model,
                    "weekday_utc": weekday,
                    "rows": total,
                    "completed": counts["completed"],
                    "interrupted": counts["interrupted"],
                    "failed": counts["failed"],
                    "cancelled": counts["cancelled"],
                    "other_status": total - known,
                    "non_completed_fraction": (total - counts["completed"]) / total,
                }
            )
    _write_csv(csv_path, audit_rows)
    audit_manifest: dict[str, object] = {
        "method_version": "exp003.live.peak-cell-audit.1",
        "evidence_status": "post-hoc after primary rolling-window inspection",
        "selection_rule": "maximum primary model_weekday_mi_bits window",
        "selected_window": peak,
        "comparison_periods": "immediately preceding and following non-overlapping row intervals of equal size",
        "observations_sha256_colon_hex": digest,
        "deployed_audit_revision_colon_hex": _revision_colon_hex(repo_root),
        "output": csv_path.name,
        "rows": len(audit_rows),
    }
    _write_json(manifest_path, audit_manifest)
    return audit_manifest


def audit_peak_days(
    run_directory: Path, output_directory: Path, repo_root: Path
) -> dict[str, object]:
    """Preserve day/model counts after weekday cells motivate closer inspection."""
    csv_path = output_directory / "exp003_live_peak_day_models.csv"
    manifest_path = output_directory / "exp003_live_peak_day_models_manifest.json"
    if csv_path.exists() or manifest_path.exists():
        raise FileExistsError("Investigation 3 peak day audit already exists")
    source_manifest, rows = load_verified_observations(run_directory)
    primary = json.loads(
        (output_directory / "exp003_live_results.json").read_text(encoding="utf-8")
    )
    peak_audit = json.loads(
        (output_directory / "exp003_live_peak_cells_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    digest = source_manifest["observations"]["sha256_colon_hex"]
    if any(
        value != digest
        for value in (
            primary["observations_sha256_colon_hex"],
            peak_audit["observations_sha256_colon_hex"],
        )
    ):
        raise ValueError("peak audit inputs reference different observation snapshots")
    peak = peak_audit["selected_window"]
    block = rows[int(peak["start_offset"]) : int(peak["end_offset_exclusive"])]
    grouped: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    for row in block:
        grouped[(row["observed_at_utc"][:10], row["weekday_utc"], row["model"])][
            row["status"]
        ] += 1
    audit_rows: list[dict[str, object]] = []
    for (date_utc, weekday, model), counts in sorted(grouped.items()):
        total = sum(counts.values())
        known = sum(
            counts[name] for name in ("completed", "interrupted", "failed", "cancelled")
        )
        audit_rows.append(
            {
                "date_utc": date_utc,
                "weekday_utc": weekday,
                "model": model,
                "rows": total,
                "completed": counts["completed"],
                "interrupted": counts["interrupted"],
                "failed": counts["failed"],
                "cancelled": counts["cancelled"],
                "other_status": total - known,
                "non_completed_fraction": (total - counts["completed"]) / total,
            }
        )
    _write_csv(csv_path, audit_rows)
    audit_manifest: dict[str, object] = {
        "method_version": "exp003.live.peak-day-model-audit.1",
        "evidence_status": "post-hoc after primary and peak-cell inspection",
        "selection_rule": "dates inside the primary maximum model_weekday_mi_bits window",
        "selected_window": peak,
        "observations_sha256_colon_hex": digest,
        "deployed_audit_revision_colon_hex": _revision_colon_hex(repo_root),
        "output": csv_path.name,
        "rows": len(audit_rows),
    }
    _write_json(manifest_path, audit_manifest)
    return audit_manifest


def _write_summary(path: Path, result: dict[str, object]) -> None:
    rolling = result["rolling_windows"]
    assert isinstance(rolling, list)
    min_window = min(rolling, key=lambda row: row["model_weekday_mi_bits"])
    max_window = max(rolling, key=lambda row: row["model_weekday_mi_bits"])
    transfers = result["transfers"]
    assert isinstance(transfers, list)
    lines = [
        "# Live Investigation 3: measured summary",
        "",
        "**Evidence status:** retrospective exploration of the already inspected live snapshot.",
        "",
        f"Primary rolling windows: {len(rolling)} overlapping views.",
        f"Joint MI range: {min_window['model_weekday_mi_bits']:.6f} to {max_window['model_weekday_mi_bits']:.6f} bits.",
        "",
        "| Train → evaluate block | Base loss | Model loss | Model+weekday loss | Weekday gain vs model | Exact joint coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in transfers:
        lines.append(
            f"| {row['training_block']} → {row['evaluation_block']} "
            f"| {row['base_log_loss_bits']:.6f} | {row['model_log_loss_bits']:.6f} "
            f"| {row['model_weekday_log_loss_bits']:.6f} "
            f"| {row['weekday_gain_vs_model_bits']:.6f} "
            f"| {row['model_weekday_exact_state_coverage']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The full report must interpret composition, entropy, conditional-null,",
            "sensitivity, discontinuity, transport, and context coverage together.",
            "No row in this summary is independent confirmation.",
        ]
    )
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _write_svg(path: Path, rolling: list[dict[str, object]]) -> None:
    width, height = 1120, 650
    left, right, top, panel_height = 90, 1080, 78, 210
    plot_width = right - left
    max_mi = max(float(row["model_weekday_mi_bits"]) for row in rolling) * 1.08
    max_entropy = max(float(row["status_entropy_bits"]) for row in rolling) * 1.08

    def x(index: int) -> float:
        return left + plot_width * index / max(1, len(rolling) - 1)

    def y(value: float, maximum: float, panel_top: float) -> float:
        # Værn mod nul-skala: en kørsel hvor alle MI-værdier er nul (fx et lille
        # fixture uden association) gav ZeroDivisionError og væltede hele
        # SVG-genereringen. Nul-serie skal tegnes som en flad linje i bunden.
        scale = maximum if maximum > 0 else 1.0
        return panel_top + panel_height * (1 - value / scale)

    def polyline(field: str, maximum: float, panel_top: float, color: str) -> str:
        points = " ".join(
            f"{x(index):.1f},{y(float(row[field]), maximum, panel_top):.1f}"
            for index, row in enumerate(rolling)
        )
        return f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.5"/>'

    second_top = 390
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf6"/>',
        "<style>text{font-family:system-ui,sans-serif;fill:#20242b}.title{font-size:21px;font-weight:700}.label{font-size:13px}.small{font-size:11px}</style>",
        '<text x="28" y="32" class="title">Investigation 3 — changing observable relationships</text>',
        '<text x="28" y="52" class="small">2,000-row windows, 500-row step; overlapping retrospective views, not independent tests</text>',
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{panel_height}" fill="none" stroke="#bbb7ae"/>',
        f'<rect x="{left}" y="{second_top}" width="{plot_width}" height="{panel_height}" fill="none" stroke="#bbb7ae"/>',
        polyline("model_weekday_mi_bits", max_mi, top, "#6d28d9"),
        polyline("model_mi_bits", max_mi, top, "#2563eb"),
        polyline("bias_reference_adjusted_increment_bits", max_mi, top, "#d97706"),
        polyline("status_entropy_bits", max_entropy, second_top, "#0f766e"),
        f'<text x="{left}" y="{top - 10}" class="label">MI bits: joint (purple), model (blue), conditional-null-adjusted weekday increment (orange)</text>',
        f'<text x="{left}" y="{second_top - 10}" class="label">Terminal-status entropy (bits)</text>',
    ]
    for index in (0, len(rolling) // 2, len(rolling) - 1):
        row = rolling[index]
        label = str(row["first_observed_at_utc"])[:10]
        position = x(index)
        svg.extend(
            [
                f'<line x1="{position:.1f}" y1="{top}" x2="{position:.1f}" y2="{top + panel_height}" stroke="#ddd8cf" stroke-dasharray="3 4"/>',
                f'<line x1="{position:.1f}" y1="{second_top}" x2="{position:.1f}" y2="{second_top + panel_height}" stroke="#ddd8cf" stroke-dasharray="3 4"/>',
                f'<text x="{position:.1f}" y="{height - 20}" class="small" text-anchor="middle">{label}</text>',
            ]
        )
    svg.append("</svg>")
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(svg) + "\n")
