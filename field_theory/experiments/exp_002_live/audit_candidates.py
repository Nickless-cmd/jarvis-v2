#!/usr/bin/env python3
"""Preserve all live candidate scores as an explicitly post-hoc audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_002_live import (  # noqa: E402
    audit_live_candidate_scores,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    audit_live_candidate_scores(args.run, REPO_ROOT)
    print(f"Wrote post-hoc candidate audit: {args.run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
