"""Trace-sink for Centralen (§3.2/§7). En trådsikker, volumen-tolerant ring-buffer
af strukturerede records nøglet på run_id. Slip ALDRIG en exception ud (selv-sikker)."""
from __future__ import annotations

import collections
import threading
from dataclasses import dataclass
from typing import Any

_MAX = 2000


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


class TraceSink:
    def __init__(self, maxlen: int = _MAX) -> None:
        self._buf: "collections.deque[TraceRecord]" = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self.dropped = 0

    def record(self, rec: TraceRecord) -> None:
        try:
            with self._lock:
                self._buf.append(rec)
        except Exception:
            self.dropped += 1

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
