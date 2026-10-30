#!/usr/bin/env python3
"""Command-line entry point for experiment 001."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research import RunConfig, run_experiment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=20261030)
    parser.add_argument("--context-block-size", type=int, default=32)
    parser.add_argument("--relation-noise", type=float, default=0.10)
    parser.add_argument("--permutations", type=int, default=500)
    args = parser.parse_args()
    config = RunConfig(
        rows_per_source=args.rows,
        seed=args.seed,
        context_block_size=args.context_block_size,
        relation_noise=args.relation_noise,
        permutations=args.permutations,
    )
    results = run_experiment(args.output, config)
    print(f"Created preserved run: {args.output}")
    for source, measured in results["sources"].items():
        values = measured["perspectives"]
        print(
            source,
            {
                name: round(value["observed_mutual_information_bits"], 6)
                for name, value in values.items()
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
