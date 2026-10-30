"""Read-only, privacy-limited extraction from deployed Jarvis visible runs."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import socket
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

METHOD_VERSION = "live-visible-runs.extract.2"
FIELDS = (
    "observation_id",
    "source_row_id",
    "observed_at_utc",
    "timestamp_basis",
    "provider",
    "model",
    "lane",
    "profile_name",
    "capability_presence",
    "hour_bin_utc",
    "weekday_utc",
    "status",
)


@dataclass(frozen=True)
class LiveExtractionConfig:
    db_path: Path = Path("/home/bs/.jarvis-v2/state/jarvis.db")
    expected_host: str = "Jarvis"


def colon_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).digest().hex(":")


def _normalize(value: object) -> str:
    text = "" if value is None else str(value).strip()
    return text or "missing"


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _git_revision(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def extract_live_visible_runs(
    output: Path, config: LiveExtractionConfig, repo_root: Path
) -> None:
    """Create one high-water-bounded extract using a read-only transaction."""
    hostname = socket.gethostname()
    if hostname != config.expected_host:
        raise RuntimeError(
            f"live extraction requires host {config.expected_host!r}; got {hostname!r}"
        )
    output.mkdir(parents=True, exist_ok=False)
    uri = f"file:{config.db_path}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        high_water = connection.execute("SELECT MAX(id) FROM visible_runs").fetchone()[
            0
        ]
        if high_water is None:
            raise ValueError("live visible_runs table is empty")
        rows = connection.execute(
            """
            SELECT id, started_at, finished_at, provider, model, lane, profile_name,
                   capability_id, status
            FROM visible_runs
            WHERE id <= ?
            ORDER BY id
            """,
            (high_water,),
        ).fetchall()
        connection.commit()
    finally:
        connection.close()
    observations = output / "observations.csv"
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    with observations.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for (
            row_id,
            started_at,
            finished_at,
            provider,
            model,
            lane,
            profile,
            capability,
            status,
        ) in rows:
            timestamp_source = started_at or finished_at
            if not timestamp_source:
                raise ValueError(f"visible_runs row {row_id} has no usable timestamp")
            timestamp = _parse_timestamp(str(timestamp_source))
            timestamp_text = timestamp.isoformat()
            first_timestamp = first_timestamp or timestamp_text
            last_timestamp = timestamp_text
            hour_start = (timestamp.hour // 6) * 6
            writer.writerow(
                {
                    "observation_id": f"visible-run:{row_id}",
                    "source_row_id": row_id,
                    "observed_at_utc": timestamp_text,
                    "timestamp_basis": (
                        "started_at" if started_at else "finished_at_fallback"
                    ),
                    "provider": _normalize(provider),
                    "model": _normalize(model),
                    "lane": _normalize(lane),
                    "profile_name": _normalize(profile),
                    "capability_presence": "present" if capability else "absent",
                    "hour_bin_utc": f"{hour_start:02d}-{hour_start + 5:02d}",
                    "weekday_utc": timestamp.strftime("%A"),
                    "status": _normalize(status),
                }
            )
    _write_json(
        output / "live_manifest.json",
        {
            "method_version": METHOD_VERSION,
            "source": {
                "hostname": hostname,
                "database_path": str(config.db_path),
                "sqlite_mode": "mode=ro; PRAGMA query_only=ON",
                "table": "visible_runs",
                "high_water_id": high_water,
                "snapshot_rows": len(rows),
                "first_observed_at_utc": first_timestamp,
                "last_observed_at_utc": last_timestamp,
            },
            "privacy_boundary": {
                "included": list(FIELDS),
                "excluded": [
                    "text_preview",
                    "error",
                    "run_id",
                    "user_id",
                    "workspace_name",
                ],
            },
            "transformations": {
                "missing_values": "normalized to literal 'missing'",
                "observed_at_utc": "started_at, or finished_at when started_at is absent",
                "timestamp_basis": "records which timestamp supplied observed_at_utc",
                "hour_bin_utc": "six-hour band derived from observed_at_utc",
                "weekday_utc": "English weekday derived from observed_at_utc",
                "capability_presence": "presence only; capability identifier excluded",
            },
            "deployed_git_revision": _git_revision(repo_root),
            "runtime": {
                "python": platform.python_version(),
                "sqlite": sqlite3.sqlite_version,
            },
            "observations": {
                "path": "observations.csv",
                "sha256_colon_hex": colon_sha256(observations),
            },
        },
    )


def load_verified_observations(
    run_directory: Path,
) -> tuple[dict, list[dict[str, str]]]:
    manifest = json.loads(
        (run_directory / "live_manifest.json").read_text(encoding="utf-8")
    )
    path = run_directory / manifest["observations"]["path"]
    if colon_sha256(path) != manifest["observations"]["sha256_colon_hex"]:
        raise ValueError("live observation digest does not match manifest")
    with path.open(newline="", encoding="utf-8") as handle:
        return manifest, list(csv.DictReader(handle))
