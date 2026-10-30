#!/usr/bin/env python3
"""Measure three fixed perspectives on the deployed visible-run extract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_001_live import (  # noqa: E402
    LiveExperiment001Config,
    analyze_live_experiment_001,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--permutations", type=int, default=500)
    args = parser.parse_args()
    results = analyze_live_experiment_001(
        args.run, LiveExperiment001Config(permutations=args.permutations)
    )
    for name, measured in results["perspectives"].items():
        print(name, f"{measured['observed_mutual_information_bits']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
