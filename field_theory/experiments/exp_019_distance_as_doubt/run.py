#!/usr/bin/env python3
"""Entrypoint for Investigation 19 — is the distance a self-doubt signal?"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_019_distance_as_doubt import (  # noqa: E402
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
        default=PROJECT_ROOT / "artifacts/exp_019_distance_as_doubt/run",
    )
    args = parser.parse_args()

    result = run_investigation(args.silso, args.noaa, args.out)
    print("verdict:", result["verdict"])
    print("conditions:", result["conditions"])
    print("controls:", result["controls"])
    print("auc:", result["auc"])
    print("quartiles:")
    for entry in result["quartiles"]:  # type: ignore[union-attr]
        print(
            f"  Q{int(entry['quartile'])}: months={int(entry['months'])} "
            f"error_rate={entry['error_rate']:.4f} "
            f"distance=[{entry['distance_low']:.3f}, {entry['distance_high']:.3f}]"
        )
    print("transfer:", result["transfer"])
    print(f"abstentions: {len(result['abstentions'])}")  # type: ignore[arg-type]
    for entry in result["abstentions"][:6]:  # type: ignore[index]
        print(
            f"  {entry['source']}/{entry['expert_set']} W={entry['window']} "
            f"thr={entry['threshold']:.3f} "
            f"dev_prec={entry['development_precision']:.3f} "
            f"test_prec={entry['test_precision']:.3f} "
            f"baseline={entry['baseline_precision']:.3f} "
            f"coverage={entry['test_coverage']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
