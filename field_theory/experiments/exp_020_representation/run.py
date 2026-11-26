#!/usr/bin/env python3
"""Entrypoint for Investigation 20 — can representation separate the series?"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_020_representation import (  # noqa: E402
    run_investigation,
)

DEFAULT_SILSO = (
    PROJECT_ROOT
    / "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
)
DEFAULT_NOAA = (
    PROJECT_ROOT / "artifacts/exp_006_order/noaa_20261030_v2/noaa_co2_mm_mlo.csv"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silso", type=Path, default=DEFAULT_SILSO)
    parser.add_argument("--noaa", type=Path, default=DEFAULT_NOAA)
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "artifacts/exp_020_representation/run",
    )
    args = parser.parse_args()

    result = run_investigation(args.silso, args.noaa, args.out)
    print("verdict:", result["verdict"])
    print("hypotheses:", result["hypotheses"])
    print(f"baseline passing C3: {result['baseline_passing']}/40")
    print(f"best representation: {result['best_representation']} "
          f"({result['best_passing']}/40)")
    print(f"irrelevant control:  {result['irrelevant_passing']}/40")
    print("accuracy:", result["accuracy"])
    print()
    print(f"{'representation':22} {'pass':>5} {'share':>7} {'median C3':>10} {'acc':>7} {'feat':>5}")
    for name, entry in result["summary"].items():  # type: ignore[union-attr]
        print(
            f"{name:22} {int(entry['passing_c3']):>5} "
            f"{entry['passing_share']:7.3f} "
            f"{entry['median_identity_rate']:10.3f} "
            f"{entry['mean_accuracy_in_passing']:7.3f} "
            f"{int(entry['feature_count']):>5}"
        )
    print()
    print("controls:", result["controls"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
