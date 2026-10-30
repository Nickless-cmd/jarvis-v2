#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_005_learning import (  # noqa: E402
    SOURCE_URL,
    run_investigation,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source", default=SOURCE_URL)
    args = parser.parse_args()
    run_investigation(args.source, args.output)


if __name__ == "__main__":
    main()
