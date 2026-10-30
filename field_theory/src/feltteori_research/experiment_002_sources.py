"""Opaque source generation for Investigation 2.

The discovery analyzer deliberately does not import this module.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

METHOD_VERSION = "exp002.generate.1"


@dataclass(frozen=True)
class GenerationConfig:
    seed: int = 202610302
    discovery_rows: int = 1024
    confirmation_rows: int = 2048

    def validate(self) -> None:
        if self.discovery_rows < 32 or self.confirmation_rows < 32:
            raise ValueError("each partition must contain at least 32 rows")


def _stable_seed(seed: int, source: str, partition: str) -> int:
    material = f"{seed}|{source}|{partition}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _source_id(seed: int, name: str) -> str:
    material = f"opaque|{seed}|{name}".encode()
    return f"S-{hashlib.sha256(material).hexdigest()[:4].upper()}"


def _flip(value: int, probability: float, rng: random.Random) -> int:
    return value ^ int(rng.random() < probability)


def _independent(
    values: tuple[int, ...],
    context: int,
    index: int,
    partition: str,
    rng: random.Random,
) -> int:
    del values, context, index, partition
    return rng.randrange(2)


def _triple_relation(
    values: tuple[int, ...],
    context: int,
    index: int,
    partition: str,
    rng: random.Random,
) -> int:
    del context, index, partition
    return _flip(values[0] ^ values[1] ^ values[2], 0.15, rng)


def _context_relation(
    values: tuple[int, ...],
    context: int,
    index: int,
    partition: str,
    rng: random.Random,
) -> int:
    del index, partition
    return _flip(values[0] ^ context, 0.12, rng)


def _digest_process(
    values: tuple[int, ...],
    context: int,
    index: int,
    partition: str,
    rng: random.Random,
) -> int:
    del values, context, index, partition
    material = rng.getrandbits(256).to_bytes(32, "big")
    return hashlib.sha256(material).digest()[0] & 1


def _partition_specific(
    values: tuple[int, ...],
    context: int,
    index: int,
    partition: str,
    rng: random.Random,
) -> int:
    del context, index
    if partition == "discovery":
        return _flip(values[2], 0.10, rng)
    return rng.randrange(2)


SourceFunction = Callable[[tuple[int, ...], int, int, str, random.Random], int]

SOURCES: dict[str, tuple[SourceFunction, dict[str, object]]] = {
    "independent_prng": (
        _independent,
        {
            "description": "Independent pseudorandom outcome and recorded variables.",
            "intended_contrast": "Search-generated apparent structure without a planted relation.",
        },
    ),
    "noisy_triple_xor": (
        _triple_relation,
        {
            "description": "Outcome is noisy XOR of v0, v1, and v2.",
            "noise_probability": 0.15,
            "intended_contrast": "Higher-order relation with weak pairwise visibility.",
        },
    ),
    "noisy_context_xor": (
        _context_relation,
        {
            "description": "Outcome is noisy XOR of v0 and context.",
            "noise_probability": 0.12,
            "intended_contrast": "A relation visible only when context participates.",
        },
    ),
    "deterministic_digest": (
        _digest_process,
        {
            "description": "Outcome is a deterministic SHA-256-derived bit with hidden input state.",
            "intended_contrast": "Determinism that may remain random-looking under available perspectives.",
        },
    ),
    "partition_specific_relation": (
        _partition_specific,
        {
            "description": "Discovery outcome is a noisy copy of v2; confirmation outcome is independent.",
            "discovery_noise_probability": 0.10,
            "intended_contrast": "Detectable sample-specific structure that should not generalize.",
        },
    ),
}


def _colon_sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).digest()
    return digest.hex(":")


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def generate_dataset(output: Path, config: GenerationConfig) -> None:
    """Create a new raw-data bundle; never overwrite an existing directory."""
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    source_ids = {name: _source_id(config.seed, name) for name in SOURCES}
    observations = output / "observations.csv"
    fields = [
        "observation_id",
        "source_id",
        "partition",
        "index",
        "v0",
        "v1",
        "v2",
        "v3",
        "context",
        "outcome",
    ]
    with observations.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for source_name, (source_function, _) in SOURCES.items():
            source_id = source_ids[source_name]
            for partition, count in (
                ("discovery", config.discovery_rows),
                ("confirmation", config.confirmation_rows),
            ):
                rng = random.Random(_stable_seed(config.seed, source_name, partition))
                for index in range(count):
                    values = tuple(rng.randrange(2) for _ in range(4))
                    context = rng.randrange(2)
                    outcome = source_function(values, context, index, partition, rng)
                    writer.writerow(
                        {
                            "observation_id": f"{source_id}:{partition}:{index:06d}",
                            "source_id": source_id,
                            "partition": partition,
                            "index": index,
                            "v0": values[0],
                            "v1": values[1],
                            "v2": values[2],
                            "v3": values[3],
                            "context": context,
                            "outcome": outcome,
                        }
                    )
    digest = _colon_sha256(observations)
    _write_json(
        output / "generation_manifest.json",
        {
            "experiment": "exp_002_discovery",
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
                "rows": len(SOURCES)
                * (config.discovery_rows + config.confirmation_rows),
                "sha256_colon_hex": digest,
            },
            "analysis_visible_source_ids": sorted(source_ids.values()),
            "blinding_note": "The analyzer must not read source_key.json.",
        },
    )
    _write_json(
        output / "source_key.json",
        {
            "status": "reveal only after results.json exists",
            "blinding_limit": "Procedural only; code author designed both source and candidate families.",
            "sources": {
                source_ids[name]: {"generator": name, **metadata}
                for name, (_, metadata) in SOURCES.items()
            },
        },
    )
