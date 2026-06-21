"""Boundary-capture for Centralen (§10). Kør en nerve bag en grænse: enhver
exception, malformet input eller anomali fanges og returneres som ErrorRecord —
funktionen kaster ALDRIG selv (§10.3 selv-sikker)."""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from core.services.gate_kernel import GateClass


@dataclass
class ErrorRecord:
    nerve: str
    cluster: str
    kind: str                      # exception|timeout|malformed|sink_down|learning_down|cascade|catcher
    message: str
    klass: GateClass = GateClass.COGNITIVE
    latency_ms: int = 0
    stack: str = ""
    signal: dict[str, Any] | None = None


def safe_call(fn: Callable[[dict], Any], ctx: Any, *, nerve: str = "",
              cluster: str = "", klass: GateClass = GateClass.COGNITIVE
              ) -> tuple[Any, ErrorRecord | None]:
    """Returnér (resultat, None) ved succes, ellers (None, ErrorRecord). Kaster aldrig."""
    t0 = time.monotonic()
    if not isinstance(ctx, dict):
        return None, ErrorRecord(nerve, cluster, "malformed",
                                 f"ctx ikke dict: {type(ctx).__name__}", klass)
    try:
        return fn(ctx), None
    except Exception as e:  # noqa: BLE001 — grænse-fangst er hele pointen
        return None, ErrorRecord(
            nerve, cluster, "exception", f"{type(e).__name__}: {e}", klass,
            int((time.monotonic() - t0) * 1000), traceback.format_exc(),
            {k: ctx.get(k) for k in ("run_id", "session_id")},
        )
