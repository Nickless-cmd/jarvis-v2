#!/usr/bin/env python3
"""Entrypoint for Investigation 12 — where retention reaches the forecast."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_012_forecast_path import run_investigation  # noqa: E402

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
    print(f"controls: {results['controls']}")
    variance = results["variance"]
    print(f"eta2: {variance['eta_squared']}")
    print(f"r2_oracle: {variance['r2_oracle']}  r2_top_weight: {variance['r2_top_weight']}")
    effect = results["retention_effect"]
    print(
        "retention: median {:.4f} mean {:.4f} fall {}/{}".format(
            effect["median_d_err"],
            effect["mean_d_err"],
            effect["pairs_where_error_falls"],
            effect["pairs"],
        )
    )
    print(f"cells: {len(results['cells'])}")


if __name__ == "__main__":
    main()
