"""Frozen forecast preparation and privacy-limited prospective evaluation."""

from __future__ import annotations

import csv
import json
import math
import platform
import socket
import sqlite3
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .experiment_004_continuity import (
    STATUSES,
    _block_state,
    _distance,
    _partition,
)
from .live_visible_runs import colon_sha256, load_verified_observations

FORECAST_METHOD_VERSION = "exp004.prospective.forecast.1"
EVALUATION_METHOD_VERSION = "exp004.prospective.evaluate.1"
PROSPECTIVE_STATUSES = (*STATUSES, "other")


@dataclass(frozen=True)
class ProspectiveEvaluationConfig:
    db_path: Path = Path("/home/bs/.jarvis-v2/state/jarvis.db")
    expected_host: str = "Jarvis"


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


def _category(status: str) -> str:
    return status if status in STATUSES else "other"


def _distribution(statuses: list[str], alpha: float) -> dict[str, float]:
    counts = Counter(_category(status) for status in statuses)
    total = len(statuses) + alpha * len(PROSPECTIVE_STATUSES)
    return {status: (counts[status] + alpha) / total for status in PROSPECTIVE_STATUSES}


def _prospective_scores(
    statuses: list[str], distribution: dict[str, float]
) -> tuple[float, float]:
    categories = [_category(status) for status in statuses]
    log_loss = -sum(math.log2(distribution[status]) for status in categories) / len(
        categories
    )
    brier = sum(
        sum(
            (distribution[candidate] - float(status == candidate)) ** 2
            for candidate in PROSPECTIVE_STATUSES
        )
        for status in categories
    ) / len(categories)
    return log_loss, brier


def prepare_prospective_forecast(
    run_directory: Path,
    analysis_directory: Path,
    output_path: Path,
    repo_root: Path,
) -> dict[str, object]:
    """Freeze forecasts using only the already inspected historical snapshot."""
    if output_path.exists():
        raise FileExistsError(output_path)
    manifest, rows = load_verified_observations(run_directory)
    analysis = json.loads(
        (analysis_directory / "exp004_live_results.json").read_text(encoding="utf-8")
    )
    digest = manifest["observations"]["sha256_colon_hex"]
    if analysis["observations_sha256_colon_hex"] != digest:
        raise ValueError("analysis and observations have different digests")
    block_rows = int(analysis["parameters"]["block_rows"])
    alpha = float(analysis["parameters"]["smoothing_alpha"])
    blocks = _partition(rows, block_rows)
    states = [_block_state(block, index) for index, block in enumerate(blocks)]
    current_index = len(states) - 1
    eligible = range(0, current_index - 1)
    forecasts: dict[str, dict[str, object]] = {
        "expanding_prevalence": {
            "distribution": _distribution([row["status"] for row in rows], alpha),
            "source": "all 25,000 historical observations",
        },
        "previous_block": {
            "distribution": _distribution([row["status"] for row in blocks[-1]], alpha),
            "source": f"historical block {len(blocks)}",
        },
    }
    for representation in ("model_composition", "operational_relation"):
        analog_index = min(
            eligible,
            key=lambda index: _distance(
                states[current_index], states[index], representation
            ),
        )
        following_index = analog_index + 1
        forecasts[f"recurrence_{representation}"] = {
            "distribution": _distribution(
                [row["status"] for row in blocks[following_index]], alpha
            ),
            "analog_state_block": analog_index + 1,
            "analog_following_block": following_index + 1,
            "analog_distance": _distance(
                states[current_index], states[analog_index], representation
            ),
            "source": "status distribution following the frozen historical analog",
        }
    result: dict[str, object] = {
        "method_version": FORECAST_METHOD_VERSION,
        "status": "frozen before availability or outcome query above source high-water",
        "primary_comparison": "previous_block versus expanding_prevalence",
        "primary_score_difference": "previous_block minus expanding_prevalence; negative favors previous_block",
        "secondary_comparisons": [
            "recurrence_model_composition",
            "recurrence_operational_relation",
        ],
        "source_observations_sha256_colon_hex": digest,
        "source_high_water_id": int(manifest["source"]["high_water_id"]),
        "source_rows": len(rows),
        "source_last_observed_at_utc": manifest["source"]["last_observed_at_utc"],
        "target": {
            "rows": block_rows,
            "selection": "first database-ordered visible_runs rows above source_high_water_id",
            "interim_outcome_inspection": "prohibited",
        },
        "smoothing_alpha": alpha,
        "statuses": list(PROSPECTIVE_STATUSES),
        "forecasts": forecasts,
        "prepared_on_deployed_revision_colon_hex": _revision_colon_hex(repo_root),
    }
    _write_json(output_path, result)
    return result


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _availability_result(
    forecast: dict[str, object],
    forecast_path: Path,
    available: int,
    high_water: int,
    config: ProspectiveEvaluationConfig,
    repo_root: Path,
) -> dict[str, object]:
    target = forecast["target"]
    assert isinstance(target, dict)
    return {
        "method_version": EVALUATION_METHOD_VERSION,
        "status": "pending_insufficient_rows",
        "available_rows": available,
        "required_rows": int(target["rows"]),
        "current_high_water_id": high_water,
        "source_high_water_id": int(forecast["source_high_water_id"]),
        "outcomes_read": False,
        "forecast_method_version": forecast["method_version"],
        "forecast_sha256_colon_hex": colon_sha256(forecast_path),
        "deployed_check_revision_colon_hex": _revision_colon_hex(repo_root),
        "source": {
            "hostname": socket.gethostname(),
            "database_path": str(config.db_path),
            "sqlite_mode": "mode=ro; PRAGMA query_only=ON",
            "queries": "COUNT(*) and MAX(id) only above frozen high-water",
        },
    }


