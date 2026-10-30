#!/usr/bin/env python3
"""Discover and confirm perspectives in chronological deployed observations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_002_live import (  # noqa: E402
    LiveExperiment002Config,
    analyze_live_experiment_002,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--permutations", type=int, default=250)
    parser.add_argument("--source-blocks", type=int, default=5)
    parser.add_argument("--maximum-lag", type=int, default=12)
    args = parser.parse_args()
    results = analyze_live_experiment_002(
        args.run,
        LiveExperiment002Config(
            source_blocks=args.source_blocks,
            permutations=args.permutations,
            maximum_lag=args.maximum_lag,
        ),
    )
    for source_id, measured in results["sources"].items():
        selected = measured["selected_candidate"]
        print(
            source_id,
            selected["name"],
            f"discovery={selected['discovery_mi_bits']:.6f}",
            f"confirmation={selected['confirmation_mi_bits']:.6f}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
