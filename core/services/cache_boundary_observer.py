"""Cache-boundary drift observer (harness Part B, Mechanism A).

Zero prompt mutation. The system message is the STATIC prompt prefix (all
per-turn dynamic content is relocated to the last user message). This observer
records the last hash of that prefix per (provider, model, section_shape) and
flags when the SAME shape produces a DIFFERENT hash run-over-run — i.e. a byte
changed in the cached prefix, which silently busts provider prefix-caching.
Pure observability → nerve context/cache_boundary_drift. Never raises."""
from __future__ import annotations

import threading

_lock = threading.Lock()
_last_sha: dict[tuple, str] = {}


def observe_static_prefix(
    *,
    provider: str,
    model: str,
    section_shape: tuple,
    static_prefix_sha: str,
) -> None:
    """Record the static-prefix hash for (provider, model, shape); on a same-shape
    change from the previous run, emit the drift nerve. Best-effort, never raises."""
    try:
        sha = str(static_prefix_sha or "")
        if not sha:
            return
        key = (str(provider or ""), str(model or ""), tuple(section_shape or ()))
        with _lock:
            prev = _last_sha.get(key)
            _last_sha[key] = sha
        if prev is None or prev == sha:
            return
        try:
            from core.services import central_timeseries as _cts
            _cts.record("context", "cache_boundary_drift", 1.0, meta={
                "provider": key[0], "model": key[1], "shape": list(key[2]),
            })
        except Exception:
            pass
    except Exception:
        pass
