#!/usr/bin/env python3
"""Analyze changing perspectives in the preserved deployed observations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_003_change import (  # noqa: E402
    Experiment003Config,
    analyze_experiment_003,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--window-rows", type=int, default=2000)
    parser.add_argument("--step-rows", type=int, default=500)
    parser.add_argument("--permutations", type=int, default=200)
    args = parser.parse_args()
    result = analyze_experiment_003(
        args.run,
        args.output,
        REPO_ROOT,
        Experiment003Config(
            window_rows=args.window_rows,
            step_rows=args.step_rows,
            permutations=args.permutations,
        ),
    )
    print(
        "Investigation 3:",
        len(result["rolling_windows"]),
        "rolling windows; output",
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
