"""Mål cold + warm import-tid for core.runtime.db.

Brug: python scripts/db_split_baseline.py [--label LABEL]

Skriver én linje per kørsel til scripts/.db_split_baseline.log med format:
  ISO_TIME  LABEL  cold=XX.XXms  warm=YY.YYms
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def measure(label: str) -> tuple[float, float]:
    repo = Path(__file__).resolve().parent.parent
    # Nuke .pyc cache for core.runtime
    for cache in (repo / "core" / "runtime").rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)

    # Cold: fresh process, no .pyc
    cold = subprocess.check_output(
        [sys.executable, "-c",
         "import time; t=time.perf_counter(); "
         "from core.runtime import db; "
         "print(f'{(time.perf_counter()-t)*1000:.2f}')"],
        cwd=repo, text=True).strip()

    # Warm: fresh process, .pyc now cached
    warm = subprocess.check_output(
        [sys.executable, "-c",
         "import time; t=time.perf_counter(); "
         "from core.runtime import db; "
         "print(f'{(time.perf_counter()-t)*1000:.2f}')"],
        cwd=repo, text=True).strip()

    return float(cold), float(warm)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--label", default="unspecified")
    args = p.parse_args()

    cold, warm = measure(args.label)
    line = f"{datetime.now(UTC).isoformat()}  {args.label}  cold={cold:.2f}ms  warm={warm:.2f}ms\n"
    log = Path(__file__).resolve().parent / ".db_split_baseline.log"
    log.write_text((log.read_text() if log.exists() else "") + line)
    print(line.strip())


if __name__ == "__main__":
    main()
