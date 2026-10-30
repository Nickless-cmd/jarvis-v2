from __future__ import annotations

import csv
import socket
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from feltteori_research.experiment_001_live import (
    LiveExperiment001Config,
    analyze_live_experiment_001,
)
from feltteori_research.experiment_002_live import (
    LiveExperiment002Config,
    analyze_live_experiment_002,
    audit_live_candidate_scores,
    candidate_catalog,
)
from feltteori_research.live_visible_runs import (
    LiveExtractionConfig,
    extract_live_visible_runs,
    load_verified_observations,
)


def build_visible_runs_db(path: Path, rows: int = 240) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE visible_runs (
            id INTEGER PRIMARY KEY,
            run_id TEXT,
            lane TEXT,
            provider TEXT,
            model TEXT,
            status TEXT,
            started_at TEXT,
            finished_at TEXT,
            text_preview TEXT,
            error TEXT,
            capability_id TEXT,
            user_id TEXT,
            workspace_name TEXT,
            profile_name TEXT
        )
        """
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(rows):
        provider = "alpha" if index % 2 == 0 else "beta"
        model = "m1" if index % 4 < 2 else "m2"
        status = "completed" if provider == "alpha" else "failed"
        connection.execute(
            """
            INSERT INTO visible_runs (
                run_id, lane, provider, model, status, started_at, finished_at,
                text_preview, error, capability_id, user_id, workspace_name,
                profile_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"sensitive-run-{index}",
                "primary",
                provider,
                model,
                status,
                None if index == 7 else (start + timedelta(hours=index)).isoformat(),
                (start + timedelta(hours=index, minutes=1)).isoformat(),
                "private text",
                "private error",
                "tool:x" if index % 3 == 0 else None,
                "private-user",
                "private-workspace",
                "visible-owner",
            ),
        )
    connection.commit()
    connection.close()


def extract_fixture(tmp_path: Path, rows: int = 240) -> Path:
    db_path = tmp_path / "jarvis.db"
    build_visible_runs_db(db_path, rows)
    output = tmp_path / "extract"
    extract_live_visible_runs(
        output,
        LiveExtractionConfig(db_path=db_path, expected_host=socket.gethostname()),
        Path(__file__).resolve().parents[2],
    )
    return output


def test_live_extractor_is_host_gated_and_privacy_limited(tmp_path: Path) -> None:
    db_path = tmp_path / "jarvis.db"
    build_visible_runs_db(db_path, 40)
    with pytest.raises(RuntimeError, match="requires host"):
        extract_live_visible_runs(
            tmp_path / "rejected",
            LiveExtractionConfig(db_path=db_path, expected_host="not-this-host"),
            Path(__file__).resolve().parents[2],
        )

    output = tmp_path / "accepted"
    extract_live_visible_runs(
        output,
        LiveExtractionConfig(db_path=db_path, expected_host=socket.gethostname()),
        Path(__file__).resolve().parents[2],
    )
    manifest, rows = load_verified_observations(output)
    assert manifest["source"]["high_water_id"] == 40
    assert len(rows) == 40
    assert "text_preview" not in rows[0]
    assert "user_id" not in rows[0]
    assert "run_id" not in rows[0]
    assert "private" not in (output / "observations.csv").read_text(encoding="utf-8")
    assert rows[7]["timestamp_basis"] == "finished_at_fallback"


def test_live_experiment_001_measures_fixed_perspectives(tmp_path: Path) -> None:
    output = extract_fixture(tmp_path)
    results = analyze_live_experiment_001(
        output, LiveExperiment001Config(permutations=12, permutation_seed=7)
    )
    assert results["descriptive"]["rows"] == 240
    assert (
        results["perspectives"]["provider_access"]["observed_mutual_information_bits"]
        > 0.9
    )
    with pytest.raises(FileExistsError):
        analyze_live_experiment_001(output, LiveExperiment001Config(permutations=2))


def test_live_experiment_002_freezes_candidates_on_later_rows(tmp_path: Path) -> None:
    output = extract_fixture(tmp_path, 400)
    results = analyze_live_experiment_002(
        output,
        LiveExperiment002Config(
            source_blocks=4,
            permutations=8,
            maximum_lag=3,
            permutation_seed=11,
        ),
    )
    assert results["candidate_count"] == len(candidate_catalog(3)) == 31
    assert len(results["sources"]) == 4
    for source in results["sources"].values():
        selected = source["selected_candidate"]
        assert "provider" in selected["variables"]
        assert selected["confirmation_mi_bits"] > 0.9
    assert (output / "exp002_live_opaque_summary.md").exists()
    assert (output / "exp002_live_revealed_summary.md").exists()
    assert (output / "exp002_live_selected.svg").exists()
    audit_live_candidate_scores(output, Path(__file__).resolve().parents[2])
    with (output / "exp002_live_candidate_scores.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        audited = list(csv.DictReader(handle))
    assert len(audited) == 4 * 31
    assert sum(int(row["selected_in_primary"]) for row in audited) == 4


def test_live_digest_tampering_is_rejected(tmp_path: Path) -> None:
    output = extract_fixture(tmp_path, 40)
    observations = output / "observations.csv"
    observations.write_text(
        observations.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="digest"):
        load_verified_observations(output)