def evaluate_prospective(
    forecast_path: Path,
    output_directory: Path,
    repo_root: Path,
    config: ProspectiveEvaluationConfig,
) -> dict[str, object]:
    """Read no outcomes until the complete frozen target is available."""
    hostname = socket.gethostname()
    if hostname != config.expected_host:
        raise RuntimeError(
            f"prospective evaluation requires host {config.expected_host!r}; got {hostname!r}"
        )
    output_directory.mkdir(parents=True, exist_ok=True)
    status_path = output_directory / "exp004_prospective_status.json"
    if status_path.exists():
        raise FileExistsError(status_path)
    forecast = json.loads(forecast_path.read_text(encoding="utf-8"))
    source_high_water = int(forecast["source_high_water_id"])
    target = forecast["target"]
    assert isinstance(target, dict)
    required = int(target["rows"])
    uri = f"file:{config.db_path}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        available, high_water = connection.execute(
            "SELECT COUNT(*), COALESCE(MAX(id), ?) FROM visible_runs WHERE id > ?",
            (source_high_water, source_high_water),
        ).fetchone()
        if available < required:
            connection.commit()
            result = _availability_result(
                forecast, forecast_path, available, high_water, config, repo_root
            )
            _write_json(status_path, result)
            return result
        rows = connection.execute(
            """
            SELECT id, started_at, finished_at, status
            FROM visible_runs WHERE id > ? ORDER BY id LIMIT ?
            """,
            (source_high_water, required),
        ).fetchall()
        connection.commit()
    finally:
        connection.close()
    observations_path = output_directory / "exp004_prospective_observations.csv"
    observations: list[dict[str, object]] = []
    for index, (row_id, started_at, finished_at, status) in enumerate(rows, start=1):
        timestamp_source = started_at or finished_at
        if not timestamp_source:
            raise ValueError(f"prospective row {row_id} has no usable timestamp")
        observations.append(
            {
                "observation_index": index,
                "source_row_id": row_id,
                "observed_at_utc": _parse_timestamp(str(timestamp_source)).isoformat(),
                "timestamp_basis": (
                    "started_at" if started_at else "finished_at_fallback"
                ),
                "status": str(status).strip() or "missing",
            }
        )
    with observations_path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(observations[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(observations)
    statuses = [str(row["status"]) for row in observations]
    measurements: dict[str, dict[str, float]] = {}
    forecasts = forecast["forecasts"]
    assert isinstance(forecasts, dict)
    for name, details in forecasts.items():
        assert isinstance(details, dict)
        distribution = details["distribution"]
        assert isinstance(distribution, dict)
        numeric_distribution = {
            key: float(value) for key, value in distribution.items()
        }
        log_loss, brier = _prospective_scores(statuses, numeric_distribution)
        measurements[name] = {
            "log_loss_bits": log_loss,
            "brier_score": brier,
        }
    primary = (
        measurements["previous_block"]["log_loss_bits"]
        - measurements["expanding_prevalence"]["log_loss_bits"]
    )
    result = {
        "method_version": EVALUATION_METHOD_VERSION,
        "status": "complete_designated_independent_evaluation",
        "available_rows_at_snapshot": available,
        "evaluated_rows": required,
        "source_high_water_id": source_high_water,
        "evaluation_high_water_id": int(rows[-1][0]),
        "forecast_method_version": forecast["method_version"],
        "forecast_sha256_colon_hex": colon_sha256(forecast_path),
        "observations_sha256_colon_hex": colon_sha256(observations_path),
        "deployed_evaluation_revision_colon_hex": _revision_colon_hex(repo_root),
        "observed_status_counts": dict(sorted(Counter(statuses).items())),
        "scored_category_counts": dict(
            sorted(Counter(_category(status) for status in statuses).items())
        ),
        "measurements": measurements,
        "primary_log_loss_difference_previous_minus_expanding": primary,
        "source": {
            "hostname": hostname,
            "database_path": str(config.db_path),
            "sqlite_mode": "mode=ro; PRAGMA query_only=ON",
        },
        "privacy_boundary": {
            "included": list(observations[0]),
            "excluded": "text, errors, run/session/user/workspace IDs, model, provider, capability, payloads",
        },
        "runtime": {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
        },
    }
    _write_json(status_path, result)
    return result
