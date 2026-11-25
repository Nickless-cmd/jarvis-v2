#!/usr/bin/env python3
"""Entrypoint for Investigation 18b — lag-structure fingerprint (exploratory)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_018b_lag_fingerprint import run_investigation  # noqa: E402

DEFAULT_SILSO = (
    PROJECT_ROOT / "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
)
DEFAULT_NOAA = PROJECT_ROOT / "artifacts/exp_006_order/noaa_20261030_v2/noaa_co2_mm_mlo.csv"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silso", default=DEFAULT_SILSO, type=Path)
    parser.add_argument("--noaa", default=DEFAULT_NOAA, type=Path)
    parser.add_argument("--output", default=None, type=Path)
    args = parser.parse_args(argv)

    output = args.output
    if output is None:
        base = PROJECT_ROOT / "artifacts/exp_018b_lag_fingerprint"
        index = 1
        while (base / f"run_20261125_v{index}").exists():
            index += 1
        output = base / f"run_20261125_v{index}"

    results = run_investigation(args.silso, args.noaa, output)

    print(f"verdict: {results['verdict']}")
    print(f"conditions: {results['conditions']}")
    print(f"controls: {results['controls']}")
    for window, aggregate in results["windows"].items():  # type: ignore[union-attr]
        print(f"  W={window}: {aggregate}")


if __name__ == "__main__":
    main()
