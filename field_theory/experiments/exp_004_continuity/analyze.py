#!/usr/bin/env python3
"""Analyze relational recurrence and historical expectation on the live snapshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_004_continuity import (  # noqa: E402
    Experiment004Config,
    analyze_experiment_004,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--block-rows", type=int, default=1000)
    args = parser.parse_args()
    result = analyze_experiment_004(
        args.run,
        args.output,
        REPO_ROOT,
        Experiment004Config(block_rows=args.block_rows),
    )
    target_count = len(
        {row["target_block"] for row in result["historical_expectations"]}
    )
    print(
        "Investigation 4:",
        len(result["blocks"]),
        "states and",
        target_count,
        "historical targets; output",
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
