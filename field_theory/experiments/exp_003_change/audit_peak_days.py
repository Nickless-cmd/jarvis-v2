#!/usr/bin/env python3
"""Preserve a post-hoc day-by-model audit of Investigation 3's peak."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_003_change import audit_peak_days  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit_peak_days(args.run, args.output, REPO_ROOT)
    print("Wrote post-hoc peak day audit:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
