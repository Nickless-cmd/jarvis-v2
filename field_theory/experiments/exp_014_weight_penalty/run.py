#!/usr/bin/env python3
"""Entrypoint for Investigation 14 — why weighting loses to the best single expert."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_014_weight_penalty import run_investigation  # noqa: E402

DEFAULT_SILSO = (
    PROJECT_ROOT
    / "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
)
DEFAULT_NOAA = PROJECT_ROOT / "artifacts/exp_006_order/noaa_20261030_v2/noaa_co2_mm_mlo.csv"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silso", default=DEFAULT_SILSO, type=Path)
    parser.add_argument("--noaa", default=DEFAULT_NOAA, type=Path)
    parser.add_argument("--output", default=None, type=Path)
    args = parser.parse_args(argv)

    output = args.output
    if output is None:
        base = PROJECT_ROOT / "artifacts/exp_014_weight_penalty"
        index = 1
        while (base / f"run_20261125_v{index}").exists():
            index += 1
        output = base / f"run_20261125_v{index}"

    results = run_investigation(args.silso, args.noaa, output)
    print(f"verdict: {results['verdict']}")
    print(f"conditions: {results['conditions']}")
    print(f"controls: {results['controls']}")
    print(f"aggregate: {results['aggregate']}")
    print(f"residual: {results['residual']}")
    print(f"warm_up_spread: {results['warm_up_spread']:.4f}")
    print(f"best_alpha: {results['best_alpha']} interior_gain: {results['interior_gain']:.4f}")
    for entry in results["concentration"]:
        print(
            f"  top_weight {entry['low']:.2f}-{entry['high']:.2f}: "
            f"n={entry['months']:>5} median={entry['median_ratio']:.4f}"
        )
    for entry in results["alpha_curve"]:
        print(
            f"  alpha={entry['alpha']:<5} mean={entry['mean_ratio']:.4f} "
            f"median={entry['median_ratio']:.4f}"
        )
    print(f"output: {output}")


if __name__ == "__main__":
    main()
