#!/usr/bin/env python3
"""Check availability and evaluate only the frozen prospective target."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_004_prospective import (  # noqa: E402
    ProspectiveEvaluationConfig,
    evaluate_prospective,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--db", type=Path, default=Path("/home/bs/.jarvis-v2/state/jarvis.db")
    )
    parser.add_argument("--expected-host", default="Jarvis")
    args = parser.parse_args()
    result = evaluate_prospective(
        args.forecast,
        args.output,
        REPO_ROOT,
        ProspectiveEvaluationConfig(db_path=args.db, expected_host=args.expected_host),
    )
    print("Prospective status:", result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
