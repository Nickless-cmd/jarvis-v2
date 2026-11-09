#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_006_order import run_investigation  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--source",
        default="fetch",
        help="'fetch' downloads the NOAA file; otherwise a path to a local copy "
        "(e.g. a preserved artifacts/exp_006_order/*/noaa_co2_mm_mlo.csv).",
    )
    args = parser.parse_args(argv)
    run_investigation(args.source, args.output)


if __name__ == "__main__":
    main()
