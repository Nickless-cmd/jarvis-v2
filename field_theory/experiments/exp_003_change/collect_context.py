#!/usr/bin/env python3
"""Collect privacy-limited aggregate context on deployed CT105."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_003_change import (  # noqa: E402
    OperationalContextConfig,
    collect_operational_context,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--db", type=Path, default=Path("/home/bs/.jarvis-v2/state/jarvis.db")
    )
    parser.add_argument("--expected-host", default="Jarvis")
    args = parser.parse_args()
    collect_operational_context(
        args.run,
        args.output,
        REPO_ROOT,
        OperationalContextConfig(db_path=args.db, expected_host=args.expected_host),
    )
    print("Wrote aggregate operational context:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
