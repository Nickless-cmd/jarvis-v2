#!/usr/bin/env python3
"""Smoke-test the jarvis-runtime startup path WITHOUT serving traffic.

Imports the FastAPI app and runs its lifespan context to completion. If
lifespan startup raises (TypeError on bad kwargs, missing DB column,
import failure, daemon init crash, etc.), this script exits non-zero —
which catches the class of bug that puts jarvis-runtime in a systemd
restart loop.

Usage:
    conda activate ai
    python scripts/smoke_test_startup.py

Exit codes:
    0  — lifespan started + shut down cleanly
    1  — exception during startup (script prints the traceback)
    2  — script ran longer than timeout (currently 60s)

Recommended: run before pushing changes that touch runtime startup paths
(apps/api/jarvis_api/app.py, core/runtime/db.py, core/services/*runtime*.py,
or anything imported during lifespan).
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys
import time
import traceback
from pathlib import Path

# Ensure repo root is importable when run as a script
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


_TIMEOUT_SECONDS = 60


async def _run_lifespan() -> None:
    """Import app + drive lifespan context to completion."""
    # Skip the noisy parts that would fail on a dev box without all creds.
    # The point is to catch *startup* TypeErrors / schema drift / import
    # failures — not to validate that every external service is reachable.
    os.environ.setdefault("JARVIS_SMOKE_TEST", "1")

    from apps.api.jarvis_api.app import create_app
    app = create_app()

    # FastAPI's lifespan can be driven manually via the router's lifespan
    # context manager. We enter it (= startup) and exit (= shutdown). If
    # any startup hook raises, the context manager re-raises here.
    async with app.router.lifespan_context(app):
        # Startup completed without exception — that's the whole point.
        pass


def main() -> int:
    started = time.monotonic()
    try:
        asyncio.run(asyncio.wait_for(_run_lifespan(), timeout=_TIMEOUT_SECONDS))
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - started
        print(
            f"smoke_test_startup: TIMEOUT after {elapsed:.1f}s "
            f"(limit {_TIMEOUT_SECONDS}s) — startup hung",
            file=sys.stderr,
        )
        return 2
    except Exception:
        elapsed = time.monotonic() - started
        print(
            f"smoke_test_startup: FAILED after {elapsed:.1f}s",
            file=sys.stderr,
        )
        traceback.print_exc()
        return 1

    elapsed = time.monotonic() - started
    print(f"smoke_test_startup: OK in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    # Ignore SIGPIPE so child-process noise doesn't make this misreport
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
