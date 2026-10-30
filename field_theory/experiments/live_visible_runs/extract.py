#!/usr/bin/env python3
"""Extract privacy-limited visible-run observations on deployed CT105."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.live_visible_runs import (  # noqa: E402
    LiveExtractionConfig,
    extract_live_visible_runs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--db", type=Path, default=Path("/home/bs/.jarvis-v2/state/jarvis.db")
    )
    parser.add_argument("--expected-host", default="Jarvis")
    args = parser.parse_args()
    extract_live_visible_runs(
        args.output,
        LiveExtractionConfig(db_path=args.db, expected_host=args.expected_host),
        REPO_ROOT,
    )
    print(f"Created read-only live extract: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
