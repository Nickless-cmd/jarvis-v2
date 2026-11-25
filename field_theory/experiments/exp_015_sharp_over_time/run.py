#!/usr/bin/env python3
"""Entrypoint for Investigation 15 — sharpening on the median over time."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_015_sharp_over_time import run_investigation  # noqa: E402

DEFAULT_SILSO = (
    PROJECT_ROOT
    / "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
)
DEFAULT_NOAA = (
    PROJECT_ROOT / "artifacts/exp_006_order/noaa_20261030_v2/noaa_co2_mm_mlo.csv"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/exp_015_sharp_over_time/run_20261125_v1"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silso", default=DEFAULT_SILSO, type=Path)
    parser.add_argument("--noaa", default=DEFAULT_NOAA, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT, type=Path)
    args = parser.parse_args(argv)

    results = run_investigation(args.silso, args.noaa, args.output)

    print(f"verdict: {results['verdict']}")
    print(f"conditions: {results['conditions']}")
    print(f"controls: {results['controls']}")
    print(f"aggregate_choice: {results['aggregate_choice']}")
    print(f"best_moderate: {results['best_moderate']}")
    print(f"moderate_gains: {results['moderate_gains']}")
    print(f"limit_gain_unconditional: {results['limit_gain_unconditional']:.6f}")
    print(f"limit_gain_conditional: {results['limit_gain_conditional']:.6f}")
    print(f"limit_per_cell_conditional: {results['limit_per_cell_conditional']}")
    print(f"per_cell: {results['per_cell_improved']}/{results['per_cell_total']} improved")
    print(f"win_rates: {results['win_rates']}")
    print("--- summary ---")
    for label, entry in results["summary"].items():  # type: ignore[union-attr]
        print(
            f"alpha={label:<5} n={entry['months']:6d} "
            f"u_med={entry['unconditional_median']:.4f} u_mean={entry['unconditional_mean']:8.3f} "
            f"hit={entry['hit_share']:.4f} | c_med {entry['conditional_median_base']:.4f}"
            f" -> {entry['conditional_median_sharp']:.4f} (n={entry['conditional_months']})"
        )


if __name__ == "__main__":
    main()
