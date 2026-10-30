#!/usr/bin/env python3
"""Generate the opaque raw sources for Investigation 2."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_002_sources import (  # noqa: E402
    GenerationConfig,
    generate_dataset,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=202610302)
    parser.add_argument("--discovery-rows", type=int, default=1024)
    parser.add_argument("--confirmation-rows", type=int, default=2048)
    args = parser.parse_args()
    generate_dataset(
        args.output,
        GenerationConfig(
            seed=args.seed,
            discovery_rows=args.discovery_rows,
            confirmation_rows=args.confirmation_rows,
        ),
    )
    print(f"Created opaque observations: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
