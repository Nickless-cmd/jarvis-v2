#!/usr/bin/env python3
"""Entrypoint for Investigation 13 — the regime where retention has a reliable sign."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_013_retention_sign import run_investigation  # noqa: E402

DEFAULT_SILSO = (
    PROJECT_ROOT
    / "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
)
DEFAULT_NOAA = PROJECT_ROOT / "artifacts/exp_006_order/noaa_20261030_v2/noaa_co2_mm_mlo.csv"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--silso", default=DEFAULT_SILSO, type=Path)
    parser.add_argument("--noaa", default=DEFAULT_NOAA, type=Path)
    args = parser.parse_args(argv)

    results = run_investigation(args.silso, args.noaa, args.output)
    print(f"verdict: {results['verdict']}")
    print(f"conditions: {results['conditions_fired']}")
    controls = results["controls"]
    print(
        "months: {months_total} | ensemble beats oracle: {months_ensemble_beats_oracle} "
        "| worst err/oracle: {worst_error_over_oracle:.2f}".format(**controls)
    )
    print(
        "cross share: median {cross_share_median:+.4f} "
        "| amplify in {cells_where_experts_amplify}/{cells_total} cells".format(**controls)
    )
    print(
        "split-half R2: a={split_half_r2_a} b={split_half_r2_b} "
        "(same half {same_half_r2})".format(**controls)
    )
    regime = results["regime"]
    print(f"corr(ratio, d_err): {regime['corr_ratio_d_err']}")
    print(f"best ex ante predictor: {regime['best_ex_ante_predictor']} R2={regime['best_ex_ante_r2']}")
    print(f"ex ante R2 all: {regime['ex_ante_r2']}")
    print("hold-out:")
    for key, value in controls["hold_out"].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
