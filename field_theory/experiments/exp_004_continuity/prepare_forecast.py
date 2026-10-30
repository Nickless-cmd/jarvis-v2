#!/usr/bin/env python3
"""Freeze Investigation 4 forecasts before prospective outcome access."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_004_prospective import (  # noqa: E402
    prepare_prospective_forecast,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare_prospective_forecast(args.run, args.analysis, args.output, REPO_ROOT)
    print("Froze prospective forecasts:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
