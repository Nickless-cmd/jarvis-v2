from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from feltteori_research import RunConfig, run_experiment
from feltteori_research.metrics import entropy, mutual_information


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).digest().hex(":")


def test_discrete_metrics_have_known_values() -> None:
    assert entropy([0, 0, 1, 1]) == pytest.approx(1.0)
    assert mutual_information([0, 0, 1, 1], [0, 0, 1, 1]) == pytest.approx(1.0)
    assert mutual_information([0, 0, 1, 1], [0, 1, 0, 1]) == pytest.approx(0.0)


def test_run_is_reproducible_and_records_raw_digest(tmp_path: Path) -> None:
    config = RunConfig(
        rows_per_source=128, seed=7, context_block_size=8, permutations=12
    )
    first = tmp_path / "first"
    second = tmp_path / "second"
    run_experiment(first, config)
    run_experiment(second, config)

    assert (first / "observations.csv").read_bytes() == (
        second / "observations.csv"
    ).read_bytes()
    assert (first / "results.json").read_bytes() == (
        second / "results.json"
    ).read_bytes()
    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    results = json.loads((first / "results.json").read_text(encoding="utf-8"))
    digest = file_digest(first / "observations.csv")
    assert manifest["raw_observations"]["sha256_colon_hex"] == digest
    assert results["raw_observations_sha256_colon_hex"] == digest


def test_existing_run_cannot_be_overwritten(tmp_path: Path) -> None:
    destination = tmp_path / "preserved"
    config = RunConfig(rows_per_source=16, permutations=2)
    run_experiment(destination, config)

    with pytest.raises(FileExistsError):
        run_experiment(destination, config)


def test_constructed_relation_is_visible_only_with_context_access(
    tmp_path: Path,
) -> None:
    results = run_experiment(
        tmp_path / "run",
        RunConfig(
            rows_per_source=1024,
            seed=19,
            context_block_size=16,
            relation_noise=0.1,
            permutations=20,
        ),
    )
    perspectives = results["sources"]["context_relation"]["perspectives"]
    contextual = perspectives["cue_context_access"]["observed_mutual_information_bits"]
    cue_only = perspectives["cue_access"]["observed_mutual_information_bits"]
    assert contextual > 0.3
    assert cue_only < 0.05
