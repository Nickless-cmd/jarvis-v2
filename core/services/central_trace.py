"""Trace-sink for Centralen (§3.2/§7). En trådsikker, volumen-tolerant ring-buffer
af strukturerede records nøglet på run_id. Slip ALDRIG en exception ud (selv-sikker)."""
from __future__ import annotations

import collections
import queue as _queue
import threading
import time
from dataclasses import dataclass
from typing import Any

_MAX = 2000
_SUB_MAX = 256  # pr. subscriber-kø; ældre droppes hvis konsumenten ikke følger med


@dataclass
class TraceRecord:
    run_id: str
    session_id: str
    cluster: str
    nerve: str
    kind: str                       # decide|observe|error
    decision: str = ""
    reason: str = ""
    latency_ms: int = 0
    payload: dict[str, Any] | None = None
    ts: float = 0.0                 # wall-clock ved record (cross-proces feed-fletning)


class TraceSink:
    def __init__(self, maxlen: int = _MAX) -> None:
        self._buf: "collections.deque[TraceRecord]" = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._subs: "list[_queue.Queue]" = []   # live SSE-abonnenter (owner-stream)
        self._sublock = threading.Lock()
        self.dropped = 0

    def record(self, rec: TraceRecord) -> None:
        try:
            if not rec.ts:
                rec.ts = time.time()
        except Exception:
            pass
        try:
            with self._lock:
                self._buf.append(rec)
        except Exception:
            self.dropped += 1
        # Push til live-abonnenter (SSE) — non-blocking, self-safe: en langsom konsument
        # taber gamle records (put_nowait → Full ignoreres), aldrig den hotte sti.
        try:
            with self._sublock:
                subs = list(self._subs)
            for q in subs:
                try:
                    q.put_nowait(rec)
                except Exception:
                    pass
        except Exception:
            pass
        # Cross-proces tee: publicér (throttled) denne proces' feed+sundhed til shared_cache
        # så owner-snapshottet kan flette runtime- OG api-processens fyringer. Lazy import
        # (undgår cyklus) + fuldt self-safe (en tee-fejl må aldrig røre den hotte sti).
        try:
            from core.services import central_xproc
            central_xproc.maybe_publish()
        except Exception:
            pass

    def subscribe(self) -> "_queue.Queue":
        q: "_queue.Queue" = _queue.Queue(maxsize=_SUB_MAX)
        with self._sublock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q: "_queue.Queue") -> None:
        try:
            with self._sublock:
                if q in self._subs:
                    self._subs.remove(q)
        except Exception:
            pass

    def records_for_run(self, run_id: str) -> list[TraceRecord]:
        with self._lock:
            return [r for r in self._buf if r.run_id == run_id]

    def recent(self, limit: int = 50) -> list[TraceRecord]:
        with self._lock:
            return list(self._buf)[-limit:]


_SINK: TraceSink | None = None


def sink() -> TraceSink:
    global _SINK
    if _SINK is None:
        _SINK = TraceSink()
    return _SINK
