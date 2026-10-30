from __future__ import annotations

import json
from pathlib import Path

import pytest

from feltteori_research.experiment_002_discovery import (
    DiscoveryConfig,
    analyze_dataset,
    candidate_catalog,
    reveal_sources,
)
from feltteori_research.experiment_002_sources import (
    GenerationConfig,
    generate_dataset,
)


def test_candidate_catalog_is_declared_and_unique() -> None:
    candidates = candidate_catalog(12)
    names = [candidate.name for candidate in candidates]
    assert len(candidates) == 52
    assert len(names) == len(set(names))
    assert "xor(v0,v1,v2)" in names
    assert "outcome_lag(12)" in names


def test_analysis_is_reproducible_without_source_key(tmp_path: Path) -> None:
    generation = GenerationConfig(seed=41, discovery_rows=128, confirmation_rows=256)
    discovery = DiscoveryConfig(permutations=8, maximum_lag=4, permutation_seed=42)
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_dataset(first, generation)
    generate_dataset(second, generation)
    (second / "source_key.json").unlink()

    analyze_dataset(first, discovery)
    analyze_dataset(second, discovery)

    assert (first / "observations.csv").read_bytes() == (
        second / "observations.csv"
    ).read_bytes()
    assert (first / "results.json").read_bytes() == (
        second / "results.json"
    ).read_bytes()


def test_known_relations_are_found_then_independently_examined(tmp_path: Path) -> None:
    run = tmp_path / "run"
    generate_dataset(
        run, GenerationConfig(seed=202610302, discovery_rows=512, confirmation_rows=768)
    )
    results = analyze_dataset(
        run, DiscoveryConfig(permutations=12, maximum_lag=6, permutation_seed=99)
    )
    source_key = json.loads((run / "source_key.json").read_text(encoding="utf-8"))
    by_generator = {
        details["generator"]: results["sources"][source_id]
        for source_id, details in source_key["sources"].items()
    }

    triple = by_generator["noisy_triple_xor"]["selected_candidate"]
    contextual = by_generator["noisy_context_xor"]["selected_candidate"]
    unstable = by_generator["partition_specific_relation"]["selected_candidate"]
    assert triple["name"] == "xor(v0,v1,v2)"
    assert triple["confirmation_mi_bits"] > 0.2
    assert set(contextual["variables"]) == {"v0", "context"}
    assert contextual["family"] in {"joint", "xor"}
    assert contextual["confirmation_mi_bits"] > 0.3
    assert "v2" in unstable["variables"]
    assert unstable["discovery_mi_bits"] > 0.3
    assert unstable["confirmation_mi_bits"] < 0.02


def test_digest_mismatch_and_output_overwrite_are_rejected(tmp_path: Path) -> None:
    run = tmp_path / "run"
    config = GenerationConfig(seed=3, discovery_rows=64, confirmation_rows=64)
    generate_dataset(run, config)
    with pytest.raises(FileExistsError):
        generate_dataset(run, config)

    observations = run / "observations.csv"
    observations.write_text(
        observations.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="digest"):
        analyze_dataset(run, DiscoveryConfig(permutations=2, maximum_lag=2))


def test_analysis_and_reveal_are_append_only(tmp_path: Path) -> None:
    run = tmp_path / "run"
    generate_dataset(
        run, GenerationConfig(seed=5, discovery_rows=64, confirmation_rows=64)
    )
    config = DiscoveryConfig(permutations=2, maximum_lag=2)
    analyze_dataset(run, config)
    reveal_sources(run)

    with pytest.raises(FileExistsError):
        analyze_dataset(run, config)
    with pytest.raises(FileExistsError):
        reveal_sources(run)
